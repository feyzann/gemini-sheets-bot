"""Chat endpoint handler."""

import time
import uuid
from typing import Dict, Any
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from loguru import logger

from app.models.request import ChatRequest
from app.models.response import ChatResponse, ErrorResponse, Reference
from app.sheets.client import sheets_client
from app.people.find import PersonFinder
from app.llm.gemini import gemini_client
from app.core.config import get_settings

settings = get_settings()

router = APIRouter(
    prefix="/api/v1",
    tags=["chat"],
    responses={500: {"model": ErrorResponse}}
)

def create_not_found_response(user_phone: str | None = None, user_name: str | None = None) -> ChatResponse:
    msg = ("Numaranızla eşleşen kayıt bulamadım; ad-soyad ve okul/bölüm bilgisini paylaşır mısınız?"
           if user_phone else
           "Size yardımcı olabilmem için ad-soyad ve okul/bölüm bilgisini paylaşır mısınız?")
    return ChatResponse(
        answer_text=msg,
        intent="genel",
        confidence=0.3,
        references=[],
        meta={"locale_used": settings.default_locale, "person_not_found": True}
    )

def create_error_response() -> ErrorResponse:
    return ErrorResponse(
        answer_text="Şu an teknik bir sorun oluştu. Lütfen daha sonra tekrar dener misiniz?",
        intent="genel",
        confidence=0.0,
        references=[]
    )

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse | JSONResponse:
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    logger.info(f"[{request_id}] Chat request: {request.message[:100]}...")

    try:
        # 1) Sheets
        t0 = time.time()
        people_data = sheets_client.get_people_data()
        t_sheets = (time.time() - t0) * 1000
        logger.info(f"[{request_id}] People rows: {len(people_data)} in {t_sheets:.1f}ms")

        # 2) Find person
        finder = PersonFinder(people_data)
        user_phone = request.user.phone if request.user else None
        user_name  = request.user.name if request.user else None
        user_locale = request.user.locale if request.user else None
        if not user_name:
            user_name = finder.extract_name_from_message(request.message)

        person = finder.find_person(user_phone, user_name)
        if not person:
            logger.info(f"[{request_id}] Person not found (phone={user_phone}, name={user_name})")
            return create_not_found_response(user_phone, user_name)

        # 3) Facts & locale
        facts = finder.build_facts(person)
        profile_text = facts.get("profile_text", "")
        locale = user_locale or facts.get("locale") or settings.default_locale
        logger.info(f"[{request_id}] Found: {facts.get('full_name','?')} (id={facts.get('person_id','?')})")

        # 4) LLM
        t1 = time.time()
        response = gemini_client.generate_response(
            message=request.message,
            facts=facts,
            profile_text=profile_text,
            locale=locale
        )
        t_llm = (time.time() - t1) * 1000

        # 5) Ensure People reference (avoid duplicates)
        if facts.get("person_id"):
            has_people_ref = any(
                (r.source == "People" and r.person_id == facts["person_id"])
                for r in (response.references or [])
            )
            if not has_people_ref:
                response.references.append(Reference(source="People", person_id=facts["person_id"]))

        # 6) Meta enrich
        match_method = "phone" if user_phone else ("name" if user_name else "none")
        response.meta = {**(response.meta or {}),
                         "locale_used": response.meta.get("locale_used", locale) if response.meta else locale,
                         "request_id": request_id,
                         "timing_ms": {"sheets": round(t_sheets,1), "llm": round(t_llm,1), "total": round((time.time()-start_time)*1000,1)},
                         "match": match_method}

        logger.info(f"[{request_id}] Done intent={response.intent} conf={response.confidence} "
                    f"(sheets {t_sheets:.1f}ms, llm {t_llm:.1f}ms)")
        return response

    except Exception as e:
        logger.error(f"[{request_id}] Chat endpoint error: {e}")
        err = create_error_response()
        return JSONResponse(status_code=500, content=err.model_dump())
