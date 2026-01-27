from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import Subscription, PinnedPost

@receiver(pre_delete, sender=Subscription)
def subscription_pre_delete(sender, instance, **kwargs):
    """Deletes pinned post if subscription is cancelled"""
    try:
        instance.user.pinned_post.delete()
    except PinnedPost.DoesNotExist:
        pass

@receiver(post_save, sender=PinnedPost)
def pinned_post_post_save(sender, instance, created, **kwargs):
    """Handles pinned post"""
    if created:
        if not hasattr(instance.user, 'subscription') or not instance.user.subscription.is_active:
            instance.delete()

