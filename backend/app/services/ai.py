from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI, OpenAIError

from app.config import settings


class AIServiceError(RuntimeError):
    """Base error for configured LLM calls."""


class AIConfigurationError(AIServiceError):
    """Raised when the LLM provider is not configured enough to call."""


class AIResponseError(AIServiceError):
    """Raised when the LLM provider returns unusable content."""


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _api_key() -> str | None:
    return _blank_to_none(settings.llm_api_key) or _blank_to_none(settings.openai_api_key)


def _base_url() -> str | None:
    return _blank_to_none(settings.llm_base_url) or _blank_to_none(settings.openai_base_url)


def _model_fast() -> str:
    return _blank_to_none(settings.llm_model_fast) or settings.openai_model_fast


def _model_smart() -> str:
    return _blank_to_none(settings.llm_model_smart) or settings.openai_model_smart


def _client() -> OpenAI | None:
    if settings.apgl_mock_ai:
        return None
    api_mode = _blank_to_none(settings.llm_api_mode) or "chat_completions"
    if api_mode != "chat_completions":
        raise AIConfigurationError("Only LLM_API_MODE=chat_completions is supported.")

    api_key = _api_key()
    if not api_key:
        raise AIConfigurationError(
            "LLM_API_KEY is required when APGL_MOCK_AI=false. "
            "Set LLM_API_KEY in .env, or set APGL_MOCK_AI=true for local mock output."
        )

    base_url = _base_url()
    if _blank_to_none(settings.llm_api_key) and not base_url:
        raise AIConfigurationError(
            "LLM_BASE_URL is required for third-party OpenAI-compatible providers. "
            "Use the provider's /v1 base URL, or use OPENAI_API_KEY for official OpenAI."
        )

    kwargs: dict[str, str] = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAI(**kwargs)


def _json_from_text(text: str) -> dict[str, Any] | None:
    cleaned = text.strip()
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.S | re.I).strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.S)
    if fenced:
        cleaned = fenced.group(1).strip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        for match in re.finditer(r"\{", cleaned):
            try:
                value, _ = decoder.raw_decode(cleaned[match.start() :])
                break
            except json.JSONDecodeError:
                continue
        else:
            return None
    return value if isinstance(value, dict) else None


def _response_json(model: str, system: str, user: str) -> dict[str, Any] | None:
    client = _client()
    if client is None:
        return None
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
    except OpenAIError as exc:
        raise AIServiceError(f"LLM request failed: {exc}") from exc
    except Exception as exc:
        raise AIServiceError(f"LLM request failed: {exc}") from exc

    if not response.choices:
        raise AIResponseError("LLM returned no choices.")

    content = response.choices[0].message.content
    if isinstance(content, list):
        text = "".join(str(part) for part in content)
    else:
        text = content or ""

    parsed = _json_from_text(text)
    if parsed is None:
        raise AIResponseError("LLM response was not valid JSON.")
    return parsed


