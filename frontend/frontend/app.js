/* =========================================================
   LICENSEFLOW — FRONTEND ENGINE
   ========================================================= */


/* =========================================================
   DEFAULT STATE
   ========================================================= */

const DEFAULT_STATE = {

    customer: {
        name: "Aditya Birla",
        email: "aditya@example.com"
    },

    subscription: {
        plan: "Medium",
        price: 999,
        status: "ACTIVE",
        billing: "Monthly",
        expiry: "12 Oct 2026"
    },

    license: {
        key: "MSLM-8K4P-X92Q-7T3A-5L9D",
        status: "ACTIVE",
        plan: "Medium",
        expiry: "12 Oct 2026"
    },

    usage: {
        projects: 12,
        tasks: 184,
        devices: 2,
        team: 4
    },

    revenue: 2480000,

    transactions: [
        {
            amount: 999,
            plan: "Medium",
            status: "PAID",
            date: "12 Sep 2026"
        },

        {
            amount: 999,
            plan: "Medium",
            status: "PAID",
            date: "12 Aug 2026"
        },

        {
            amount: 999,
            plan: "Medium",
            status: "PAID",
            date: "12 Jul 2026"
        }
    ]
};


/* =========================================================
   STATE
   ========================================================= */

function getState() {

    const saved =
        localStorage.getItem("licenseflow_state");

    if (!saved) {

        localStorage.setItem(
            "licenseflow_state",
            JSON.stringify(DEFAULT_STATE)
        );

        return JSON.parse(
            JSON.stringify(DEFAULT_STATE)
        );
    }

    try {

        return JSON.parse(saved);

    } catch (error) {

        console.error(
            "LicenseFlow state error:",
            error
        );

        localStorage.setItem(
            "licenseflow_state",
            JSON.stringify(DEFAULT_STATE)
        );

        return JSON.parse(
            JSON.stringify(DEFAULT_STATE)
        );
    }
}


function saveState(state) {

    localStorage.setItem(
        "licenseflow_state",
        JSON.stringify(state)
    );

}


let LF = getState();

window.getState = getState;
window.saveState = saveState;


/* =========================================================
   LOGIN MODAL
   ========================================================= */
let selectedLoginRole = "customer";

function showLoginForm(role) {
    selectedLoginRole = role;

    document.getElementById("portalSelection").style.display = "none";
    document.getElementById("credentialForm").style.display = "block";

    document.getElementById("selectedPortal").textContent =
        role === "owner"
            ? "Sign in to Owner / Admin Portal"
            : "Sign in to Customer Portal";

    document.getElementById("loginError").style.display = "none";
}

function backToPortalSelection() {
    document.getElementById("credentialForm").style.display = "none";
    document.getElementById("portalSelection").style.display = "block";
}

function openLogin() {

    const modal =
        document.getElementById("loginModal");

    if (!modal) {
        return;
    }

    modal.classList.add("active");

    modal.style.display = "flex";
}


function closeLogin() {

    const modal =
        document.getElementById("loginModal");

    if (!modal) {
        return;
    }

    modal.classList.remove("active");

    modal.style.display = "";
}


/* =========================================================
   LOGIN
   ========================================================= */

/**
 * loginAs(usernameOrEmail, password)
 *
 * Dispatches a real authentication request to POST /api/auth/login/
 * via loginUser() in api.js.  No credentials are hardcoded here.
 *
 * Called by the login form in index.html with the values the user typed.
 * Redirects to admin.html for staff/owner accounts or customer.html otherwise.
 */
async function loginAs(usernameOrEmail, password, selectedRole = selectedLoginRole) {

    if (!usernameOrEmail || !password) {
        _showLoginError("Please enter your username/email and password.");
        return;
    }

    _setLoginLoading(true);

    try {

        // loginUser() is defined in api.js — performs POST /api/auth/login/
        // and stores the returned JWT tokens in localStorage.
        const data = await loginUser(usernameOrEmail, password);

        const role = data.user && data.user.role;

if (!role) {
    throw new Error("Your account role was not returned by the server.");
}

if (role !== selectedRole) {
    clearTokens();

    throw new Error(
        "Your account does not have access to the selected portal."
    );
}

if (role === "owner") {
    window.location.href = "admin (4).html";
}else if (role === "customer") {
    window.location.href = "customer.html";
} else {
    clearTokens();
    throw new Error("Unknown account role: " + role);
}

    } catch (err) {
        console.error("Login failed:", err);
        _showLoginError(
            err.message ||
            "Invalid credentials. Please check your username and password."
        );
    } finally {
        _setLoginLoading(false);
    }
}


