"""
User Management Routes
Handles user listing, editing, password changes, and permission management.
"""

from flask import render_template, request, redirect, session, jsonify, flash
from flask_login import current_user
from datetime import datetime
import models
from app import db, bcrypt


def register_user_routes(app):
    """Register user management routes with the Flask app"""
    
    @app.route("/user_management", methods=["GET"])
    def user_management():
        """Display list of all users"""
        # Check if user is authenticated
        if not session.get("name"):
            return redirect("/login")
        
        # Check if user has ALL permission (only ALL can manage users)
        if current_user.is_authenticated:
            if current_user.permission != models.UserPermission.ALL:
                flash("You do not have permission to access user management.", "error")
                return redirect("/s_all")
        else:
            return redirect("/login")
        
        # Get all users
        try:
            users = models.Users.query.order_by(models.Users.id.asc()).all()
        except Exception as e:
            print(f"Error fetching users: {e}")
            users = []
        
        return render_template('user_management.html', users=users)
    
    @app.route("/user_management/edit/<int:user_id>", methods=["GET", "POST"])
    def edit_user(user_id):
        """Edit user details (password and permission)"""
        # Check if user is authenticated
        if not session.get("name"):
            return redirect("/login")
        
        # Check if user has ALL permission (only ALL can manage users)
        if current_user.is_authenticated:
            if current_user.permission != models.UserPermission.ALL:
                flash("You do not have permission to edit users.", "error")
                return redirect("/user_management")
        else:
            return redirect("/login")
        
        # Get the user to edit
        user = models.Users.query.get(user_id)
        if not user:
            flash("User not found.", "error")
            return redirect("/user_management")
        
        if request.method == "POST":
            try:
                # Update password if provided
                new_password = request.form.get("password", "").strip()
                if new_password:
                    user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
                    flash(f"Password updated for user '{user.username}'.", "success")
                
                # Update permission if provided
                new_permission = request.form.get("permission", "").strip()
                if new_permission:
                    try:
                        user.permission = models.UserPermission[new_permission.upper()]
                        flash(f"Permission updated for user '{user.username}'.", "success")
                    except (KeyError, ValueError) as e:
                        flash(f"Invalid permission value: {new_permission}", "error")
                
                # Update disabled status
                disabled = request.form.get("disabled") == "true"
                user.disabled = disabled
                if disabled:
                    flash(f"User '{user.username}' has been disabled.", "success")
                else:
                    flash(f"User '{user.username}' has been enabled.", "success")
                
                # Commit changes
                db.session.commit()
                flash("User updated successfully.", "success")
                return redirect("/user_management")
                
            except Exception as e:
                db.session.rollback()
                print(f"Error updating user: {e}")
                flash(f"Error updating user: {str(e)}", "error")
                return redirect(f"/user_management/edit/{user_id}")
        
        # GET request - show edit form
        return render_template('edit_user.html', user=user)
    
    @app.route("/user_management/delete/<int:user_id>", methods=["POST"])
    def delete_user(user_id):
        """Delete a user (soft delete by disabling)"""
        # Check if user is authenticated
        if not session.get("name"):
            return redirect("/login")
        
        # Check if user has ALL permission (only ALL can manage users)
        if current_user.is_authenticated:
            if current_user.permission != models.UserPermission.ALL:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({"error": "Permission denied"}), 403
                flash("You do not have permission to delete users.", "error")
                return redirect("/user_management")
        else:
            return redirect("/login")
        
        # Prevent deleting yourself
        if user_id == current_user.id:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"error": "You cannot delete your own account"}), 400
            flash("You cannot delete your own account.", "error")
            return redirect("/user_management")
        
        try:
            user = models.Users.query.get(user_id)
            if not user:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({"error": "User not found"}), 404
                flash("User not found.", "error")
                return redirect("/user_management")
            
            username = user.username
            # Soft delete by disabling
            user.disabled = True
            db.session.commit()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"success": True, "message": f"User '{username}' has been disabled."}), 200
            
            flash(f"User '{username}' has been disabled.", "success")
            return redirect("/user_management")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error deleting user: {e}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"error": str(e)}), 500
            flash(f"Error deleting user: {str(e)}", "error")
            return redirect("/user_management")
    
    @app.route("/user_management/enable/<int:user_id>", methods=["POST"])
    def enable_user(user_id):
        """Enable a disabled user"""
        # Check if user is authenticated
        if not session.get("name"):
            return redirect("/login")
        
        # Check if user has ALL permission (only ALL can manage users)
        if current_user.is_authenticated:
            if current_user.permission != models.UserPermission.ALL:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({"error": "Permission denied"}), 403
                flash("You do not have permission to enable users.", "error")
                return redirect("/user_management")
        else:
            return redirect("/login")
        
        try:
            user = models.Users.query.get(user_id)
            if not user:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({"error": "User not found"}), 404
                flash("User not found.", "error")
                return redirect("/user_management")
            
            user.disabled = False
            db.session.commit()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"success": True, "message": f"User '{user.username}' has been enabled."}), 200
            
            flash(f"User '{user.username}' has been enabled.", "success")
            return redirect("/user_management")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error enabling user: {e}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"error": str(e)}), 500
            flash(f"Error enabling user: {str(e)}", "error")
            return redirect("/user_management")

