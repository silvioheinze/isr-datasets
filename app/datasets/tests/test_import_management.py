"""
Unit tests for import management views
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import patch, MagicMock

from ..models import Dataset, DatasetVersion, DatasetImport, ImportQueue
from user.models import Role

User = get_user_model()


class ImportManagementViewsTestCase(TestCase):
    """Test cases for import management views"""
    
    def setUp(self):
        """Set up test data"""
        # Create roles
        self.admin_role, _ = Role.objects.get_or_create(
            name='Administrator',
            defaults={'is_active': True, 'permissions': {}}
        )
        self.editor_role, _ = Role.objects.get_or_create(
            name='Editor',
            defaults={'is_active': True, 'permissions': {}}
        )
        
        # Create users
        self.admin_user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            role=self.admin_role
        )
        self.editor_user = User.objects.create_user(
            username='editor',
            email='editor@test.com',
            password='testpass123',
            role=self.editor_role
        )
        
        # Create test dataset
        self.dataset = Dataset.objects.create(
            title='Test Dataset',
            description='Test dataset for import management',
            owner=self.admin_user,
            status='published'
        )
        
        # Create dataset version
        self.version = DatasetVersion.objects.create(
            dataset=self.dataset,
            version_number='1.0',
            description='Test version',
            is_current=True,
            created_by=self.admin_user
        )
        
        # Create import queue entry
        self.queue_entry = ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.admin_user,
            status='pending',
            priority='normal'
        )
        
        # Create dataset import
        self.dataset_import = DatasetImport.objects.create(
            dataset=self.dataset,
            imported_by=self.admin_user,
            status='completed',
            import_database_table='imported_dataset_test',
            records_imported=100
        )
        
        self.client = Client()
    
    def test_import_management_view_admin_access(self):
        """Test that administrators can access import management"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('datasets:import_management'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Database Management')
        self.assertContains(response, 'Test Dataset')
    
    def test_import_management_view_editor_access_denied(self):
        """Test that editors cannot access import management"""
        self.client.login(username='editor', password='testpass123')
        response = self.client.get(reverse('datasets:import_management'))
        
        self.assertEqual(response.status_code, 302)  # Redirected due to access denied
    
    def test_import_management_view_unauthenticated(self):
        """Test that unauthenticated users cannot access import management"""
        response = self.client.get(reverse('datasets:import_management'))
        
        self.assertEqual(response.status_code, 302)  # Redirected to login
    
    def test_import_management_context_data(self):
        """Test that import management view provides correct context data"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('datasets:import_management'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('queue_stats', response.context)
        self.assertIn('dataset_import_stats', response.context)
        self.assertIn('recent_imports', response.context)
        
        # Check queue stats
        queue_stats = response.context['queue_stats']
        self.assertEqual(queue_stats['total'], 1)
        self.assertEqual(queue_stats['pending'], 1)
        self.assertEqual(queue_stats['completed'], 0)
    
    def test_import_queue_detail_view(self):
        """Test import queue detail view"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('datasets:import_queue_detail', args=[self.queue_entry.pk]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Import Queue Detail')
        self.assertContains(response, 'Test Dataset')
    
    def test_import_queue_detail_view_access_denied(self):
        """Test that editors cannot access import queue detail"""
        self.client.login(username='editor', password='testpass123')
        response = self.client.get(reverse('datasets:import_queue_detail', args=[self.queue_entry.pk]))
        
        self.assertEqual(response.status_code, 302)  # Redirected due to access denied
    
    def test_cancel_import_success(self):
        """Test successful import cancellation"""
        self.client.login(username='admin', password='testpass123')
        
        # Ensure queue entry is pending
        self.queue_entry.status = 'pending'
        self.queue_entry.save()
        
        response = self.client.post(reverse('datasets:cancel_import', args=[self.queue_entry.pk]))
        
        self.assertEqual(response.status_code, 302)  # Redirected to management
        
        # Check that status was updated
        self.queue_entry.refresh_from_db()
        self.assertEqual(self.queue_entry.status, 'cancelled')
        self.assertIsNotNone(self.queue_entry.completed_at)
        self.assertEqual(self.queue_entry.error_message, 'Cancelled by administrator')
    
    def test_cancel_import_wrong_status(self):
        """Test that cancelling completed import fails"""
        self.client.login(username='admin', password='testpass123')
        
        # Set queue entry to completed
        self.queue_entry.status = 'completed'
        self.queue_entry.save()
        
        response = self.client.post(reverse('datasets:cancel_import', args=[self.queue_entry.pk]))
        
        self.assertEqual(response.status_code, 302)  # Redirected to management
        
        # Check that status was not changed
        self.queue_entry.refresh_from_db()
        self.assertEqual(self.queue_entry.status, 'completed')
    
    def test_cancel_import_access_denied(self):
        """Test that editors cannot cancel imports"""
        self.client.login(username='editor', password='testpass123')
        response = self.client.post(reverse('datasets:cancel_import', args=[self.queue_entry.pk]))
        
        self.assertEqual(response.status_code, 302)  # Redirected due to access denied
    
    def test_retry_import_success(self):
        """Test successful import retry"""
        self.client.login(username='admin', password='testpass123')
        
        # Set queue entry to failed
        self.queue_entry.status = 'failed'
        self.queue_entry.error_message = 'Test error'
        self.queue_entry.save()
        
        response = self.client.post(reverse('datasets:retry_import', args=[self.queue_entry.pk]))
        
        self.assertEqual(response.status_code, 302)  # Redirected to management
        
        # Check that status was reset
        self.queue_entry.refresh_from_db()
        self.assertEqual(self.queue_entry.status, 'pending')
        self.assertIsNone(self.queue_entry.started_at)
        self.assertIsNone(self.queue_entry.completed_at)
        self.assertEqual(self.queue_entry.error_message, '')
    
    def test_retry_import_wrong_status(self):
        """Test that retrying non-failed import fails"""
        self.client.login(username='admin', password='testpass123')
        
        # Ensure queue entry is pending
        self.queue_entry.status = 'pending'
        self.queue_entry.save()
        
        response = self.client.post(reverse('datasets:retry_import', args=[self.queue_entry.pk]))
        
        self.assertEqual(response.status_code, 302)  # Redirected to management
        
        # Check that status was not changed
        self.queue_entry.refresh_from_db()
        self.assertEqual(self.queue_entry.status, 'pending')
    
    def test_retry_import_access_denied(self):
        """Test that editors cannot retry imports"""
        self.client.login(username='editor', password='testpass123')
        response = self.client.post(reverse('datasets:retry_import', args=[self.queue_entry.pk]))
        
        self.assertEqual(response.status_code, 302)  # Redirected due to access denied
    
    @patch('datasets.views.ETLPipelineManager')
    def test_cleanup_import_database_success(self, mock_manager):
        """Test successful import database cleanup"""
        self.client.login(username='admin', password='testpass123')
        
        # Mock the cleanup method
        mock_manager.cleanup_old_imports.return_value = 5
        
        response = self.client.post(reverse('datasets:cleanup_import_database'))
        
        self.assertEqual(response.status_code, 302)  # Redirected to management
        mock_manager.cleanup_old_imports.assert_called_once_with(days=30)
    
    def test_cleanup_import_database_access_denied(self):
        """Test that editors cannot clean up import database"""
        self.client.login(username='editor', password='testpass123')
        response = self.client.post(reverse('datasets:cleanup_import_database'))
        
        self.assertEqual(response.status_code, 302)  # Redirected due to access denied
    
    def test_import_management_pagination(self):
        """Test that import management view supports pagination"""
        self.client.login(username='admin', password='testpass123')
        
        # Create additional queue entries to test pagination
        for i in range(25):
            dataset = Dataset.objects.create(
                title=f'Test Dataset {i}',
                description=f'Test dataset {i}',
                owner=self.admin_user,
                status='published'
            )
            ImportQueue.objects.create(
                dataset=dataset,
                requested_by=self.admin_user,
                status='pending',
                priority='normal'
            )
        
        response = self.client.get(reverse('datasets:import_management'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('is_paginated', response.context)
        self.assertTrue(response.context['is_paginated'])
    
    def test_import_queue_detail_with_dataset_import(self):
        """Test import queue detail view with associated dataset import"""
        self.client.login(username='admin', password='testpass123')
        
        # Link dataset import to queue entry
        self.queue_entry.dataset_import = self.dataset_import
        self.queue_entry.save()
        
        response = self.client.get(reverse('datasets:import_queue_detail', args=[self.queue_entry.pk]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dataset Import Details')
        self.assertContains(response, 'imported_dataset_test')
        self.assertContains(response, '100')
    
    @patch('django.db.connections')
    def test_import_management_database_error(self, mock_connections):
        """Test import management view with database connection error"""
        self.client.login(username='admin', password='testpass123')
        
        # Mock database connection error
        mock_connections.__getitem__.side_effect = Exception('Database connection failed')
        
        response = self.client.get(reverse('datasets:import_management'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Database Connection Error')
    
    def test_import_management_recent_imports(self):
        """Test that recent imports are displayed correctly"""
        self.client.login(username='admin', password='testpass123')
        
        # Create completed and failed imports
        completed_entry = ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.admin_user,
            status='completed',
            priority='normal',
            completed_at=timezone.now()
        )
        
        failed_entry = ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.admin_user,
            status='failed',
            priority='normal',
            completed_at=timezone.now()
        )
        
        response = self.client.get(reverse('datasets:import_management'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Recent Imports')
        self.assertContains(response, 'Completed')
        self.assertContains(response, 'Failed')
    
    @patch('datasets.etl_pipeline.ETLPipelineManager')
    def test_start_pipeline_success(self, mock_manager):
        """Test successful pipeline start"""
        self.client.login(username='admin', password='testpass123')
        
        # Mock the ETL pipeline to return a successful result
        mock_result = MagicMock()
        mock_result.dataset.title = 'Test Dataset'
        mock_manager.process_queue.return_value = mock_result
        
        # Ensure queue entry is pending
        self.queue_entry.status = 'pending'
        self.queue_entry.save()
        
        response = self.client.post(reverse('datasets:start_pipeline'))
        
        self.assertEqual(response.status_code, 302)  # Redirected to management
        mock_manager.process_queue.assert_called_once()
    
    def test_start_pipeline_already_processing(self):
        """Test starting pipeline when already processing"""
        self.client.login(username='admin', password='testpass123')
        
        # Set queue entry to processing
        self.queue_entry.status = 'processing'
        self.queue_entry.save()
        
        response = self.client.post(reverse('datasets:start_pipeline'))
        
        self.assertEqual(response.status_code, 302)  # Redirected to management
    
    def test_start_pipeline_access_denied(self):
        """Test that editors cannot start pipeline"""
        self.client.login(username='editor', password='testpass123')
        response = self.client.post(reverse('datasets:start_pipeline'))
        
        self.assertEqual(response.status_code, 302)  # Redirected due to access denied
    
    @patch('datasets.etl_pipeline.ETLPipelineManager')
    def test_process_all_pending_success(self, mock_manager):
        """Test processing all pending imports"""
        self.client.login(username='admin', password='testpass123')
        
        # Mock the ETL pipeline to return a successful result
        mock_result = MagicMock()
        mock_result.dataset.title = 'Test Dataset'
        mock_manager.process_queue.return_value = mock_result
        
        # Create additional pending imports
        for i in range(3):
            dataset = Dataset.objects.create(
                title=f'Test Dataset {i}',
                description=f'Test dataset {i}',
                owner=self.admin_user,
                status='published'
            )
            ImportQueue.objects.create(
                dataset=dataset,
                requested_by=self.admin_user,
                status='pending',
                priority='normal'
            )
        
        response = self.client.post(reverse('datasets:process_all_pending'))
        
        self.assertEqual(response.status_code, 302)  # Redirected to management
        # Should be called multiple times for each pending import
        self.assertGreater(mock_manager.process_queue.call_count, 0)
    
    def test_process_all_pending_no_pending(self):
        """Test processing when no pending imports exist"""
        self.client.login(username='admin', password='testpass123')
        
        # Ensure no pending imports
        ImportQueue.objects.filter(status='pending').update(status='completed')
        
        response = self.client.post(reverse('datasets:process_all_pending'))
        
        self.assertEqual(response.status_code, 302)  # Redirected to management
    
    def test_process_all_pending_access_denied(self):
        """Test that editors cannot process all pending"""
        self.client.login(username='editor', password='testpass123')
        response = self.client.post(reverse('datasets:process_all_pending'))
        
        self.assertEqual(response.status_code, 302)  # Redirected due to access denied
    
    def test_get_pipeline_status_success(self):
        """Test successful pipeline status retrieval"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('datasets:get_pipeline_status'))
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('is_processing', data)
        self.assertIn('queue_stats', data)
        self.assertIn('timestamp', data)
    
    def test_get_pipeline_status_access_denied(self):
        """Test that editors cannot get pipeline status"""
        self.client.login(username='editor', password='testpass123')
        response = self.client.get(reverse('datasets:get_pipeline_status'))
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertIn('error', data)
    
    def test_get_pipeline_status_unauthenticated(self):
        """Test that unauthenticated users cannot get pipeline status"""
        response = self.client.get(reverse('datasets:get_pipeline_status'))
        
        self.assertEqual(response.status_code, 302)  # Redirected to login
    
    @patch('datasets.etl_pipeline.ETLPipelineManager')
    def test_start_pipeline_with_error(self, mock_manager):
        """Test pipeline start with ETL error"""
        self.client.login(username='admin', password='testpass123')
        
        # Mock ETL error
        mock_manager.process_queue.side_effect = Exception('ETL processing failed')
        
        response = self.client.post(reverse('datasets:start_pipeline'))
        
        self.assertEqual(response.status_code, 302)  # Redirected to management
    
    def test_import_management_pipeline_status_context(self):
        """Test that import management view includes pipeline status"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('datasets:import_management'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('pipeline_status', response.context)
        
        pipeline_status = response.context['pipeline_status']
        self.assertIn('is_processing', pipeline_status)
        self.assertIn('pipeline_available', pipeline_status)
