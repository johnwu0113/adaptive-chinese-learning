import json
import re
from typing import Any, Dict, Optional

import requests

from .config import settings


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    candidate = text.strip()
    candidate = re.sub(r"```json\s*", "", candidate, flags=re.IGNORECASE)
    candidate = re.sub(r"```\s*$", "", candidate)
    candidate = candidate.strip()
    if not candidate:
        return None
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", candidate, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
        return None


def _fallback_diagnosis(turn1: str, turn2: str) -> Dict[str, Any]:
    text = f"{turn1} {turn2}".strip()
    grammar_errors = 0
    for pattern in [
        r"\b(it|they|we|you)\s+help\b",
        r"\b(i|he|she|they)\s+go\b",
        r"\b(i|we|they)\s+am\b",
        r"\b(I|you|we|they)\s+is\b",
    ]:
        grammar_errors += len(re.findall(pattern, text, flags=re.IGNORECASE))
    tokens = re.findall(r"\b[a-zA-Z]+\b", text)
    vocab_score = min(100, max(25, 35 + len(set(tokens)) * 2 + len(tokens) // 3))
    grammar_score = max(20, 82 - grammar_errors * 18)
    fluency_score = min(100, max(25, 40 + len(tokens) // 2 - grammar_errors * 6))
    overall = int(round((vocab_score + grammar_score + fluency_score) / 3))
    level = 4 if overall >= 80 else 3 if overall >= 65 else 2 if overall >= 50 else 1
    return {
        "level": level,
        "confidence": 0.8,
        "breakdown": {
            "vocab": int(round(vocab_score)),
            "grammar": int(round(grammar_score)),
            "fluency": int(round(fluency_score)),
        },
        "notes": "文法結構仍較不穩定，建議加強動詞時態與句型練習。",
    }


def _fallback_plan(diagnosis: Dict[str, Any], teacher_input: Optional[str]) -> Dict[str, Any]:
    level = diagnosis.get("level", 2)
    grammar = diagnosis.get("breakdown", {}).get("grammar", 50)
    base = (
        "先從基礎句型練習開始，固定每天練習 3 個核心句型，例如『I went to…』『It helps me…』，"
        "再用簡短句子重述自己的想法。"
    )
    if teacher_input:
        base += f" 教師補充：{teacher_input}."
    if grammar < 50 or level <= 2:
        reasoning = "語法弱點明顯，適合降低難度並回到核心語法重建。"
    elif level >= 4:
        reasoning = "學生已具備中高階基礎，應優先提升表達深度與連貫性。"
    else:
        reasoning = "學生已具備穩定基礎，但需提升句型準確性與表達完整度。"
    return {"suggestion": base, "reasoning": reasoning}


class LLMService:
    def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        if settings.use_mock_llm or not settings.has_real_llm:
            if "診斷" in system_prompt or "level" in system_prompt:
                return _fallback_diagnosis(user_prompt.split("學生發言：")[-1], "")
            return _fallback_plan({"level": 2, "breakdown": {"grammar": 46}}, None)

        url = settings.openai_base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        }
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            parsed = _extract_json(content)
            if parsed:
                return parsed
        except Exception:
            pass

        if "診斷" in system_prompt or "level" in system_prompt:
            return _fallback_diagnosis(user_prompt, "")
        return _fallback_plan({"level": 2, "breakdown": {"grammar": 46}}, None)


llm_service = LLMService()
