import re

from datetime import datetime


def clean_text(text):
    """Clean OCR text for easier analysis."""

    text = text.replace("\n", " ")

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def extract_amount(text):
    """Extract Indian Rupee amounts."""

    patterns = [
        r"(?:₹|rs\.?|inr)\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)",

        r"(?:amount|pay|payment|total)\s*(?:is|of|:)?\s*(?:₹|rs\.?|inr)?\s*([0-9]{2,}(?:\.[0-9]{1,2})?)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            try:

                value = match.group(1).replace(
                    ",",
                    ""
                )

                return float(value)

            except ValueError:

                pass

    return None


def extract_phone_number(text):
    """Extract Indian mobile numbers."""

    matches = re.findall(
        r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b",
        text
    )

    if matches:

        return matches[0]

    return None


def extract_upi_id(text):
    """Extract UPI ID."""

    pattern = r"\b[a-zA-Z0-9._-]{2,}@[a-zA-Z]{2,}\b"

    match = re.search(
        pattern,
        text
    )

    if match:

        return match.group(0)

    return None


def extract_transaction_id(text):
    """Extract transaction/reference IDs."""

    patterns = [

        r"(?:transaction\s*(?:id|no|number)|txn\s*(?:id|no)|reference\s*(?:id|no))\s*[:#-]?\s*([A-Za-z0-9-]{6,})",

        r"\b(?:TXN|UPI|REF)[A-Za-z0-9-]{6,}\b"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            if match.lastindex:

                return match.group(1)

            return match.group(0)

    return None


def extract_utr(text):
    """Extract UTR numbers."""

    patterns = [

        r"(?:utr)\s*[:#-]?\s*([A-Za-z0-9]{8,})",

        r"\b[0-9]{12}\b"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            if match.lastindex:

                return match.group(1)

            return match.group(0)

    return None


def extract_date(text, filename=None):
    """Extract date from OCR or filename."""

    date_patterns = [

        r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b",

        r"\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b",

        r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b"
    ]

    for pattern in date_patterns:

        match = re.search(
            pattern,
            text
        )

        if match:

            return match.group(0)

    # WhatsApp filename fallback
    if filename:

        match = re.search(
            r"\b(20\d{2}-\d{2}-\d{2})\b",
            filename
        )

        if match:

            return match.group(1)

    return None


def extract_merchant(text):
    """
    Try to identify the recipient/merchant from
    common payment wording.
    """

    patterns = [

        r"(?:paid\s+to|payment\s+to|pay\s+to|sent\s+to)\s+([A-Za-z][A-Za-z0-9 .&'-]{2,50})",

        r"(?:merchant|recipient|receiver|payee)\s*[:\-]?\s*([A-Za-z][A-Za-z0-9 .&'-]{2,50})"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            merchant = match.group(1).strip()

            merchant = re.sub(
                r"\s+",
                " ",
                merchant
            )

            return merchant

    return None


def detect_payment_method(text):
    """Detect payment application/method."""

    text_lower = text.lower()

    methods = [

        ("Paytm", ["paytm"]),

        ("Google Pay", ["google pay", "gpay"]),

        ("PhonePe", ["phonepe", "phone pe"]),

        ("UPI", ["upi"]),

        ("Credit Card", ["credit card"]),

        ("Debit Card", ["debit card"]),

        ("Net Banking", ["net banking"]),

        ("Bank Transfer", ["bank transfer"])
    ]

    for method, keywords in methods:

        for keyword in keywords:

            if keyword in text_lower:

                return method

    return None


def detect_payment_status(text):
    """Detect payment status."""

    text_lower = text.lower()

    success_words = [

        "payment successful",

        "payment success",

        "paid successfully",

        "transaction successful",

        "transaction success",

        "payment completed",

        "paid"
    ]

    failed_words = [

        "payment failed",

        "transaction failed",

        "payment unsuccessful",

        "transaction unsuccessful",

        "declined",

        "rejected"
    ]

    for word in failed_words:

        if word in text_lower:

            return "failed"

    for word in success_words:

        if word in text_lower:

            return "success"

    return "unknown"


def extract_payment_details(
    text: str,
    filename: str = None
):
    """
    Extract payment details from OCR text.

    Privacy note:
    Raw OCR text is intentionally not printed or logged.
    """

    amount = extract_amount(
        text
    )

    merchant = extract_merchant(
        text
    )

    date = extract_date(
        text,
        filename
    )

    transaction_id = extract_transaction_id(
        text
    )

    utr = extract_utr(
        text
    )

    phone_number = extract_phone_number(
        text
    )

    upi_id = extract_upi_id(
        text
    )

    payment_method = detect_payment_method(
        text
    )

    payment_status = detect_payment_status(
        text
    )

    return {
        "amount": amount,

        "merchant": merchant,

        "date": date,

        "transaction_id": transaction_id,

        "utr": utr,

        "phone_number": phone_number,

        "upi_id": upi_id,

        "payment_method": payment_method,

        "payment_status": payment_status
    }