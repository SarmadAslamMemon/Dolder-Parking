from flask import render_template, request, redirect, session, jsonify, url_for
from flask_login import current_user
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from PIL import Image
import json
import models

LOGO_FOLDER = 'static/logos'
LOGO_CONFIG_FILE = 'logo_config.json'
ALLOWED_LOGO_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'])

def get_active_logo_path():
    """Get the path of the active logo, or return default"""
    config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), LOGO_CONFIG_FILE)
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                active_logo = config.get('active_logo')
                if active_logo:
                    # Check if the logo file still exists
                    logo_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), LOGO_FOLDER, active_logo)
                    if os.path.exists(logo_path):
                        # Return path without 'static/' prefix since url_for('static', ...) adds it
                        # LOGO_FOLDER is 'static/logos', so we need just 'logos/...'
                        return os.path.join('logos', active_logo)
        except Exception as e:
            print(f"Error reading logo config: {e}")
    # Default logo
    return 'applogo.png'

def get_logo_size():
    """Get the logo size from config, default is 2.5rem (for backward compatibility)"""
    config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), LOGO_CONFIG_FILE)
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                # Check for new width/height format first
                if 'logo_width' in config or 'logo_height' in config:
                    width = config.get('logo_width', 'auto')
                    height = config.get('logo_height', '2.5rem')
                    return {'width': width, 'height': height}
                # Fallback to old logo_size format
                size = config.get('logo_size', '2.5rem')
                return {'width': 'auto', 'height': size}
        except Exception as e:
            print(f"Error reading logo size: {e}")
    return {'width': 'auto', 'height': '2.5rem'}  # Default size

def get_logo_width():
    """Get the logo width from config"""
    size = get_logo_size()
    return size.get('width', 'auto')

def get_logo_height():
    """Get the logo height from config"""
    size = get_logo_size()
    return size.get('height', '2.5rem')

def set_active_logo(filename):
    """Set the active logo in the config file"""
    config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), LOGO_CONFIG_FILE)
    try:
        # Read existing config to preserve logo_size
        config = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
            except:
                pass
        
        if filename is None:
            # Clear active logo
            config['active_logo'] = None
        else:
            config['active_logo'] = filename
        
        with open(config_path, 'w') as f:
            json.dump(config, f)
        return True
    except Exception as e:
        print(f"Error writing logo config: {e}")
        return False

def set_logo_size(size):
    """Set the logo size in the config file (for backward compatibility)"""
    # If size is a string, treat it as height and set width to auto
    if isinstance(size, str):
        return set_logo_dimensions('auto', size)
    return False

def set_logo_dimensions(width, height):
    """Set the logo width and height in the config file"""
    config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), LOGO_CONFIG_FILE)
    try:
        # Read existing config to preserve active_logo
        config = {}
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
            except:
                pass
        
        config['logo_width'] = width if width else 'auto'
        config['logo_height'] = height if height else '2.5rem'
        # Remove old logo_size if it exists
        if 'logo_size' in config:
            del config['logo_size']
        
        with open(config_path, 'w') as f:
            json.dump(config, f)
        return True
    except Exception as e:
        print(f"Error writing logo dimensions: {e}")
        return False

