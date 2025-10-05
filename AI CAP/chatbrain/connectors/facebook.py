from __future__ import annotations

import logging
import os
from typing import Any, Dict, Iterable, List, Optional

try:  # pragma: no cover - cho phép chạy test khi thiếu httpx
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore

from fastapi import APIRouter, HTTPException, Query, Response, status

router = APIRouter()

logger = logging.getLogger(__name__)

VERIFY_TOKEN = os.getenv("FB_VERIFY_TOKEN", "")
PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN", "")
USE_MEDIA = os.getenv("USE_MEDIA", "false").lower() in {"1", "true", "yes"}
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")
MESSAGE_ENDPOINT = os.getenv("CHATBRAIN_MESSAGE_URL", "http://127.0.0.1:8000/message")


@router.get("/webhook/facebook")
async def verify_webhook(
    hub_mode: str = Query(default=""),
    hub_challenge: str = Query(default=""),
    hub_verify_token: str = Query(default=""),
) -> Response:
    """Xác thực webhook với Facebook."""
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return Response(content=hub_challenge)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token không hợp lệ")


@router.post("/webhook/facebook")
async def handle_webhook(payload: Dict[str, Any]) -> Dict[str, str]:
    """Nhận sự kiện từ Facebook và chuyển tới lõi ChatBrain."""
    entries = payload.get("entry", [])
    for entry in entries:
        messaging_events = entry.get("messaging", [])
        for event in messaging_events:
            sender_id = _extract_sender(event)
            if not sender_id:
                continue
            text = _extract_message(event)
            if text is None:
                continue
            try:
                core_response = await _forward_to_core(sender_id, text)
            except Exception as exc:  # pragma: no cover - lỗi runtime khó tái hiện
                logger.exception("Lỗi gọi lõi ChatBrain: %s", exc)
                continue
            if not core_response:
                continue
            await _dispatch_response(sender_id, core_response)
    return {"status": "ok"}


async def _forward_to_core(session_id: str, message: str) -> Dict[str, Any]:
    if httpx is None:
        raise HTTPException(status_code=500, detail="Thiếu thư viện httpx")
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(MESSAGE_ENDPOINT, json={"session_id": session_id, "message": message})
        response.raise_for_status()
        return response.json()


async def _dispatch_response(recipient_id: str, response: Dict[str, Any]) -> None:
    reply_text = response.get("reply") or ""
    ui = response.get("ui") or {}
    buttons = _extract_buttons(ui)
    media_items = _extract_media(ui)

    if reply_text:
        await _send_text(recipient_id, reply_text, buttons)

    if USE_MEDIA and media_items:
        for item in media_items:
            await _send_media(recipient_id, item)


def _extract_buttons(ui: Dict[str, Any]) -> List[str]:
    buttons = ui.get("buttons", [])
    if not isinstance(buttons, list):
        return []
    result: List[str] = []
    for button in buttons:
        if isinstance(button, str) and button.strip():
            result.append(button.strip())
    return result[:11]


def _extract_media(ui: Dict[str, Any]) -> List[Dict[str, Any]]:
    media = ui.get("media", [])
    if not isinstance(media, Iterable) or isinstance(media, (str, bytes)):
        return []
    normalized: List[Dict[str, Any]] = []
    for item in media:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if not isinstance(url, str) or not url:
            continue
        media_type = str(item.get("type", "image") or "image")
        normalized.append(
            {
                "type": media_type,
                "url": _resolve_media_url(url),
                "alt": item.get("alt"),
            }
        )
    return normalized


async def _send_text(recipient_id: str, text: str, buttons: List[str]) -> None:
    payload: Dict[str, Any] = {
        "recipient": {"id": recipient_id},
        "message": {"text": text},
    }
    quick_replies = _build_quick_replies(buttons)
    if quick_replies:
        payload["message"]["quick_replies"] = quick_replies
    await _call_facebook(payload)


def _build_quick_replies(buttons: List[str]) -> List[Dict[str, str]]:
    replies: List[Dict[str, str]] = []
    for label in buttons[:11]:
        if not label:
            continue
        replies.append(
            {
                "content_type": "text",
                "title": label[:20],
                "payload": label,
            }
        )
    return replies


async def _send_media(recipient_id: str, media: Dict[str, Any]) -> None:
    attachment = {
        "type": media.get("type", "image"),
        "payload": {
            "url": media.get("url"),
            "is_reusable": False,
        },
    }
    alt_text = media.get("alt")
    if isinstance(alt_text, str) and alt_text.strip():
        attachment["payload"]["alt_text"] = alt_text.strip()
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"attachment": attachment},
    }
    await _call_facebook(payload)


async def _call_facebook(payload: Dict[str, Any]) -> None:
    if not PAGE_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="Thiếu FB_PAGE_ACCESS_TOKEN")
    if httpx is None:
        raise HTTPException(status_code=500, detail="Thiếu thư viện httpx")
    url = "https://graph.facebook.com/v17.0/me/messages"
    params = {"access_token": PAGE_ACCESS_TOKEN}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, params=params, json=payload)
        if response.status_code >= 400:
            logger.error("Gửi tin nhắn tới Facebook thất bại: %s", response.text)
            raise HTTPException(status_code=500, detail="Gửi tin nhắn tới Facebook thất bại")


def _extract_sender(event: Dict[str, Any]) -> Optional[str]:
    sender = event.get("sender", {})
    sender_id = sender.get("id")
    if isinstance(sender_id, str):
        return sender_id
    return None


def _extract_message(event: Dict[str, Any]) -> Optional[str]:
    message = event.get("message")
    if isinstance(message, dict):
        quick_reply = message.get("quick_reply")
        if isinstance(quick_reply, dict):
            payload = quick_reply.get("payload")
            if isinstance(payload, str):
                return payload
        text = message.get("text")
        if isinstance(text, str):
            return text
    postback = event.get("postback")
    if isinstance(postback, dict):
        payload = postback.get("payload")
        if isinstance(payload, str):
            return payload
    return None


def _resolve_media_url(url: str) -> str:
    if url.startswith("/") and PUBLIC_BASE_URL:
        return f"{PUBLIC_BASE_URL.rstrip('/')}{url}"
    return url
