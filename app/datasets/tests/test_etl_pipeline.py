"""
Unit tests for ETL Pipeline functionality.
"""

import os
import tempfile
import json
import csv
from unittest.mock import patch, MagicMock, mock_open
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import connections

from datasets.models import Dataset, DatasetVersion, ImportQueue, DatasetImport
from datasets.etl_pipeline import (
    DatasetETLPipeline, 
    ETLPipelineManager, 
    ETLError, 
    ExtractionError, 
    TransformationError, 
    LoadingError
)

User = get_user_model()


class DatasetETLPipelineTestCase(TestCase):
    """Test cases for DatasetETLPipeline class."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.dataset = Dataset.objects.create(
            title='Test Dataset',
            description='Test dataset for ETL pipeline',
            owner=self.user,
            status='published'
        )
        
        self.version = DatasetVersion.objects.create(
            dataset=self.dataset,
            version_number=1,
            description='Test version',
            is_current=True,
            created_by=self.user
        )
        
        self.queue_entry = ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.user,
            status='pending',
            priority='normal'
        )
    
    def test_pipeline_initialization(self):
        """Test pipeline initialization."""
        pipeline = DatasetETLPipeline(self.queue_entry)
        
        self.assertEqual(pipeline.queue_entry, self.queue_entry)
        self.assertEqual(pipeline.dataset, self.dataset)
        self.assertEqual(pipeline.requested_by, self.user)
        self.assertIsNone(pipeline.extracted_data)
        self.assertIsNone(pipeline.transformed_data)
    
    def test_extract_basic_info(self):
        """Test basic info extraction."""
        pipeline = DatasetETLPipeline(self.queue_entry)
        extracted_data = pipeline._extract_basic_info(self.version)
        
        self.assertEqual(extracted_data['format'], 'basic')
        self.assertEqual(extracted_data['record_count'], 1)
        self.assertEqual(len(extracted_data['records']), 1)
        
        record = extracted_data['records'][0]
        self.assertEqual(record['dataset_id'], str(self.dataset.id))
        self.assertEqual(record['dataset_title'], self.dataset.title)
        self.assertEqual(record['version_number'], self.version.version_number)
    
    def test_extract_gdb(self):
        """Test File Geodatabase extraction."""
        # Create a temporary GDB file (mock)
        with tempfile.NamedTemporaryFile(suffix='.gdb', delete=False) as f:
            gdb_path = f.name
        
        try:
            pipeline = DatasetETLPipeline(self.queue_entry)
            
            # Mock geopandas import and functionality
            with patch('datasets.etl_pipeline.gpd') as mock_gpd:
                mock_layer_data = {
                    'layer1': type('MockDataFrame', (), {
                        'iterrows': lambda: [
                            (0, {'id': 1, 'name': 'Test', 'geometry': type('MockGeometry', (), {'wkt': 'POINT(0 0)'})()})
                        ]
                    })()
                }
                mock_gpd.read_file.return_value = mock_layer_data
                
                extracted_data = pipeline._extract_gdb(gdb_path)
                
                self.assertEqual(extracted_data['format'], 'gdb')
                self.assertEqual(extracted_data['record_count'], 1)
                self.assertIn('layers', extracted_data)
                
        finally:
            os.unlink(gdb_path)
    
    def test_extract_spatialite(self):
        """Test SpatiaLite extraction."""
        # Create a temporary SQLite file
        with tempfile.NamedTemporaryFile(suffix='.sqlite', delete=False) as f:
            sqlite_path = f.name
        
        try:
            import sqlite3
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.cursor()
            
            # Create a test table
            cursor.execute('CREATE TABLE test_table (id INTEGER, name TEXT)')
            cursor.execute('INSERT INTO test_table (id, name) VALUES (1, "Test")')
            conn.commit()
            conn.close()
            
            pipeline = DatasetETLPipeline(self.queue_entry)
            extracted_data = pipeline._extract_spatialite(sqlite_path)
            
            self.assertEqual(extracted_data['format'], 'spatialite')
            self.assertEqual(extracted_data['record_count'], 1)
            self.assertIn('tables', extracted_data)
            self.assertEqual(extracted_data['tables'], ['test_table'])
            
        finally:
            os.unlink(sqlite_path)
    
    def test_extract_geopackage(self):
        """Test GeoPackage extraction."""
        # Create a temporary GPKG file (mock)
        with tempfile.NamedTemporaryFile(suffix='.gpkg', delete=False) as f:
            gpkg_path = f.name
        
        try:
            pipeline = DatasetETLPipeline(self.queue_entry)
            
            # Mock geopandas import and functionality
            with patch('datasets.etl_pipeline.gpd') as mock_gpd:
                mock_layer_data = {
                    'layer1': type('MockDataFrame', (), {
                        'iterrows': lambda: [
                            (0, {'id': 1, 'name': 'Test', 'geometry': type('MockGeometry', (), {'wkt': 'POINT(0 0)'})()})
                        ]
                    })()
                }
                mock_gpd.read_file.return_value = mock_layer_data
                
                extracted_data = pipeline._extract_geopackage(gpkg_path)
                
                self.assertEqual(extracted_data['format'], 'gpkg')
                self.assertEqual(extracted_data['record_count'], 1)
                self.assertIn('layers', extracted_data)
                
        finally:
            os.unlink(gpkg_path)
    
    def test_extract_sql(self):
        """Test SQL file extraction."""
        # Create a temporary SQL file
        sql_content = "CREATE TABLE test (id INT, name VARCHAR(100));\nINSERT INTO test VALUES (1, 'Test');"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as f:
            f.write(sql_content)
            sql_path = f.name
        
        try:
            pipeline = DatasetETLPipeline(self.queue_entry)
            extracted_data = pipeline._extract_sql(sql_path)
            
            self.assertEqual(extracted_data['format'], 'sql')
            self.assertEqual(extracted_data['record_count'], 1)
            self.assertEqual(extracted_data['sql_type'], 'script')
            
            record = extracted_data['records'][0]
            self.assertEqual(record['sql_content'], sql_content)
            self.assertEqual(record['sql_type'], 'script')
            
        finally:
            os.unlink(sql_path)
    
    def test_extract_csv(self):
        """Test CSV file extraction."""
        # Create a temporary CSV file
        csv_content = "name,age,city\nJohn,25,New York\nJane,30,Los Angeles"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            csv_path = f.name
        
        try:
            pipeline = DatasetETLPipeline(self.queue_entry)
            extracted_data = pipeline._extract_csv(csv_path)
            
            self.assertEqual(extracted_data['format'], 'csv')
            self.assertEqual(extracted_data['record_count'], 2)
            self.assertEqual(len(extracted_data['records']), 2)
            self.assertEqual(extracted_data['columns'], ['name', 'age', 'city'])
            
            # Check first record
            self.assertEqual(extracted_data['records'][0]['name'], 'John')
            self.assertEqual(extracted_data['records'][0]['age'], '25')
            self.assertEqual(extracted_data['records'][0]['city'], 'New York')
            
        finally:
            os.unlink(csv_path)
    
    def test_extract_json(self):
        """Test JSON file extraction."""
        # Create a temporary JSON file
        json_data = [
            {"name": "John", "age": 25, "city": "New York"},
            {"name": "Jane", "age": 30, "city": "Los Angeles"}
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(json_data, f)
            json_path = f.name
        
        try:
            pipeline = DatasetETLPipeline(self.queue_entry)
            extracted_data = pipeline._extract_json(json_path)
            
            self.assertEqual(extracted_data['format'], 'json')
            self.assertEqual(extracted_data['record_count'], 2)
            self.assertEqual(len(extracted_data['records']), 2)
            
            # Check first record
            self.assertEqual(extracted_data['records'][0]['name'], 'John')
            self.assertEqual(extracted_data['records'][0]['age'], 25)
            
        finally:
            os.unlink(json_path)
    
    def test_extract_geojson(self):
        """Test GeoJSON file extraction."""
        # Create a temporary GeoJSON file
        geojson_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [0, 0]},
                    "properties": {"name": "Test Point"}
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.geojson', delete=False) as f:
            json.dump(geojson_data, f)
            geojson_path = f.name
        
        try:
            pipeline = DatasetETLPipeline(self.queue_entry)
            extracted_data = pipeline._extract_json(geojson_path)
            
            self.assertEqual(extracted_data['format'], 'geojson')
            self.assertEqual(extracted_data['record_count'], 1)
            self.assertEqual(extracted_data['geometry_type'], 'Point')
            
        finally:
            os.unlink(geojson_path)
    
    def test_clean_column_name(self):
        """Test column name cleaning."""
        pipeline = DatasetETLPipeline(self.queue_entry)
        
        # Test various column names
        test_cases = [
            ('User Name', 'user_name'),
            ('Email@Address', 'email_address'),
            ('123Number', '_123number'),
            ('Special!@#$%', 'special'),
            ('Multiple___Underscores', 'multiple_underscores'),
            ('', 'column'),
            ('UPPERCASE', 'uppercase'),
        ]
        
        for input_name, expected in test_cases:
            result = pipeline._clean_column_name(input_name)
            self.assertEqual(result, expected, f"Failed for input: {input_name}")
    
    def test_clean_value(self):
        """Test value cleaning."""
        pipeline = DatasetETLPipeline(self.queue_entry)
        
        # Test various value types
        test_cases = [
            ('true', True),
            ('false', False),
            ('123', 123),
            ('123.45', 123.45),
            ('  spaced  ', 'spaced'),
            ('', None),
            (None, None),
            ('normal text', 'normal text'),
        ]
        
        for input_value, expected in test_cases:
            result = pipeline._clean_value(input_value)
            self.assertEqual(result, expected, f"Failed for input: {input_value}")
    
    def test_transform_tabular_data(self):
        """Test tabular data transformation."""
        pipeline = DatasetETLPipeline(self.queue_entry)
        
        # Set up extracted data
        pipeline.extracted_data = {
            'format': 'csv',
            'records': [
                {'Name': 'John', 'Age': '25', 'City': 'New York'},
                {'Name': 'Jane', 'Age': '30', 'City': 'Los Angeles'}
            ],
            'columns': ['Name', 'Age', 'City']
        }
        
        transformed_data = pipeline._transform_tabular_data()
        
        self.assertEqual(transformed_data['format'], 'transformed_tabular')
        self.assertEqual(len(transformed_data['records']), 2)
        
        # Check first transformed record
        record = transformed_data['records'][0]
        self.assertEqual(record['name'], 'John')  # Column name cleaned
        self.assertEqual(record['age'], 25)  # Value cleaned
        self.assertEqual(record['city'], 'New York')
        self.assertEqual(record['_dataset_id'], str(self.dataset.id))
        self.assertEqual(record['_imported_by'], self.user.username)
    
    def test_transform_json_data(self):
        """Test JSON data transformation."""
        pipeline = DatasetETLPipeline(self.queue_entry)
        
        # Set up extracted data
        pipeline.extracted_data = {
            'format': 'json',
            'records': [
                {'name': 'John', 'age': 25, 'city': 'New York'},
                {'name': 'Jane', 'age': 30, 'city': 'Los Angeles'}
            ]
        }
        
        transformed_data = pipeline._transform_json_data()
        
        self.assertEqual(transformed_data['format'], 'transformed_json')
        self.assertEqual(len(transformed_data['records']), 2)
        
        # Check first transformed record
        record = transformed_data['records'][0]
        self.assertEqual(record['name'], 'John')
        self.assertEqual(record['age'], 25)
        self.assertEqual(record['_dataset_id'], str(self.dataset.id))
        self.assertEqual(record['_imported_by'], self.user.username)
    
    def test_transform_geospatial_data(self):
        """Test geospatial data transformation."""
        pipeline = DatasetETLPipeline(self.queue_entry)
        
        # Set up extracted data for GDB
        pipeline.extracted_data = {
            'format': 'gdb',
            'records': [
                {'id': 1, 'name': 'Test', 'geometry_wkt': 'POINT(0 0)', '_layer_name': 'layer1'},
                {'id': 2, 'name': 'Test2', 'geometry_wkt': 'POINT(1 1)', '_layer_name': 'layer1'}
            ],
            'layers': ['layer1']
        }
        
        transformed_data = pipeline._transform_geospatial_data()
        
        self.assertEqual(transformed_data['format'], 'transformed_geospatial')
        self.assertEqual(len(transformed_data['records']), 2)
        self.assertEqual(transformed_data['source_format'], 'gdb')
        self.assertEqual(transformed_data['layers'], ['layer1'])
        
        # Check first transformed record
        record = transformed_data['records'][0]
        self.assertEqual(record['id'], 1)
        self.assertEqual(record['name'], 'Test')
        self.assertEqual(record['geometry_wkt'], 'POINT(0 0)')
        self.assertEqual(record['_source_format'], 'File Geodatabase')
        self.assertEqual(record['_layer_name'], 'layer1')
        self.assertEqual(record['_dataset_id'], str(self.dataset.id))
        self.assertEqual(record['_imported_by'], self.user.username)
    
    def test_transform_sql_data(self):
        """Test SQL data transformation."""
        pipeline = DatasetETLPipeline(self.queue_entry)
        
        # Set up extracted data
        pipeline.extracted_data = {
            'format': 'sql',
            'records': [
                {
                    'sql_content': 'CREATE TABLE test (id INT, name VARCHAR(100));',
                    'file_name': 'test.sql',
                    'file_size': 100,
                    'sql_type': 'script'
                }
            ],
            'sql_type': 'script'
        }
        
        transformed_data = pipeline._transform_sql_data()
        
        self.assertEqual(transformed_data['format'], 'transformed_sql')
        self.assertEqual(len(transformed_data['records']), 1)
        self.assertEqual(transformed_data['sql_type'], 'script')
        
        # Check transformed record
        record = transformed_data['records'][0]
        self.assertEqual(record['sql_content'], 'CREATE TABLE test (id INT, name VARCHAR(100));')
        self.assertEqual(record['file_name'], 'test.sql')
        self.assertEqual(record['_source_format'], 'SQL Script')
        self.assertEqual(record['_dataset_id'], str(self.dataset.id))
        self.assertEqual(record['_imported_by'], self.user.username)
    
    def test_extract_no_current_version(self):
        """Test extraction when no current version exists."""
        # Remove current version
        self.version.is_current = False
        self.version.save()
        
        pipeline = DatasetETLPipeline(self.queue_entry)
        
        with self.assertRaises(ExtractionError):
            pipeline._extract()
    
    def test_extract_with_file(self):
        """Test extraction with file."""
        # Create a temporary CSV file
        csv_content = "name,age\nJohn,25\nJane,30"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            csv_path = f.name
        
        try:
            # Mock the version file to point to our test file
            mock_file = MagicMock()
            mock_file.path = csv_path
            
            with patch.object(self.version, 'file', mock_file):
                pipeline = DatasetETLPipeline(self.queue_entry)
                pipeline._extract()
                
                # Verify that data was extracted
                self.assertIsNotNone(pipeline.extracted_data)
                self.assertEqual(pipeline.extracted_data['format'], 'csv')
                
        finally:
            os.unlink(csv_path)
    
    def test_extract_with_url(self):
        """Test extraction with URL."""
        self.version.file_url = 'https://example.com/data.csv'
        self.version.save()
        
        pipeline = DatasetETLPipeline(self.queue_entry)
        with patch.object(pipeline, '_extract_from_url') as mock_extract_url:
            mock_extract_url.return_value = {'format': 'url', 'records': []}
            
            pipeline._extract()
            
            mock_extract_url.assert_called_once_with(self.version)
    
    def test_extract_without_file_or_url(self):
        """Test extraction without file or URL."""
        pipeline = DatasetETLPipeline(self.queue_entry)
        pipeline._extract()
        
        self.assertEqual(pipeline.extracted_data['format'], 'basic')
        self.assertEqual(len(pipeline.extracted_data['records']), 1)
    
    @patch('datasets.etl_pipeline.connections')
    def test_create_import_table(self, mock_connections):
        """Test import table creation."""
        # Mock database connection
        mock_cursor = MagicMock()
        mock_connections.__getitem__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        pipeline = DatasetETLPipeline(self.queue_entry)
        pipeline.transformed_data = {
            'records': [
                {'name': 'John', 'age': 25, '_dataset_id': str(self.dataset.id)}
            ]
        }
        
        pipeline._create_import_table('test_table')
        
        # Verify CREATE TABLE was called
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args[0][0]
        self.assertIn('CREATE TABLE IF NOT EXISTS "test_table"', call_args)
        self.assertIn('"name" TEXT', call_args)
        self.assertIn('"age" TEXT', call_args)
        self.assertIn('id SERIAL PRIMARY KEY', call_args)
    
    @patch('datasets.etl_pipeline.connections')
    def test_insert_data(self, mock_connections):
        """Test data insertion."""
        # Mock database connection
        mock_cursor = MagicMock()
        mock_connections.__getitem__.return_value.cursor.return_value.__enter__.return_value = mock_cursor
        
        pipeline = DatasetETLPipeline(self.queue_entry)
        pipeline.transformed_data = {
            'records': [
                {'name': 'John', 'age': 25},
                {'name': 'Jane', 'age': 30}
            ]
        }
        
        pipeline._insert_data('test_table')
        
        # Verify INSERT was called
        mock_cursor.executemany.assert_called_once()
        call_args = mock_cursor.executemany.call_args
        self.assertIn('INSERT INTO "test_table"', call_args[0][0])
        self.assertEqual(len(call_args[0][1]), 2)  # Two records
    
    def test_create_dataset_import_record(self):
        """Test DatasetImport record creation."""
        pipeline = DatasetETLPipeline(self.queue_entry)
        pipeline.transformed_data = {
            'records': [{'name': 'John'}, {'name': 'Jane'}]
        }
        
        pipeline._create_dataset_import_record('test_table')
        
        # Check that DatasetImport was created
        dataset_import = DatasetImport.objects.get(dataset=self.dataset, imported_by=self.user)
        self.assertEqual(dataset_import.status, 'completed')
        self.assertEqual(dataset_import.import_database_table, 'test_table')
        self.assertEqual(dataset_import.records_imported, 2)
        
        # Check that queue entry was linked
        self.queue_entry.refresh_from_db()
        self.assertEqual(self.queue_entry.dataset_import, dataset_import)
    
    def test_update_queue_status(self):
        """Test queue status updates."""
        pipeline = DatasetETLPipeline(self.queue_entry)
        
        # Test processing status
        pipeline._update_queue_status('processing')
        self.queue_entry.refresh_from_db()
        self.assertEqual(self.queue_entry.status, 'processing')
        self.assertIsNotNone(self.queue_entry.started_at)
        
        # Test completed status
        pipeline._update_queue_status('completed')
        self.queue_entry.refresh_from_db()
        self.assertEqual(self.queue_entry.status, 'completed')
        self.assertIsNotNone(self.queue_entry.completed_at)
        
        # Test failed status with error
        pipeline._update_queue_status('failed', 'Test error')
        self.queue_entry.refresh_from_db()
        self.assertEqual(self.queue_entry.status, 'failed')
        self.assertEqual(self.queue_entry.error_message, 'Test error')
    
    @patch('datasets.etl_pipeline.transaction')
    def test_execute_success(self, mock_transaction):
        """Test successful pipeline execution."""
        pipeline = DatasetETLPipeline(self.queue_entry)
        
        with patch.object(pipeline, '_extract'), \
             patch.object(pipeline, '_transform'), \
             patch.object(pipeline, '_load'):
            
            result = pipeline.execute()
            
            self.assertTrue(result)
            self.queue_entry.refresh_from_db()
            self.assertEqual(self.queue_entry.status, 'completed')
    
    def test_execute_extraction_error(self):
        """Test pipeline execution with extraction error."""
        pipeline = DatasetETLPipeline(self.queue_entry)
        
        with patch.object(pipeline, '_extract', side_effect=ExtractionError("Extraction failed")):
            result = pipeline.execute()
            
            self.assertFalse(result)
            self.queue_entry.refresh_from_db()
            self.assertEqual(self.queue_entry.status, 'failed')
            self.assertIn('Extraction failed', self.queue_entry.error_message)
    
    def test_execute_transformation_error(self):
        """Test pipeline execution with transformation error."""
        pipeline = DatasetETLPipeline(self.queue_entry)
        
        with patch.object(pipeline, '_extract'), \
             patch.object(pipeline, '_transform', side_effect=TransformationError("Transformation failed")):
            
            result = pipeline.execute()
            
            self.assertFalse(result)
            self.queue_entry.refresh_from_db()
            self.assertEqual(self.queue_entry.status, 'failed')
            self.assertIn('Transformation failed', self.queue_entry.error_message)
    
    def test_execute_loading_error(self):
        """Test pipeline execution with loading error."""
        pipeline = DatasetETLPipeline(self.queue_entry)
        
        with patch.object(pipeline, '_extract'), \
             patch.object(pipeline, '_transform'), \
             patch.object(pipeline, '_load', side_effect=LoadingError("Loading failed")):
            
            result = pipeline.execute()
            
            self.assertFalse(result)
            self.queue_entry.refresh_from_db()
            self.assertEqual(self.queue_entry.status, 'failed')
            self.assertIn('Loading failed', self.queue_entry.error_message)
    
    def test_execute_unexpected_error(self):
        """Test pipeline execution with unexpected error."""
        pipeline = DatasetETLPipeline(self.queue_entry)
        
        with patch.object(pipeline, '_extract', side_effect=Exception("Unexpected error")):
            result = pipeline.execute()
            
            self.assertFalse(result)
            self.queue_entry.refresh_from_db()
            self.assertEqual(self.queue_entry.status, 'failed')
            self.assertIn('Unexpected error', self.queue_entry.error_message)


class ETLPipelineManagerTestCase(TestCase):
    """Test cases for ETLPipelineManager class."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.dataset = Dataset.objects.create(
            title='Test Dataset',
            description='Test dataset for ETL pipeline',
            owner=self.user,
            status='published'
        )
        
        self.version = DatasetVersion.objects.create(
            dataset=self.dataset,
            version_number=1,
            description='Test version',
            is_current=True,
            created_by=self.user
        )
    
    def test_process_next_import_no_queue(self):
        """Test processing when no imports are in queue."""
        result = ETLPipelineManager.process_next_import()
        self.assertFalse(result)
    
    def test_process_next_import_already_processing(self):
        """Test processing when import is already in progress."""
        # Create a processing import
        ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.user,
            status='processing',
            priority='normal'
        )
        
        result = ETLPipelineManager.process_next_import()
        self.assertFalse(result)
    
    @patch('datasets.etl_pipeline.DatasetETLPipeline')
    def test_process_next_import_success(self, mock_pipeline_class):
        """Test successful import processing."""
        # Create a pending import
        queue_entry = ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.user,
            status='pending',
            priority='normal'
        )
        
        # Mock successful pipeline execution
        mock_pipeline = MagicMock()
        mock_pipeline.execute.return_value = True
        mock_pipeline_class.return_value = mock_pipeline
        
        result = ETLPipelineManager.process_next_import()
        
        self.assertTrue(result)
        mock_pipeline_class.assert_called_once_with(queue_entry)
        mock_pipeline.execute.assert_called_once()
    
    @patch('datasets.etl_pipeline.DatasetETLPipeline')
    def test_process_next_import_failure(self, mock_pipeline_class):
        """Test failed import processing."""
        # Create a pending import
        queue_entry = ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.user,
            status='pending',
            priority='normal'
        )
        
        # Mock failed pipeline execution
        mock_pipeline = MagicMock()
        mock_pipeline.execute.return_value = False
        mock_pipeline_class.return_value = mock_pipeline
        
        result = ETLPipelineManager.process_next_import()
        
        self.assertFalse(result)
        mock_pipeline_class.assert_called_once_with(queue_entry)
        mock_pipeline.execute.assert_called_once()
    
    def test_get_queue_status(self):
        """Test queue status retrieval."""
        # Create various queue entries
        ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.user,
            status='pending',
            priority='normal'
        )
        ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.user,
            status='processing',
            priority='high'
        )
        ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.user,
            status='completed',
            priority='normal'
        )
        ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.user,
            status='failed',
            priority='low'
        )
        
        stats = ETLPipelineManager.get_queue_status()
        
        self.assertEqual(stats['pending'], 1)
        self.assertEqual(stats['processing'], 1)
        self.assertEqual(stats['completed'], 1)
        self.assertEqual(stats['failed'], 1)
        self.assertEqual(stats['total'], 4)
    
    def test_cleanup_old_imports(self):
        """Test cleanup of old imports."""
        from datetime import timedelta
        
        # Create additional dataset for testing
        dataset2 = Dataset.objects.create(
            title='Test Dataset 2',
            description='Second test dataset',
            owner=self.user,
            status='published'
        )
        
        # Create old completed import
        old_import = ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.user,
            status='completed',
            priority='normal'
        )
        old_import.completed_at = timezone.now() - timedelta(days=35)
        old_import.save()
        
        # Create recent completed import
        recent_import = ImportQueue.objects.create(
            dataset=dataset2,
            requested_by=self.user,
            status='completed',
            priority='normal'
        )
        recent_import.completed_at = timezone.now() - timedelta(days=10)
        recent_import.save()
        
        # Run cleanup
        ETLPipelineManager.cleanup_old_imports(days=30)
        
        # Check that only old import was deleted
        self.assertFalse(ImportQueue.objects.filter(id=old_import.id).exists())
        self.assertTrue(ImportQueue.objects.filter(id=recent_import.id).exists())


