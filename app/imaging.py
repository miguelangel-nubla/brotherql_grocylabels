import treepoem
import qrcode
from PIL import Image, ImageColor, ImageFont, ImageDraw

def createDatamatrix(text: str):
    try:
        # Use treepoem for Data Matrix generation
        barcode = treepoem.generate_barcode(
            barcode_type='datamatrix',
            data=text
        )
        return barcode.convert('RGB')
    except Exception:
        # If data matrix fails, fall back to QR code which is more flexible
        return createQRCode(text)

def createQRCode(text: str):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=1,
        border=0  # Remove white border
    )
    qr.add_data(text)
    qr.make(fit=True)
    qr_image = qr.make_image(fill_color="black", back_color="white")
    return qr_image

def createBarcode(text: str, type: str):
    match type:
        case "QRCode":
            return createQRCode(text)
        case "DataMatrix":
            return createDatamatrix(text)
        case _:
            return createDatamatrix(text)

def createLabelImage(labelSize : tuple, printableSize : tuple, text : str, textFont : ImageFont, textMaxLines : int, barcode : Image, best_before_date : str, purchased_date : str, amount : str, unit_name : str, dueDateFont : ImageFont):
    is_endless = labelSize[1] == 0
    
    if is_endless:
        (height, width) = labelSize  # swap for endless: height=fixed, width=endless
    else:
        (width, height) = labelSize
        
    lineSpacing = 4

    # for endless labels with a width of zero (after dimension swap)
    if width == 0:
        # Scale barcode to fill the full height for endless labels
        scale_factor = height / barcode.size[1]
        new_barcode_width = int(barcode.size[0] * scale_factor)
        new_barcode_height = int(barcode.size[1] * scale_factor)
        barcode = barcode.resize((new_barcode_width, new_barcode_height), Image.Resampling.NEAREST)
        
        # Now calculate width with the scaled barcode
        (nameText, nameTextWidth) = wrapText(text, textFont, 1000, textMaxLines)  # use large max width for initial calculation
        
        # Create date display string
        date_display = ""
        if purchased_date and best_before_date:
            date_display = f"{purchased_date} - {best_before_date}"
        elif best_before_date:
            date_display = best_before_date
        elif purchased_date:
            date_display = purchased_date
            
        # Create amount display string
        amount_display = ""
        if amount and unit_name:
            amount_display = f"{amount} {unit_name}"
        elif amount:
            amount_display = amount
        
        # Calculate width based on whichever is longer: product text, date, or amount
        text_width_needed = nameTextWidth
        
        if date_display:
            (_, _, ddRight, _) = dueDateFont.getbbox(date_display)
            text_width_needed = max(text_width_needed, ddRight)
            
        if amount_display:
            (_, _, amountRight, _) = dueDateFont.getbbox(amount_display)
            text_width_needed = max(text_width_needed, amountRight)
        
        barcode_text_gap = textFont.size // 2  # gap is half the text height
        width = int(barcode.size[0] + barcode_text_gap + text_width_needed)
        
        # ensure reasonable minimum width but not excessive  
        width = max(width, barcode.size[0] + int(height * 0.4))  # use 40% of height as minimum text space
        
        print(f"Calculated width: {width} (barcode: {barcode.size[0]}, text: {nameTextWidth}, dates: {date_display}, amount: {amount_display})")
        print(f"Label dimensions - Total: {labelSize}, Printable: {printableSize}")
        print(f"Using height: {height}, width: {width}")

    # For fixed labels, keep original scaling logic
    if not is_endless:
        effective_height = height
        max_barcode_width = width // 2  # allow barcode to use up to half the width
        if effective_height > (height * 0.4) and barcode.size[0] <= max_barcode_width:  # require at least 40% of height
            if (barcode.size[1] * 8) < effective_height and (barcode.size[0] * 8) <= max_barcode_width:
                barcode = barcode.resize((barcode.size[0] * 8, barcode.size[1] * 8), Image.Resampling.NEAREST)
            elif (barcode.size[1] * 6) < effective_height and (barcode.size[0] * 6) <= max_barcode_width:
                barcode = barcode.resize((barcode.size[0] * 6, barcode.size[1] * 6), Image.Resampling.NEAREST)
            elif (barcode.size[1] * 4) < effective_height and (barcode.size[0] * 4) <= max_barcode_width:
                barcode = barcode.resize((barcode.size[0] * 4, barcode.size[1] * 4), Image.Resampling.NEAREST)
            elif (barcode.size[1] * 2) < effective_height and (barcode.size[0] * 2) <= max_barcode_width:
                barcode = barcode.resize((barcode.size[0] * 2, barcode.size[1] * 2), Image.Resampling.NEAREST)
    
    label = Image.new("RGB", (width, height), ImageColor.getrgb("#FFF"))
    # position barcode at top with no margins for endless, centered for fixed
    barcode_y = 0 if is_endless else (height - barcode.size[1]) // 2
    barcode_padding = [0, barcode_y]
    label.paste(barcode, barcode_padding)
    
    draw = ImageDraw.Draw(label)

    # Calculate text layout based on label type
    if is_endless:
        # Get the natural width of the text without wrapping
        natural_text_width = textFont.getlength(text)
        nameText, nameTextWidth = text, natural_text_width
        barcode_text_gap = textFont.size // 2  # gap is half the text height
        text_x = barcode.size[0] + barcode_text_gap  # add gap between barcode and text
        text_align = "left"
        
        # Adjust text position based on what's displayed
        if amount_display and not date_display:
            # Amount at top, center text vertically in remaining space
            amount_height = dueDateFont.size
            available_height = height - amount_height
            _, text_top, _, text_bottom = textFont.getbbox(nameText)
            actual_text_height = text_bottom - text_top
            text_y = amount_height + (available_height - actual_text_height) // 2 - text_top
        elif not date_display and not amount_display:
            # No date or amount, center text vertically
            _, text_top, _, text_bottom = textFont.getbbox(nameText)
            actual_text_height = text_bottom - text_top
            text_y = (height - actual_text_height) // 2 - text_top
        else:
            # Date present, keep text at top with space for amount if present
            text_y = dueDateFont.size if amount_display else 0
    else:
        # Wrap text and center it for fixed labels
        nameText, nameTextWidth = wrapText(text, textFont, width - barcode.size[0], textMaxLines)
        nameMaxWidth = width - barcode.size[0]
        nameLeftMargin = (nameMaxWidth - nameTextWidth) / 2
        text_x = barcode.size[0] + nameLeftMargin
        text_align = "center"
        text_y = 0  # fixed labels keep original positioning

    draw.multiline_text(
        [text_x, text_y],
        nameText,
        fill = ImageColor.getrgb("#000"),
        font = textFont,
        align = text_align,
        spacing = lineSpacing
    )

    # Display amount in top right if available
    if amount_display:
        (_, _, amountRight, _) = dueDateFont.getbbox(amount_display)
        
        if is_endless:
            # For endless labels, position in top right corner
            amount_x = label.size[0] - amountRight
            amount_y = 0
        else:
            # For fixed labels, position in top right corner
            amount_x = label.size[0] - amountRight
            amount_y = 0
            
        draw.text(
            [amount_x, amount_y],
            amount_display,
            fill = ImageColor.getrgb("#000"),
            font = dueDateFont
        )

    # Display date information if available
    if date_display:
        (_, _, ddRight, ddBottom) = dueDateFont.getbbox(date_display)
        
        # Position date based on label type
        if is_endless:
            # For endless labels, align date with text
            if ddRight > nameTextWidth:
                due_date_x = text_x  # Date is longer - position normally
            else:
                due_date_x = text_x + nameTextWidth - ddRight  # Align right edge with text end
            due_date_y = label.size[1] - ddBottom  # bottom position with no margin
        else:
            # For fixed labels, position in bottom right corner
            due_date_x = label.size[0] - ddRight
            due_date_y = label.size[1] - ddBottom
            
        draw.text(
            [due_date_x, due_date_y],
            date_display,
            fill = ImageColor.getrgb("#000"),
            font = dueDateFont
        )

    # For endless labels, rotate the image to match printer orientation
    if is_endless:
        label = label.rotate(-90, expand=True)
    
    return label

