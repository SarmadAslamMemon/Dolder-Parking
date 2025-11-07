import os
from datetime import date, datetime
from docxtpl import DocxTemplate #https://docxtpl.readthedocs.io/  https://medium.com/@lukas.forst/automating-your-job-with-python-89b8878cdef1
from qrbill import QRBill   #https://github.com/claudep/swiss-qr-bill/
from cairosvg import svg2png
from flask import send_file


def generate_reminder(vorlage, busse, m_mahn, dir_path, REMI_FOLDER):
    exportFailed = False
    # welche vorlage wird angewendet
    if vorlage == 1:
        reminder_template = os.path.join(dir_path, REMI_FOLDER, '1_mahnung_vorlage.docx')
        docName = '1.Mahnung_eAuto_Nr_'
    elif vorlage == 2:
        reminder_template = os.path.join(dir_path, REMI_FOLDER, '2_mahnung_vorlage.docx')
        docName = '1.Mahnung_HalterAb_Nr_'
    elif vorlage == 3:
        reminder_template = os.path.join(dir_path, REMI_FOLDER, '3_mahnung_vorlage.docx')
        docName = '2.Mahnung_eAuto_Nr_'
    elif vorlage == 4:
        reminder_template = os.path.join(dir_path, REMI_FOLDER, '4_mahnung_vorlage.docx')
        docName = '2.Mahnung_HalterAb_Nr_'
    else:
        exportFailed = True
        return exportFailed

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
        # check data
        is_busse    = str(busse.db_bussennr)
        is_datum    = busse.db_aufnahmedatum
        is_schild   = busse.db_nummerschild
        is_anred    = busse.db_anrede
        is_name     = busse.db_name
        is_stra1    = busse.db_strasse
        is_stra2    = busse.db_zusatz
        is_platz    = busse.db_plz
        is_ort      = busse.db_ort
        is_land     = busse.db_land             # muss gueltiger code sein gem. ISO-3166, deshalb nicht in QR Rechnung
        is_m1datum  = busse.db_mahndatum_1
        is_mahn     = m_mahn
        old_pic     = "qr"

        if is_name == None:
            is_name = 'kein Name'
        if is_stra1 == None:
            is_stra1 = 'keine Strasse'
        if is_ort == None:
            is_ort = 'kein Ort'
        if is_platz == None:
            is_platz = 'kein PLZ'
        if is_datum == None:
            is_busse = datetime(2000, 1, 1, 0, 0)
        if is_stra2 == None:
            is_stra2 = 'NULL'
        if is_m1datum == None:
            is_m1datum = date(2000, 1, 1)

        # generate qr code
        my_bill = QRBill(
            language="de",
            font_factor=0.85,
            account='CH200025125183542001D',
            creditor={
                'name'      : "Dolder Eis & Bad AG",
                'street'    : 'Adlisbergstrasse 36',
                'pcode'     : "8098", 
                'city'      : "Zürich", 
                'country'   : "CH",
            },
            debtor={
                'name'      : is_name,
                'street'    : is_stra1,
                #'house_num': '28',
                'pcode'     : is_ort,
                'city'      : is_platz,
                #'country'   : is_land,
            },
            additional_information= "Nachzahlgebühr-Nr.: " + is_busse,
            amount= is_mahn,
        )

        # generate svg from bill
        my_bill.as_svg(qr_pic1)
        # Convert SVG file to PNG file
        svg2png(url=qr_pic1, write_to=qr_pic2, dpi=200)

        # lade template document
        doc = DocxTemplate(reminder_template)

        # setze variablen
        context = { 
            'anrede'    : is_anred,
            'name'      : is_name,
            'strasse1'  : is_stra1,
            'strasse2'  : is_stra2,
            'plz'       : is_platz,
            'ort'       : is_ort,
            'land'      : is_land,
            'datum'     : is_datum.strftime('%d.%m.%Y'),
            'uhrz'      : is_datum.strftime('%H:%M'),
            'm1datum'   : is_m1datum.strftime('%d.%m.%Y'),
            'kennz'     : is_schild,
            'busse'     : is_busse,
            'heute'     : date.today().strftime('%d.%m.%Y'),
            }

        # ersetze QR Vorlagebild mit generiertem QR
        doc.replace_pic(old_pic, qr_pic2)
        
        # verarbeite generiertes document
        doc.render(context)
        doc.save(reminder_file)

        docName = docName + is_busse + '_DolderPark.docx'

        return send_file(
            reminder_file,
            mimetype="application/msword",
            #download_name= 'Mahnung_Bussennr_' + is_busse + '_DolderPark.docx',
            download_name= docName,
            as_attachment=True)

    except Exception as exception:
        print("Reminder generation aborted")
        print("got the following exception: " + str(exception))
        exportFailed = True

        return exportFailed