class ImportQueueModelTestCase(TestCase):
    """Test cases for ImportQueue model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.dataset = Dataset.objects.create(
            title='Test Dataset',
            description='Test dataset for ETL pipeline',
            owner=self.user,
            status='published'
        )
    
    def test_create_import_queue_entry(self):
        """Test creating import queue entry."""
        queue_entry = ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.user,
            status='pending',
            priority='normal'
        )
        
        self.assertEqual(queue_entry.dataset, self.dataset)
        self.assertEqual(queue_entry.requested_by, self.user)
        self.assertEqual(queue_entry.status, 'pending')
        self.assertEqual(queue_entry.priority, 'normal')
        self.assertIsNotNone(queue_entry.created_at)
    
    def test_import_queue_properties(self):
        """Test import queue properties."""
        queue_entry = ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.user,
            status='pending',
            priority='normal'
        )
        
        # Test pending
        self.assertTrue(queue_entry.is_pending)
        self.assertFalse(queue_entry.is_processing)
        self.assertFalse(queue_entry.is_completed)
        self.assertFalse(queue_entry.is_failed)
        
        # Test processing
        queue_entry.status = 'processing'
        queue_entry.started_at = timezone.now()
        queue_entry.save()
        
        self.assertFalse(queue_entry.is_pending)
        self.assertTrue(queue_entry.is_processing)
        self.assertFalse(queue_entry.is_completed)
        self.assertFalse(queue_entry.is_failed)
        
        # Test completed
        queue_entry.status = 'completed'
        queue_entry.completed_at = timezone.now()
        queue_entry.save()
        
        self.assertFalse(queue_entry.is_pending)
        self.assertFalse(queue_entry.is_processing)
        self.assertTrue(queue_entry.is_completed)
        self.assertFalse(queue_entry.is_failed)
        
        # Test failed
        queue_entry.status = 'failed'
        queue_entry.save()
        
        self.assertFalse(queue_entry.is_pending)
        self.assertFalse(queue_entry.is_processing)
        self.assertFalse(queue_entry.is_completed)
        self.assertTrue(queue_entry.is_failed)
    
    def test_processing_time_calculation(self):
        """Test processing time calculation."""
        queue_entry = ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.user,
            status='processing',
            priority='normal',
            started_at=timezone.now()
        )
        
        # Test processing time while in progress
        processing_time = queue_entry.processing_time
        self.assertIsNotNone(processing_time)
        self.assertGreater(processing_time.total_seconds(), 0)
        
        # Test processing time after completion
        queue_entry.status = 'completed'
        queue_entry.completed_at = timezone.now()
        queue_entry.save()
        
        processing_time = queue_entry.processing_time
        self.assertIsNotNone(processing_time)
        self.assertGreaterEqual(processing_time.total_seconds(), 0)
    
    def test_get_next_import(self):
        """Test getting next import to process."""
        # Create additional datasets for testing
        dataset2 = Dataset.objects.create(
            title='Test Dataset 2',
            description='Second test dataset',
            owner=self.user,
            status='published'
        )
        
        dataset3 = Dataset.objects.create(
            title='Test Dataset 3',
            description='Third test dataset',
            owner=self.user,
            status='published'
        )
        
        # Create imports with different priorities
        low_priority = ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.user,
            status='pending',
            priority='low'
        )
        
        high_priority = ImportQueue.objects.create(
            dataset=dataset2,
            requested_by=self.user,
            status='pending',
            priority='high'
        )
        
        normal_priority = ImportQueue.objects.create(
            dataset=dataset3,
            requested_by=self.user,
            status='pending',
            priority='normal'
        )
        
        # Should return high priority first (priority order: urgent > high > normal > low)
        next_import = ImportQueue.get_next_import()
        # Check that it's a high priority import (could be either dataset2 or dataset3 depending on creation order)
        self.assertEqual(next_import.priority, 'high')
        
        # Mark high priority as processing
        high_priority.status = 'processing'
        high_priority.save()
        
        # Should return normal priority next
        next_import = ImportQueue.get_next_import()
        self.assertEqual(next_import, normal_priority)
    
    def test_is_processing_import(self):
        """Test checking if any import is processing."""
        # Initially no imports are processing
        self.assertFalse(ImportQueue.is_processing_import())
        
        # Create a processing import
        ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.user,
            status='processing',
            priority='normal'
        )
        
        # Should return True
        self.assertTrue(ImportQueue.is_processing_import())
        
        # Mark as completed
        processing_import = ImportQueue.objects.get(status='processing')
        processing_import.status = 'completed'
        processing_import.save()
        
        # Should return False
        self.assertFalse(ImportQueue.is_processing_import())
    
    def test_import_queue_ordering(self):
        """Test import queue ordering by priority and creation time."""
        # Create additional datasets for testing
        dataset2 = Dataset.objects.create(
            title='Test Dataset 2',
            description='Second test dataset',
            owner=self.user,
            status='published'
        )
        
        dataset3 = Dataset.objects.create(
            title='Test Dataset 3',
            description='Third test dataset',
            owner=self.user,
            status='published'
        )
        
        dataset4 = Dataset.objects.create(
            title='Test Dataset 4',
            description='Fourth test dataset',
            owner=self.user,
            status='published'
        )
        
        # Create imports in different order
        normal1 = ImportQueue.objects.create(
            dataset=self.dataset,
            requested_by=self.user,
            status='pending',
            priority='normal'
        )
        
        high = ImportQueue.objects.create(
            dataset=dataset2,
            requested_by=self.user,
            status='pending',
            priority='high'
        )
        
        normal2 = ImportQueue.objects.create(
            dataset=dataset3,
            requested_by=self.user,
            status='pending',
            priority='normal'
        )
        
        low = ImportQueue.objects.create(
            dataset=dataset4,
            requested_by=self.user,
            status='pending',
            priority='low'
        )
        
        # Get all pending imports
        pending_imports = list(ImportQueue.objects.filter(status='pending'))
        
        # Should be ordered by priority (high, normal, low) then by creation time
        self.assertEqual(pending_imports[0].priority, 'high')  # High priority first
        self.assertEqual(pending_imports[1].priority, 'normal')  # Normal priority second
        self.assertEqual(pending_imports[2].priority, 'normal')  # Normal priority third
        self.assertEqual(pending_imports[3].priority, 'low')  # Low priority last
        
        # Within same priority, should be ordered by creation time
        normal_priority_imports = [p for p in pending_imports if p.priority == 'normal']
        self.assertEqual(normal_priority_imports[0], normal1)  # Older first
        self.assertEqual(normal_priority_imports[1], normal2)  # Newer second
