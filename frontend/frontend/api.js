/* =========================================================
   LICENSEFLOW — BACKEND API CONNECTION
   ========================================================= */

const API_BASE_URL = "http://127.0.0.1:8000";


/* =========================================================
   TOKEN MANAGEMENT
   ========================================================= */

function getAccessToken() {
    return localStorage.getItem("licenseflow_access_token");
}

function getRefreshToken() {
    return localStorage.getItem("licenseflow_refresh_token");
}

function setTokens(access, refresh) {
    if (access) localStorage.setItem("licenseflow_access_token", access);
    if (refresh) localStorage.setItem("licenseflow_refresh_token", refresh);
}

function clearTokens() {
    localStorage.removeItem("licenseflow_access_token");
    localStorage.removeItem("licenseflow_refresh_token");
    localStorage.removeItem("licenseflow_user");
    localStorage.removeItem("licenseflow_role");
    localStorage.removeItem("licenseflow_logged_in");
}


async function apiRequest(endpoint, options = {}) {

    const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {})
    };

    // Attach Bearer token if available and not skipped
    const token = getAccessToken();
    if (token && !options.skipAuth && !headers["Authorization"]) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    let response;
    try {
        response = await fetch(
            API_BASE_URL + endpoint,
            {
                ...options,
                headers
            }
        );
    } catch (networkErr) {
        throw new Error("Unable to connect to backend server: " + networkErr.message);
    }

    // Auto-refresh token on 401 if refresh token is available and not already retrying
    if (response.status === 401 && !options._isRetry && !endpoint.includes("/auth/")) {
        const refreshToken = getRefreshToken();
        if (refreshToken) {
            try {
                const refreshRes = await fetch(API_BASE_URL + "/auth/refresh/", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ refresh: refreshToken })
                });

                if (refreshRes.ok) {
                    const refreshData = await refreshRes.json();
                    if (refreshData.access) {
                        setTokens(refreshData.access, refreshData.refresh || refreshToken);
                        return await apiRequest(endpoint, { ...options, _isRetry: true });
                    }
                }
            } catch (refErr) {
                console.error("Token refresh failed:", refErr);
            }
        }
        // If refresh failed or not possible, clear session
        clearTokens();
    }

    let data;
    try {
        data = await response.json();
    } catch (parseErr) {
        data = { error: "Failed to parse response from server" };
    }

    if (!response.ok) {
        const errorMsg =
            data.message ||
            data.error ||
            data.detail ||
            (typeof data === "string" ? data : "Backend request failed");
        const err = new Error(errorMsg);
        err.status = response.status;
        err.data = data;
        throw err;
    }

    return data;
}


/* =========================================================
   AUTH API
   ========================================================= */

async function loginUser(usernameOrEmail, password) {
    const data = await apiRequest("/auth/login/", {
        method: "POST",
        skipAuth: true,
        body: JSON.stringify({
            username: usernameOrEmail,
            password: password
        })
    });

    if (data.access) {
        setTokens(data.access, data.refresh);
        localStorage.setItem("licenseflow_role", data.user.role);
        localStorage.setItem("licenseflow_logged_in", "true");
        localStorage.setItem("licenseflow_user", JSON.stringify(data.user));
    }

    return data;
}

async function getMe() {
    return await apiRequest("/auth/me/");
}


/* =========================================================
   HEALTH CHECK
   ========================================================= */

async function checkBackend() {

    try {

        const data =
            await apiRequest("/health/");

        console.log(
            "LicenseFlow Backend:",
            data.message
        );

        return true;

    } catch (error) {

        console.error(
            "Backend connection failed:",
            error
        );

        return false;
    }
}


/* =========================================================
   DASHBOARD
   ========================================================= */

async function getDashboardSummary() {

    return await apiRequest(
        "/dashboard/"
    );
}


/* =========================================================
   CUSTOMERS
   ========================================================= */

async function getCustomers() {

    return await apiRequest(
        "/customers/"
    );
}


/* =========================================================
   PLANS
   ========================================================= */

async function getPlans() {

    return await apiRequest(
        "/plans/"
    );
}


/* =========================================================
   SUBSCRIPTIONS
   ========================================================= */

async function getSubscriptions() {

    return await apiRequest(
        "/subscriptions/"
    );
}


/* =========================================================
   LICENSES
   ========================================================= */

async function getLicenses() {

    return await apiRequest(
        "/licenses/"
    );
}


async function verifyLicense(licenseKey) {

    return await apiRequest(
        "/verify-license/",
        {
            method: "POST",

            body: JSON.stringify({
                license_key: licenseKey
            })
        }
    );
}


/* =========================================================
   TRANSACTIONS
   ========================================================= */

async function getTransactions() {

    return await apiRequest(
        "/transactions/"
    );
}


/* =========================================================
   INVOICES
   ========================================================= */

async function getInvoices() {

    return await apiRequest(
        "/invoices/"
    );
}


/* =========================================================
   MAKE API FUNCTIONS AVAILABLE
   ========================================================= */

window.apiRequest =
    apiRequest;

window.checkBackend =
    checkBackend;

window.getDashboardSummary =
    getDashboardSummary;

window.getCustomers =
    getCustomers;

window.getPlans =
    getPlans;

window.getSubscriptions =
    getSubscriptions;

window.getLicenses =
    getLicenses;

window.verifyLicense =
    verifyLicense;

window.getTransactions =
    getTransactions;

window.getInvoices =
    getInvoices;

window.getAccessToken =
    getAccessToken;

window.getRefreshToken =
    getRefreshToken;

window.setTokens =
    setTokens;

window.clearTokens =
    clearTokens;

window.loginUser =
    loginUser;

window.getMe =
    getMe;