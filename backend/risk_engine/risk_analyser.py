import re
from urllib.parse import urlparse, parse_qs, unquote


# ============================================================
# QR PAYMENT DETAILS
# ============================================================

def extract_qr_payment_details(qr_data: str):
    """
    Extract useful payment information from a UPI QR string.
    """

    if not qr_data:
        return {
            "upi_id": None,
            "payee_name": None,
            "amount": None
        }

    if not qr_data.lower().startswith("upi://pay"):
        return {
            "upi_id": None,
            "payee_name": None,
            "amount": None
        }

    try:
        parsed = urlparse(qr_data)
        params = parse_qs(parsed.query)

        upi_id = params.get("pa", [None])[0]
        payee_name = params.get("pn", [None])[0]
        amount = params.get("am", [None])[0]

        if payee_name:
            payee_name = unquote(payee_name)

        if amount:
            try:
                amount = float(amount)
            except ValueError:
                amount = None

        return {
            "upi_id": upi_id,
            "payee_name": payee_name,
            "amount": amount
        }

    except Exception:
        return {
            "upi_id": None,
            "payee_name": None,
            "amount": None
        }


# ============================================================
# TEXT SIGNAL DETECTION
# ============================================================

def detect_scam_signals(text: str):

    text = text or ""
    text_lower = text.lower()

    signals = {
        "urgency": [],
        "threats": [],
        "sensitive_information": [],
        "prize_or_lottery": [],
        "payment_pressure": [],
        "suspicious_links": [],
        "verification_requests": []
    }

    # --------------------------------------------------------
    # URGENCY
    # --------------------------------------------------------

    urgency_patterns = [
        "urgent",
        "immediately",
        "right now",
        "act now",
        "hurry",
        "as soon as possible",
        "within minutes",
        "within 10 minutes",
        "within 15 minutes",
        "within 30 minutes",
        "last chance",
        "limited time",
        "do it now",
        "respond immediately",
        "today only",
        "before today",
        "before midnight"
    ]

    for phrase in urgency_patterns:
        if phrase in text_lower:
            signals["urgency"].append(phrase)

    # --------------------------------------------------------
    # THREATS
    # --------------------------------------------------------

    threat_patterns = [
        "account blocked",
        "account suspended",
        "account will be blocked",
        "account will be suspended",
        "bank account blocked",
        "bank account suspended",
        "service will be stopped",
        "service stopped",
        "account disabled",
        "account will be disabled",
        "legal action",
        "police action",
        "police complaint",
        "penalty will be charged",
        "connection will be disconnected",
        "electricity will be disconnected",
        "sim will be blocked",
        "card will be blocked",
        "account will be closed",
        "service will be disconnected",
        "arrest warrant",
        "court action",
        "fine will be charged"
    ]

    for phrase in threat_patterns:
        if phrase in text_lower:
            signals["threats"].append(phrase)

    # --------------------------------------------------------
    # SENSITIVE INFORMATION
    # --------------------------------------------------------

    sensitive_patterns = [
        "otp",
        "one time password",
        "upi pin",
        "pin",
        "cvv",
        "password",
        "passcode",
        "security code",
        "card number",
        "debit card number",
        "credit card number",
        "bank details",
        "banking details",
        "login details",
        "login credentials",
        "account credentials"
    ]

    for phrase in sensitive_patterns:
        if phrase in text_lower:
            signals["sensitive_information"].append(phrase)

    # --------------------------------------------------------
    # PRIZE / LOTTERY
    # --------------------------------------------------------

    prize_patterns = [
        "lottery",
        "prize",
        "winner",
        "won",
        "congratulations",
        "reward",
        "jackpot",
        "lucky draw",
        "claim your prize",
        "cash prize",
        "gift voucher",
        "free gift",
        "cash reward",
        "special reward",
        "you have won",
        "you are a winner"
    ]

    for phrase in prize_patterns:
        if phrase in text_lower:
            signals["prize_or_lottery"].append(phrase)

    # --------------------------------------------------------
    # PAYMENT PRESSURE
    # --------------------------------------------------------

    payment_pressure_patterns = [
        "pay now",
        "send money",
        "transfer now",
        "make payment",
        "payment required",
        "pay immediately",
        "send the money",
        "transfer the money",
        "payment must be made",
        "pay the amount",
        "complete the payment",
        "claim",
        "pay the bill",
        "clear the bill",
        "send payment",
        "transfer payment",
        "make the payment"
    ]

    for phrase in payment_pressure_patterns:
        if phrase in text_lower:
            signals["payment_pressure"].append(phrase)

    # --------------------------------------------------------
    # SUSPICIOUS LINKS
    # --------------------------------------------------------

    urls = re.findall(
        r"https?://[^\s]+",
        text,
        re.IGNORECASE
    )

    short_url_domains = [
        "bit.ly",
        "tinyurl.com",
        "t.co",
        "goo.gl",
        "shorturl.at",
        "cutt.ly",
        "is.gd",
        "rb.gy"
    ]

    suspicious_urls = []

    for url in urls:

        url_lower = url.lower()

        for domain in short_url_domains:

            if domain in url_lower:
                suspicious_urls.append(url)
                break

    if urls and not suspicious_urls:

        signals["suspicious_links"].extend(urls)

    else:

        signals["suspicious_links"].extend(
            suspicious_urls
        )

    # --------------------------------------------------------
    # VERIFICATION REQUESTS
    # --------------------------------------------------------

    verification_patterns = [
        "verify now",
        "verify your account",
        "verify payment",
        "verification required",
        "confirm your account",
        "confirm payment",
        "verify your identity",
        "complete verification",
        "kyc required",
        "update kyc",
        "kyc verification",
        "verify immediately",
        "verify your kyc",
        "confirm your identity",
        "authentication required",
        "complete kyc"
    ]

    for phrase in verification_patterns:

        if phrase in text_lower:

            signals["verification_requests"].append(
                phrase
            )

    return signals


