import os
from app import db
from app import app
from docxtpl import DocxTemplate #https://docxtpl.readthedocs.io/  https://medium.com/@lukas.forst/automating-your-job-with-python-89b8878cdef1
from qrbill import QRBill #https://github.com/claudep/swiss-qr-bill/
from svglib.svglib import svg2rlg
from datetime import date
from cairosvg import svg2png
import models

dir_path = os.path.dirname(os.path.realpath(__file__))
REMI_FOLDER = 'static/rem'

def create_reminder1(bnum, dergeld):
    print("Reminder 1 start")

    reminderDone = False
    # welche vorlage wird angewendet
    reminder_template = os.path.join(dir_path, REMI_FOLDER, '1_mahnung_vorlage.docx') 
    
    # delete old files if exists
    reminder_file = os.path.join(dir_path, REMI_FOLDER, 'reminder.docx')
    qr_pic1 = os.path.join(dir_path, REMI_FOLDER, 'tempQR.svg')
    qr_pic2 = os.path.join(dir_path, REMI_FOLDER, 'tempQR.png')
    try:
        print("Try1")
        os.remove(reminder_file)
        os.remove(qr_pic1)
        os.remove(qr_pic2)
    except:
        print("Except1")
        #None

    try:
        print("Try2")
        # grab data
        data_reminder = models.Busse.query.order_by(models.Busse.db_bussennr.asc()).filter(bnum).first()
        is_busse    = data_reminder.db_bussennr
        is_datum    = data_reminder.db_aufnahmedatum
        is_schild   = data_reminder.db_nummerschild
        is_anred    = data_reminder.db_anrede
        is_name     = data_reminder.db_name
        is_stra1    = data_reminder.db_strasse
        is_stra2    = data_reminder.db_zusatz
        is_platz    = data_reminder.db_plz
        is_ort      = data_reminder.db_ort
        is_land     = data_reminder.db_land
        is_geld     = dergeld
        old_pic     = "qr"

        print("sql ok")

        # generate qr code
        my_bill = QRBill(
                language="de",
                account='CH200025125183542001D',
                creditor={
                    'name': "Dolder Eis & Bad AG",
                    'street': 'Adlisbergstrasse 36',
                    'pcode': "8098", 
                    'city': "Zürich", 
                    'country': "CH",
                },
                debtor={
                        'name': is_name,
                        'street': is_stra1,
                        #'house_num': '28',
                        'pcode': is_ort,
                        'city': is_platz,
                        'country': is_land,
                },
                additional_information= "Nachzahlgebühr-Nr.: " + is_busse,
                amount=is_geld,
            )
        
        print("qr gen ok")

        # generate svg from bill
        my_bill.as_svg("tempQR.svg")
        # Convert SVG file to PNG file
        svg2png(url="tempQR.svg", write_to="tempQR.png", dpi=200)

        print("qr convert ok")

        # lade template document
        doc = DocxTemplate(reminder_template)

        print("read template ok")

        # setze variablen
        context = { 
            'anrede' : is_anred,
            'name' : is_name,
            'strasse1' : is_stra1,
            'strasse2' : is_stra2,
            'plz' : is_platz,
            'ort' : is_ort,
            'land' : is_land,
            'datum' : is_datum,
            'kennz' : is_schild,
            'busse' : is_busse,
            'heute' : date.today().strftime('%d.%m.%Y'),
            'geld' : is_geld,
            }

        print("create rem ok")

        # ersetze QR Vorlagebild mit generiertem QR
        doc.replace_pic(old_pic,'tempQR.png')

        print("add QR ok")
        
        # verarbeite generiertes document
        doc.render(context)
        doc.save(reminder_file)
        print("Word reminder generated")

        reminderDone = True
        send_file(
            reminder_file,
            mimetype="application/msword",
            download_name= 'Mahnung_Bussennr: ' + is_busse + 'DolderPark.docx',
            as_attachment=True)

        #return(reminderDone)

    except Exception as exception:
        print("Reminder generation aborted")
        print("got the following exception: " + str(exception))
        
        reminderDone = False
        #return(reminderDone)