/* Make functions available to HTML onclick */
window.openLogin  = openLogin;
window.closeLogin = closeLogin;
window.loginAs    = loginAs;

/* =========================================================
   LOGIN FORM SUBMISSION
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    const loginForm = document.getElementById("loginForm");

    if (!loginForm) {
        return;
    }

    loginForm.addEventListener("submit", async function (event) {

        event.preventDefault();

        const username = document
            .getElementById("loginUsername")
            .value
            .trim();

        const password = document
            .getElementById("loginPassword")
            .value;

        await loginAs(username, password, selectedLoginRole);

    });

});


/* =========================================================
   LOGOUT
   ========================================================= */

function logoutLicenseFlow() {

    if (typeof clearTokens === "function") {
        clearTokens();
    } else {
        localStorage.removeItem("licenseflow_access_token");
        localStorage.removeItem("licenseflow_refresh_token");
        localStorage.removeItem("licenseflow_user");
        localStorage.removeItem("licenseflow_logged_in");
        localStorage.removeItem("licenseflow_role");
    }

    window.location.href =
        "index.html";
}


window.logoutLicenseFlow =
    logoutLicenseFlow;


/* =========================================================
   LOGIN UI HELPERS
   ========================================================= */

/**
 * Display an error message inside the login modal.
 * Falls back to console.error if the element is not found.
 */
function _showLoginError(message) {

    const errEl = document.getElementById("loginError");

    if (errEl) {
        errEl.textContent = message;
        errEl.style.display = "block";
    } else {
        console.error("Login error:", message);
    }
}


/**
 * Toggle the submit button's disabled state and label
 * while an auth request is in flight.
 */
function _setLoginLoading(isLoading) {

    const btn = document.getElementById("loginSubmitBtn");

    if (!btn) return;

    btn.disabled    = isLoading;
    btn.textContent = isLoading ? "Signing in…" : "Sign In";
}


/* =========================================================
   AUTH GUARD
   ========================================================= */

/**
 * _isTokenExpired(token)
 *
 * Decodes the JWT payload (base-64 middle segment) and returns true
 * if the `exp` claim is in the past.  Returns true on any parse error
 * so we always attempt a refresh rather than silently accepting a bad token.
 */
function _isTokenExpired(token) {

    try {
        const payload = JSON.parse(
            atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/"))
        );
        // exp is in seconds; Date.now() is ms
        return payload.exp * 1000 < Date.now();
    } catch (_) {
        return true;
    }
}


/**
 * requireLogin(requiredRole)
 *
 * Synchronous auth guard used at the top of protected pages.
 *
 * 1. Checks licenseflow_logged_in and licenseflow_access_token.
 * 2. If the access token is expired, kicks off a silent background refresh
 *    via the refresh token (POST /api/auth/refresh/).  The page continues
 *    to load — the next API call will use the freshly stored token.
 *    If the refresh itself fails the user is redirected to index.html.
 * 3. Validates the stored role against requiredRole.
 *
 * Returns true when the caller may proceed, false when a redirect was issued.
 */
