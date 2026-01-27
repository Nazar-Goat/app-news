from celery import shared_task
from django.utils import timezone
from .models import Subscription, PinnedPost, SubscriptionHistory

@shared_task
def check_expired_subscriptions():
    """Checks expired subscriptions and deletes pinned posts if exist"""
    time_now = timezone.now()

    expired_subscriptions = Subscription.objects.filter(
        status='active',
        end_date__lt=time_now,
    )

    expired_subscriptions_count = 0
    removed_pinned_posts_count = 0

    for subscription in expired_subscriptions:
        subscription.delete()
        expired_subscriptions_count += 1

        try:
            pinned_post = subscription.user.pinned_post
            pinned_post.delete()
            removed_pinned_posts_count += 1
        except PinnedPost.DoesNotExist:
            pass

    return {
        'expired_subscriptions': expired_subscriptions_count,
        'removed_pinned_posts': removed_pinned_posts_count
    }


@shared_task
def send_expiring_subscription_reminder():
    """Sends an email to notificate about expiring subscription"""
    from datetime import timedelta
    from django.core.mail import send_mail
    from django.conf import settings

    reminder_date = timezone.now() + timedelta(days=3)

    expiring_subscriptions = Subscription.objects.filter(
        status='active',
        end_date=reminder_date,
        auto_renew=False
    )

    reminders_sent_count = 0

    for subscription in expiring_subscriptions:
        try:
            send_mail(
                subject='Your subscription is expiring soon',
                message=f'Dear {subscription.user.get_full_name() or subscription.user.username},\n\n'
                       f'Your {subscription.plan.name} subscription will expire on {subscription.end_date.strftime("%B %d, %Y")}.\n\n'
                       f'To continue enjoying premium features, please renew your subscription.\n\n'
                       f'Best regards,\nNews Site Team',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[subscription.user.email],
                fail_silently=True
            )
            reminders_sent_count += 1
        except Exception as e:
            print(f'Failed to send reminder to {subscription.user.email}: {e}')

    return {
        'reminders_count': reminders_sent_count
    }