import os
import pandas as pd
from flask import Flask, render_template, request, url_for, redirect, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user
from flask_bcrypt import Bcrypt
from flask_session import Session
from PIL import Image, ImageOps
from werkzeug.utils import secure_filename
from sqlalchemy import create_engine, text
from datetime import timedelta, datetime, date
from utils import generate_reminder

UPLOAD_FOLDER = 'static/carpics'
REMI_FOLDER = 'static/rem'
NO_IMAGE = 'static'
EXCEL_FOLDER = 'static/excel'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

dir_path = os.path.dirname(os.path.realpath(__file__))

# Use SQLite for easier deployment
if os.environ.get('SQLITE_MODE') == '1':
    mariadb_string = 'sqlite:///dolderpark.db'
else:
    # Original MariaDB setup
    mariadb_user = os.environ['DB_USER']
    mariadb_pass = os.environ['DB_PASS']
    mariadb_url = os.environ['DB_URL']
    mariadb_port = os.environ['DB_PORT']
    mariadb_db = os.environ['DB_NAME']
    mariadb_string = 'mariadb+mariadbconnector://' + mariadb_user + ':' + mariadb_pass + '@' + mariadb_url + ':' + mariadb_port + '/' + mariadb_db

# Fine amounts
m_mahn1 = os.environ.get('M_MAHN1', '76.20')
m_mahn2 = os.environ.get('M_MAHN2', '91.20')
m_mahn3 = os.environ.get('M_MAHN3', '118.00')
m_mahn4 = os.environ.get('M_MAHN4', '133.00')

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = mariadb_string
app.config["SECRET_KEY"] = "sadgargea4rt345qtejgfn46z75"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['NO_IMAGE'] = NO_IMAGE
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['TEMPLATES_AUTO_RELOAD'] = True

if os.environ.get('FLASK_DEBUG') == '1':
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Session configuration
app.config['SESSION_PERMANENT'] = True
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=10)
app.config['SESSION_FILE_THRESHOLD'] = 100 

dir_path = os.path.dirname(os.path.realpath(__file__))

db = SQLAlchemy()
engine = create_engine(mariadb_string)

login_manager = LoginManager()
login_manager.init_app(app)

Session(app)
db.init_app(app)
bcrypt = Bcrypt(app) 

# Import and initialize database
import db_init_sqlite, models
db_init_sqlite.create_database()

OnlyOpenCase = True
nextnum = 0

@login_manager.user_loader
def loader_user(user_id):
    return models.Users.query.get(user_id)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        try:
            user = models.Users.query.filter_by(
                username=request.form.get("username")).first()
            if bcrypt.check_password_hash(user.password, request.form.get("password")):
                login_user(user)
                session["name"] = request.form.get("username")
                if user.permission == models.UserPermission.ADMIN:
                    busse = models.Busse.query.order_by(models.Busse.db_bussennr.desc()).first()
                    num = busse.db_bussennr
                    page = str(num)
                    return redirect(page)
                elif user.permission == models.UserPermission.APP:
                    return redirect("/s_app")
                elif user.permission == models.UserPermission.ALL:
                    return redirect("/s_all")
                else:
                    logout_user()
                    session["name"] = None
                    return render_template("login.html")
            else:
                logout_user()
                session["name"] = None
                return render_template("pw_wrong.html")
        except Exception as exception:
            print("got the following exception: " + str(exception))
            logout_user()
            session["name"] = None
            return render_template("pw_wrong.html")
    return render_template("login.html")

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        hashed_password = bcrypt.generate_password_hash(password)
        user = models.Users(username=username, password=hashed_password, permission='app')
        db.session.add(user)
        db.session.commit()
        return redirect("/login")
    return render_template("sign_up.html")

@app.route("/logout")
def logout():
    logout_user()
    session["name"] = None
    return redirect("/")

@app.route("/flask-health-check")
def health_check():
    return "OK", 200

# Add all your other routes here...
# (Copy the rest from your original app.py)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=8000, debug=True)

