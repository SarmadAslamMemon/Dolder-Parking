from flask import render_template, request, redirect, session, send_file, Response
from flask_login import current_user
from datetime import datetime
import os
import stat
import shutil
import tempfile
import subprocess
import time
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

# Mapping for special upload filenames to actual stored filenames
UPLOAD_FILENAME_MAPPING = {
    '1.docx': '1_mahnung_vorlage.docx',
    '2.docx': '2_mahnung_vorlage.docx',
    '3.docx': '3_mahnung_vorlage.docx',
    '4.docx': '4_mahnung_vorlage.docx'
}

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
        
        # Ensure the rem folder exists with proper permissions
        os.makedirs(rem_folder_path, exist_ok=True)
        try:
            # Ensure the directory is writable (0o755 = rwxr-xr-x)
            os.chmod(rem_folder_path, 0o755)
        except Exception as chmod_error:
            print(f"Warning: Could not set directory permissions: {chmod_error}")
        
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
                # Get original filename and secure version
                original_filename = file.filename
                uploaded_filename = secure_filename(original_filename)
                
                # Check if secure_filename changed the filename
                if uploaded_filename != original_filename:
                    print(f"Filename sanitized: '{original_filename}' -> '{uploaded_filename}'")
                
                # Check if this is a special filename that needs mapping
                # If user uploads 1.docx, 2.docx, 3.docx, or 4.docx, map to *_mahnung_vorlage.docx
                if uploaded_filename in UPLOAD_FILENAME_MAPPING:
                    filename = UPLOAD_FILENAME_MAPPING[uploaded_filename]
                else:
                    # Use the secure filename (sanitized version)
                    filename = uploaded_filename
                
                # Save file to static/rem folder
                file_path = os.path.join(rem_folder_path, filename)
                
                # Clean up any leftover temp files from previous failed uploads
                try:
                    for item in os.listdir(rem_folder_path):
                        if item.startswith('.tmp_upload_'):
                            temp_item_path = os.path.join(rem_folder_path, item)
                            try:
                                # Only remove if it's a file and older than 1 hour (in case it's still being used)
                                if os.path.isfile(temp_item_path):
                                    file_age = os.path.getmtime(temp_item_path)
                                    if time.time() - file_age > 3600:  # 1 hour
                                        os.remove(temp_item_path)
                                        print(f"Cleaned up old temp file: {temp_item_path}")
                            except Exception as cleanup_error:
                                print(f"Could not clean up temp file {temp_item_path}: {cleanup_error}")
                except Exception as cleanup_error:
                    print(f"Error during temp file cleanup: {cleanup_error}")
                
                # Check if file already exists
                file_existed = os.path.exists(file_path)
                
                # Save to a temporary file first, then move it (this handles permissions better)
                temp_file = None
                try:
                    # Get the file extension from the original filename
                    file_ext = os.path.splitext(filename)[1] or '.docx'
                    # Create a temporary file in the same directory with the correct extension
                    temp_fd, temp_file = tempfile.mkstemp(
                        suffix=file_ext,
                        dir=rem_folder_path,
                        prefix='.tmp_upload_'
                    )
                    os.close(temp_fd)  # Close the file descriptor, we'll use the path
                    
                    # Save the uploaded file to the temporary location
                    file.save(temp_file)
                    
                    # Verify the temp file was saved correctly
                    if not os.path.exists(temp_file):
                        session['upload_error'] = f"Fehler beim Speichern der Datei: Temporäre Datei konnte nicht erstellt werden."
                        return redirect("/upload_template")
                    
                    temp_file_size = os.path.getsize(temp_file)
                    if temp_file_size == 0:
                        if temp_file and os.path.exists(temp_file):
                            os.remove(temp_file)
                        session['upload_error'] = f"Fehler beim Speichern der Datei: Die hochgeladene Datei ist leer."
                        return redirect("/upload_template")
                    
                    print(f"Temp file saved successfully: {temp_file} ({temp_file_size} bytes)")
                    
                    # If file already exists, try multiple methods to replace it
                    if file_existed:
                        replaced = False
                        
                        # Method 1: Try to make writable and remove, then move temp file
                        try:
                            current_permissions = os.stat(file_path).st_mode
                            # Add write permission for owner, group, and others
                            os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)
                            os.remove(file_path)
                            # Now move the temp file to the target location
                            shutil.move(temp_file, file_path)
                            # Verify it worked
                            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                                replaced = True
                                temp_file = None  # Mark as moved
                                print(f"Successfully removed and replaced file: {file_path}")
                            else:
                                raise Exception("File removed but move failed")
                        except Exception as method1_error:
                            print(f"Method 1 (remove and move) failed: {method1_error}")
                        
                        # Method 2: Try to overwrite by copying content
                        if not replaced:
                            try:
                                # Try to overwrite by copying the temp file over the existing one
                                shutil.copy2(temp_file, file_path)
                                # Verify it worked
                                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                                    replaced = True
                                    # Remove temp file after successful copy
                                    try:
                                        os.remove(temp_file)
                                        temp_file = None  # Mark as moved
                                    except:
                                        pass
                                    print(f"Successfully overwrote file using copy2: {file_path}")
                                else:
                                    raise Exception("Copy appeared to succeed but file not found or empty")
                            except Exception as method2_error:
                                print(f"Method 2 (copy2) failed: {method2_error}")
                        
                        # Method 3: Try to overwrite by reading and writing bytes
                        if not replaced:
                            try:
                                # Read the new file content
                                with open(temp_file, 'rb') as src:
                                    content = src.read()
                                
                                # Try to write directly to the existing file
                                with open(file_path, 'wb') as dst:
                                    dst.write(content)
                                    dst.flush()
                                    os.fsync(dst.fileno())
                                
                                # Verify it worked
                                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                                    replaced = True
                                    # Remove temp file after successful write
                                    try:
                                        os.remove(temp_file)
                                        temp_file = None  # Mark as moved
                                    except:
                                        pass
                                    print(f"Successfully overwrote file using direct write: {file_path}")
                                else:
                                    raise Exception("Direct write appeared to succeed but file not found or empty")
                            except Exception as method3_error:
                                print(f"Method 3 (direct write) failed: {method3_error}")
                        
                        # Method 4: Try shutil.move (atomic operation)
                        if not replaced:
                            try:
                                # Try to move even if file exists - sometimes works
                                if os.path.exists(file_path):
                                    # Create a backup name
                                    backup_path = file_path + '.old'
                                    try:
                                        if os.path.exists(backup_path):
                                            os.remove(backup_path)
                                        os.rename(file_path, backup_path)
                                    except:
                                        pass
                                
                                shutil.move(temp_file, file_path)
                                # Verify it worked
                                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                                    replaced = True
                                    temp_file = None  # Mark as moved
                                    print(f"Successfully moved file: {file_path}")
                                else:
                                    raise Exception("Move appeared to succeed but file not found or empty")
                                
                                # Clean up backup if it exists
                                backup_path = file_path + '.old'
                                if os.path.exists(backup_path):
                                    try:
                                        os.remove(backup_path)
                                    except:
                                        pass
                            except Exception as method4_error:
                                print(f"Method 4 (move) failed: {method4_error}")
                        
                        # Method 5: Try using subprocess to change permissions (last resort)
                        if not replaced:
                            try:
                                # Try to change file permissions using chmod command
                                result = subprocess.run(
                                    ['chmod', '666', file_path],
                                    capture_output=True,
                                    text=True,
                                    timeout=5
                                )
                                if result.returncode == 0:
                                    # Now try to remove and replace
                                    try:
                                        os.remove(file_path)
                                        shutil.move(temp_file, file_path)
                                        # Verify it worked
                                        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                                            replaced = True
                                            temp_file = None  # Mark as moved
                                            print(f"Successfully replaced file using chmod: {file_path}")
                                        else:
                                            raise Exception("Move after chmod appeared to succeed but file not found or empty")
                                    except Exception as chmod_remove_error:
                                        print(f"chmod succeeded but remove/move failed: {chmod_remove_error}")
                                        # Try copy2 again after chmod
                                        try:
                                            shutil.copy2(temp_file, file_path)
                                            # Verify it worked
                                            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                                                replaced = True
                                                try:
                                                    os.remove(temp_file)
                                                    temp_file = None  # Mark as moved
                                                except:
                                                    pass
                                                print(f"Successfully replaced file using copy2 after chmod: {file_path}")
                                            else:
                                                raise Exception("Copy2 after chmod appeared to succeed but file not found or empty")
                                        except Exception as copy2_error:
                                            print(f"Copy2 after chmod also failed: {copy2_error}")
                            except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as subprocess_error:
                                print(f"Method 5 (subprocess chmod) failed: {subprocess_error}")
                        
                        if not replaced:
                            # Provide detailed error information
                            file_stat = None
                            try:
                                file_stat = os.stat(file_path)
                                file_owner = f"UID: {file_stat.st_uid}, GID: {file_stat.st_gid}"
                                file_perms = oct(file_stat.st_mode)[-3:]
                            except:
                                file_owner = "unknown"
                                file_perms = "unknown"
                            
                            error_details = (
                                f"Could not replace file {file_path} using any method. "
                                f"File owner: {file_owner}, Permissions: {file_perms}. "
                                f"Please run in Docker container: 'chmod 666 {file_path}' or 'chown $(whoami) {file_path}'"
                            )
                            raise PermissionError(error_details)
                    else:
                        # File doesn't exist, just move it
                        moved_successfully = False
                        try:
                            shutil.move(temp_file, file_path)
                            # Verify the move actually worked
                            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                                moved_successfully = True
                                print(f"Successfully moved new file: {file_path}")
                                temp_file = None  # Mark as moved so we don't try to delete it
                            else:
                                # Move appeared to succeed but file doesn't exist or is empty
                                raise Exception(f"File move appeared to succeed but file not found or empty at {file_path}")
                        except Exception as move_error:
                            # If move fails, try copy2 as fallback
                            if temp_file and os.path.exists(temp_file):
                                try:
                                    shutil.copy2(temp_file, file_path)
                                    # Verify the copy actually worked
                                    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                                        moved_successfully = True
                                        print(f"Successfully copied new file (fallback): {file_path}")
                                        try:
                                            os.remove(temp_file)
                                            temp_file = None  # Mark as moved so we don't try to delete it
                                        except:
                                            pass
                                    else:
                                        raise Exception(f"File copy appeared to succeed but file not found or empty at {file_path}")
                                except Exception as copy_error:
                                    # Both move and copy failed
                                    raise Exception(f"Could not save file: move failed ({move_error}), copy failed ({copy_error})")
                            else:
                                # Temp file doesn't exist, can't retry
                                raise Exception(f"Could not save file: move failed ({move_error}), temp file not found")
                        
                        if not moved_successfully:
                            raise Exception("File operation completed but file was not saved successfully")
                    
                except PermissionError as perm_error:
                    error_msg = f"Berechtigung verweigert: Die Datei '{filename}' kann nicht überschrieben werden. Bitte überprüfen Sie die Dateiberechtigungen oder führen Sie 'chmod 644 {file_path}' aus."
                    print(f"Error saving file: {perm_error}")
                    if temp_file and os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                        except:
                            pass
                    session['upload_error'] = error_msg
                    return redirect("/upload_template")
                except Exception as save_error:
                    error_msg = f"Fehler beim Speichern der Datei: {str(save_error)}"
                    print(f"Error saving file: {save_error}")
                    if temp_file and os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                        except:
                            pass
                    session['upload_error'] = error_msg
                    return redirect("/upload_template")
                finally:
                    # Clean up temp file if it still exists (shouldn't happen if move succeeded)
                    if temp_file and os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                        except:
                            pass
                
                # Verify file was saved (before we exit the try block)
                if not os.path.exists(file_path):
                    error_details = f"Die Datei '{filename}' wurde nicht gefunden nach dem Speichern. Bitte versuchen Sie es erneut."
                    print(f"Error: File not found after save: {file_path}")
                    # Clean up any remaining temp files
                    if temp_file and os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                        except:
                            pass
                    session['upload_error'] = f"Fehler beim Speichern der Datei: {error_details}"
                    return redirect("/upload_template")
                
                saved_file_size = os.path.getsize(file_path)
                if saved_file_size == 0:
                    error_details = f"Die gespeicherte Datei '{filename}' ist leer."
                    print(f"Error: Saved file is empty: {file_path}")
                    # Clean up any remaining temp files
                    if temp_file and os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                        except:
                            pass
                    session['upload_error'] = f"Fehler beim Speichern der Datei: {error_details}"
                    return redirect("/upload_template")
                
                print(f"File saved successfully: {file_path} ({saved_file_size} bytes)")
                
                # Success message
                action = "ersetzt" if file_existed else "hochgeladen"
                # Show original filename if it was changed, otherwise show the saved filename
                if original_filename != filename:
                    display_name = f"{original_filename} (als '{filename}' gespeichert)"
                else:
                    display_name = filename
                session['upload_success'] = f"Datei '{display_name}' wurde erfolgreich {action}."
                
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
