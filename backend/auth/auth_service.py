from argon2 import PasswordHasher
from argon2.exceptions import (
    VerifyMismatchError,
    VerificationError,
    InvalidHashError
)


# ============================================================
# CIVICPAY PASSWORD SECURITY
# ============================================================

# Argon2 password hasher.
#
# PasswordHasher automatically handles:
# - password hashing
# - salt generation
# - password verification
# - secure Argon2 parameters
#
# The generated hash contains the information required
# for verification, so we do not need to store the salt
# separately.

password_hasher = PasswordHasher()


# ============================================================
# HASH PASSWORD
# ============================================================

def hash_password(password: str) -> str:
    """
    Convert a plain-text password into a secure Argon2 hash.

    The plain-text password should NEVER be stored in the
    database.
    """

    if not isinstance(password, str):

        raise ValueError(
            "Password must be a string."
        )

    if not password:

        raise ValueError(
            "Password cannot be empty."
        )

    return password_hasher.hash(
        password
    )


# ============================================================
# VERIFY PASSWORD
# ============================================================

def verify_password(
    password: str,
    password_hash: str
) -> bool:
    """
    Verify a plain-text password against its Argon2 hash.

    Returns:
        True  -> password is correct
        False -> password is incorrect or hash is invalid
    """

    if not isinstance(password, str):

        return False

    if not isinstance(password_hash, str):

        return False

    if not password_hash:

        return False

    try:

        return password_hasher.verify(
            password_hash,
            password
        )

    except (
        VerifyMismatchError,
        VerificationError,
        InvalidHashError
    ):

        return False


# ============================================================
# CHECK WHETHER HASH NEEDS REHASHING
# ============================================================

def needs_rehash(password_hash: str) -> bool:
    """
    Check whether an existing password hash should be
    regenerated using the current Argon2 configuration.

    This allows CivicPay to upgrade password security
    parameters in the future.
    """

    if not isinstance(password_hash, str):

        return False

    if not password_hash:

        return False

    try:

        return password_hasher.check_needs_rehash(
            password_hash
        )

    except (
        VerificationError,
        InvalidHashError
    ):

        return False