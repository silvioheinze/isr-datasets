from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, Http404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone
from django.db import transaction

from .models import Dataset, DatasetCategory, DatasetVersion, DatasetDownload, Comment, Publisher
from .forms import DatasetForm, DatasetFilterForm, DatasetVersionForm, DatasetCategoryForm, DatasetCategoryFilterForm, CommentForm, CommentEditForm, PublisherForm, PublisherFilterForm, DatasetProjectAssignmentForm


class DatasetListView(ListView):
    """List all published datasets"""
    model = Dataset
    template_name = 'datasets/dataset_list.html'
    context_object_name = 'datasets'
    paginate_by = 12

    def get_queryset(self):
        # Superusers can see all datasets
        if self.request.user and self.request.user.is_authenticated and self.request.user.is_superuser:
            queryset = Dataset.objects.all().select_related('owner', 'category').prefetch_related('contributors', 'versions')
        else:
            # Base queryset for published datasets with public/restricted access
            queryset = Dataset.objects.filter(
                status='published',
                access_level__in=['public', 'restricted']
            ).select_related('owner', 'category').prefetch_related('contributors', 'versions')
            
            # Add private datasets that belong to the current user
            if self.request.user and self.request.user.is_authenticated:
                user_private_datasets = Dataset.objects.filter(
                    owner=self.request.user,
                    access_level='private'
                ).select_related('owner', 'category').prefetch_related('contributors', 'versions')
                
                # Combine the querysets
                queryset = queryset.union(user_private_datasets)
        
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
        
        # Featured datasets - superusers see all featured datasets
        if self.request.user and self.request.user.is_authenticated and self.request.user.is_superuser:
            featured_queryset = Dataset.objects.filter(
                is_featured=True
            ).select_related('owner', 'category').prefetch_related('versions')
        else:
            # Featured datasets including user's private datasets
            featured_queryset = Dataset.objects.filter(
                status='published',
                is_featured=True,
                access_level__in=['public', 'restricted']
            ).select_related('owner', 'category').prefetch_related('versions')
            
            # Add user's private featured datasets
            if self.request.user and self.request.user.is_authenticated:
                user_private_featured = Dataset.objects.filter(
                    owner=self.request.user,
                    is_featured=True,
                    access_level='private'
                ).select_related('owner', 'category').prefetch_related('versions')
                
                featured_queryset = featured_queryset.union(user_private_featured)
        
        context['featured_datasets'] = featured_queryset[:6]
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
        return Dataset.objects.select_related('owner', 'category', 'publisher').prefetch_related(
            'contributors', 'versions', 'related_datasets', 'comments__author', 'projects'
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
        context['can_assign_project'] = (
            self.request.user == dataset.owner or 
            self.request.user.is_superuser
        )
        
        # Add comments to context
        context['comments'] = dataset.comments.filter(is_approved=True).select_related('author')
        context['comment_form'] = CommentForm(user=self.request.user, dataset=dataset)
        
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
        # Allow owners, contributors, and staff/superusers to edit
        if self.request.user.is_staff or self.request.user.is_superuser:
            return Dataset.objects.all()
        return Dataset.objects.filter(
            Q(owner=self.request.user) | 
            Q(contributors=self.request.user)
        ).distinct()

    def form_valid(self, form):
        # Send notification about dataset update
        send_dataset_update_notification_email(self.object)
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
        # Allow owners, contributors, and staff/superusers to delete
        if self.request.user.is_staff or self.request.user.is_superuser:
            return Dataset.objects.all()
        return Dataset.objects.filter(
            Q(owner=self.request.user) | 
            Q(contributors=self.request.user)
        ).distinct()

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
        
        # Send notification about new version
        send_new_version_notification_email(self.dataset, form.instance)
        
        messages.success(self.request, f'Version {form.instance.version_number} created successfully!')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

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


# Comment Views
@login_required
def add_comment(request, dataset_id):
    """Add a comment to a dataset"""
    dataset = get_object_or_404(Dataset, id=dataset_id)
    
    if request.method == 'POST':
        form = CommentForm(request.POST, user=request.user, dataset=dataset)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.dataset = dataset
            comment.author = request.user
            comment.save()
            
            # Send email notification to dataset owner if enabled
            if dataset.owner.notify_comments and dataset.owner != request.user:
                send_comment_notification_email(comment)
            
            messages.success(request, 'Your comment has been added successfully.')
            return redirect('datasets:dataset_detail', pk=dataset.id)
    else:
        form = CommentForm(user=request.user, dataset=dataset)
    
    return render(request, 'datasets/dataset_detail.html', {
        'dataset': dataset,
        'comment_form': form
    })


@login_required
def edit_comment(request, comment_id):
    """Edit a comment"""
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Check if user can edit this comment
    if not comment.can_edit(request.user):
        messages.error(request, 'You do not have permission to edit this comment.')
        return redirect('datasets:dataset_detail', pk=comment.dataset.id)
    
    if request.method == 'POST':
        form = CommentEditForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your comment has been updated successfully.')
            return redirect('datasets:dataset_detail', pk=comment.dataset.id)
    else:
        form = CommentEditForm(instance=comment)
    
    return render(request, 'datasets/comment_edit.html', {
        'form': form,
        'comment': comment,
        'dataset': comment.dataset
    })


@login_required
def delete_comment(request, comment_id):
    """Delete a comment"""
    comment = get_object_or_404(Comment, id=comment_id)
    
    # Check if user can delete this comment
    if not comment.can_delete(request.user):
        messages.error(request, 'You do not have permission to delete this comment.')
        return redirect('datasets:dataset_detail', pk=comment.dataset.id)
    
    dataset_id = comment.dataset.id
    comment.delete()
    messages.success(request, 'Your comment has been deleted successfully.')
    return redirect('datasets:dataset_detail', pk=dataset_id)


def send_comment_notification_email(comment):
    """Send email notification to dataset owner about new comment"""
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.conf import settings
    
    dataset = comment.dataset
    owner = dataset.owner
    
    # Check if owner wants to receive comment notifications
    if not owner.notify_comments:
        return
    
    # Prepare email context
    context = {
        'owner': owner,
        'comment': comment,
        'dataset': dataset,
        'commenter': comment.author,
        'site_name': getattr(settings, 'SITE_NAME', 'ISR Datasets'),
        'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
    }
    
    # Render email templates
    subject = f'New comment on your dataset: {dataset.title}'
    html_message = render_to_string('datasets/email/comment_notification.html', context)
    plain_message = render_to_string('datasets/email/comment_notification.txt', context)
    
    try:
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[owner.email],
            fail_silently=False,
        )
    except Exception as e:
        # Log the error but don't break the comment creation
        print(f"Failed to send comment notification email: {e}")


