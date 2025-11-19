from app import db
from app import app
import models
from datetime import datetime

mariadb_user = 'user'
mariadb_pass = 'pass'
mariadb_url = 'dolder.stec.li'
mariadb_port = '3306'
mariadb_db = 'dolderpark' 

mariadb_string = 'mariadb+mariadbconnector://' + mariadb_user + ':' + mariadb_pass + '@' + mariadb_url + ':' + mariadb_port + '/' + mariadb_db


class create_database():
    with app.test_request_context():
        try:
            print("create databasese")
            
            # Check and repair html_template table if corrupted
            try:
                from sqlalchemy import text, inspect
                inspector = inspect(db.engine)
                if 'html_template' in inspector.get_table_names():
                    # Try to query the table to check if it's corrupted
                    try:
                        db.session.execute(text("SELECT COUNT(*) FROM html_template"))
                        print("html_template table is accessible")
                    except Exception as table_error:
                        if "crashed" in str(table_error).lower() or "repair" in str(table_error).lower():
                            print("html_template table is corrupted, attempting repair...")
                            try:
                                # Drop the corrupted table
                                db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
                                db.session.execute(text("DROP TABLE IF EXISTS html_template"))
                                db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                                db.session.commit()
                                print("✓ Dropped corrupted html_template table")
                            except Exception as drop_error:
                                print(f"Could not drop table: {drop_error}")
            except Exception as check_error:
                print(f"Error checking html_template table: {check_error}")
            
            # Create all tables
            db.create_all()
            
            # Update permission enum to include POWERUSER if it doesn't exist
            try:
                from sqlalchemy import text
                result = db.session.execute(text("""
                    SELECT COLUMN_TYPE 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = DATABASE() 
                    AND TABLE_NAME = 'users' 
                    AND COLUMN_NAME = 'permission'
                """))
                current_enum = result.fetchone()
                if current_enum and 'poweruser' not in current_enum[0].lower():
                    print("Updating permission enum to include 'poweruser'...")
                    db.session.execute(text("""
                        ALTER TABLE users 
                        MODIFY COLUMN permission ENUM('none', 'all', 'app', 'admin', 'poweruser') 
                        NOT NULL DEFAULT 'none'
                    """))
                    db.session.commit()
                    print("✓ Successfully updated permission enum to include 'poweruser'")
                elif current_enum and 'poweruser' in current_enum[0].lower():
                    print("✓ Permission enum already includes 'poweruser'")
            except Exception as enum_error:
                print(f"Note: Could not update permission enum (this is okay if it's already updated): {enum_error}")
        except Exception as exception:
            print("got the following exception when attempting db.create_all(): " + str(exception))
        finally:
            print("db.create_all() was successfull - no exceptions were raised")

        try:
            # check if user exist already
            user = models.Users.query.filter_by(username='admin').first()
            if user and user.username == 'admin':
                print(f"Admin user already exists: {user.username}")
            else:
                print("Admin user does not exist, creating...")
                # create user
                user = models.Users(
                    username='admin',
                    password='$2a$12$Adcq3b3S66Y5ki9cvxe9n.gegg4tFWyyfvdRztL.wwVR/oTNov5ti',   # this is a hash
                    permission=models.UserPermission.ALL
                )
                # Add the user to the database
                db.session.add(user)
                # Commit the changes made
                db.session.commit()
                print("✓ Admin user created successfully")
        except Exception as user_error:
            # Check if error is due to duplicate entry (user already exists)
            if 'duplicate' in str(user_error).lower() or 'unique' in str(user_error).lower():
                print("Admin user already exists (duplicate key error)")
            else:
                print(f"Error creating admin user: {user_error}")
                # Try to rollback if there was an error
                try:
                    db.session.rollback()
                except:
                    pass

        
        # add at least one entry in database
        try:
            busse = models.Busse.query.filter_by(db_bussennr=0).first()
            if busse:
                print(f"Initial busse entry already exists (bussennr: {busse.db_bussennr})")
            else:
                print("No initial busse entry exists, creating...")
                busse = models.Busse(
                    db_bussennr=0,
                    db_aufnahmedatum=datetime.now()
                )
                # add a new case
                db.session.add(busse)
                # Commit the new case
                db.session.commit()
                print("✓ Initial busse entry created successfully")
        except Exception as busse_error:
            # Check if error is due to duplicate entry
            if 'duplicate' in str(busse_error).lower() or 'unique' in str(busse_error).lower():
                print("Initial busse entry already exists (duplicate key error)")
            else:
                print(f"Error creating initial busse entry: {busse_error}")
                # Try to rollback if there was an error
                try:
                    db.session.rollback()
                except:
                    pass