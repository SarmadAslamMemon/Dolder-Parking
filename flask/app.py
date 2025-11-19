import os
import pandas as pd
from flask import Flask, render_template, request, url_for, redirect, session, send_file, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, current_user
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
    alreadySaved = False
    saveError = None
    imgw = 100

    # Initialize nextnum - empty on GET (page load/reload), use session on POST
    nextnum = None
    
    # Clear all error flags on GET requests (page load/reload)
    if request.method == 'GET':
        doesExist = False
        wrongFile = False
        alreadySaved = False
        saveError = None
        
        # On GET (page load), show the next available number for auto-increment
        # This allows the user to see what the next number will be
        if session.get("nextnum") is not None:
            nextnum = session["nextnum"]
        else:
            # If no nextnum in session, get the highest number + 1
            try:
                last_busse = models.Busse.query.order_by(models.Busse.db_bussennr.desc()).first()
                if last_busse:
                    nextnum = last_busse.db_bussennr + 1
                    session["nextnum"] = nextnum
                else:
                    nextnum = None  # First case, user enters manually
            except:
                nextnum = None
    
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
            if nextnum:
                nextnum = int(nextnum)
                session["actnum"] = nextnum
            else:
                nextnum = None
                session["actnum"] = None

        #if request.form.get('nextfree') == 'nextfree':
        #    busse = models.Busse.query.order_by(models.Busse.db_bussennr.desc()).first()
        #    nextnum = busse.db_bussennr + 1
        #    nextnum = int(nextnum)

    # On POST requests, use session value if available (but not after save redirect)
    # Only set nextnum from session if it's a POST and we're not coming from a save
    if request.method == 'POST' and session.get("actnum") is not None:
        # Check if this is a save operation - if so, don't use the session value
        if request.form.get('doneall') != 'doneall':
            nextnum = session["actnum"]
    
    # load picture if available (only if actnum is set)
    # Always start with no-image placeholder
    htmlpath = os.path.join(app.config['NO_IMAGE'], 'no-image-available.jpg')
    doesExist = False
    
    # Only load image if session has actnum (for POST requests when user is working on a case)
    # On GET requests after save, session is cleared so this won't execute
    if session.get("actnum") is not None:
        # Only load image on POST requests (when user is actively working on a case)
        # On GET requests after save, session is cleared so htmlpath stays as placeholder
        if request.method == 'POST':
            picpath = os.path.join(dir_path, app.config['UPLOAD_FOLDER'], str(session["actnum"]) + ".png")
            if (os.path.exists(picpath)):
                htmlpath = os.path.join(app.config['UPLOAD_FOLDER'], str(session["actnum"]) + ".png")

        # check if case already exists (only if actnum is set)
        try:
            busse = models.Busse.query.filter_by(db_bussennr = session["actnum"]).first()
            test = busse.db_bussennr
            doesExist = True
        except:
            doesExist = False
        
    if (request.method == 'POST'):
        # Check if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('Accept', '').find('application/json') != -1

        if request.files:
            if 'file' not in request.files:
                print('No file part')
                wrongFile = True
                if is_ajax:
                    return jsonify({"error": "Keine Datei ausgewählt"}), 400
                
            file = request.files['file']

            # If the user does not select a file, the browser submits an
            # empty file without a filename.
            if file.filename == '':
                print('No selected file')
                wrongFile = True
                if is_ajax:
                    return jsonify({"error": "Keine Datei ausgewählt"}), 400

            if file and allowed_file(file.filename):
                # Ensure session["actnum"] is set before saving image
                # Priority: 1) Form input, 2) Existing session, 3) Generate new
                upload_case_number = None
                
                # First, try to get from form (if user entered a number)
                if 'next_bussennr' in request.form and request.form['next_bussennr']:
                    try:
                        upload_case_number = int(request.form['next_bussennr'])
                        print(f"[UPLOAD] Got case number from form: {upload_case_number}")
                    except:
                        pass
                
                # If not in form, use existing session value
                if upload_case_number is None and session.get("actnum") is not None:
                    upload_case_number = session["actnum"]
                    print(f"[UPLOAD] Using case number from session: {upload_case_number}")
                
                # If still not set, get next available number
                if upload_case_number is None:
                    try:
                        last_busse = models.Busse.query.order_by(models.Busse.db_bussennr.desc()).first()
                        if last_busse:
                            upload_case_number = last_busse.db_bussennr + 1
                        else:
                            upload_case_number = 1
                        print(f"[UPLOAD] Generated new case number: {upload_case_number}")
                    except Exception as e:
                        print(f"[UPLOAD] Error getting next number: {e}")
                        upload_case_number = 1
                
                # Set session to the determined case number
                session["actnum"] = upload_case_number
                print(f"[UPLOAD] Final case number for image: {upload_case_number}")
                
                filename = secure_filename(file.filename)
                case_number = session["actnum"]
                print(f"[UPLOAD] Processing image for case number: {case_number}")
                print(f"[UPLOAD] Original filename: {file.filename}")
                print(f"[UPLOAD] dir_path: {dir_path}")
                print(f"[UPLOAD] UPLOAD_FOLDER: {app.config['UPLOAD_FOLDER']}")
                
                # Ensure upload directory exists
                upload_dir = os.path.join(dir_path, app.config['UPLOAD_FOLDER'])
                os.makedirs(upload_dir, exist_ok=True)
                print(f"[UPLOAD] Upload directory: {upload_dir}")
                print(f"[UPLOAD] Upload directory exists: {os.path.exists(upload_dir)}")
                
                # store file extension
                ftype = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'png'
                # original upload name (temporary)
                oldname = os.path.join(dir_path, app.config['UPLOAD_FOLDER'], filename)
                print(f"[UPLOAD] Temporary file path: {oldname}")
                
                # save file temporarily
                try:
                    file.save(oldname)
                    print(f"[UPLOAD] ✓ Saved temporary file to: {oldname}")
                    print(f"[UPLOAD] Temporary file exists: {os.path.exists(oldname)}")
                    if os.path.exists(oldname):
                        temp_size = os.path.getsize(oldname)
                        print(f"[UPLOAD] Temporary file size: {temp_size} bytes")
                except Exception as save_error:
                    print(f"[UPLOAD] ✗ ERROR saving temporary file: {save_error}")
                    import traceback
                    traceback.print_exc()
                    if is_ajax:
                        return jsonify({"error": f"Fehler beim Speichern: {str(save_error)}"}), 500
                    wrongFile = True
                    raise
                
                # resize image (create thumbnail)
                try:
                    print(f"[UPLOAD] Opening image: {oldname}")
                    img = Image.open(oldname) # Open image
                    print(f"[UPLOAD] Image opened successfully. Size: {img.size}, Format: {img.format}")
                    img = ImageOps.exif_transpose(img) # check image EXIF data
                    img_sq = crop_max_square(img) #.resize((thumb_width, thumb_width), Image.LANCZOS)
                    img_sq.thumbnail((500, 500), Image.Resampling.LANCZOS)
                    print(f"[UPLOAD] Image processed. New size: {img_sq.size}")
                    
                    # create final filename to match case number: {case_number}.png
                    final_filename = str(case_number) + ".png"
                    thumbname = os.path.join(dir_path, app.config['UPLOAD_FOLDER'], final_filename)
                    print(f"[UPLOAD] Final image path: {thumbname}")
                    
                    # If a file with this name already exists, remove it first
                    if os.path.exists(thumbname):
                        os.remove(thumbname)
                        print(f"[UPLOAD] Removed existing image: {thumbname}")
                    
                    # make png and save with case number as filename
                    print(f"[UPLOAD] Saving image to: {thumbname}")
                    img_sq.save(thumbname, 'PNG', quality=50)
                    print(f"[UPLOAD] ✓ Saved renamed image to: {thumbname}")
                    print(f"[UPLOAD] Image renamed from '{filename}' to '{final_filename}' for case {case_number}")
                    
                    # Verify the file was actually saved
                    if os.path.exists(thumbname):
                        saved_size = os.path.getsize(thumbname)
                        print(f"[UPLOAD] ✓ Image verified! File size: {saved_size} bytes")
                    else:
                        print(f"[UPLOAD] ✗ ERROR: Image was not saved! File does not exist at: {thumbname}")
                        raise Exception(f"Image was not saved to {thumbname}")
                    
                    # delete original temporary file
                    if (thumbname != oldname) and os.path.exists(oldname):
                        os.remove(oldname)
                        print(f"[UPLOAD] Removed temporary file: {oldname}")
                    
                except Exception as img_error:
                    print(f"[UPLOAD] ✗ Error processing image: {img_error}")
                    import traceback
                    traceback.print_exc()
                    # Clean up temporary file
                    if os.path.exists(oldname):
                        try:
                            os.remove(oldname)
                            print(f"[UPLOAD] Cleaned up temporary file: {oldname}")
                        except:
                            pass
                    if is_ajax:
                        return jsonify({"error": f"Fehler beim Verarbeiten des Bildes: {str(img_error)}"}), 500
                    wrongFile = True
                    raise
                
                htmlpath = os.path.join(app.config['UPLOAD_FOLDER'], str(case_number) + ".png")
                
                # Verify image was saved with correct name
                if os.path.exists(thumbname):
                    file_size = os.path.getsize(thumbname)
                    print(f"[UPLOAD] ✓ Image verified at: {thumbname}")
                    print(f"[UPLOAD] ✓ File size: {file_size} bytes")
                    print(f"[UPLOAD] ✓ Final filename: {final_filename}")
                else:
                    print(f"[UPLOAD] ✗ ERROR: Image not found at: {thumbname}")
                    raise Exception(f"Image was not saved correctly to {thumbname}")
                
                # Return JSON for AJAX requests
                if is_ajax:
                    return jsonify({
                        "success": True,
                        "message": "Bild erfolgreich hochgeladen!",
                        "image_path": htmlpath,
                        "case_number": session["actnum"]
                    }), 200
            else:
                wrongFile = True
                if is_ajax:
                    return jsonify({"error": "Ungültiges Dateiformat"}), 400


        # save case with picture and datetime
        if request.form.get('doneall') == 'doneall':
            print("doneall")
            # Check if this is an AJAX request
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('Accept', '').find('application/json') != -1
            
            # IMPORTANT: Set session["actnum"] from form input FIRST (like original code)
            # This ensures the image path matches the case number being saved
            if 'next_bussennr' in request.form and request.form['next_bussennr']:
                try:
                    nextnum = int(request.form['next_bussennr'])
                    session["actnum"] = nextnum
                    print(f"[SAVE] Set session actnum from form: {nextnum}")
                except:
                    pass  # If conversion fails, use existing logic
            
            # Check if actnum is set, if not get the next available number
            if session.get("actnum") is None:
                # Get the highest busse number and increment
                try:
                    last_busse = models.Busse.query.order_by(models.Busse.db_bussennr.desc()).first()
                    if last_busse:
                        session["actnum"] = last_busse.db_bussennr + 1
                    else:
                        session["actnum"] = 1
                    print(f"[SAVE] Generated new actnum: {session['actnum']}")
                except:
                    session["actnum"] = 1
                    print(f"[SAVE] Set default actnum: 1")
            
            if session["actnum"] is not None:
                # Check if case already exists before saving
                existing_busse = models.Busse.query.filter_by(db_bussennr=session["actnum"]).first()
                
                if existing_busse:
                    # Case already exists - return JSON error for AJAX
                    if is_ajax:
                        return jsonify({"error": f"Fall {session['actnum']} wurde bereits gespeichert!"}), 400
                    # Case already exists - set error flags
                    alreadySaved = True
                    saveError = f"Fall {session['actnum']} wurde bereits gespeichert!"
                    # Keep the session actnum so user can see the error
                    # Don't clear session yet
                else:
                    # Case doesn't exist - proceed with saving
                    try:
                        case_number = session["actnum"]
                        print(f"[SAVE] Attempting to save case number: {case_number}")
                        
                        # Get license plate number from form if provided
                        license_plate = request.form.get('db_nummerschild', '').strip() if 'db_nummerschild' in request.form else None
                        print(f"[SAVE] Form data received:")
                        print(f"      - next_bussennr: {request.form.get('next_bussennr', 'N/A')}")
                        print(f"      - db_nummerschild: {request.form.get('db_nummerschild', 'N/A')}")
                        if license_plate:
                            print(f"[SAVE] License plate detected: {license_plate}")
                        else:
                            print(f"[SAVE] No license plate in form data")
                        
                        # Check if image exists for this case
                        image_path = os.path.join(dir_path, app.config['UPLOAD_FOLDER'], str(case_number) + ".png")
                        image_exists = os.path.exists(image_path)
                        print(f"[SAVE] Checking for image at: {image_path}")
                        print(f"[SAVE] Image exists: {image_exists}")
                        
                        # If image doesn't exist, try to find and rename any uploaded image
                        if not image_exists:
                            print(f"[SAVE] ⚠ Image not found for case {case_number}, searching for uploaded images...")
                            
                            # Check if there's a file upload in this request
                            if request.files and 'file' in request.files:
                                uploaded_file = request.files['file']
                                if uploaded_file.filename:
                                    print(f"[SAVE] Found file upload in save request: {uploaded_file.filename}")
                                    # Save the image now with the correct case number
                                    try:
                                        filename = secure_filename(uploaded_file.filename)
                                        temp_path = os.path.join(dir_path, app.config['UPLOAD_FOLDER'], filename)
                                        uploaded_file.save(temp_path)
                                        
                                        # Process and rename to case number
                                        img = Image.open(temp_path)
                                        img = ImageOps.exif_transpose(img)
                                        img_sq = crop_max_square(img)
                                        img_sq.thumbnail((500, 500), Image.Resampling.LANCZOS)
                                        
                                        # Save with case number
                                        img_sq.save(image_path, 'PNG', quality=50)
                                        print(f"[SAVE] ✓ Saved image during save operation: {image_path}")
                                        
                                        # Remove temp file
                                        if os.path.exists(temp_path) and temp_path != image_path:
                                            os.remove(temp_path)
                                        
                                        image_exists = True
                                    except Exception as img_save_error:
                                        print(f"[SAVE] ✗ Error saving image during save: {img_save_error}")
                            
                            # If still no image, check for any recently uploaded files that might need renaming
                            if not image_exists:
                                # Look for images in the upload folder that might need to be renamed
                                upload_dir = os.path.join(dir_path, app.config['UPLOAD_FOLDER'])
                                if os.path.exists(upload_dir):
                                    # Check if there's an image that was just uploaded (check by modification time)
                                    try:
                                        import time
                                        all_files = os.listdir(upload_dir)
                                        png_files = [f for f in all_files if f.endswith('.png')]
                                        if png_files:
                                            # Get the most recently modified PNG file
                                            png_files_with_time = []
                                            for f in png_files:
                                                file_path = os.path.join(upload_dir, f)
                                                mtime = os.path.getmtime(file_path)
                                                png_files_with_time.append((f, mtime, file_path))
                                            
                                            # Sort by modification time (newest first)
                                            png_files_with_time.sort(key=lambda x: x[1], reverse=True)
                                            
                                            # Check the most recent file (might be the uploaded one)
                                            if png_files_with_time:
                                                recent_file, recent_mtime, recent_path = png_files_with_time[0]
                                                # If file was modified in the last 5 minutes, it might be the uploaded one
                                                if (time.time() - recent_mtime) < 300:  # 5 minutes
                                                    # Check if it's not already the correct name
                                                    if recent_file != str(case_number) + ".png":
                                                        print(f"[SAVE] Found recently uploaded image: {recent_file}, renaming to {case_number}.png")
                                                        try:
                                                            # Copy/rename the file
                                                            img = Image.open(recent_path)
                                                            img = ImageOps.exif_transpose(img)
                                                            img_sq = crop_max_square(img)
                                                            img_sq.thumbnail((500, 500), Image.Resampling.LANCZOS)
                                                            img_sq.save(image_path, 'PNG', quality=50)
                                                            print(f"[SAVE] ✓ Renamed and saved image: {image_path}")
                                                            # Remove old file
                                                            if recent_path != image_path:
                                                                os.remove(recent_path)
                                                            image_exists = True
                                                        except Exception as rename_error:
                                                            print(f"[SAVE] ✗ Error renaming image: {rename_error}")
                                    except Exception as search_error:
                                        print(f"[SAVE] ✗ Error searching for images: {search_error}")
                        
                        if not image_exists:
                            print(f"[SAVE] ⚠ WARNING: Image file not found for case {case_number}")
                            print(f"[SAVE] ⚠ Image path checked: {image_path}")
                            print(f"[SAVE] Case will be saved, but NO IMAGE will be associated")
                        else:
                            print(f"[SAVE] ✓ Image file confirmed at: {image_path}")
                            file_size = os.path.getsize(image_path)
                            print(f"[SAVE] ✓ Image file size: {file_size} bytes")
                        
                        busse = models.Busse(   db_bussennr         = case_number,
                                                db_aufnahmedatum    = datetime.now(),
                                                db_nummerschild     = license_plate if license_plate else None)
                        # add a new case
                        db.session.add(busse)
                        # Commit the new case
                        db.session.commit()
                        print(f"[SAVE] Committed to database")
                        
                        # Verify the save was successful by querying the database
                        saved_busse = models.Busse.query.filter_by(db_bussennr=case_number).first()
                        if saved_busse:
                            print(f"[SAVE] ✓ Successfully saved case {case_number} to database.")
                            print(f"      - ID: {saved_busse.id}")
                            print(f"      - Date: {saved_busse.db_aufnahmedatum}")
                            print(f"      - License Plate: {saved_busse.db_nummerschild or 'N/A'}")
                            
                            # Final check for image after save
                            final_image_check = os.path.exists(image_path)
                            print(f"      - Image file exists: {'Yes' if final_image_check else 'No'}")
                            if final_image_check:
                                file_size = os.path.getsize(image_path)
                                print(f"      - Image file size: {file_size} bytes")
                                print(f"      - Image path: {image_path}")
                            else:
                                print(f"      - Image NOT FOUND at: {image_path}")
                            
                            # Double-check license plate was saved
                            if license_plate and saved_busse.db_nummerschild != license_plate:
                                print(f"[SAVE] ✗ ERROR: License plate mismatch!")
                                print(f"      Expected: {license_plate}")
                                print(f"      Got: {saved_busse.db_nummerschild}")
                        else:
                            print(f"[SAVE] ✗ WARNING: Case {case_number} was not found in database after commit!")
                        
                        htmlpath = os.path.join(app.config['UPLOAD_FOLDER'], str(case_number) + ".png")
                        
                        # After saving, set nextnum to the next available number for auto-increment
                        # Get the highest busse number and set it as the next number
                        try:
                            last_busse = models.Busse.query.order_by(models.Busse.db_bussennr.desc()).first()
                            if last_busse:
                                next_available = last_busse.db_bussennr + 1
                            else:
                                next_available = 1
                            session["nextnum"] = next_available
                            print(f"[SAVE] Set nextnum for auto-increment: {next_available}")
                        except:
                            session["nextnum"] = case_number + 1
                        
                        # Clear session actnum after saving to reset page to initial state
                        session["actnum"] = None
                        
                        # Calculate next number for auto-increment
                        next_number = case_number + 1
                        
                        # Return JSON success for AJAX requests
                        if is_ajax:
                            return jsonify({
                                "success": True, 
                                "message": f"Fall {case_number} erfolgreich gespeichert!",
                                "case_number": case_number,
                                "next_number": next_number,
                                "license_plate": license_plate,
                                "image_saved": image_exists
                            }), 200
                        
                        return redirect("/s_app")
                    except Exception as e:
                        # Database error occurred
                        print(f"[SAVE] ✗ Error saving case: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        if is_ajax:
                            return jsonify({"error": f"Fehler beim Speichern: {str(e)}"}), 500
                        saveError = f"Fehler beim Speichern: {str(e)}"
                        alreadySaved = False
            
            # If we reach here, there was an error - return JSON for AJAX or render template
            if is_ajax:
                return jsonify({"error": saveError or "Unbekannter Fehler"}), 400
            # Don't redirect, show error on same page

        
        # delete picture and start over
        if request.form.get('delall') == 'delall':
            # Check if this is an AJAX request
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('Accept', '').find('application/json') != -1
            
            try:
                if session.get("actnum") is not None:
                    thumbname = os.path.join(dir_path, app.config['UPLOAD_FOLDER'], str(session["actnum"]) + ".png")
                    if os.path.exists(thumbname):
                        os.remove(thumbname)
                
                htmlpath = os.path.join(app.config['NO_IMAGE'], 'no-image-available.jpg')
                
                # Return JSON for AJAX requests
                if is_ajax:
                    return jsonify({"success": True, "message": "Bild wurde gelöscht"}), 200
            except Exception as e:
                if is_ajax:
                    return jsonify({"error": f"Fehler beim Löschen: {str(e)}"}), 500
                wrongFile = True

    return render_template('s_app.html', nextnum=nextnum, doesExist=doesExist, wrongFile=wrongFile, htmlpath=htmlpath, alreadySaved=alreadySaved, saveError=saveError)


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
    if not session.get("name") == "admin":
        # if not there in the session then redirect to the login page
        return redirect("/login")

    # Handle POST requests
    if request.method == "POST":
        # Check if this is a user creation request
        if request.form.get("action") == "create_user":
            try:
                username = request.form.get("username", "").strip()
                password = request.form.get("password", "").strip()
                permission = request.form.get("permission", "").strip()
                
                # Validate inputs
                if not username:
                    flash("Username is required.", "error")
                    return redirect("/register")
                if not password:
                    flash("Password is required.", "error")
                    return redirect("/register")
                if not permission:
                    flash("Permission level is required.", "error")
                    return redirect("/register")
                
                # Check if username already exists
                existing_user = models.Users.query.filter_by(username=username).first()
                if existing_user:
                    flash(f"Username '{username}' already exists.", "error")
                    return redirect("/register")
                
                # Create new user
                user = models.Users(
                    username=username,
                    password=bcrypt.generate_password_hash(password).decode('utf-8'),
                    permission=models.UserPermission[permission.upper()] if permission.upper() in ['NONE', 'APP', 'ADMIN', 'ALL'] else models.UserPermission.NONE
                )
                db.session.add(user)
                db.session.commit()
                flash(f"User '{username}' created successfully.", "success")
                return redirect("/register")
            except Exception as e:
                db.session.rollback()
                print(f"Error creating user: {e}")
                flash(f"Error creating user: {str(e)}", "error")
                return redirect("/register")
        
        # Check if this is a user edit request
        elif request.form.get("action") == "edit_user":
            try:
                user_id = request.form.get("user_id")
                if not user_id:
                    flash("User ID is required.", "error")
                    return redirect("/register")
                
                user = models.Users.query.get(int(user_id))
                if not user:
                    flash("User not found.", "error")
                    return redirect("/register")
                
                # Update password if provided
                new_password = request.form.get("password", "").strip()
                if new_password:
                    user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
                
                # Update permission if provided
                new_permission = request.form.get("permission", "").strip()
                if new_permission and new_permission.upper() in ['NONE', 'APP', 'ADMIN', 'ALL']:
                    user.permission = models.UserPermission[new_permission.upper()]
                
                # Update disabled status
                disabled = request.form.get("disabled") == "true"
                user.disabled = disabled
                
                db.session.commit()
                flash(f"User '{user.username}' updated successfully.", "success")
                return redirect("/register")
            except Exception as e:
                db.session.rollback()
                print(f"Error updating user: {e}")
                flash(f"Error updating user: {str(e)}", "error")
                return redirect("/register")
        
        # Check if this is a delete/disable request
        elif request.form.get("action") == "delete_user":
            try:
                user_id = request.form.get("user_id")
                if not user_id:
                    flash("User ID is required.", "error")
                    return redirect("/register")
                
                user = models.Users.query.get(int(user_id))
                if not user:
                    flash("User not found.", "error")
                    return redirect("/register")
                
                # Prevent deleting yourself
                if user.id == current_user.id:
                    flash("You cannot disable your own account.", "error")
                    return redirect("/register")
                
                # Soft delete by disabling
                user.disabled = True
                db.session.commit()
                flash(f"User '{user.username}' has been disabled.", "success")
                return redirect("/register")
            except Exception as e:
                db.session.rollback()
                print(f"Error disabling user: {e}")
                flash(f"Error disabling user: {str(e)}", "error")
                return redirect("/register")
        
        # Check if this is an enable request
        elif request.form.get("action") == "enable_user":
            try:
                user_id = request.form.get("user_id")
                if not user_id:
                    flash("User ID is required.", "error")
                    return redirect("/register")
                
                user = models.Users.query.get(int(user_id))
                if not user:
                    flash("User not found.", "error")
                    return redirect("/register")
                
                user.disabled = False
                db.session.commit()
                flash(f"User '{user.username}' has been enabled.", "success")
                return redirect("/register")
            except Exception as e:
                db.session.rollback()
                print(f"Error enabling user: {e}")
                flash(f"Error enabling user: {str(e)}", "error")
                return redirect("/register")
    
    # GET request - show user management page with all users
    try:
        users = models.Users.query.order_by(models.Users.id.asc()).all()
    except Exception as e:
        print(f"Error fetching users: {e}")
        users = []
    
    return render_template("user_management_register.html", users=users)

@app.route("/flask-health-check")
def flask_health_check():
    return "success", 200

# Import and register upload routes
from upload_routes import register_upload_routes
register_upload_routes(app, db)

# Import and register logo routes
try:
    from logo_routes import register_logo_routes, get_active_logo_path, get_logo_width, get_logo_height
    register_logo_routes(app, db)
    # Make logo functions available to templates
    app.jinja_env.globals['get_active_logo_path'] = get_active_logo_path
    app.jinja_env.globals['get_logo_width'] = get_logo_width
    app.jinja_env.globals['get_logo_height'] = get_logo_height
    print("Logo upload routes registered successfully")
except Exception as e:
    print(f"Warning: Failed to register logo routes: {e}")
    print("Logo upload functionality will not be available")
    import traceback
    traceback.print_exc()
    # Fallback functions for templates
    def get_active_logo_path():
        return 'applogo.png'
    def get_logo_width():
        return 'auto'
    def get_logo_height():
        return '2.5rem'
    app.jinja_env.globals['get_active_logo_path'] = get_active_logo_path
    app.jinja_env.globals['get_logo_width'] = get_logo_width
    app.jinja_env.globals['get_logo_height'] = get_logo_height

# Import and register plate extraction routes
try:
    from plate_extraction_routes import register_plate_extraction_routes
    register_plate_extraction_routes(app)
    print("Plate extraction routes registered successfully")
except Exception as e:
    print(f"Warning: Failed to register plate extraction routes: {e}")
    print("Plate extraction functionality will not be available")
    import traceback
    traceback.print_exc()

# Import and register user management routes
try:
    from user_routes import register_user_routes
    register_user_routes(app)
    print("User management routes registered successfully")
except Exception as e:
    print(f"Warning: Failed to register user management routes: {e}")
    print("User management functionality will not be available")
    import traceback
    traceback.print_exc()

@app.route("/")
def home():
    #return render_template("home.html")
    return redirect("/login")
    #return render_template("login.html")


#if __name__ == "__main__":
#    app.run(host='0.0.0.0', debug=True, port=5000)