def _fallback_grade(prompt: str, expected: str, submitted: str) -> dict[str, Any]:
    expected_words = {word.lower() for word in re.findall(r"[A-Za-z]{4,}", expected)}
    submitted_words = {word.lower() for word in re.findall(r"[A-Za-z]{4,}", submitted)}
    overlap = len(expected_words & submitted_words)
    is_correct = overlap >= max(1, min(3, len(expected_words) // 3))
    feedback = (
        "Good answer. You captured the core idea."
        if is_correct
        else f"Review the expected idea: {expected}"
    )
    return {"is_correct": is_correct, "feedback": feedback}


def _fallback_plan(title: str, goal: str, source_excerpt: str | None = None) -> dict[str, Any]:
    context = source_excerpt or goal
    return {
        "knowledge_points": [
            {
                "name": f"{title} learning objective",
                "explanation": f"Clarify what '{title}' is for, what you can do today, and what success should look like.",
            },
            {
                "name": f"{title} core concepts",
                "explanation": f"Identify the essential concepts, terms, and examples behind: {context[:180]}",
            },
            {
                "name": f"{title} practice loop",
                "explanation": "Use short exercises, feedback, mistakes, and review to turn knowledge into usable skill.",
            },
        ],
        "lessons": [
            {
                "title": f"Orient yourself in {title}",
                "summary": "Define the target outcome, current baseline, and first useful practice step.",
                "content": (
                    f"Your goal is: {goal}\n\n"
                    f"Start by naming why {title} matters to you, which parts are unfamiliar, "
                    "and what a small successful practice result would look like."
                ),
                "quiz": [
                    {
                        "question_type": "short_answer",
                        "prompt": f"What concrete outcome do you want from learning {title}?",
                        "answer": "A specific outcome with a clear use case.",
                        "explanation": "A clear outcome helps the AI tutor choose better lessons and practice.",
                    }
                ],
            },
            {
                "title": f"Build the {title} concept map",
                "summary": "Study the smallest useful set of concepts before practicing.",
                "content": (
                    f"List the key {title} concepts, restate each one in your own words, "
                    "then connect each concept to a concrete example or use case."
                ),
                "quiz": [
                    {
                        "question_type": "short_answer",
                        "prompt": f"Explain one core {title} concept in your own words.",
                        "answer": "A correct explanation should be concise and include an example.",
                        "explanation": "Self-explanation exposes shallow understanding quickly.",
                    }
                ],
            },
            {
                "title": f"Practice and review {title}",
                "summary": "Use feedback and spaced review to make the learning stick.",
                "content": (
                    f"Complete a small {title} exercise, compare your answer with feedback, "
                    "and schedule review for weak points."
                ),
                "quiz": [
                    {
                        "question_type": "short_answer",
                        "prompt": "Why does reviewing mistakes improve learning?",
                        "answer": "It targets weak points and strengthens recall over time.",
                        "explanation": "Mistake-focused review makes practice adaptive instead of repetitive.",
                    }
                ],
            },
        ],
    }


def generate_skill_plan(title: str, goal: str, current_level: str | None) -> dict[str, Any]:
    if settings.apgl_mock_ai:
        return _fallback_plan(title, goal)

    system = (
        "You are an AI private tutor. Return only JSON with keys "
        "knowledge_points and lessons. Each lesson must include title, summary, content, "
        "and quiz. Each quiz item must include question_type, prompt, answer, explanation. "
        "Use the same language as the learner's goal."
    )
    user = (
        f"Create a concise MVP learning path.\nTitle: {title}\nGoal: {goal}\n"
        f"Current level: {current_level or 'unknown'}\nReturn 3 lessons and 3-6 knowledge points."
    )
    return _response_json(_model_smart(), system, user)


def generate_material_plan(title: str, goal: str, chunks: list[str]) -> dict[str, Any]:
    if settings.apgl_mock_ai:
        excerpt = "\n\n".join(chunks[:3])[:6000]
        return _fallback_plan(title, goal, excerpt)

    excerpt = "\n\n".join(chunks[:3])[:6000]
    system = (
        "You convert learning materials into guided study plans. Return only JSON with keys "
        "knowledge_points and lessons. Lessons must be grounded in the supplied material. "
        "Use the same language as the learner's goal or material."
    )
    user = (
        f"Project title: {title}\nGoal: {goal}\nMaterial excerpt:\n{excerpt}\n\n"
        "Return 3 lessons, 3-8 knowledge points, and one quiz item per lesson."
    )
    return _response_json(_model_fast(), system, user)


def grade_answer(prompt: str, expected: str, submitted: str) -> dict[str, Any]:
    if not submitted.strip():
        return {"is_correct": False, "feedback": "Please provide an answer."}
    if settings.apgl_mock_ai:
        return _fallback_grade(prompt, expected, submitted)

    system = (
        "You grade short learning answers. Return only JSON with keys "
        "is_correct and feedback."
    )
    user = (
        f"Question: {prompt}\nExpected answer: {expected}\nLearner answer: {submitted}\n"
        "Mark correct only if the core idea is present."
    )
    data = _response_json(_model_smart(), system, user)
    if data and isinstance(data.get("is_correct"), bool):
        return {
            "is_correct": data["is_correct"],
            "feedback": str(data.get("feedback") or ""),
        }
    raise AIResponseError("LLM grading response must include a boolean is_correct value.")
