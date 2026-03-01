import json
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id, get_db
from app.models.audit import LLMAuditLog
from app.models.consent import Consent
from app.providers.factory import get_provider
from app.schemas.chat import ChatRequest, ChatResult
from app.services.context_builder import build_user_context
from app.services.safety_service import detect_safety_flags, emergency_template
from app.utils.hash import context_hash

router = APIRouter()


def _check_consent(db: Session, user_id: str) -> None:
    consent = db.execute(select(Consent).where(Consent.user_id == user_id)).scalars().first()
    if consent is None or not consent.allow_ai_chat:
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "AI_CONSENT_REQUIRED",
                "message": "Please enable AI data processing consent in settings",
            },
        )


def _save_audit(
    db: Session,
    user_id: str,
    provider: str,
    model: str,
    latency_ms: int,
    used_context: dict,
    meta: dict,
) -> None:
    log = LLMAuditLog(
        user_id=user_id,
        provider=provider,
        model=model,
        latency_ms=latency_ms,
        prompt_tokens=None,
        completion_tokens=None,
        context_hash=context_hash(used_context),
        meta=meta,
    )
    db.add(log)
    db.commit()


@router.post("", response_model=ChatResult)
def chat(payload: ChatRequest, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    _check_consent(db, user_id)

    flags = detect_safety_flags(payload.message)
    context = build_user_context(db, user_id)

    if "emergency_symptom" in flags:
        answer = ChatResult(
            answer_markdown=emergency_template(),
            confidence=1.0,
            followups=["如果你愿意，我可以帮你整理就医时要描述的关键信息。"],
            safety_flags=flags,
            used_context=context,
        )
        _save_audit(
            db,
            user_id,
            provider="policy",
            model="emergency-template",
            latency_ms=0,
            used_context=context,
            meta={"message": payload.message, "safety_flags": flags},
        )
        return answer

    provider = get_provider()
    t0 = time.perf_counter()
    result = provider.generate_text(context, payload.message)
    latency_ms = int((time.perf_counter() - t0) * 1000)

    _save_audit(
        db,
        user_id,
        provider=provider.provider_name,
        model=provider.text_model,
        latency_ms=latency_ms,
        used_context=context,
        meta={"message": payload.message, "safety_flags": flags},
    )

    return ChatResult(
        answer_markdown=result.answer_markdown,
        confidence=result.confidence,
        followups=result.followups,
        safety_flags=flags + result.safety_flags,
        used_context=context,
    )


@router.post("/stream")
def chat_stream(payload: ChatRequest, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    _check_consent(db, user_id)

    flags = detect_safety_flags(payload.message)
    context = build_user_context(db, user_id)

    if "emergency_symptom" in flags:
        result = {
            "answer_markdown": emergency_template(),
            "confidence": 1.0,
            "followups": ["如果你愿意，我可以帮你整理就医时要描述的关键信息。"],
            "safety_flags": flags,
            "used_context": context,
        }

        _save_audit(
            db,
            user_id,
            provider="policy",
            model="emergency-template",
            latency_ms=0,
            used_context=context,
            meta={"message": payload.message, "safety_flags": flags, "stream": True},
        )

        def emergency_gen():
            yield f"data: {json.dumps({'type': 'done', 'result': result}, ensure_ascii=False)}\n\n"

        return StreamingResponse(emergency_gen(), media_type="text/event-stream")

    provider = get_provider()

    def event_stream():
        started = time.perf_counter()
        emitted_parts: list[str] = []
        for chunk in provider.stream_text(context, payload.message):
            emitted_parts.append(chunk)
            yield f"data: {json.dumps({'type': 'token', 'delta': chunk}, ensure_ascii=False)}\n\n"

        final_text = "".join(emitted_parts).strip()
        latency_ms = int((time.perf_counter() - started) * 1000)

        _save_audit(
            db,
            user_id,
            provider=provider.provider_name,
            model=provider.text_model,
            latency_ms=latency_ms,
            used_context=context,
            meta={"message": payload.message, "safety_flags": flags, "stream": True},
        )

        payload_done = {
            "answer_markdown": final_text or "(empty response)",
            "confidence": 0.85,
            "followups": [],
            "safety_flags": flags,
            "used_context": context,
        }
        yield f"data: {json.dumps({'type': 'done', 'result': payload_done}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/history")
def history(thread_id: str):
    _ = thread_id
    return []
