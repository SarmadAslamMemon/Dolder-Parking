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

#from datetime import date
#from docxtpl import DocxTemplate #https://docxtpl.readthedocs.io/  https://medium.com/@lukas.forst/automating-your-job-with-python-89b8878cdef1
#from qrbill import QRBill #https://github.com/claudep/swiss-qr-bill/
#from svglib.svglib import svg2rlg
#from cairosvg import svg2png


UPLOAD_FOLDER = 'static/carpics'
REMI_FOLDER = 'static/rem'
NO_IMAGE = 'static'
EXCEL_FOLDER = 'static/excel'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

dir_path = os.path.dirname(os.path.realpath(__file__))

mariadb_user = os.environ['DB_USER']
mariadb_pass = os.environ['DB_PASS']
mariadb_url = os.environ['DB_URL']
mariadb_port = os.environ['DB_PORT']
mariadb_db = os.environ['DB_NAME']

m_mahn1 = os.environ['M_MAHN1']
m_mahn2 = os.environ['M_MAHN2']
m_mahn3 = os.environ['M_MAHN3']
m_mahn4 = os.environ['M_MAHN4']

mariadb_string = 'mariadb+mariadbconnector://' + mariadb_user + ':' + mariadb_pass + '@' + mariadb_url + ':' + mariadb_port + '/' + mariadb_db

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = mariadb_string #"sqlite:///db.sqlite"
app.config["SECRET_KEY"] = "sadgargea4rt345qtejgfn46z75"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['NO_IMAGE'] = NO_IMAGE
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
# session - using server-side cookie sessions (more reliable in Docker)
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=10)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # Allow cookies in same-site requests
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access
# Comment out filesystem sessions - they don't work reliably in Docker
# app.config['SESSION_TYPE'] = 'filesystem'
# app.config['SESSION_FILE_THRESHOLD'] = 100 

dir_path = os.path.dirname(os.path.realpath(__file__))

db = SQLAlchemy()
engine = create_engine(mariadb_string)


login_manager = LoginManager()
login_manager.init_app(app)

# Session(app)  # Commented out - using Flask's built-in cookie sessions instead
db.init_app(app)
bcrypt = Bcrypt(app) 

# geht ned vor der connector läuft
import db_init, models #, reminder
db_init.create_database()

OnlyOpenCase = True
nextnum = 0

@login_manager.user_loader
def loader_user(user_id):
    return models.Users.query.get(user_id)


@app.route("/login", methods=["GET", "POST"])
def login():
    # If a post request was made, find the user by 
    # filtering for the username
    if request.method == "POST":
        try:
            user = models.Users.query.filter_by(
                username=request.form.get("username")).first()
            # Check if the password entered is t same as the user's password
            if bcrypt.check_password_hash(user.password, request.form.get("password")):
                # Use the login_user method to log in the user
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

        # Redirect the user back to the home
        # (we'll create the home route in a moment)
    return render_template("login.html")
#@limiter_5.limit("5 per minute")    # limit the number of requests to 5 per minute

# check filename is valid and permitted
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# picture size manipulation ( make it square )
def crop_max_square(pil_img):
    return crop_center(pil_img, min(pil_img.size), min(pil_img.size))

