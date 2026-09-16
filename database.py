import sqlite3
from datetime import datetime


DATABASE = "telegram_bot.db"


def get_connection():
    return sqlite3.connect(DATABASE)


def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()

    # General users
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            first_seen TEXT NOT NULL,
            last_active TEXT NOT NULL,
            message_count INTEGER DEFAULT 0
        )
    """)

    # Verification requests
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            username TEXT,
            first_name TEXT,

            name TEXT,
            age INTEGER,

            latitude REAL,
            longitude REAL,

            selfie_file_id TEXT,

            verification_method TEXT,
            verification_status TEXT DEFAULT 'pending',

            submitted_at TEXT,
            reviewed_at TEXT,
            reviewed_by INTEGER,

            notes TEXT,

            UNIQUE(telegram_id, chat_id)
        )
    """)

    # Support databases created by an older version
    existing_columns = {
        row[1]
        for row in cursor.execute(
            "PRAGMA table_info(verifications)"
        ).fetchall()
    }

    columns_to_add = {
        "name": "TEXT",
        "age": "INTEGER",
        "latitude": "REAL",
        "longitude": "REAL",
        "selfie_file_id": "TEXT",
        "verification_method": "TEXT",
        "verification_status": "TEXT DEFAULT 'pending'",
        "submitted_at": "TEXT",
        "reviewed_at": "TEXT",
        "reviewed_by": "INTEGER",
        "notes": "TEXT",
    }

    for column, column_type in columns_to_add.items():
        if column not in existing_columns:
            cursor.execute(
                f"ALTER TABLE verifications "
                f"ADD COLUMN {column} {column_type}"
            )

    conn.commit()
    conn.close()


def save_user(user):
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO users (
            telegram_id,
            username,
            first_name,
            last_name,
            first_seen,
            last_active,
            message_count
        )
        VALUES (?, ?, ?, ?, ?, ?, 1)

        ON CONFLICT(telegram_id)
        DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name,
            last_name = excluded.last_name,
            last_active = excluded.last_active,
            message_count = users.message_count + 1
    """, (
        user.id,
        user.username,
        user.first_name,
        user.last_name,
        now,
        now
    ))

    conn.commit()
    conn.close()


def create_verification(user, chat_id):
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO verifications (
            telegram_id,
            chat_id,
            username,
            first_name,
            verification_status,
            submitted_at
        )
        VALUES (?, ?, ?, ?, 'pending', ?)

        ON CONFLICT(telegram_id, chat_id)
        DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name,
            verification_status = 'pending',
            submitted_at = excluded.submitted_at
    """, (
        user.id,
        chat_id,
        user.username,
        user.first_name,
        now
    ))

    conn.commit()
    conn.close()


def update_verification_details(
    telegram_id,
    chat_id,
    name,
    age,
    latitude,
    longitude,
    selfie_file_id
):
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.now().isoformat()

    cursor.execute("""
        UPDATE verifications
        SET
            name = ?,
            age = ?,
            latitude = ?,
            longitude = ?,
            selfie_file_id = ?,
            verification_status = 'pending',
            submitted_at = ?
        WHERE telegram_id = ?
        AND chat_id = ?
    """, (
        name,
        age,
        latitude,
        longitude,
        selfie_file_id,
        now,
        telegram_id,
        chat_id
    ))

    conn.commit()
    conn.close()


def update_verification_status(
    telegram_id,
    chat_id,
    status,
    reviewed_by=None,
    notes=None
):
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.now().isoformat()

    cursor.execute("""
        UPDATE verifications
        SET
            verification_status = ?,
            reviewed_at = ?,
            reviewed_by = ?,
            notes = ?
        WHERE telegram_id = ?
        AND chat_id = ?
    """, (
        status,
        now,
        reviewed_by,
        notes,
        telegram_id,
        chat_id
    ))

    conn.commit()
    conn.close()


def get_pending_verifications():
    conn = get_connection()
    cursor = conn.cursor()

    rows = cursor.execute("""
        SELECT
            telegram_id,
            chat_id,
            username,
            first_name,
            name,
            age,
            latitude,
            longitude,
            selfie_file_id,
            submitted_at,
            verification_status
        FROM verifications
        WHERE verification_status = 'pending'
        ORDER BY submitted_at ASC
    """).fetchall()

    conn.close()

    return rows


def get_verification(telegram_id, chat_id):
    conn = get_connection()
    cursor = conn.cursor()

    row = cursor.execute("""
        SELECT
            telegram_id,
            chat_id,
            username,
            first_name,
            name,
            age,
            latitude,
            longitude,
            selfie_file_id,
            verification_status,
            submitted_at,
            reviewed_at,
            reviewed_by,
            notes
        FROM verifications
        WHERE telegram_id = ?
        AND chat_id = ?
    """, (
        telegram_id,
        chat_id
    )).fetchone()

    conn.close()

    return row