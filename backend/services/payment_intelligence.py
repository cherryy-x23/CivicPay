import re


# ============================================================
# PHASE 5.3 — ADVANCED PAYMENT INTELLIGENCE
# ============================================================


def build_payment_intelligence(
    payment: dict,
    extracted_text: str = "",
    qr_data: str = None,
    scam_signals: dict = None,
    qr_details: dict = None,
):
    """
    Build a structured intelligence profile from the payment evidence.

    This layer does not claim bank-side verification and does not by
    itself decide that a payment is a scam. It summarizes evidence
    quality, payment context, behavioral signals and cross-source
    consistency for the AI investigation layer.
    """

    payment = payment or {}
    scam_signals = scam_signals or {}
    qr_details = qr_details or {}

    amount = payment.get("amount")
    merchant = payment.get("merchant")
    upi_id = payment.get("upi_id")
    transaction_id = payment.get("transaction_id")
    utr = payment.get("utr")
    payment_status = payment.get("payment_status")
    payment_method = payment.get("payment_method")

    qr_upi_id = qr_details.get("upi_id")
    qr_payee_name = qr_details.get("payee_name")
    qr_amount = qr_details.get("amount")

    # ============================================================
    # 1. EVIDENCE QUALITY
    # ============================================================

    evidence_fields = [
        amount is not None,
        bool(merchant),
        bool(upi_id),
        bool(payment_method),
        bool(transaction_id),
        bool(utr),
    ]

    available_fields = sum(evidence_fields)

    evidence_completeness = round(
        (available_fields / len(evidence_fields)) * 100
    )

    if evidence_completeness >= 80:
        evidence_quality = "HIGH"

    elif evidence_completeness >= 50:
        evidence_quality = "MEDIUM"

    else:
        evidence_quality = "LOW"

    # ============================================================
    # 2. AMOUNT PROFILE
    # ============================================================

    if amount is None:

        amount_profile = "NOT_PROVIDED"

    else:

        try:

            numeric_amount = float(amount)

            if numeric_amount <= 0:

                amount_profile = "INVALID"

            elif numeric_amount < 500:

                amount_profile = "LOW"

            elif numeric_amount < 10000:

                amount_profile = "MODERATE"

            elif numeric_amount < 50000:

                amount_profile = "HIGH"

            else:

                amount_profile = "VERY_HIGH"

        except (TypeError, ValueError):

            amount_profile = "INVALID"

    # ============================================================
    # 3. RECIPIENT PROFILE
    # ============================================================

    if merchant and upi_id:

        recipient_profile = "IDENTIFIED_WITH_UPI"

    elif merchant or upi_id:

        recipient_profile = "PARTIALLY_IDENTIFIED"

    else:

        recipient_profile = "UNIDENTIFIED"

    # ============================================================
    # 4. QR PROFILE
    # ============================================================

    if not qr_data:

        qr_profile = "NOT_DETECTED"

    elif not qr_data.lower().startswith("upi://pay"):

        qr_profile = "NON_UPI_QR"

    elif qr_upi_id:

        qr_profile = "VALID_UPI_QR"

    else:

        qr_profile = "INCOMPLETE_UPI_QR"

    # ============================================================
    # 5. CROSS-SOURCE CONSISTENCY
    # ============================================================

    consistency_checks = []

    # ------------------------------------------------------------
    # UPI ID
    # ------------------------------------------------------------

    if upi_id and qr_upi_id:

        consistency_checks.append(
            upi_id.strip().lower()
            ==
            qr_upi_id.strip().lower()
        )

    # ------------------------------------------------------------
    # MERCHANT / PAYEE
    # ------------------------------------------------------------

    if merchant and qr_payee_name:

        merchant_clean = re.sub(
            r"[^a-z0-9]",
            "",
            merchant.lower()
        )

        payee_clean = re.sub(
            r"[^a-z0-9]",
            "",
            qr_payee_name.lower()
        )

        if merchant_clean and payee_clean:

            consistency_checks.append(
                merchant_clean in payee_clean
                or
                payee_clean in merchant_clean
            )

    # ------------------------------------------------------------
    # AMOUNT
    # ------------------------------------------------------------

    if amount is not None and qr_amount is not None:

        try:

            consistency_checks.append(
                abs(
                    float(amount)
                    -
                    float(qr_amount)
                )
                <= 0.01
            )

        except (TypeError, ValueError):

            consistency_checks.append(False)

    # ------------------------------------------------------------
    # CONSISTENCY RESULT
    # ------------------------------------------------------------

    if consistency_checks:

        if all(consistency_checks):

            cross_source_consistency = "CONSISTENT"

        elif not any(consistency_checks):

            cross_source_consistency = "CONFLICTING"

        else:

            cross_source_consistency = "MIXED"

    elif qr_data:

        cross_source_consistency = "SINGLE_SOURCE"

    else:

        cross_source_consistency = "NOT_AVAILABLE"

    # ============================================================
    # 6. BEHAVIORAL PROFILE
    # ============================================================

    signal_categories = {

        "urgency": len(
            scam_signals.get(
                "urgency",
                []
            )
        ),

        "threats": len(
            scam_signals.get(
                "threats",
                []
            )
        ),

        "sensitive_information": len(
            scam_signals.get(
                "sensitive_information",
                []
            )
        ),

        "prize_or_lottery": len(
            scam_signals.get(
                "prize_or_lottery",
                []
            )
        ),

        "payment_pressure": len(
            scam_signals.get(
                "payment_pressure",
                []
            )
        ),

        "suspicious_links": len(
            scam_signals.get(
                "suspicious_links",
                []
            )
        ),

        "verification_requests": len(
            scam_signals.get(
                "verification_requests",
                []
            )
        ),
    }

    active_signal_categories = [

        category

        for category, count
        in signal_categories.items()

        if count > 0
    ]

    # ------------------------------------------------------------
    # BEHAVIOR CLASSIFICATION
    # ------------------------------------------------------------

    if signal_categories[
        "sensitive_information"
    ] > 0:

        behavior_profile = (
            "SENSITIVE_INFORMATION_REQUEST"
        )

    elif (
        signal_categories["threats"] > 0
        and
        signal_categories["urgency"] > 0
    ):

        behavior_profile = (
            "THREAT_AND_URGENCY"
        )

    elif signal_categories[
        "prize_or_lottery"
    ] > 0:

        behavior_profile = (
            "REWARD_OR_PRIZE_PATTERN"
        )

    elif (
        signal_categories["payment_pressure"] > 0
        or
        signal_categories["urgency"] > 0
    ):

        behavior_profile = (
            "PAYMENT_PRESSURE"
        )

    elif signal_categories[
        "suspicious_links"
    ] > 0:

        behavior_profile = (
            "LINK_DRIVEN_REQUEST"
        )

    else:

        behavior_profile = (
            "NO_STRONG_BEHAVIORAL_SIGNAL"
        )

    # ============================================================
    # 7. INTELLIGENCE FLAGS
    # ============================================================

    flags = []

    if amount is None:

        flags.append(
            "Payment amount is not available for verification."
        )

    if not merchant:

        flags.append(
            "Recipient or merchant could not be identified."
        )

    if not upi_id and qr_upi_id is None:

        flags.append(
            "No UPI destination was available from the evidence."
        )

    if amount_profile in {
        "HIGH",
        "VERY_HIGH"
    }:

        flags.append(
            "The requested amount is relatively high."
        )

    if amount_profile == "INVALID":

        flags.append(
            "The extracted payment amount is invalid or non-positive."
        )

    if qr_profile == "NON_UPI_QR":

        flags.append(
            "The detected QR does not appear to be a UPI payment QR."
        )

    elif qr_profile == "INCOMPLETE_UPI_QR":

        flags.append(
            "The UPI QR does not contain enough destination information."
        )

    if cross_source_consistency == "CONFLICTING":

        flags.append(
            "Payment evidence contains conflicting values across sources."
        )

    elif cross_source_consistency == "MIXED":

        flags.append(
            "Some payment evidence matches while other fields require review."
        )

    if active_signal_categories:

        flags.append(
            "Behavioral signals detected: "
            +
            ", ".join(active_signal_categories)
            +
            "."
        )

    if payment_status == "failed":

        flags.append(
            "The extracted payment status indicates failure."
        )

    elif payment_status == "unknown":

        flags.append(
            "Payment status could not be confidently established."
        )

    # ============================================================
    # 8. OVERALL INTELLIGENCE ASSESSMENT
    # ============================================================

    concern_points = 0

    # Missing amount is important evidence uncertainty.
    if amount is None:

        concern_points += 1

    if evidence_quality == "LOW":

        concern_points += 1

    if amount_profile in {
        "HIGH",
        "VERY_HIGH",
        "INVALID"
    }:

        concern_points += 1

    if recipient_profile == "UNIDENTIFIED":

        concern_points += 1

    if qr_profile in {
        "NON_UPI_QR",
        "INCOMPLETE_UPI_QR"
    }:

        concern_points += 2

    if cross_source_consistency in {
        "CONFLICTING",
        "MIXED"
    }:

        concern_points += 2

    concern_points += min(
        3,
        len(active_signal_categories)
    )

    if concern_points >= 5:

        assessment = "HIGH_CONCERN"

    elif concern_points >= 1:

        assessment = "REQUIRES_REVIEW"

    else:

        assessment = (
            "CONSISTENT_WITH_AVAILABLE_EVIDENCE"
        )

    # ============================================================
    # 9. INTELLIGENCE CONFIDENCE
    # ============================================================

    # This describes evidence quality.
    # It is NOT bank or UPI confirmation.

    intelligence_confidence = min(
        100,
        max(
            0,
            evidence_completeness
            +
            (
                10
                if qr_profile == "VALID_UPI_QR"
                else 0
            )
            +
            (
                10
                if cross_source_consistency == "CONSISTENT"
                else 0
            )
            -
            (
                15
                if cross_source_consistency == "CONFLICTING"
                else 0
            )
        )
    )

    # ============================================================
    # FINAL INTELLIGENCE OBJECT
    # ============================================================

    return {

        "assessment": assessment,

        "confidence": intelligence_confidence,

        "evidence_quality": evidence_quality,

        "evidence_completeness": evidence_completeness,

        "amount_profile": amount_profile,

        "recipient_profile": recipient_profile,

        "qr_profile": qr_profile,

        "cross_source_consistency":
            cross_source_consistency,

        "behavior_profile":
            behavior_profile,

        "signal_categories":
            signal_categories,

        "active_signal_categories":
            active_signal_categories,

        "flags":
            flags,

        "scope": (
            "Evidence-based payment intelligence. "
            "It does not confirm bank, wallet or "
            "UPI network status."
        ),
    }