function requireLogin(requiredRole) {

    const loggedIn = localStorage.getItem("licenseflow_logged_in");
    const role     = localStorage.getItem("licenseflow_role");
    const token    = localStorage.getItem("licenseflow_access_token");

    // Hard fail — no session at all
    if (loggedIn !== "true" || !token) {
        window.location.href = "index.html";
        return false;
    }

    // Soft fail — token exists but may be expired; try a silent refresh
    if (_isTokenExpired(token)) {

        const refreshToken = localStorage.getItem("licenseflow_refresh_token");

        if (refreshToken) {

            // Fire-and-forget: kick off a silent refresh in the background.
            // If it fails, the next authenticated API call will 401 and
            // api.js will redirect to index.html via its own 401 handler.
            (async () => {
                try {
                    const res = await fetch(
                        "http://127.0.0.1:8000/api/auth/refresh/",
                        {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ refresh: refreshToken })
                        }
                    );

                    if (res.ok) {
                        const data = await res.json();
                        if (data.access) {
                            // setTokens() is defined in api.js
                            if (typeof setTokens === "function") {
                                setTokens(data.access, data.refresh || refreshToken);
                            } else {
                                localStorage.setItem("licenseflow_access_token", data.access);
                            }
                        } else {
                            // Refresh succeeded but returned no token — force re-login
                            if (typeof clearTokens === "function") clearTokens();
                            window.location.href = "index.html";
                        }
                    } else {
                        // Refresh failed (e.g. token revoked) — force re-login
                        if (typeof clearTokens === "function") clearTokens();
                        window.location.href = "index.html";
                    }
                } catch (_) {
                    // Network failure during refresh — let the page load;
                    // next API call will surface the error to the user.
                }
            })();

        } else {
            // No refresh token — session is unrecoverable
            if (typeof clearTokens === "function") clearTokens();
            window.location.href = "index.html";
            return false;
        }
    }

    // Role check
    if (requiredRole && role !== requiredRole) {

        if (role === "owner") {
    window.location.href = "admin (4).html";
} else if (role === "customer") {
    window.location.href = "customer.html";
} else {
    clearTokens();
    throw new Error("Unknown account role: " + role);
}

        return false;
    }

    return true;
}


window.requireLogin = requireLogin;


/* =========================================================
   LICENSE GENERATOR
   ========================================================= */

function generateLicense() {

    const chars =
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";


    function segment(length) {

        let result = "";

        for (
            let i = 0;
            i < length;
            i++
        ) {

            result +=
                chars.charAt(
                    Math.floor(
                        Math.random() *
                        chars.length
                    )
                );
        }

        return result;
    }


    return (
        "MSLM-" +
        segment(4) +
        "-" +
        segment(4) +
        "-" +
        segment(4) +
        "-" +
        segment(4) +
        "-" +
        segment(4)
    );
}


window.generateLicense =
    generateLicense;


/* =========================================================
   DATE
   ========================================================= */

function getFutureDate(days) {

    const date =
        new Date();

    date.setDate(
        date.getDate() + days
    );


    return date.toLocaleDateString(
        "en-IN",
        {
            day: "2-digit",
            month: "short",
            year: "numeric"
        }
    );
}


/* =========================================================
   PURCHASE PLAN
   ========================================================= */

function purchasePlan(plan, price) {

    LF.subscription = {

        plan: plan,

        price: price,

        status: "ACTIVE",

        billing: "Monthly",

        expiry:
            getFutureDate(30)

    };


    LF.license = {

        key:
            generateLicense(),

        status:
            "ACTIVE",

        plan:
            plan,

        expiry:
            LF.subscription.expiry
    };


    if (!Array.isArray(LF.transactions)) {

        LF.transactions = [];
    }


    LF.transactions.unshift({

        amount: price,

        plan: plan,

        status: "PAID",

        date:
            new Date().toLocaleDateString(
                "en-IN",
                {
                    day: "2-digit",
                    month: "short",
                    year: "numeric"
                }
            )
    });


    saveState(LF);


    alert(
        "Payment successful!\n\n" +
        "Plan: " +
        plan +
        "\nAmount: ₹" +
        price +
        "\n\n" +
        "Your software license has been generated."
    );


    window.location.href =
        "customer.html";
}


window.purchasePlan =
    purchasePlan;


/* =========================================================
   PLAN SELECTION
   ========================================================= */

function selectPlan(plan, price) {

    localStorage.setItem(
        "selected_plan",
        plan
    );

    localStorage.setItem(
        "selected_price",
        String(price)
    );


    /*
       If checkout.html exists,
       open the checkout page.
    */

    window.location.href =
        "checkout.html";
}


window.selectPlan =
    selectPlan;


/* =========================================================
   TASKFLOW ACCESS
   ========================================================= */

function openTaskFlow() {

    const state =
        getState();


    if (
        !state.license ||
        state.license.status !== "ACTIVE"
    ) {

        alert(
            "Access denied.\n\n" +
            "Your LicenseFlow subscription is not active."
        );

        return;
    }


    window.location.href =
        "taskflow.html";
}


window.openTaskFlow =
    openTaskFlow;


/* =========================================================
   TASKFLOW LICENSE VALIDATION
   ========================================================= */

