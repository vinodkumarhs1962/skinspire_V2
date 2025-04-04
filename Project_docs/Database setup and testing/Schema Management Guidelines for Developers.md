# Schema Management Guidelines for Developers

## Overview

This guide explains our hybrid approach to database schema changes, which balances development speed with proper schema control.

## Development Workflow

### Making Schema Changes

When adding or modifying database models:

1. Make changes to your model definitions in `app/models/`.

2. Use the direct sync command to update your development database:
   ```bash
   python scripts/manage_db.py sync-dev-schema
   ```

3. Iterate on your changes as needed, repeating the sync command after each update.

4. Test your changes thoroughly in the development environment.

### Benefits of Direct Schema Sync

- Avoid writing migration files during active development
- Immediately see the effects of model changes
- Faster iteration cycles while experimenting with schema changes
- No need to understand Alembic migration details during initial development

## Preparing for Testing/QA

Once your model changes are complete and ready for testing:

1. Check what changes will be included in a migration:
   ```bash
   python scripts/manage_db.py detect-schema-changes
   ```
   This will show all differences between your models and the current database schema.

2. Generate proper migration files:
   ```bash
   python scripts/manage_db.py prepare-migration -m "Added user preferences field"
   ```
   This creates an Alembic migration file that captures all your changes.

3. Review the generated migration file in the `migrations/versions/` directory.

4. Include the migration file in your pull request for code review.

## Testing Phase

In the testing environment:

1. **Never** use `sync-dev-schema` - always apply migrations:
   ```bash
   python scripts/manage_db.py apply-migrations --env test
   ```

2. Verify that the database changes work as expected.

3. If issues are found, fix them in development and create a new migration.

## Production Deployment

For production environments:

1. Always use the same migrations that were tested:
   ```bash
   python scripts/manage_db.py apply-migrations --env prod
   ```

2. Always back up the production database before applying migrations:
   ```bash
   python scripts/manage_db.py create-backup --env prod
   ```

## Viewing Migration History

To see the current migration history:
```bash
python scripts/manage_db.py show-all-migrations
```

## When Things Go Wrong

If you need to roll back a migration:
```bash
python scripts/manage_db.py rollback-db-migration
```

To roll back multiple migrations:
```bash
python scripts/manage_db.py rollback-db-migration --steps 3
```

## Best Practices

1. **Environment Boundaries**:
   - `sync-dev-schema` is for development ONLY
   - Always use migrations for testing and production

2. **Code Review**:
   - Always include migration files in code reviews
   - Review changes for potential data loss

3. **Data Preservation**:
   - Consider how schema changes affect existing data
   - Use backups before applying schema changes

4. **Complex Changes**:
   - For complex schema changes, consider writing migrations manually
   - Use multiple migrations for very large changes

5. **Testing Migrations**:
   - Test migration both forward and backward
   - Verify data integrity after migrations

## Safety Measures

The schema sync system includes these safety measures:

- Only works in development environment
- Requires explicit confirmation
- Creates automatic backups before changes
- Environment validation before operations

Remember: The goal of this hybrid approach is to make development faster while maintaining proper schema control for testing and production.