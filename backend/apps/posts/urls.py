from django.urls import path
from . import views

urlpatterns = [
    path('categories/', views.CategoryListCreateView.as_view(), name='category-list'),
    path('categories/<slug:slug>/', views.CategoryDetailsView.as_view(), name='category-detail'),

    path('', views.PostListCreateView.as_view(), name='posts-list'),
    path('my-posts/', views.MyPostsView.as_view(), name='my-posts'),
    path('pinned/', views.pinned_posts_only, name='pinned-posts-only'),
    path('featured/', views.featured_posts, name='featured-posts'),
    path('<slug:slug>/', views.PostDetailsView.as_view(), name='post-detail'),
    
]
