
import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone

import psycopg
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# --------------------------------------------------
# APP CONFIGURATION
# --------------------------------------------------

app = FastAPI(
    title="Bhavesh & Heena Wedding Guestbook (Bride Side)",
    version="1.0.4",
)

ALLOWED_ORIGINS = [
    "https://bride-wedding.vercel.app",
    "https://wedding-eta.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=600,
)

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
TOKEN_SECRET = os.getenv("TOKEN_SECRET", "")
WEDDING_ID = (
    os.getenv("WEDDING_ID", "heena-bride-side").strip()
    or "heena-bride-side"
)


# --------------------------------------------------
# REQUEST MODELS
# --------------------------------------------------

class WishInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    message: str = Field(min_length=1, max_length=1000)


class LoginInput(BaseModel):
    password: str = Field(min_length=1, max_length=200)


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

def get_connection():
    if not DATABASE_URL:
        raise HTTPException(
            status_code=500,
            detail="DATABASE_URL environment variable is missing",
        )

    try:
        return psycopg.connect(
            DATABASE_URL,
            connect_timeout=10,
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Could not connect to the database",
        )


def ensure_table():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS wedding_wishes (
                    id BIGSERIAL PRIMARY KEY,
                    name VARCHAR(80) NOT NULL,
                    message TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )

            cur.execute(
                """
                ALTER TABLE wedding_wishes
                ADD COLUMN IF NOT EXISTS wedding_id
                VARCHAR(100) NOT NULL DEFAULT 'bhavesh-groom-side'
                """
            )

        conn.commit()


# --------------------------------------------------
# ADMIN TOKEN HELPERS
# --------------------------------------------------

def create_admin_token():
    if not TOKEN_SECRET:
        raise HTTPException(
            status_code=500,
            detail="TOKEN_SECRET environment variable is missing",
        )

    payload = {
        "exp": int(time.time()) + 60 * 60 * 12,
        "wedding_id": WEDDING_ID,
    }

    payload_bytes = json.dumps(
        payload,
        separators=(",", ":"),
    ).encode("utf-8")

    encoded_payload = base64.urlsafe_b64encode(
        payload_bytes
    ).decode("utf-8").rstrip("=")

    signature = hmac.new(
        TOKEN_SECRET.encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    encoded_signature = base64.urlsafe_b64encode(
        signature
    ).decode("utf-8").rstrip("=")

    return f"{encoded_payload}.{encoded_signature}"


def verify_admin_token(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Admin authentication required",
        )

    if not TOKEN_SECRET:
        raise HTTPException(
            status_code=500,
            detail="TOKEN_SECRET environment variable is missing",
        )

    token = authorization.split(" ", 1)[1].strip()
    parts = token.split(".")

    if len(parts) != 2:
        raise HTTPException(
            status_code=401,
            detail="Invalid admin token",
        )

    encoded_payload, encoded_signature = parts

    expected_signature = hmac.new(
        TOKEN_SECRET.encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    expected_encoded_signature = base64.urlsafe_b64encode(
        expected_signature
    ).decode("utf-8").rstrip("=")

    if not hmac.compare_digest(
        encoded_signature,
        expected_encoded_signature,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid admin token",
        )

    try:
        padded_payload = encoded_payload + "=" * (
            -len(encoded_payload) % 4
        )

        payload = json.loads(
            base64.urlsafe_b64decode(padded_payload)
        )
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid admin token",
        )

    if payload.get("exp", 0) < int(time.time()):
        raise HTTPException(
            status_code=401,
            detail="Admin token has expired",
        )

    if payload.get("wedding_id") != WEDDING_ID:
        raise HTTPException(
            status_code=403,
            detail="Token is for a different wedding",
        )

    return payload


# --------------------------------------------------
# BASIC & HEALTH ENDPOINTS
# --------------------------------------------------

@app.get("/")
def root():
    return {
        "ok": True,
        "message": "Wedding guestbook API is running",
        "wedding_id": WEDDING_ID,
    }


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "service": "wedding-guestbook",
        "wedding_id": WEDDING_ID,
    }


