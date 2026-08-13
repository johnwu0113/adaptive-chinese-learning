import re
from typing import Any, Dict, Optional

from .llm_service import llm_service


class StudentAgent:
    def __init__(self):
        self.role = "Student Agent"

    def build_student_context(self, turn1: str, turn2: str) -> Dict[str, Any]:
        combined = f"{turn1} {turn2}".strip()
        total_chars = len(combined)
        sentence_count = max(1, len(re.findall(r"[.!?]", combined)) + 1)
        grammar_mistakes = 0
        for pattern in [
            r"\b(it|they|we|you)\s+help\b",
            r"\b(i|he|she|they)\s+go\b",
            r"\b(i|we|they)\s+am\b",
            r"\b(I|you|we|they)\s+is\b",
        ]:
            grammar_mistakes += len(re.findall(pattern, combined, flags=re.IGNORECASE))
        frustration_index = min(
            0.95,
            max(0.15, 0.2 + (grammar_mistakes * 0.14) + max(0, (sentence_count - 2) * 0.08)),
        )
        return {
            "student_id": "student-demo-01",
            "frustration_index": round(frustration_index, 2),
            "turn_count": sentence_count,
            "total_chars": total_chars,
            "grammar_error_count": grammar_mistakes,
            "summary": "學生已提交兩輪語言練習內容，系統開始進行診斷與路徑規劃。",
        }


class DiagnosticAgent:
    def diagnose(self, turn1: str, turn2: str) -> Dict[str, Any]:
        system_prompt = (
            "你是語言能力診斷 Agent。根據學生的語言發言，輸出 JSON 格式："
            '{"level": 1-5, "confidence": 0.0-1.0, "breakdown": {"vocab": 0-100, "grammar": 0-100, "fluency": 0-100}, "notes": "簡短繁體中文說明"}'
        )
        user_prompt = f"學生發言：\n1. {turn1}\n2. {turn2}"
        result = llm_service.generate_json(system_prompt, user_prompt)
        if not isinstance(result, dict):
            result = {
                "level": 2,
                "confidence": 0.8,
                "breakdown": {"vocab": 60, "grammar": 50, "fluency": 55},
                "notes": "系統已回歸到本地判斷邏輯。",
            }
        breakdown = result.get("breakdown", {})
        result["breakdown"] = {
            "vocab": int(breakdown.get("vocab", 60)),
            "grammar": int(breakdown.get("grammar", 50)),
            "fluency": int(breakdown.get("fluency", 55)),
        }
        result["confidence"] = float(result.get("confidence", 0.8))
        result["level"] = int(result.get("level", 2))
        return result


class PlanningAgent:
    def __init__(self):
        self.role = "Planning Agent"

    def generate(self, diagnosis: Dict[str, Any], teacher_input: Optional[str] = None) -> Dict[str, Any]:
        system_prompt = (
            "你是語言學習規劃 Agent。依據診斷結果，產生對學生鼓勵且具體的繁體中文建議，"
            "輸出 JSON 格式：{'suggestion': '建議文字', 'reasoning': '規劃理由'}"
        )
        level = diagnosis.get("level", 2)
        grammar = diagnosis.get("breakdown", {}).get("grammar", 50)
        notes = diagnosis.get("notes", "")
        user_prompt = (
            f"診斷結果：等級 {level}，字彙 {diagnosis.get('breakdown', {}).get('vocab', 60)}，"
            f"文法 {grammar}，流暢度 {diagnosis.get('breakdown', {}).get('fluency', 50)}。"
            f"診斷備註：{notes}。"
            + (f"教師備註：{teacher_input}" if teacher_input else "")
        )
        result = llm_service.generate_json(system_prompt, user_prompt)
        if not isinstance(result, dict):
            return {"suggestion": "先從基礎句型練習開始，逐步提升語法正確度。", "reasoning": "維持穩定學習節奏。"}
        suggestion = result.get("suggestion") or "先從基礎句型練習開始，逐步提升語法正確度。"
        reasoning = result.get("reasoning") or "維持穩定學習節奏。"
        return {"suggestion": suggestion, "reasoning": reasoning}


class TeacherAgent:
    def evaluate(self, diagnosis: Dict[str, Any]) -> Dict[str, Any]:
        level = diagnosis.get("level", 2)
        grammar = diagnosis.get("breakdown", {}).get("grammar", 50)
        confidence = diagnosis.get("confidence", 0.7)
        high_risk = level <= 2 or grammar < 60 or confidence < 0.7
        if high_risk:
            return {
                "status": "needs_support",
                "summary": "學生語法與語句穩定性仍偏低，建議教師介入提供結構化練習。",
                "recommended_action": "安排微步距教學與詞句重建練習。",
                "level": level,
                "grammar_score": grammar,
            }
        return {
            "status": "monitor",
            "summary": "學生表現穩定，持續觀察即可。",
            "recommended_action": "維持現有節奏，持續追蹤進步。",
            "level": level,
            "grammar_score": grammar,
        }


class MASWorkflow:
    def __init__(self):
        self.student_agent = StudentAgent()
        self.diagnostic_agent = DiagnosticAgent()
        self.planning_agent = PlanningAgent()
        self.teacher_agent = TeacherAgent()

    def run(self, turn1: str, turn2: str):
        student_context = self.student_agent.build_student_context(turn1, turn2)
        diagnosis = self.diagnostic_agent.diagnose(turn1, turn2)
        plan = self.planning_agent.generate(diagnosis)
        teacher = self.teacher_agent.evaluate(diagnosis)
        return {
            "student_context": student_context,
            "diagnosis": diagnosis,
            "plan": plan,
            "teacher": teacher,
        }
