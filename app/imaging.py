from pylibdmtx.pylibdmtx import encode
import qrcode
from PIL import Image, ImageColor, ImageFont, ImageDraw

def createDatamatrix(text: str):
    encoded = encode(text.encode('utf8'), "Ascii", "ShapeAuto")
    barcode = Image.frombytes('RGB', (encoded.width, encoded.height), encoded.pixels)
    return barcode

def createQRCode(text: str):
    return qrcode.make(text, box_size = 1)

def createBarcode(text: str, type: str):
    match type:
        case "QRCode":
            return createQRCode(text)
        case "DataMatrix":
            return createDatamatrix(text)
        case _:
            return createDatamatrix(text)

def createLabelImage(labelSize : tuple, endlessMargin : int, text : str, textFont : ImageFont, textFontSize : int, textMaxLines : int, barcode : Image, dueDate : str, dueDateFont : ImageFont):
    # For endless labels, swap dimensions to use the longer side
    if labelSize[1] == 0:  # endless label
        (height, width) = labelSize  # height becomes the fixed dimension (12mm), width becomes endless
    else:
        (width, height) = labelSize
    # default line spacing used by multiline_text, doesn't seem to have an effect if changed though but we need to take into account
    lineSpacing = 4
    # margin to use for label
    marginTop = 0
    marginBottom = 0

    # for endless labels with a width of zero (after dimension swap)
    if width == 0:
        # width should be barcode width + text width + margins
        (nameText, nameTextWidth) = wrapText(text, textFont, 1000, textMaxLines)  # use large max width for initial calculation
        
        # Calculate width based on whichever is longer: product text or due date
        text_width_needed = nameTextWidth
        
        if dueDate:
            (_, _, ddRight, _) = dueDateFont.getbbox(dueDate)
            text_width_needed = max(nameTextWidth, ddRight)  # use the longer of the two
        
        width = int(barcode.size[0] + text_width_needed + endlessMargin)  # minimal margins
        
        # ensure reasonable minimum width but not excessive
        width = max(width, barcode.size[0] + 50)
        
        print(f"Calculated width: {width} (barcode: {barcode.size[0]}, text: {nameTextWidth}, due_date: {dueDate})")
        
        marginTop = endlessMargin
        marginBottom = endlessMargin

    # increase the size of the barcode if space permits
    # ensure barcode doesn't exceed label width and height is reasonable
    max_barcode_width = min(width // 2, 200)  # limit barcode to half label width or 200px max
    if height > 50 and barcode.size[0] <= max_barcode_width:
        if (barcode.size[1] * 8) < height and (barcode.size[0] * 8) <= max_barcode_width:
            barcode = barcode.resize((barcode.size[0] * 8, barcode.size[1] * 8), Image.Resampling.NEAREST)
        elif (barcode.size[1] * 6) < height and (barcode.size[0] * 6) <= max_barcode_width:
            barcode = barcode.resize((barcode.size[0] * 6, barcode.size[1] * 6), Image.Resampling.NEAREST)
        elif (barcode.size[1] * 4) < height and (barcode.size[0] * 4) <= max_barcode_width:
            barcode = barcode.resize((barcode.size[0] * 4, barcode.size[1] * 4), Image.Resampling.NEAREST)
        elif (barcode.size[1] * 2) < height and (barcode.size[0] * 2) <= max_barcode_width:
            barcode = barcode.resize((barcode.size[0] * 2, barcode.size[1] * 2), Image.Resampling.NEAREST)
    
    label = Image.new("RGB", (width, height), ImageColor.getrgb("#FFF"))
    # vertically align barcode (ignoring margin)
    barcode_padding = [0, (int)((label.size[1] / 2) - (barcode.size[1] / 2))]
    label.paste(barcode, barcode_padding)
    
    draw = ImageDraw.Draw(label)

    # For endless labels, calculate text width without constraints first
    if labelSize[1] == 0:  # endless label
        # Get the natural width of the text without wrapping
        natural_text_width = textFont.getlength(text)
        (nameText, nameTextWidth) = (text, natural_text_width)  # use text as-is for endless labels
    else:
        (nameText, nameTextWidth) = wrapText(text, textFont, width - barcode.size[0], textMaxLines)
    
    # For endless labels, place text with minimal spacing after barcode
    if labelSize[1] == 0:  # endless label
        text_x = barcode.size[0] + 5  # minimal 5px gap
    else:
        # Original layout with centered text for fixed labels
        nameMaxWidth = width - barcode.size[0]
        nameLeftMargin = (nameMaxWidth - nameTextWidth) / 2
        text_x = barcode.size[0] + nameLeftMargin

    draw.multiline_text(
        [text_x, marginTop],
        nameText,
        fill = ImageColor.getrgb("#000"),
        font = textFont,
        align = "left" if labelSize[1] == 0 else "center",
        spacing = lineSpacing
    )

    if dueDate:
        (_, _, ddRight, ddBottom) = dueDateFont.getbbox(dueDate)
        
        # For endless labels, place due date below text 
        if labelSize[1] == 0:  # endless label
            if ddRight > nameTextWidth:
                # Due date is longer - position it normally from text_x
                due_date_x = text_x
            else:
                # Product text is longer - align due date right edge with text end
                due_date_x = text_x + nameTextWidth - ddRight
            due_date_y = label.size[1] - ddBottom - marginBottom  # bottom position as before
        else:
            # Original layout - bottom right corner for fixed labels
            due_date_x = label.size[0] - ddRight
            due_date_y = label.size[1] - ddBottom - marginBottom
            
        draw.text(
            [due_date_x, due_date_y],
            dueDate,
            fill = ImageColor.getrgb("#000"),
            font = dueDateFont
        )

    # For endless labels, rotate the image to match printer orientation
    if labelSize[1] == 0:  # endless label
        label = label.rotate(-90, expand=True)
    
    return label

def wrapText(text : str, font : ImageFont, maxWidth : int, maxLines : int):
    # safety check for extremely narrow labels
    if maxWidth < 20:
        # for very narrow labels, just truncate the text
        truncated = text[:5] + "..." if len(text) > 5 else text
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
            if maxWidth < min_char_width * 2:
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
