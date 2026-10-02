from __future__ import annotations

import base64
import os
from typing import Any

import requests

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GNEWS_URL = "https://gnews.io/api/v4"


def get_secret(name: str, secrets: Any = None) -> str:
    if secrets is not None:
        try:
            value = secrets.get(name)
            if value:
                return str(value).strip()
        except Exception:
            pass
    return os.getenv(name, "").strip()


def fetch_gnews(
    api_key: str,
    query: str = "",
    category: str = "business",
    country: str = "in",
    language: str = "en",
    limit: int = 10,
) -> list[dict]:
    if not api_key:
        raise ValueError("GNEWS_API_KEY is not configured.")

    if query.strip():
        endpoint = f"{GNEWS_URL}/search"
        params = {
            "q": query.strip(),
            "lang": language,
            "country": country,
            "max": min(limit, 10),
            "sortby": "publishedAt",
            "apikey": api_key,
        }
    else:
        endpoint = f"{GNEWS_URL}/top-headlines"
        params = {
            "category": category,
            "lang": language,
            "country": country,
            "max": min(limit, 10),
            "apikey": api_key,
        }

    response = requests.get(endpoint, params=params, timeout=20)
    response.raise_for_status()
    payload = response.json()

    if payload.get("errors"):
        raise ValueError("; ".join(str(x) for x in payload["errors"]))

    return payload.get("articles", [])


def generate_with_openrouter(
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    model: str = "openrouter/free",
    use_reasoning: bool = True,
    image_bytes: bytes | None = None,
    image_mime: str = "image/jpeg",
) -> str:
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not configured.")

    user_content: str | list[dict[str, Any]] = user_prompt
    if image_bytes:
        encoded_image = base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:{image_mime};base64,{encoded_image}"
        user_content = [
            {"type": "text", "text": user_prompt},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]

    body: dict[str, Any] = {
        "model": model or "openrouter/free",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.4,
        "max_tokens": 900,
    }

    if use_reasoning:
        body["reasoning"] = {"enabled": True}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/mr-Arun-2006/linkedin_Automation",
        "X-Title": "LinkedIn Automation",
    }

    response = requests.post(
        OPENROUTER_URL,
        headers=headers,
        json=body,
        timeout=60,
    )

    if response.status_code == 400 and use_reasoning:
        body.pop("reasoning", None)
        response = requests.post(
            OPENROUTER_URL,
            headers=headers,
            json=body,
            timeout=60,
        )

    response.raise_for_status()
    payload = response.json()
    choices = payload.get("choices") or []

    if not choices:
        raise ValueError("OpenRouter returned no choices.")

    content = choices[0].get("message", {}).get("content")
    if not content:
        raise ValueError("OpenRouter returned an empty response.")

    return str(content).strip()


def format_news_for_ai(articles: list[dict], limit: int = 8) -> str:
    rows: list[str] = []

    for idx, article in enumerate(articles[:limit], start=1):
        source = article.get("source", {}).get("name", "Unknown source")
        title = article.get("title", "").strip()
        description = article.get("description", "").strip()
        published = article.get("publishedAt", "")
        url = article.get("url", "")

        rows.append(
            f"{idx}. {title}\n"
            f"Source: {source}\n"
            f"Published: {published}\n"
            f"Summary: {description}\n"
            f"URL: {url}"
        )

    return "\n\n".join(rows)
