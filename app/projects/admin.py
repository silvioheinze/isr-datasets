from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'owner', 'status', 'access_level', 
        'start_date', 'end_date', 'datasets_count', 'collaborators_count', 'created_at'
    ]
    list_filter = [
        'status', 'access_level', 'created_at', 'start_date', 'end_date'
    ]
    search_fields = [
        'title', 'description', 'abstract', 'keywords', 'tags', 
        'owner__username', 'owner__email', 'funding_source', 'grant_number'
    ]
    list_editable = ['status', 'access_level']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['collaborators']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'abstract')
        }),
        ('Project Timeline', {
            'fields': ('start_date', 'end_date', 'status')
        }),
        ('Access & Permissions', {
            'fields': ('access_level', 'owner', 'collaborators')
        }),
        ('Categorization', {
            'fields': ('keywords', 'tags')
        }),
        ('External References', {
            'fields': ('project_url', 'funding_source', 'grant_number'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def datasets_count(self, obj):
        """Display the number of datasets associated with this project"""
        return obj.datasets.count()
    datasets_count.short_description = _('Datasets')
    
    def collaborators_count(self, obj):
        """Display the number of collaborators"""
        return obj.collaborators.count()
    collaborators_count.short_description = _('Collaborators')
    
    def get_queryset(self, request):
        """Optimize queryset for admin list view"""
        return super().get_queryset(request).select_related('owner').prefetch_related(
            'collaborators', 'datasets'
        )