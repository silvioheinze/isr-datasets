# Import Database Configuration

This document describes how to configure the import database for dataset imports in the ISR Datasets application.

## Overview

The application now supports two databases:
- **Default Database**: Main application database for all standard operations
- **Import Database**: Dedicated database for importing datasets from external sources

## Environment Variables

### Required Environment Variables for Import Database

Add these environment variables to your `.env` file or environment configuration:

```bash
# Import Database Configuration
IMPORT_POSTGRES_DB=isrdatasets_import
IMPORT_POSTGRES_USER=isruser
IMPORT_POSTGRES_PASSWORD=isrpass
IMPORT_POSTGRES_HOST=import_db
IMPORT_POSTGRES_PORT=5432
```

### Alternative: Complete Database URL

Instead of individual variables, you can use a complete database URL:

```bash
IMPORT_DATABASE_URL=postgres://isruser:isrpass@import_db:5432/isrdatasets_import
```

## Docker Compose Configuration

The `docker-compose.yml` file has been updated to include:
- `import_db` service running PostGIS
- Separate volume for import database data
- Health checks for the import database
- Application dependency on both databases

## Database Router

A database router has been implemented in `main/database_router.py` to handle routing between databases:

- **Default Database**: Used for all standard application models
- **Import Database**: Used for models/apps configured for imports

### Configuring Models for Import Database

To route specific models to the import database, update the router configuration:

```python
# In main/database_router.py
import_models = {
    'datasets.ImportedDataset',  # Example model
    'datasets.ImportLog',        # Example model
}

import_apps = {
    'import_datasets',  # Example app
}
```

## Usage in Code

### Using the Import Database

```python
from django.db import connections

# Get import database connection
import_db = connections['import']

# Execute queries on import database
with import_db.cursor() as cursor:
    cursor.execute("SELECT * FROM some_table")

# Or use using parameter in model operations
MyModel.objects.using('import').all()
```

### Creating Models for Import Database

```python
from django.db import models

class ImportedDataset(models.Model):
    name = models.CharField(max_length=255)
    source_url = models.URLField()
    imported_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # This model will use the import database if configured in router
        db_table = 'imported_datasets'
```

## Testing

The configuration includes test database setup:
- Test databases are prefixed with `test_`
- Both default and import databases get test versions
- Router handles test database routing

## Migration Management

### Running Migrations

```bash
# Run migrations on default database
python manage.py migrate

# Run migrations on import database
python manage.py migrate --database=import

# Create migrations for import-specific models
python manage.py makemigrations
```

### Managing Multiple Databases

```bash
# Show database connections
python manage.py dbshell
python manage.py dbshell --database=import

# Load data into specific database
python manage.py loaddata --database=import fixtures/import_data.json
```

## Security Considerations

- Import database should have restricted access
- Consider using different credentials for import database
- Regularly backup both databases
- Monitor import database usage and performance

## Troubleshooting

### Common Issues

1. **Connection Refused**: Ensure import_db service is running
2. **Authentication Failed**: Check import database credentials
3. **Router Not Working**: Verify DATABASE_ROUTERS setting

### Debugging

```python
# Check database connections
from django.db import connections
print(connections.databases)

# Test import database connection
from django.db import connection
connection.ensure_connection()
```

## Production Deployment

For production deployment:

1. Use separate database servers for better isolation
2. Configure proper backup strategies for both databases
3. Set up monitoring for both database instances
4. Use connection pooling if needed
5. Consider read replicas for import database if needed

## Example Import Workflow

1. Connect to external data source
2. Process data using import database
3. Validate and transform data
4. Transfer processed data to main database
5. Update application models
6. Clean up temporary data from import database

