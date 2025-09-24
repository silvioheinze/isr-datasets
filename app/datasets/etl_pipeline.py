"""
ETL Pipeline for Dataset Imports

This module contains the Extract, Transform, Load (ETL) pipeline classes
for importing datasets into the import database.
"""

import logging
import os
import tempfile
from typing import Dict, Any, Optional, List
from django.db import connections, transaction
from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from .models import Dataset, DatasetVersion, DatasetImport, ImportQueue

logger = logging.getLogger(__name__)


class ETLError(Exception):
    """Base exception for ETL pipeline errors"""
    pass


class ExtractionError(ETLError):
    """Error during data extraction"""
    pass


class TransformationError(ETLError):
    """Error during data transformation"""
    pass


class LoadingError(ETLError):
    """Error during data loading"""
    pass


class DatasetETLPipeline:
    """
    ETL Pipeline for importing datasets to the import database.
    
    This pipeline handles:
    1. Extract: Retrieving data from dataset files
    2. Transform: Processing and cleaning the data
    3. Load: Loading data into the import database
    """
    
    def __init__(self, queue_entry: ImportQueue):
        """
        Initialize the ETL pipeline with a queue entry.
        
        Args:
            queue_entry: The ImportQueue entry to process
        """
        self.queue_entry = queue_entry
        self.dataset = queue_entry.dataset
        self.requested_by = queue_entry.requested_by
        self.logger = logger
        self.import_db = connections['import']
        self.extracted_data = None
        self.transformed_data = None
        
    def execute(self) -> bool:
        """
        Execute the complete ETL pipeline.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info(f"Starting ETL pipeline for dataset: {self.dataset.title}")
            
            # Update queue status to processing
            self._update_queue_status('processing')
            
            # Execute ETL steps
            self._extract()
            self._transform()
            self._load()
            
            # Mark as completed
            self._update_queue_status('completed')
            self.logger.info(f"ETL pipeline completed successfully for dataset: {self.dataset.title}")
            
            return True
            
        except ETLError as e:
            self.logger.error(f"ETL pipeline failed for dataset {self.dataset.title}: {str(e)}")
            self._update_queue_status('failed', str(e))
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error in ETL pipeline for dataset {self.dataset.title}: {str(e)}")
            self._update_queue_status('failed', f"Unexpected error: {str(e)}")
            return False
    
    def _extract(self):
        """Extract data from dataset files"""
        self.logger.info(f"Extracting data for dataset: {self.dataset.title}")
        
        # Get the latest version of the dataset
        latest_version = self.dataset.versions.filter(is_current=True).first()
        if not latest_version:
            raise ExtractionError("No current version found for dataset")
        
        # Extract data based on file type
        if latest_version.file:
            self.extracted_data = self._extract_from_file(latest_version)
        elif latest_version.file_url:
            self.extracted_data = self._extract_from_url(latest_version)
        else:
            # Use basic info extraction for versions without files
            self.extracted_data = self._extract_basic_info(latest_version)
        
        self.logger.info(f"Extracted {len(self.extracted_data.get('records', []))} records from dataset")
    
    def _extract_from_file(self, version: DatasetVersion) -> Dict[str, Any]:
        """Extract data from uploaded file"""
        try:
            file_path = version.file.path
            file_extension = os.path.splitext(file_path)[1].lower()
            
            if file_extension in ['.csv']:
                return self._extract_csv(file_path)
            elif file_extension in ['.json', '.geojson']:
                return self._extract_json(file_path)
            elif file_extension in ['.xlsx', '.xls']:
                return self._extract_excel(file_path)
            elif file_extension in ['.gdb']:
                return self._extract_gdb(file_path)
            elif file_extension in ['.sqlite']:
                return self._extract_spatialite(file_path)
            elif file_extension in ['.gpkg']:
                return self._extract_geopackage(file_path)
            elif file_extension in ['.sql']:
                return self._extract_sql(file_path)
            else:
                # For unsupported formats, create a basic record
                return self._extract_basic_info(version)
                
        except Exception as e:
            raise ExtractionError(f"Failed to extract from file: {str(e)}")
    
    def _extract_from_url(self, version: DatasetVersion) -> Dict[str, Any]:
        """Extract data from external URL"""
        try:
            # For now, create basic info from URL
            # In a real implementation, you would download and process the URL
            return self._extract_basic_info(version)
            
        except Exception as e:
            raise ExtractionError(f"Failed to extract from URL: {str(e)}")
    
    def _extract_csv(self, file_path: str) -> Dict[str, Any]:
        """Extract data from CSV file"""
        import csv
        
        records = []
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                records.append(row)
        
        return {
            'format': 'csv',
            'records': records,
            'columns': list(records[0].keys()) if records else [],
            'record_count': len(records)
        }
    
    def _extract_json(self, file_path: str) -> Dict[str, Any]:
        """Extract data from JSON/GeoJSON file"""
        import json
        
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        # Handle GeoJSON format
        if isinstance(data, dict) and data.get('type') == 'FeatureCollection':
            records = data.get('features', [])
            return {
                'format': 'geojson',
                'records': records,
                'record_count': len(records),
                'geometry_type': records[0].get('geometry', {}).get('type') if records else None
            }
        else:
            # Handle regular JSON
            if isinstance(data, list):
                records = data
            else:
                records = [data]
            
            return {
                'format': 'json',
                'records': records,
                'record_count': len(records)
            }
    
    def _extract_excel(self, file_path: str) -> Dict[str, Any]:
        """Extract data from Excel file"""
        import pandas as pd
        
        try:
            df = pd.read_excel(file_path)
            records = df.to_dict('records')
            
            return {
                'format': 'excel',
                'records': records,
                'columns': list(df.columns),
                'record_count': len(records)
            }
        except ImportError:
            raise ExtractionError("pandas library required for Excel processing")
    
    def _extract_basic_info(self, version: DatasetVersion) -> Dict[str, Any]:
        """Extract basic information for unsupported formats"""
        return {
            'format': 'basic',
            'records': [{
                'dataset_id': str(self.dataset.id),
                'dataset_title': self.dataset.title,
                'version_number': version.version_number,
                'file_name': version.file.name if version.file else 'external_url',
                'file_url': version.file_url,
                'description': version.description or '',
                'version_created_at': version.created_at.isoformat(),
                'created_by': version.created_by.username if version.created_by else 'system'
            }],
            'record_count': 1
        }
    
    def _extract_gdb(self, file_path: str) -> Dict[str, Any]:
        """Extract data from File Geodatabase (.gdb)"""
        try:
            import geopandas as gpd
            
            # Read all layers from the GDB
            layers = gpd.read_file(file_path, driver='OpenFileGDB')
            records = []
            
            for layer_name, layer_data in layers.items():
                # Convert to records
                for idx, row in layer_data.iterrows():
                    record = row.to_dict()
                    record['_layer_name'] = layer_name
                    # Convert geometry to WKT if present
                    if 'geometry' in record and record['geometry'] is not None:
                        record['geometry_wkt'] = record['geometry'].wkt
                        del record['geometry']  # Remove geometry object
                    records.append(record)
            
            return {
                'format': 'gdb',
                'records': records,
                'record_count': len(records),
                'layers': list(layers.keys())
            }
            
        except ImportError:
            # Fallback if geopandas is not available
            return self._extract_basic_info_from_path(file_path, 'gdb')
        except Exception as e:
            self.logger.warning(f"Failed to extract from GDB: {str(e)}")
            return self._extract_basic_info_from_path(file_path, 'gdb')
    
    def _extract_spatialite(self, file_path: str) -> Dict[str, Any]:
        """Extract data from SpatiaLite database (.sqlite)"""
        try:
            import sqlite3
            import json
            
            records = []
            conn = sqlite3.connect(file_path)
            cursor = conn.cursor()
            
            # Get list of tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
                # Get table schema
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in cursor.fetchall()]
                
                # Get data from table
                cursor.execute(f"SELECT * FROM {table}")
                rows = cursor.fetchall()
                
                for row in rows:
                    record = dict(zip(columns, row))
                    record['_table_name'] = table
                    # Convert geometry to WKT if present
                    if 'geometry' in record and record['geometry'] is not None:
                        try:
                            # Try to get WKT from geometry blob
                            cursor.execute(f"SELECT AsText(geometry) FROM {table} WHERE rowid = ?", (row[0],))
                            wkt_result = cursor.fetchone()
                            if wkt_result:
                                record['geometry_wkt'] = wkt_result[0]
                        except:
                            pass
                    records.append(record)
            
            conn.close()
            
            return {
                'format': 'spatialite',
                'records': records,
                'record_count': len(records),
                'tables': tables
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to extract from SpatiaLite: {str(e)}")
            return self._extract_basic_info_from_path(file_path, 'spatialite')
    
    def _extract_geopackage(self, file_path: str) -> Dict[str, Any]:
        """Extract data from GeoPackage (.gpkg)"""
        try:
            import geopandas as gpd
            
            # Read all layers from the GeoPackage
            layers = gpd.read_file(file_path, driver='GPKG')
            records = []
            
            for layer_name, layer_data in layers.items():
                # Convert to records
                for idx, row in layer_data.iterrows():
                    record = row.to_dict()
                    record['_layer_name'] = layer_name
                    # Convert geometry to WKT if present
                    if 'geometry' in record and record['geometry'] is not None:
                        record['geometry_wkt'] = record['geometry'].wkt
                        del record['geometry']  # Remove geometry object
                    records.append(record)
            
            return {
                'format': 'gpkg',
                'records': records,
                'record_count': len(records),
                'layers': list(layers.keys())
            }
            
        except ImportError:
            # Fallback if geopandas is not available
            return self._extract_basic_info_from_path(file_path, 'gpkg')
        except Exception as e:
            self.logger.warning(f"Failed to extract from GeoPackage: {str(e)}")
            return self._extract_basic_info_from_path(file_path, 'gpkg')
    
    def _extract_sql(self, file_path: str) -> Dict[str, Any]:
        """Extract data from SQL file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                sql_content = file.read()
            
            # Parse SQL file to extract table information
            # This is a basic implementation - in practice, you might want to use a SQL parser
            records = [{
                'sql_content': sql_content,
                'file_name': os.path.basename(file_path),
                'file_size': os.path.getsize(file_path),
                'sql_type': 'script'
            }]
            
            return {
                'format': 'sql',
                'records': records,
                'record_count': 1,
                'sql_type': 'script'
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to extract from SQL file: {str(e)}")
            return self._extract_basic_info_from_path(file_path, 'sql')
    
    def _extract_basic_info_from_path(self, file_path: str, format_type: str) -> Dict[str, Any]:
        """Extract basic information from file path for unsupported formats"""
        return {
            'format': format_type,
            'records': [{
                'file_name': os.path.basename(file_path),
                'file_path': file_path,
                'file_size': os.path.getsize(file_path),
                'format_type': format_type,
                'extraction_status': 'basic_info_only'
            }],
            'record_count': 1
        }
    
    def _transform(self):
        """Transform extracted data"""
        self.logger.info(f"Transforming data for dataset: {self.dataset.title}")
        
        if not self.extracted_data:
            raise TransformationError("No data extracted to transform")
        
        # Apply transformations based on data format
        if self.extracted_data['format'] in ['csv', 'excel']:
            self.transformed_data = self._transform_tabular_data()
        elif self.extracted_data['format'] in ['json', 'geojson']:
            self.transformed_data = self._transform_json_data()
        elif self.extracted_data['format'] in ['gdb', 'spatialite', 'gpkg']:
            self.transformed_data = self._transform_geospatial_data()
        elif self.extracted_data['format'] in ['sql']:
            self.transformed_data = self._transform_sql_data()
        else:
            self.transformed_data = self.extracted_data
        
        self.logger.info(f"Transformed {len(self.transformed_data.get('records', []))} records")
    
    def _transform_tabular_data(self) -> Dict[str, Any]:
        """Transform tabular data (CSV, Excel)"""
        records = self.extracted_data['records']
        transformed_records = []
        
        for record in records:
            # Clean and standardize data
            transformed_record = {}
            for key, value in record.items():
                # Clean column names
                clean_key = self._clean_column_name(key)
                # Clean values
                clean_value = self._clean_value(value)
                transformed_record[clean_key] = clean_value
            
            # Add metadata
            transformed_record['_dataset_id'] = str(self.dataset.id)
            transformed_record['_dataset_title'] = self.dataset.title
            transformed_record['_import_timestamp'] = timezone.now().isoformat()
            transformed_record['_imported_by'] = self.requested_by.username
            
            transformed_records.append(transformed_record)
        
        return {
            'format': 'transformed_tabular',
            'records': transformed_records,
            'columns': list(transformed_records[0].keys()) if transformed_records else [],
            'record_count': len(transformed_records)
        }
    
    def _transform_json_data(self) -> Dict[str, Any]:
        """Transform JSON/GeoJSON data"""
        records = self.extracted_data['records']
        transformed_records = []
        
        for record in records:
            transformed_record = {
                '_dataset_id': str(self.dataset.id),
                '_dataset_title': self.dataset.title,
                '_import_timestamp': timezone.now().isoformat(),
                '_imported_by': self.requested_by.username
            }
            
            # Handle GeoJSON features
            if self.extracted_data['format'] == 'geojson':
                transformed_record['_geometry'] = record.get('geometry', {})
                transformed_record.update(record.get('properties', {}))
            else:
                transformed_record.update(record)
            
            transformed_records.append(transformed_record)
        
        return {
            'format': 'transformed_json',
            'records': transformed_records,
            'record_count': len(transformed_records),
            'geometry_type': self.extracted_data.get('geometry_type')
        }
    
    def _clean_column_name(self, name: str) -> str:
        """Clean column name for database compatibility"""
        import re
        
        # Remove special characters and replace with underscores
        cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', str(name))
        # Remove multiple underscores
        cleaned = re.sub(r'_+', '_', cleaned)
        # Remove leading/trailing underscores
        cleaned = cleaned.strip('_')
        # Ensure it starts with a letter or underscore
        if cleaned and not cleaned[0].isalpha() and cleaned[0] != '_':
            cleaned = '_' + cleaned
        # Ensure it's not empty
        if not cleaned:
            cleaned = 'column'
        
        return cleaned.lower()
    
    def _clean_value(self, value: Any) -> Any:
        """Clean data value"""
        if value is None:
            return None
        
        # Convert to string and strip whitespace
        cleaned = str(value).strip()
        
        # Try to convert to appropriate type
        if cleaned.lower() in ['true', 'false']:
            return cleaned.lower() == 'true'
        elif cleaned.isdigit():
            return int(cleaned)
        elif cleaned.replace('.', '').isdigit():
            try:
                return float(cleaned)
            except ValueError:
                pass
        
        return cleaned if cleaned else None
    
    def _transform_geospatial_data(self) -> Dict[str, Any]:
        """Transform geospatial data (GDB, SpatiaLite, GeoPackage)"""
        records = self.extracted_data['records']
        transformed_records = []
        
        for record in records:
            transformed_record = {
                '_dataset_id': str(self.dataset.id),
                '_dataset_title': self.dataset.title,
                '_import_timestamp': timezone.now().isoformat(),
                '_imported_by': self.requested_by.username
            }
            
            # Add format-specific metadata
            if self.extracted_data['format'] == 'gdb':
                transformed_record['_source_format'] = 'File Geodatabase'
                transformed_record['_layer_name'] = record.get('_layer_name', '')
            elif self.extracted_data['format'] == 'spatialite':
                transformed_record['_source_format'] = 'SpatiaLite'
                transformed_record['_table_name'] = record.get('_table_name', '')
            elif self.extracted_data['format'] == 'gpkg':
                transformed_record['_source_format'] = 'GeoPackage'
                transformed_record['_layer_name'] = record.get('_layer_name', '')
            
            # Handle geometry data
            if 'geometry_wkt' in record:
                transformed_record['geometry_wkt'] = record['geometry_wkt']
            elif 'geometry' in record:
                transformed_record['geometry'] = record['geometry']
            
            # Add all other fields
            for key, value in record.items():
                if not key.startswith('_') and key not in ['geometry', 'geometry_wkt']:
                    clean_key = self._clean_column_name(key)
                    clean_value = self._clean_value(value)
                    transformed_record[clean_key] = clean_value
            
            transformed_records.append(transformed_record)
        
        return {
            'format': 'transformed_geospatial',
            'records': transformed_records,
            'record_count': len(transformed_records),
            'source_format': self.extracted_data['format'],
            'layers': self.extracted_data.get('layers', []),
            'tables': self.extracted_data.get('tables', [])
        }
    
    def _transform_sql_data(self) -> Dict[str, Any]:
        """Transform SQL data"""
        records = self.extracted_data['records']
        transformed_records = []
        
        for record in records:
            transformed_record = {
                '_dataset_id': str(self.dataset.id),
                '_dataset_title': self.dataset.title,
                '_import_timestamp': timezone.now().isoformat(),
                '_imported_by': self.requested_by.username,
                '_source_format': 'SQL Script'
            }
            
            # Add SQL-specific fields
            transformed_record.update(record)
            transformed_records.append(transformed_record)
        
        return {
            'format': 'transformed_sql',
            'records': transformed_records,
            'record_count': len(transformed_records),
            'sql_type': self.extracted_data.get('sql_type', 'script')
        }
    
    def _load(self):
        """Load transformed data into import database"""
        self.logger.info(f"Loading data into import database for dataset: {self.dataset.title}")
        
        if not self.transformed_data:
            raise LoadingError("No transformed data to load")
        
        # Create table name
        table_name = f"imported_dataset_{self.dataset.id}_{self.requested_by.id}"
        
        try:
            with transaction.atomic(using='import'):
                # Create table
                self._create_import_table(table_name)
                
                # Insert data
                self._insert_data(table_name)
                
                # Create DatasetImport record
                self._create_dataset_import_record(table_name)
                
        except Exception as e:
            raise LoadingError(f"Failed to load data: {str(e)}")
        
        self.logger.info(f"Successfully loaded {len(self.transformed_data['records'])} records into table: {table_name}")
    
    def _create_import_table(self, table_name: str):
        """Create table in import database"""
        # Get columns from transformed data or derive from records
        if 'columns' in self.transformed_data:
            columns = self.transformed_data['columns']
        elif self.transformed_data.get('records'):
            # Derive columns from the first record
            columns = list(self.transformed_data['records'][0].keys())
        else:
            # Fallback to basic columns
            columns = ['_dataset_id', '_dataset_title', '_import_timestamp', '_imported_by']
        
        # Build CREATE TABLE statement
        column_defs = []
        for column in columns:
            if column.startswith('_'):
                # Metadata columns
                column_defs.append(f'"{column}" TEXT')
            else:
                # Data columns - use TEXT for simplicity
                column_defs.append(f'"{column}" TEXT')
        
        # Add standard columns
        column_defs.extend([
            'id SERIAL PRIMARY KEY',
            'created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        ])
        
        create_sql = f"""
        CREATE TABLE IF NOT EXISTS "{table_name}" (
            {', '.join(column_defs)}
        )
        """
        
        with self.import_db.cursor() as cursor:
            cursor.execute(create_sql)
    
    def _insert_data(self, table_name: str):
        """Insert data into import table"""
        records = self.transformed_data['records']
        
        if not records:
            return
        
        # Get columns from transformed data or derive from records
        if 'columns' in self.transformed_data:
            columns = self.transformed_data['columns']
        else:
            # Derive columns from the first record
            columns = list(records[0].keys())
        
        # Prepare insert statement
        column_names = [f'"{col}"' for col in columns]
        placeholders = ', '.join(['%s'] * len(columns))
        
        insert_sql = f"""
        INSERT INTO "{table_name}" ({', '.join(column_names)})
        VALUES ({placeholders})
        """
        
        # Prepare data for insertion
        insert_data = []
        for record in records:
            row_data = [record.get(col) for col in columns]
            insert_data.append(row_data)
        
        # Execute batch insert
        with self.import_db.cursor() as cursor:
            cursor.executemany(insert_sql, insert_data)
    
    def _create_dataset_import_record(self, table_name: str):
        """Create DatasetImport record"""
        dataset_import = DatasetImport.objects.create(
            dataset=self.dataset,
            imported_by=self.requested_by,
            status='completed',
            import_completed_at=timezone.now(),
            import_database_table=table_name,
            records_imported=len(self.transformed_data['records']),
            import_notes=f"ETL pipeline import completed successfully. Table: {table_name}"
        )
        
        # Link to queue entry
        self.queue_entry.dataset_import = dataset_import
        self.queue_entry.save()
    
    def _update_queue_status(self, status: str, error_message: str = None):
        """Update queue entry status"""
        now = timezone.now()
        
        if status == 'processing':
            self.queue_entry.status = status
            self.queue_entry.started_at = now
        elif status in ['completed', 'failed']:
            self.queue_entry.status = status
            self.queue_entry.completed_at = now
            if error_message:
                self.queue_entry.error_message = error_message
        
        self.queue_entry.save()


class ETLPipelineManager:
    """
    Manager class for handling ETL pipeline operations.
    
    This class ensures only one import runs at a time and manages
    the import queue processing.
    """
    
    @staticmethod
    def process_next_import() -> bool:
        """
        Process the next import in the queue.
        
        Returns:
            bool: True if an import was processed, False if queue is empty
        """
        # Check if any import is currently processing
        if ImportQueue.is_processing_import():
            logger.info("Import already in progress, skipping queue processing")
            return False
        
        # Get next import to process
        queue_entry = ImportQueue.get_next_import()
        if not queue_entry:
            logger.info("No imports in queue")
            return False
        
        logger.info(f"Processing import queue entry: {queue_entry}")
        
        # Create and execute ETL pipeline
        pipeline = DatasetETLPipeline(queue_entry)
        success = pipeline.execute()
        
        return success
    
    @staticmethod
    def get_queue_status() -> Dict[str, Any]:
        """
        Get current queue status.
        
        Returns:
            Dict with queue statistics
        """
        from django.db.models import Count
        
        from django.db.models import Q
        
        stats = ImportQueue.objects.aggregate(
            pending=Count('id', filter=Q(status='pending')),
            processing=Count('id', filter=Q(status='processing')),
            completed=Count('id', filter=Q(status='completed')),
            failed=Count('id', filter=Q(status='failed')),
            total=Count('id')
        )
        
        return stats
    
    @staticmethod
    def cleanup_old_imports(days: int = 30):
        """
        Clean up old completed imports.
        
        Args:
            days: Number of days to keep completed imports
        """
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Delete old completed imports
        deleted_count = ImportQueue.objects.filter(
            status='completed',
            completed_at__lt=cutoff_date
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old import records")
    
    @staticmethod
    def diagnose_and_fix_import_error(queue_entry: ImportQueue) -> Dict[str, Any]:
        """
        Diagnose and attempt to fix import errors.
        
        Args:
            queue_entry: The failed ImportQueue entry to diagnose
            
        Returns:
            Dict with diagnosis results and fix attempts
        """
        result = {
            'success': False,
            'diagnosis': [],
            'fixes_applied': [],
            'remaining_issues': [],
            'recommendations': []
        }
        
        try:
            logger.info(f"Diagnosing import error for queue entry: {queue_entry.pk}")
            
            # 1. Check dataset and version availability
            if not queue_entry.dataset:
                result['diagnosis'].append("Dataset not found")
                result['remaining_issues'].append("Dataset reference is missing")
                return result
            
            if not queue_entry.dataset.versions.exists():
                result['diagnosis'].append("No dataset versions available")
                result['recommendations'].append("Upload a dataset version before importing")
                return result
            
            # 2. Check file accessibility
            latest_version = queue_entry.dataset.versions.first()
            if not latest_version.file:
                result['diagnosis'].append("No file attached to dataset version")
                result['remaining_issues'].append("Dataset version has no file")
                return result
            
            # 3. Check file existence and accessibility
            try:
                if not latest_version.file.storage.exists(latest_version.file.name):
                    result['diagnosis'].append("File not found in storage")
                    result['remaining_issues'].append("File is missing from storage")
                    return result
            except Exception as e:
                result['diagnosis'].append(f"File access error: {str(e)}")
                result['remaining_issues'].append("Cannot access file")
                return result
            
            # 4. Check database connection
            try:
                import_db = connections['import']
                with import_db.cursor() as cursor:
                    cursor.execute("SELECT 1")
            except Exception as e:
                result['diagnosis'].append(f"Database connection error: {str(e)}")
                result['remaining_issues'].append("Import database is not accessible")
                return result
            
            # 5. Check for specific error patterns and apply fixes
            error_message = queue_entry.error_message or ""
            
            # Fix 1: Reset status if stuck in processing
            if queue_entry.status == 'processing':
                queue_entry.status = 'pending'
                queue_entry.error_message = ""
                queue_entry.save()
                result['fixes_applied'].append("Reset status from 'processing' to 'pending'")
                result['success'] = True
            
            # Fix 2: Clear error message and reset to pending for retry
            elif queue_entry.status == 'failed' and error_message:
                queue_entry.status = 'pending'
                queue_entry.error_message = ""
                queue_entry.save()
                result['fixes_applied'].append("Cleared error message and reset to pending")
                result['success'] = True
            
            # Fix 3: Check for file format issues
            file_extension = os.path.splitext(latest_version.file.name)[1].lower()
            supported_formats = ['.csv', '.json', '.geojson', '.xlsx', '.xls', '.gdb', '.sqlite', '.gpkg', '.sql']
            
            if file_extension not in supported_formats:
                result['diagnosis'].append(f"Unsupported file format: {file_extension}")
                result['recommendations'].append(f"Convert file to one of: {', '.join(supported_formats)}")
            
            # Fix 4: Check for corrupted dataset import record
            if queue_entry.dataset_import:
                try:
                    # Check if dataset import is in a bad state
                    if queue_entry.dataset_import.status == 'importing':
                        queue_entry.dataset_import.status = 'failed'
                        queue_entry.dataset_import.error_message = "Import was interrupted and reset"
                        queue_entry.dataset_import.save()
                        result['fixes_applied'].append("Reset stuck dataset import status")
                except Exception as e:
                    result['diagnosis'].append(f"Dataset import record issue: {str(e)}")
            
            # Fix 5: Clean up any orphaned database tables
            if queue_entry.dataset_import and queue_entry.dataset_import.import_database_table:
                try:
                    import_db = connections['import']
                    table_name = queue_entry.dataset_import.import_database_table
                    
                    with import_db.cursor() as cursor:
                        # Check if table exists and is empty (orphaned)
                        cursor.execute("""
                            SELECT COUNT(*) FROM information_schema.tables 
                            WHERE table_name = %s
                        """, [table_name])
                        
                        if cursor.fetchone()[0] > 0:
                            cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                            record_count = cursor.fetchone()[0]
                            
                            if record_count == 0:
                                # Drop empty orphaned table
                                cursor.execute(f'DROP TABLE IF EXISTS "{table_name}"')
                                result['fixes_applied'].append(f"Cleaned up empty orphaned table: {table_name}")
                except Exception as e:
                    result['diagnosis'].append(f"Database cleanup issue: {str(e)}")
            
            # Fix 6: Reset timestamps for retry
            if queue_entry.started_at:
                queue_entry.started_at = None
                queue_entry.completed_at = None
                queue_entry.save()
                result['fixes_applied'].append("Reset processing timestamps")
            
            # If we get here and no specific issues were found, mark as ready for retry
            if not result['remaining_issues'] and not result['diagnosis']:
                result['success'] = True
                result['fixes_applied'].append("Import is ready for retry")
                result['recommendations'].append("Try running the import again")
            
            logger.info(f"Diagnosis completed for queue entry {queue_entry.pk}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error during diagnosis: {str(e)}")
            result['diagnosis'].append(f"Diagnosis failed: {str(e)}")
            return result