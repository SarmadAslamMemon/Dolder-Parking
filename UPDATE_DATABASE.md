# Database Update Required

## Issue
The database enum column for `permission` doesn't include 'poweruser' as a valid value, causing errors when trying to set a user's permission to POWERUSER.

## Solution

### Option 1: Automatic Update (Recommended)
The database initialization script (`db_init.py`) has been updated to automatically add 'poweruser' to the enum when the application starts. Simply restart your Flask application and it will update the database automatically.

### Option 2: Manual SQL Update
If you prefer to update manually, run this SQL command in your MariaDB/MySQL database:

```sql
ALTER TABLE users 
MODIFY COLUMN permission ENUM('none', 'all', 'app', 'admin', 'poweruser') 
NOT NULL DEFAULT 'none';
```

### Option 3: Run the Update Script
If you have the Python environment set up, you can run:

```bash
cd flask
python update_permission_enum.py
```

## Verification
After updating, you can verify the enum includes 'poweruser' by running:

```sql
SELECT COLUMN_TYPE 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = DATABASE() 
AND TABLE_NAME = 'users' 
AND COLUMN_NAME = 'permission';
```

You should see `ENUM('none','all','app','admin','poweruser')` in the result.

