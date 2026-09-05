from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
from ai_agent.decision_agent import create_decision
from auth.dependencies import get_current_user

from services.ocr_service import extract_text
from services.qr_service import extract_qr_data
from services.verification_service import verify_payment
from services.payment_intelligence import build_payment_intelligence

from payment_parser import extract_payment_details
from risk_engine.risk_analyser import analyze_payment_risk

from auth.database import (
    initialize_database,
    create_user,
    get_user_by_email,
    get_user_by_username,
    create_analysis_record,
    get_analysis_history_by_user
)

from auth.auth_service import (
    hash_password,
    verify_password
)

from auth.jwt_service import (
    create_access_token
)

import os
import uuid
import re
import tempfile

from urllib.parse import urlparse, parse_qs, unquote

from PIL import Image, UnidentifiedImageError  # type: ignore[import-not-found]

load_dotenv()
# ============================================================
# CIVICPAY API
# ============================================================

app = FastAPI(
    title="CivicPay API",
    description="AI-powered payment security and verification system",
    version="1.0.0"
)


# ============================================================
# INITIALIZE DATABASE
# ============================================================

initialize_database()


# ============================================================
# CORS
# ============================================================

CIVICPAY_FRONTEND_URL = os.getenv(
    "CIVICPAY_FRONTEND_URL",
    "http://localhost:5173"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        CIVICPAY_FRONTEND_URL,
        "http://localhost:5173",
        "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# ============================================================
# SECURITY CONFIGURATION
# ============================================================

MAX_FILE_SIZE = 10 * 1024 * 1024

MAX_OCR_TEXT_LENGTH = 20000

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/bmp"
}

ALLOWED_IMAGE_FORMATS = {
    "JPEG",
    "PNG",
    "WEBP",
    "BMP"
}


# ============================================================
# AUTHENTICATION CONFIGURATION
# ============================================================

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128

MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 30

MAX_EMAIL_LENGTH = 254


# ============================================================
# ANALYSIS HISTORY CONFIGURATION
# ============================================================

MAX_HISTORY_ITEMS = 100


# ============================================================
# REQUEST MODELS
# ============================================================

class RegisterRequest(BaseModel):
    """
    Data required when creating a CivicPay account.
    """

    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    """
    Data required when logging into CivicPay.
    """

    email: str
    password: str


# ============================================================
# VALIDATION HELPERS
# ============================================================

def validate_username(
    username: str
) -> str:
    """
    Validate and normalize a CivicPay username.
    """

    if not isinstance(
        username,
        str
    ):
        raise HTTPException(
            status_code=422,
            detail="Username must be a string."
        )

    username = username.strip()

    if len(username) < MIN_USERNAME_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Username must contain at least "
                f"{MIN_USERNAME_LENGTH} characters."
            )
        )

    if len(username) > MAX_USERNAME_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Username must not exceed "
                f"{MAX_USERNAME_LENGTH} characters."
            )
        )

    if not re.fullmatch(
        r"[A-Za-z0-9_-]+",
        username
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "Username can contain only letters, "
                "numbers, underscores and hyphens."
            )
        )

    return username


def validate_email(
    email: str
) -> str:
    """
    Validate and normalize an email address.
    """

    if not isinstance(
        email,
        str
    ):
        raise HTTPException(
            status_code=422,
            detail="Email must be a string."
        )

    email = email.strip().lower()

    if not email:
        raise HTTPException(
            status_code=422,
            detail="Email is required."
        )

    if len(email) > MAX_EMAIL_LENGTH:
        raise HTTPException(
            status_code=422,
            detail="Email address is too long."
        )

    if not re.fullmatch(
        r"[^@\s]+@[^@\s]+\.[^@\s]+",
        email
    ):
        raise HTTPException(
            status_code=422,
            detail="Please provide a valid email address."
        )

    return email