def allowed_logo_file(filename):
    """Check if the file extension is allowed for logos"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_LOGO_EXTENSIONS

def register_logo_routes(app, db):
    """Register logo upload routes with the Flask app"""
    
    @app.route("/upload_logo", methods=["GET", "POST"])
    def upload_logo():
        # Check if the user exists or not
        if not session.get("name"):
            return redirect("/login")
        
        # Check if user has ADMIN or ALL permission
        if current_user.is_authenticated:
            if current_user.permission not in [models.UserPermission.ADMIN, models.UserPermission.ALL]:
                return redirect("/s_all")
        else:
            return redirect("/login")
        
        # Get directory path
        dir_path = os.path.dirname(os.path.realpath(__file__))
        logo_dir = os.path.join(dir_path, LOGO_FOLDER)
        os.makedirs(logo_dir, exist_ok=True)
        
        success_message = None
        error_message = None
        
        # Get messages from session and clear them
        if 'logo_upload_success' in session:
            success_message = session.pop('logo_upload_success')
        if 'logo_upload_error' in session:
            error_message = session.pop('logo_upload_error')
        
        if request.method == 'POST':
            # Check if it's a file upload
            if 'logo_file' in request.files and request.files['logo_file'].filename:
                # Handle file upload
                file = request.files['logo_file']
                
                if file and allowed_logo_file(file.filename):
                    try:
                        filename = secure_filename(file.filename)
                        # Save with timestamp to avoid conflicts
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        name, ext = os.path.splitext(filename)
                        final_filename = f"logo_{timestamp}{ext}"
                        filepath = os.path.join(logo_dir, final_filename)
                        
                        # Save the file
                        file.save(filepath)
                        
                        # If it's an image (not SVG), optimize it
                        if ext.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                            try:
                                img = Image.open(filepath)
                                
                                # Resize if too large (max 500px width/height)
                                max_size = 500
                                if img.width > max_size or img.height > max_size:
                                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                                
                                # Save the optimized image with proper format
                                if ext.lower() in ['.jpg', '.jpeg']:
                                    # Convert RGBA/LA/P to RGB for JPEG (JPEG doesn't support transparency)
                                    if img.mode in ('RGBA', 'LA', 'P'):
                                        if img.mode == 'P':
                                            img = img.convert('RGBA')
                                        background = Image.new('RGB', img.size, (255, 255, 255))
                                        if img.mode == 'RGBA':
                                            background.paste(img, mask=img.split()[-1])
                                        else:
                                            background.paste(img)
                                        img = background
                                    img.save(filepath, 'JPEG', optimize=True, quality=85)
                                elif ext.lower() == '.png':
                                    # Preserve transparency for PNG files
                                    # Convert palette mode with transparency to RGBA if needed
                                    if img.mode == 'P':
                                        # Check if palette has transparency
                                        if 'transparency' in img.info:
                                            img = img.convert('RGBA')
                                        else:
                                            img = img.convert('RGB')
                                    # Keep RGBA mode for transparency, convert RGB to RGB
                                    elif img.mode == 'LA':
                                        img = img.convert('RGBA')
                                    elif img.mode not in ('RGBA', 'RGB'):
                                        img = img.convert('RGB')
                                    # Save PNG with proper format
                                    img.save(filepath, 'PNG', optimize=True)
                                elif ext.lower() == '.gif':
                                    # Preserve GIF mode
                                    if img.mode not in ('P', 'RGB', 'RGBA'):
                                        img = img.convert('RGB')
                                    img.save(filepath, 'GIF', optimize=True)
                                elif ext.lower() == '.webp':
                                    # WebP supports transparency
                                    save_kwargs = {'format': 'WEBP', 'quality': 85}
                                    if img.mode in ('RGBA', 'LA', 'P'):
                                        if img.mode == 'P':
                                            img = img.convert('RGBA')
                                        save_kwargs['lossless'] = False
                                    elif img.mode not in ('RGB', 'RGBA'):
                                        img = img.convert('RGB')
                                    img.save(filepath, **save_kwargs)
                                else:
                                    img.save(filepath, optimize=True)
                                
                                print(f"Logo optimized: {img.size[0]}x{img.size[1]} ({ext.lower()})")
                            except Exception as img_error:
                                print(f"Warning: Could not optimize image: {img_error}")
                                import traceback
                                traceback.print_exc()
                        
                        session['logo_upload_success'] = f"Logo erfolgreich hochgeladen: {final_filename}"
                        return redirect("/upload_logo")
                    except Exception as e:
                        print(f"Error uploading logo file: {e}")
                        import traceback
                        traceback.print_exc()
                        session['logo_upload_error'] = f"Fehler beim Hochladen: {str(e)}"
                        return redirect("/upload_logo")
                else:
                    session['logo_upload_error'] = "Ungültiges Dateiformat. Erlaubt: PNG, JPG, JPEG, GIF, SVG, WEBP"
                    return redirect("/upload_logo")
            else:
                session['logo_upload_error'] = "Bitte wählen Sie eine Datei aus."
                return redirect("/upload_logo")
        
        # Get active logo and size
        active_logo = None
        logo_width = 'auto'
        logo_height = '2.5rem'
        config_path = os.path.join(dir_path, LOGO_CONFIG_FILE)
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    active_logo = config.get('active_logo')
                    # Check for new width/height format first
                    if 'logo_width' in config or 'logo_height' in config:
                        logo_width = config.get('logo_width', 'auto')
                        logo_height = config.get('logo_height', '2.5rem')
                    else:
                        # Fallback to old logo_size format
                        logo_size = config.get('logo_size', '2.5rem')
                        logo_height = logo_size
            except Exception as e:
                print(f"Error reading logo config: {e}")
        
        # Get list of uploaded logos
        uploaded_logos = []
        if os.path.exists(logo_dir):
            try:
                files = os.listdir(logo_dir)
                for file in files:
                    if file.startswith('logo_') and allowed_logo_file(file):
                        filepath = os.path.join(logo_dir, file)
                        file_size = os.path.getsize(filepath)
                        file_time = os.path.getmtime(filepath)
                        uploaded_logos.append({
                            'filename': file,
                            'path': os.path.join('logos', file),  # Remove 'static/' prefix for url_for
                            'size': file_size,
                            'date': datetime.fromtimestamp(file_time),
                            'is_active': (file == active_logo)
                        })
                # Sort by date (newest first)
                uploaded_logos.sort(key=lambda x: x['date'], reverse=True)
            except Exception as e:
                print(f"Error listing logos: {e}")
        
        return render_template('upload_logo.html',
                            success_message=success_message,
                            error_message=error_message,
                            uploaded_logos=uploaded_logos,
                            active_logo=active_logo,
                            logo_width=logo_width,
                            logo_height=logo_height)
    
    @app.route("/delete_logo/<filename>", methods=["POST"])
    def delete_logo(filename):
        # Check if the user exists or not
        if not session.get("name"):
            return redirect("/login")
        
        # Check if user has ADMIN or ALL permission
        if current_user.is_authenticated:
            if current_user.permission not in [models.UserPermission.ADMIN, models.UserPermission.ALL]:
                return redirect("/s_all")
        else:
            return redirect("/login")
        
        dir_path = os.path.dirname(os.path.realpath(__file__))
        logo_dir = os.path.join(dir_path, LOGO_FOLDER)
        filepath = os.path.join(logo_dir, secure_filename(filename))
        
        # Security check: ensure file is in logo directory
        if not os.path.abspath(filepath).startswith(os.path.abspath(logo_dir)):
            session['logo_upload_error'] = "Ungültiger Dateipfad."
            return redirect("/upload_logo")
        
        # Check if this is the active logo
        config_path = os.path.join(dir_path, LOGO_CONFIG_FILE)
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    if config.get('active_logo') == secure_filename(filename):
                        # Clear active logo if deleting it
                        set_active_logo(None)
            except Exception as e:
                print(f"Error reading logo config: {e}")
        
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                session['logo_upload_success'] = f"Logo {filename} wurde erfolgreich gelöscht."
            else:
                session['logo_upload_error'] = "Datei nicht gefunden."
        except Exception as e:
            print(f"Error deleting logo: {e}")
            session['logo_upload_error'] = f"Fehler beim Löschen: {str(e)}"
        
        return redirect("/upload_logo")
    
    @app.route("/set_logo_size", methods=["POST"])
    def set_logo_size_route():
        # Check if the user exists or not
        if not session.get("name"):
            return redirect("/login")
        
        # Check if user has ADMIN or ALL permission
        if current_user.is_authenticated:
            if current_user.permission not in [models.UserPermission.ADMIN, models.UserPermission.ALL]:
                return redirect("/s_all")
        else:
            return redirect("/login")
        
        width = request.form.get('width', 'auto').strip()
        height = request.form.get('height', '2.5rem').strip()
        
        # Validate inputs
        if not width:
            width = 'auto'
        if not height:
            height = '2.5rem'
        
        if set_logo_dimensions(width, height):
            session['logo_upload_success'] = f"Logo-Größe wurde auf Breite: {width}, Höhe: {height} gesetzt."
        else:
            session['logo_upload_error'] = "Fehler beim Setzen der Logo-Größe."
        
        return redirect("/upload_logo")
    
    @app.route("/set_active_logo/<filename>", methods=["POST"])
    def set_active_logo_route(filename):
        # Check if the user exists or not
        if not session.get("name"):
            return redirect("/login")
        
        # Check if user has ADMIN or ALL permission
        if current_user.is_authenticated:
            if current_user.permission not in [models.UserPermission.ADMIN, models.UserPermission.ALL]:
                return redirect("/s_all")
        else:
            return redirect("/login")
        
        dir_path = os.path.dirname(os.path.realpath(__file__))
        logo_dir = os.path.join(dir_path, LOGO_FOLDER)
        filepath = os.path.join(logo_dir, secure_filename(filename))
        
        # Security check: ensure file is in logo directory
        if not os.path.abspath(filepath).startswith(os.path.abspath(logo_dir)):
            session['logo_upload_error'] = "Ungültiger Dateipfad."
            return redirect("/upload_logo")
        
        # Check if file exists
        if not os.path.exists(filepath):
            session['logo_upload_error'] = "Datei nicht gefunden."
            return redirect("/upload_logo")
        
        # Set as active logo
        if set_active_logo(secure_filename(filename)):
            session['logo_upload_success'] = f"Logo {filename} wurde als Website-Logo gesetzt."
        else:
            session['logo_upload_error'] = "Fehler beim Setzen des Logos."
        
        return redirect("/upload_logo")

