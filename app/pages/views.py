import logging
import requests
import json
from datetime import datetime, timedelta

from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.db.models import Count, Sum, Q
from django.utils import timezone

logger = logging.getLogger(__name__)


class HomePageView(LoginRequiredMixin, TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['host'] = self.request.get_host()
        context['API_URL'] = settings.API_URL
        
        # Get real data from models
        try:
            from datasets.models import Dataset, DatasetVersion, DatasetCategory
            from user.models import CustomUser
            
            # Get basic statistics
            total_datasets = Dataset.objects.filter(status='published').count()
            total_users = CustomUser.objects.filter(is_active=True).count()
            
            # Calculate total data volume (sum of all file sizes)
            total_data_volume = DatasetVersion.objects.aggregate(
                total_size=Sum('file_size')
            )['total_size'] or 0
            
            # Convert bytes to human readable format
            if total_data_volume > 1024**4:  # TB
                data_volume_display = f"{total_data_volume / (1024**4):.1f}TB"
            elif total_data_volume > 1024**3:  # GB
                data_volume_display = f"{total_data_volume / (1024**3):.1f}GB"
            elif total_data_volume > 1024**2:  # MB
                data_volume_display = f"{total_data_volume / (1024**2):.1f}MB"
            else:
                data_volume_display = f"{total_data_volume / 1024:.1f}KB"
            
            # Get recent datasets (last 30 days)
            thirty_days_ago = timezone.now() - timedelta(days=30)
            recent_datasets = Dataset.objects.filter(
                created_at__gte=thirty_days_ago,
                status='published'
            ).select_related('owner', 'category').order_by('-created_at')[:5]
            
            # Get popular datasets (by download count)
            popular_datasets = Dataset.objects.filter(
                status='published'
            ).select_related('owner', 'category').order_by('-download_count')[:5]
            
            # Get recent activity (recent dataset versions)
            recent_versions = DatasetVersion.objects.filter(
                created_at__gte=thirty_days_ago
            ).select_related('dataset', 'dataset__owner').order_by('-created_at')[:10]
            
            # Get categories with dataset counts
            categories_with_counts = DatasetCategory.objects.annotate(
                dataset_count=Count('datasets', filter=Q(datasets__status='published'))
            ).filter(dataset_count__gt=0).order_by('-dataset_count')[:6]
            
            # Get user's datasets if logged in
            user_datasets = []
            if self.request.user.is_authenticated:
                user_datasets = Dataset.objects.filter(
                    owner=self.request.user
                ).select_related('category').order_by('-created_at')[:5]
            
            # Get user's recent activity
            user_recent_activity = []
            if self.request.user.is_authenticated:
                user_recent_activity = DatasetVersion.objects.filter(
                    dataset__owner=self.request.user
                ).select_related('dataset').order_by('-created_at')[:5]
            
            # System uptime (mock for now - could be real system monitoring)
            uptime_percentage = 99.9
            
            context.update({
                'total_datasets': total_datasets,
                'total_users': total_users,
                'data_volume_display': data_volume_display,
                'uptime_percentage': uptime_percentage,
                'recent_datasets': recent_datasets,
                'popular_datasets': popular_datasets,
                'recent_versions': recent_versions,
                'categories_with_counts': categories_with_counts,
                'user_datasets': user_datasets,
                'user_recent_activity': user_recent_activity,
                'thirty_days_ago': thirty_days_ago,
            })
            
        except ImportError:
            # If models are not available, use mock data
            context.update({
                'total_datasets': 0,
                'total_users': 0,
                'data_volume_display': '0KB',
                'uptime_percentage': 0,
                'recent_datasets': [],
                'popular_datasets': [],
                'recent_versions': [],
                'categories_with_counts': [],
                'user_datasets': [],
                'user_recent_activity': [],
                'thirty_days_ago': timezone.now() - timedelta(days=30),
            })
        
        # Add group membership data for the current user (keeping existing functionality)
        if self.request.user.is_authenticated:
            try:
                from group.models import GroupMember
                from local.models import Local, Council
                
                # Get user's group memberships
                group_memberships = GroupMember.objects.filter(
                    user=self.request.user,
                    is_active=True
                ).select_related(
                    'group',
                    'group__party',
                    'group__party__local'
                ).order_by('group__name')
                
                context['group_memberships'] = group_memberships
                
                # Get unique locals and councils from memberships
                locals_from_memberships = set()
                councils_from_memberships = set()
                
                for membership in group_memberships:
                    if membership.group.party and membership.group.party.local:
                        locals_from_memberships.add(membership.group.party.local)
                        if hasattr(membership.group.party.local, 'council') and membership.group.party.local.council:
                            councils_from_memberships.add(membership.group.party.local.council)
                
                context['locals_from_memberships'] = sorted(locals_from_memberships, key=lambda x: x.name)
                context['councils_from_memberships'] = sorted(councils_from_memberships, key=lambda x: x.name)
                
            except ImportError:
                # If models are not available, set empty lists
                context['group_memberships'] = []
                context['locals_from_memberships'] = []
                context['councils_from_memberships'] = []
        else:
            context['group_memberships'] = []
            context['locals_from_memberships'] = []
            context['councils_from_memberships'] = []
        
        return context