def validate_password(
    password: str
) -> str:
    """
    Validate a user's password.
    """

    if not isinstance(
        password,
        str
    ):
        raise HTTPException(
            status_code=422,
            detail="Password must be a string."
        )

    if len(password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Password must contain at least "
                f"{MIN_PASSWORD_LENGTH} characters."
            )
        )

    if len(password) > MAX_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Password must not exceed "
                f"{MAX_PASSWORD_LENGTH} characters."
            )
        )

    return password


# ============================================================
# PHASE 6.3.4
# PRIVACY-SAFE API RESPONSE HELPERS
# ============================================================

def build_privacy_safe_payment(
    payment_details: dict
) -> dict:
    """
    Create the payment section that is safe to expose
    through the API.

    IMPORTANT PRIVACY RULE:

    Sensitive recipient/payment identity information is
    intentionally NOT returned to the client.

    The following internal fields are removed:

        - upi_id
        - merchant
        - transaction_id
        - utr
        - raw payment evidence
        - source evidence

    These values may still be used internally by the
    verification and risk-analysis engines.
    """

    if not isinstance(
        payment_details,
        dict
    ):
        return {}

    safe_payment = {}

    # --------------------------------------------------------
    # ONLY NON-SENSITIVE PAYMENT METADATA
    # --------------------------------------------------------

    allowed_keys = {
        "amount",
        "payment_method",
        "currency",
        "transaction_type"
    }

    for key in allowed_keys:

        if key in payment_details:

            safe_payment[key] = payment_details[key]

    return safe_payment


def build_privacy_safe_qr(
    qr_data: dict
) -> dict:
    """
    Create a privacy-safe QR response.

    The raw QR payload can contain:

        - UPI ID
        - merchant name
        - amount
        - transaction information
        - arbitrary URLs

    Therefore the raw `data` field is never returned.
    """

    if not isinstance(
        qr_data,
        dict
    ):
        return {
            "detected": False,
            "is_payment_qr": False
        }

    safe_qr = {}

    safe_qr["detected"] = bool(
        qr_data.get(
            "detected",
            False
        )
    )

    safe_qr["is_payment_qr"] = bool(
        qr_data.get(
            "is_payment_qr",
            False
        )
    )

    # --------------------------------------------------------
    # Preserve only non-sensitive QR metadata.
    # --------------------------------------------------------

    allowed_keys = {
        "format",
        "type",
        "count"
    }

    for key in allowed_keys:

        if key in qr_data:

            safe_qr[key] = qr_data[key]

    return safe_qr


def build_privacy_safe_verification(
    verification: dict
) -> dict:
    """
    Return only verification information required by
    the frontend.

    Raw evidence and internal details are excluded.
    """

    if not isinstance(
        verification,
        dict
    ):
        return {}

    safe_verification = {}

    allowed_keys = {
        "verification_status",
        "verification_confidence",
        "evidence_completeness",
        "consistency_score",
        "recommendation",
        "summary",
        "status",
        "confidence",
        "evidence_quality"
    }

    for key in allowed_keys:

        if key in verification:

            safe_verification[key] = verification[key]

    return safe_verification


