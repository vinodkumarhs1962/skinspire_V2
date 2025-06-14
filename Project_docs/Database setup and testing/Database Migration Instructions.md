# Database Migration Instructions

## Creating and Running the Migration

Follow these steps to create and apply the migration for the verification and staff approval features:

### 1. Ensure your models are updated

First, add the new models and fields to `app/models/transaction.py`:

- Add the `verification_status` column to the User model
- Add the `is_phone_verified`, `is_email_verified`, and `verification_info` properties to the User model
- Add the new `VerificationCode` model class
- Add the new `StaffApprovalRequest` model class

### 2. Generate the migration

Run the following command to generate the migration script:

```bash
flask db migrate -m "Add verification and staff approval tables"
```

This will:
1. Scan your models for changes
2. Generate a new migration script in the `migrations/versions` directory
3. Automatically add the script to the migration chain

The generated migration file will have a filename like `xxxx_add_verification_and_staff_approval_tables.py` where `xxxx` is an auto-generated revision ID.

### 3. Review the migration

Open the generated migration file and review it to ensure it correctly captures all the changes:

- The `verification_status` column in the users table
- The new `verification_codes` table
- The new `staff_approval_requests` table
- All necessary indexes and foreign keys

### 4. Apply the migration

Run the following command to apply the migration:

```bash
flask db upgrade
```

This will execute the upgrade() function in your migration script, creating the new tables and columns.

### 5. Verify the migration

You can verify the migration was successful by:

- Checking the database schema using a tool like pgAdmin
- Checking the alembic_version table in your database to see that the new revision is listed
- Running `flask db current` to see the current migration version

## Troubleshooting

If you encounter any issues during migration:

### Issue: Foreign key constraints fail

**Solution**: Check that the referenced tables exist and have the correct column names.

### Issue: Tables already exist

**Solution**: If you've manually created these tables, you may need to drop them first or mark the migration as completed:

```bash
flask db stamp <revision_id>
```

### Issue: Data type conflicts

**Solution**: If your database has stricter type constraints than SQLAlchemy, you may need to adjust the column types in your migration script.

### Rolling back migrations

If you need to undo the migration:

```bash
flask db downgrade
```

This will execute the downgrade() function in your migration script, removing the tables and columns.