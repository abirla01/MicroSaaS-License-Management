from django.urls import path

from . import views


urlpatterns = [

    # Health
    path(
        "health/",
        views.health_check,
        name="health-check"
    ),

    # Authentication
    path(
        "auth/register/",
        views.register_view,
        name="auth-register"
    ),
    path(
        "auth/login/",
        views.login_view,
        name="auth-login"
    ),
    path(
        "auth/refresh/",
        views.refresh_view,
        name="auth-refresh"
    ),
    path(
        "auth/me/",
        views.me_view,
        name="auth-me"
    ),

    # Customers
    path(
        "customers/",
        views.customers,
        name="customers"
    ),

    path(
        "customers/<int:customer_id>/",
        views.customer_detail,
        name="customer-detail"
    ),

    # Plans
    path(
        "plans/",
        views.plans,
        name="plans"
    ),

    # Subscriptions
    path(
        "subscriptions/",
        views.subscriptions,
        name="subscriptions"
    ),

    path(
        "subscriptions/<int:subscription_id>/",
        views.subscription_detail,
        name="subscription-detail"
    ),

    # Licenses
    path(
        "licenses/",
        views.licenses,
        name="licenses"
    ),

    path(
        "licenses/<str:license_key>/",
        views.license_detail,
        name="license-detail"
    ),

    # License verification
    path(
        "verify-license/",
        views.verify_license,
        name="verify-license"
    ),

    # Transactions
    path(
        "transactions/",
        views.transactions,
        name="transactions"
    ),

    # Invoices
    path(
        "invoices/",
        views.invoices,
        name="invoices"
    ),

    # Dashboard
    path(
        "dashboard/",
        views.dashboard_summary,
        name="dashboard"
    ),
]