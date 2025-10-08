# app/llm/gemini.py
"""Gemini LLM client with structured output (final)."""

from __future__ import annotations
import json
from typing import Dict, Any, Optional, List

import google.generativeai as genai
from loguru import logger

from app.core.config import get_settings
from app.models.response import ChatResponse, Reference

S = get_settings()
genai.configure(api_key=S.gemini_api_key)


def _response_schema() -> Dict[str, Any]:
    # person_id'yi da zorunlu yaptık → Pydantic Reference ile uyumlu
    return {
        "type": "object",
        "properties": {
            "answer_text": {"type": "string", "description": "Yanıt (TR)"},
            "intent": {"type": "string", "description": "genel/bilgi/randevu/..."},
            "confidence": {"type": "number", "description": "0..1"},
            "references": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "person_id": {"type": "string"}
                    },
                    "required": ["source", "person_id"]
                }
            },
            "meta": {"type": "object", "properties": {"locale_used": {"type": "string"}}}
        },
        "required": ["answer_text", "intent", "confidence", "references"]
    }


def _system_prompt(locale: str) -> str:
    return (
        "Sen kişiselleştirilmiş yanıt üreten bir yardımcısın.\n\n"
        "Öncelik sırası:\n"
        "1) FACTS (tablodaki kesin bilgi) — bu bilgiler kesin kabul edilir\n"
        "2) PROFILE_TEXT — sadece zenginleştirme içindir\n"
        "3) Kullanıcı mesajı — bağlam için\n\n"
        "Çelişki durumunda FACTS kazanır. Kısa, nazik, net yaz. Bilgi yoksa uydurma; eksik bilgi iste.\n"
        f"Yanıt dilini {locale} olarak kullan.\n"
        "Yanıtı verdiğim JSON şemasına UYGUN döndür."
    )


def _parts(message: str, facts: Dict[str, Any], profile_text: str, locale: str) -> List[Dict[str, Any]]:
    parts: List[Dict[str, Any]] = [
        {"role": "user", "parts": [{"text": f"LOCALE: {locale}"}]},
        {"role": "user", "parts": [{"text": f"MESSAGE:\n{message}"}]},
        {"role": "user", "parts": [{"text": f"FACTS JSON:\n{json.dumps(facts, ensure_ascii=False)}"}]},
    ]
    if profile_text:
        parts.append({"role": "user", "parts": [{"text": f"PROFILE_TEXT:\n{profile_text}"}]})
    return parts


class GeminiClient:
    """Gemini 2.5 Flash client with structured JSON output."""

    def __init__(self) -> None:
        # Model nesnesini her çağrıda system_instruction ile kuracağız (locale'e göre)
        # Bu nedenle burada kalıcı bir model tutmuyoruz.
        pass

    def _fallback(self, locale: str, person_id: Optional[str]) -> ChatResponse:
        return ChatResponse(
            answer_text="Şu an teknik bir sorun oluştu. Lütfen daha sonra tekrar dener misiniz?",
            intent="genel",
            confidence=0.0,
            references=([Reference(source="People", person_id=person_id)] if person_id else []),
            meta={"locale_used": locale, "fallback": True},
        )

    def generate_response(
        self,
        message: str,
        facts: Dict[str, Any],
        profile_text: str = "",
        locale: str = "tr-TR",
    ) -> ChatResponse:
        try:
            model = genai.GenerativeModel(
                model_name=S.gemini_model,
                system_instruction=_system_prompt(locale),
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    response_schema=_response_schema(),
                    temperature=0.3,              # Daha tutarlı cevap için düşük sıcaklık
                    max_output_tokens=512,
                ),
            )
            resp = model.generate_content(
                contents=_parts(message, facts, profile_text, locale)
            )

            # Bazı SDK sürümlerinde .text dolu olur; güvenlik için candidates üzerinden de deneyelim
            raw = resp.text
            if not raw and getattr(resp, "candidates", None):
                cand = resp.candidates[0]
                if cand and cand.content and cand.content.parts:
                    raw = cand.content.parts[0].text

            if not raw:
                logger.warning("Empty response from Gemini")
                return self._fallback(locale, facts.get("person_id"))

            data = json.loads(raw)

            # Zorunlu referanslar yoksa People'a bağla
            if not data.get("references"):
                data["references"] = [{"source": "People", "person_id": facts.get("person_id", "")}]

            # Meta zenginleştir
            meta = data.get("meta") or {}
            meta.setdefault("locale_used", locale)
            data["meta"] = meta

            # Pydantic ile doğrula
            return ChatResponse.model_validate(data)

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return self._fallback(locale, facts.get("person_id"))


# Tekil client
gemini_client = GeminiClient()
