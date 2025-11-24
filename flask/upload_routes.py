from flask import render_template, request, redirect, session, send_file, Response
from flask_login import current_user
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import json
import models

REMI_FOLDER = 'static/rem'
ALLOWED_EXTENSIONS = ['doc', 'docx']
TEMPLATE_CONFIG_FILE = 'template_config.json'

# Protected system files that cannot be deleted
PROTECTED_FILES = [
    '1_mahnung_vorlage.docx',
    '2_mahnung_vorlage.docx',
    '3_mahnung_vorlage.docx',
    '4_mahnung_vorlage.docx',
    'reminder.docx'
]

def allowed_file(filename):
    """Check if file has an allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def is_protected_file(filename):
    """Check if file is a protected system file"""
    return filename in PROTECTED_FILES

def get_template_config_path():
    """Get the path to the template config file"""
    dir_path = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(dir_path, TEMPLATE_CONFIG_FILE)

def get_template_config():
    """Get the full template config dictionary"""
    config_path = get_template_config_path()
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading template config: {e}")
    return {}

def save_template_config(config):
    """Save the template config dictionary"""
    config_path = get_template_config_path()
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error writing template config: {e}")
        return False

def get_active_template():
    """Get the active template filename from config, only if file exists"""
    config = get_template_config()
    active_template = config.get('active_template')
    if active_template:
        # Verify the file still exists
        dir_path = os.path.dirname(os.path.realpath(__file__))
        rem_folder_path = os.path.join(dir_path, REMI_FOLDER)
        file_path = os.path.join(rem_folder_path, active_template)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return active_template
        else:
            # File doesn't exist, clear the active template
            print(f"Active template file '{active_template}' not found, clearing active template")
            set_active_template(None)
            return None
    return None

def set_active_template(filename):
    """Set the active template filename in config (None to clear)"""
    config = get_template_config()
    if filename is None:
        # Clear active template
        config['active_template'] = None
    else:
        config['active_template'] = filename
    return save_template_config(config)

def get_button_name(filename):
    """Get the button name for a template file, or return filename if not set"""
    config = get_template_config()
    button_names = config.get('button_names', {})
    return button_names.get(filename, filename)

def set_button_name(filename, button_name):
    """Set the button name for a template file"""
    config = get_template_config()
    if 'button_names' not in config:
        config['button_names'] = {}
    config['button_names'][filename] = button_name
    return save_template_config(config)

def get_active_template_path():
    """Get the full path to the active template file, or None if not set"""
    active_template = get_active_template()
    if active_template:
        dir_path = os.path.dirname(os.path.realpath(__file__))
        rem_folder_path = os.path.join(dir_path, REMI_FOLDER)
        file_path = os.path.join(rem_folder_path, active_template)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return file_path
    return None

def get_active_template_button_name():
    """Get the button name for the active template, or filename if not set"""
    active_template = get_active_template()
    if active_template:
        return get_button_name(active_template)
    return None

def register_upload_routes(app, db):
    """Register upload template routes with the Flask app"""
    
    @app.route("/upload_template", methods=["GET", "POST"])
    def upload_template():
        # check if the users exist or not
        if not session.get("name"):
            # if not there in the session then redirect to the login page
            return redirect("/login")
        
        # Check if user has ADMIN or ALL permission
        if current_user.is_authenticated:
            if current_user.permission not in [models.UserPermission.ADMIN, models.UserPermission.ALL]:
                return redirect("/s_all")
        else:
            return redirect("/login")
        
        # Get the directory path
        dir_path = os.path.dirname(os.path.realpath(__file__))
        rem_folder_path = os.path.join(dir_path, REMI_FOLDER)
        
        # Ensure the rem folder exists
        os.makedirs(rem_folder_path, exist_ok=True)
        
        if request.method == 'POST':
            # Handle POST request - process upload and redirect
            if 'html_file' not in request.files:
                session['upload_error'] = "Keine Datei ausgewählt."
                return redirect("/upload_template")
            
            file = request.files['html_file']
            if file.filename == '':
                session['upload_error'] = "Keine Datei ausgewählt."
                return redirect("/upload_template")
            
            # Check file type - only DOC/DOCX allowed
            if not allowed_file(file.filename):
                session['upload_error'] = "Nur DOC und DOCX-Dateien sind erlaubt."
                return redirect("/upload_template")
            
            try:
                # Get secure filename (use original filename as-is)
                filename = secure_filename(file.filename)
                
                # Save file to static/rem folder
                file_path = os.path.join(rem_folder_path, filename)
                
                # Check if file already exists
                file_existed = os.path.exists(file_path)
                
                # If file already exists, remove it first (all files can be replaced)
                if file_existed:
                    # Remove existing file to replace it
                    os.remove(file_path)
                
                # Save the file
                file.save(file_path)
                
                # Verify file was saved
                if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
                    session['upload_error'] = "Fehler beim Speichern der Datei."
                    return redirect("/upload_template")
                
                # Success message
                action = "ersetzt" if file_existed else "hochgeladen"
                session['upload_success'] = f"Datei '{filename}' wurde erfolgreich {action}."
                
                return redirect("/upload_template")
                
            except Exception as exception:
                error_msg = str(exception)
                print("Error uploading file: " + error_msg)
                session['upload_error'] = f"Fehler beim Speichern der Datei: {error_msg}"
                return redirect("/upload_template")
        
        # Handle GET request - display form and messages
        success_message = None
        error_message = None
        
        # Get messages from session and clear them
        if 'upload_success' in session:
            success_message = session.pop('upload_success')
        if 'upload_error' in session:
            error_message = session.pop('upload_error')
        if 'delete_success' in session:
            success_message = session.pop('delete_success')
        if 'delete_error' in session:
            error_message = session.pop('delete_error')
        
        return render_template('upload_template.html', 
                             success_message=success_message, 
                             error_message=error_message)

    @app.route("/download_template/<filename>")
    def download_template(filename):
        # check if the users exist or not
        if not session.get("name"):
            return redirect("/login")
        
        # Check if user has ADMIN or ALL permission
        if current_user.is_authenticated:
            if current_user.permission not in [models.UserPermission.ADMIN, models.UserPermission.ALL]:
                return redirect("/s_all")
        else:
            return redirect("/login")
        
        try:
            dir_path = os.path.dirname(os.path.realpath(__file__))
            rem_folder_path = os.path.join(dir_path, REMI_FOLDER)
            file_path = os.path.join(rem_folder_path, secure_filename(filename))
            
            # Security check: ensure file is in the rem folder
            if not os.path.abspath(file_path).startswith(os.path.abspath(rem_folder_path)):
                return "Zugriff verweigert.", 403
            
            if os.path.exists(file_path) and os.path.isfile(file_path):
                # Determine MIME type
                file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
                mime_types = {
                    'doc': 'application/msword',
                    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                }
                mime_type = mime_types.get(file_ext, 'application/octet-stream')
                
                return send_file(file_path, mimetype=mime_type, as_attachment=True, download_name=filename)
            else:
                return "Datei nicht gefunden.", 404
        except Exception as e:
            print(f"Error downloading file: {e}")
            return f"Fehler beim Herunterladen: {str(e)}", 500

    @app.route("/delete_template/<filename>", methods=["POST"])
    def delete_template(filename):
        # check if the users exist or not
        if not session.get("name"):
            # if not there in the session then redirect to the login page
            return redirect("/login")
        
        # Check if user has ADMIN or ALL permission
        if current_user.is_authenticated:
            if current_user.permission not in [models.UserPermission.ADMIN, models.UserPermission.ALL]:
                return redirect("/s_all")
        else:
            return redirect("/login")
        
        try:
            dir_path = os.path.dirname(os.path.realpath(__file__))
            rem_folder_path = os.path.join(dir_path, REMI_FOLDER)
            secure_name = secure_filename(filename)
            file_path = os.path.join(rem_folder_path, secure_name)
            
            # Security check: ensure file is in the rem folder
            if not os.path.abspath(file_path).startswith(os.path.abspath(rem_folder_path)):
                session['delete_error'] = "Zugriff verweigert."
                return redirect("/upload_template")
            
            # Check if file is protected
            if is_protected_file(secure_name):
                session['delete_error'] = "Diese Datei ist geschützt und kann nicht gelöscht werden."
                return redirect("/upload_template")
            
            if os.path.exists(file_path) and os.path.isfile(file_path):
                # Check if this is the active template and clear it if so
                active_template = get_active_template()
                if active_template == secure_name:
                    print(f"Deleting active template '{secure_name}', clearing active template setting")
                    set_active_template(None)
                
                os.remove(file_path)
                session['delete_success'] = f"Datei '{secure_name}' wurde erfolgreich gelöscht."
            else:
                session['delete_error'] = "Datei nicht gefunden."
        except Exception as exception:
            print("Error deleting file: " + str(exception))
            session['delete_error'] = "Fehler beim Löschen der Datei."
        
        return redirect("/upload_template")

    @app.route("/set_active_template/<filename>", methods=["POST"])
    def set_active_template_route(filename):
        # check if the users exist or not
        if not session.get("name"):
            return redirect("/login")
        
        # Check if user has ADMIN or ALL permission
        if current_user.is_authenticated:
            if current_user.permission not in [models.UserPermission.ADMIN, models.UserPermission.ALL]:
                return redirect("/s_all")
        else:
            return redirect("/login")
        
        try:
            dir_path = os.path.dirname(os.path.realpath(__file__))
            rem_folder_path = os.path.join(dir_path, REMI_FOLDER)
            secure_name = secure_filename(filename)
            file_path = os.path.join(rem_folder_path, secure_name)
            
            # Security check: ensure file is in the rem folder
            if not os.path.abspath(file_path).startswith(os.path.abspath(rem_folder_path)):
                session['upload_error'] = "Zugriff verweigert."
                return redirect("/upload_template")
            
            # Check if file exists
            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                session['upload_error'] = "Datei nicht gefunden."
                return redirect("/upload_template")
            
            # Set as active template
            if set_active_template(secure_name):
                session['upload_success'] = f"Datei '{secure_name}' wurde als aktiv gesetzt und wird in der Übersicht verwendet."
            else:
                session['upload_error'] = "Fehler beim Setzen der aktiven Datei."
        except Exception as exception:
            print("Error setting active template: " + str(exception))
            session['upload_error'] = "Fehler beim Setzen der aktiven Datei."
        
        return redirect("/upload_template")
