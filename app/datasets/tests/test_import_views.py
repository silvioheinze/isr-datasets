"""
Unit tests for import views with queue functionality.
"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from datasets.models import Dataset, DatasetVersion, ImportQueue, DatasetImport
from user.models import Role

User = get_user_model()


class ImportViewsTestCase(TestCase):
    """Test cases for import views with queue functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Get or create roles
        self.admin_role, _ = Role.objects.get_or_create(
            name='Administrator',
            defaults={
                'description': 'Administrator role',
                'permissions': {'dataset.create': True, 'dataset.edit': True, 'dataset.delete': True}
            }
        )
        
        self.editor_role, _ = Role.objects.get_or_create(
            name='Editor',
            defaults={
                'description': 'Editor role',
                'permissions': {'dataset.create': True, 'dataset.edit': True}
            }
        )
        
        self.viewer_role, _ = Role.objects.get_or_create(
            name='Viewer',
            defaults={
                'description': 'Viewer role',
                'permissions': {'dataset.view': True}
            }
        )
        
        # Create users
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            role=self.admin_role
        )
        
        self.editor_user = User.objects.create_user(
            username='editor',
            email='editor@example.com',
            password='testpass123',
            role=self.editor_role
        )
        
        self.viewer_user = User.objects.create_user(
            username='viewer',
            email='viewer@example.com',
            password='testpass123',
            role=self.viewer_role
        )
        
        self.superuser = User.objects.create_superuser(
            username='superuser',
            email='superuser@example.com',
            password='testpass123'
        )
        
        # Create dataset
        self.dataset = Dataset.objects.create(
            title='Test Dataset',
            description='Test dataset for import views',
            owner=self.admin_user,
            status='published'
        )
        
        self.version = DatasetVersion.objects.create(
            dataset=self.dataset,
            version_number=1,
            description='Test version',
            is_current=True,
            created_by=self.admin_user
        )
        
        self.client = Client()
    
    def test_import_dataset_admin_access(self):
        """Test that admin users can import datasets."""
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get(reverse('datasets:import_dataset', kwargs={'pk': self.dataset.pk}))
        
        self.assertEqual(response.status_code, 302)  # Redirect after successful queue
        
        # Check that queue entry was created
        queue_entry = ImportQueue.objects.filter(
            dataset=self.dataset,
            requested_by=self.admin_user
        ).first()
        
        self.assertIsNotNone(queue_entry)
        self.assertEqual(queue_entry.status, 'pending')
        self.assertEqual(queue_entry.priority, 'normal')
    
    def test_import_dataset_editor_access(self):
        """Test that editor users can import datasets."""
        self.client.login(username='editor', password='testpass123')
        
        response = self.client.get(reverse('datasets:import_dataset', kwargs={'pk': self.dataset.pk}))
        
        self.assertEqual(response.status_code, 302)  # Redirect after successful queue
        
        # Check that queue entry was created
        queue_entry = ImportQueue.objects.filter(
            dataset=self.dataset,
            requested_by=self.editor_user
        ).first()
        
        self.assertIsNotNone(queue_entry)
        self.assertEqual(queue_entry.status, 'pending')
        self.assertEqual(queue_entry.priority, 'normal')
    
    def test_import_dataset_viewer_access_denied(self):
        """Test that viewer users cannot import datasets."""
        self.client.login(username='viewer', password='testpass123')
        
        response = self.client.get(reverse('datasets:import_dataset', kwargs={'pk': self.dataset.pk}))
        
        self.assertEqual(response.status_code, 302)  # Redirect after access denied
        
        # Check that no queue entry was created
        queue_entry = ImportQueue.objects.filter(
            dataset=self.dataset,
            requested_by=self.viewer_user
        ).first()
        
        self.assertIsNone(queue_entry)
    
    def test_import_dataset_superuser_access(self):
        """Test that superusers can import datasets with high priority."""
        self.client.login(username='superuser', password='testpass123')
        
        response = self.client.get(reverse('datasets:import_dataset', kwargs={'pk': self.dataset.pk}))
        
        self.assertEqual(response.status_code, 302)  # Redirect after successful queue
        
        # Check that queue entry was created
        queue_entry = ImportQueue.objects.filter(
            dataset=self.dataset,
            requested_by=self.superuser
        ).first()
        
        self.assertIsNotNone(queue_entry)
        self.assertEqual(queue_entry.status, 'pending')
        self.assertEqual(queue_entry.priority, 'high')  # Superusers get high priority
    
    def test_import_dataset_unauthenticated_access_denied(self):
        """Test that unauthenticated users cannot import datasets."""
        response = self.client.get(reverse('datasets:import_dataset', kwargs={'pk': self.dataset.pk}))
        
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Check that no queue entry was created
        queue_entry = ImportQueue.objects.filter(dataset=self.dataset).first()
        self.assertIsNone(queue_entry)
    
    def test_import_dataset_already_imported(self):
        """Test that users cannot import already imported datasets."""
        # Create a completed import
        DatasetImport.objects.create(
            dataset=self.dataset,
            imported_by=self.admin_user,
            status='completed',
            import_completed_at=timezone.now(),
            records_imported=10
        )
        
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get(reverse('datasets:import_dataset', kwargs={'pk': self.dataset.pk}))
        
        self.assertEqual(response.status_code, 302)  # Redirect after info message
        
        # Check that no new queue entry was created
        queue_entries = ImportQueue.objects.filter(
            dataset=self.dataset,
            requested_by=self.admin_user
        )
        self.assertEqual(queue_entries.count(), 0)
    
    def test_import_dataset_already_in_progress(self):
        """Test that users cannot import datasets already in progress."""
        # Create an in-progress import
        DatasetImport.objects.create(
            dataset=self.dataset,
            imported_by=self.admin_user,
            status='importing',
            records_imported=0
        )
        
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get(reverse('datasets:import_dataset', kwargs={'pk': self.dataset.pk}))
        
        self.assertEqual(response.status_code, 302)  # Redirect after info message
        
        # Check that no new queue entry was created
        queue_entries = ImportQueue.objects.filter(
            dataset=self.dataset,
            requested_by=self.admin_user
        )
        self.assertEqual(queue_entries.count(), 0)
    
    def test_import_dataset_already_queued(self):
        """Test that users cannot queue already queued datasets."""
        # Create a pending queue entry
        ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.admin_user,
            status='pending',
            priority='normal'
        )
        
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get(reverse('datasets:import_dataset', kwargs={'pk': self.dataset.pk}))
        
        self.assertEqual(response.status_code, 302)  # Redirect after info message
        
        # Check that only one queue entry exists
        queue_entries = ImportQueue.objects.filter(
            dataset=self.dataset,
            requested_by=self.admin_user
        )
        self.assertEqual(queue_entries.count(), 1)
    
    def test_import_dataset_already_processing(self):
        """Test that users cannot queue datasets already processing."""
        # Create a processing queue entry
        ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.admin_user,
            status='processing',
            priority='normal'
        )
        
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get(reverse('datasets:import_dataset', kwargs={'pk': self.dataset.pk}))
        
        self.assertEqual(response.status_code, 302)  # Redirect after info message
        
        # Check that only one queue entry exists
        queue_entries = ImportQueue.objects.filter(
            dataset=self.dataset,
            requested_by=self.admin_user
        )
        self.assertEqual(queue_entries.count(), 1)
    
    def test_import_dataset_failed_import_retry(self):
        """Test that users can retry failed imports."""
        # Create a failed import
        DatasetImport.objects.create(
            dataset=self.dataset,
            imported_by=self.admin_user,
            status='failed',
            error_message='Test error'
        )
        
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get(reverse('datasets:import_dataset', kwargs={'pk': self.dataset.pk}))
        
        self.assertEqual(response.status_code, 302)  # Redirect after successful queue
        
        # Check that queue entry was created for retry
        queue_entry = ImportQueue.objects.filter(
            dataset=self.dataset,
            requested_by=self.admin_user
        ).first()
        
        self.assertIsNotNone(queue_entry)
        self.assertEqual(queue_entry.status, 'pending')
    
    def test_import_dataset_queue_position(self):
        """Test that queue position is calculated correctly."""
        # Create multiple queue entries
        ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.editor_user,
            status='pending',
            priority='normal'
        )
        
        ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.viewer_user,
            status='pending',
            priority='low'
        )
        
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get(reverse('datasets:import_dataset', kwargs={'pk': self.dataset.pk}))
        
        self.assertEqual(response.status_code, 302)  # Redirect after successful queue
        
        # Check that queue entry was created
        queue_entry = ImportQueue.objects.filter(
            dataset=self.dataset,
            requested_by=self.admin_user
        ).first()
        
        self.assertIsNotNone(queue_entry)
        self.assertEqual(queue_entry.status, 'pending')
    
    def test_import_dataset_priority_assignment(self):
        """Test that priority is assigned correctly based on user role."""
        # Test admin priority
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('datasets:import_dataset', kwargs={'pk': self.dataset.pk}))
        self.assertEqual(response.status_code, 302)
        
        admin_queue = ImportQueue.objects.filter(
            dataset=self.dataset,
            requested_by=self.admin_user
        ).first()
        self.assertEqual(admin_queue.priority, 'normal')
        
        # Test superuser priority
        self.client.login(username='superuser', password='testpass123')
        response = self.client.get(reverse('datasets:import_dataset', kwargs={'pk': self.dataset.pk}))
        self.assertEqual(response.status_code, 302)
        
        superuser_queue = ImportQueue.objects.filter(
            dataset=self.dataset,
            requested_by=self.superuser
        ).first()
        self.assertEqual(superuser_queue.priority, 'high')
    
    def test_import_dataset_nonexistent_dataset(self):
        """Test import request for non-existent dataset."""
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get(reverse('datasets:import_dataset', kwargs={'pk': '99999999-9999-9999-9999-999999999999'}))
        
        self.assertEqual(response.status_code, 404)  # Not found