@app.get("/api/health/database")
def database_health():
    try:
        ensure_table()

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()

        return {
            "ok": True,
            "database_connected": True,
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Database health check failed",
        )


# --------------------------------------------------
# PUBLIC GUESTBOOK ENDPOINTS
# --------------------------------------------------

@app.post("/api/wishes")
def create_wish(wish: WishInput):
    name = wish.name.strip()
    message = wish.message.strip()

    if not name or not message:
        raise HTTPException(
            status_code=422,
            detail="Name and message are required",
        )

    try:
        ensure_table()

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO wedding_wishes
                    (wedding_id, name, message)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (WEDDING_ID, name, message),
                )

                row = cur.fetchone()

            conn.commit()

        return {
            "ok": True,
            "id": row[0],
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Could not save the wedding wish",
        )


@app.get("/api/wishes")
def get_public_wishes():
    try:
        ensure_table()

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, message, created_at
                    FROM wedding_wishes
                    WHERE wedding_id = %s
                    ORDER BY created_at DESC, id DESC
                    LIMIT 200
                    """,
                    (WEDDING_ID,),
                )

                rows = cur.fetchall()

        wishes = []

        for row in rows:
            created_at = row[3]

            if isinstance(created_at, datetime):
                if created_at.tzinfo is None:
                    created_at = created_at.replace(
                        tzinfo=timezone.utc
                    )

                created_at = created_at.isoformat()

            wishes.append(
                {
                    "id": row[0],
                    "name": row[1],
                    "message": row[2],
                    "created_at": created_at,
                }
            )

        return {
            "ok": True,
            "wishes": wishes,
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Could not load wedding wishes",
        )


# --------------------------------------------------
# ADMIN LOGIN
# --------------------------------------------------

@app.post("/api/admin/login")
def admin_login(data: LoginInput):
    if not ADMIN_PASSWORD:
        raise HTTPException(
            status_code=500,
            detail="ADMIN_PASSWORD environment variable is missing",
        )

    if not hmac.compare_digest(
        data.password,
        ADMIN_PASSWORD,
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect admin password",
        )

    return {
        "ok": True,
        "token": create_admin_token(),
    }


# --------------------------------------------------
# ADMIN: VIEW ALL WISHES
# --------------------------------------------------

@app.get("/api/admin/wishes")
def admin_get_wishes(
    authorization: str | None = Header(default=None),
):
    verify_admin_token(authorization)

    try:
        ensure_table()

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, message, created_at
                    FROM wedding_wishes
                    WHERE wedding_id = %s
                    ORDER BY created_at DESC, id DESC
                    """,
                    (WEDDING_ID,),
                )

                rows = cur.fetchall()

        wishes = []

        for row in rows:
            created_at = row[3]

            if isinstance(created_at, datetime):
                if created_at.tzinfo is None:
                    created_at = created_at.replace(
                        tzinfo=timezone.utc
                    )

                created_at = created_at.isoformat()

            wishes.append(
                {
                    "id": row[0],
                    "name": row[1],
                    "message": row[2],
                    "created_at": created_at,
                }
            )

        return {
            "ok": True,
            "wishes": wishes,
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Could not load admin wishes",
        )


# --------------------------------------------------
# ADMIN: DELETE A WISH
# --------------------------------------------------

@app.delete("/api/admin/wishes/{wish_id}")
def admin_delete_wish(
    wish_id: int,
    authorization: str | None = Header(default=None),
):
    verify_admin_token(authorization)

    try:
        ensure_table()

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM wedding_wishes
                    WHERE id = %s AND wedding_id = %s
                    RETURNING id
                    """,
                    (wish_id, WEDDING_ID),
                )

                deleted = cur.fetchone()

            conn.commit()

        if not deleted:
            raise HTTPException(
                status_code=404,
                detail="Wish not found",
            )

        return {
            "ok": True,
            "deleted_id": deleted[0],
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Could not delete the wedding wish",
        )
