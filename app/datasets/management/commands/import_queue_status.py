"""
Management command to check the status of the import queue.
"""

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from datasets.models import ImportQueue
from datasets.etl_pipeline import ETLPipelineManager


class Command(BaseCommand):
    help = 'Show the status of the dataset import queue'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed information about each queue entry',
        )
        parser.add_argument(
            '--recent',
            type=int,
            default=24,
            help='Show entries from the last N hours (default: 24)',
        )
    
    def handle(self, *args, **options):
        """Handle the command execution"""
        
        # Get queue statistics
        stats = ETLPipelineManager.get_queue_status()
        
        self.stdout.write(
            self.style.SUCCESS('=== Import Queue Status ===')
        )
        
        # Show summary
        self.stdout.write(f'Total entries: {stats["total"]}')
        self.stdout.write(f'Pending: {stats["pending"]}')
        self.stdout.write(f'Processing: {stats["processing"]}')
        self.stdout.write(f'Completed: {stats["completed"]}')
        self.stdout.write(f'Failed: {stats["failed"]}')
        
        # Show detailed information if requested
        if options['detailed']:
            self._show_detailed_status(options['recent'])
        
        # Show current processing status
        if ImportQueue.is_processing_import():
            processing = ImportQueue.objects.filter(status='processing').first()
            self.stdout.write(
                self.style.WARNING(
                    f'Currently processing: {processing.dataset.title} '
                    f'(started {processing.started_at})'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('No imports currently processing')
            )
    
    def _show_detailed_status(self, recent_hours):
        """Show detailed status of recent queue entries"""
        
        cutoff_time = timezone.now() - timedelta(hours=recent_hours)
        recent_entries = ImportQueue.objects.filter(
            created_at__gte=cutoff_time
        ).order_by('-created_at')
        
        if not recent_entries.exists():
            self.stdout.write(f'No entries in the last {recent_hours} hours')
            return
        
        self.stdout.write(
            self.style.SUCCESS(f'\n=== Recent Entries (last {recent_hours}h) ===')
        )
        
        for entry in recent_entries:
            # Status styling
            if entry.status == 'completed':
                status_style = self.style.SUCCESS
            elif entry.status == 'failed':
                status_style = self.style.ERROR
            elif entry.status == 'processing':
                status_style = self.style.WARNING
            else:
                status_style = self.style.NOTICE
            
            # Basic info
            self.stdout.write(
                f'ID: {entry.id} | '
                f'Dataset: {entry.dataset.title[:50]}... | '
                f'User: {entry.requested_by.username} | '
                f'Priority: {entry.priority} | '
                f'Status: {status_style(entry.status.upper())}'
            )
            
            # Timing info
            if entry.started_at:
                processing_time = entry.processing_time
                if processing_time:
                    self.stdout.write(
                        f'  Started: {entry.started_at} | '
                        f'Processing time: {processing_time}'
                    )
            
            if entry.completed_at:
                self.stdout.write(f'  Completed: {entry.completed_at}')
            
            # Error info
            if entry.status == 'failed' and entry.error_message:
                self.stdout.write(f'  Error: {entry.error_message[:100]}...')
            
            self.stdout.write('')  # Empty line for readability