class DatasetDetailViewImportTestCase(TestCase):
    """Test cases for dataset detail view with import functionality."""
    
    def setUp(self):
        """Set up test data."""
        # Get or create roles
        self.admin_role, _ = Role.objects.get_or_create(
            name='Administrator',
            defaults={
                'description': 'Administrator role',
                'permissions': {'dataset.create': True, 'dataset.edit': True, 'dataset.delete': True}
            }
        )
        
        self.editor_role, _ = Role.objects.get_or_create(
            name='Editor',
            defaults={
                'description': 'Editor role',
                'permissions': {'dataset.create': True, 'dataset.edit': True}
            }
        )
        
        self.viewer_role, _ = Role.objects.get_or_create(
            name='Viewer',
            defaults={
                'description': 'Viewer role',
                'permissions': {'dataset.view': True}
            }
        )
        
        # Create users
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass123',
            role=self.admin_role
        )
        
        self.editor_user = User.objects.create_user(
            username='editor',
            email='editor@example.com',
            password='testpass123',
            role=self.editor_role
        )
        
        self.viewer_user = User.objects.create_user(
            username='viewer',
            email='viewer@example.com',
            password='testpass123',
            role=self.viewer_role
        )
        
        # Create dataset
        self.dataset = Dataset.objects.create(
            title='Test Dataset',
            description='Test dataset for detail view',
            owner=self.admin_user,
            status='published'
        )
        
        self.version = DatasetVersion.objects.create(
            dataset=self.dataset,
            version_number=1,
            description='Test version',
            is_current=True,
            created_by=self.admin_user
        )
        
        self.client = Client()
    
    def test_dataset_detail_view_import_context_admin(self):
        """Test that admin users see import context in dataset detail view."""
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get(reverse('datasets:dataset_detail', kwargs={'pk': self.dataset.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['can_import'])
        self.assertIsNone(response.context['dataset_import'])
        self.assertIsNone(response.context['import_queue_entry'])
        self.assertIsNotNone(response.context['queue_stats'])
    
    def test_dataset_detail_view_import_context_editor(self):
        """Test that editor users see import context in dataset detail view."""
        self.client.login(username='editor', password='testpass123')
        
        response = self.client.get(reverse('datasets:dataset_detail', kwargs={'pk': self.dataset.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['can_import'])
        self.assertIsNone(response.context['dataset_import'])
        self.assertIsNone(response.context['import_queue_entry'])
        self.assertIsNotNone(response.context['queue_stats'])
    
    def test_dataset_detail_view_import_context_viewer(self):
        """Test that viewer users do not see import context in dataset detail view."""
        self.client.login(username='viewer', password='testpass123')
        
        response = self.client.get(reverse('datasets:dataset_detail', kwargs={'pk': self.dataset.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['can_import'])
        self.assertIsNone(response.context['dataset_import'])
        self.assertIsNone(response.context['import_queue_entry'])
        self.assertIsNone(response.context['queue_stats'])
    
    def test_dataset_detail_view_with_completed_import(self):
        """Test dataset detail view with completed import."""
        # Create completed import
        dataset_import = DatasetImport.objects.create(
            dataset=self.dataset,
            imported_by=self.admin_user,
            status='completed',
            import_completed_at=timezone.now(),
            records_imported=10,
            import_database_table='test_table'
        )
        
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get(reverse('datasets:dataset_detail', kwargs={'pk': self.dataset.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['dataset_import'], dataset_import)
        self.assertIsNone(response.context['import_queue_entry'])
    
    def test_dataset_detail_view_with_pending_queue(self):
        """Test dataset detail view with pending queue entry."""
        # Create pending queue entry
        queue_entry = ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.admin_user,
            status='pending',
            priority='normal'
        )
        
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get(reverse('datasets:dataset_detail', kwargs={'pk': self.dataset.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['dataset_import'])
        self.assertEqual(response.context['import_queue_entry'], queue_entry)
    
    def test_dataset_detail_view_with_processing_queue(self):
        """Test dataset detail view with processing queue entry."""
        # Create processing queue entry
        queue_entry = ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.admin_user,
            status='processing',
            priority='normal',
            started_at=timezone.now()
        )
        
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get(reverse('datasets:dataset_detail', kwargs={'pk': self.dataset.pk}))
        
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['dataset_import'])
        self.assertEqual(response.context['import_queue_entry'], queue_entry)
    
    def test_dataset_detail_view_queue_stats(self):
        """Test that queue statistics are included in context."""
        # Create various queue entries
        ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.admin_user,
            status='pending',
            priority='normal'
        )
        ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.editor_user,
            status='processing',
            priority='high'
        )
        ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.viewer_user,
            status='completed',
            priority='normal'
        )
        
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get(reverse('datasets:dataset_detail', kwargs={'pk': self.dataset.pk}))
        
        self.assertEqual(response.status_code, 200)
        queue_stats = response.context['queue_stats']
        self.assertEqual(queue_stats['pending'], 1)
        self.assertEqual(queue_stats['processing'], 1)
        self.assertEqual(queue_stats['completed'], 1)
        self.assertEqual(queue_stats['failed'], 0)
        self.assertEqual(queue_stats['total'], 3)
