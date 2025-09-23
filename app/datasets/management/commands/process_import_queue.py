"""
Management command to process the import queue.

This command processes dataset imports one at a time from the queue.
It can be run manually or scheduled as a cron job.
"""

import logging
import time
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction

from datasets.models import ImportQueue
from datasets.etl_pipeline import ETLPipelineManager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process the dataset import queue'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--continuous',
            action='store_true',
            help='Run continuously, processing imports as they come in',
        )
        parser.add_argument(
            '--max-runtime',
            type=int,
            default=3600,
            help='Maximum runtime in seconds for continuous mode (default: 3600)',
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up old completed imports after processing',
        )
        parser.add_argument(
            '--cleanup-days',
            type=int,
            default=30,
            help='Number of days to keep completed imports (default: 30)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output',
        )
    
    def handle(self, *args, **options):
        """Handle the command execution"""
        
        # Set up logging level
        if options['verbose']:
            logging.getLogger('datasets.etl_pipeline').setLevel(logging.DEBUG)
        
        self.stdout.write(
            self.style.SUCCESS('Starting import queue processor...')
        )
        
        start_time = timezone.now()
        processed_count = 0
        failed_count = 0
        
        try:
            if options['continuous']:
                self._run_continuous_mode(options, start_time)
            else:
                processed_count, failed_count = self._run_single_mode(options)
            
            # Cleanup if requested
            if options['cleanup']:
                self.stdout.write('Cleaning up old imports...')
                ETLPipelineManager.cleanup_old_imports(options['cleanup_days'])
            
            # Show summary
            runtime = (timezone.now() - start_time).total_seconds()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Processing completed. Runtime: {runtime:.1f}s, '
                    f'Processed: {processed_count}, Failed: {failed_count}'
                )
            )
            
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('\nProcessing interrupted by user')
            )
        except Exception as e:
            raise CommandError(f'Error processing import queue: {str(e)}')
    
    def _run_single_mode(self, options):
        """Run in single mode - process one import and exit"""
        processed_count = 0
        failed_count = 0
        
        # Get queue status
        stats = ETLPipelineManager.get_queue_status()
        self.stdout.write(f'Queue status: {stats}')
        
        # Process next import
        if stats['pending'] > 0:
            self.stdout.write('Processing next import in queue...')
            success = ETLPipelineManager.process_next_import()
            
            if success:
                processed_count = 1
                self.stdout.write(
                    self.style.SUCCESS('Import processed successfully')
                )
            else:
                failed_count = 1
                self.stdout.write(
                    self.style.ERROR('Import processing failed')
                )
        else:
            self.stdout.write('No imports pending in queue')
        
        return processed_count, failed_count
    
    def _run_continuous_mode(self, options, start_time):
        """Run in continuous mode - process imports until max runtime"""
        max_runtime = options['max_runtime']
        processed_count = 0
        failed_count = 0
        
        self.stdout.write(f'Running in continuous mode for up to {max_runtime} seconds...')
        
        while True:
            # Check if we've exceeded max runtime
            runtime = (timezone.now() - start_time).total_seconds()
            if runtime >= max_runtime:
                self.stdout.write(f'Maximum runtime ({max_runtime}s) reached')
                break
            
            # Check for pending imports
            stats = ETLPipelineManager.get_queue_status()
            if stats['pending'] == 0:
                if options['verbose']:
                    self.stdout.write('No imports pending, waiting...')
                time.sleep(5)  # Wait 5 seconds before checking again
                continue
            
            # Process next import
            self.stdout.write(f'Processing import {processed_count + 1}...')
            success = ETLPipelineManager.process_next_import()
            
            if success:
                processed_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Import {processed_count} processed successfully')
                )
            else:
                failed_count += 1
                self.stdout.write(
                    self.style.ERROR(f'Import {failed_count} processing failed')
                )
            
            # Small delay between imports
            time.sleep(1)
        
        return processed_count, failed_count

