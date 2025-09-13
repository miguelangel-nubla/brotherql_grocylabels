"""Barcode generation utilities."""

import treepoem
import qrcode
from PIL import Image


def create_datamatrix(text: str) -> Image.Image:
    """Create a Data Matrix barcode, fallback to QR code if it fails."""
    try:
        barcode = treepoem.generate_barcode(barcode_type='datamatrix', data=text)
        return barcode.convert('RGB')
    except Exception:
        return create_qr_code(text)


def create_qr_code(text: str) -> Image.Image:
    """Create a QR code with minimal border."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=1,
        border=0
    )
    qr.add_data(text)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to PIL Image if needed
    if hasattr(qr_image, 'get_image'):
        return qr_image.get_image()
    return qr_image.convert('RGB')


def create_barcode(text: str, barcode_type: str) -> Image.Image:
    """Create barcode based on type."""
    if barcode_type == "QRCode":
        return create_qr_code(text)
    return create_datamatrix(text)  # Default to DataMatrix