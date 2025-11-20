from app import db
from flask_login import UserMixin
from sqlalchemy import ForeignKey, TypeDecorator, String, LargeBinary
from sqlalchemy.orm import relationship
import enum

# tabel Users (usermanagement)
class UserPermission(enum.Enum):
    NONE = "none"
    ALL = "all"
    APP = "app"
    ADMIN = "admin"
    POWERUSER = "poweruser"

class UserPermissionType(TypeDecorator):
    """Custom type to handle UserPermission enum conversion"""
    impl = String(20)
    cache_ok = True
    
    def __init__(self):
        super().__init__(length=20)
    
    def process_bind_param(self, value, dialect):
        """Convert enum to string when writing to database"""
        if value is None:
            return None
        if isinstance(value, UserPermission):
            return value.value
        if isinstance(value, str):
            return value
        return str(value)
    
    def process_result_value(self, value, dialect):
        """Convert string from database to enum"""
        if value is None:
            return None
        if isinstance(value, UserPermission):
            return value
        # Try to find enum by value (lowercase string)
        for perm in UserPermission:
            if perm.value == value or perm.value == value.lower():
                return perm
        # Fallback: return the string value
        return value

class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    permission = db.Column(UserPermissionType(), default=UserPermission.NONE)
    disabled = db.Column(db.Boolean, nullable=False, default=False)
    
    @property
    def permission_value(self):
        """Safely return permission value as string"""
        if isinstance(self.permission, UserPermission):
            return self.permission.value
        elif isinstance(self.permission, str):
            return self.permission
        else:
            return str(self.permission) if self.permission else 'none'

# table busse
class Busse(db.Model):
    id                  = db.Column(db.Integer, primary_key = True)
    db_bussennr         = db.Column(db.Integer, nullable = False)
    db_aufnahmedatum    = db.Column(db.DateTime(), nullable = False) # ,default = datetime.now())

    db_nummerschild     = db.Column(db.String(200), nullable = True)
    db_mahndatum_1      = db.Column(db.Date(), nullable = True)
    db_bezahlt_1        = db.Column(db.Date(), nullable = True)
    db_mahndatum_2      = db.Column(db.Date(), nullable = True)
    db_bezahlt_2        = db.Column(db.Date(), nullable = True)
    db_mahndatum_3      = db.Column(db.Date(), nullable = True)
    db_bezahlt_3        = db.Column(db.Date(), nullable = True)    
    db_anrede           = db.Column(db.String(20), nullable = True)
    db_name             = db.Column(db.String(200), nullable = True)
    db_strasse          = db.Column(db.String(200), nullable = True)
    db_zusatz           = db.Column(db.String(200), nullable = True)
    db_plz              = db.Column(db.String(200), nullable = True)
    db_ort              = db.Column(db.String(200), nullable = True)
    db_land             = db.Column(db.String(200), nullable = True)
    db_status           = db.Column(db.SMALLINT, server_default="1")
    db_notes            = db.Column(db.Text, nullable = True)
                            # 1 = pendig, 2 = canceled, 3 =done

# table html_templates
class HtmlTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    html_content = db.Column(db.Text, nullable=True)  # Nullable for DOC/PDF files
    file_data = db.Column(LargeBinary, nullable=True)  # Binary data for DOC/PDF files
    file_type = db.Column(db.String(10), nullable=True)  # 'html', 'doc', 'docx', 'pdf'
    file_name = db.Column(db.String(255), nullable=True)  # Original filename
    created_at = db.Column(db.DateTime(), nullable=False)
    user_id = db.Column(db.Integer, ForeignKey('users.id'), nullable=True)
    
    # Relationship to access the user who created this template
    user = relationship("Users", backref="html_templates")
                            