import os
import json
import hmac
import hashlib
import base64
import sqlite3
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.environ.get("LICENSEFLOW_DB", os.path.join(BASE_DIR, "db.sqlite3"))
JWT_SECRET = os.environ.get(
    "LICENSEFLOW_JWT_SECRET",
    "change-this-local-development-secret",
)
ACCESS_MINUTES = 60
REFRESH_DAYS = 7

app = Flask(__name__)
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def rows(sql, params=()):
    return [dict(r) for r in db().execute(sql, params).fetchall()]


def one(sql, params=()):
    r = db().execute(sql, params).fetchone()
    return dict(r) if r else None


def table_exists(name):
    return one(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (name,),
    ) is not None


def ensure_schema():
    """Create a clean SQLite schema when no legacy Django database is supplied."""
    conn = sqlite3.connect(DATABASE)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE,
      email TEXT NOT NULL DEFAULT '', password_hash TEXT NOT NULL,
      first_name TEXT NOT NULL DEFAULT '', last_name TEXT NOT NULL DEFAULT '',
      role TEXT NOT NULL DEFAULT 'customer', is_active INTEGER NOT NULL DEFAULT 1,
      created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS customer_profiles (
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
      phone TEXT NOT NULL DEFAULT '', company TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS subscription_plans (
      id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
      price NUMERIC NOT NULL DEFAULT 0, billing_cycle TEXT NOT NULL DEFAULT 'monthly',
      max_users INTEGER NOT NULL DEFAULT 1, max_devices INTEGER NOT NULL DEFAULT 1,
      is_active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS subscriptions (
      id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER NOT NULL REFERENCES customer_profiles(id),
      plan_id INTEGER NOT NULL REFERENCES subscription_plans(id), start_date TEXT NOT NULL,
      expiry_date TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'ACTIVE',
      razorpay_subscription_id TEXT, auto_renew INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS licenses (
      id INTEGER PRIMARY KEY AUTOINCREMENT, subscription_id INTEGER NOT NULL UNIQUE REFERENCES subscriptions(id),
      license_key TEXT NOT NULL UNIQUE, status TEXT NOT NULL DEFAULT 'ACTIVE', activation_date TEXT NOT NULL,
      expiry_date TEXT NOT NULL, last_verified TEXT, verification_count INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS transactions (
      id INTEGER PRIMARY KEY AUTOINCREMENT, transaction_id TEXT NOT NULL UNIQUE, customer_id INTEGER NOT NULL REFERENCES customer_profiles(id),
      subscription_id INTEGER REFERENCES subscriptions(id), amount NUMERIC NOT NULL DEFAULT 0,
      payment_method TEXT NOT NULL DEFAULT 'OTHER', razorpay_payment_id TEXT, status TEXT NOT NULL DEFAULT 'PENDING',
      transaction_date TEXT NOT NULL, created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS invoices (
      id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_id TEXT NOT NULL UNIQUE, customer_id INTEGER NOT NULL REFERENCES customer_profiles(id),
      transaction_id INTEGER NOT NULL UNIQUE REFERENCES transactions(id), amount NUMERIC NOT NULL DEFAULT 0,
      status TEXT NOT NULL DEFAULT 'PAID', invoice_date TEXT NOT NULL, pdf_generated INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()


def legacy_mode():
    conn = sqlite3.connect(DATABASE)
    names = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    conn.close()
    return "auth_user" in names and "core_customerprofile" in names


def django_password_matches(encoded, password):
    """Verify Werkzeug hashes and common Django PBKDF2 password hashes."""
    if not isinstance(encoded, str):
        return False

    if encoded.startswith(("scrypt:", "pbkdf2:")):
        try:
            return check_password_hash(encoded, password)
        except (ValueError, TypeError):
            return False

    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)

        if algorithm == "pbkdf2_sha256":
            digest = "sha256"
        elif algorithm == "pbkdf2_sha1":
            digest = "sha1"
        else:
            return False

        actual = hashlib.pbkdf2_hmac(
            digest,
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        )
        actual_hash = base64.b64encode(actual).decode("ascii")
        return hmac.compare_digest(actual_hash, expected)
    except (ValueError, TypeError):
        return False


def find_user(identifier):
    if legacy_mode():
        return one(
            """SELECT id, username, email, password, first_name, last_name,
                      is_staff, is_superuser, is_active
               FROM auth_user
               WHERE username = ? COLLATE NOCASE
                  OR email = ? COLLATE NOCASE
               LIMIT 1""",
            (identifier, identifier),
        )
    return one(
        """SELECT id, username, email, password_hash, first_name, last_name,
                  role, is_active
           FROM users
           WHERE username = ? COLLATE NOCASE
              OR email = ? COLLATE NOCASE
           LIMIT 1""",
        (identifier, identifier),
    )


def user_role(user):
    if "is_superuser" in user:
        return (
            "owner"
            if user.get("is_staff") or user.get("is_superuser")
            else "customer"
        )
    return "owner" if user.get("role") in ("owner", "admin") else "customer"


def user_payload(user):
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user.get("email", ""),
        "first_name": user.get("first_name", ""),
        "last_name": user.get("last_name", ""),
        "role": user_role(user),
    }


def issue_token(user, token_type="access"):
    now = datetime.now(timezone.utc)
    exp = now + (
        timedelta(days=REFRESH_DAYS)
        if token_type == "refresh"
        else timedelta(minutes=ACCESS_MINUTES)
    )
    return jwt.encode(
        {
            "sub": str(user["id"]),
            "username": user["username"],
            "role": user_role(user),
            "type": token_type,
            "iat": now,
            "exp": exp,
        },
        JWT_SECRET,
        algorithm="HS256",
    )


def current_user():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        payload = jwt.decode(auth[7:], JWT_SECRET, algorithms=["HS256"])
        if payload.get("type") != "access":
            return None
        if legacy_mode():
            user = one(
                """SELECT id, username, email, first_name, last_name,
                          is_staff, is_superuser, is_active
                   FROM auth_user WHERE id=?""",
                (int(payload["sub"]),),
            )
        else:
            user = one(
                """SELECT id, username, email, first_name, last_name, role, is_active
                   FROM users WHERE id=?""",
                (int(payload["sub"]),),
            )
        return user if user and user.get("is_active", 1) else None
    except Exception:
        return None


def require_auth(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            return jsonify({
                "detail": "Authentication credentials were not provided or are invalid."
            }), 401
        g.user = user
        return fn(*args, **kwargs)
    return wrapped


def require_admin(fn):
    @wraps(fn)
    @require_auth
    def wrapped(*args, **kwargs):
        if user_role(g.user) != "owner":
            return jsonify({"detail": "Administrator access required."}), 403
        return fn(*args, **kwargs)
    return wrapped


def customers_data():
    if legacy_mode():
        return rows(
            """SELECT cp.id,
                      COALESCE(NULLIF(trim(u.first_name || ' ' || u.last_name), ''), u.username) AS name,
                      u.email, cp.phone, cp.company, cp.created_at, cp.user_id
               FROM core_customerprofile cp
               JOIN auth_user u ON u.id=cp.user_id
               ORDER BY cp.id DESC"""
        )
    return rows(
        """SELECT cp.id,
                  COALESCE(NULLIF(trim(u.first_name || ' ' || u.last_name), ''), u.username) AS name,
                  u.email, cp.phone, cp.company, cp.created_at, cp.user_id
           FROM customer_profiles cp
           JOIN users u ON u.id=cp.user_id
           ORDER BY cp.id DESC"""
    )


def list_plans():
    table = "core_subscriptionplan" if legacy_mode() else "subscription_plans"
    return rows(f"SELECT * FROM {table} ORDER BY id DESC")


def list_subscriptions():
    if legacy_mode():
        return rows(
            """SELECT s.*, p.name AS plan_name, cp.id AS customer_id,
                      COALESCE(NULLIF(trim(u.first_name || ' ' || u.last_name), ''), u.username) AS customer_name
               FROM core_subscription s
               JOIN core_subscriptionplan p ON p.id=s.plan_id
               JOIN core_customerprofile cp ON cp.id=s.customer_id
               JOIN auth_user u ON u.id=cp.user_id
               ORDER BY s.id DESC"""
        )
    return rows(
        """SELECT s.*, p.name AS plan_name, cp.id AS customer_id,
                  COALESCE(NULLIF(trim(u.first_name || ' ' || u.last_name), ''), u.username) AS customer_name
           FROM subscriptions s
           JOIN subscription_plans p ON p.id=s.plan_id
           JOIN customer_profiles cp ON cp.id=s.customer_id
           JOIN users u ON u.id=cp.user_id
           ORDER BY s.id DESC"""
    )


def list_licenses():
    if legacy_mode():
        return rows(
            """SELECT l.*, p.name AS plan_name,
                      COALESCE(NULLIF(trim(u.first_name || ' ' || u.last_name), ''), u.username) AS customer_name
               FROM core_license l
               JOIN core_subscription s ON s.id=l.subscription_id
               JOIN core_subscriptionplan p ON p.id=s.plan_id
               JOIN core_customerprofile cp ON cp.id=s.customer_id
               JOIN auth_user u ON u.id=cp.user_id
               ORDER BY l.id DESC"""
        )
    return rows(
        """SELECT l.*, p.name AS plan_name,
                  COALESCE(NULLIF(trim(u.first_name || ' ' || u.last_name), ''), u.username) AS customer_name
           FROM licenses l
           JOIN subscriptions s ON s.id=l.subscription_id
           JOIN subscription_plans p ON p.id=s.plan_id
           JOIN customer_profiles cp ON cp.id=s.customer_id
           JOIN users u ON u.id=cp.user_id
           ORDER BY l.id DESC"""
    )


def list_transactions():
    if legacy_mode():
        return rows(
            """SELECT t.*,
                      COALESCE(NULLIF(trim(u.first_name || ' ' || u.last_name), ''), u.username) AS customer_name
               FROM core_transaction t
               JOIN core_customerprofile cp ON cp.id=t.customer_id
               JOIN auth_user u ON u.id=cp.user_id
               ORDER BY t.id DESC"""
        )
    return rows(
        """SELECT t.*,
                  COALESCE(NULLIF(trim(u.first_name || ' ' || u.last_name), ''), u.username) AS customer_name
           FROM transactions t
           JOIN customer_profiles cp ON cp.id=t.customer_id
           JOIN users u ON u.id=cp.user_id
           ORDER BY t.id DESC"""
    )


def list_invoices():
    if legacy_mode():
        return rows(
            """SELECT i.*,
                      COALESCE(NULLIF(trim(u.first_name || ' ' || u.last_name), ''), u.username) AS customer_name
               FROM core_invoice i
               JOIN core_customerprofile cp ON cp.id=i.customer_id
               JOIN auth_user u ON u.id=cp.user_id
               ORDER BY i.id DESC"""
        )
    return rows(
        """SELECT i.*,
                  COALESCE(NULLIF(trim(u.first_name || ' ' || u.last_name), ''), u.username) AS customer_name
           FROM invoices i
           JOIN customer_profiles cp ON cp.id=i.customer_id
           JOIN users u ON u.id=cp.user_id
           ORDER BY i.id DESC"""
    )


@app.get("/")
def index():
    return jsonify({"service": "LicenseFlow Python API", "status": "ok"})


@app.get("/health/")
def health():
    return jsonify({"status": "ok", "message": "LicenseFlow backend is running"})


@app.post("/auth/login/")
def login():
    data = request.get_json(silent=True) or {}
    identifier = str(data.get("username") or data.get("email") or "").strip()
    password = str(data.get("password") or "")

    if not identifier or not password:
        return jsonify({
            "error": "Username/email and password are required."
        }), 400

    user = find_user(identifier)
    if not user or not user.get("is_active", 1):
        return jsonify({"error": "Invalid username or password."}), 401

    if legacy_mode():
        valid = django_password_matches(user.get("password", ""), password)
    else:
        try:
            valid = check_password_hash(user.get("password_hash", ""), password)
        except (ValueError, TypeError):
            valid = False

    if not valid:
        return jsonify({"error": "Invalid username or password."}), 401

    return jsonify({
        "access": issue_token(user, "access"),
        "refresh": issue_token(user, "refresh"),
        "user": user_payload(user),
    }), 200


@app.post("/auth/refresh/")
def refresh():
    data = request.get_json(silent=True) or {}
    token = str(data.get("refresh") or "")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise ValueError("Not a refresh token")
        if legacy_mode():
            user = one(
                """SELECT id, username, email, first_name, last_name,
                          is_staff, is_superuser, is_active
                   FROM auth_user WHERE id=?""",
                (int(payload["sub"]),),
            )
        else:
            user = one(
                """SELECT id, username, email, first_name, last_name, role, is_active
                   FROM users WHERE id=?""",
                (int(payload["sub"]),),
            )
        if not user or not user.get("is_active", 1):
            raise ValueError("User inactive")
        return jsonify({
            "access": issue_token(user, "access"),
            "refresh": issue_token(user, "refresh"),
        })
    except Exception:
        return jsonify({"detail": "Refresh token is invalid or expired."}), 401


@app.get("/auth/me/")
@require_auth
def me():
    return jsonify({"user": user_payload(g.user), **user_payload(g.user)})


@app.post("/auth/register/")
def register():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    password = str(data.get("password") or "")

    if not username or not email or len(password) < 8:
        return jsonify({
            "error": "Username, email, and a password of at least 8 characters are required."
        }), 400

    if legacy_mode():
        return jsonify({
            "error": "Registration is not enabled for the legacy database. An administrator must migrate it to the new Python schema first."
        }), 409

    conn = db()
    try:
        cur = conn.execute(
            """INSERT INTO users
               (username, email, password_hash, first_name, last_name, role, is_active, created_at)
               VALUES (?, ?, ?, ?, ?, 'customer', 1, ?)""",
            (
                username, email, generate_password_hash(password),
                str(data.get("first_name") or ""),
                str(data.get("last_name") or ""),
                now_iso(),
            ),
        )
        user_id = cur.lastrowid
        conn.execute(
            """INSERT INTO customer_profiles (user_id, phone, company, created_at)
               VALUES (?, ?, ?, ?)""",
            (
                user_id, str(data.get("phone") or ""),
                str(data.get("company") or ""), now_iso(),
            ),
        )
        conn.commit()
        user = one(
            "SELECT id, username, email, first_name, last_name, role, is_active FROM users WHERE id=?",
            (user_id,),
        )
        return jsonify({
            "access": issue_token(user),
            "refresh": issue_token(user, "refresh"),
            "user": user_payload(user),
        }), 201
    except sqlite3.IntegrityError:
        conn.rollback()
        return jsonify({"error": "Username or email already exists."}), 409


@app.get("/customers/")
@require_admin
def customers():
    return jsonify(customers_data())


@app.get("/customers/<int:customer_id>/")
@require_admin
def customer_detail(customer_id):
    result = next(
        (c for c in customers_data() if c["id"] == customer_id),
        None,
    )
    return (jsonify(result), 200) if result else (
        jsonify({"error": "Customer not found."}), 404
    )


@app.route("/plans/", methods=["GET", "POST"])
@require_auth
def plans():
    if request.method == "GET":
        return jsonify(list_plans())

    if user_role(g.user) != "owner":
        return jsonify({"detail": "Administrator access required."}), 403

    data = request.get_json(silent=True) or {}
    name = str(data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Plan name is required."}), 400

    table = "core_subscriptionplan" if legacy_mode() else "subscription_plans"
    cur = db().execute(
        f"""INSERT INTO {table}
            (name, description, price, billing_cycle, max_users, max_devices, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            name, data.get("description", ""), data.get("price", 0),
            data.get("billing_cycle", "monthly"), int(data.get("max_users", 1)),
            int(data.get("max_devices", 1)), int(data.get("is_active", 1)),
            now_iso(),
        ),
    )
    db().commit()
    return jsonify(one(f"SELECT * FROM {table} WHERE id=?", (cur.lastrowid,))), 201


@app.get("/subscriptions/")
@require_auth
def subscriptions():
    data = list_subscriptions()
    if user_role(g.user) != "owner":
        data = [s for s in data if s.get("customer_name") == g.user["username"]]
    return jsonify(data)


@app.get("/subscriptions/<int:subscription_id>/")
@require_auth
def subscription_detail(subscription_id):
    item = next(
        (s for s in list_subscriptions() if s["id"] == subscription_id),
        None,
    )
    if not item:
        return jsonify({"error": "Subscription not found."}), 404
    if user_role(g.user) != "owner" and item.get("customer_name") != g.user["username"]:
        return jsonify({"detail": "Forbidden."}), 403
    return jsonify(item)


@app.get("/licenses/")
@require_auth
def licenses():
    data = list_licenses()
    if user_role(g.user) != "owner":
        data = [l for l in data if l.get("customer_name") == g.user["username"]]
    return jsonify(data)


@app.get("/licenses/<path:license_key>/")
@require_auth
def license_detail(license_key):
    item = next(
        (l for l in list_licenses() if l["license_key"] == license_key),
        None,
    )
    if not item:
        return jsonify({"error": "License not found."}), 404
    return jsonify(item)


@app.post("/verify-license/")
def verify_license():
    data = request.get_json(silent=True) or {}
    key = str(data.get("license_key") or "").strip()
    if not key:
        return jsonify({"valid": False, "reason": "MISSING_LICENSE_KEY"}), 400

    if legacy_mode():
        license_row = one(
            """SELECT l.*, s.status AS subscription_status
               FROM core_license l
               LEFT JOIN core_subscription s ON s.id=l.subscription_id
               WHERE l.license_key=?""",
            (key,),
        )
        table = "core_license"
    else:
        license_row = one(
            """SELECT l.*, s.status AS subscription_status
               FROM licenses l
               LEFT JOIN subscriptions s ON s.id=l.subscription_id
               WHERE l.license_key=?""",
            (key,),
        )
        table = "licenses"

    if not license_row:
        return jsonify({"valid": False, "reason": "LICENSE_NOT_FOUND"}), 403

    active = (
        license_row.get("status") == "ACTIVE"
        and license_row.get("subscription_status") == "ACTIVE"
    )
    try:
        expiry = datetime.fromisoformat(
            str(license_row["expiry_date"]).replace("Z", "+00:00")
        )
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        active = active and expiry > datetime.now(timezone.utc)
    except Exception:
        pass

    db().execute(
        f"""UPDATE {table}
            SET last_verified=?, verification_count=verification_count+1
            WHERE id=?""",
        (now_iso(), license_row["id"]),
    )
    db().commit()
    return jsonify({
        "valid": bool(active),
        "reason": "VALID" if active else "INACTIVE_OR_EXPIRED",
        "license_key": key,
        "expiry_date": license_row.get("expiry_date"),
    }), (200 if active else 403)


@app.get("/transactions/")
@require_auth
def transactions():
    data = list_transactions()
    if user_role(g.user) != "owner":
        data = [t for t in data if t.get("customer_name") == g.user["username"]]
    return jsonify(data)


@app.get("/invoices/")
@require_auth
def invoices():
    data = list_invoices()
    if user_role(g.user) != "owner":
        data = [i for i in data if i.get("customer_name") == g.user["username"]]
    return jsonify(data)


@app.get("/dashboard/")
@require_auth
def dashboard():
    if user_role(g.user) == "owner":
        return jsonify({
            "role": "owner",
            "customers": len(customers_data()),
            "plans": len(list_plans()),
            "subscriptions": len(list_subscriptions()),
            "licenses": len(list_licenses()),
            "transactions": len(list_transactions()),
            "invoices": len(list_invoices()),
        })

    username = g.user["username"]
    subs = [s for s in list_subscriptions() if s.get("customer_name") == username]
    licenses_for_user = [
        l for l in list_licenses() if l.get("customer_name") == username
    ]
    txns = [t for t in list_transactions() if t.get("customer_name") == username]
    return jsonify({
        "role": "customer",
        "subscriptions": len(subs),
        "licenses": len(licenses_for_user),
        "transactions": len(txns),
    })


@app.errorhandler(404)
def not_found(_error):
    return jsonify({"error": "Endpoint not found."}), 404


@app.errorhandler(500)
def server_error(_error):
    return jsonify({"error": "Internal server error."}), 500


if __name__ == "__main__":
    if not os.path.exists(DATABASE):
        ensure_schema()
    print(f"LicenseFlow Python API using database: {DATABASE}")
    app.run(
        host="127.0.0.1",
        port=int(os.environ.get("PORT", "8000")),
        debug=True,
    )
