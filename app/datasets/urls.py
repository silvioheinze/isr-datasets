from django.urls import path
from . import views

app_name = 'datasets'

urlpatterns = [
    # Dataset views
    path('', views.DatasetListView.as_view(), name='dataset_list'),
    path('<int:pk>/', views.DatasetDetailView.as_view(), name='dataset_detail'),
    path('create/', views.DatasetCreateView.as_view(), name='dataset_create'),
    path('<int:pk>/edit/', views.DatasetUpdateView.as_view(), name='dataset_edit'),
    path('<int:pk>/delete/', views.DatasetDeleteView.as_view(), name='dataset_delete'),
    path('<int:pk>/download/', views.dataset_download, name='dataset_download'),
    path('<int:dataset_pk>/version/create/', views.DatasetVersionCreateView.as_view(), name='dataset_version_create'),
    
    # Statistics
    path('statistics/', views.dataset_statistics, name='dataset_statistics'),
    
    # Category views
    path('categories/', views.DatasetCategoryListView.as_view(), name='category_list'),
    path('categories/create/', views.DatasetCategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/edit/', views.DatasetCategoryUpdateView.as_view(), name='category_edit'),
    path('categories/<int:pk>/delete/', views.DatasetCategoryDeleteView.as_view(), name='category_delete'),
    
    # Comment views
    path('<int:dataset_id>/comment/add/', views.add_comment, name='add_comment'),
    path('comment/<int:comment_id>/edit/', views.edit_comment, name='edit_comment'),
    path('comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),
    
    # Publishing Authority views
    path('publishing-authorities/', views.PublishingAuthorityListView.as_view(), name='publishing_authority_list'),
    path('publishing-authorities/create/', views.PublishingAuthorityCreateView.as_view(), name='publishing_authority_create'),
    path('publishing-authorities/<int:pk>/edit/', views.PublishingAuthorityUpdateView.as_view(), name='publishing_authority_edit'),
    path('publishing-authorities/<int:pk>/delete/', views.PublishingAuthorityDeleteView.as_view(), name='publishing_authority_delete'),
]
