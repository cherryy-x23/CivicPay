from risk_engine.risk_analyser import analyze_payment_risk


# =====================================================
# CASE 1 — SAFE PAYMENT
# =====================================================

safe_payment = {
    "amount": 500,
    "merchant": "Mummy",
    "transaction_id": "72608260637291599377839",
    "utr": "117806874890",
    "payment_status": "success"
}

safe_text = """
Payment successful
Received from Mummy
₹500
Transaction ID available
UTR available
"""


# =====================================================
# CASE 2 — SUSPICIOUS PAYMENT
# =====================================================

suspicious_payment = {
    "amount": 12000,
    "merchant": None,
    "transaction_id": None,
    "utr": None,
    "payment_status": "unknown"
}

suspicious_text = """
URGENT! Your account will be blocked.
Pay ₹12,000 immediately.
Click here to verify.
"""


# =====================================================
# CASE 3 — HIGHLY SUSPICIOUS PAYMENT
# =====================================================

high_risk_payment = {
    "amount": 50000,
    "merchant": None,
    "transaction_id": None,
    "utr": None,
    "payment_status": "unknown"
}

high_risk_text = """
Congratulations! You won ₹5,00,000.
Pay ₹50,000 immediately to claim your prize.
Send your OTP and PIN.
"""


# =====================================================
# RUN TESTS
# =====================================================

print("\n========================================")
print("CASE 1 — SAFE PAYMENT")
print("========================================")

result = analyze_payment_risk(
    safe_payment,
    safe_text
)

print("Risk Score:", result["risk_score"])
print("Risk Level:", result["risk_level"])
print("Reasons:")

for reason in result["reasons"]:
    print("-", reason)

print("Recommendation:", result["recommendation"])


print("\n========================================")
print("CASE 2 — SUSPICIOUS PAYMENT")
print("========================================")

result = analyze_payment_risk(
    suspicious_payment,
    suspicious_text
)

print("Risk Score:", result["risk_score"])
print("Risk Level:", result["risk_level"])
print("Reasons:")

for reason in result["reasons"]:
    print("-", reason)

print("Recommendation:", result["recommendation"])


print("\n========================================")
print("CASE 3 — HIGHLY SUSPICIOUS PAYMENT")
print("========================================")

result = analyze_payment_risk(
    high_risk_payment,
    high_risk_text
)

print("Risk Score:", result["risk_score"])
print("Risk Level:", result["risk_level"])
print("Reasons:")

for reason in result["reasons"]:
    print("-", reason)

print("Recommendation:", result["recommendation"])