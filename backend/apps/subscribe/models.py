from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

class SubscriptionPlan(models.Model):
    """Model for subscription_plans."""

    name = models.CharField(max_length=100, unique=True)#subscription name
    price = models.DecimalField(max_digits=10, decimal_places=2)#price
    duration_days = models.PositiveIntegerField(default=30)  # duration in days, 30 days default
    stripe_price_id = models.CharField(max_length=255, unique=True)#stripe price id
    features = models.JSONField(default=dict, help_text="Features included in the plan")#features included in the plan
    is_active = models.BooleanField(default=True)#is active plan
    created_at = models.DateTimeField(auto_now_add=True)#created at
    updated_at = models.DateTimeField(auto_now=True)#updated at

    class Meta:
        db_table = "subscription_plans"
        verbose_name = "Subscription Plan"
        verbose_name_plural = "Subscription Plans"
        ordering = ["price"]

    def __str__(self):
        return f"{self.name} - {self.price}"
    

class Subscription(models.Model):
    """Model for user subscriptions."""

    STATUS_ACTIVE = "active"

    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        ("cancelled", "Cancelled"),
        ("expired", "Expired"),
        ("pending", "Pending")
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscription"
    )

    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.CASCADE,
        related_name="subscriptions"
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    auto_renew = models.BooleanField(default=True)
    stripe_payment_id = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        db_table = "subscriptions"
        verbose_name = "Subscription"
        verbose_name_plural = "Subscriptions"
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.user.username} - {self.plan.name} {self.status}"
    

    @property
    def is_active(self):
        """Check if the subscription is currently active."""
        now = timezone.now()
        return self.status == "active" and self.start_date <= now <= self.end_date
    
    @property
    def days_remaining(self):
        """Calculate the number of days remaining in the subscription."""
        if self.is_active:
            delta = self.end_date - timezone.now()
            return delta.days
        return 0
    
    def extend_subscription(self, days=30):
        """extend the subscription by given days."""
        if self.is_active:
            self.end_date += timedelta(days=days)
        else:
            self.start_date = timezone.now()
            self.end_date = self.start_date + timedelta(days=days)
            self.status = "active"
        self.save()

    def cancel_subscription(self):
        """Cancel the subscription."""
        self.status = "cancelled"
        self.auto_renew = False     
        self.save()

    def expire_subscription(self):
        """Expire the subscription."""
        self.status = "expired"
        self.auto_renew = False     
        self.save()

    def activate_subscription(self):
        """Activate the subscription."""
        self.status = "active"
        self.start_date = timezone.now()
        self.end_date = self.start_date + timedelta(days=self.plan.duration_days)     
        self.save()


class PinnedPost(models.Model):
    """Model for pinned posts by a subscribed user."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pinned_post"
    )

    post = models.OneToOneField(
        "posts.Post",
        on_delete=models.CASCADE,
        related_name="pinned_info"
    )
    pinned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pinned_posts"
        verbose_name = "Pinned Post"
        verbose_name_plural = "Pinned Posts"
        ordering = ["-pinned_at"]

    def __str__(self):
        return f"{self.user.username} - {self.post.title}"
    
    def save(self, *args, **kwargs):
        """Override save to ensure user has an active subscription."""
        if not hasattr(self.user, 'subscription') or not self.user.subscription.is_active:
            raise ValueError("User must have an active subscription to pin a post.")
        
        if  self.user != self.post.author:
            raise ValueError("User can only pin their own posts.")
        super().save(*args, **kwargs)

