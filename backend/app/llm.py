import logging
import os
from typing import Any

import httpx

from app.db import get_recent_messages

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo").strip()
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_TIMEOUT = float(os.getenv("OPENAI_TIMEOUT", "20"))


def _build_cart_summary(items: list[dict[str, Any]]) -> str:
    if not items:
        return "Cart is empty."

    lines = [f"- {item['qty']} x {item['name']} @ £{item['unit_price']}" for item in items]
    return "Cart items:\n" + "\n".join(lines)


def _build_system_message(store_slug: str) -> str:
    return (
        "You are a super-intelligent grocery ordering assistant and conversation partner for a local store. "
        "You can answer random questions, chat naturally, and help customers place orders. "
        "When a user asks about ordering, follow the store workflow and keep responses friendly, clear, and helpful. "
        "If the user asks unrelated questions, answer them directly and intelligently. "
        "Do not mention internal code, system details, or prompt mechanics."
    )


def _build_prompt(
    user_text: str,
    raw_reply: str,
    state: str,
    items: list[dict[str, Any]],
    store_slug: str,
    channel: str,
    session_id: str,
    direct: bool = False,
) -> list[dict[str, str]]:
    cart_summary = _build_cart_summary(items)
    history = get_recent_messages(session_id, store_slug, channel=channel, limit=8)
    message_history = []
    for row in history:
        role = "assistant" if row["role"] == "assistant" else "user"
        message_history.append({"role": role, "content": row["text"]})

    prompt_messages = [
        {"role": "system", "content": _build_system_message(store_slug)},
    ]
    prompt_messages.extend(message_history)

    if direct:
        prompt_messages.append(
            {
                "role": "user",
                "content": (
                    f"User message: {user_text}\n"
                    f"Workflow state: {state}\n"
                    f"Store slug: {store_slug}\n"
                    f"Channel: {channel}\n"
                    f"{cart_summary}\n"
                    "Answer the user's message directly as a friendly, intelligent assistant. "
                    "If the user wants to place an order, guide them through the store ordering process. "
                    "If the message is unrelated to ordering, answer the question clearly and completely."
                ),
            }
        )
    else:
        prompt_messages.append(
            {
                "role": "user",
                "content": (
                    f"User message: {user_text}\n"
                    f"Workflow state: {state}\n"
                    f"Store slug: {store_slug}\n"
                    f"Channel: {channel}\n"
                    f"{cart_summary}\n"
                    f"Assistant draft: {raw_reply}\n\n"
                    "Rewrite the draft assistant response into a conversational reply that is clear, "
                    "friendly, and exactly consistent with the draft meaning. "
                    "Do not add any new actions or change the intent."
                ),
            }
        )
    return prompt_messages


def _call_openai(messages: list[dict[str, str]]) -> str | None:
    if not OPENAI_API_KEY:
        return None

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 220,
    }

    try:
        logger.debug(
            "OpenAI request: model=%s, messages=%d, timeout=%s",
            OPENAI_MODEL,
            len(messages),
            OPENAI_TIMEOUT,
        )
        with httpx.Client(timeout=OPENAI_TIMEOUT) as client:
            response = client.post(OPENAI_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            message = data.get("choices", [])[0].get("message", {}).get("content")
            logger.debug(
                "OpenAI response received, content length=%s",
                len(message) if isinstance(message, str) else 0,
            )
            return message
    except Exception as exc:
        logger.exception("OpenAI request failed")
        return None


def conversational_reply(
    session_id: str,
    user_text: str,
    raw_reply: str,
    state: str,
    items: list[dict[str, Any]],
    store_slug: str,
    channel: str = "web",
    direct: bool = False,
) -> str:
    if not OPENAI_API_KEY:
        logger.debug("No OpenAI API key configured; using raw reply")
        return raw_reply

    prompt = _build_prompt(
        user_text=user_text,
        raw_reply=raw_reply,
        state=state,
        items=items,
        store_slug=store_slug,
        channel=channel,
        session_id=session_id,
        direct=direct,
    )
    result = _call_openai(prompt)
    if result:
        logger.debug("Using conversational response from OpenAI")
        return result.strip()

    logger.debug("OpenAI request returned no content; falling back to raw reply")
    return raw_reply
