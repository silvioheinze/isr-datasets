from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView
)
from django.db.models import Q, Count
from django.urls import reverse_lazy
from django.http import Http404
from django.contrib.auth import get_user_model

from .models import Project
from .forms import ProjectForm, ProjectFilterForm

User = get_user_model()


class ProjectListView(LoginRequiredMixin, ListView):
    """List all projects accessible to the user"""
    model = Project
    template_name = 'projects/project_list.html'
    context_object_name = 'projects'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Project.objects.select_related('owner').prefetch_related('collaborators')
        
        # Apply access control
        if not self.request.user.is_superuser:
            queryset = queryset.filter(
                Q(owner=self.request.user) |
                Q(collaborators=self.request.user) |
                Q(access_level='public')
            ).distinct()
        
        # Apply filters
        search = self.request.GET.get('search')
        status = self.request.GET.get('status')
        
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(abstract__icontains=search) |
                Q(keywords__icontains=search) |
                Q(tags__icontains=search)
            )
        
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = ProjectFilterForm(self.request.GET)
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_status'] = self.request.GET.get('status', '')
        return context


class ProjectDetailView(LoginRequiredMixin, DetailView):
    """View individual project details"""
    model = Project
    template_name = 'projects/project_detail.html'
    context_object_name = 'project'
    
    def get_queryset(self):
        return Project.objects.select_related('owner').prefetch_related(
            'collaborators', 'datasets__owner', 'datasets__category', 'datasets__versions'
        )
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        
        # Check access permissions
        if not obj.is_accessible_by(self.request.user):
            raise Http404("Project not found or access denied")
        
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_object()
        
        context['can_edit'] = (
            self.request.user == project.owner or
            self.request.user in project.collaborators.all() or
            self.request.user.is_superuser
        )
        
        context['is_collaborator'] = (
            self.request.user in project.collaborators.all()
        )
        
        return context


class ProjectCreateView(LoginRequiredMixin, CreateView):
    """Create a new project"""
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Project "{self.object.title}" has been created successfully.'
        )
        return response
    
    def get_success_url(self):
        return reverse_lazy('projects:project_detail', kwargs={'pk': self.object.pk})


class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing project"""
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_form.html'
    
    def get_queryset(self):
        if self.request.user.is_superuser:
            return Project.objects.all()
        return Project.objects.filter(
            Q(owner=self.request.user) |
            Q(collaborators=self.request.user)
        )
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f'Project "{self.object.title}" has been updated successfully.'
        )
        return response
    
    def get_success_url(self):
        return reverse_lazy('projects:project_detail', kwargs={'pk': self.object.pk})


class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a project"""
    model = Project
    template_name = 'projects/project_confirm_delete.html'
    success_url = reverse_lazy('projects:project_list')
    
    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        project = self.get_object()
        project_title = project.title
        response = super().delete(request, *args, **kwargs)
        messages.success(
            request,
            f'Project "{project_title}" has been deleted successfully.'
        )
        return response

