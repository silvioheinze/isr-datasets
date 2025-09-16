import datetime
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, TemplateView, UpdateView, ListView
from django.views.generic.list import ListView
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied

from .forms import CustomUserCreationForm, CustomUserEditForm, RoleForm, RoleFilterForm, UserSettingsForm, UserProfileForm, DataExportForm
from .models import Role

CustomUser = get_user_model()


def is_superuser_or_has_permission(permission):
    """Decorator to check if user is superuser or has specific permission"""
    def check_permission(user):
        return user.is_superuser or user.has_role_permission(permission)
    return user_passes_test(check_permission)


class AccountDeleteView(LoginRequiredMixin, DeleteView):
    model = get_user_model()
    template_name = 'user/confirm_delete.html'
    success_url = reverse_lazy('home')

    def get_object(self, queryset=None):
        # Ensure that only the logged-in user can delete their user
        return self.request.user

    def delete(self, request, *args, **kwargs):
        # Optionally, add a message for the user or perform extra cleanup
        messages.success(request, "Your user has been deleted successfully.")
        return super().delete(request, *args, **kwargs)





class SignupPageView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy("home")
    template_name = "user/signup.html"

    def form_valid(self, form):
        user = form.instance
        return super().form_valid(form)


def SettingsView(request):
    """
    Display user settings including profile and language preferences.
    If the user is not authenticated, display the login form.
    """
    if request.user.is_authenticated:
        # Initialize forms
        profile_form = UserProfileForm(instance=request.user)
        settings_form = UserSettingsForm(instance=request.user)
        
        # Handle form submissions
        if request.method == 'POST':
            # Check which form was submitted
            if 'profile_submit' in request.POST:
                profile_form = UserProfileForm(request.POST, instance=request.user)
                if profile_form.is_valid():
                    profile_form.save()
                    messages.success(request, 'Your profile information has been updated successfully.')
                    return redirect('user-settings')
            
            elif 'language_submit' in request.POST:
                settings_form = UserSettingsForm(request.POST, instance=request.user)
                if settings_form.is_valid():
                    settings_form.save()
                    # Activate the new language immediately
                    from django.utils import translation
                    new_language = settings_form.cleaned_data.get('language')
                    if new_language:
                        translation.activate(new_language)
                        request.LANGUAGE_CODE = new_language
                    messages.success(request, 'Your language preference has been updated successfully.')
                    return redirect('user-settings')
        
        context = {
            'user': request.user,
            'profile_form': profile_form,
            'settings_form': settings_form,
        }
        return render(request, "user/settings.html", context)
    else:
        # Process the login form for unauthenticated users
        form = AuthenticationForm(request=request, data=request.POST or None)
        if request.method == "POST":
            if form.is_valid():
                user = form.get_user()
                login(request, user)
                return redirect("home")
        return render(request, "user/login.html", {"form": form})


