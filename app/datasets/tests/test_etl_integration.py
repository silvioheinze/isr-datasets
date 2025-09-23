"""
Integration tests for ETL pipeline complete workflow.
"""

import os
import tempfile
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.management import call_command
from django.db import connections

from datasets.models import Dataset, DatasetVersion, ImportQueue, DatasetImport
from datasets.etl_pipeline import ETLPipelineManager
from user.models import Role

User = get_user_model()


class ETLIntegrationTestCase(TestCase):
    """Integration tests for complete ETL workflow."""
    
    def setUp(self):
        """Set up test data."""
        # Create roles
        self.admin_role = Role.objects.create(
            name='Administrator',
            description='Administrator role',
            permissions={'dataset.create': True, 'dataset.edit': True, 'dataset.delete': True}
        )
        
        self.editor_role = Role.objects.create(
            name='Editor',
            description='Editor role',
            permissions={'dataset.create': True, 'dataset.edit': True}
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
        
        # Create dataset
        self.dataset = Dataset.objects.create(
            title='Test Dataset',
            description='Test dataset for ETL integration',
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
    
    def test_complete_etl_workflow_basic_info(self):
        """Test complete ETL workflow with basic info extraction."""
        # Step 1: Queue import through web interface
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get(reverse('datasets:import_dataset', kwargs={'pk': self.dataset.pk}))
        self.assertEqual(response.status_code, 302)
        
        # Verify queue entry was created
        queue_entry = ImportQueue.objects.filter(
            dataset=self.dataset,
            requested_by=self.admin_user
        ).first()
        
        self.assertIsNotNone(queue_entry)
        self.assertEqual(queue_entry.status, 'pending')
        
        # Step 2: Process queue using ETL pipeline
        success = ETLPipelineManager.process_next_import()
        self.assertTrue(success)
        
        # Step 3: Verify queue entry was updated
        queue_entry.refresh_from_db()
        self.assertEqual(queue_entry.status, 'completed')
        self.assertIsNotNone(queue_entry.started_at)
        self.assertIsNotNone(queue_entry.completed_at)
        
        # Step 4: Verify DatasetImport was created
        dataset_import = queue_entry.dataset_import
        self.assertIsNotNone(dataset_import)
        self.assertEqual(dataset_import.status, 'completed')
        self.assertEqual(dataset_import.records_imported, 1)
        self.assertIsNotNone(dataset_import.import_database_table)
        
        # Step 5: Verify dataset detail view shows completed import
        response = self.client.get(reverse('datasets:dataset_detail', kwargs={'pk': self.dataset.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['dataset_import'], dataset_import)
        self.assertIsNone(response.context['import_queue_entry'])
    
    def test_complete_etl_workflow_csv_file(self):
        """Test complete ETL workflow with CSV file."""
        # Create a temporary CSV file
        csv_content = "name,age,city\nJohn,25,New York\nJane,30,Los Angeles"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            csv_path = f.name
        
        try:
            # Update version with file path
            self.version.file.name = csv_path
            self.version.save()
            
            # Step 1: Queue import
            self.client.login(username='admin', password='testpass123')
            response = self.client.get(reverse('datasets:import_dataset', kwargs={'pk': self.dataset.pk}))
            self.assertEqual(response.status_code, 302)
            
            # Step 2: Process queue
            success = ETLPipelineManager.process_next_import()
            self.assertTrue(success)
            
            # Step 3: Verify results
            queue_entry = ImportQueue.objects.filter(
                dataset=self.dataset,
                requested_by=self.admin_user
            ).first()
            
            self.assertEqual(queue_entry.status, 'completed')
            dataset_import = queue_entry.dataset_import
            self.assertEqual(dataset_import.records_imported, 2)
            
        finally:
            os.unlink(csv_path)
    
    def test_complete_etl_workflow_json_file(self):
        """Test complete ETL workflow with JSON file."""
        # Create a temporary JSON file
        json_data = [
            {"name": "John", "age": 25, "city": "New York"},
            {"name": "Jane", "age": 30, "city": "Los Angeles"},
            {"name": "Bob", "age": 35, "city": "Chicago"}
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(json_data, f)
            json_path = f.name
        
        try:
            # Update version with file path
            self.version.file.name = json_path
            self.version.save()
            
            # Step 1: Queue import
            self.client.login(username='admin', password='testpass123')
            response = self.client.get(reverse('datasets:import_dataset', kwargs={'pk': self.dataset.pk}))
            self.assertEqual(response.status_code, 302)
            
            # Step 2: Process queue
            success = ETLPipelineManager.process_next_import()
            self.assertTrue(success)
            
            # Step 3: Verify results
            queue_entry = ImportQueue.objects.filter(
                dataset=self.dataset,
                requested_by=self.admin_user
            ).first()
            
            self.assertEqual(queue_entry.status, 'completed')
            dataset_import = queue_entry.dataset_import
            self.assertEqual(dataset_import.records_imported, 3)
            
        finally:
            os.unlink(json_path)
    
    def test_multiple_imports_queue_processing(self):
        """Test processing multiple imports in queue."""
        # Create multiple datasets
        dataset2 = Dataset.objects.create(
            title='Test Dataset 2',
            description='Second test dataset',
            owner=self.admin_user,
            status='published'
        )
        
        DatasetVersion.objects.create(
            dataset=dataset2,
            version_number=1,
            description='Second test version',
            is_current=True,
            created_by=self.admin_user
        )
        
        dataset3 = Dataset.objects.create(
            title='Test Dataset 3',
            description='Third test dataset',
            owner=self.admin_user,
            status='published'
        )
        
        DatasetVersion.objects.create(
            dataset=dataset3,
            version_number=1,
            description='Third test version',
            is_current=True,
            created_by=self.admin_user
        )
        
        # Queue multiple imports
        self.client.login(username='admin', password='testpass123')
        
        response1 = self.client.get(reverse('datasets:import_dataset', kwargs={'pk': self.dataset.pk}))
        response2 = self.client.get(reverse('datasets:import_dataset', kwargs={'pk': dataset2.pk}))
        response3 = self.client.get(reverse('datasets:import_dataset', kwargs={'pk': dataset3.pk}))
        
        self.assertEqual(response1.status_code, 302)
        self.assertEqual(response2.status_code, 302)
        self.assertEqual(response3.status_code, 302)
        
        # Verify all queue entries were created
        queue_entries = ImportQueue.objects.filter(
            requested_by=self.admin_user,
            status='pending'
        )
        self.assertEqual(queue_entries.count(), 3)
        
        # Process all imports
        processed_count = 0
        while ETLPipelineManager.process_next_import():
            processed_count += 1
            if processed_count > 10:  # Safety break
                break
        
        self.assertEqual(processed_count, 3)
        
        # Verify all imports were completed
        completed_imports = ImportQueue.objects.filter(
            requested_by=self.admin_user,
            status='completed'
        )
        self.assertEqual(completed_imports.count(), 3)
    
    def test_priority_based_processing(self):
        """Test that imports are processed by priority."""
        # Create multiple datasets with different priorities
        dataset2 = Dataset.objects.create(
            title='High Priority Dataset',
            description='High priority test dataset',
            owner=self.admin_user,
            status='published'
        )
        
        DatasetVersion.objects.create(
            dataset=dataset2,
            version_number=1,
            description='High priority version',
            is_current=True,
            created_by=self.admin_user
        )
        
        # Create queue entries with different priorities
        low_priority = ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.admin_user,
            status='pending',
            priority='low'
        )
        
        high_priority = ImportQueue.objects.create(
            dataset=dataset2,
            requested_by=self.admin_user,
            status='pending',
            priority='high'
        )
        
        # Process imports
        success = ETLPipelineManager.process_next_import()
        self.assertTrue(success)
        
        # Verify high priority was processed first
        high_priority.refresh_from_db()
        self.assertEqual(high_priority.status, 'completed')
        
        # Process next import
        success = ETLPipelineManager.process_next_import()
        self.assertTrue(success)
        
        # Verify low priority was processed second
        low_priority.refresh_from_db()
        self.assertEqual(low_priority.status, 'completed')
    
    def test_management_command_processing(self):
        """Test processing imports using management command."""
        # Queue an import
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('datasets:import_dataset', kwargs={'pk': self.dataset.pk}))
        self.assertEqual(response.status_code, 302)
        
        # Verify queue entry exists
        queue_entry = ImportQueue.objects.filter(
            dataset=self.dataset,
            requested_by=self.admin_user
        ).first()
        self.assertIsNotNone(queue_entry)
        self.assertEqual(queue_entry.status, 'pending')
        
        # Process using management command
        call_command('process_import_queue')
        
        # Verify import was processed
        queue_entry.refresh_from_db()
        self.assertEqual(queue_entry.status, 'completed')
    
    def test_management_command_continuous_mode(self):
        """Test continuous mode of management command."""
        # Queue an import
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('datasets:import_dataset', kwargs={'pk': self.dataset.pk}))
        self.assertEqual(response.status_code, 302)
        
        # Run continuous mode for a short time
        with patch('datasets.management.commands.process_import_queue.time.sleep') as mock_sleep:
            mock_sleep.side_effect = [None, KeyboardInterrupt()]  # Simulate interruption
            
            try:
                call_command('process_import_queue', '--continuous', '--max-runtime', '5')
            except KeyboardInterrupt:
                pass
        
        # Verify import was processed
        queue_entry = ImportQueue.objects.filter(
            dataset=self.dataset,
            requested_by=self.admin_user
        ).first()
        self.assertEqual(queue_entry.status, 'completed')
    
    def test_management_command_status(self):
        """Test queue status management command."""
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
            requested_by=self.admin_user,
            status='completed',
            priority='normal'
        )
        
        # Run status command
        call_command('import_queue_status')
        
        # This should not raise any exceptions
        # The command output is captured by Django's test framework
    
    def test_etl_pipeline_error_handling(self):
        """Test ETL pipeline error handling and recovery."""
        # Create a dataset without a version
        dataset_no_version = Dataset.objects.create(
            title='No Version Dataset',
            description='Dataset without version',
            owner=self.admin_user,
            status='published'
        )
        
        # Queue import for dataset without version
        queue_entry = ImportQueue.objects.create(
            dataset=dataset_no_version,
            requested_by=self.admin_user,
            status='pending',
            priority='normal'
        )
        
        # Process import (should fail)
        success = ETLPipelineManager.process_next_import()
        self.assertFalse(success)
        
        # Verify queue entry was marked as failed
        queue_entry.refresh_from_db()
        self.assertEqual(queue_entry.status, 'failed')
        self.assertIsNotNone(queue_entry.error_message)
        
        # Verify no DatasetImport was created
        dataset_import = DatasetImport.objects.filter(
            dataset=dataset_no_version,
            imported_by=self.admin_user
        ).first()
        self.assertIsNone(dataset_import)
    
    def test_concurrent_import_prevention(self):
        """Test that only one import processes at a time."""
        # Create two queue entries
        queue_entry1 = ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.admin_user,
            status='pending',
            priority='normal'
        )
        
        dataset2 = Dataset.objects.create(
            title='Second Dataset',
            description='Second test dataset',
            owner=self.admin_user,
            status='published'
        )
        
        DatasetVersion.objects.create(
            dataset=dataset2,
            version_number=1,
            description='Second version',
            is_current=True,
            created_by=self.admin_user
        )
        
        queue_entry2 = ImportQueue.objects.create(
            dataset=dataset2,
            requested_by=self.admin_user,
            status='pending',
            priority='normal'
        )
        
        # Process first import
        success = ETLPipelineManager.process_next_import()
        self.assertTrue(success)
        
        # Verify first import is processing or completed
        queue_entry1.refresh_from_db()
        self.assertIn(queue_entry1.status, ['processing', 'completed'])
        
        # Try to process second import
        success = ETLPipelineManager.process_next_import()
        
        if queue_entry1.status == 'processing':
            # If first is still processing, second should not be processed
            self.assertFalse(success)
            queue_entry2.refresh_from_db()
            self.assertEqual(queue_entry2.status, 'pending')
        else:
            # If first completed, second should be processed
            self.assertTrue(success)
            queue_entry2.refresh_from_db()
            self.assertIn(queue_entry2.status, ['processing', 'completed'])
    
    def test_queue_cleanup(self):
        """Test cleanup of old completed imports."""
        from datetime import timedelta
        
        # Create old completed import
        old_import = ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.admin_user,
            status='completed',
            priority='normal',
            completed_at=timezone.now() - timedelta(days=35)
        )
        
        # Create recent completed import
        recent_import = ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.editor_user,
            status='completed',
            priority='normal',
            completed_at=timezone.now() - timedelta(days=10)
        )
        
        # Run cleanup
        ETLPipelineManager.cleanup_old_imports(days=30)
        
        # Verify old import was deleted
        self.assertFalse(ImportQueue.objects.filter(id=old_import.id).exists())
        
        # Verify recent import was kept
        self.assertTrue(ImportQueue.objects.filter(id=recent_import.id).exists())
    
    @patch('datasets.etl_pipeline.connections')
    def test_import_database_integration(self, mock_connections):
        """Test integration with import database."""
        # Mock database connection
        mock_cursor = MagicMock()
        mock_connections.__getitem__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Queue and process import
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('datasets:import_dataset', kwargs={'pk': self.dataset.pk}))
        self.assertEqual(response.status_code, 302)
        
        success = ETLPipelineManager.process_next_import()
        self.assertTrue(success)
        
        # Verify database operations were called
        self.assertTrue(mock_cursor.execute.called)
        self.assertTrue(mock_cursor.executemany.called)
        
        # Verify queue entry was completed
        queue_entry = ImportQueue.objects.filter(
            dataset=self.dataset,
            requested_by=self.admin_user
        ).first()
        self.assertEqual(queue_entry.status, 'completed')
        
        # Verify DatasetImport was created
        dataset_import = queue_entry.dataset_import
        self.assertIsNotNone(dataset_import)
        self.assertEqual(dataset_import.status, 'completed')
        self.assertIsNotNone(dataset_import.import_database_table)
    
    def test_etl_pipeline_performance(self):
        """Test ETL pipeline performance with larger datasets."""
        # Create a larger JSON dataset
        large_data = []
        for i in range(100):
            large_data.append({
                "id": i,
                "name": f"User {i}",
                "email": f"user{i}@example.com",
                "age": 20 + (i % 50),
                "city": f"City {i % 10}"
            })
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(large_data, f)
            json_path = f.name
        
        try:
            # Update version with large file
            self.version.file.name = json_path
            self.version.save()
            
            # Queue and process import
            self.client.login(username='admin', password='testpass123')
            response = self.client.get(reverse('datasets:import_dataset', kwargs={'pk': self.dataset.pk}))
            self.assertEqual(response.status_code, 302)
            
            # Process import
            success = ETLPipelineManager.process_next_import()
            self.assertTrue(success)
            
            # Verify results
            queue_entry = ImportQueue.objects.filter(
                dataset=self.dataset,
                requested_by=self.admin_user
            ).first()
            
            self.assertEqual(queue_entry.status, 'completed')
            dataset_import = queue_entry.dataset_import
            self.assertEqual(dataset_import.records_imported, 100)
            
        finally:
            os.unlink(json_path)

