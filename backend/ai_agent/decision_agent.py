import os
import json
import re

from huggingface_hub import InferenceClient


# ============================================================
# HUGGING FACE CONFIGURATION
# ============================================================

HF_TOKEN = os.getenv("HF_TOKEN")

MODEL = "meta-llama/Llama-3.1-8B-Instruct"

client = InferenceClient(
    token=HF_TOKEN
)


# ============================================================
# JSON EXTRACTION
# ============================================================

def extract_json(text):
    """
    Extract JSON even if the AI returns:
    ```json
    {...}
    ```
    """

    if not text:
        return None

    text = text.strip()

    # Remove markdown code fences
    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\s*```$",
        "",
        text
    )

    text = text.strip()

    # Direct JSON
    try:
        return json.loads(text)
    except Exception:
        pass

    # Try to find JSON object inside response
    match = re.search(
        r"\{.*\}",
        text,
        re.DOTALL
    )

    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    return None


# ============================================================
# AI ANALYSIS
# ============================================================

def ask_ai(
    payment,
    qr_analysis,
    risk_analysis,
    verification
):
    """
    Ask the language model to explain the payment
    using CivicPay's deterministic evidence.

    The AI is explanatory only.
    It cannot override CivicPay's security decision.
    """

    if not HF_TOKEN:
        return None

    risk_score = risk_analysis.get(
        "risk_score",
        0
    )

    risk_level = risk_analysis.get(
        "risk_level",
        "UNKNOWN"
    )

    verification_status = verification.get(
        "verification_status",
        "unknown"
    )

    verification_confidence = verification.get(
        "verification_confidence",
        0
    )

    evidence_completeness = verification.get(
        "evidence_completeness",
        0
    )

    consistency_score = verification.get(
        "consistency_score",
        0
    )

    prompt = f"""
You are CivicPay AI, a payment security investigation agent.

Your job is to analyze payment evidence and explain the
security situation clearly to the user.

IMPORTANT SECURITY RULES:

1. CivicPay's deterministic risk engine is authoritative.
2. CivicPay's verification result is authoritative for
   evidence consistency.
3. NEVER reduce or override a HIGH risk level.
4. NEVER invent missing payment information.
5. NEVER claim that a bank or UPI network was contacted.
6. Evidence-based verification is NOT the same as bank verification.
7. If payment evidence conflicts, clearly explain the conflict.
8. If important information is missing, clearly say it is missing.
9. Do not call something a scam unless the evidence explicitly proves it.
10. If verification status is failed, recommend NOT proceeding.
11. If verification status is incomplete, recommend verification.
12. If verification status is passed, explain that the available
    evidence is consistent, but do not claim bank-level verification.

CURRENT CIVICPAY RISK:

Risk Level: {risk_level}
Risk Score: {risk_score}

PHASE 5.1 VERIFICATION:

Verification Status: {verification_status}
Verification Confidence: {verification_confidence}%
Evidence Completeness: {evidence_completeness}%
Consistency Score: {consistency_score}%

PAYMENT INFORMATION:

{json.dumps(payment, indent=2)}

QR ANALYSIS:

{json.dumps(qr_analysis, indent=2)}

VERIFICATION INTELLIGENCE:

{json.dumps(verification, indent=2)}

RISK ENGINE FINDINGS:

{json.dumps(risk_analysis, indent=2)}

Analyze the evidence using these five stages:

DETECT:
What payment-related information was detected?

INVESTIGATE:
What evidence was examined?

EXPLAIN:
Why does the current risk and verification status exist?

VERIFY:
What should the user independently verify?

RECOMMEND:
What is the safest next action?

Return ONLY valid JSON.

Use exactly this structure:

{{
    "detected": [
        "short finding"
    ],
    "investigation": [
        "short finding"
    ],
    "explanation": "short explanation",
    "verification_steps": [
        "step 1",
        "step 2"
    ],
    "recommendation": "short recommendation"
}}

Keep the language simple and easy to understand.
"""

    try:

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a careful financial security "
                        "assistant. You must only use the evidence "
                        "provided by CivicPay."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=600,
            temperature=0.1
        )

        raw_response = response.choices[0].message.content

        return extract_json(
            raw_response
        )

    except Exception as e:

        print(
            "AI model error:",
            e
        )

        return None


# ============================================================
# FALLBACK ANALYSIS
# ============================================================

def create_fallback_analysis(
    payment,
    qr_analysis,
    risk_analysis,
    verification
):

    risk_level = risk_analysis.get(
        "risk_level",
        "UNKNOWN"
    )

    risk_score = risk_analysis.get(
        "risk_score",
        0
    )

    verification_status = verification.get(
        "verification_status",
        "unknown"
    )

    detected = []

    if qr_analysis.get("detected"):
        detected.append(
            "QR code detected."
        )

    if qr_analysis.get("is_payment_qr"):
        detected.append(
            "UPI payment QR detected."
        )

    if payment.get("payment_method"):
        detected.append(
            f"{payment.get('payment_method')} payment information detected."
        )

    if payment.get("amount") is not None:
        detected.append(
            f"Payment amount detected: ₹{payment.get('amount')}"
        )

    if payment.get("merchant"):
        detected.append(
            f"Recipient detected: {payment.get('merchant')}"
        )

    if payment.get("upi_id"):
        detected.append(
            f"UPI ID detected: {payment.get('upi_id')}"
        )

    # --------------------------------------------------------
    # INVESTIGATION
    # --------------------------------------------------------

    investigation = []

    for reason in risk_analysis.get(
        "reasons",
        []
    ):

        if reason not in investigation:
            investigation.append(
                reason
            )

    for item in verification.get(
        "summary",
        []
    ):

        if item not in investigation:
            investigation.append(
                item
            )

    if not investigation:
        investigation.append(
            "Available payment information was examined."
        )

    # --------------------------------------------------------
    # VERIFICATION-AWARE EXPLANATION
    # --------------------------------------------------------

    if verification_status == "failed":

        explanation = (
            "The payment contains conflicting information. "
            "Important payment evidence does not match."
        )

        verification_steps = [
            "Do not make the payment.",
            "Verify the recipient using an independent source.",
            "Check the UPI ID and payment amount carefully."
        ]

        recommendation = (
            "Do not proceed until the conflicting payment "
            "information has been independently verified."
        )

    elif verification_status in (
        "invalid_qr",
        "unsupported_qr"
    ):

        explanation = (
            "A QR code was detected, but it could not be "
            "verified as a valid UPI payment QR."
        )

        verification_steps = [
            "Do not rely on the QR code alone.",
            "Verify the recipient independently.",
            "Confirm the payment details before proceeding."
        ]

        recommendation = (
            "Do not proceed until the payment request "
            "has been independently verified."
        )

    elif verification_status == "incomplete":

        explanation = (
            f"The payment has a {risk_level} risk score of "
            f"{risk_score}. The available evidence is "
            "partially consistent, but important information "
            "is still missing."
        )

        verification_steps = [
            "Verify the recipient independently.",
            "Confirm the payment amount.",
            "Check the payment details before proceeding."
        ]

        recommendation = (
            "Verify the missing payment information "
            "before proceeding."
        )

    elif verification_status == "passed":

        explanation = (
            "The available payment evidence is consistent. "
            "The UPI information and recipient details "
            "match the QR evidence."
        )

        verification_steps = [
            "Confirm the recipient before paying.",
            "Check the amount carefully in your payment app.",
            "Never share your UPI PIN or OTP."
        ]

        recommendation = (
            "The available evidence is consistent. "
            "Proceed only after checking the payment details."
        )

    elif risk_level == "HIGH":

        explanation = (
            f"The payment has a HIGH risk score of "
            f"{risk_score}. Important security concerns "
            "were detected."
        )

        verification_steps = [
            "Do not make the payment yet.",
            "Verify the recipient independently.",
            "Do not enter your UPI PIN."
        ]

        recommendation = (
            "Do not proceed until the payment request "
            "has been independently verified."
        )

    elif risk_level == "MEDIUM":

        explanation = (
            f"The payment has a MEDIUM risk score of "
            f"{risk_score}. Some information needs "
            "additional verification."
        )

        verification_steps = [
            "Verify the recipient.",
            "Confirm the payment amount.",
            "Check the payment details."
        ]

        recommendation = (
            "Verify the payment details before proceeding."
        )

    else:

        explanation = (
            f"The payment has a LOW risk score of "
            f"{risk_score} based on the available evidence."
        )

        verification_steps = [
            "Confirm the recipient.",
            "Check the payment amount.",
            "Review the payment details."
        ]

        recommendation = (
            "The available evidence looks consistent, "
            "but verify the payment details before completing it."
        )

    return {
        "detected": detected,
        "investigation": investigation,
        "explanation": explanation,
        "verification_steps": verification_steps,
        "recommendation": recommendation
    }


# ============================================================
# VERIFICATION DECISION
# ============================================================

def build_verification_decision(
    risk_level,
    verification
):
    """
    Combines deterministic risk and Phase 5.1 verification.

    This does NOT perform real bank verification.
    It only evaluates the evidence available to CivicPay.
    """

    verification_status = verification.get(
        "verification_status",
        "unknown"
    )

    confidence = verification.get(
        "verification_confidence",
        0
    )

    consistency = verification.get(
        "consistency_score",
        0
    )

    completeness = verification.get(
        "evidence_completeness",
        0
    )

    mismatches = verification.get(
        "mismatches",
        []
    )

    # --------------------------------------------------------
    # CRITICAL CONFLICT
    # --------------------------------------------------------

    if verification_status == "failed" or mismatches:

        return {
            "final_safety_status": "DO_NOT_PROCEED",
            "verification_decision": "FAILED_VERIFICATION",
            "verification_reason": (
                "Conflicting payment evidence was detected."
            ),
            "verification_confidence": confidence
        }

    # --------------------------------------------------------
    # INVALID / UNSUPPORTED QR
    # --------------------------------------------------------

    if verification_status in (
        "invalid_qr",
        "unsupported_qr"
    ):

        return {
            "final_safety_status": "DO_NOT_PROCEED",
            "verification_decision": "QR_NOT_VERIFIABLE",
            "verification_reason": (
                "The detected QR code could not be verified "
                "as a valid UPI payment QR."
            ),
            "verification_confidence": confidence
        }

    # --------------------------------------------------------
    # HIGH RISK ALWAYS WINS
    # --------------------------------------------------------

    if risk_level == "HIGH":

        return {
            "final_safety_status": "DO_NOT_PROCEED",
            "verification_decision": "HIGH_RISK",
            "verification_reason": (
                "The risk engine identified a high-risk payment."
            ),
            "verification_confidence": confidence
        }

    # --------------------------------------------------------
    # INCOMPLETE EVIDENCE
    # --------------------------------------------------------

    if verification_status == "incomplete":

        return {
            "final_safety_status": "VERIFY_BEFORE_PROCEEDING",
            "verification_decision": "INCOMPLETE_VERIFICATION",
            "verification_reason": (
                "Important payment information is still missing."
            ),
            "verification_confidence": confidence
        }

    # --------------------------------------------------------
    # MEDIUM RISK
    # --------------------------------------------------------

    if risk_level == "MEDIUM":

        return {
            "final_safety_status": "VERIFY_BEFORE_PROCEEDING",
            "verification_decision": "MEDIUM_RISK",
            "verification_reason": (
                "The payment requires additional verification."
            ),
            "verification_confidence": confidence
        }

    # --------------------------------------------------------
    # PASSED VERIFICATION
    # --------------------------------------------------------

    if (
        verification_status == "passed"
        and consistency >= 90
        and confidence >= 80
    ):

        return {
            "final_safety_status": "VERIFIED_WITH_EVIDENCE",
            "verification_decision": "VERIFIED",
            "verification_reason": (
                "Available payment evidence is consistent "
                "across the verification sources."
            ),
            "verification_confidence": confidence
        }

    # --------------------------------------------------------
    # DEFAULT
    # --------------------------------------------------------

    return {
        "final_safety_status": "VERIFY_BEFORE_PROCEEDING",
        "verification_decision": "ADDITIONAL_VERIFICATION",
        "verification_reason": (
            "The available evidence is not sufficient "
            "for a stronger verification result."
        ),
        "verification_confidence": confidence
    }


# ============================================================
# MAIN DECISION AGENT
# ============================================================

def create_decision(
    payment,
    qr_analysis,
    risk_analysis,
    extracted_text="",
    verification=None
):

    if verification is None:
        verification = {}

    risk_score = risk_analysis.get(
        "risk_score",
        0
    )

    risk_level = risk_analysis.get(
        "risk_level",
        "UNKNOWN"
    )

    reasons = risk_analysis.get(
        "reasons",
        []
    )

    # --------------------------------------------------------
    # DETECT
    # --------------------------------------------------------

    detected = []

    if qr_analysis.get("detected"):

        detected.append(
            "QR code detected."
        )

    if qr_analysis.get("is_payment_qr"):

        detected.append(
            "UPI payment QR detected."
        )

    payment_method = payment.get(
        "payment_method"
    )

    if payment_method:

        detected.append(
            f"{payment_method} payment information detected."
        )

    if payment.get("amount") is not None:

        detected.append(
            f"Payment amount detected: ₹{payment.get('amount')}"
        )

    if payment.get("merchant"):

        detected.append(
            f"Recipient detected: {payment.get('merchant')}"
        )

    if payment.get("upi_id"):

        detected.append(
            f"UPI ID detected: {payment.get('upi_id')}"
        )

    # --------------------------------------------------------
    # PHASE 5.1 VERIFICATION
    # --------------------------------------------------------

    verification_result = build_verification_decision(
        risk_level,
        verification
    )

    final_safety_status = verification_result[
        "final_safety_status"
    ]

    verification_decision = verification_result[
        "verification_decision"
    ]

    verification_reason = verification_result[
        "verification_reason"
    ]

    # --------------------------------------------------------
    # INVESTIGATION
    # --------------------------------------------------------

    investigation = []

    for reason in reasons:

        if reason not in investigation:

            investigation.append(
                reason
            )

    for item in verification.get(
        "summary",
        []
    ):

        if item not in investigation:

            investigation.append(
                item
            )

    if verification_reason not in investigation:

        investigation.append(
            verification_reason
        )

    if not investigation:

        investigation.append(
            "Available payment information was examined."
        )

    # --------------------------------------------------------
    # DETERMINISTIC FINAL DECISION
    # --------------------------------------------------------

    if final_safety_status == "DO_NOT_PROCEED":

        decision = "DO_NOT_PROCEED"

    elif final_safety_status == "VERIFY_BEFORE_PROCEEDING":

        decision = "VERIFY_BEFORE_PROCEEDING"

    else:

        # Keep the existing Phase 3 decision format
        # so the current frontend continues to work.

        decision = "LOW_RISK_BUT_VERIFY"

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    if final_safety_status == "DO_NOT_PROCEED":

        summary = (
            "Do not proceed. CivicPay detected a security "
            "problem or could not safely verify the payment."
        )

    elif final_safety_status == "VERIFIED_WITH_EVIDENCE":

        summary = (
            "Payment evidence is consistent. CivicPay found "
            "no major conflict between the available sources."
        )

    elif risk_level == "MEDIUM":

        summary = (
            "This payment requires additional verification "
            "before proceeding."
        )

    else:

        summary = (
            "The available payment information is relatively "
            "consistent, but some details should still be checked."
        )

    # --------------------------------------------------------
    # RECOMMENDED ACTIONS
    # --------------------------------------------------------

    if final_safety_status == "DO_NOT_PROCEED":

        recommended_actions = [
            "Do not make the payment yet.",
            "Verify the recipient through an independent source.",
            "Do not share OTP, UPI PIN, CVV or passwords."
        ]

    elif final_safety_status == "VERIFIED_WITH_EVIDENCE":

        recommended_actions = [
            "Confirm the recipient name before paying.",
            "Check the amount carefully.",
            "Never share your UPI PIN or OTP."
        ]

    elif risk_level == "MEDIUM":

        recommended_actions = [
            "Verify the recipient before paying.",
            "Confirm the payment amount.",
            "Avoid sharing sensitive financial information."
        ]

    else:

        recommended_actions = [
            "Verify the recipient before completing the payment.",
            "Check the amount and payment details carefully."
        ]

    # --------------------------------------------------------
    # CONFIDENCE
    # --------------------------------------------------------

    verification_confidence = verification.get(
        "verification_confidence",
        0
    )

    confidence = max(
        30,
        min(
            100,
            int(
                (
                    verification_confidence * 0.7
                )
                +
                (
                    30 if risk_level != "UNKNOWN" else 0
                )
            )
        )
    )

    # --------------------------------------------------------
    # ASK REAL AI
    # --------------------------------------------------------

    ai_analysis = ask_ai(
        payment,
        qr_analysis,
        risk_analysis,
        verification
    )

    # --------------------------------------------------------
    # FALLBACK IF AI FAILS
    # --------------------------------------------------------

    if not ai_analysis:

        ai_analysis = create_fallback_analysis(
            payment,
            qr_analysis,
            risk_analysis,
            verification
        )

    # --------------------------------------------------------
    # SECURITY OVERRIDE PROTECTION
    # --------------------------------------------------------

    # The AI can explain the result,
    # but cannot change CivicPay's deterministic decision.

    if final_safety_status == "DO_NOT_PROCEED":

        ai_analysis["recommendation"] = (
            "Do not proceed until the payment request "
            "has been independently verified."
        )

    elif final_safety_status == "VERIFY_BEFORE_PROCEEDING":

        ai_analysis["recommendation"] = (
            "Verify the recipient and payment details "
            "before proceeding."
        )

    elif final_safety_status == "VERIFIED_WITH_EVIDENCE":

        ai_analysis["recommendation"] = (
            "The available payment evidence is consistent. "
            "Check the final payment details before completing it."
        )

    # --------------------------------------------------------
    # FINAL RESULT
    # --------------------------------------------------------

    return {

        "decision": decision,

        "risk_level": risk_level,

        "risk_score": risk_score,

        "confidence": confidence,

        "summary": summary,

        "ai_explanation": ai_analysis.get(
            "explanation",
            summary
        ),

        "detected": detected,

        "findings": investigation,

        "recommended_actions": recommended_actions,

        # ====================================================
        # PHASE 5.2 SMART VERIFICATION
        # ====================================================

        "final_safety_status": final_safety_status,

        "verification_decision": verification_decision,

        "verification_reason": verification_reason,

        "verification_confidence": verification_confidence,

        "verification_status": verification.get(
            "verification_status",
            "unknown"
        ),

        "evidence_completeness": verification.get(
            "evidence_completeness",
            0
        ),

        "consistency_score": verification.get(
            "consistency_score",
            0
        ),

        # ====================================================
        # AI ANALYSIS
        # ====================================================

        "ai_analysis": {

            "detected": ai_analysis.get(
                "detected",
                detected
            ),

            "investigation": ai_analysis.get(
                "investigation",
                investigation
            ),

            "explanation": ai_analysis.get(
                "explanation",
                summary
            ),

            "verification_steps": ai_analysis.get(
                "verification_steps",
                recommended_actions
            ),

            "recommendation": ai_analysis.get(
                "recommendation",
                recommended_actions[0]
            )
        }
    }