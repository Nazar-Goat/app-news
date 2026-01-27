from django.urls import path
from . import views

urlpatterns = [
    path('', views.CommentListCreateView.as_view(), name='comment-list'),
    path('my_comments/', views.MyCommentsListView.as_view(), name='my-comments'),
    path('<int:pk>/', views.CommentDetailsView.as_view(), name='comment-detail'),
    
    
]