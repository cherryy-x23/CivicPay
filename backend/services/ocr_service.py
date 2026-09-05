import os
import shutil

import cv2
import pytesseract
from dotenv import load_dotenv

load_dotenv()


# =====================================================
# TESSERACT CONFIGURATION
# =====================================================

TESSERACT_CMD = os.getenv("TESSERACT_CMD")

if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

elif os.name == "nt":
    windows_tesseract = (
        r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    )

    if os.path.exists(windows_tesseract):
        pytesseract.pytesseract.tesseract_cmd = (
            windows_tesseract
        )

elif shutil.which("tesseract"):
    pytesseract.pytesseract.tesseract_cmd = (
        shutil.which("tesseract")
    )


# =====================================================
# QR REMOVAL
# =====================================================

def remove_qr_from_image(image):
    """
    Detect a QR code region and cover it before OCR.

    This prevents the QR pattern from being interpreted
    as random OCR characters.
    """

    detector = cv2.QRCodeDetector()

    try:
        data, points, _ = detector.detectAndDecode(image)

        if points is not None:
            points = points[0].astype(int)

            x_min = max(
                0,
                int(points[:, 0].min()) - 20
            )

            x_max = min(
                image.shape[1],
                int(points[:, 0].max()) + 20
            )

            y_min = max(
                0,
                int(points[:, 1].min()) - 20
            )

            y_max = min(
                image.shape[0],
                int(points[:, 1].max()) + 20
            )

            image[y_min:y_max, x_min:x_max] = 255

    except Exception:
        # QR detection must never prevent OCR.
        pass

    return image


# =====================================================
# OCR TEXT CLEANING
# =====================================================

def clean_text(text):
    """
    Clean OCR output and remove duplicate lines.
    """

    lines = []
    existing_lines = set()

    for line in text.splitlines():
        line = line.strip()

        if not line:
            continue

        # Ignore one-character OCR noise.
        if len(line) <= 1:
            continue

        normalized = line.lower()

        if normalized in existing_lines:
            continue

        existing_lines.add(normalized)
        lines.append(line)

    return "\n".join(lines)


# =====================================================
# IMAGE PREPARATION
# =====================================================

def prepare_image_for_ocr(image):
    """
    Prepare an image for OCR.

    The image is converted to grayscale and resized only
    when necessary. This avoids unnecessarily processing
    already-large screenshots.
    """

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    height, width = gray.shape[:2]

    # OCR works well with moderate-size screenshots.
    # Avoid huge images because they make Tesseract slow.
    max_dimension = 2200

    current_max = max(height, width)

    if current_max < 1400:
        scale = 1.5

        gray = cv2.resize(
            gray,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC
        )

    elif current_max > max_dimension:
        scale = max_dimension / current_max

        gray = cv2.resize(
            gray,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_AREA
        )

    return gray


# =====================================================
# EXTRACT TEXT
# =====================================================

def extract_text(image_path: str):
    """
    Extract payment-related text from an image using
    Tesseract OCR.

    The function intentionally does not print or log
    extracted text because payment screenshots may contain
    sensitive financial information.

    Only one optimized Tesseract pass is performed to
    reduce processing time on cloud deployment.
    """

    image = cv2.imread(image_path)

    if image is None:
        return ""

    # =================================================
    # REMOVE QR FROM OCR INPUT
    # =================================================

    image_for_ocr = image.copy()

    image_for_ocr = remove_qr_from_image(
        image_for_ocr
    )

    # =================================================
    # PREPARE IMAGE
    # =================================================

    processed = prepare_image_for_ocr(
        image_for_ocr
    )

    # =================================================
    # LIGHT CONTRAST IMPROVEMENT
    # =================================================

    processed = cv2.GaussianBlur(
        processed,
        (3, 3),
        0
    )

    # =================================================
    # SINGLE OCR PASS
    # =================================================

    try:
        text = pytesseract.image_to_string(
            processed,
            config="--psm 6"
        )

    except Exception:
        return ""

    # =================================================
    # CLEAN OCR
    # =================================================

    return clean_text(text)