def wrapText(text : str, font : ImageFont, maxWidth : int, maxLines : int):
    # safety check for extremely narrow labels
    min_reasonable_width = font.getlength("A") * 3  # at least 3 characters wide
    if maxWidth < min_reasonable_width:
        # for very narrow labels, just truncate the text
        max_chars = max(1, int(maxWidth / font.getlength("A")))
        truncated = text[:max_chars] + ("..." if len(text) > max_chars else "")
        return (truncated, font.getlength(truncated))
    
    parts = text.split(" ")
    parts.reverse()
    lines = []
    longestLine = 0

    # break words that are too long for a single line
    trimmedParts = []
    for part in parts:
        if font.getlength(part) >= maxWidth:
            # prevent infinite loop by ensuring we can fit at least one character
            min_char_width = font.getlength("A")
            if maxWidth < min_char_width * 1.5:  # need at least 1.5 character widths
                # too narrow, just use first character
                trimmedParts.append(part[0] if part else "")
            else:
                # just chop in half, nothing fancy
                midpoint = int(len(part) / 2);
                trimmedParts.append(part[midpoint:])
                trimmedParts.append(part[0:midpoint] + '-')
        else:
            trimmedParts.append(part)

    parts = trimmedParts
    
    # create lines from input
    while len(parts) > 0:
        nextLine = []
        
        # create this line adding words while the next word fits
        while len(parts) > 0:
            nextPart = parts.pop()

            if font.getlength(' '.join(nextLine) + ' ' + nextPart) < maxWidth:
                nextLine.append(nextPart)
            else:
                # didn't fit so put it back on the stack
                parts.append(nextPart)
                break
        
        # safety check: if no words fit on this line, force at least one to prevent infinite loop
        if len(nextLine) == 0 and len(parts) > 0:
            nextLine.append(parts.pop()[:1])  # force at least one character
        
        # finished with the line
        if len(nextLine) > 0:
            lines.append(' '.join(nextLine))
            lineLength = font.getlength(' '.join(nextLine))
            if lineLength > longestLine:
                longestLine = lineLength
    
    if len(lines) > maxLines:
        lines = lines[0:maxLines]
        lines[-1] += '...'
        lineLength = font.getlength(lines[-1])
        if lineLength > longestLine:
            longestLine = lineLength

    return ('\n'.join(lines), longestLine)
