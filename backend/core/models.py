from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
import secrets


def generate_transaction_id():
    return f"TXN-{uuid.uuid4().hex[:12].upper()}"


# =========================================================
# CUSTOMER PROFILE
# =========================================================

class CustomerProfile(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="customer_profile"
    )

    phone = models.CharField(
        max_length=20,
        blank=True
    )

    company = models.CharField(
        max_length=150,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.user.get_full_name() or self.user.username


# =========================================================
# SUBSCRIPTION PLANS
# =========================================================

class SubscriptionPlan(models.Model):

    BILLING_CHOICES = [
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
    ]

    name = models.CharField(
        max_length=100
    )

    description = models.TextField(
        blank=True
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    billing_cycle = models.CharField(
        max_length=20,
        choices=BILLING_CHOICES,
        default="monthly"
    )

    max_users = models.PositiveIntegerField(
        default=1
    )

    max_devices = models.PositiveIntegerField(
        default=1
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.name


# =========================================================
# SUBSCRIPTIONS
# =========================================================

class Subscription(models.Model):

    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("EXPIRED", "Expired"),
        ("CANCELLED", "Cancelled"),
        ("SUSPENDED", "Suspended"),
    ]

    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.CASCADE,
        related_name="subscriptions"
    )

    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name="subscriptions"
    )

    start_date = models.DateTimeField(
        default=timezone.now
    )

    expiry_date = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ACTIVE"
    )

    razorpay_subscription_id = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )

    auto_renew = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"{self.customer} - "
            f"{self.plan.name}"
        )


# =========================================================
# LICENSE
# =========================================================

class License(models.Model):

    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("EXPIRED", "Expired"),
        ("REVOKED", "Revoked"),
        ("SUSPENDED", "Suspended"),
    ]

    subscription = models.OneToOneField(
        Subscription,
        on_delete=models.CASCADE,
        related_name="license"
    )

    license_key = models.CharField(
        max_length=29,
        unique=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="ACTIVE"
    )

    activation_date = models.DateTimeField(
        default=timezone.now
    )

    expiry_date = models.DateTimeField()

    last_verified = models.DateTimeField(
        null=True,
        blank=True
    )

    verification_count = models.PositiveIntegerField(
        default=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.license_key


# =========================================================
# TRANSACTION
# =========================================================

class Transaction(models.Model):

    STATUS_CHOICES = [
        ("PAID", "Paid"),
        ("PENDING", "Pending"),
        ("FAILED", "Failed"),
        ("REFUNDED", "Refunded"),
    ]

    PAYMENT_CHOICES = [
        ("RAZORPAY", "Razorpay"),
        ("CASH", "Cash"),
        ("OTHER", "Other"),
    ]

    transaction_id = models.CharField(
    max_length=50,
    unique=True,
    default=generate_transaction_id
    )   

    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.PROTECT,
        related_name="transactions"
    )

    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    payment_method = models.CharField(
        max_length=30,
        choices=PAYMENT_CHOICES,
        default="RAZORPAY"
    )

    razorpay_payment_id = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PENDING"
    )

    transaction_date = models.DateTimeField(
        default=timezone.now
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.transaction_id


# =========================================================
# INVOICE
# =========================================================

class Invoice(models.Model):

    STATUS_CHOICES = [
        ("PAID", "Paid"),
        ("PENDING", "Pending"),
        ("REFUNDED", "Refunded"),
    ]

    invoice_id = models.CharField(
        max_length=50,
        unique=True
    )

    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.PROTECT,
        related_name="invoices"
    )

    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.PROTECT,
        related_name="invoice"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="PAID"
    )

    invoice_date = models.DateTimeField(
        default=timezone.now
    )

    pdf_generated = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.invoice_id