@login_required
def data_export_view(request):
    """
    Handle data export requests for GDPR compliance
    """
    if request.method == 'POST':
        form = DataExportForm(request.POST)
        if form.is_valid():
            export_format = form.cleaned_data['format']
            include_datasets = form.cleaned_data['include_datasets']
            include_projects = form.cleaned_data['include_projects']
            include_activity = form.cleaned_data['include_activity']
            
            # Prepare user data for export
            user_data = {
                'user_info': {
                    'username': request.user.username,
                    'email': request.user.email,
                    'first_name': request.user.first_name,
                    'last_name': request.user.last_name,
                    'date_joined': request.user.date_joined.isoformat(),
                    'last_login': request.user.last_login.isoformat() if request.user.last_login else None,
                    'language': request.user.language,
                    'role': request.user.role.name if request.user.role else None,
                }
            }
            
            # Add datasets if requested
            if include_datasets:
                try:
                    from datasets.models import Dataset, DatasetVersion
                    user_datasets = []
                    datasets = Dataset.objects.filter(owner=request.user)
                    for dataset in datasets:
                        dataset_info = {
                            'title': dataset.title,
                            'description': dataset.description,
                            'abstract': dataset.abstract,
                            'status': dataset.status,
                            'created_at': dataset.created_at.isoformat(),
                            'updated_at': dataset.updated_at.isoformat(),
                            'download_count': dataset.download_count,
                            'view_count': dataset.view_count,
                        }
                        
                        # Add dataset versions
                        versions = DatasetVersion.objects.filter(dataset=dataset)
                        dataset_info['versions'] = [
                            {
                                'version_number': version.version_number,
                                'description': version.description,
                                'created_at': version.created_at.isoformat(),
                                'file_size': version.file_size,
                            }
                            for version in versions
                        ]
                        user_datasets.append(dataset_info)
                    
                    user_data['datasets'] = user_datasets
                except ImportError:
                    user_data['datasets'] = []
            
            # Add projects if requested
            if include_projects:
                try:
                    from projects.models import Project
                    user_projects = []
                    projects = Project.objects.filter(
                        Q(owner=request.user) | Q(collaborators=request.user)
                    ).distinct()
                    for project in projects:
                        project_info = {
                            'title': project.title,
                            'description': project.description,
                            'abstract': project.abstract,
                            'status': project.status,
                            'access_level': project.access_level,
                            'created_at': project.created_at.isoformat(),
                            'updated_at': project.updated_at.isoformat(),
                            'is_owner': project.owner == request.user,
                        }
                        user_projects.append(project_info)
                    
                    user_data['projects'] = user_projects
                except ImportError:
                    user_data['projects'] = []
            
            # Add activity log if requested
            if include_activity:
                try:
                    from auditlog.models import LogEntry
                    # Get audit log entries for this user
                    log_entries = LogEntry.objects.filter(
                        content_type__model='customuser',
                        object_id=request.user.id
                    ).order_by('-timestamp')[:100]  # Limit to last 100 entries
                    
                    activity_log = [
                        {
                            'timestamp': entry.timestamp.isoformat(),
                            'action': entry.action,
                            'changes': entry.changes,
                        }
                        for entry in log_entries
                    ]
                    
                    user_data['activity_log'] = activity_log
                except ImportError:
                    user_data['activity_log'] = []
            
            # Generate response based on format
            from django.http import HttpResponse
            from datetime import datetime
            import json
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if export_format == 'json':
                response = HttpResponse(
                    json.dumps(user_data, indent=2, ensure_ascii=False),
                    content_type='application/json'
                )
                response['Content-Disposition'] = f'attachment; filename="user_data_export_{timestamp}.json"'
            
            elif export_format == 'csv':
                import csv
                import io
                
                output = io.StringIO()
                writer = csv.writer(output)
                
                # Write user info
                writer.writerow(['Field', 'Value'])
                for key, value in user_data['user_info'].items():
                    writer.writerow([key, value])
                
                # Write datasets if included
                if 'datasets' in user_data:
                    writer.writerow([])
                    writer.writerow(['Dataset', 'Title', 'Status', 'Created'])
                    for dataset in user_data['datasets']:
                        writer.writerow(['', dataset['title'], dataset['status'], dataset['created_at']])
                
                response = HttpResponse(
                    output.getvalue(),
                    content_type='text/csv'
                )
                response['Content-Disposition'] = f'attachment; filename="user_data_export_{timestamp}.csv"'
            
            else:  # XML
                from django.utils.xmlutils import SimplerXMLGenerator
                import io
                
                output = io.StringIO()
                xml = SimplerXMLGenerator(output, 'utf-8')
                xml.startDocument()
                xml.startElement('user_data_export', {})
                
                # User info
                xml.startElement('user_info', {})
                for key, value in user_data['user_info'].items():
                    xml.startElement(key, {})
                    xml.characters(str(value) if value is not None else '')
                    xml.endElement(key)
                xml.endElement('user_info')
                
                # Datasets
                if 'datasets' in user_data:
                    xml.startElement('datasets', {})
                    for dataset in user_data['datasets']:
                        xml.startElement('dataset', {})
                        for key, value in dataset.items():
                            if key != 'versions':
                                xml.startElement(key, {})
                                xml.characters(str(value) if value is not None else '')
                                xml.endElement(key)
                        xml.endElement('dataset')
                    xml.endElement('datasets')
                
                xml.endElement('user_data_export')
                xml.endDocument()
                
                response = HttpResponse(
                    output.getvalue(),
                    content_type='application/xml'
                )
                response['Content-Disposition'] = f'attachment; filename="user_data_export_{timestamp}.xml"'
            
            return response
    
    else:
        form = DataExportForm()
    
    return render(request, 'user/data_export.html', {'form': form})


class UsersUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = get_user_model()
    form_class = CustomUserEditForm
    template_name = 'user/edit.html'
    pk_url_kwarg = 'user_id'

    def get_success_url(self):
        return reverse_lazy('user-list')

    def test_func(self):
        # Allow access if user is superuser or has user.edit permission
        return self.request.user.is_superuser or self.request.user.has_role_permission('user.edit')


class UsersListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = get_user_model()
    context_object_name = 'users'
    template_name = 'user/list.html'
    paginate_by = 20

    def test_func(self):
        # Allow access only if user is superuser
        return self.request.user.is_superuser

    def get_queryset(self):
        queryset = CustomUser.objects.select_related('role').all().order_by('username')
        
        # Filter by search query
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(username__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
        
        # Filter by role
        role_filter = self.request.GET.get('role', '')
        if role_filter:
            queryset = queryset.filter(role__name=role_filter)
        
        # Filter by status
        status_filter = self.request.GET.get('status', '')
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['roles'] = Role.objects.filter(is_active=True)
        context['search_query'] = self.request.GET.get('search', '')
        context['role_filter'] = self.request.GET.get('role', '')
        context['status_filter'] = self.request.GET.get('status', '')
        return context


class UserCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = get_user_model()
    form_class = CustomUserCreationForm
    template_name = 'user/user_form.html'
    success_url = reverse_lazy('user-list')

    def test_func(self):
        # Allow access only if user is superuser
        return self.request.user.is_superuser

    def form_valid(self, form):
        messages.success(self.request, 'User created successfully.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


# Role Management Views
class RoleListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Role
    context_object_name = 'roles'
    template_name = 'user/role_list.html'
    paginate_by = 20

    def test_func(self):
        # Allow access only if user is superuser
        return self.request.user.is_superuser

    def get_queryset(self):
        queryset = Role.objects.all().order_by('name')
        
        # Filter by search query
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # Filter by status
        status_filter = self.request.GET.get('status', '')
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        return context


class RoleCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Role
    form_class = RoleForm
    template_name = 'user/role_form.html'
    success_url = reverse_lazy('role-list')

    def test_func(self):
        # Allow access only if user is superuser
        return self.request.user.is_superuser

    def form_valid(self, form):
        messages.success(self.request, f"Role '{form.instance.name}' created successfully.")
        return super().form_valid(form)


class RoleUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Role
    form_class = RoleForm
    template_name = 'user/role_form.html'
    success_url = reverse_lazy('role-list')

    def test_func(self):
        # Allow access only if user is superuser
        return self.request.user.is_superuser

    def form_valid(self, form):
        messages.success(self.request, f"Role '{form.instance.name}' updated successfully.")
        return super().form_valid(form)


class RoleDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Role
    template_name = 'user/role_confirm_delete.html'
    success_url = reverse_lazy('role-list')

    def test_func(self):
        # Allow access only if user is superuser
        return self.request.user.is_superuser

    def delete(self, request, *args, **kwargs):
        role = self.get_object()
        messages.success(request, f"Role '{role.name}' deleted successfully.")
        return super().delete(request, *args, **kwargs)


@login_required
def user_management_view(request):
    # Allow access only if user is superuser
    if not request.user.is_superuser:
        raise PermissionDenied
    """Comprehensive user management dashboard"""
    User = get_user_model()
    context = {
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'inactive_users': User.objects.filter(is_active=False).count(),
        'users_with_roles': User.objects.filter(role__isnull=False).count(),
        'users_without_roles': User.objects.filter(role__isnull=True).count(),
        'total_roles': Role.objects.count(),
        'active_roles': Role.objects.filter(is_active=True).count(),
        'recent_users': User.objects.select_related('role').order_by('-date_joined')[:5],
        'recent_roles': Role.objects.order_by('-created_at')[:5],
    }
    return render(request, 'user/management.html', context)
