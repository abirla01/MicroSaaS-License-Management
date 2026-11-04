from rest_framework import serializers

from django.contrib.auth.models import User

from .models import (
    CustomerProfile,
    SubscriptionPlan,
    Subscription,
    License,
    Transaction,
    Invoice,
)


# =========================================================
# USER
# =========================================================

class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User

        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
        ]


# =========================================================
# CUSTOMER
# =========================================================

class CustomerProfileSerializer(serializers.ModelSerializer):

    user = UserSerializer(read_only=True)

    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()

    class Meta:
        model = CustomerProfile

        fields = [
            "id",
            "name",
            "email",
            "phone",
            "company",
            "created_at",
            "user",
        ]

    def get_name(self, obj):

        return (
            obj.user.get_full_name()
            or obj.user.username
        )

    def get_email(self, obj):

        return obj.user.email


# =========================================================
# PLAN
# =========================================================

class SubscriptionPlanSerializer(serializers.ModelSerializer):

    class Meta:
        model = SubscriptionPlan

        fields = [
            "id",
            "name",
            "description",
            "price",
            "billing_cycle",
            "max_users",
            "max_devices",
            "is_active",
            "created_at",
        ]


# =========================================================
# SUBSCRIPTION
# =========================================================

class SubscriptionSerializer(serializers.ModelSerializer):

    customer_name = serializers.SerializerMethodField()
    plan_name = serializers.CharField(
        source="plan.name",
        read_only=True
    )

    class Meta:
        model = Subscription

        fields = [
            "id",
            "customer",
            "customer_name",
            "plan",
            "plan_name",
            "start_date",
            "expiry_date",
            "status",
            "razorpay_subscription_id",
            "auto_renew",
            "created_at",
        ]

    def get_customer_name(self, obj):

        return (
            obj.customer.user.get_full_name()
            or obj.customer.user.username
        )


# =========================================================
# LICENSE
# =========================================================

class LicenseSerializer(serializers.ModelSerializer):

    customer_name = serializers.SerializerMethodField()
    plan_name = serializers.CharField(
        source="subscription.plan.name",
        read_only=True
    )

    class Meta:
        model = License

        fields = [
            "id",
            "license_key",
            "customer_name",
            "plan_name",
            "subscription",
            "status",
            "activation_date",
            "expiry_date",
            "last_verified",
            "verification_count",
            "created_at",
        ]

    def get_customer_name(self, obj):

        return (
            obj.subscription.customer.user.get_full_name()
            or obj.subscription.customer.user.username
        )


# =========================================================
# TRANSACTION
# =========================================================

class TransactionSerializer(serializers.ModelSerializer):

    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = Transaction

        fields = [
            "id",
            "transaction_id",
            "customer",
            "customer_name",
            "subscription",
            "amount",
            "payment_method",
            "razorpay_payment_id",
            "status",
            "transaction_date",
            "created_at",
        ]

    def get_customer_name(self, obj):

        return (
            obj.customer.user.get_full_name()
            or obj.customer.user.username
        )


# =========================================================
# INVOICE
# =========================================================

class InvoiceSerializer(serializers.ModelSerializer):

    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = Invoice

        fields = [
            "id",
            "invoice_id",
            "customer",
            "customer_name",
            "transaction",
            "amount",
            "status",
            "invoice_date",
            "pdf_generated",
            "created_at",
        ]

    def get_customer_name(self, obj):

        return (
            obj.customer.user.get_full_name()
            or obj.customer.user.username
        )


# =========================================================
# LICENSE VERIFICATION
# =========================================================

class LicenseVerificationSerializer(serializers.Serializer):

    license_key = serializers.CharField(
        max_length=29
    )