function validateTaskFlowLicense() {

    const state =
        getState();


    const valid =
        state.license &&
        state.license.status === "ACTIVE";


    const status =
        document.querySelector(
            ".license-status-left strong"
        );


    const details =
        document.querySelector(
            ".license-status-left span"
        );


    const dot =
        document.querySelector(
            ".license-dot"
        );


    if (!status) {
        return;
    }


    if (valid) {

        status.innerText =
            "License verified";


        if (details) {

            details.innerText =
                state.subscription.plan +
                " Plan · Expires " +
                state.license.expiry;
        }


        if (dot) {

            dot.style.background =
                "#25d695";

            dot.style.boxShadow =
                "0 0 10px #25d695";
        }

    } else {

        status.innerText =
            "License invalid";


        if (details) {

            details.innerText =
                "Your software access has been restricted.";
        }


        if (dot) {

            dot.style.background =
                "#ff596d";

            dot.style.boxShadow =
                "0 0 10px #ff596d";
        }
    }
}


/* =========================================================
   CUSTOMER DASHBOARD
   ========================================================= */

function loadCustomerDashboard() {

    const state =
        getState();


    /*
       Subscription heading
    */

    const headings =
        document.querySelectorAll(
            ".subscription-banner h2"
        );


    headings.forEach(function(el) {

        if (
            state.subscription &&
            state.subscription.plan
        ) {

            el.innerHTML =
                state.subscription.plan +
                ' <span class="active-badge">● ACTIVE</span>';
        }

    });


    /*
       License key
    */

    const license =
        document.getElementById(
            "licenseKey"
        );


    if (
        license &&
        state.license
    ) {

        license.innerText =
            state.license.key;
    }


    /*
       License status
    */

    const licenseStatus =
        document.querySelector(
            ".license-meta div:nth-child(2) strong"
        );


    if (
        licenseStatus &&
        state.license
    ) {

        licenseStatus.innerText =
            state.license.status;
    }


    /*
       License expiry
    */

    const licenseExpiry =
        document.querySelector(
            ".license-meta div:nth-child(3) strong"
        );


    if (
        licenseExpiry &&
        state.license
    ) {

        licenseExpiry.innerText =
            state.license.expiry;
    }
}


/* =========================================================
   OWNER DASHBOARD
   ========================================================= */

function loadOwnerDashboard() {

    const owner =
        document.querySelector(
            ".owner-main"
        );


    if (!owner) {
        return;
    }


    const state =
        getState();


    const statValues =
        document.querySelectorAll(
            ".owner-stat h2"
        );


    if (
        statValues.length >= 4
    ) {

        /*
           Keep demo business numbers
           while reflecting active customer.
        */

        statValues[1].innerText =
            state.subscription &&
            state.subscription.status === "ACTIVE"
                ? "428"
                : "427";


        statValues[2].innerText =
            state.license &&
            state.license.status === "ACTIVE"
                ? "417"
                : "416";
    }
}


/* =========================================================
   RESET DEMO
   ========================================================= */

function resetLicenseFlow() {

    localStorage.removeItem(
        "licenseflow_state"
    );

    localStorage.removeItem(
        "licenseflow_logged_in"
    );

    localStorage.removeItem(
        "licenseflow_role"
    );

    localStorage.removeItem(
        "selected_plan"
    );

    localStorage.removeItem(
        "selected_price"
    );


    window.location.href =
        "index.html";
}


window.resetLicenseFlow =
    resetLicenseFlow;


/* =========================================================
   SCROLL TO PLANS
   ========================================================= */

function scrollToPlans() {

    const plans =
        document.getElementById(
            "pricing"
        );


    if (plans) {

        plans.scrollIntoView({
            behavior: "smooth"
        });
    }
}


window.scrollToPlans =
    scrollToPlans;


/* =========================================================
   CLOSE LOGIN MODAL ON BACKDROP CLICK
   ========================================================= */

document.addEventListener(
    "click",
    function(event) {

        const modal =
            document.getElementById(
                "loginModal"
            );


        if (
            modal &&
            event.target === modal
        ) {

            closeLogin();
        }
    }
);


/* =========================================================
   INITIALIZE
   ========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    function() {

        loadCustomerDashboard();

        validateTaskFlowLicense();

        loadOwnerDashboard();

    }
);