'''
#----------------------------------------------------------------------------------------------------------
# generate reminder 2
class create_reminder2(bnum, dergeld):
    reminderDone = False
    # welche vorlage wird angewendet
    reminder_template = os.path.join(dir_path, REMI_FOLDER, '2_mahnung_vorlage.docx') 

    # delete old files if exists
    reminder_file = os.path.join(dir_path, REMI_FOLDER, 'reminder.docx')
    qr_pic1 = os.path.join(dir_path, REMI_FOLDER, 'tempQR.svg')
    qr_pic2 = os.path.join(dir_path, REMI_FOLDER, 'tempQR.png')
    try:
        os.remove(reminder_file)
        os.remove(qr_pic1)
        os.remove(qr_pic2)
    except:
        None

    try:
        # grab data
        data_reminder = models.Busse.query.order_by(models.Busse.db_bussennr.asc()).filter(bnum).first()
        is_busse    = data_reminder.db_bussennr
        is_datum    = data_reminder.db_aufnahmedatum
        is_schild   = data_reminder.db_
        is_anred    = data_reminder.db_anrede
        is_name     = data_reminder.db_name
        is_stra1    = data_reminder.db_strasse
        is_stra2    = data_reminder.db_zusatz
        is_platz    = data_reminder.db_plz
        is_ort      = data_reminder.db_ort
        is_land     = data_reminder.db_land
        is_geld     = dergeld
        old_pic     = "qr"

        # generate qr code
        my_bill = QRBill(
                language="de",
                account='CH200025125183542001D',
                creditor={
                    'name': "Dolder Eis & Bad AG",
                    'street': 'Adlisbergstrasse 36',
                    'pcode': "8098", 
                    'city': "Zürich", 
                    'country': "CH",
                },
                debtor={
                        'name': is_name,
                        'street': is_stra1,
                        #'house_num': '28',
                        'pcode': is_ort,
                        'city': is_platz,
                        'country': is_land,
                },
                additional_information= "Nachzahlgebühr-Nr.: " + is_busse,
                amount=is_geld,
            )
        
        # generate svg from bill
        my_bill.as_svg("tempQR.svg")
        # Convert SVG file to PNG file
        svg2png(url="tempQR.svg", write_to="tempQR.png", dpi=200)

        # lade template document
        doc = DocxTemplate(reminder_template)

        # setze variablen
        context = { 
            'anrede' : is_anred,
            'name' : is_name,
            'strasse1' : is_stra1,
            'strasse2' : is_stra2,
            'plz' : is_platz,
            'ort' : is_ort,
            'land' : is_land,
            'datum' : is_datum,
            'kennz' : is_schild,
            'busse' : is_busse,
            'heute' : date.today().strftime('%d.%m.%Y'),
            'geld' : is_geld,
            }

        # ersetze QR Vorlagebild mit generiertem QR
        doc.replace_pic(old_pic,'tempQR.png')

        # verarbeite generiertes document
        doc.render(context)
        doc.save(reminder_file)
        print("Word reminder generated")

        reminderDone = True
        send_file(
            reminder_file,
            mimetype="application/msword",
            download_name= 'Mahnung_Bussennr: ' + is_busse + 'DolderPark.docx',
            as_attachment=True)

        #return(reminderDone)

    except Exception as exception:
        print("Reminder generation aborted")
        print("got the following exception: " + str(exception))
        
        #reminderDone = False
        #return(reminderDone)

#----------------------------------------------------------------------------------------------------------
# generate reminder 3
class create_reminder3(bnum, dergeld):
    reminderDone = False
    # welche vorlage wird angewendet
    reminder_template = os.path.join(dir_path, REMI_FOLDER, '3_mahnung_vorlage.docx') 

    # delete old files if exists
    reminder_file = os.path.join(dir_path, REMI_FOLDER, 'reminder.docx')
    qr_pic1 = os.path.join(dir_path, REMI_FOLDER, 'tempQR.svg')
    qr_pic2 = os.path.join(dir_path, REMI_FOLDER, 'tempQR.png')
    try:
        os.remove(reminder_file)
        os.remove(qr_pic1)
        os.remove(qr_pic2)
    except:
        None

    try:
        # grab data
        data_reminder = models.Busse.query.order_by(models.Busse.db_bussennr.asc()).filter(bnum).first()
        is_busse    = data_reminder.db_bussennr
        is_datum    = data_reminder.db_aufnahmedatum
        is_schild   = data_reminder.db_
        is_anred    = data_reminder.db_anrede
        is_name     = data_reminder.db_name
        is_stra1    = data_reminder.db_strasse
        is_stra2    = data_reminder.db_zusatz
        is_platz    = data_reminder.db_plz
        is_ort      = data_reminder.db_ort
        is_land     = data_reminder.db_land
        is_geld     = dergeld
        old_pic     = "qr"

        # generate qr code
        my_bill = QRBill(
                language="de",
                account='CH200025125183542001D',
                creditor={
                    'name': "Dolder Eis & Bad AG",
                    'street': 'Adlisbergstrasse 36',
                    'pcode': "8098", 
                    'city': "Zürich", 
                    'country': "CH",
                },
                debtor={
                        'name': is_name,
                        'street': is_stra1,
                        #'house_num': '28',
                        'pcode': is_ort,
                        'city': is_platz,
                        'country': is_land,
                },
                additional_information= "Nachzahlgebühr-Nr.: " + is_busse,
                amount=is_geld,
            )
        
        # generate svg from bill
        my_bill.as_svg("tempQR.svg")
        # Convert SVG file to PNG file
        svg2png(url="tempQR.svg", write_to="tempQR.png", dpi=200)

        # lade template document
        doc = DocxTemplate(reminder_template)

        # setze variablen
        context = { 
            'anrede' : is_anred,
            'name' : is_name,
            'strasse1' : is_stra1,
            'strasse2' : is_stra2,
            'plz' : is_platz,
            'ort' : is_ort,
            'land' : is_land,
            'datum' : is_datum,
            'kennz' : is_schild,
            'busse' : is_busse,
            'heute' : date.today().strftime('%d.%m.%Y'),
            'geld' : is_geld,
            }

        # ersetze QR Vorlagebild mit generiertem QR
        doc.replace_pic(old_pic,'tempQR.png')

        # verarbeite generiertes document
        doc.render(context)
        doc.save(reminder_file)
        print("Word reminder generated")

        reminderDone = True
        send_file(
            reminder_file,
            mimetype="application/msword",
            download_name= 'Mahnung_Bussennr: ' + is_busse + 'DolderPark.docx',
            as_attachment=True)

        #return(reminderDone)

    except Exception as exception:
        print("Reminder generation aborted")
        print("got the following exception: " + str(exception))
        
        reminderDone = False
        #return(reminderDone)

#----------------------------------------------------------------------------------------------------------
# generate reminder 4
class create_reminder4(bnum, dergeld):
    reminderDone = False
    # welche vorlage wird angewendet
    reminder_template = os.path.join(dir_path, REMI_FOLDER, '4_mahnung_vorlage.docx') 

    # delete old files if exists
    reminder_file = os.path.join(dir_path, REMI_FOLDER, 'reminder.docx')
    qr_pic1 = os.path.join(dir_path, REMI_FOLDER, 'tempQR.svg')
    qr_pic2 = os.path.join(dir_path, REMI_FOLDER, 'tempQR.png')
    try:
        os.remove(reminder_file)
        os.remove(qr_pic1)
        os.remove(qr_pic2)
    except:
        None

    try:
        # grab data
        data_reminder = models.Busse.query.order_by(models.Busse.db_bussennr.asc()).filter(bnum).first()
        is_busse    = data_reminder.db_bussennr
        is_datum    = data_reminder.db_aufnahmedatum
        is_schild   = data_reminder.db_
        is_anred    = data_reminder.db_anrede
        is_name     = data_reminder.db_name
        is_stra1    = data_reminder.db_strasse
        is_stra2    = data_reminder.db_zusatz
        is_platz    = data_reminder.db_plz
        is_ort      = data_reminder.db_ort
        is_land     = data_reminder.db_land
        is_geld     = dergeld
        old_pic     = "qr"

        # generate qr code
        my_bill = QRBill(
                language="de",
                account='CH200025125183542001D',
                creditor={
                    'name': "Dolder Eis & Bad AG",
                    'street': 'Adlisbergstrasse 36',
                    'pcode': "8098", 
                    'city': "Zürich", 
                    'country': "CH",
                },
                debtor={
                        'name': is_name,
                        'street': is_stra1,
                        #'house_num': '28',
                        'pcode': is_ort,
                        'city': is_platz,
                        'country': is_land,
                },
                additional_information= "Nachzahlgebühr-Nr.: " + is_busse,
                amount=is_geld,
            )
        
        # generate svg from bill
        my_bill.as_svg("tempQR.svg")
        # Convert SVG file to PNG file
        svg2png(url="tempQR.svg", write_to="tempQR.png", dpi=200)

        # lade template document
        doc = DocxTemplate(reminder_template)

        # setze variablen
        context = { 
            'anrede' : is_anred,
            'name' : is_name,
            'strasse1' : is_stra1,
            'strasse2' : is_stra2,
            'plz' : is_platz,
            'ort' : is_ort,
            'land' : is_land,
            'datum' : is_datum,
            'kennz' : is_schild,
            'busse' : is_busse,
            'heute' : date.today().strftime('%d.%m.%Y'),
            'geld' : is_geld,
            }

        # ersetze QR Vorlagebild mit generiertem QR
        doc.replace_pic(old_pic,'tempQR.png')

        # verarbeite generiertes document
        doc.render(context)
        doc.save(reminder_file)
        print("Word reminder generated")

        reminderDone = True
        send_file(
            reminder_file,
            mimetype="application/msword",
            download_name= 'Mahnung_Bussennr: ' + is_busse + 'DolderPark.docx',
            as_attachment=True)

        #return(reminderDone)

    except Exception as exception:
        print("Reminder generation aborted")
        print("got the following exception: " + str(exception))
        
        reminderDone = False
        #return(reminderDone)
        
'''