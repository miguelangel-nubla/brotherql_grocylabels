from io import BytesIO
from os import path, getenv
import logging
from flask import Flask, Response, request
from PIL import Image, ImageFont
from dotenv import load_dotenv
from brother_ql.labels import ALL_LABELS, Color
from brother_ql import BrotherQLRaster, create_label
from brother_ql.backends import guess_backend, backend_factory
from app.imaging import createBarcode, createLabelImage

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

LABEL_SIZE = getenv("LABEL_SIZE", "62x29")
PRINTER_MODEL = getenv("PRINTER_MODEL", "QL-500")
PRINTER_PATH = getenv("PRINTER_PATH", "file:///dev/usb/lp1")
BARCODE_FORMAT = getenv("BARCODE_FORMAT", "Datamatrix")
NAME_FONT = getenv("NAME_FONT", "NotoSerif-Regular.ttf")
NAME_FONT_SIZE = int(getenv("NAME_FONT_SIZE", "48"))
NAME_MAX_LINES = int(getenv("NAME_MAX_LINES", "4"))
DUE_DATE_FONT =  getenv("NAME_FONT", "NotoSerif-Regular.ttf")
DUE_DATE_FONT_SIZE = int(getenv("DUE_DATE_FONT_SIZE", "30"))
ENDLESS_MARGIN = int(getenv("ENDLESS_MARGIN", "10"))

selected_backend = guess_backend(PRINTER_PATH)
BACKEND_CLASS = backend_factory(selected_backend)['backend_class']

label_spec = next(x for x in ALL_LABELS if x.identifier == LABEL_SIZE)

thisDir = path.dirname(path.abspath(__file__))
nameFont = ImageFont.truetype(path.join(thisDir, "..", "fonts", NAME_FONT), NAME_FONT_SIZE)
ddFont = ImageFont.truetype(path.join(thisDir, "..", "fonts", DUE_DATE_FONT), DUE_DATE_FONT_SIZE)

app = Flask(__name__)

@app.before_request
def log_post_json_requests():
    if request.method == "POST" and request.is_json:
        json_data = request.get_json()
        endpoint = request.endpoint or request.path
        logging.info(f"POST JSON Request to {endpoint} - Data: {json_data}")

@app.route("/")
def home_route():
    return "Label %s, %s"%(label_spec.identifier, label_spec.name)

def get_params():
    # Handle different data sources: JSON, form data, or query params
    if request.method == "POST":
        if request.is_json:
            source = request.get_json()
            logging.debug(f"HTTP {request.method} request - JSON data: {source}")
        else:
            source = request.form
            logging.debug(f"HTTP {request.method} request - Form data: {dict(source)}")
    else:
        source = request.args
        logging.debug(f"HTTP {request.method} request - Query params: {dict(source)}")

    name = ""
    # Check for different name fields
    if 'product' in source:
        name = source['product']
    elif 'battery' in source:
        name = source['battery']
    elif 'chore' in source:
        name = source['chore']
    elif 'recipe' in source:
        name = source['recipe']
    
    barcode = source.get('grocycode', '')
    
    # Extract stock entry data (at top level)
    stock_entry = source.get('stock_entry', {}) if isinstance(source.get('stock_entry'), dict) else {}
    best_before_date = str(stock_entry.get('best_before_date', '')) if stock_entry.get('best_before_date') else ''
    purchased_date = str(stock_entry.get('purchased_date', '')) if stock_entry.get('purchased_date') else ''
    amount = str(stock_entry.get('amount', '')) if stock_entry.get('amount') else ''
    
    # Extract quantity unit stock data (check both top level and under details)
    quantity_unit_stock = {}
    if 'quantity_unit_stock' in source and isinstance(source['quantity_unit_stock'], dict):
        quantity_unit_stock = source['quantity_unit_stock']
    elif 'details' in source and isinstance(source['details'], dict) and 'quantity_unit_stock' in source['details']:
        quantity_unit_stock = source['details']['quantity_unit_stock']
    
    # Choose singular or plural unit name based on amount
    unit_name = ''
    if quantity_unit_stock.get('name'):
        try:
            amount_float = float(amount) if amount else 0
            if amount_float > 1 and quantity_unit_stock.get('name_plural'):
                unit_name = str(quantity_unit_stock.get('name_plural'))
            else:
                unit_name = str(quantity_unit_stock.get('name'))
        except (ValueError, TypeError):
            unit_name = str(quantity_unit_stock.get('name', ''))

    logging.debug(f"Extracted parameters - name: '{name}', barcode: '{barcode}', best_before_date: '{best_before_date}', purchased_date: '{purchased_date}', amount: '{amount}', unit: '{unit_name}'")

    return (name, barcode, best_before_date, purchased_date, amount, unit_name)

@app.route("/print", methods=["GET", "POST"])
def print_route():
    logging.debug(f"Print endpoint accessed: {request.method} {request.url}")
    (name, barcode, best_before_date, purchased_date, amount, unit_name) = get_params();

    label = createLabelImage(label_spec.dots_total, label_spec.dots_printable, name, nameFont, NAME_MAX_LINES, createBarcode(barcode, BARCODE_FORMAT), best_before_date, purchased_date, amount, unit_name, ddFont)

    buf = BytesIO()
    label.save(buf, format="PNG")
    buf.seek(0)
    sendToPrinter(label)

    logging.debug("Label sent to printer successfully")
    return Response("OK", 200)

@app.route("/image")
def test():
    logging.debug(f"Image endpoint accessed: {request.method} {request.url}")
    (name, barcode, best_before_date, purchased_date, amount, unit_name) = get_params();

    img = createLabelImage(label_spec.dots_total, label_spec.dots_printable, name, nameFont, NAME_MAX_LINES, createBarcode(barcode, BARCODE_FORMAT), best_before_date, purchased_date, amount, unit_name, ddFont)
    
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    logging.debug("Label image generated successfully")
    return Response(buf, 200, mimetype="image/png")

def sendToPrinter(image : Image):
    bql = BrotherQLRaster(PRINTER_MODEL)
    bql.dpi_600 = True  # Enable high resolution mode

    redLabel = label_spec.color == Color.BLACK_RED_WHITE

    create_label(
        bql,
        image,
        LABEL_SIZE,
        red=redLabel
    )

    be = BACKEND_CLASS(PRINTER_PATH)
    be.write(bql.data)
    del be