# ============================================================
# SOCIAL ENGINEERING DETECTION
# ============================================================

def detect_social_engineering(
    text: str,
    scam_signals: dict
):

    text = text or ""
    text_lower = text.lower()

    social_signals = {
        "authority_impersonation": [],
        "fear_or_threat": [],
        "time_pressure": [],
        "unexpected_payment": [],
        "reward_bait": [],
        "credential_request": [],
        "suspicious_link": [],
        "combined_patterns": []
    }

    # --------------------------------------------------------
    # AUTHORITY IMPERSONATION
    # --------------------------------------------------------

    authority_patterns = [
        "bank",
        "bank manager",
        "bank officer",
        "rbi",
        "reserve bank",
        "police",
        "cyber police",
        "government",
        "govt",
        "income tax department",
        "income tax",
        "electricity department",
        "electricity board",
        "power department",
        "telecom department",
        "telecom company",
        "mobile operator",
        "sim department",
        "uidai",
        "aadhaar",
        "gst department",
        "customs department",
        "court",
        "court officer",
        "legal department",
        "insurance company",
        "insurance department",
        "loan department",
        "credit card department",
        "customer care",
        "customer support",
        "official department"
    ]

    for phrase in authority_patterns:

        if phrase in text_lower:

            social_signals[
                "authority_impersonation"
            ].append(phrase)

    # --------------------------------------------------------
    # FEAR / THREAT
    # --------------------------------------------------------

    if scam_signals.get("threats"):

        social_signals["fear_or_threat"].extend(
            scam_signals["threats"]
        )

    fear_patterns = [
        "you will be arrested",
        "you may be arrested",
        "warrant issued",
        "legal consequences",
        "criminal case",
        "your account is at risk",
        "your account is in danger",
        "service interruption",
        "avoid disconnection",
        "avoid penalty",
        "avoid arrest"
    ]

    for phrase in fear_patterns:

        if phrase in text_lower:

            if phrase not in social_signals[
                "fear_or_threat"
            ]:

                social_signals[
                    "fear_or_threat"
                ].append(phrase)

    # --------------------------------------------------------
    # TIME PRESSURE
    # --------------------------------------------------------

    if scam_signals.get("urgency"):

        social_signals["time_pressure"].extend(
            scam_signals["urgency"]
        )

    # --------------------------------------------------------
    # UNEXPECTED PAYMENT
    # --------------------------------------------------------

    payment_request_patterns = [
        "pay",
        "payment",
        "send money",
        "transfer money",
        "transfer",
        "pay the bill",
        "clear the bill",
        "make payment",
        "amount due",
        "outstanding amount",
        "pending payment",
        "payment required",
        "payment due",
        "pay immediately"
    ]

    for phrase in payment_request_patterns:

        if phrase in text_lower:

            social_signals[
                "unexpected_payment"
            ].append(phrase)

    # --------------------------------------------------------
    # REWARD BAIT
    # --------------------------------------------------------

    if scam_signals.get("prize_or_lottery"):

        social_signals["reward_bait"].extend(
            scam_signals["prize_or_lottery"]
        )

    # --------------------------------------------------------
    # CREDENTIAL REQUEST
    # --------------------------------------------------------

    if scam_signals.get(
        "sensitive_information"
    ):

        social_signals[
            "credential_request"
        ].extend(
            scam_signals[
                "sensitive_information"
            ]
        )

    # --------------------------------------------------------
    # SUSPICIOUS LINK
    # --------------------------------------------------------

    if scam_signals.get(
        "suspicious_links"
    ):

        social_signals[
            "suspicious_link"
        ].extend(
            scam_signals[
                "suspicious_links"
            ]
        )

    # --------------------------------------------------------
    # BOOLEAN FLAGS
    # --------------------------------------------------------

    has_authority = bool(
        social_signals[
            "authority_impersonation"
        ]
    )

    has_threat = bool(
        social_signals[
            "fear_or_threat"
        ]
    )

    has_urgency = bool(
        social_signals[
            "time_pressure"
        ]
    )

    has_payment = bool(
        social_signals[
            "unexpected_payment"
        ]
    )

    has_reward = bool(
        social_signals[
            "reward_bait"
        ]
    )

    has_credentials = bool(
        social_signals[
            "credential_request"
        ]
    )

    has_link = bool(
        social_signals[
            "suspicious_link"
        ]
    )

    # --------------------------------------------------------
    # COMBINATIONS
    # --------------------------------------------------------

    if has_authority and has_threat:

        social_signals[
            "combined_patterns"
        ].append(
            "Authority impersonation combined "
            "with a threat."
        )

    if (
        has_authority
        and has_urgency
        and has_payment
    ):

        social_signals[
            "combined_patterns"
        ].append(
            "Authority impersonation combined "
            "with urgency and a payment request."
        )

    if (
        has_threat
        and has_urgency
        and has_payment
    ):

        social_signals[
            "combined_patterns"
        ].append(
            "Threat combined with time pressure "
            "and a payment request."
        )

    if has_reward and has_payment:

        social_signals[
            "combined_patterns"
        ].append(
            "Reward or prize bait combined "
            "with a payment request."
        )

    if has_reward and has_credentials:

        social_signals[
            "combined_patterns"
        ].append(
            "Reward or prize bait combined "
            "with a request for sensitive information."
        )

    if (
        scam_signals.get(
            "verification_requests"
        )
        and has_credentials
    ):

        social_signals[
            "combined_patterns"
        ].append(
            "Verification request combined "
            "with a sensitive information request."
        )

    if has_urgency and has_credentials:

        social_signals[
            "combined_patterns"
        ].append(
            "Urgency combined with a sensitive "
            "information request."
        )

    if has_urgency and has_payment and has_link:

        social_signals[
            "combined_patterns"
        ].append(
            "Urgency and payment pressure "
            "combined with a link."
        )

    if has_authority and has_credentials:

        social_signals[
            "combined_patterns"
        ].append(
            "An apparent authority combined with "
            "a sensitive information request."
        )

    return social_signals


