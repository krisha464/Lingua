# utils/ocr.py


import textwrap
import io
import tempfile
from PIL import Image, ImageDraw, ImageFont
import os
from fpdf import FPDF

# OCR libs (optional)
try:
    import pytesseract
    _HAS_TESSERACT = True
except Exception:
    _HAS_TESSERACT = False


try:
    import easyocr
    _HAS_EASYOCR = True
except Exception:
    _HAS_EASYOCR = False
    
def _save_image(uploaded_file):
    """Save uploaded file (Streamlit UploadFile-like) to temporary path and return path."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        tmp.write(uploaded_file.read())
        return tmp.name
    
def extract_text_from_image(uploaded_file, lang="en"):
    """
    Extract text + bounding boxes from an uploaded image file.
    Returns: (text, boxes) where boxes = [((x1,y1,w,h), text), ...]
    """
    path = _save_image(uploaded_file)
    try:
        img = Image.open(path)
    except Exception as e:
        raise RuntimeError("Could not open uploaded image.") from e

    results = []
    text_out = ""

    # pytesseract approach: uses image_to_data
    if _HAS_TESSERACT:
        try:
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, lang=lang)
            n = len(data.get("text", []))
            for i in range(n):
                txt = data["text"][i].strip()
                if txt:
                    x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                    results.append(((x, y, w, h), txt))
                    text_out += txt + " "
            if results:
                os.unlink(path)
                return text_out.strip(), results
        except Exception:
            pass

    # easyocr fallback
    if _HAS_EASYOCR:
        try:
            reader = easyocr.Reader([lang], gpu=False)
            detections = reader.readtext(path)
            for bbox, text, conf in detections:
                (x_min, y_min), (x_max, y_max) = bbox[0], bbox[2]
                w, h = x_max - x_min, y_max - y_min
                results.append(((int(x_min), int(y_min), int(w), int(h)), text))
                text_out += text + " "
            if results:
                os.unlink(path)
                return text_out.strip(), results
        except Exception:
            pass

    # nothing found
    try:
        os.unlink(path)
    except Exception:
        pass
    return "", [] 
def draw_bounding_boxes(image_bytes, boxes, translated_boxes):
    """
    Draw bounding boxes and overlay translated text on image.
    - image_bytes: raw bytes or BytesIO
    - boxes: list of ((x,y,w,h), original_text)
    - translated_boxes: list of translated text (matching order)
    Returns PIL.Image
    """
    # open image
    if isinstance(image_bytes, bytes):
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    else:
        # BytesIO-like
        img = Image.open(image_bytes).convert("RGB")

    draw = ImageDraw.Draw(img)
   
    try:
        font = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        font = ImageFont.load_default()

    for (bbox, original_text), translated_text in zip(boxes, translated_boxes):
        x1, y1, w, h = bbox
        x2, y2 = x1 + w, y1 + h
        draw.rectangle([x1, y1, x2, y2], outline=(255,0,0), width=2)
        # wrap text to fit inside width
        max_chars = max(10, w // 8)
        wrapped = textwrap.fill(translated_text or "", width=max_chars)
        # background rectangle for readability
        text_size = draw.multiline_textsize(wrapped, font=font)
        padding = 4
        rect_x2 = x1 + text_size[0] + padding*2
        rect_y2 = y1 + text_size[1] + padding*2
        draw.rectangle([x1, y1 - padding, rect_x2, rect_y2 - padding], fill=(0,0,0,160))
        draw.multiline_text((x1+padding, y1+padding), wrapped, fill=(255,255,0), font=font)
    return img

def export_ocr_pdf(ocr_results, output_path="ocr_report.pdf"):
    """
    ocr_results: list of dicts with keys:
      - original_img (bytes)
      - translated_img (bytes)
      - extracted (str)
      - translated (str)
    Produces a simple PDF report with images and texts.
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    for res in ocr_results:
        pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, "OCR Result", ln=True)
        pdf.ln(4)
        # Insert original image
        try:
            # save temp
            tmp_in = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            tmp_in.write(res["original_img"])
            tmp_in.flush()
            tmp_in.close()
            pdf.image(tmp_in.name, w=90)
            os.unlink(tmp_in.name)
        except Exception:
            pass
        pdf.set_xy(110, 20)
        pdf.set_font("Arial", size=10)
        extracted = (res.get("extracted") or "")[:1000]
        pdf.multi_cell(0, 6, f"Extracted: {extracted}")
        pdf.ln(3)
        # Insert translated image
        try:
            tmp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            tmp_out.write(res["translated_img"])
            tmp_out.flush()
            tmp_out.close()
            pdf.image(tmp_out.name, w=90)
            os.unlink(tmp_out.name)
        except Exception:
            pass
        pdf.ln(4)
        translated = (res.get("translated") or "")[:1000]
        pdf.multi_cell(0, 6, f"Translated: {translated}")
    pdf.output(output_path)
    return output_path
    