def send_dataset_update_notification_email(dataset):
    """Send email notification to users following this dataset about updates"""
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.conf import settings
    from user.models import CustomUser
    
    # Get users who want to receive dataset update notifications
    # For now, we'll notify all users who have this preference enabled
    # In a more advanced system, you might have a "following" relationship
    users_to_notify = CustomUser.objects.filter(
        notify_dataset_updates=True,
        is_active=True
    ).exclude(email='')
    
    if not users_to_notify.exists():
        return
    
    # Prepare email context
    context = {
        'dataset': dataset,
        'site_name': getattr(settings, 'SITE_NAME', 'ISR Datasets'),
        'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
    }
    
    # Render email templates
    subject = f'Dataset updated: {dataset.title}'
    html_message = render_to_string('datasets/email/dataset_update_notification.html', context)
    plain_message = render_to_string('datasets/email/dataset_update_notification.txt', context)
    
    # Send emails to all users
    for user in users_to_notify:
        try:
            context['user'] = user
            send_mail(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Failed to send dataset update notification email to {user.email}: {e}")


def send_new_version_notification_email(dataset, version):
    """Send email notification to users following this dataset about new versions"""
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    from django.conf import settings
    from user.models import CustomUser
    
    # Get users who want to receive new version notifications
    users_to_notify = CustomUser.objects.filter(
        notify_new_versions=True,
        is_active=True
    ).exclude(email='')
    
    if not users_to_notify.exists():
        return
    
    # Prepare email context
    context = {
        'dataset': dataset,
        'version': version,
        'site_name': getattr(settings, 'SITE_NAME', 'ISR Datasets'),
        'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
    }
    
    # Render email templates
    subject = f'New version available: {dataset.title} v{version.version_number}'
    html_message = render_to_string('datasets/email/new_version_notification.html', context)
    plain_message = render_to_string('datasets/email/new_version_notification.txt', context)
    
    # Send emails to all users
    for user in users_to_notify:
        try:
            context['user'] = user
            send_mail(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Failed to send new version notification email to {user.email}: {e}")


# Publisher Views
class PublisherListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """List all publishers"""
    model = Publisher
    context_object_name = 'publishers'
    template_name = 'datasets/publisher_list.html'
    paginate_by = 20

    def test_func(self):
        # Allow access only if user is superuser
        return self.request.user.is_superuser

    def get_queryset(self):
        queryset = Publisher.objects.all().order_by('name')
        
        # Filter by search query
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        # Filter by active status
        is_active_filter = self.request.GET.get('is_active', '')
        if is_active_filter == 'true':
            queryset = queryset.filter(is_active=True)
        elif is_active_filter == 'false':
            queryset = queryset.filter(is_active=False)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['is_active_filter'] = self.request.GET.get('is_active', '')
        return context


class PublisherCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Create a new publisher"""
    model = Publisher
    form_class = PublisherForm
    template_name = 'datasets/publisher_form.html'
    success_url = reverse_lazy('datasets:publisher_list')

    def test_func(self):
        # Allow access only if user is superuser
        return self.request.user.is_superuser

    def form_valid(self, form):
        messages.success(self.request, 'Publishing authority created successfully.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class PublisherUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update an existing publisher"""
    model = Publisher
    form_class = PublisherForm
    template_name = 'datasets/publisher_form.html'
    success_url = reverse_lazy('datasets:publisher_list')

    def test_func(self):
        # Allow access only if user is superuser
        return self.request.user.is_superuser

    def form_valid(self, form):
        messages.success(self.request, 'Publishing authority updated successfully.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class PublisherDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete a publisher"""
    model = Publisher
    template_name = 'datasets/publisher_confirm_delete.html'
    success_url = reverse_lazy('datasets:publisher_list')

    def test_func(self):
        # Allow access only if user is superuser
        return self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        publishing_authority = self.get_object()
        
        # Check if publishing authority is used by any datasets
        dataset_count = Dataset.objects.filter(publishing_authority=publishing_authority).count()
        context['dataset_count'] = dataset_count
        context['can_delete'] = dataset_count == 0
        
        return context

    def delete(self, request, *args, **kwargs):
        publishing_authority = self.get_object()
        dataset_count = Dataset.objects.filter(publishing_authority=publishing_authority).count()
        
        if dataset_count > 0:
            messages.error(
                request, 
                f'Cannot delete "{publishing_authority.name}" because it is used by {dataset_count} dataset(s).'
            )
            return redirect('datasets:publishing_authority_list')
        
        messages.success(request, f'Publishing authority "{publishing_authority.name}" deleted successfully.')
        return super().delete(request, *args, **kwargs)


def assign_dataset_to_project(request, pk):
    """Assign a dataset to projects"""
    dataset = get_object_or_404(Dataset, pk=pk)
    
    # Check permissions - user must be dataset owner or superuser
    if not (request.user == dataset.owner or request.user.is_superuser):
        messages.error(request, 'You do not have permission to assign this dataset to projects.')
        return redirect('datasets:dataset_detail', pk=pk)
    
    if request.method == 'POST':
        form = DatasetProjectAssignmentForm(request.POST, user=request.user, dataset=dataset)
        if form.is_valid():
            selected_projects = form.cleaned_data['projects']
            
            # Update the dataset's projects
            dataset.projects.set(selected_projects)
            
            if selected_projects:
                project_names = [p.title for p in selected_projects]
                messages.success(request, f'Dataset "{dataset.title}" has been assigned to projects: {", ".join(project_names)}.')
            else:
                messages.success(request, f'Dataset "{dataset.title}" has been removed from all projects.')
            
            return redirect('datasets:dataset_detail', pk=pk)
    else:
        form = DatasetProjectAssignmentForm(user=request.user, dataset=dataset)
    
    return render(request, 'datasets/assign_to_project.html', {
        'form': form,
        'dataset': dataset
    })