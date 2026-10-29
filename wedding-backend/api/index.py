
import hashlib
import hmac
import os
import secrets
import time
from datetime import timezone

import psycopg
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


app = FastAPI(
    title="Bhavesh & Heena Wedding Guestbook (Bride Side)",
    version="1.0.2",
)


# -------------------- CORS --------------------
# Public wedding guestbook API; no cookies are used.
# Allow browser requests from any origin.
app.add_middleware(
    CORSMiddleware,
allow_origins=[
    "https://wedding-eta.vercel.app",
],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=600,
)


# -------------------- ENVIRONMENT VARIABLES --------------------

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
TOKEN_SECRET = os.getenv("TOKEN_SECRET", "")

# Keep this ID unique to the bride-side wedding.
WEDDING_ID = (
    os.getenv("WEDDING_ID", "heena-bride-side").strip()
    or "heena-bride-side"
)


# -------------------- REQUEST MODELS --------------------

class WishInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    message: str = Field(min_length=1, max_length=1000)


class LoginInput(BaseModel):
    password: str = Field(min_length=1, max_length=256)


# -------------------- DATABASE --------------------

def get_connection():
    if not DATABASE_URL:
        raise HTTPException(
            status_code=503,
            detail="Database is not configured. Set DATABASE_URL in Vercel.",
        )

    return psycopg.connect(
        DATABASE_URL,
        connect_timeout=10,
    )


def ensure_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS wedding_wishes (
            id BIGSERIAL PRIMARY KEY,
            wedding_id VARCHAR(100) NOT NULL
                DEFAULT 'bhavesh-groom-side',
            name VARCHAR(80) NOT NULL,
            message VARCHAR(1000) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    conn.execute("""
        ALTER TABLE wedding_wishes
        ADD COLUMN IF NOT EXISTS wedding_id VARCHAR(100)
        NOT NULL DEFAULT 'bhavesh-groom-side'
    """)


# -------------------- ADMIN TOKEN --------------------

def sign_token(payload):
    signature = hmac.new(
        TOKEN_SECRET.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()

    return f"{payload}.{signature}"


def validate_token(token):
    if not token or not TOKEN_SECRET:
        return False

    try:
        payload, signature = token.rsplit(".", 1)

        expected = hmac.new(
            TOKEN_SECRET.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected):
            return False

        expiry = int(payload.split(":", 1)[0])
        return expiry > int(time.time())

    except (ValueError, IndexError):
        return False


def require_admin(authorization):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    token = authorization[7:].strip()

    if not validate_token(token):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired admin token.",
        )


# -------------------- HEALTH CHECKS --------------------

@app.get("/")
def root():
    return {
        "ok": True,
        "service": "Bhavesh & Heena Wedding Guestbook (Bride Side)",
        "docs": "/docs",
    }


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "database_configured": bool(DATABASE_URL),
    }


@app.get("/api/health/database")
def database_health():
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1")

        return {
            "ok": True,
            "database_connected": True,
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Database connection failed. Check DATABASE_URL and Neon settings.",
        )


# -------------------- PUBLIC GUEST BOOK --------------------

@app.post("/api/wishes")
def create_wish(body: WishInput):
    name = body.name.strip()
    message = body.message.strip()

    if not name or not message:
        raise HTTPException(
            status_code=422,
            detail="Please enter your name and blessings.",
        )

    try:
        with get_connection() as conn:
            ensure_table(conn)

            row = conn.execute(
                """
                INSERT INTO wedding_wishes
                    (wedding_id, name, message)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (WEDDING_ID, name, message),
            ).fetchone()

            conn.commit()

        return {
            "ok": True,
            "id": row[0],
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Could not save your blessings right now. Please try again.",
        )


# -------------------- ADMIN LOGIN --------------------

@app.post("/api/admin/login")
def admin_login(body: LoginInput):
    if not ADMIN_PASSWORD or not TOKEN_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Admin login is not configured. Set ADMIN_PASSWORD and TOKEN_SECRET.",
        )

    if not hmac.compare_digest(
        body.password.encode(),
        ADMIN_PASSWORD.encode(),
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect password.",
        )

    payload = (
        f"{int(time.time()) + 43200}:"
        f"{secrets.token_urlsafe(18)}"
    )

    return {
        "token": sign_token(payload),
        "expires_in": 43200,
    }


# -------------------- ADMIN: LIST BLESSINGS --------------------

@app.get("/api/admin/wishes")
def list_wishes(authorization: str = Header(default="")):
    require_admin(authorization)

    try:
        with get_connection() as conn:
            ensure_table(conn)

            rows = conn.execute(
                """
                SELECT id, name, message, created_at
                FROM wedding_wishes
                WHERE wedding_id = %s
                ORDER BY created_at DESC
                LIMIT 1000
                """,
                (WEDDING_ID,),
            ).fetchall()

        return {
            "wishes": [
                {
                    "id": row[0],
                    "name": row[1],
                    "message": row[2],
                    "created_at": row[3]
                    .astimezone(timezone.utc)
                    .isoformat(),
                }
                for row in rows
            ]
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Could not load the guestbook.",
        )


# -------------------- ADMIN: DELETE BLESSING --------------------

@app.delete("/api/admin/wishes/{wish_id}")
def delete_wish(
    wish_id: int,
    authorization: str = Header(default=""),
):
    require_admin(authorization)

    try:
        with get_connection() as conn:
            ensure_table(conn)

            result = conn.execute(
                """
                DELETE FROM wedding_wishes
                WHERE id = %s AND wedding_id = %s
                """,
                (wish_id, WEDDING_ID),
            )

            conn.commit()

            if result.rowcount == 0:
                raise HTTPException(
                    status_code=404,
                    detail="Blessing not found.",
                )

        return {"ok": True}

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Could not delete this blessing.",
        )
