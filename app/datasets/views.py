from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, Http404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone
from django.db import transaction

from .models import Dataset, DatasetCategory, DatasetVersion, DatasetDownload
from .forms import DatasetForm, DatasetFilterForm, DatasetVersionForm, DatasetCategoryForm, DatasetCategoryFilterForm


class DatasetListView(ListView):
    """List all published datasets"""
    model = Dataset
    template_name = 'datasets/dataset_list.html'
    context_object_name = 'datasets'
    paginate_by = 12

    def get_queryset(self):
        queryset = Dataset.objects.filter(
            status='published',
            access_level__in=['public', 'restricted']
        ).select_related('owner', 'category').prefetch_related('contributors')
        
        # Filter by category
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category__name=category)
        
        # Filter by search query
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(abstract__icontains=search) |
                Q(keywords__icontains=search) |
                Q(tags__icontains=search)
            )
        
        # Filter by tags
        tags = self.request.GET.get('tags')
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',')]
            for tag in tag_list:
                queryset = queryset.filter(tags__icontains=tag)
        
        # Order by featured first, then by creation date
        return queryset.order_by('-is_featured', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = DatasetCategory.objects.filter(is_active=True)
        context['featured_datasets'] = Dataset.objects.filter(
            status='published',
            is_featured=True,
            access_level__in=['public', 'restricted']
        ).select_related('owner', 'category')[:6]
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_category'] = self.request.GET.get('category', '')
        context['selected_tags'] = self.request.GET.get('tags', '')
        return context


class DatasetDetailView(DetailView):
    """View individual dataset details"""
    model = Dataset
    template_name = 'datasets/dataset_detail.html'
    context_object_name = 'dataset'

    def get_queryset(self):
        return Dataset.objects.select_related('owner', 'category').prefetch_related(
            'contributors', 'versions', 'related_datasets'
        )

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        
        # Check access permissions
        if not obj.is_accessible_by(self.request.user):
            raise Http404("Dataset not found or access denied")
        
        # Increment view count
        if self.request.user.is_authenticated:
            obj.view_count += 1
            obj.save(update_fields=['view_count'])
        
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dataset = self.get_object()
        
        # Add related datasets to context (from model relationship)
        context['related_datasets'] = dataset.related_datasets.filter(
            status='published',
            access_level__in=['public', 'restricted']
        ).select_related('owner', 'category')[:8]
        context['can_edit'] = (
            self.request.user == dataset.owner or 
            self.request.user.is_superuser
        )
        context['can_download'] = dataset.is_accessible_by(self.request.user)
        
        return context


class DatasetCreateView(LoginRequiredMixin, CreateView):
    """Create a new dataset"""
    model = Dataset
    form_class = DatasetForm
    template_name = 'datasets/dataset_form.html'

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, 'Dataset created successfully!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('datasets:dataset_detail', kwargs={'pk': self.object.pk})


class DatasetUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing dataset"""
    model = Dataset
    form_class = DatasetForm
    template_name = 'datasets/dataset_form.html'

    def get_queryset(self):
        return Dataset.objects.filter(owner=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Dataset updated successfully!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('datasets:dataset_detail', kwargs={'pk': self.object.pk})


class DatasetDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a dataset"""
    model = Dataset
    template_name = 'datasets/dataset_confirm_delete.html'
    success_url = reverse_lazy('datasets:dataset_list')

    def get_queryset(self):
        return Dataset.objects.filter(owner=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Dataset deleted successfully!')
        return super().delete(request, *args, **kwargs)


@login_required
def dataset_download(request, pk):
    """Handle dataset downloads"""
    dataset = get_object_or_404(Dataset, pk=pk)
    
    # Check access permissions
    if not dataset.is_accessible_by(request.user):
        raise Http404("Dataset not found or access denied")
    
    if not dataset.file:
        messages.error(request, 'No file available for download.')
        return redirect('datasets:dataset_detail', pk=pk)
    
    # Record download
    DatasetDownload.objects.create(
        dataset=dataset,
        user=request.user if request.user.is_authenticated else None,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    # Increment download count
    dataset.download_count += 1
    dataset.save(update_fields=['download_count'])
    
    # Serve file
    response = HttpResponse(dataset.file.read(), content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="{dataset.file.name}"'
    return response


def dataset_statistics(request):
    """Display dataset statistics"""
    stats = {
        'total_datasets': Dataset.objects.filter(status='published').count(),
        'total_categories': DatasetCategory.objects.filter(is_active=True).count(),
        'total_downloads': DatasetDownload.objects.count(),
        'total_contributors': Dataset.objects.filter(status='published').values('owner').distinct().count(),
        'recent_datasets': Dataset.objects.filter(
            status='published',
            access_level__in=['public', 'restricted']
        ).order_by('-created_at')[:5],
        'most_downloaded': Dataset.objects.filter(
            status='published',
            access_level__in=['public', 'restricted']
        ).order_by('-download_count')[:5],
        'categories_with_counts': DatasetCategory.objects.filter(
            is_active=True
        ).annotate(
            dataset_count=Count('datasets', filter=Q(datasets__status='published'))
        ).order_by('-dataset_count'),
    }
    
    return render(request, 'datasets/statistics.html', {'stats': stats})


class DatasetVersionCreateView(LoginRequiredMixin, CreateView):
    """Create a new version for a dataset"""
    model = DatasetVersion
    form_class = DatasetVersionForm
    template_name = 'datasets/dataset_version_form.html'

    def dispatch(self, request, *args, **kwargs):
        # Get the dataset and check permissions
        self.dataset = get_object_or_404(Dataset, pk=kwargs['dataset_pk'])
        
        # Check if user can add versions (owner, contributor, or superuser)
        if not (request.user == self.dataset.owner or 
                request.user in self.dataset.contributors.all() or 
                request.user.is_superuser):
            messages.error(request, 'You do not have permission to add versions to this dataset.')
            return redirect('datasets:dataset_detail', pk=self.dataset.pk)
        
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['dataset'] = self.dataset
        return kwargs

    def form_valid(self, form):
        form.instance.dataset = self.dataset
        form.instance.created_by = self.request.user
        form.instance.is_current = True  # New version becomes current
        
        # Set previous versions to not current
        DatasetVersion.objects.filter(dataset=self.dataset).update(is_current=False)
        
        messages.success(self.request, f'Version {form.instance.version_number} created successfully!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('datasets:dataset_detail', kwargs={'pk': self.dataset.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dataset'] = self.dataset
        return context


# Category Views
class DatasetCategoryListView(LoginRequiredMixin, ListView):
    """List all dataset categories"""
    model = DatasetCategory
    template_name = 'datasets/category_list.html'
    context_object_name = 'categories'
    paginate_by = 20

    def get_queryset(self):
        queryset = DatasetCategory.objects.all()
        
        # Apply filters
        search = self.request.GET.get('search')
        is_active = self.request.GET.get('is_active')
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(description__icontains=search)
            )
        
        if is_active == 'true':
            queryset = queryset.filter(is_active=True)
        elif is_active == 'false':
            queryset = queryset.filter(is_active=False)
        
        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = DatasetCategoryFilterForm(self.request.GET)
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_status'] = self.request.GET.get('is_active', '')
        return context


class DatasetCategoryCreateView(LoginRequiredMixin, CreateView):
    """Create a new dataset category"""
    model = DatasetCategory
    form_class = DatasetCategoryForm
    template_name = 'datasets/category_form.html'

    def get_success_url(self):
        return reverse('datasets:category_list')

    def form_valid(self, form):
        messages.success(self.request, f'Category "{form.instance.name}" created successfully!')
        return super().form_valid(form)


class DatasetCategoryUpdateView(LoginRequiredMixin, UpdateView):
    """Update an existing dataset category"""
    model = DatasetCategory
    form_class = DatasetCategoryForm
    template_name = 'datasets/category_form.html'

    def get_success_url(self):
        return reverse('datasets:category_list')

    def form_valid(self, form):
        messages.success(self.request, f'Category "{form.instance.name}" updated successfully!')
        return super().form_valid(form)


class DatasetCategoryDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a dataset category"""
    model = DatasetCategory
    template_name = 'datasets/category_confirm_delete.html'
    success_url = reverse_lazy('datasets:category_list')

    def delete(self, request, *args, **kwargs):
        category = self.get_object()
        messages.success(request, f'Category "{category.name}" deleted successfully!')
        return super().delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.get_object()
        
        # Check if category is used by any datasets
        dataset_count = Dataset.objects.filter(category=category).count()
        context['dataset_count'] = dataset_count
        context['can_delete'] = dataset_count == 0
        
        return context