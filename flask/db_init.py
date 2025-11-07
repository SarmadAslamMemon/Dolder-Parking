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
            db.create_all()
        except Exception as exception:
            print("got the following exception when attempting db.create_all(): " + str(exception))
        finally:
            print("db.create_all() was successfull - no exceptions were raised")

        try:
            # check if user exist already
            user = models.Users.query.filter_by(username='admin').first()
            if (user.username == 'admin'):
                print(user.username)
                print("user does exist")
            else:
                user = models.Users(username='admin',
                                password='$2a$12$Adcq3b3S66Y5ki9cvxe9n.gegg4tFWyyfvdRztL.wwVR/oTNov5ti',    # this is a hash
                                permission='all',)
                # Add the user to the database
                db.session.add(user)
                # Commit the changes made
                db.session.commit()
        except:
            print("user does not exist")
            # create user
            user = models.Users(username='admin',
                                password='$2a$12$Adcq3b3S66Y5ki9cvxe9n.gegg4tFWyyfvdRztL.wwVR/oTNov5ti',   # this is a hash
                                permission='all',)
            # Add the user to the database
            db.session.add(user)
            # Commit the changes made
            db.session.commit()

        
        # add at least one entry in database
        try:
            busse = models.Busse.query.filter_by(db_bussennr = 0).first()
            test = busse.db_bussennr
        except:
            print("no entry exsists")
            busse = models.Busse(db_bussennr = 0,
                            db_aufnahmedatum = datetime.now(),)
            # add a new case
            db.session.add(busse)
            # Commit the new case
            db.session.commit()