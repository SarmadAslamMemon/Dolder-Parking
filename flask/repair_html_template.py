"""
Script to repair the corrupted html_template table.
This script will:
1. Drop the corrupted table
2. Recreate it with the correct structure
"""
from app import db, app
from sqlalchemy import text
import models

def repair_html_template_table():
    """Repair the corrupted html_template table"""
    with app.app_context():
        try:
            print("=" * 60)
            print("Repairing html_template table...")
            print("=" * 60)
            
            # Check if table exists
            inspector = db.inspect(db.engine)
            table_exists = 'html_template' in inspector.get_table_names()
            
            if table_exists:
                print("\n[1/4] Table exists. Checking structure...")
                try:
                    # Try to query the table to see if it's accessible
                    result = db.session.execute(text("SELECT COUNT(*) FROM html_template"))
                    count = result.scalar()
                    print(f"    Table is accessible. Current row count: {count}")
                    
                    # Try to get column info
                    columns = inspector.get_columns('html_template')
                    print(f"    Columns found: {[col['name'] for col in columns]}")
                except Exception as e:
                    print(f"    ✗ Table is corrupted: {e}")
                    print("\n[2/4] Dropping corrupted table...")
                    try:
                        db.session.execute(text("DROP TABLE IF EXISTS html_template"))
                        db.session.commit()
                        print("    ✓ Corrupted table dropped successfully")
                    except Exception as drop_error:
                        print(f"    ✗ Error dropping table: {drop_error}")
                        # Try to force drop using InnoDB recovery
                        try:
                            print("    Attempting force drop...")
                            db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
                            db.session.execute(text("DROP TABLE IF EXISTS html_template"))
                            db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                            db.session.commit()
                            print("    ✓ Table force-dropped successfully")
                        except Exception as force_error:
                            print(f"    ✗ Force drop failed: {force_error}")
                            return False
            else:
                print("\n[1/4] Table does not exist. Will create new one.")
            
            print("\n[3/4] Creating new html_template table...")
            try:
                # Create the table using SQLAlchemy
                models.HtmlTemplate.__table__.create(db.engine, checkfirst=True)
                print("    ✓ Table created successfully")
            except Exception as create_error:
                print(f"    ✗ Error creating table: {create_error}")
                # Try manual creation
                try:
                    print("    Attempting manual creation...")
                    db.session.execute(text("""
                        CREATE TABLE IF NOT EXISTS html_template (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            html_content TEXT NOT NULL,
                            created_at DATETIME NOT NULL,
                            user_id INT NULL,
                            FOREIGN KEY (user_id) REFERENCES users(id)
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                    """))
                    db.session.commit()
                    print("    ✓ Table created manually")
                except Exception as manual_error:
                    print(f"    ✗ Manual creation failed: {manual_error}")
                    return False
            
            print("\n[4/4] Verifying table structure...")
            try:
                columns = inspector.get_columns('html_template')
                column_names = [col['name'] for col in columns]
                expected_columns = ['id', 'html_content', 'created_at', 'user_id']
                
                print(f"    Expected columns: {expected_columns}")
                print(f"    Actual columns: {column_names}")
                
                if set(column_names) == set(expected_columns):
                    print("    ✓ Table structure is correct!")
                else:
                    missing = set(expected_columns) - set(column_names)
                    extra = set(column_names) - set(expected_columns)
                    if missing:
                        print(f"    ⚠ Missing columns: {missing}")
                    if extra:
                        print(f"    ⚠ Extra columns: {extra}")
                
                # Test insert
                print("\n[TEST] Testing table functionality...")
                test_result = db.session.execute(text("SELECT 1 FROM html_template LIMIT 1"))
                print("    ✓ Table is functional")
                
            except Exception as verify_error:
                print(f"    ✗ Verification failed: {verify_error}")
                return False
            
            print("\n" + "=" * 60)
            print("✓ html_template table repair completed successfully!")
            print("=" * 60)
            return True
            
        except Exception as e:
            print(f"\n✗ Error during repair: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = repair_html_template_table()
    if success:
        print("\nYou can now restart your Flask application.")
    else:
        print("\nRepair failed. Please check the errors above.")
        exit(1)

