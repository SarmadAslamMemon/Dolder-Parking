from app_sqlite import db, app
import models
from datetime import datetime

class create_database():
    with app.test_request_context():
        try:
            print("Creating SQLite database...")
            db.create_all()
        except Exception as exception:
            print("Exception during db.create_all(): " + str(exception))
        finally:
            print("db.create_all() completed")

        try:
            # Check if admin user exists
            user = models.Users.query.filter_by(username='admin').first()
            if user and user.username == 'admin':
                print("Admin user already exists")
            else:
                print("Creating admin user...")
                user = models.Users(
                    username='admin',
                    password='$2a$12$Adcq3b3S66Y5ki9cvxe9n.gegg4tFWyyfvdRztL.wwVR/oTNov5ti',  # password: admin
                    permission='all'
                )
                db.session.add(user)
                db.session.commit()
                print("Admin user created successfully")
        except Exception as e:
            print("Error creating admin user: " + str(e))
            # Create user anyway
            user = models.Users(
                username='admin',
                password='$2a$12$Adcq3b3S66Y5ki9cvxe9n.gegg4tFWyyfvdRztL.wwVR/oTNov5ti',  # password: admin
                permission='all'
            )
            db.session.add(user)
            db.session.commit()
            print("Admin user created after error")

        # Add sample data if needed
        try:
            # Check if there are any busse records
            busse_count = models.Busse.query.count()
            if busse_count == 0:
                print("Adding sample busse record...")
                sample_busse = models.Busse(
                    db_bussennr=1,
                    db_status=1,
                    db_date=datetime.now().date(),
                    db_platenr="DEMO-123",
                    db_make="Demo Car",
                    db_model="Sample Model",
                    db_color="Blue",
                    db_location="Demo Location",
                    db_description="This is a demo case for testing purposes"
                )
                db.session.add(sample_busse)
                db.session.commit()
                print("Sample busse record added")
            else:
                print(f"Found {busse_count} existing busse records")
        except Exception as e:
            print("Error adding sample data: " + str(e))

        print("Database initialization completed successfully!")