# ============================================================
# PAYMENT INTELLIGENCE
# ============================================================

def normalize_name(value):
    """
    Normalize recipient names so that small formatting
    differences do not produce false mismatches.
    """

    if not value:
        return ""

    return re.sub(
        r"[^a-z0-9]",
        "",
        str(value).lower()
    )


def normalize_upi(value):
    """
    Normalize a UPI ID for comparison.
    """

    if not value:
        return ""

    return str(value).strip().lower()


def compare_payment_evidence(
    payment,
    qr_details,
    qr_data
):
    """
    Compare payment information extracted from OCR/text
    against information extracted from the QR code.

    This function does not decide the final risk level.
    It produces evidence and consistency information.
    """

    payment = payment or {}
    qr_details = qr_details or {}

    checks = []

    mismatches = []

    matches = []

    missing_fields = []

    # ========================================================
    # UPI ID
    # ========================================================

    payment_upi = normalize_upi(
        payment.get("upi_id")
    )

    qr_upi = normalize_upi(
        qr_details.get("upi_id")
    )

    if payment_upi and qr_upi:

        if payment_upi == qr_upi:

            checks.append({
                "field": "upi_id",
                "status": "MATCH",
                "payment_value": payment.get("upi_id"),
                "qr_value": qr_details.get("upi_id")
            })

            matches.append(
                "UPI ID matches the QR code."
            )

        else:

            checks.append({
                "field": "upi_id",
                "status": "MISMATCH",
                "payment_value": payment.get("upi_id"),
                "qr_value": qr_details.get("upi_id")
            })

            mismatches.append(
                "UPI ID in the payment information "
                "does not match the UPI ID in the QR code."
            )

    elif qr_upi:

        missing_fields.append(
            "UPI ID was not found in the payment text, "
            "but it was found in the QR code."
        )

        checks.append({
            "field": "upi_id",
            "status": "PARTIAL",
            "payment_value": None,
            "qr_value": qr_details.get("upi_id")
        })

    elif payment_upi:

        missing_fields.append(
            "UPI ID was found in the payment information, "
            "but no UPI payment QR UPI ID was available."
        )

        checks.append({
            "field": "upi_id",
            "status": "PARTIAL",
            "payment_value": payment.get("upi_id"),
            "qr_value": None
        })

    # ========================================================
    # RECIPIENT NAME
    # ========================================================

    payment_merchant = normalize_name(
        payment.get("merchant")
    )

    qr_payee = normalize_name(
        qr_details.get("payee_name")
    )

    if payment_merchant and qr_payee:

        if (
            payment_merchant in qr_payee
            or qr_payee in payment_merchant
        ):

            checks.append({
                "field": "recipient",
                "status": "MATCH",
                "payment_value": payment.get("merchant"),
                "qr_value": qr_details.get("payee_name")
            })

            matches.append(
                "Recipient name is consistent with the QR payee."
            )

        else:

            checks.append({
                "field": "recipient",
                "status": "MISMATCH",
                "payment_value": payment.get("merchant"),
                "qr_value": qr_details.get("payee_name")
            })

            mismatches.append(
                "Recipient name in the payment information "
                "does not match the QR payee name."
            )

    elif qr_payee:

        missing_fields.append(
            "Recipient name was found in the QR code, "
            "but could not be confirmed from the payment text."
        )

        checks.append({
            "field": "recipient",
            "status": "PARTIAL",
            "payment_value": None,
            "qr_value": qr_details.get("payee_name")
        })

    elif payment_merchant:

        checks.append({
            "field": "recipient",
            "status": "TEXT_ONLY",
            "payment_value": payment.get("merchant"),
            "qr_value": None
        })

    # ========================================================
    # AMOUNT
    # ========================================================

    payment_amount = payment.get("amount")
    qr_amount = qr_details.get("amount")

    if (
        payment_amount is not None
        and qr_amount is not None
    ):

        try:

            difference = abs(
                float(payment_amount)
                - float(qr_amount)
            )

            if difference <= 0.01:

                checks.append({
                    "field": "amount",
                    "status": "MATCH",
                    "payment_value": payment_amount,
                    "qr_value": qr_amount
                })

                matches.append(
                    "Payment amount matches the QR amount."
                )

            else:

                checks.append({
                    "field": "amount",
                    "status": "MISMATCH",
                    "payment_value": payment_amount,
                    "qr_value": qr_amount
                })

                mismatches.append(
                    f"Payment amount ₹{payment_amount:g} "
                    f"does not match QR amount "
                    f"₹{qr_amount:g}."
                )

        except (ValueError, TypeError):

            missing_fields.append(
                "Payment amount could not be compared reliably."
            )

    elif payment_amount is not None:

        checks.append({
            "field": "amount",
            "status": "TEXT_ONLY",
            "payment_value": payment_amount,
            "qr_value": None
        })

    elif qr_amount is not None:

        checks.append({
            "field": "amount",
            "status": "QR_ONLY",
            "payment_value": None,
            "qr_value": qr_amount
        })

    else:

        missing_fields.append(
            "Payment amount could not be verified from "
            "the available evidence."
        )

    # ========================================================
    # QR VALIDATION
    # ========================================================

    qr_is_payment = bool(
        qr_data
        and str(qr_data).lower().startswith(
            "upi://pay"
        )
    )

    if qr_data and not qr_is_payment:

        mismatches.append(
            "A QR code was detected, but its payload "
            "is not a valid UPI payment QR."
        )

    # ========================================================
    # EVIDENCE COMPLETENESS
    # ========================================================

    evidence_fields = [
        bool(payment_amount is not None),
        bool(payment.get("merchant")),
        bool(payment.get("upi_id")),
        bool(qr_details.get("upi_id")),
        bool(qr_details.get("payee_name")),
        bool(qr_details.get("amount"))
    ]

    evidence_count = sum(
        evidence_fields
    )

    evidence_total = len(
        evidence_fields
    )

    evidence_completeness = round(
        (
            evidence_count
            / evidence_total
        ) * 100
    )

    # ========================================================
    # CONSISTENCY SCORE
    # ========================================================

    comparable_checks = [
        check
        for check in checks
        if check["status"] in [
            "MATCH",
            "MISMATCH"
        ]
    ]

    if comparable_checks:

        matched_checks = sum(
            1
            for check in comparable_checks
            if check["status"] == "MATCH"
        )

        consistency_score = round(
            (
                matched_checks
                / len(comparable_checks)
            ) * 100
        )

    else:

        consistency_score = 0

    # ========================================================
    # VERIFICATION CONFIDENCE
    # ========================================================

    verification_confidence = round(
        (
            evidence_completeness * 0.4
        )
        +
        (
            consistency_score * 0.6
        )
    )

    return {
        "checks": checks,
        "matches": matches,
        "mismatches": mismatches,
        "missing_fields": missing_fields,
        "evidence_completeness": evidence_completeness,
        "consistency_score": consistency_score,
        "verification_confidence": verification_confidence
    }


