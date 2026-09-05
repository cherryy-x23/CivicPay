import os
import shutil

import cv2
import pytesseract
from dotenv import load_dotenv


# Load environment variables from .env
load_dotenv()


# =====================================================
# TESSERACT CONFIGURATION
# =====================================================

# Use an explicitly configured Tesseract executable
# when provided through the environment.
TESSERACT_CMD = os.getenv("TESSERACT_CMD")

if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

elif os.name == "nt":
    # Windows local-development fallback.
    windows_tesseract = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )

    if os.path.exists(windows_tesseract):
        pytesseract.pytesseract.tesseract_cmd = (
            windows_tesseract
        )

elif shutil.which("tesseract"):
    # Linux/macOS fallback when Tesseract is available
    # in the system PATH.
    pytesseract.pytesseract.tesseract_cmd = (
        shutil.which("tesseract")
    )


def remove_qr_from_image(image):
    """
    Detect QR code regions and cover them so OCR
    does not try to read QR patterns as text.
    """
    detector = cv2.QRCodeDetector()

    try:
        data, points, _ = detector.detectAndDecode(image)

        if points is not None:
            points = points[0].astype(int)

            x_min = max(0, points[:, 0].min() - 20)
            x_max = min(image.shape[1], points[:, 0].max() + 20)

            y_min = max(0, points[:, 1].min() - 20)
            y_max = min(image.shape[0], points[:, 1].max() + 20)

            # Cover QR area with white
            image[y_min:y_max, x_min:x_max] = 255

    except Exception:
        pass

    return image


def clean_text(text):
    """
    Clean OCR output and remove duplicate lines.
    """
    lines = []

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        # Ignore extremely short garbage
        if len(line) <= 1:
            continue

        # Avoid duplicate lines
        if line.lower() not in [
            existing.lower()
            for existing in lines
        ]:
            lines.append(line)

    return "\n".join(lines)


def extract_text(image_path: str):
    """
    Extract text from an image using Tesseract OCR.

    The function returns cleaned OCR text but does not
    print or log the extracted text, protecting sensitive
    payment information from terminal logs.
    """

    image = cv2.imread(image_path)

    if image is None:
        return ""

    # =====================================================
    # REMOVE QR FROM OCR IMAGE
    # =====================================================

    image_for_ocr = image.copy()

    image_for_ocr = remove_qr_from_image(
        image_for_ocr
    )

    # =====================================================
    # GRAYSCALE
    # =====================================================

    gray = cv2.cvtColor(
        image_for_ocr,
        cv2.COLOR_BGR2GRAY
    )

    # =====================================================
    # UPSCALE
    # =====================================================

    enlarged = cv2.resize(
        gray,
        None,
        fx=2,
        fy=2,
        interpolation=cv2.INTER_CUBIC
    )

    # =====================================================
    # CONTRAST / THRESHOLD
    # =====================================================

    threshold = cv2.threshold(
        enlarged,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )[1]

    # =====================================================
    # OCR PASS 1
    # =====================================================

    text1 = pytesseract.image_to_string(
        enlarged,
        config="--psm 6"
    )

    # =====================================================
    # OCR PASS 2
    # =====================================================

    text2 = pytesseract.image_to_string(
        threshold,
        config="--psm 6"
    )

    # =====================================================
    # COMBINE
    # =====================================================

    combined = text1 + "\n" + text2

    # =====================================================
    # CLEAN
    # =====================================================

    return clean_text(combined)