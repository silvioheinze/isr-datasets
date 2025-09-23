"""
Database router for handling multiple databases in ISR Datasets application.

This router determines which database to use for different operations:
- 'default': Main application database for all standard models
- 'import': Import database for dataset import operations
"""


class ImportDatabaseRouter:
    """
    Database router to handle routing between the main database and import database.
    
    The import database is used specifically for dataset import operations,
    while the main database handles all other application data.
    """
    
    # Models that should use the import database
    import_models = {
        # Add models here that should use the import database
        # Example: 'datasets.ImportedDataset',
        # Example: 'datasets.ImportLog',
    }
    
    # Apps that should use the import database
    import_apps = {
        # Add apps here that should use the import database
        # Example: 'import_datasets',
    }
    
    def db_for_read(self, model, **hints):
        """Suggest the database to read from."""
        if self._should_use_import_db(model):
            return 'import'
        return 'default'
    
    def db_for_write(self, model, **hints):
        """Suggest the database to write to."""
        if self._should_use_import_db(model):
            return 'import'
        return 'default'
    
    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations if both objects are in the same database."""
        db_set = {'default', 'import'}
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return True
        return None
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Ensure that certain models end up in the right database."""
        if db == 'import':
            # Only allow migrations for models/apps that should use import DB
            if app_label in self.import_apps:
                return True
            if model_name and f"{app_label}.{model_name}" in self.import_models:
                return True
            return False
        elif db == 'default':
            # Allow all other models to use the default database
            if app_label in self.import_apps:
                return False
            if model_name and f"{app_label}.{model_name}" in self.import_models:
                return False
            return True
        return None
    
    def _should_use_import_db(self, model):
        """Determine if a model should use the import database."""
        # Check if the model is explicitly configured for import database
        model_key = f"{model._meta.app_label}.{model._meta.model_name}"
        if model_key in self.import_models:
            return True
        
        # Check if the app is configured for import database
        if model._meta.app_label in self.import_apps:
            return True
        
        return False


# Create router instance
database_router = ImportDatabaseRouter()

