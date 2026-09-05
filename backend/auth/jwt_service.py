import os
from datetime import datetime, timedelta, timezone

import jwt


# ============================================================
# CIVICPAY JWT CONFIGURATION
# ============================================================

JWT_ALGORITHM = "HS256"

JWT_EXPIRATION_MINUTES = 60


# ============================================================
# GET JWT SECRET
# ============================================================

def get_jwt_secret() -> str:
    """
    Get the JWT signing secret from the environment.

    The secret must not be hard-coded into the source code.
    """

    secret = os.getenv(
        "CIVICPAY_JWT_SECRET"
    )

    if not secret:

        raise RuntimeError(
            "CIVICPAY_JWT_SECRET environment variable "
            "is not configured."
        )

    if len(secret) < 32:

        raise RuntimeError(
            "CIVICPAY_JWT_SECRET must contain at least "
            "32 characters."
        )

    return secret


# ============================================================
# CREATE ACCESS TOKEN
# ============================================================

def create_access_token(
    user_id: int,
    username: str
) -> str:
    """
    Create a signed JWT access token for a CivicPay user.
    """

    now = datetime.now(
        timezone.utc
    )

    expiration = (
        now
        +
        timedelta(
            minutes=JWT_EXPIRATION_MINUTES
        )
    )

    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": now,
        "exp": expiration,
        "type": "access"
    }

    token = jwt.encode(
        payload,
        get_jwt_secret(),
        algorithm=JWT_ALGORITHM
    )

    return token


# ============================================================
# DECODE ACCESS TOKEN
# ============================================================

def decode_access_token(
    token: str
) -> dict:
    """
    Decode and validate a CivicPay JWT.

    This function will be used in Phase 6.2.5
    to protect authenticated endpoints.
    """

    if not token:

        raise ValueError(
            "Access token is missing."
        )

    try:

        payload = jwt.decode(
            token,
            get_jwt_secret(),
            algorithms=[JWT_ALGORITHM]
        )

    except jwt.ExpiredSignatureError:

        raise ValueError(
            "Access token has expired."
        )

    except jwt.InvalidTokenError:

        raise ValueError(
            "Invalid access token."
        )

    # --------------------------------------------------------
    # Validate required claims
    # --------------------------------------------------------

    if payload.get("type") != "access":

        raise ValueError(
            "Invalid access token type."
        )

    if not payload.get("sub"):

        raise ValueError(
            "Access token does not contain a user ID."
        )

    return payload