# ============================================================
# RISK ANALYSIS
# ============================================================

def analyze_payment_risk(
    payment: dict,
    extracted_text: str = "",
    qr_data: str = None
):

    risk_score = 0
    reasons = []

    text = extracted_text.lower()

    amount = payment.get("amount")
    merchant = payment.get("merchant")
    transaction_id = payment.get("transaction_id")
    utr = payment.get("utr")
    payment_status = payment.get("payment_status")
    payment_upi_id = payment.get("upi_id")

    # ========================================================
    # 1. AMOUNT ANALYSIS
    # ========================================================

    if amount is None:

        risk_score += 5

        reasons.append(
            "Payment amount could not be verified."
        )

    elif amount >= 50000:

        risk_score += 20

        reasons.append(
            "The payment amount is unusually high."
        )

    elif amount >= 10000:

        risk_score += 10

        reasons.append(
            "The payment amount is relatively high."
        )

    # ========================================================
    # 2. MERCHANT / RECIPIENT
    # ========================================================

    if not merchant:

        risk_score += 5

        reasons.append(
            "Recipient or merchant could not be identified."
        )

    # ========================================================
    # 3. TRANSACTION ID
    # ========================================================

    if not transaction_id:

        risk_score += 5

        reasons.append(
            "Transaction ID is missing."
        )

    # ========================================================
    # 4. UTR
    # ========================================================

    if not utr:

        risk_score += 5

        reasons.append(
            "UTR number is missing."
        )

    # ========================================================
    # 5. PAYMENT STATUS
    # ========================================================

    if payment_status == "failed":

        risk_score += 20

        reasons.append(
            "The payment appears to have failed."
        )

    elif payment_status == "unknown":

        risk_score += 5

        reasons.append(
            "Payment status could not be confidently verified."
        )

    elif payment_status == "success":

        reasons.append(
            "Payment status indicates a successful transaction."
        )

    # ========================================================
    # 6. SCAM SIGNALS
    # ========================================================

    scam_signals = detect_scam_signals(
        extracted_text
    )

    # --------------------------------------------------------
    # URGENCY
    # --------------------------------------------------------

    detected_urgency = scam_signals["urgency"]

    if detected_urgency:

        risk_score += min(
            15,
            len(detected_urgency) * 5
        )

        reasons.append(
            "Urgent or pressure-based language detected: "
            + ", ".join(detected_urgency)
        )

    # --------------------------------------------------------
    # THREATS
    # --------------------------------------------------------

    detected_threats = scam_signals["threats"]

    if detected_threats:

        risk_score += min(
            20,
            len(detected_threats) * 10
        )

        reasons.append(
            "Threatening account or service language detected: "
            + ", ".join(detected_threats)
        )

    # --------------------------------------------------------
    # SENSITIVE INFORMATION
    # --------------------------------------------------------

    detected_sensitive = (
        scam_signals["sensitive_information"]
    )

    if detected_sensitive:

        risk_score += min(
            40,
            len(detected_sensitive) * 20
        )

        reasons.append(
            "Sensitive financial information requested: "
            + ", ".join(detected_sensitive)
        )

    # --------------------------------------------------------
    # PRIZE
    # --------------------------------------------------------

    detected_prize_words = (
        scam_signals["prize_or_lottery"]
    )

    if detected_prize_words:

        risk_score += min(
            25,
            len(detected_prize_words) * 8
        )

        reasons.append(
            "Prize or lottery-related language detected: "
            + ", ".join(detected_prize_words)
        )

    # --------------------------------------------------------
    # PAYMENT PRESSURE
    # --------------------------------------------------------

    detected_payment_pressure = (
        scam_signals["payment_pressure"]
    )

    if detected_payment_pressure:

        risk_score += min(
            15,
            len(detected_payment_pressure) * 5
        )

        reasons.append(
            "Payment pressure detected: "
            + ", ".join(detected_payment_pressure)
        )

    # --------------------------------------------------------
    # LINKS
    # --------------------------------------------------------

    detected_links = (
        scam_signals["suspicious_links"]
    )

    if detected_links:

        risk_score += 20

        reasons.append(
            "A potentially suspicious link was detected "
            "in the payment request."
        )

    # --------------------------------------------------------
    # VERIFICATION
    # --------------------------------------------------------

    detected_verification = (
        scam_signals["verification_requests"]
    )

    if detected_verification:

        risk_score += min(
            15,
            len(detected_verification) * 5
        )

        reasons.append(
            "Account or payment verification request detected: "
            + ", ".join(detected_verification)
        )

    # ========================================================
    # 7. SOCIAL ENGINEERING
    # ========================================================

    social_engineering = detect_social_engineering(
        extracted_text,
        scam_signals
    )

    authority_signals = social_engineering[
        "authority_impersonation"
    ]

    if authority_signals:

        risk_score += min(
            10,
            len(authority_signals) * 5
        )

        reasons.append(
            "Possible authority or official-service "
            "impersonation detected: "
            + ", ".join(authority_signals)
        )

    combined_patterns = social_engineering[
        "combined_patterns"
    ]

    if combined_patterns:

        risk_score += min(
            30,
            len(combined_patterns) * 10
        )

        for pattern in combined_patterns:

            reasons.append(
                "Social-engineering pattern detected: "
                + pattern
            )

    # ========================================================
    # 8. PAYMENT INFORMATION COMPLETENESS
    # ========================================================

    complete_information = all([
        amount is not None,
        merchant is not None,
        transaction_id is not None,
        utr is not None
    ])

    if complete_information:

        reasons.append(
            "Amount, recipient, transaction ID and UTR "
            "information are available."
        )

    # ========================================================
    # 9. QR CODE ANALYSIS
    # ========================================================

    qr_payment = extract_qr_payment_details(
        qr_data
    )

    qr_upi_id = qr_payment["upi_id"]
    qr_payee_name = qr_payment["payee_name"]
    qr_amount = qr_payment["amount"]

    if qr_data:

        if qr_data.lower().startswith("upi://pay"):

            reasons.append(
                "A UPI payment QR code was detected and decoded."
            )

        else:

            risk_score += 35

            reasons.append(
                "A QR code was detected, but it does not contain "
                "a valid UPI payment link."
            )

    # ========================================================
    # 10. ADVANCED CROSS-VERIFICATION
    # ========================================================

    payment_intelligence = compare_payment_evidence(
        payment,
        qr_payment,
        qr_data
    )

    # --------------------------------------------------------
    # MISMATCHES
    # --------------------------------------------------------

    mismatches = payment_intelligence[
        "mismatches"
    ]

    for mismatch in mismatches:

        if (
            "UPI ID" in mismatch
            or "Recipient name" in mismatch
            or "amount" in mismatch
        ):

            risk_score += 20

        else:

            risk_score += 10

        reasons.append(
            "Cross-verification: "
            + mismatch
        )

    # --------------------------------------------------------
    # MATCHES
    # --------------------------------------------------------

    matches = payment_intelligence[
        "matches"
    ]

    for match in matches:

        reasons.append(
            "Cross-verification: "
            + match
        )

    # --------------------------------------------------------
    # EVIDENCE COMPLETENESS
    # --------------------------------------------------------

    evidence_completeness = payment_intelligence[
        "evidence_completeness"
    ]

    verification_confidence = payment_intelligence[
        "verification_confidence"
    ]

    if evidence_completeness >= 80:

        reasons.append(
            f"Payment evidence completeness is "
            f"{evidence_completeness}%."
        )

    elif evidence_completeness < 40:

        reasons.append(
            f"Only {evidence_completeness}% of the "
            "expected payment evidence is available."
        )

    # ========================================================
    # 11. QR ↔ PAYMENT CROSS-VERIFICATION
    # ========================================================

    # Kept as an explicit section for compatibility with
    # the previous CivicPay logic.

    if qr_data and qr_data.lower().startswith(
        "upi://pay"
    ):

        if payment_upi_id and qr_upi_id:

            if payment_upi_id.lower() != qr_upi_id.lower():

                # Avoid adding the same mismatch score twice.
                if not any(
                    "UPI ID" in mismatch
                    for mismatch in mismatches
                ):

                    risk_score += 20

        if merchant and qr_payee_name:

            merchant_clean = normalize_name(
                merchant
            )

            payee_clean = normalize_name(
                qr_payee_name
            )

            if (
                merchant_clean
                and payee_clean
                and merchant_clean not in payee_clean
                and payee_clean not in merchant_clean
            ):

                if not any(
                    "Recipient name" in mismatch
                    for mismatch in mismatches
                ):

                    risk_score += 20

        if (
            amount is not None
            and qr_amount is not None
        ):

            try:

                if abs(
                    float(amount)
                    - float(qr_amount)
                ) > 0.01:

                    if not any(
                        "amount" in mismatch
                        for mismatch in mismatches
                    ):

                        risk_score += 25

            except (
                ValueError,
                TypeError
            ):

                pass

    # ========================================================
    # 12. CRITICAL SCAM COMBINATION
    # ========================================================

    critical_information_request = any(
        word in text
        for word in [
            "otp",
            "one time password",
            "upi pin",
            "cvv",
            "password",
            "passcode"
        ]
    )

    scam_context = any(
        word in text
        for word in [
            "urgent",
            "immediately",
            "pay now",
            "send money",
            "prize",
            "lottery",
            "winner",
            "won",
            "claim",
            "account blocked",
            "account suspended",
            "verify now"
        ]
    )

    if (
        critical_information_request
        and scam_context
    ):

        risk_score = max(
            risk_score,
            75
        )

        reasons.append(
            "Critical scam indicators detected involving "
            "sensitive financial information."
        )

    # ========================================================
    # 13. SOCIAL ENGINEERING HIGH-RISK OVERRIDE
    # ========================================================

    social_signal_categories = 0

    if social_engineering[
        "authority_impersonation"
    ]:
        social_signal_categories += 1

    if social_engineering[
        "fear_or_threat"
    ]:
        social_signal_categories += 1

    if social_engineering[
        "time_pressure"
    ]:
        social_signal_categories += 1

    if social_engineering[
        "unexpected_payment"
    ]:
        social_signal_categories += 1

    if social_engineering[
        "reward_bait"
    ]:
        social_signal_categories += 1

    if social_engineering[
        "credential_request"
    ]:
        social_signal_categories += 1

    if social_engineering[
        "suspicious_link"
    ]:
        social_signal_categories += 1

    if social_signal_categories >= 4:

        risk_score = max(
            risk_score,
            70
        )

        reasons.append(
            "Multiple social-engineering tactics were detected "
            "in the same payment request."
        )

    # ========================================================
    # 14. SCAM SIGNAL SUMMARY
    # ========================================================

    signal_count = sum(
        len(values)
        for values in scam_signals.values()
    )

    if signal_count >= 3:

        reasons.append(
            f"Multiple suspicious language signals were detected "
            f"({signal_count} signal matches)."
        )

    # ========================================================
    # 15. LIMIT SCORE
    # ========================================================

    risk_score = min(
        risk_score,
        100
    )

    # ========================================================
    # 16. RISK LEVEL
    # ========================================================

    if risk_score >= 60:

        risk_level = "HIGH"

    elif risk_score >= 30:

        risk_level = "MEDIUM"

    else:

        risk_level = "LOW"

    # ========================================================
    # 17. RECOMMENDATION
    # ========================================================

    if risk_level == "HIGH":

        recommendation = (
            "Do not proceed. Independently verify the "
            "recipient and payment request before taking any action."
        )

    elif risk_level == "MEDIUM":

        recommendation = (
            "Proceed with caution. Verify the recipient, "
            "payment amount and request through an independent source."
        )

    else:

        recommendation = (
            "Payment appears relatively safe based on the "
            "available information. Still verify the recipient "
            "before proceeding."
        )

    # ========================================================
    # 18. RETURN RESULT
    # ========================================================

    return {
        "risk_score": risk_score,

        "risk_level": risk_level,

        "reasons": reasons,

        "recommendation": recommendation,

        "scam_signals": scam_signals,

        "signal_count": signal_count,

        "social_engineering": social_engineering,

        "social_signal_categories": social_signal_categories,

        "payment_intelligence": payment_intelligence,

        "qr_details": {
            "upi_id": qr_upi_id,
            "payee_name": qr_payee_name,
            "amount": qr_amount
        }
    }