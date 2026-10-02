from __future__ import annotations

import os
import sys

import requests

API = "https://api.telegram.org"


def env(name: str) -> str:
    return os.getenv(name, "").strip()


def call(method: str, payload: dict) -> dict:
    token = env("TELEGRAM_BOT_TOKEN")
    if not token:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set.")

    response = requests.post(
        f"{API}/bot{token}/{method}",
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise SystemExit(data.get("description", "Telegram API request failed."))
    return data


def main() -> None:
    webhook_url = env("TELEGRAM_WEBHOOK_URL")
    secret = env("TELEGRAM_WEBHOOK_SECRET")

    if not webhook_url:
        raise SystemExit(
            "Set TELEGRAM_WEBHOOK_URL, for example: "
            "https://your-service.onrender.com/webhook"
        )
    if not secret:
        raise SystemExit("Set TELEGRAM_WEBHOOK_SECRET.")

    if not webhook_url.startswith("https://"):
        raise SystemExit("TELEGRAM_WEBHOOK_URL must use HTTPS.")

    commands = [
        {"command": "help", "description": "Show bot commands"},
        {"command": "id", "description": "Show your Telegram user ID"},
        {"command": "status", "description": "Show service configuration status"},
        {"command": "trend", "description": "Generate a current-news LinkedIn draft"},
        {"command": "comment", "description": "Generate a builder-style comment"},
        {"command": "approve", "description": "Approve a generated draft"},
        {"command": "reject", "description": "Reject a generated draft"},
    ]

    webhook = call(
        "setWebhook",
        {
            "url": webhook_url,
            "secret_token": secret,
            "allowed_updates": ["message", "callback_query"],
        },
    )
    menu = call("setMyCommands", {"commands": commands})

    bot = call("getMe")
    username = bot.get("result", {}).get("username", "unknown")

    print(f"Bot: @{username}")
    print(f"Webhook configured: {webhook.get('ok', False)}")
    print(f"Command menu configured: {menu.get('ok', False)}")


if __name__ == "__main__":
    main()