def crop_center(pil_img, crop_width, crop_height):
    img_width, img_height = pil_img.size
    return pil_img.crop(((img_width - crop_width) // 2,
                         (img_height - crop_height) // 2,
                         (img_width + crop_width) // 2,
                         (img_height + crop_height) // 2))

@app.route("/s_app", methods=["GET", "POST"])
def s_app():
    # check if the users exist or not
    if not session.get("name"):
        # if not there in the session then redirect to the login page
        return redirect("/login")

    # var need to be global because it should be persistent between button presses
    #global nextnum
    # fill local vars with default values
    doesExist = False
    wrongFile = False
    imgw = 100

    # search last number in database
    try:
        session["actnum"]
        nextnum = session["actnum"]
    except:
        session["actnum"] = None
        nextnum = session["actnum"]

    #intial picture to show
    htmlpath = os.path.join(app.config['NO_IMAGE'], 'no-image-available.jpg')

    if (request.method == 'POST'):
        # increment case nr
        #if request.form.get('nrinc') == 'nrinc':
        #    nextnum = nextnum + 1

        # decrement case nr
        #if request.form.get('nrdec') == 'nrdec':
        #    nextnum = nextnum - 1

        # go directly to number
        if request.form.get('gotonr') == 'gotonr':
            nextnum = request.form['next_bussennr']
            nextnum = int(nextnum)
            session["actnum"] = nextnum

        #if request.form.get('nextfree') == 'nextfree':
        #    busse = models.Busse.query.order_by(models.Busse.db_bussennr.desc()).first()
        #    nextnum = busse.db_bussennr + 1
        #    nextnum = int(nextnum)

    # load picture if available (only if actnum is set)
    if session["actnum"] is not None:
        picpath = os.path.join(dir_path, app.config['UPLOAD_FOLDER'], str(session["actnum"]) + ".png")
        if (os.path.exists(picpath)):
            htmlpath = os.path.join(app.config['UPLOAD_FOLDER'], str(session["actnum"]) + ".png")
        else:
            htmlpath = os.path.join(app.config['NO_IMAGE'], 'no-image-available.jpg')

        # check if case already exists (only if actnum is set)
        try:
            busse = models.Busse.query.filter_by(db_bussennr = session["actnum"]).first()
            test = busse.db_bussennr
            doesExist = True
        except:
            doesExist = False
    else:
        htmlpath = os.path.join(app.config['NO_IMAGE'], 'no-image-available.jpg')
        doesExist = False
        
    if (request.method == 'POST'):

        if request.files:
            if 'file' not in request.files:
                print('No file part')
                wrongFile = True
                
            file = request.files['file']

            # If the user does not select a file, the browser submits an
            # empty file without a filename.
            if file.filename == '':
                print('No selected file')
                wrongFile = True

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # store file extension
                ftype = filename.rsplit('.', 1)[1].lower()
                # original upload name
                oldname = os.path.join(dir_path, app.config['UPLOAD_FOLDER'], filename)
                # save file
                file.save(oldname)
                # resize image (create tumbnail)
                img = Image.open(oldname) # Open image
                img = ImageOps.exif_transpose(img) # check image EXIF data
                img_sq = crop_max_square(img) #.resize((thumb_width, thumb_width), Image.LANCZOS)
                img_sq.thumbnail((500, 500), Image.Resampling.LANCZOS)
                # create thumbnail name to match case nr.
                thumbname = os.path.join(dir_path, app.config['UPLOAD_FOLDER'], str(session["actnum"]) + ".png")
                # make png
                img_sq.save(thumbname, 'PNG' , quality=50)
                # delete original file only if file name is different
                if (thumbname != oldname):
                    os.remove(oldname)
                htmlpath = os.path.join(app.config['UPLOAD_FOLDER'], str(session["actnum"]) + ".png")


        # save case with picture and datetime
        if request.form.get('doneall') == 'doneall':
            print("doneall")
            busse = models.Busse(   db_bussennr         = session["actnum"],
                                    db_aufnahmedatum    = datetime.now(),)
            # add a new case
            db.session.add(busse)
            # Commit the new case
            db.session.commit()
            #session["actnum"]
            #nextnum = session["actnum"] + 1
            htmlpath = os.path.join(app.config['UPLOAD_FOLDER'], str(session["actnum"]) + ".png")
            #htmlpath = os.path.join(app.config['NO_IMAGE'], 'no-image-available.jpg')
            return redirect("/s_app")

        
        # delete picture and start over
        if request.form.get('delall') == 'delall':
            try:
                thumbname = os.path.join(dir_path, app.config['UPLOAD_FOLDER'], str(session["actnum"]) + ".png")
                htmlpath = os.path.join(app.config['NO_IMAGE'], 'no-image-available.jpg')
                os.remove(thumbname)
            except:
                wrongFile = True

    return render_template('s_app.html', nextnum=nextnum, doesExist=doesExist, wrongFile=wrongFile, htmlpath=htmlpath)


# overview site for admins
@app.route("/<num>", methods=["GET", "POST"])
def overview(num):
    # check if the users exist or not
    if not session.get("name"):
        # if not there in the session then redirect to the login page
        return redirect("/login")
    
    # var need to be global because it should be persistent between button presses
    global OnlyOpenCase
    # to show an error if an number is 
    busse_not_found = False
    exportFailed = False
    act_busse = num
    busse = models.Busse.query.filter_by(db_bussennr = act_busse).first()

    # load picture if available
    picpath = os.path.join(dir_path, app.config['UPLOAD_FOLDER'], str(act_busse) + ".png")
    if (os.path.exists(picpath)):
        htmlpath = os.path.join(app.config['UPLOAD_FOLDER'], str(act_busse) + ".png")
    else:
        htmlpath = os.path.join(app.config['NO_IMAGE'], 'no-image-available.jpg')

    if (request.method == 'POST'):
        # search for specific nr
        if request.form.get('search') == 'search':
            new_busse_raw = request.form.get('db_bussennr', '').strip()
            try:
                new_busse_num = int(new_busse_raw)
            except Exception:
                new_busse_num = None

            if new_busse_num is None:
                # invalid/empty input
                busse_not_found = True
            else:
                found = models.Busse.query.filter_by(db_bussennr=new_busse_num).first()
                if found:
                    return redirect("/" + str(found.db_bussennr))
                else:
                    busse_not_found = True
                    # keep showing the current busse
                    busse = models.Busse.query.filter_by(db_bussennr=act_busse).first()

        # jump to newest nr
        if request.form.get('lastnr') == 'lastnr':
            busse = models.Busse.query.order_by(models.Busse.db_bussennr.desc()).first()
            act_busse = busse.db_bussennr
            return redirect("/" + str(act_busse))

        # nr plus
        if request.form.get('nrplus') == 'nrplus':
            # store actual case nr
            old_busse = busse.db_bussennr

            # check checkbox
            if request.form.get('onlyopen'):   
                OnlyOpenCase = True
            else:
                OnlyOpenCase = False

            # search for cases with higher numbers
            try:
                # filter by open cases or not
                if (OnlyOpenCase):
                    busse = models.Busse.query.order_by(models.Busse.db_bussennr.asc()).filter(models.Busse.db_bussennr > old_busse, models.Busse.db_status == 1).first()
                else:
                    busse = models.Busse.query.order_by(models.Busse.db_bussennr.asc()).filter(models.Busse.db_bussennr > old_busse).first()
                return redirect("/" + str(busse.db_bussennr))
            except:
                return redirect("/" + str(old_busse))
        
        # nr minus
        if request.form.get('nrminus') == 'nrminus':
            # store actual case nr
            old_busse = busse.db_bussennr

            # check checkbox
            if request.form.get('onlyopen'):   
                OnlyOpenCase = True
            else:
                OnlyOpenCase = False

            # search for cases with lower numbers    
            try:
                if (OnlyOpenCase):
                    busse = models.Busse.query.order_by(models.Busse.db_bussennr.desc()).filter(models.Busse.db_bussennr < old_busse, models.Busse.db_status == 1).first()
                else:
                    busse = models.Busse.query.order_by(models.Busse.db_bussennr.desc()).filter(models.Busse.db_bussennr < old_busse).first()
                return redirect("/" + str(busse.db_bussennr))
            except:
                return redirect("/" + str(old_busse))

        # modifing values
        if request.form.get('save') == 'save':
            busse.db_nummerschild = request.form['db_nummerschild'] if request.form['db_nummerschild'] else None
            busse.db_mahndatum_1  = datetime.strptime(request.form['db_mahndatum_1'], '%Y-%m-%d') if request.form['db_mahndatum_1'] else None
            busse.db_bezahlt_1    = datetime.strptime(request.form['db_bezahlt_1'], '%Y-%m-%d') if request.form['db_bezahlt_1'] else None
            busse.db_mahndatum_2  = datetime.strptime(request.form['db_mahndatum_2'], '%Y-%m-%d') if request.form['db_mahndatum_2'] else None
            busse.db_bezahlt_2    = datetime.strptime(request.form['db_bezahlt_2'], '%Y-%m-%d') if request.form['db_bezahlt_2'] else None
            busse.db_mahndatum_3  = datetime.strptime(request.form['db_mahndatum_3'], '%Y-%m-%d') if request.form['db_mahndatum_3'] else None
            busse.db_bezahlt_3    = datetime.strptime(request.form['db_bezahlt_3'], '%Y-%m-%d') if request.form['db_bezahlt_3'] else None
            busse.db_anrede       = request.form['db_anrede'] if request.form['db_anrede'] else None
            busse.db_name         = request.form['db_name'] if request.form['db_name'] else None
            busse.db_strasse      = request.form['db_strasse'] if request.form['db_strasse'] else None
            busse.db_zusatz       = request.form['db_zusatz'] if request.form['db_zusatz'] else None
            busse.db_plz          = request.form['db_plz'] if request.form['db_plz'] else None
            busse.db_ort          = request.form['db_ort'] if request.form['db_ort'] else None
            busse.db_land         = request.form['db_land'] if request.form['db_land'] else None
            busse.db_notes        = request.form['db_notes'] if request.form['db_notes'] else None
            db.session.commit()

        # generate reminder1
        if request.form.get('reminder1') == 'reminder1':
            return generate_reminder(1, busse, m_mahn1, dir_path, REMI_FOLDER)
        # generate reminder2
        if request.form.get('reminder2') == 'reminder2':
            return generate_reminder(2, busse, m_mahn2, dir_path, REMI_FOLDER)
        # generate reminder3
        if request.form.get('reminder3') == 'reminder3':
            return generate_reminder(3, busse, m_mahn3, dir_path, REMI_FOLDER)
        # generate reminder4
        if request.form.get('reminder4') == 'reminder4':
            return generate_reminder(4, busse, m_mahn4, dir_path, REMI_FOLDER)

        # close current case
        if request.form.get('close') == 'close':
            busse.db_status = 3
            db.session.commit()

        # cancel current case
        if request.form.get('cancel') == 'cancel':
            busse.db_status = 2
            db.session.commit()

        # reopen current case
        if request.form.get('reopen') == 'reopen':
            busse.db_status = 1
            db.session.commit()

    return render_template('s_overview.html', busse=busse, nfound=busse_not_found, OnlyOpenCase=OnlyOpenCase, htmlpath=htmlpath, exportFailed=exportFailed)

@app.route("/s_reports", methods=["GET", "POST"])
def reports():
    # check if the users exist or not
    if not session.get("name"):
        # if not there in the session then redirect to the login page
        return redirect("/login")
    
    today = date.today()
    # define and reset flag
    dateWrong = False
    exportfailed = False
    exportDone = False
    excel_file = os.path.join(dir_path, EXCEL_FOLDER, 'temp.xlsx')
    try:
        os.remove(excel_file)
    except:
        None

    if (request.method == 'POST'):
        # back to overview page grab last nr
        if request.form.get('back') == 'back':
            # search for last nr
            busse = models.Busse.query.order_by(models.Busse.db_bussennr.desc()).first()
            num = busse.db_bussennr
            page = str(num)
            return redirect(page)
        # generate report and open dialog for export
        if request.form.get('generate') =='generate':
            startDate = request.form['startDate']
            endDate = request.form['endDate']
            # check if both date are present
            if (startDate == '' or endDate == '' or startDate > endDate):
                dateWrong = True
                exportDone = False
            else:
                dateWrong = False
                exportDone = False
                query = text('SELECT * FROM busse WHERE db_aufnahmedatum >= "' + startDate + 'T00:00:00.000" AND db_aufnahmedatum <= "' + endDate + 'T23:59:59.999"')
                print('Startdate: ', startDate)
                print('Enddate:   ', endDate)
                print('Query begin --------------------')
                print(query)
                print('Query end ----------------------')
                excel_file = os.path.join(dir_path, EXCEL_FOLDER, 'temp.xlsx')
                print("execl psth: ", excel_file)
                try:
                    with engine.connect() as conn: 
                        data = conn.execute(query).all()
                        df = pd.DataFrame(data)
                        writer = pd.ExcelWriter(excel_file)
                        df.to_excel(writer, index=False)
                        writer.close()
                        conn.close()
                        exportDone = True
                        #download_path = os.path.join(EXCEL_FOLDER, 'temp.xlsx')
                        return render_template('s_reports.html', today=today, dateWrong=dateWrong, exportfailed=exportfailed, exportDone=exportDone)
                        #return send_file(
                        #    excel_file,
                        #    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        #    download_name='DolderParkExport.xlsx',
                        #    as_attachment=True)
                except Exception as exception:
                    print("got the following exception: " + str(exception))
                    exportfailed = True
                    exportDone = False
                
    # query example
        # SELECT * FROM busse WHERE db_aufnahmedatum >= '2024-09-06T00:00:00.000' AND db_aufnahmedatum <= '2024-09-06T23:59:59.999'


    return render_template('s_reports.html', today=today, dateWrong=dateWrong, exportfailed=exportfailed, exportDone=exportDone)

@app.route('/download')
def download():
    # check if the users exist or not
    if not session.get("name"):
        # if not there in the session then redirect to the login page
        return redirect("/login")

    excel_file = os.path.join(dir_path, EXCEL_FOLDER, 'temp.xlsx')
    return send_file(
        excel_file,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name='DolderParkExport.xlsx',
        as_attachment=True)

@app.route("/s_all")
def all():
  # check if the users exist or not
    if not session.get("name"):
        # if not there in the session then redirect to the login page
        return redirect("/login")

    #busse = models.Busse.query.order_by(models.Busse.db_bussennr.desc()).first()

    return render_template('s_all.html')

@app.route("/logout")
def logout():
    logout_user()
    session["name"] = None
    return redirect(url_for("home"))

@app.route('/register', methods=["GET", "POST"])
def register():
    # check if the users is allowed to create users or not
    if not session.get("name") == "chefstrangetec":
        # if not there in the session then redirect to the login page
        return redirect("/login")

    # If the user made a POST request, create a new user
    if request.method == "POST":
        user = models.Users(username=request.form.get("username"),
                    password=bcrypt.generate_password_hash(request.form.get("password")).decode('utf-8'),
                    permission=request.form.get("permission"),)
        # Add the user to the database
        db.session.add(user)
        # Commit the changes made
        db.session.commit()
        # Once user account created, redirect them
        # to login route (created later on)
        return redirect(url_for("login"))
    # Renders sign_up template if user made a GET request
    return render_template("sign_up.html")

@app.route("/flask-health-check")
def flask_health_check():
    return "success", 200

@app.route("/")
def home():
    #return render_template("home.html")
    return redirect("/login")
    #return render_template("login.html")


#if __name__ == "__main__":
#    app.run(host='0.0.0.0', debug=True, port=5000)