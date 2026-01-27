from django.conf import settings
from django.db import models
from django.urls import reverse
from slugify import slugify


class Category(models.Model):
    """Model representing a blog post category."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "categories"
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    

class PostManager(models.Manager):
    """Custom manager for Post model"""

    def published(self):
        """returns published posts"""
        return self.filter(status='published')
    
    def pinned_posts(self):
        return self.filter(
            pinned_info__isnull=False,
            pinned_info__user__subscription__status='active',
            pinned_info__user__subscription__end_date__gt=models.functions.Now(),
            status='published'
        ).select_related(
            'pinned_info', 'pinned_info__user', 'pinned_info_user__subscription'
        ).order_by('pinned_info__pinned_at')
    
    def regular_posts(self):
        """returns regular posts"""
        return self.filter(
            pinned_info__isnull=True,
            status='published'
        )
    
    def with_subscription_info(self):
        return self.select_related(
            'author',
            'author__subscriptions',
            'category'
        ).prefetch_related('pinned_info')
    

class Post(models.Model):
    """Model representing a blog post."""

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    content = models.TextField()
    image = models.ImageField(upload_to='posts/', blank=True, null=True)
    
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='posts'
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='posts'
    )

    status = models.CharField(
        max_length=10,
        choices=[('draft', 'Draft'), ('published', 'Published')],
        default='draft'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    view_count = models.PositiveIntegerField(default=0)

    objects = PostManager()


    class Meta:
        db_table = "posts"
        verbose_name = "Post"
        verbose_name_plural = "Posts"
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse("post_detail", kwargs={"slug": self.slug})
    
    @property
    def count_comments(self):
        #
        return self.comments.filter(active=True).count()
    

    @property
    def is_pinned(self):
        return hasattr(self, 'pinned_info') and self.pinned_info is not None
    
    @property
    def can_be_pinned_by_user(self):
        if self.status != 'published':
            return False
        return True
    
    def can_be_pinned_by(self, user):
        if not user or not user.is_authenticated:
            return False
        
        if self.author != user:
            return False
        
        if self.status != 'published':
            return False
        
        if not hasattr(user, 'subscription') or not user.subscription.is_active:
            return False
        
        return True
    
    def increment_view_count(self):
        self.view_count += 1
        self.save(update_fields=['view_count'])

    def get_pinned_info(self):
        if self.is_pinned:
            return {
                'is_pinned': True,
                'pinned_at': self.pinned_info.pinned_at,
                'pinned_by':{
                    'id': self.pinned_info.user.id,
                    'username': self.pinned_info.user.username,
                    'has_active_subscription': self.pinned_info.user.subscription.is_active
                }
            }
        return {'is_pinned': False}
    