def build_privacy_safe_risk(
    risk_analysis: dict
) -> dict:
    """
    Return a privacy-safe risk analysis.

    Raw QR payloads, OCR content and internal evidence
    are excluded.
    """

    if not isinstance(
        risk_analysis,
        dict
    ):
        return {}

    safe_risk = {}

    # --------------------------------------------------------
    # Basic risk information
    # --------------------------------------------------------

    allowed_basic_keys = {
        "risk_level",
        "risk_score",
        "confidence",
        "recommendation",
        "summary",
        "scam_signals",
        "flags",
        "signal_categories",
        "active_signal_categories",
        "amount_profile",
        "recipient_profile",
        "cross_source_consistency",
        "behavior_profile",
        "payment_intelligence"
    }

    for key in allowed_basic_keys:

        if key not in risk_analysis:
            continue

        value = risk_analysis[key]

        # ----------------------------------------------------
        # Payment intelligence contains nested data.
        # Only approved safe fields are exposed.
        # ----------------------------------------------------

        if key == "payment_intelligence":

            if isinstance(
                value,
                dict
            ):

                safe_intelligence = {}

                intelligence_keys = {
                    "assessment",
                    "confidence",
                    "evidence_quality",
                    "evidence_completeness",
                    "amount_profile",
                    "recipient_profile",
                    "qr_profile",
                    "cross_source_consistency",
                    "behavior_profile",
                    "signal_categories",
                    "active_signal_categories",
                    "flags",
                    "scope"
                }

                for intelligence_key in intelligence_keys:

                    if intelligence_key in value:

                        safe_intelligence[
                            intelligence_key
                        ] = value[
                            intelligence_key
                        ]

                safe_risk[
                    "payment_intelligence"
                ] = safe_intelligence

            continue

        # ----------------------------------------------------
        # Scam signals may contain raw source data.
        # ----------------------------------------------------

        if key == "scam_signals":

            if isinstance(
                value,
                dict
            ):

                safe_signals = {}

                for signal_key, signal_value in value.items():

                    # ----------------------------------------
                    # Never expose raw OCR or QR content.
                    # ----------------------------------------

                    if signal_key.lower() in {
                        "data",
                        "raw_data",
                        "qr_payload",
                        "payload",
                        "extracted_text",
                        "ocr_text",
                        "upi_id",
                        "merchant",
                        "transaction_id",
                        "utr"
                    }:
                        continue

                    safe_signals[
                        signal_key
                    ] = signal_value

                safe_risk[
                    "scam_signals"
                ] = safe_signals

            else:

                safe_risk[
                    "scam_signals"
                ] = value

            continue

        safe_risk[key] = value

    return safe_risk


def build_privacy_safe_ai_decision(
    ai_decision: dict
) -> dict:
    """
    Return only user-facing AI decision information.

    Internal model/debug information is excluded.
    """

    if not isinstance(
        ai_decision,
        dict
    ):
        return {}

    safe_decision = {}

    allowed_keys = {
        "decision",
        "risk_level",
        "confidence",
        "reason",
        "explanation",
        "recommendation",
        "summary",
        "action",
        "status"
    }

    for key in allowed_keys:

        if key in ai_decision:

            safe_decision[key] = ai_decision[key]

    return safe_decision


def build_privacy_safe_response(
    payment_details: dict,
    qr_data: dict,
    verification: dict,
    risk_analysis: dict,
    ai_decision: dict,
    analysis_id: str
) -> dict:
    """
    Construct the final API response for /analyze.

    IMPORTANT:

    This function intentionally does NOT return:

        - original uploaded filename
        - raw OCR text
        - raw QR payload
        - UPI ID
        - merchant/payment recipient
        - transaction ID
        - UTR
        - source evidence
        - internal debugging information

    The internal analysis still uses all required data.
    Only the API response is filtered.
    """

    return {

        "message":
            "Payment analyzed successfully!",

        "analysis_id":
            analysis_id,

        "payment":
            build_privacy_safe_payment(
                payment_details
            ),

        "qr_analysis":
            build_privacy_safe_qr(
                qr_data
            ),

        "verification":
            build_privacy_safe_verification(
                verification
            ),

        "risk_analysis":
            build_privacy_safe_risk(
                risk_analysis
            ),

        "ai_decision":
            build_privacy_safe_ai_decision(
                ai_decision
            )
    }


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/")
def home():

    return {
        "message": "CivicPay backend is running!",
        "status": "success"
    }


# ============================================================
# PHASE 6.2.3
# USER REGISTRATION
# ============================================================

