from app import db
from flask_login import UserMixin
import enum

# tabel Users (usermanagement)
class UserPermission(enum.Enum):
    NONE = "none"
    ALL = "all"
    APP = "app"
    ADMIN = "admin"
class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    permission = db.Column(db.Enum(UserPermission), default=UserPermission.NONE)
    disabled = db.Column(db.Boolean, nullable=False, default=False)

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
                            