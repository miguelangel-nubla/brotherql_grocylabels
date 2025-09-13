from io import BytesIO
from os import path, getenv
import logging
from flask import Flask, Response, request
from PIL import ImageFont
from dotenv import load_dotenv
from brother_ql.labels import ALL_LABELS, Color
from brother_ql import BrotherQLRaster, create_label
from brother_ql.backends import guess_backend, backend_factory
from app.imaging import create_barcode, create_label_image

load_dotenv()

class Config:
    """Application configuration."""
    LABEL_SIZE = getenv("LABEL_SIZE", "62x29")
    PRINTER_MODEL = getenv("PRINTER_MODEL", "QL-500")
    PRINTER_PATH = getenv("PRINTER_PATH", "file:///dev/usb/lp1")
    PRINTER_600DPI = getenv("PRINTER_600DPI", "true").lower() == "true"
    BARCODE_FORMAT = getenv("BARCODE_FORMAT", "Datamatrix")
    NAME_FONT = getenv("NAME_FONT", "NotoSerif-Regular.ttf")
    NAME_FONT_SIZE = int(getenv("NAME_FONT_SIZE", "48"))
    NAME_MAX_LINES = int(getenv("NAME_MAX_LINES", "4"))
    DUE_DATE_FONT = getenv("DUE_DATE_FONT", getenv("NAME_FONT", "NotoSerif-Regular.ttf"))
    DUE_DATE_FONT_SIZE = int(getenv("DUE_DATE_FONT_SIZE", "30"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Initialize printer configuration
selected_backend = guess_backend(Config.PRINTER_PATH)
BACKEND_CLASS = backend_factory(selected_backend)['backend_class']
label_spec = next(x for x in ALL_LABELS if x.identifier == Config.LABEL_SIZE)

# Load fonts
thisDir = path.dirname(path.abspath(__file__))
nameFont = ImageFont.truetype(path.join(thisDir, "..", "fonts", Config.NAME_FONT), Config.NAME_FONT_SIZE)
ddFont = ImageFont.truetype(path.join(thisDir, "..", "fonts", Config.DUE_DATE_FONT), Config.DUE_DATE_FONT_SIZE)

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
    """Extract and validate parameters from request."""
    # Handle different data sources
    if request.method == "POST" and request.is_json:
        source = request.get_json()
        logging.debug(f"POST JSON request - Data: {source}")
    elif request.method == "POST":
        source = request.form
        logging.debug(f"POST form request - Data: {dict(source)}")
    else:
        source = request.args
        logging.debug(f"GET request - Query params: {dict(source)}")

    # Extract name from various fields
    name_fields = ['product', 'battery', 'chore', 'recipe']
    name = next((source.get(field, '') for field in name_fields if source.get(field)), '')
    
    barcode = source.get('grocycode', '')
    
    # Extract stock entry data
    stock_entry = source.get('stock_entry') or {}
    if not isinstance(stock_entry, dict):
        stock_entry = {}
    
    dates = {
        'best_before_date': str(stock_entry.get('best_before_date', '')) if stock_entry.get('best_before_date') else '',
        'purchased_date': str(stock_entry.get('purchased_date', '')) if stock_entry.get('purchased_date') else '',
        'amount': str(stock_entry.get('amount', '')) if stock_entry.get('amount') else ''
    }
    
    # Extract unit info
    quantity_unit_stock = (
        source.get('quantity_unit_stock') if isinstance(source.get('quantity_unit_stock'), dict)
        else source.get('details', {}).get('quantity_unit_stock', {})
    )
    
    unit_name = _get_unit_name(quantity_unit_stock, dates['amount'])
    
    logging.debug(f"Extracted - name: '{name}', barcode: '{barcode}', dates: {dates}, unit: '{unit_name}'")
    return (name, barcode, dates['best_before_date'], dates['purchased_date'], dates['amount'], unit_name)

def _get_unit_name(quantity_unit_stock, amount):
    """Get appropriate unit name (singular/plural)."""
    if not quantity_unit_stock.get('name'):
        return ''
    
    try:
        amount_float = float(amount) if amount else 0
        if amount_float > 1 and quantity_unit_stock.get('name_plural'):
            return str(quantity_unit_stock['name_plural'])
        return str(quantity_unit_stock['name'])
    except (ValueError, TypeError):
        return str(quantity_unit_stock.get('name', ''))

@app.route("/print", methods=["GET", "POST"])
def print_route():
    """Generate and print a label."""
    logging.debug(f"Print endpoint: {request.method} {request.url}")
    params = get_params()
    label = _create_label(*params)
    sendToPrinter(label)
    logging.debug("Label sent to printer successfully")
    return Response("OK", 200)

@app.route("/image")
def image_route():
    """Generate and return label image."""
    logging.debug(f"Image endpoint: {request.method} {request.url}")
    params = get_params()
    img = _create_label(*params)
    
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    
    logging.debug("Label image generated successfully")
    return Response(buf, 200, mimetype="image/png")

def _create_label(name, barcode_text, best_before_date, purchased_date, amount, unit_name):
    """Create label image with given parameters."""
    barcode = create_barcode(barcode_text, Config.BARCODE_FORMAT)
    return create_label_image(
        label_spec.dots_total, name, nameFont, Config.NAME_MAX_LINES,
        barcode, best_before_date, purchased_date, amount, unit_name, ddFont
    )

def sendToPrinter(image):
    """Send image to Brother QL printer."""
    bql = BrotherQLRaster(Config.PRINTER_MODEL)
    bql.dpi_600 = Config.PRINTER_600DPI
    
    create_label(
        bql, image, Config.LABEL_SIZE,
        red=(label_spec.color == Color.BLACK_RED_WHITE)
    )
    
    backend = BACKEND_CLASS(Config.PRINTER_PATH)
    backend.write(bql.data)
    backend.dispose() if hasattr(backend, 'dispose') else None
