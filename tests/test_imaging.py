#!/usr/bin/env python3
"""Comprehensive test suite for imaging functions."""

import sys
import os
from PIL import ImageFont, Image

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.imaging import create_barcode, create_label_image, wrap_text

def test_barcode_creation():
    """Test barcode creation functions."""
    print("Testing barcode creation...")
    
    # Test QR Code
    qr_code = create_barcode("test_data", "QRCode")
    print(f"QR code type: {type(qr_code)}")
    assert isinstance(qr_code, Image.Image), f"QR code should return PIL Image, got {type(qr_code)}"
    assert qr_code.size[0] > 0 and qr_code.size[1] > 0, "QR code should have valid dimensions"
    print("✓ QR code creation works")
    
    # Test DataMatrix (default)
    datamatrix = create_barcode("test_data", "DataMatrix")
    print(f"DataMatrix type: {type(datamatrix)}")
    assert isinstance(datamatrix, Image.Image), f"DataMatrix should return PIL Image, got {type(datamatrix)}"
    assert datamatrix.size[0] > 0 and datamatrix.size[1] > 0, "DataMatrix should have valid dimensions"
    print("✓ DataMatrix creation works")

def test_text_wrapping():
    """Test text wrapping function."""
    print("Testing text wrapping...")
    
    # Create a simple font for testing
    try:
        # Try to use a system font or fallback to default
        font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # Test normal text wrapping
    wrapped_text, width = wrap_text("This is a long text that should wrap", font, 100, 3)
    assert isinstance(wrapped_text, str), "Wrapped text should be string"
    assert isinstance(width, (int, float)), "Width should be numeric"
    assert '\n' in wrapped_text or len(wrapped_text.split()) <= 3, "Text should wrap or be short"
    print("✓ Text wrapping works")
    
    # Test with very narrow width
    wrapped_text, width = wrap_text("VeryLongWordThatShouldNotFit", font, 20, 2)
    assert isinstance(wrapped_text, str), "Wrapped text should be string even with narrow width"
    print("✓ Narrow width text wrapping works")

def test_label_creation():
    """Test label image creation."""
    print("Testing label creation...")
    
    try:
        font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    # Create test barcode
    barcode = create_barcode("test", "QRCode")
    
    # Test endless label (width = 0)
    label_size = (200, 0)  # height, width for endless
    label = create_label_image(
        label_size=label_size,
        text="Test Product Name",
        text_font=font,
        text_max_lines=2,
        barcode=barcode,
        best_before_date="2024-12-31",
        purchased_date="2024-01-01",
        amount="1.5",
        unit_name="kg"
    )
    
    assert isinstance(label, Image.Image), "Label should return PIL Image"
    assert label.size[0] > 0 and label.size[1] > 0, "Label should have valid dimensions"
    print("✓ Endless label creation works")
    
    # Test fixed label
    label_size = (400, 200)  # width, height for fixed
    label = create_label_image(
        label_size=label_size,
        text="Test Product",
        text_font=font,
        text_max_lines=2,
        barcode=barcode
    )
    
    assert isinstance(label, Image.Image), "Fixed label should return PIL Image"
    assert label.size == (400, 200), "Fixed label should maintain specified dimensions"
    print("✓ Fixed label creation works")

def main():
    """Run all tests."""
    print("Running imaging function tests...\n")
    
    try:
        test_barcode_creation()
        test_text_wrapping()
        test_label_creation()
        print("\n✅ All tests passed! The refactored code works correctly.")
        return True
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)