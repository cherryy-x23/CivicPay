import re
from urllib.parse import parse_qs, urlparse, unquote


# ---------------------------------------------------------
# BASIC HELPERS
# ---------------------------------------------------------

def normalize_text(value):
    if value is None:
        return ""

    value = str(value).strip().lower()
    value = re.sub(r"\s+", " ", value)

    return value


def normalize_upi_id(value):
    if not value:
        return ""

    return normalize_text(value).replace(" ", "")


def normalize_merchant(value):
    if not value:
        return ""

    value = normalize_text(value)

    # Remove punctuation for comparison
    value = re.sub(r"[^a-z0-9 ]", "", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def amounts_match(value1, value2):
    if value1 is None or value2 is None:
        return False

    try:
        return abs(float(value1) - float(value2)) <= 0.01
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------
# UPI VALIDATION
# ---------------------------------------------------------

def is_valid_upi_id(upi_id):
    """
    Basic UPI ID format validation.

    Example:
        user@upi
        9876543210@ybl
        merchant-name@axl
    """

    if not upi_id:
        return False

    pattern = r"^[a-zA-Z0-9._-]{2,}@[a-zA-Z]{2,}$"

    return bool(re.match(pattern, str(upi_id).strip()))


# ---------------------------------------------------------
# QR PAYLOAD ANALYSIS
# ---------------------------------------------------------

def parse_upi_qr(qr_payload):
    result = {
        "is_valid": False,
        "upi_id": None,
        "merchant": None,
        "amount": None,
        "currency": None,
        "merchant_code": None,
        "mode": None,
        "purpose": None,
        "errors": []
    }

    if not qr_payload:
        result["errors"].append("QR payload is empty")
        return result

    try:
        parsed_url = urlparse(qr_payload)

        # Must be a UPI payment URI
        if parsed_url.scheme.lower() != "upi":
            result["errors"].append(
                "QR payload is not a UPI payment URI"
            )
            return result

        if parsed_url.netloc.lower() != "pay":
            result["errors"].append(
                "QR payload does not use the UPI pay endpoint"
            )
            return result

        parameters = parse_qs(parsed_url.query)

        # UPI ID
        if parameters.get("pa"):
            upi_id = unquote(parameters["pa"][0]).strip()

            result["upi_id"] = upi_id

            if not is_valid_upi_id(upi_id):
                result["errors"].append(
                    "UPI ID inside QR has an invalid format"
                )
        else:
            result["errors"].append(
                "QR does not contain a payee UPI ID"
            )

        # Merchant / recipient name
        if parameters.get("pn"):
            result["merchant"] = unquote(
                parameters["pn"][0]
            ).strip()

        # Amount
        if parameters.get("am"):
            amount_value = parameters["am"][0]

            try:
                amount = float(amount_value)

                if amount < 0:
                    result["errors"].append(
                        "QR contains a negative amount"
                    )
                else:
                    result["amount"] = amount

            except ValueError:
                result["errors"].append(
                    "QR contains an invalid amount"
                )

        # Currency
        if parameters.get("cu"):
            result["currency"] = parameters["cu"][0]

        # Merchant category code
        if parameters.get("mc"):
            result["merchant_code"] = parameters["mc"][0]

        # Transaction mode
        if parameters.get("mode"):
            result["mode"] = parameters["mode"][0]

        # Purpose
        if parameters.get("purpose"):
            result["purpose"] = parameters["purpose"][0]

        # A valid payment QR needs a valid UPI ID
        result["is_valid"] = (
            bool(result["upi_id"])
            and is_valid_upi_id(result["upi_id"])
            and not any(
                "invalid amount" in error.lower()
                for error in result["errors"]
            )
        )

        return result

    except Exception as e:
        result["errors"].append(
            f"QR parsing failed: {str(e)}"
        )

        return result


# ---------------------------------------------------------
# UPI ID CROSS-CHECK
# ---------------------------------------------------------

def check_upi_id(ocr_upi_id, qr_upi_id):
    result = {
        "field": "upi_id",
        "status": "missing",
        "ocr_value": ocr_upi_id,
        "qr_value": qr_upi_id,
        "message": ""
    }

    ocr_value = normalize_upi_id(ocr_upi_id)
    qr_value = normalize_upi_id(qr_upi_id)

    if not ocr_value and not qr_value:
        result["status"] = "missing"
        result["message"] = "UPI ID was not found"
        return result

    if not ocr_value:
        result["status"] = "single_source"
        result["message"] = (
            "UPI ID is available only from the QR code"
        )
        return result

    if not qr_value:
        result["status"] = "single_source"
        result["message"] = (
            "UPI ID is available only from OCR evidence"
        )
        return result

    if ocr_value == qr_value:
        result["status"] = "match"
        result["message"] = (
            "UPI ID matches between OCR evidence and QR"
        )
        return result

    result["status"] = "mismatch"
    result["message"] = (
        "UPI ID differs between OCR evidence and QR"
    )

    return result


# ---------------------------------------------------------
# MERCHANT CROSS-CHECK
# ---------------------------------------------------------

def check_merchant(ocr_merchant, qr_merchant):
    result = {
        "field": "merchant",
        "status": "missing",
        "ocr_value": ocr_merchant,
        "qr_value": qr_merchant,
        "message": ""
    }

    ocr_value = normalize_merchant(ocr_merchant)
    qr_value = normalize_merchant(qr_merchant)

    if not ocr_value and not qr_value:
        result["status"] = "missing"
        result["message"] = "Recipient/merchant name was not found"
        return result

    if not ocr_value:
        result["status"] = "single_source"
        result["message"] = (
            "Merchant name is available only from the QR"
        )
        return result

    if not qr_value:
        result["status"] = "single_source"
        result["message"] = (
            "Merchant name is available only from OCR evidence"
        )
        return result

    if ocr_value == qr_value:
        result["status"] = "match"
        result["message"] = (
            "Merchant name matches"
        )
        return result

    # Allow partial matches for names with extra words
    if (
        ocr_value in qr_value
        or qr_value in ocr_value
    ):
        result["status"] = "match"
        result["message"] = (
            "Merchant names are consistent"
        )
        return result

    result["status"] = "mismatch"
    result["message"] = (
        "Merchant/recipient name differs between OCR and QR"
    )

    return result


# ---------------------------------------------------------
# AMOUNT CROSS-CHECK
# ---------------------------------------------------------

def check_amount(ocr_amount, qr_amount):
    result = {
        "field": "amount",
        "status": "missing",
        "ocr_value": ocr_amount,
        "qr_value": qr_amount,
        "message": ""
    }

    if ocr_amount is None and qr_amount is None:
        result["status"] = "missing"
        result["message"] = "Payment amount was not found"
        return result

    if ocr_amount is None:
        result["status"] = "single_source"
        result["message"] = (
            "Amount is available only from the QR"
        )
        return result

    if qr_amount is None:
        result["status"] = "single_source"
        result["message"] = (
            "Amount is available only from OCR evidence"
        )
        return result

    if amounts_match(ocr_amount, qr_amount):
        result["status"] = "match"
        result["message"] = (
            "Payment amount matches"
        )
        return result

    result["status"] = "mismatch"
    result["message"] = (
        "Payment amount differs between OCR and QR"
    )

    return result


# ---------------------------------------------------------
# PAYMENT METHOD CROSS-CHECK
# ---------------------------------------------------------

def check_payment_method(ocr_method, qr_detected):
    result = {
        "field": "payment_method",
        "status": "missing",
        "ocr_value": ocr_method,
        "qr_value": "UPI" if qr_detected else None,
        "message": ""
    }

    if not ocr_method and not qr_detected:
        result["status"] = "missing"
        result["message"] = (
            "Payment method could not be determined"
        )
        return result

    if qr_detected and not ocr_method:
        result["status"] = "single_source"
        result["message"] = (
            "QR indicates UPI payment"
        )
        return result

    if not qr_detected and ocr_method:
        result["status"] = "single_source"
        result["message"] = (
            "Payment method is available only from OCR"
        )
        return result

    method = normalize_text(ocr_method)

    compatible_methods = {
        "upi",
        "google pay",
        "phonepe",
        "paytm"
    }

    if method in compatible_methods:
        result["status"] = "match"
        result["message"] = (
            "Payment method is compatible with UPI QR"
        )
        return result

    result["status"] = "mismatch"
    result["message"] = (
        "Payment method appears inconsistent with the QR"
    )

    return result


# ---------------------------------------------------------
# EVIDENCE COMPLETENESS
# ---------------------------------------------------------

def calculate_evidence_completeness(payment_details, qr_details):
    important_fields = [
        payment_details.get("amount"),
        payment_details.get("merchant"),
        payment_details.get("upi_id"),
        payment_details.get("payment_method")
    ]

    available_payment_fields = sum(
        value is not None and str(value).strip() != ""
        for value in important_fields
    )

    qr_fields = [
        qr_details.get("upi_id"),
        qr_details.get("merchant"),
        qr_details.get("amount")
    ]

    available_qr_fields = sum(
        value is not None and str(value).strip() != ""
        for value in qr_fields
    )

    # Payment details contribute 60%
    # QR details contribute 40%
    payment_score = (
        available_payment_fields / len(important_fields)
    ) * 60

    qr_score = (
        available_qr_fields / len(qr_fields)
    ) * 40

    score = round(payment_score + qr_score)

    return max(0, min(100, score))


# ---------------------------------------------------------
# CONSISTENCY SCORE
# ---------------------------------------------------------

def calculate_consistency_score(checks):
    comparable_checks = [
        check
        for check in checks
        if check["status"] in [
            "match",
            "mismatch"
        ]
    ]

    if not comparable_checks:
        return 50

    matches = sum(
        check["status"] == "match"
        for check in comparable_checks
    )

    score = (
        matches / len(comparable_checks)
    ) * 100

    return round(score)


# ---------------------------------------------------------
# VERIFICATION CONFIDENCE
# ---------------------------------------------------------

def calculate_verification_confidence(
    evidence_completeness,
    consistency_score,
    qr_valid
):
    confidence = (
        evidence_completeness * 0.45
        + consistency_score * 0.40
        + (100 if qr_valid else 40) * 0.15
    )

    return round(
        max(0, min(100, confidence))
    )


# ---------------------------------------------------------
# MAIN VERIFICATION FUNCTION
# ---------------------------------------------------------

def verify_payment(payment_details, qr_data):
    """
    Performs evidence-based payment verification.

    IMPORTANT:
    This does NOT contact a bank or UPI network.
    It only checks the information available
    in the uploaded payment evidence.
    """

    payment_details = payment_details or {}
    qr_data = qr_data or {}

    qr_payload = qr_data.get("data")

    qr_details = parse_upi_qr(
        qr_payload
    )

    qr_detected = bool(
        qr_data.get("detected")
    )

    qr_is_payment = bool(
        qr_data.get("is_payment_qr")
    )

    # Prefer our own payload validation when data exists
    qr_valid = (
        qr_is_payment
        and qr_details["is_valid"]
    )

    checks = [
        check_upi_id(
            payment_details.get("upi_id"),
            qr_details.get("upi_id")
        ),
        check_merchant(
            payment_details.get("merchant"),
            qr_details.get("merchant")
        ),
        check_amount(
            payment_details.get("amount"),
            qr_details.get("amount")
        ),
        check_payment_method(
            payment_details.get("payment_method"),
            qr_is_payment
        )
    ]

    mismatches = [
        check
        for check in checks
        if check["status"] == "mismatch"
    ]

    matches = [
        check
        for check in checks
        if check["status"] == "match"
    ]

    missing = [
        check
        for check in checks
        if check["status"] == "missing"
    ]

    single_source = [
        check
        for check in checks
        if check["status"] == "single_source"
    ]

    evidence_completeness = (
        calculate_evidence_completeness(
            payment_details,
            qr_details
        )
    )

    consistency_score = (
        calculate_consistency_score(
            checks
        )
    )

    verification_confidence = (
        calculate_verification_confidence(
            evidence_completeness,
            consistency_score,
            qr_valid
        )
    )

    # -----------------------------------------------------
    # VERIFICATION STATUS
    # -----------------------------------------------------

    if mismatches:
        verification_status = "failed"

    elif not qr_detected:
        verification_status = "incomplete"

    elif qr_detected and not qr_is_payment:
        verification_status = "unsupported_qr"

    elif not qr_valid:
        verification_status = "invalid_qr"

    elif missing:
        verification_status = "incomplete"

    elif matches:
        verification_status = "passed"

    else:
        verification_status = "incomplete"

    # -----------------------------------------------------
    # RECOMMENDATION
    # -----------------------------------------------------

    if mismatches:
        recommendation = "DO_NOT_PROCEED"

    elif verification_status in [
        "invalid_qr",
        "unsupported_qr"
    ]:
        recommendation = "DO_NOT_PROCEED"

    elif verification_status == "incomplete":
        recommendation = "VERIFY_BEFORE_PROCEEDING"

    elif verification_status == "passed":
        recommendation = "PROCEED_WITH_NORMAL_CAUTION"

    else:
        recommendation = "VERIFY_BEFORE_PROCEEDING"

    # -----------------------------------------------------
    # HUMAN-READABLE SUMMARY
    # -----------------------------------------------------

    summary = []

    if mismatches:
        for check in mismatches:
            summary.append(
                f"{check['field'].replace('_', ' ').title()}: "
                f"{check['message']}"
            )

    if not qr_detected:
        summary.append(
            "No QR code was detected in the payment evidence."
        )

    elif not qr_is_payment:
        summary.append(
            "A QR code was detected, but it is not a UPI payment QR."
        )

    elif not qr_valid:
        for error in qr_details.get("errors", []):
            summary.append(
                f"QR validation: {error}"
            )

    if not summary:
        summary.append(
            "Available payment evidence is consistent."
        )

    return {
        "verification_status": verification_status,
        "verification_confidence": verification_confidence,
        "evidence_completeness": evidence_completeness,
        "consistency_score": consistency_score,

        "qr_validation": {
            "detected": qr_detected,
            "is_payment_qr": qr_is_payment,
            "is_valid": qr_valid,
            "upi_id": qr_details.get("upi_id"),
            "merchant": qr_details.get("merchant"),
            "amount": qr_details.get("amount"),
            "currency": qr_details.get("currency"),
            "merchant_code": qr_details.get("merchant_code"),
            "mode": qr_details.get("mode"),
            "purpose": qr_details.get("purpose"),
            "errors": qr_details.get("errors", [])
        },

        "checks": checks,

        "mismatches": mismatches,
        "matches": matches,
        "missing": missing,
        "single_source": single_source,

        "summary": summary,

        "recommendation": recommendation,

        "verification_scope": (
            "Evidence-based verification only. "
            "No direct bank or UPI network verification "
            "has been performed."
        )
    }