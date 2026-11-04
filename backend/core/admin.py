from django.contrib import admin

from .models import (
    CustomerProfile,
    SubscriptionPlan,
    Subscription,
    License,
    Transaction,
    Invoice,
)


# --------------------------------------------------
# CUSTOMER
# --------------------------------------------------

@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "phone",
        "company",
        "created_at",
    )

    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
        "company",
    )

    list_filter = (
        "created_at",
    )


# --------------------------------------------------
# SUBSCRIPTION PLANS
# --------------------------------------------------

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "price",
        "billing_cycle",
        "max_users",
        "max_devices",
        "is_active",
        "created_at",
    )

    search_fields = (
        "name",
        "description",
    )

    list_filter = (
        "billing_cycle",
        "is_active",
    )


# --------------------------------------------------
# SUBSCRIPTIONS
# --------------------------------------------------

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):

    list_display = (
        "customer",
        "plan",
        "start_date",
        "expiry_date",
        "status",
        "auto_renew",
        "created_at",
    )

    search_fields = (
        "customer__user__username",
        "customer__user__email",
        "plan__name",
        "razorpay_subscription_id",
    )

    list_filter = (
        "status",
        "auto_renew",
        "plan",
    )


# --------------------------------------------------
# LICENSES
# --------------------------------------------------

@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):

    list_display = (
        "license_key",
        "subscription",
        "status",
        "activation_date",
        "expiry_date",
        "last_verified",
        "verification_count",
        "created_at",
    )

    search_fields = (
        "license_key",
        "subscription__customer__user__username",
        "subscription__customer__user__email",
    )

    list_filter = (
        "status",
        "created_at",
    )

    readonly_fields = (
        "last_verified",
        "verification_count",
        "created_at",
    )


# --------------------------------------------------
# TRANSACTIONS
# --------------------------------------------------

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):

    list_display = (
        "transaction_id",
        "customer",
        "amount",
        "payment_method",
        "status",
        "transaction_date",
        "created_at",
    )

    search_fields = (
        "transaction_id",
        "customer__user__username",
        "customer__user__email",
        "razorpay_payment_id",
    )

    list_filter = (
        "status",
        "payment_method",
        "transaction_date",
    )


# --------------------------------------------------
# INVOICES
# --------------------------------------------------

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):

    list_display = (
        "invoice_id",
        "customer",
        "transaction",
        "amount",
        "status",
        "invoice_date",
        "pdf_generated",
        "created_at",
    )

    search_fields = (
        "invoice_id",
        "customer__user__username",
        "customer__user__email",
        "transaction__transaction_id",
    )

    list_filter = (
        "status",
        "pdf_generated",
        "invoice_date",
    )