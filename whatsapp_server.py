from __future__ import annotations

import hashlib
import hmac
import mimetypes
import os
from typing import Any

import requests
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from whatsapp_control import (
    build_comment,
    build_trend_post,
    create_approval,
    format_approval,
    help_text,
    resolve_approval,
    status_text,
    verify_admin,
)

app = FastAPI(title="LinkedIn Automation WhatsApp Control")

GRAPH_VERSION = os.getenv("WHATSAPP_GRAPH_VERSION", "v26.0")
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


def _verify_signature(body: bytes, signature: str) -> bool:
    secret = _env("WHATSAPP_APP_SECRET")
    if not secret:
        return False
    if not signature.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature.split("=", 1)[1], expected)


def send_whatsapp_text(to: str, body: str) -> None:
    token = _env("WHATSAPP_ACCESS_TOKEN")
    phone_id = _env("WHATSAPP_PHONE_NUMBER_ID")
    if not token or not phone_id:
        raise RuntimeError("WhatsApp access token or phone number ID is missing.")

    response = requests.post(
        f"{GRAPH_BASE}/{phone_id}/messages",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "messaging_product": "whatsapp",
            "to": to.replace("whatsapp:", "").replace(" ", ""),
            "type": "text",
            "text": {"preview_url": False, "body": body[:4096]},
        },
        timeout=30,
    )
    response.raise_for_status()


def download_whatsapp_media(media_id: str) -> tuple[bytes, str]:
    token = _env("WHATSAPP_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("WhatsApp access token is missing.")

    meta = requests.get(
        f"{GRAPH_BASE}/{media_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    meta.raise_for_status()
    media_url = meta.json().get("url")
    mime = meta.json().get("mime_type", "image/jpeg")
    if not media_url:
        raise ValueError("WhatsApp media URL was not returned.")

    media = requests.get(
        media_url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    media.raise_for_status()
    return media.content, mime


def extract_messages(payload: dict[str, Any]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []) or []:
                messages.append(message)
    return messages


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "whatsapp-control"}


@app.get("/webhook")
def verify_webhook(
    hub_mode: str | None = Query(default=None, alias="hub.mode"),
    hub_verify_token: str | None = Query(default=None, alias="hub.verify_token"),
    hub_challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> PlainTextResponse:
    if (
        hub_mode == "subscribe"
        and hub_verify_token
        and hmac.compare_digest(hub_verify_token, _env("WHATSAPP_VERIFY_TOKEN"))
        and hub_challenge
    ):
        return PlainTextResponse(hub_challenge)

    raise HTTPException(status_code=403, detail="Webhook verification failed.")


@app.post("/webhook")
async def whatsapp_webhook(request: Request) -> dict[str, bool]:
    body = await request.body()
    if not _verify_signature(
        body,
        request.headers.get("x-hub-signature-256", ""),
    ):
        raise HTTPException(status_code=403, detail="Invalid webhook signature.")

    payload = await request.json()
    openrouter_key = _env("OPENROUTER_API_KEY")
    gnews_key = _env("GNEWS_API_KEY")
    model = _env("OPENROUTER_MODEL") or "openrouter/free"

    for message in extract_messages(payload):
        sender = str(message.get("from", ""))
        if not verify_admin(sender):
            continue

        msg_type = message.get("type", "")
        body_text = ""
        image_bytes = None
        image_mime = "image/jpeg"

        if msg_type == "text":
            body_text = message.get("text", {}).get("body", "")
        elif msg_type == "image":
            body_text = message.get("image", {}).get("caption", "")
            media_id = message.get("image", {}).get("id")
            if media_id:
                try:
                    image_bytes, image_mime = download_whatsapp_media(media_id)
                except Exception as exc:
                    send_whatsapp_text(sender, f"Poster download failed: {exc}")
                    continue
        else:
            send_whatsapp_text(sender, "Supported controls: text commands and image messages.")
            continue

        command = body_text.strip()
        upper = command.upper()

        try:
            if upper == "HELP":
                send_whatsapp_text(sender, help_text())
                continue

            if upper == "STATUS":
                send_whatsapp_text(sender, status_text())
                continue

            if upper.startswith("APPROVE "):
                approval_id = upper.split(maxsplit=1)[1].strip()
                row = resolve_approval(approval_id, "approved")
                if not row:
                    send_whatsapp_text(sender, "Approval ID not found or already resolved.")
                else:
                    send_whatsapp_text(
                        sender,
                        (
                            f"Approved {approval_id}.\n\n"
                            "The draft is approved for your manual LinkedIn action. "
                            "Use the Open LinkedIn button in the local/web app or copy the draft."
                        ),
                    )
                continue

            if upper.startswith("REJECT "):
                approval_id = upper.split(maxsplit=1)[1].strip()
                row = resolve_approval(approval_id, "rejected")
                if not row:
                    send_whatsapp_text(sender, "Approval ID not found or already resolved.")
                else:
                    send_whatsapp_text(sender, f"Rejected {approval_id}.")
                continue

            if upper.startswith("TREND "):
                region = command.split(maxsplit=1)[1].strip()
                if not openrouter_key or not gnews_key:
                    send_whatsapp_text(sender, "Configure OPENROUTER_API_KEY and GNEWS_API_KEY first.")
                    continue
                post = build_trend_post(openrouter_key, gnews_key, model, region)
                approval_id = create_approval("Trending Topic Post", post)
                send_whatsapp_text(
                    sender,
                    format_approval("Trending Topic Post", approval_id, post),
                )
                continue

            if upper.startswith("COMMENT"):
                post_text = command[len("COMMENT"):].strip()
                if not post_text and not image_bytes:
                    send_whatsapp_text(
                        sender,
                        "Send COMMENT followed by the post text, or send the poster image with its post text as the caption.",
                    )
                    continue
                if not openrouter_key:
                    send_whatsapp_text(sender, "Configure OPENROUTER_API_KEY first.")
                    continue

                comment = build_comment(
                    openrouter_key,
                    model,
                    post_text,
                    poster_bytes=image_bytes,
                    poster_mime=image_mime,
                )
                approval_id = create_approval("Connection Comment", comment)
                send_whatsapp_text(
                    sender,
                    format_approval("Connection Comment", approval_id, comment),
                )
                continue

            send_whatsapp_text(
                sender,
                "Unknown command. Reply HELP for available remote controls.",
            )
        except Exception as exc:
            send_whatsapp_text(sender, f"Command failed: {exc}")

    return {"received": True}
