"""
Script to update the permission enum in the database to include POWERUSER
Run this script once to update the database schema

Usage: python update_permission_enum.py
"""
import os
from sqlalchemy import create_engine, text

# Get database connection from environment variables
mariadb_user = os.environ.get('DB_USER', 'user')
mariadb_pass = os.environ.get('DB_PASS', 'pass')
mariadb_url = os.environ.get('DB_URL', 'localhost')
mariadb_port = os.environ.get('DB_PORT', '3306')
mariadb_db = os.environ.get('DB_NAME', 'dolderpark')

mariadb_string = f'mariadb+mariadbconnector://{mariadb_user}:{mariadb_pass}@{mariadb_url}:{mariadb_port}/{mariadb_db}'

def update_permission_enum():
    """Add POWERUSER to the permission enum in the users table"""
    try:
        # Create database connection
        engine = create_engine(mariadb_string)
        
        with engine.connect() as conn:
            # Check current enum values
            result = conn.execute(text("""
                SELECT COLUMN_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'users' 
                AND COLUMN_NAME = 'permission'
            """))
            current_enum = result.fetchone()
            if current_enum:
                print(f"Current enum definition: {current_enum[0]}")
            
            # Check if poweruser already exists
            if current_enum and 'poweruser' in current_enum[0].lower():
                print("✓ 'poweruser' already exists in the enum. No update needed.")
                return
            
            # Modify the enum column to include poweruser
            print("Updating permission enum to include 'poweruser'...")
            conn.execute(text("""
                ALTER TABLE users 
                MODIFY COLUMN permission ENUM('none', 'all', 'app', 'admin', 'poweruser') 
                NOT NULL DEFAULT 'none'
            """))
            conn.commit()
            print("✓ Successfully updated permission enum to include 'poweruser'")
            
    except Exception as e:
        print(f"✗ Error updating permission enum: {e}")
        print("\nYou can run this SQL command manually in your database:")
        print("ALTER TABLE users MODIFY COLUMN permission ENUM('none', 'all', 'app', 'admin', 'poweruser') NOT NULL DEFAULT 'none';")
        raise

if __name__ == "__main__":
    print("Updating permission enum in database...")
    update_permission_enum()
    print("Done!")
