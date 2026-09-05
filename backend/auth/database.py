import sqlite3
from pathlib import Path


# ============================================================
# CIVICPAY USER DATABASE
# ============================================================

# Get the backend directory.
BASE_DIR = Path(__file__).resolve().parent.parent

# SQLite database file.
DATABASE_PATH = BASE_DIR / "civicpay.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    """
    Create and return a connection to the CivicPay SQLite database.
    """

    connection = sqlite3.connect(
        DATABASE_PATH,
        check_same_thread=False
    )

    connection.row_factory = sqlite3.Row

    return connection


# ============================================================
# INITIALIZE DATABASE
# ============================================================

def initialize_database():
    """
    Create the required CivicPay database tables if they
    do not already exist.
    """

    connection = get_connection()

    try:

        cursor = connection.cursor()

        # ----------------------------------------------------
        # USERS TABLE
        # ----------------------------------------------------

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                username TEXT NOT NULL UNIQUE,

                email TEXT NOT NULL UNIQUE,

                password_hash TEXT NOT NULL,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP

            )
            """
        )

        # ----------------------------------------------------
        # ANALYSIS HISTORY TABLE
        #
        # Each analysis belongs to exactly one user.
        #
        # IMPORTANT:
        # The uploaded payment image is NOT stored here.
        # Raw OCR and QR payloads are NOT stored here.
        # ----------------------------------------------------

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_history (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                user_id INTEGER NOT NULL,

                analysis_id TEXT NOT NULL UNIQUE,

                original_filename TEXT,

                risk_level TEXT,

                risk_score REAL,

                verification_status TEXT,

                verification_confidence REAL,

                ai_decision TEXT,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE

            )
            """
        )

        # ----------------------------------------------------
        # INDEX FOR USER-SPECIFIC QUERIES
        #
        # This makes secure user-history queries efficient.
        # ----------------------------------------------------

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_analysis_history_user_id
            ON analysis_history(user_id)
            """
        )

        # ----------------------------------------------------
        # INDEX FOR RECENT HISTORY
        #
        # Helps when history is ordered by creation time.
        # ----------------------------------------------------

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_analysis_history_user_created
            ON analysis_history(user_id, created_at DESC)
            """
        )

        connection.commit()

    finally:

        connection.close()


# ============================================================
# CREATE USER
# ============================================================

def create_user(
    username: str,
    email: str,
    password_hash: str
):
    """
    Create a new user.

    Returns:
        dict containing the newly created user,
        or None if creation fails because the username
        or email already exists.
    """

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO users (
                username,
                email,
                password_hash
            )
            VALUES (?, ?, ?)
            """,
            (
                username,
                email,
                password_hash
            )
        )

        connection.commit()

        user_id = cursor.lastrowid

        return {
            "id": user_id,
            "username": username,
            "email": email
        }

    except sqlite3.IntegrityError:

        return None

    finally:

        connection.close()


# ============================================================
# FIND USER BY EMAIL
# ============================================================

def get_user_by_email(email: str):
    """
    Find a user using their email address.

    Returns:
        Dictionary-like SQLite Row if found,
        otherwise None.
    """

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                username,
                email,
                password_hash,
                created_at
            FROM users
            WHERE email = ?
            LIMIT 1
            """,
            (email,)
        )

        user = cursor.fetchone()

        return user

    finally:

        connection.close()


# ============================================================
# FIND USER BY ID
# ============================================================

def get_user_by_id(user_id: int):
    """
    Find a user using their database ID.

    Returns:
        Dictionary-like SQLite Row if found,
        otherwise None.
    """

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                username,
                email,
                created_at
            FROM users
            WHERE id = ?
            LIMIT 1
            """,
            (user_id,)
        )

        user = cursor.fetchone()

        return user

    finally:

        connection.close()


# ============================================================
# FIND USER BY USERNAME
# ============================================================

def get_user_by_username(username: str):
    """
    Find a user using their username.

    Returns:
        Dictionary-like SQLite Row if found,
        otherwise None.
    """

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                username,
                email,
                password_hash,
                created_at
            FROM users
            WHERE username = ?
            LIMIT 1
            """,
            (username,)
        )

        user = cursor.fetchone()

        return user

    finally:

        connection.close()


# ============================================================
# CREATE ANALYSIS HISTORY RECORD
# ============================================================

def create_analysis_record(
    user_id: int,
    analysis_id: str,
    original_filename: str,
    risk_level: str,
    risk_score: float,
    verification_status: str,
    verification_confidence: float,
    ai_decision: str
):
    """
    Store a privacy-safe analysis record belonging to a user.

    IMPORTANT:
    This function does NOT store:
        - uploaded image
        - OCR text
        - QR payload
        - UPI ID
        - merchant name
        - payment amount

    Only summary information required for secure analysis
    history is stored.
    """

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO analysis_history (

                user_id,
                analysis_id,
                original_filename,
                risk_level,
                risk_score,
                verification_status,
                verification_confidence,
                ai_decision

            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                analysis_id,
                original_filename,
                risk_level,
                risk_score,
                verification_status,
                verification_confidence,
                ai_decision
            )
        )

        connection.commit()

        return {
            "id": cursor.lastrowid,
            "analysis_id": analysis_id,
            "user_id": user_id
        }

    except sqlite3.IntegrityError:

        return None

    finally:

        connection.close()


# ============================================================
# PHASE 6.4.1
# GET AUTHENTICATED USER'S ANALYSIS HISTORY
# ============================================================

def get_analysis_history_by_user(
    user_id: int,
    limit: int = 50
):
    """
    Retrieve analysis history belonging ONLY to the specified
    authenticated user.

    SECURITY:
    The caller must provide the user ID obtained from the
    authenticated JWT.

    This function intentionally selects only privacy-safe
    summary fields.

    It does NOT return:
        - uploaded image
        - OCR text
        - QR payload
        - UPI ID
        - merchant name
        - payment amount
        - original filename

    Returns:
        List of privacy-safe analysis history records.
    """

    connection = get_connection()

    try:

        cursor = connection.cursor()

        # ----------------------------------------------------
        # Keep the limit within a safe server-side range.
        # ----------------------------------------------------

        try:

            limit = int(limit)

        except (
            TypeError,
            ValueError
        ):

            limit = 50

        limit = max(
            1,
            min(limit, 100)
        )

        # ----------------------------------------------------
        # IMPORTANT SECURITY RULE
        #
        # user_id is taken from the authenticated JWT by the
        # API layer.
        #
        # There is NO query parameter allowing a client to
        # choose another user's ID.
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                analysis_id,
                risk_level,
                risk_score,
                verification_status,
                verification_confidence,
                ai_decision,
                created_at
            FROM analysis_history
            WHERE user_id = ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (
                user_id,
                limit
            )
        )

        rows = cursor.fetchall()

        history = []

        for row in rows:

            history.append(
                {
                    "analysis_id": row["analysis_id"],
                    "risk_level": row["risk_level"],
                    "risk_score": row["risk_score"],
                    "verification_status":
                        row["verification_status"],
                    "verification_confidence":
                        row["verification_confidence"],
                    "ai_decision":
                        row["ai_decision"],
                    "created_at": row["created_at"]
                }
            )

        return history

    finally:

        connection.close()