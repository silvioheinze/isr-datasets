from django.urls import path, include

from user.views import (
    AccountDeleteView, SettingsView, SignupPageView, 
    UsersUpdateView, UsersListView, UserCreateView, RoleListView, RoleCreateView, 
    RoleUpdateView, RoleDeleteView, user_management_view, data_export_view
)


urlpatterns = [
    # User Management
    path('delete/', AccountDeleteView.as_view(), name='user-delete'),
    path('settings/', SettingsView, name='user-settings'),
    path('data-export/', data_export_view, name='data-export'),
    path("signup/", SignupPageView.as_view(), name="user-signup"),
    path('list/', UsersListView.as_view(), name='user-list'),
    path('create/', UserCreateView.as_view(), name='user-create'),
    path('edit/<int:user_id>/', UsersUpdateView.as_view(), name='user-edit'),
    
    # Role Management
    path('roles/', RoleListView.as_view(), name='role-list'),
    path('roles/create/', RoleCreateView.as_view(), name='role-create'),
    path('roles/<int:pk>/edit/', RoleUpdateView.as_view(), name='role-edit'),
    path('roles/<int:pk>/delete/', RoleDeleteView.as_view(), name='role-delete'),
    
    # User Management Dashboard
    path('management/', user_management_view, name='user-management'),
    
    # Allauth URLs
    path("", include("allauth.account.urls")),
]