from __future__ import annotations

import hashlib
import hmac
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_news import fetch_gnews, generate_with_openrouter

DB_PATH = Path(os.getenv("WHATSAPP_STATE_DB", "data/whatsapp_state.db"))

TREND_QUERIES = {
    "india": ("India technology OR business OR AI OR stock market", "in"),
    "global": ("technology OR AI OR business OR markets", "us"),
    "technology": ("artificial intelligence OR software OR cloud OR cybersecurity", "us"),
    "business": ("business OR startups OR finance OR markets", "us"),
}


def _connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS approvals (
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
        )
        """
    )
    conn.commit()
    return conn


def create_approval(kind: str, content: str) -> str:
    seed = f"{kind}|{content}|{datetime.now(timezone.utc).isoformat()}".encode()
    approval_id = hashlib.sha256(seed).hexdigest()[:8].upper()
    with _connection() as conn:
        conn.execute(
            "INSERT INTO approvals(id, kind, content, created_at, status) VALUES (?, ?, ?, ?, 'pending')",
            (approval_id, kind, content, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    return approval_id


def resolve_approval(approval_id: str, status: str) -> sqlite3.Row | None:
    with _connection() as conn:
        row = conn.execute(
            "SELECT * FROM approvals WHERE id = ? AND status = 'pending'",
            (approval_id.upper(),),
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE approvals SET status = ? WHERE id = ?",
                (status, approval_id.upper()),
            )
            conn.commit()
        return row


def verify_admin(sender: str) -> bool:
    allowed = os.getenv("WHATSAPP_ADMIN_PHONE", "").strip()
    if not allowed:
        return False

    normalized_sender = re.sub(r"\D", "", sender)
    normalized_allowed = re.sub(r"\D", "", allowed)
    return bool(normalized_sender) and hmac.compare_digest(
        normalized_sender,
        normalized_allowed,
    )


def build_trend_post(api_key: str, gnews_key: str, model: str, region: str) -> str:
    normalized = region.strip().lower()
    if normalized not in TREND_QUERIES:
        raise ValueError(
            "Unknown trend region. Use India, Global, Technology, or Business."
        )

    query, country = TREND_QUERIES[normalized]
    articles = fetch_gnews(
        gnews_key,
        query=query,
        country=country,
        language="en",
        limit=10,
    )
    if not articles:
        raise ValueError("No current news articles were returned.")

    context = "\n\n".join(
        f"{i}. {a.get('title', '')} | "
        f"{a.get('source', {}).get('name', 'Unknown')} | "
        f"{a.get('publishedAt', '')} | "
        f"{a.get('description', '')} | "
        f"{a.get('url', '')}"
        for i, a in enumerate(articles, start=1)
    )

    system = (
        "Create one professional LinkedIn post based only on the supplied current news. "
        "Identify one strong theme, explain concrete developments, add one practical takeaway, "
        "avoid unsupported claims, and end with 4-6 concise hashtags. "
        "Do not mention hidden reasoning."
    )
    user = f"Region: {region}\n\nCurrent news:\n{context}"
    return generate_with_openrouter(
        api_key,
        system,
        user,
        model=model,
        use_reasoning=True,
    )


def build_comment(
    api_key: str,
    model: str,
    post_text: str,
    poster_bytes: bytes | None = None,
    poster_mime: str = "image/jpeg",
    question_focus: str = "Implementation",
) -> str:
    system = (
        "Write a professional LinkedIn comment in a practical builder style. "
        "Sound like someone who actively builds, tests, learns, and thinks about real-world implementation. "
        "Use this structure: specific point from the post/poster -> original professional or technical insight "
        "-> practical building implication -> ONE specific answerable question. "
        "The question must relate to the requested focus and the actual content. "
        "Avoid generic praise, empty engagement bait, repetition, invented facts, invented experience, "
        "invented visual details, hashtags, and emojis. "
        "Keep it natural, concise, normally 3-5 sentences and 50-90 words. "
        "Do not reveal hidden reasoning."
    )
    user = (
        f"Question focus: {question_focus}\n\n"
        f"LinkedIn post text:\n{post_text.strip() or 'Not supplied'}"
    )
    return generate_with_openrouter(
        api_key,
        system,
        user,
        model=model,
        use_reasoning=True,
        image_bytes=poster_bytes,
        image_mime=poster_mime,
    )


def help_text() -> str:
    return (
        "LinkedIn Automation remote control\n\n"
        "STATUS - check configuration\n"
        "TREND India - generate a current-news LinkedIn draft\n"
        "TREND Global\n"
        "TREND Technology\n"
        "TREND Business\n"
        "COMMENT <post text> - generate a builder-style comment\n"
        "COMMENT with a poster image - send the image with a caption containing the post text\n"
        "APPROVE <ID> - approve the generated draft for manual LinkedIn use\n"
        "REJECT <ID> - reject a pending draft\n"
        "HELP - show commands\n\n"
        "LinkedIn posting/commenting stays a human action."
    )


def status_text() -> str:
    openrouter = bool(os.getenv("OPENROUTER_API_KEY", "").strip())
    gnews = bool(os.getenv("GNEWS_API_KEY", "").strip())
    whatsapp = bool(os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip())
    phone_id = bool(os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip())
    return (
        "Remote control status\n\n"
        f"OpenRouter: {'configured' if openrouter else 'missing'}\n"
        f"GNews: {'configured' if gnews else 'missing'}\n"
        f"WhatsApp access token: {'configured' if whatsapp else 'missing'}\n"
        f"WhatsApp phone ID: {'configured' if phone_id else 'missing'}\n"
        "LinkedIn: manual action required"
    )


def format_approval(kind: str, approval_id: str, content: str) -> str:
    preview = content.strip()
    if len(preview) > 2500:
        preview = preview[:2500].rstrip() + "..."
    return (
        f"{kind} draft\n\n"
        f"{preview}\n\n"
        f"Approval ID: {approval_id}\n"
        f"Reply APPROVE {approval_id} or REJECT {approval_id}."
    )