@app.post("/auth/register")
def register_user(
    request: RegisterRequest
):
    """
    Register a new CivicPay user.
    """

    username = validate_username(
        request.username
    )

    email = validate_email(
        request.email
    )

    password = validate_password(
        request.password
    )

    # --------------------------------------------------------
    # Check username
    # --------------------------------------------------------

    existing_username = get_user_by_username(
        username
    )

    if existing_username:

        raise HTTPException(
            status_code=409,
            detail="Username is already registered."
        )

    # --------------------------------------------------------
    # Check email
    # --------------------------------------------------------

    existing_email = get_user_by_email(
        email
    )

    if existing_email:

        raise HTTPException(
            status_code=409,
            detail="Email is already registered."
        )

    # --------------------------------------------------------
    # Hash password
    # --------------------------------------------------------

    try:

        password_hash = hash_password(
            password
        )

    except Exception:

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to securely process the password."
            )
        )

    # --------------------------------------------------------
    # Create user
    # --------------------------------------------------------

    user = create_user(
        username=username,
        email=email,
        password_hash=password_hash
    )

    if user is None:

        raise HTTPException(
            status_code=409,
            detail=(
                "Username or email is already registered."
            )
        )

    # --------------------------------------------------------
    # PRIVACY-SAFE LOG
    # --------------------------------------------------------

    print(
        "CivicPay account created successfully."
    )

    return {

        "message":
            "Account created successfully.",

        "user": {

            "id":
                user["id"],

            "username":
                user["username"],

            "email":
                user["email"]
        }
    }


# ============================================================
# PHASE 6.2.4
# USER LOGIN
# ============================================================

@app.post("/auth/login")
def login_user(
    request: LoginRequest
):
    """
    Authenticate a CivicPay user and return a JWT access token.
    """

    # --------------------------------------------------------
    # Validate email
    # --------------------------------------------------------

    email = validate_email(
        request.email
    )

    # --------------------------------------------------------
    # Validate password
    # --------------------------------------------------------

    password = validate_password(
        request.password
    )

    # --------------------------------------------------------
    # Find user
    # --------------------------------------------------------

    user = get_user_by_email(
        email
    )

    # --------------------------------------------------------
    # Do not reveal whether the email exists.
    # --------------------------------------------------------

    if not user:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    # --------------------------------------------------------
    # Verify Argon2 password
    # --------------------------------------------------------

    password_is_valid = verify_password(
        password,
        user["password_hash"]
    )

    if not password_is_valid:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password."
        )

    # --------------------------------------------------------
    # Create JWT
    # --------------------------------------------------------

    try:

        access_token = create_access_token(
            user_id=user["id"],
            username=user["username"]
        )

    except RuntimeError:

        raise HTTPException(
            status_code=500,
            detail=(
                "Authentication service is not configured."
            )
        )

    except Exception:

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to create authentication session."
            )
        )

    # --------------------------------------------------------
    # PRIVACY-SAFE LOG
    # --------------------------------------------------------

    print(
        "CivicPay user authentication successful."
    )

    return {

        "message":
            "Login successful.",

        "access_token":
            access_token,

        "token_type":
            "bearer",

        "expires_in":
            60 * 60,

        "user": {

            "id":
                user["id"],

            "username":
                user["username"],

            "email":
                user["email"]
        }
    }


# ============================================================
# PHASE 6.4.1
# SECURE ANALYSIS HISTORY
# ============================================================

@app.get("/analysis-history")
def get_analysis_history(
    current_user: dict = Depends(get_current_user)
):
    """
    Return the authenticated user's privacy-safe analysis history.

    SECURITY:

    The user ID is obtained from the validated JWT.

    The client cannot provide a user ID to retrieve another
    user's history.
    """

    # --------------------------------------------------------
    # Extract authenticated user ID from JWT.
    # --------------------------------------------------------

    try:

        user_id = int(
            current_user.get("sub")
        )

    except (
        TypeError,
        ValueError
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid authenticated user."
        )

    # --------------------------------------------------------
    # Retrieve ONLY this user's records.
    # --------------------------------------------------------

    try:

        history = get_analysis_history_by_user(
            user_id=user_id,
            limit=MAX_HISTORY_ITEMS
        )

    except Exception:

        # Do not expose database internals.
        raise HTTPException(
            status_code=500,
            detail=(
                "CivicPay could not retrieve your "
                "analysis history."
            )
        )

    # --------------------------------------------------------
    # Privacy-safe response.
    # --------------------------------------------------------

    return {
        "message": "Analysis history retrieved successfully.",
        "count": len(history),
        "history": history
    }


# ============================================================
# SECURE UPLOAD VALIDATION
# ============================================================

