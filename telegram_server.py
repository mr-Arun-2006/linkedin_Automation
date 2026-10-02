from __future__ import annotations

import os
from typing import Any

import requests
from fastapi import FastAPI, HTTPException, Request

from telegram_control import (
    build_comment,
    build_trend_post,
    create_approval,
    format_approval,
    help_text,
    resolve_approval,
    status_text,
    verify_admin,
)

app = FastAPI(title="LinkedIn Automation Telegram Control")

TELEGRAM_API = "https://api.telegram.org"
TELEGRAM_FILE_API = "https://api.telegram.org/file"


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


def _bot_url(method: str) -> str:
    token = _env("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured.")
    return f"{TELEGRAM_API}/bot{token}/{method}"


def telegram_call(method: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(
        _bot_url(method),
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("description", "Telegram API request failed."))
    return data


def send_text(chat_id: int, text: str, reply_markup: dict[str, Any] | None = None) -> None:
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text[:4096],
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    telegram_call("sendMessage", payload)


def send_approval(chat_id: int, kind: str, approval_id: str, content: str) -> None:
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "Approve", "callback_data": f"approve:{approval_id}"},
                {"text": "Reject", "callback_data": f"reject:{approval_id}"},
            ],
            [
                {
                    "text": "Open LinkedIn",
                    "url": "https://www.linkedin.com/feed/",
                }
            ],
        ]
    }
    send_text(
        chat_id,
        format_approval(kind, approval_id, content),
        reply_markup=keyboard,
    )


def download_telegram_photo(file_id: str) -> tuple[bytes, str]:
    file_info = telegram_call("getFile", {"file_id": file_id})
    file_path = file_info.get("result", {}).get("file_path")
    if not file_path:
        raise ValueError("Telegram file path was not returned.")

    token = _env("TELEGRAM_BOT_TOKEN")
    response = requests.get(
        f"{TELEGRAM_FILE_API}/bot{token}/{file_path}",
        timeout=30,
    )
    response.raise_for_status()

    extension = os.path.splitext(file_path)[1].lower()
    mime = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(extension, "image/jpeg")
    return response.content, mime


def answer_callback(callback_id: str, text: str) -> None:
    try:
        telegram_call(
            "answerCallbackQuery",
            {"callback_query_id": callback_id, "text": text[:200]},
        )
    except Exception:
        pass


def process_message(message: dict[str, Any]) -> None:
    from_user = message.get("from", {})
    user_id = from_user.get("id")
    chat_id = message.get("chat", {}).get("id")

    if user_id is None or chat_id is None:
        return

    text = (message.get("text") or message.get("caption") or "").strip()
    if text.lower() in {"/id", "id"}:
        send_text(
            int(chat_id),
            f"Your Telegram user ID is: {user_id}\nUse this numeric ID for TELEGRAM_ADMIN_USER_ID.",
        )
        return

    if not verify_admin(int(user_id)):
        return
    photo = message.get("photo") or []

    if not text:
        send_text(
            int(chat_id),
            "Send a command. Use /help to see the available controls.",
        )
        return

    lower = text.lower()

    if lower in {"/start", "/help", "help"}:
        send_text(int(chat_id), help_text())
        return

    if lower in {"/status", "status"}:
        send_text(int(chat_id), status_text())
        return

    if lower.startswith("/approve ") or lower.startswith("/reject "):
        parts = text.split(maxsplit=1)
        command = parts[0].lower()
        approval_id = parts[1].strip().upper() if len(parts) > 1 else ""
        status = "approved" if command == "/approve" else "rejected"
        row = resolve_approval(approval_id, status)
        if not row:
            send_text(int(chat_id), "Approval ID not found or already resolved.")
        elif status == "approved":
            send_text(
                int(chat_id),
                (
                    f"Approved {approval_id}.\n\n"
                    "Your draft is approved for manual LinkedIn action. "
                    "Use the Open LinkedIn button from the draft message."
                ),
            )
        else:
            send_text(int(chat_id), f"Rejected {approval_id}.")
        return

    openrouter_key = _env("OPENROUTER_API_KEY")
    gnews_key = _env("GNEWS_API_KEY")
    model = _env("OPENROUTER_MODEL") or "openrouter/free"

    if lower.startswith("/trend "):
        region = text.split(maxsplit=1)[1].strip()
        if not openrouter_key or not gnews_key:
            send_text(
                int(chat_id),
                "Configure OPENROUTER_API_KEY and GNEWS_API_KEY first.",
            )
            return
        post = build_trend_post(openrouter_key, gnews_key, model, region)
        approval_id = create_approval("Trending Topic Post", post)
        send_approval(int(chat_id), "Trending Topic Post", approval_id, post)
        return

    if lower.startswith("/comment"):
        post_text = text[len("/comment"):].strip()
        image_bytes = None
        image_mime = "image/jpeg"

        if photo:
            file_id = photo[-1].get("file_id")
            if file_id:
                image_bytes, image_mime = download_telegram_photo(file_id)

        if not post_text and not image_bytes:
            send_text(
                int(chat_id),
                (
                    "Use /comment <LinkedIn post text>, or send the poster image "
                    "with /comment <LinkedIn post text> as the caption."
                ),
            )
            return

        if not openrouter_key:
            send_text(int(chat_id), "Configure OPENROUTER_API_KEY first.")
            return

        comment = build_comment(
            openrouter_key,
            model,
            post_text,
            poster_bytes=image_bytes,
            poster_mime=image_mime,
        )
        approval_id = create_approval("Connection Comment", comment)
        send_approval(int(chat_id), "Connection Comment", approval_id, comment)
        return

    send_text(int(chat_id), "Unknown command. Use /help.")


def process_callback(callback: dict[str, Any]) -> None:
    from_user = callback.get("from", {})
    callback_id = str(callback.get("id", ""))
    user_id = from_user.get("id")

    if user_id is None or not verify_admin(int(user_id)):
        answer_callback(callback_id, "Not authorized.")
        return

    data = str(callback.get("data", ""))
    action, _, approval_id = data.partition(":")
    status = {
        "approve": "approved",
        "reject": "rejected",
    }.get(action)

    if not status:
        answer_callback(callback_id, "Unknown action.")
        return

    row = resolve_approval(approval_id.upper(), status)
    if not row:
        answer_callback(callback_id, "Already resolved or invalid.")
        return

    answer_callback(
        callback_id,
        "Approved." if status == "approved" else "Rejected.",
    )

    message = callback.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    if chat_id:
        if status == "approved":
            send_text(
                int(chat_id),
                (
                    f"Approved {approval_id.upper()}.\n\n"
                    "Continue with the LinkedIn action manually."
                ),
            )
        else:
            send_text(int(chat_id), f"Rejected {approval_id.upper()}.")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "telegram-control"}


@app.post("/webhook")
async def telegram_webhook(request: Request) -> dict[str, bool]:
    secret = _env("TELEGRAM_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(status_code=500, detail="TELEGRAM_WEBHOOK_SECRET is not configured.")

    received_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if received_secret != secret:
        raise HTTPException(status_code=403, detail="Invalid Telegram webhook secret.")

    payload = await request.json()

    try:
        callback = payload.get("callback_query")
        if callback:
            process_callback(callback)

        message = payload.get("message")
        if message:
            process_message(message)
    except Exception as exc:
        # Do not expose secrets; Telegram will retry unsuccessful webhook calls.
        message = payload.get("message") or {}
        chat_id = message.get("chat", {}).get("id")
        if chat_id:
            try:
                send_text(int(chat_id), f"Command failed: {exc}")
            except Exception:
                pass

    return {"received": True}
