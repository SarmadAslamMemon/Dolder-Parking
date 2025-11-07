from flask import render_template, request, redirect, session
from flask_login import current_user
from datetime import datetime
from sqlalchemy import inspect, text
from sqlalchemy.orm import joinedload
import models

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
        
        if request.method == 'POST':
            # Handle POST request - process upload and redirect
            if 'html_file' not in request.files:
                session['upload_error'] = "Keine Datei ausgewählt."
                return redirect("/upload_template")
            else:
                file = request.files['html_file']
                if file.filename == '':
                    session['upload_error'] = "Keine Datei ausgewählt."
                    return redirect("/upload_template")
                else:
                    # Check if file is HTML
                    if file.filename.endswith('.html'):
                        try:
                            # Read file content
                            html_content = file.read().decode('utf-8')
                            
                            # Check if user_id column exists in the table
                            try:
                                inspector = inspect(db.engine)
                                # Try different possible table names
                                table_name = None
                                for table in inspector.get_table_names():
                                    if 'html' in table.lower() and 'template' in table.lower():
                                        table_name = table
                                        break
                                
                                if not table_name:
                                    # Try the standard naming convention
                                    table_name = 'html_template'
                                
                                columns = [col['name'] for col in inspector.get_columns(table_name)]
                                has_user_id_column = 'user_id' in columns
                                
                                # If user_id column doesn't exist, try to add it
                                if not has_user_id_column:
                                    print("user_id column doesn't exist during upload, attempting to add it...")
                                    try:
                                        db.session.execute(
                                            text("ALTER TABLE html_template ADD COLUMN user_id INT NULL")
                                        )
                                        db.session.commit()
                                        print("Successfully added user_id column")
                                        has_user_id_column = True
                                    except Exception as alter_error:
                                        print(f"Could not add user_id column: {alter_error}")
                                        # Continue without the column
                            except Exception as inspect_error:
                                print(f"Could not inspect table: {inspect_error}")
                                # Default to trying with user_id, will fail gracefully if column doesn't exist
                                has_user_id_column = True
                            
                            # Save to database
                            if has_user_id_column:
                                # Column exists, use it
                                if not current_user.is_authenticated:
                                    session['upload_error'] = "Benutzer nicht authentifiziert."
                                    return redirect("/upload_template")
                                
                                user_id_to_save = current_user.id
                                print(f"Uploading file for user_id: {user_id_to_save} (type: {type(user_id_to_save)}), current_user.id: {current_user.id}, username: {current_user.username}")
                                
                                html_template = models.HtmlTemplate(
                                    html_content=html_content,
                                    created_at=datetime.now(),
                                    user_id=user_id_to_save
                                )
                                print(f"Created HtmlTemplate object with user_id: {html_template.user_id}")
                            else:
                                # Column doesn't exist, use raw SQL to insert without user_id
                                print("Warning: user_id column doesn't exist, inserting without it")
                                db.session.execute(
                                    text("INSERT INTO html_template (html_content, created_at) VALUES (:content, :created_at)"),
                                    {"content": html_content, "created_at": datetime.now()}
                                )
                                db.session.commit()
                                # Get the inserted ID using LAST_INSERT_ID()
                                page_id_result = db.session.execute(text("SELECT LAST_INSERT_ID()"))
                                page_id = page_id_result.scalar()
                                
                                if page_id:
                                    session['upload_success'] = f"Seite gespeichert! Ansehen unter /page/{page_id}"
                                    session['upload_page_id'] = page_id
                                else:
                                    # Fallback: get the max ID
                                    max_id_result = db.session.execute(text("SELECT MAX(id) FROM html_template"))
                                    page_id = max_id_result.scalar()
                                    session['upload_success'] = f"Seite gespeichert! Ansehen unter /page/{page_id}"
                                    session['upload_page_id'] = page_id
                                return redirect("/upload_template")
                            
                            db.session.add(html_template)
                            db.session.flush()  # Flush to get the ID before commit
                            page_id = html_template.id
                            print(f"File added to session. ID: {page_id}, user_id: {html_template.user_id}")
                            
                            db.session.commit()
                            
                            # Refresh the object to ensure it's up to date
                            db.session.refresh(html_template)
                            print(f"File uploaded successfully! ID: {page_id}, user_id: {html_template.user_id}")
                            
                            # Verify the file was saved correctly by querying fresh
                            db.session.expire_all()  # Expire all objects to force fresh query
                            verify_file = models.HtmlTemplate.query.get(page_id)
                            if verify_file:
                                print(f"Verification: File {page_id} exists with user_id: {verify_file.user_id}")
                                # Also verify we can query it by user_id
                                user_files = models.HtmlTemplate.query.filter_by(user_id=current_user.id).all()
                                print(f"Verification: Found {len(user_files)} files for user {current_user.id}")
                                for uf in user_files:
                                    print(f"  - File ID: {uf.id}, user_id: {uf.user_id}")
                            else:
                                print(f"WARNING: File {page_id} not found after upload!")
                            
                            session['upload_success'] = f"Seite gespeichert! Ansehen unter /page/{page_id}"
                            session['upload_page_id'] = page_id
                            return redirect("/upload_template")
                        except Exception as exception:
                            error_msg = str(exception)
                            print("got the following exception: " + error_msg)
                            session['upload_error'] = f"Fehler beim Speichern der Datei: {error_msg}"
                            return redirect("/upload_template")
                    else:
                        session['upload_error'] = "Nur HTML-Dateien sind erlaubt."
                        return redirect("/upload_template")
        
        # Handle GET request - display form and messages
        success_message = None
        error_message = None
        page_id = None
        
        # Get messages from session and clear them
        if 'upload_success' in session:
            success_message = session.pop('upload_success')
            page_id = session.pop('upload_page_id', None)
        if 'upload_error' in session:
            error_message = session.pop('upload_error')
        if 'delete_success' in session:
            success_message = session.pop('delete_success')
        if 'delete_error' in session:
            error_message = session.pop('delete_error')
        
        # Fetch files based on user permission
        # ALL users see all files, ADMIN users see only their own files
        uploaded_files = []  # Always initialize to empty list
        if current_user.is_authenticated and current_user.id:
            print(f"DEBUG: Current user authenticated - ID: {current_user.id}, Username: {current_user.username}, Permission: {current_user.permission}")
            try:
                # Check if user_id column exists first
                inspector = inspect(db.engine)
                table_name = None
                for table in inspector.get_table_names():
                    if 'html' in table.lower() and 'template' in table.lower():
                        table_name = table
                        break
                
                if not table_name:
                    table_name = 'html_template'
                
                columns = [col['name'] for col in inspector.get_columns(table_name)]
                has_user_id_column = 'user_id' in columns
                
                # If user_id column doesn't exist, try to add it
                if not has_user_id_column:
                    print("user_id column doesn't exist, attempting to add it...")
                    try:
                        db.session.execute(
                            text("ALTER TABLE html_template ADD COLUMN user_id INT NULL")
                        )
                        db.session.commit()
                        print("Successfully added user_id column")
                        has_user_id_column = True
                    except Exception as alter_error:
                        print(f"Could not add user_id column: {alter_error}")
                        # Continue without the column
                
                if has_user_id_column:
                    # Column exists, use raw SQL for more reliable results
                    try:
                        # First, debug: check what's in the database
                        debug_check = db.session.execute(
                            text("SELECT id, user_id, created_at FROM html_template ORDER BY created_at DESC LIMIT 10")
                        )
                        debug_rows = debug_check.fetchall()
                        print(f"DEBUG: Found {len(debug_rows)} total files in database:")
                        for dr in debug_rows:
                            print(f"  - File ID: {dr[0]}, user_id: {dr[1]}, created_at: {dr[2]}")
                        
                        # Check permission: ALL sees all files, ADMIN sees only their own
                        if current_user.permission == models.UserPermission.ALL:
                            # ALL permission: show all files from all users
                            print(f"DEBUG: User has ALL permission - showing all files")
                            sql_query = text("""
                                SELECT ht.id, ht.html_content, ht.created_at, ht.user_id, u.username
                                FROM html_template ht
                                LEFT JOIN users u ON ht.user_id = u.id
                                ORDER BY ht.created_at DESC
                            """)
                            params = {}
                        else:
                            # ADMIN or other: show only files uploaded by current user
                            print(f"DEBUG: User has {current_user.permission} permission - showing only own files (user_id={current_user.id})")
                            sql_query = text("""
                                SELECT ht.id, ht.html_content, ht.created_at, ht.user_id, u.username
                                FROM html_template ht
                                LEFT JOIN users u ON ht.user_id = u.id
                                WHERE ht.user_id = :user_id
                                ORDER BY ht.created_at DESC
                            """)
                            params = {"user_id": current_user.id}
                        
                        result = db.session.execute(sql_query, params)
                        rows = result.fetchall()
                        print(f"DEBUG: Raw SQL query returned {len(rows)} rows")
                        
                        # Convert to model-like objects with username
                        uploaded_files = []
                        for row in rows:
                            try:
                                # Parse created_at if it's a string
                                created_at_val = row[2]
                                if isinstance(created_at_val, str):
                                    try:
                                        created_at_val = datetime.strptime(created_at_val, '%Y-%m-%d %H:%M:%S')
                                    except:
                                        created_at_val = datetime.now()
                                elif created_at_val is None:
                                    created_at_val = datetime.now()
                                
                                file_obj = type('HtmlTemplate', (), {
                                    'id': int(row[0]),
                                    'html_content': row[1],
                                    'created_at': created_at_val,
                                    'user_id': row[3] if row[3] is not None else None,
                                    'username': row[4] if row[4] else 'Unbekannt'
                                })()
                                uploaded_files.append(file_obj)
                                print(f"DEBUG: Added file ID={file_obj.id}, user_id={file_obj.user_id}, username={file_obj.username}, created_at={file_obj.created_at}")
                            except Exception as row_error:
                                print(f"DEBUG: Error processing row {row}: {row_error}")
                                import traceback
                                traceback.print_exc()
                        
                        print(f"Found {len(uploaded_files)} files for user {current_user.id} (permission: {current_user.permission})")
                    except Exception as sql_error:
                        print(f"SQL query failed: {sql_error}")
                        import traceback
                        traceback.print_exc()
                        # Fallback: try simpler query
                        try:
                            # Check permission: ALL sees all files, ADMIN sees only their own
                            if current_user.permission == models.UserPermission.ALL:
                                # ALL permission: show all files
                                print(f"DEBUG: Raw SQL - User has ALL permission - showing all files")
                                result = db.session.execute(
                                    text("""
                                        SELECT ht.id, ht.html_content, ht.created_at, ht.user_id, u.username
                                        FROM html_template ht
                                        LEFT JOIN users u ON ht.user_id = u.id
                                        ORDER BY ht.created_at DESC
                                    """)
                                )
                            else:
                                # ADMIN or other: show only files uploaded by current user
                                print(f"DEBUG: Raw SQL - User has {current_user.permission} permission - showing only own files")
                                result = db.session.execute(
                                    text("""
                                        SELECT ht.id, ht.html_content, ht.created_at, ht.user_id, u.username
                                        FROM html_template ht
                                        LEFT JOIN users u ON ht.user_id = u.id
                                        WHERE ht.user_id = :user_id
                                        ORDER BY ht.created_at DESC
                                    """),
                                    {"user_id": current_user.id}
                                )
                            
                            rows = result.fetchall()
                            # Convert to model-like objects with username
                            uploaded_files = []
                            for row in rows:
                                file_obj = type('HtmlTemplate', (), {
                                    'id': row[0],
                                    'html_content': row[1],
                                    'created_at': row[2] if row[2] else datetime.now(),
                                    'user_id': row[3],
                                    'username': row[4] if row[4] else 'Unbekannt'
                                })()
                                uploaded_files.append(file_obj)
                            print(f"Found {len(uploaded_files)} files using raw SQL for user {current_user.id} (permission: {current_user.permission})")
                        except Exception as sql_error:
                            print(f"Raw SQL query failed: {sql_error}")
                            uploaded_files = []
                else:
                    # Column doesn't exist, show all files (can't filter by user)
                    print("No user_id column - showing all files (cannot filter by user)")
                    try:
                        # Show all files since we can't filter by user_id
                        result = db.session.execute(
                            text("""
                                SELECT id, html_content, created_at, NULL as user_id, 'Unbekannt' as username
                                FROM html_template
                                ORDER BY created_at DESC
                            """)
                        )
                        rows = result.fetchall()
                        print(f"DEBUG: Found {len(rows)} files (no user_id column)")
                        
                        uploaded_files = []
                        for row in rows:
                            try:
                                created_at_val = row[2]
                                if isinstance(created_at_val, str):
                                    try:
                                        created_at_val = datetime.strptime(created_at_val, '%Y-%m-%d %H:%M:%S')
                                    except:
                                        created_at_val = datetime.now()
                                elif created_at_val is None:
                                    created_at_val = datetime.now()
                                
                                file_obj = type('HtmlTemplate', (), {
                                    'id': int(row[0]),
                                    'html_content': row[1],
                                    'created_at': created_at_val,
                                    'user_id': None,
                                    'username': 'Unbekannt'
                                })()
                                uploaded_files.append(file_obj)
                                print(f"DEBUG: Added file ID={file_obj.id}, created_at={file_obj.created_at}")
                            except Exception as row_error:
                                print(f"DEBUG: Error processing row {row}: {row_error}")
                    except Exception as e:
                        print(f"Error fetching files without user_id column: {e}")
                        uploaded_files = []
            except Exception as e:
                print(f"Error fetching files: {e}")
                import traceback
                traceback.print_exc()
                # Fallback: try to get files based on permission
                try:
                    if current_user.permission == models.UserPermission.ALL:
                        # ALL permission: show all files
                        uploaded_files = models.HtmlTemplate.query.options(
                            joinedload(models.HtmlTemplate.user)
                        ).order_by(
                            models.HtmlTemplate.created_at.desc()
                        ).all()
                    else:
                        # ADMIN or other: show only files uploaded by current user
                        uploaded_files = models.HtmlTemplate.query.options(
                            joinedload(models.HtmlTemplate.user)
                        ).filter_by(
                            user_id=current_user.id
                        ).order_by(
                            models.HtmlTemplate.created_at.desc()
                        ).all()
                    
                    for file in uploaded_files:
                        if hasattr(file, 'user') and file.user:
                            file.username = file.user.username
                        else:
                            file.username = 'Unbekannt'
                    print(f"Fallback: Found {len(uploaded_files)} files for user {current_user.id} (permission: {current_user.permission})")
                except Exception as e2:
                    print(f"Error fetching user files: {e2}")
                    traceback.print_exc()
                    uploaded_files = []
        
        print(f"Returning {len(uploaded_files)} files to template")
        print(f"DEBUG: uploaded_files type: {type(uploaded_files)}, is None: {uploaded_files is None}")
        if uploaded_files:
            print(f"DEBUG: First file in list: ID={uploaded_files[0].id if len(uploaded_files) > 0 else 'N/A'}")
        
        # Ensure uploaded_files is always a list, never None
        if uploaded_files is None:
            uploaded_files = []
            print("DEBUG: uploaded_files was None, setting to empty list")
        
        return render_template('upload_template.html', 
                             success_message=success_message, 
                             error_message=error_message, 
                             page_id=page_id,
                             uploaded_files=uploaded_files)

    @app.route("/page/<int:page_id>")
    def view_page(page_id):
        # check if the users exist or not
        if not session.get("name"):
            # if not there in the session then redirect to the login page
            return redirect("/login")
        
        try:
            # Try to get using ORM first
            html_template = models.HtmlTemplate.query.get(page_id)
            if html_template:
                # Check if user owns this file or has ADMIN/ALL permission
                if current_user.is_authenticated:
                    # Handle case where user_id might be None (old records)
                    if (html_template.user_id is None or 
                        html_template.user_id == current_user.id or 
                        current_user.permission in [models.UserPermission.ADMIN, models.UserPermission.ALL]):
                        return html_template.html_content
                return "Zugriff verweigert.", 403
            else:
                return "Seite nicht gefunden.", 404
        except Exception as e:
            # If ORM fails (e.g., user_id column doesn't exist), use raw SQL
            print(f"ORM query failed, trying raw SQL: {e}")
            try:
                result = db.session.execute(
                    text("SELECT html_content FROM html_template WHERE id = :id"),
                    {"id": page_id}
                )
                row = result.fetchone()
                if row:
                    return row[0]  # Return the html_content
                else:
                    return "Seite nicht gefunden.", 404
            except Exception as sql_error:
                print(f"Raw SQL query also failed: {sql_error}")
                return f"Fehler beim Laden der Seite: {str(sql_error)}", 500

    @app.route("/delete_template/<int:page_id>", methods=["POST"])
    def delete_template(page_id):
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
        
        html_template = models.HtmlTemplate.query.get(page_id)
        if html_template:
            # Check if user owns this file or has ADMIN/ALL permission
            # Handle case where user_id might be None (old records)
            if (html_template.user_id is None or 
                html_template.user_id == current_user.id or 
                current_user.permission in [models.UserPermission.ADMIN, models.UserPermission.ALL]):
                try:
                    db.session.delete(html_template)
                    db.session.commit()
                    session['delete_success'] = f"Seite {page_id} wurde erfolgreich gelöscht."
                except Exception as exception:
                    print("got the following exception: " + str(exception))
                    session['delete_error'] = "Fehler beim Löschen der Datei."
            else:
                session['delete_error'] = "Sie haben keine Berechtigung, diese Datei zu löschen."
        else:
            session['delete_error'] = "Datei nicht gefunden."
        
        return redirect("/upload_template")