async def read_and_validate_image(
    file: UploadFile
):
    """
    Securely read and validate an uploaded payment image.
    """

    # --------------------------------------------------------
    # Filename validation
    # --------------------------------------------------------

    if not file.filename:

        raise HTTPException(
            status_code=400,
            detail="No filename was provided."
        )

    # --------------------------------------------------------
    # MIME type validation
    # --------------------------------------------------------

    if file.content_type not in ALLOWED_CONTENT_TYPES:

        raise HTTPException(
            status_code=415,
            detail=(
                "Unsupported file type. "
                "Please upload a JPG, PNG, WEBP, or BMP image."
            )
        )

    # --------------------------------------------------------
    # Read file
    # --------------------------------------------------------

    try:

        contents = await file.read()

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="The uploaded file could not be read."
        )

    # --------------------------------------------------------
    # Empty file check
    # --------------------------------------------------------

    if not contents:

        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty."
        )

    # --------------------------------------------------------
    # File size check
    # --------------------------------------------------------

    if len(contents) > MAX_FILE_SIZE:

        raise HTTPException(
            status_code=413,
            detail=(
                "The uploaded file is too large. "
                "Maximum allowed size is 10 MB."
            )
        )

    # --------------------------------------------------------
    # Actual image validation
    # --------------------------------------------------------

    try:

        from io import BytesIO

        image = Image.open(
            BytesIO(contents)
        )

        image.verify()

        actual_format = image.format

    except UnidentifiedImageError:

        raise HTTPException(
            status_code=400,
            detail=(
                "The uploaded file is not a valid image "
                "or the image is corrupted."
            )
        )

    except Exception:

        raise HTTPException(
            status_code=400,
            detail=(
                "The uploaded image could not be validated."
            )
        )

    # --------------------------------------------------------
    # Actual format validation
    # --------------------------------------------------------

    if actual_format not in ALLOWED_IMAGE_FORMATS:

        raise HTTPException(
            status_code=415,
            detail="This image format is not supported."
        )

    await file.seek(0)

    return contents


# ============================================================
# /ANALYZE
# ============================================================

@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):

    temporary_file_path: Optional[str] = None

    # --------------------------------------------------------
    # Generate a short internal analysis ID.
    # --------------------------------------------------------

    analysis_id = uuid.uuid4().hex[:12]

    # ========================================================
    # PHASE 6.3.3
    # AUTHENTICATED USER IDENTIFICATION
    # ========================================================

    try:

        user_id = int(
            current_user.get("sub")
        )

    except (
        TypeError,
        ValueError
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid authenticated user."
        )

    try:

        # ====================================================
        # PHASE 6.1
        # SECURE FILE VALIDATION
        # ====================================================

        contents = await read_and_validate_image(
            file
        )

        print(
            f"[{analysis_id}] "
            f"Secure image validation completed."
        )

        # ====================================================
        # PHASE 6.3.2
        # SECURE TEMPORARY FILE
        # ====================================================

        try:

            temporary_file = tempfile.NamedTemporaryFile(
                mode="wb",
                prefix="civicpay_",
                suffix=".tmp",
                delete=False
            )

            temporary_file_path = (
                temporary_file.name
            )

            temporary_file.write(
                contents
            )

            temporary_file.close()

        except Exception:

            raise HTTPException(
                status_code=500,
                detail=(
                    "CivicPay could not securely prepare "
                    "the uploaded image for analysis."
                )
            )

        print(
            f"[{analysis_id}] "
            f"Temporary analysis file created."
        )

        # ====================================================
        # OCR
        # ====================================================

        extracted_text = extract_text(
            temporary_file_path
        )

        if extracted_text is None:

            extracted_text = ""

        extracted_text = str(
            extracted_text
        )

        if len(extracted_text) > MAX_OCR_TEXT_LENGTH:

            extracted_text = extracted_text[
                :MAX_OCR_TEXT_LENGTH
            ]

        print(
            f"[{analysis_id}] "
            f"OCR processing completed."
        )

        # ====================================================
        # PAYMENT INFORMATION EXTRACTION
        # ====================================================

        payment_details = extract_payment_details(
            extracted_text,
            file.filename
        )

        if not isinstance(
            payment_details,
            dict
        ):

            payment_details = {}

        # ====================================================
        # SOURCE EVIDENCE
        # ====================================================

        payment_details["source_evidence"] = {

            "ocr": {

                "upi_id":
                    payment_details.get(
                        "upi_id"
                    ),

                "merchant":
                    payment_details.get(
                        "merchant"
                    ),

                "amount":
                    payment_details.get(
                        "amount"
                    ),

                "payment_method":
                    payment_details.get(
                        "payment_method"
                    )
            }
        }

        # ====================================================
        # QR ANALYSIS
        # ====================================================

        qr_data = extract_qr_data(
            temporary_file_path
        )

        if not isinstance(
            qr_data,
            dict
        ):

            qr_data = {
                "detected": False,
                "data": None
            }

        if qr_data.get("detected"):

            print(
                f"[{analysis_id}] "
                f"QR code detected."
            )

        else:

            print(
                f"[{analysis_id}] "
                f"No QR code detected."
            )

        # ====================================================
        # UPI QR PARSING
        # ====================================================

        if (
            qr_data.get("detected")
            and
            qr_data.get("is_payment_qr")
            and
            qr_data.get("data")
        ):

            qr_payload = qr_data["data"]

            try:

                parsed_url = urlparse(
                    str(qr_payload)
                )

                qr_parameters = parse_qs(
                    parsed_url.query
                )

                # --------------------------------------------
                # UPI ID
                # --------------------------------------------

                if qr_parameters.get("pa"):

                    qr_upi_id = unquote(
                        qr_parameters["pa"][0]
                    ).strip()

                    if not payment_details.get(
                        "upi_id"
                    ):

                        payment_details[
                            "upi_id"
                        ] = qr_upi_id

                # --------------------------------------------
                # MERCHANT
                # --------------------------------------------

                if qr_parameters.get("pn"):

                    qr_merchant = unquote(
                        qr_parameters["pn"][0]
                    ).strip()

                    if not payment_details.get(
                        "merchant"
                    ):

                        payment_details[
                            "merchant"
                        ] = qr_merchant

                # --------------------------------------------
                # AMOUNT
                # --------------------------------------------

                if qr_parameters.get("am"):

                    try:

                        qr_amount = float(
                            qr_parameters["am"][0]
                        )

                        if payment_details.get(
                            "amount"
                        ) is None:

                            payment_details[
                                "amount"
                            ] = qr_amount

                    except (
                        ValueError,
                        TypeError
                    ):

                        pass

                # --------------------------------------------
                # PAYMENT METHOD
                # --------------------------------------------

                if not payment_details.get(
                    "payment_method"
                ):

                    payment_details[
                        "payment_method"
                    ] = "UPI"

                # --------------------------------------------
                # PRIVACY-SAFE LOG
                # --------------------------------------------

                print(
                    f"[{analysis_id}] "
                    f"UPI payment QR parsing completed."
                )

            except Exception:

                print(
                    f"[{analysis_id}] "
                    f"UPI QR parsing could not be completed."
                )

        # ====================================================
        # PHASE 5.1
        # VERIFICATION INTELLIGENCE
        # ====================================================

        verification = verify_payment(
            payment_details,
            qr_data
        )

        if not isinstance(
            verification,
            dict
        ):

            verification = {}

        print(
            f"[{analysis_id}] "
            f"Verification intelligence generated."
        )

        # ====================================================
        # EXISTING RISK ENGINE
        # ====================================================

        risk_analysis = analyze_payment_risk(
            payment_details,
            extracted_text,
            qr_data.get("data")
        )

        if not isinstance(
            risk_analysis,
            dict
        ):

            risk_analysis = {}

        print(
            f"[{analysis_id}] "
            f"Risk analysis completed."
        )

        # ====================================================
        # PHASE 5.3
        # ADVANCED PAYMENT INTELLIGENCE
        # ====================================================

        payment_intelligence = (
            build_payment_intelligence(

                payment=payment_details,

                extracted_text=extracted_text,

                qr_data=qr_data.get(
                    "data"
                ),

                scam_signals=
                    risk_analysis.get(
                        "scam_signals",
                        {}
                    ),

                qr_details=
                    risk_analysis.get(
                        "qr_details",
                        {}
                    ),
            )
        )

        if not isinstance(
            payment_intelligence,
            dict
        ):

            payment_intelligence = {}

        risk_analysis[
            "payment_intelligence"
        ] = payment_intelligence

        print(
            f"[{analysis_id}] "
            f"Advanced payment intelligence generated."
        )

        # ====================================================
        # AI DECISION AGENT
        # ====================================================

        ai_decision = create_decision(
            payment_details,
            qr_data,
            risk_analysis,
            extracted_text
        )

        print(
            f"[{analysis_id}] "
            f"AI decision generated."
        )

        # ====================================================
        # PHASE 6.3.3
        # USER-SPECIFIC ANALYSIS RECORD
        # ====================================================

        risk_level = str(
            risk_analysis.get(
                "risk_level",
                "UNKNOWN"
            )
        )

        risk_score_value = risk_analysis.get(
            "risk_score",
            0
        )

        try:

            risk_score_value = float(
                risk_score_value
            )

        except (
            TypeError,
            ValueError
        ):

            risk_score_value = 0.0

        verification_status = str(
            verification.get(
                "verification_status",
                "incomplete"
            )
        )

        verification_confidence_value = verification.get(
            "verification_confidence",
            0
        )

        try:

            verification_confidence_value = float(
                verification_confidence_value
            )

        except (
            TypeError,
            ValueError
        ):

            verification_confidence_value = 0.0

        ai_decision_value = ""

        if isinstance(
            ai_decision,
            dict
        ):

            ai_decision_value = str(
                ai_decision.get(
                    "decision",
                    ""
                )
            )

        try:

            analysis_record = create_analysis_record(

                user_id=user_id,

                analysis_id=analysis_id,

                original_filename="",

                risk_level=risk_level,

                risk_score=risk_score_value,

                verification_status=verification_status,

                verification_confidence=
                    verification_confidence_value,

                ai_decision=ai_decision_value
            )

        except Exception:

            analysis_record = None

        if analysis_record is None:

            print(
                f"[{analysis_id}] "
                f"Analysis result could not be saved."
            )

        else:

            print(
                f"[{analysis_id}] "
                f"User-specific analysis record saved."
            )

        # ====================================================
        # PHASE 6.3.4
        # PRIVACY-SAFE API RESPONSE
        # ====================================================

        safe_response = build_privacy_safe_response(

            payment_details=
                payment_details,

            qr_data=
                qr_data,

            verification=
                verification,

            risk_analysis=
                risk_analysis,

            ai_decision=
                ai_decision,

            analysis_id=
                analysis_id
        )

        print(
            f"[{analysis_id}] "
            f"Privacy-safe API response generated."
        )

        # ====================================================
        # ANALYSIS COMPLETE
        # ====================================================

        print(
            f"[{analysis_id}] "
            f"Payment analysis completed successfully."
        )

        return safe_response

    except HTTPException:

        raise

    except Exception:

        # ----------------------------------------------------
        # Do not expose internal exception details.
        # ----------------------------------------------------

        print(
            f"[{analysis_id}] "
            f"CivicPay analysis failed."
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "CivicPay could not complete the analysis. "
                "Please try another valid payment image."
            )
        )

    finally:

        # ====================================================
        # PHASE 6.3.2
        # SECURE TEMPORARY FILE CLEANUP
        # ====================================================

        if temporary_file_path:

            try:

                if os.path.exists(
                    temporary_file_path
                ):

                    os.remove(
                        temporary_file_path
                    )

                    print(
                        f"[{analysis_id}] "
                        f"Temporary analysis file removed."
                    )

            except Exception:

                # Do not expose filesystem details.
                print(
                    f"[{analysis_id}] "
                    f"Temporary analysis file cleanup "
                    f"could not be completed."
                )