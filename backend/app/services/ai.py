from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI

from app.config import settings


def _client() -> OpenAI | None:
    if settings.apgl_mock_ai or not settings.openai_api_key:
        return None
    return OpenAI(api_key=settings.openai_api_key)


def _json_from_text(text: str) -> dict[str, Any] | None:
    cleaned = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.S)
    if fenced:
        cleaned = fenced.group(1).strip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _response_json(model: str, system: str, user: str) -> dict[str, Any] | None:
    client = _client()
    if client is None:
        return None
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return _json_from_text(response.output_text)


def _fallback_plan(title: str, goal: str, source_excerpt: str | None = None) -> dict[str, Any]:
    context = source_excerpt or goal
    return {
        "knowledge_points": [
            {
                "name": "Learning goal",
                "explanation": f"Clarify what '{title}' is for and what success looks like.",
            },
            {
                "name": "Core concepts",
                "explanation": f"Identify the essential concepts in: {context[:180]}",
            },
            {
                "name": "Practice and feedback",
                "explanation": "Use short exercises, feedback, and review to build durable skill.",
            },
        ],
        "lessons": [
            {
                "title": f"Map the goal: {title}",
                "summary": "Turn the learning goal into a small, testable path.",
                "content": (
                    f"Your goal is: {goal}\n\n"
                    "Start by naming the outcome, the current baseline, and the first useful practice task."
                ),
                "quiz": [
                    {
                        "question_type": "short_answer",
                        "prompt": "What is the concrete outcome you want from this learning project?",
                        "answer": "A specific outcome with a clear use case.",
                        "explanation": "A clear outcome helps the AI tutor choose better lessons and practice.",
                    }
                ],
            },
            {
                "title": "Learn the core concepts",
                "summary": "Study the smallest useful set of ideas before practicing.",
                "content": (
                    "Read the key concepts, restate them in your own words, then connect each concept to an example."
                ),
                "quiz": [
                    {
                        "question_type": "short_answer",
                        "prompt": "Explain one core concept in your own words.",
                        "answer": "A correct explanation should be concise and include an example.",
                        "explanation": "Self-explanation exposes shallow understanding quickly.",
                    }
                ],
            },
            {
                "title": "Practice, correct, and review",
                "summary": "Use feedback and spaced review to make the learning stick.",
                "content": (
                    "Complete a small exercise, compare your answer with feedback, and schedule review for weak points."
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
    system = (
        "You are an AI private tutor. Return only JSON with keys "
        "knowledge_points and lessons. Each lesson must include title, summary, content, "
        "and quiz. Each quiz item must include question_type, prompt, answer, explanation."
    )
    user = (
        f"Create a concise MVP learning path.\nTitle: {title}\nGoal: {goal}\n"
        f"Current level: {current_level or 'unknown'}\nReturn 3 lessons and 3-6 knowledge points."
    )
    data = _response_json(settings.openai_model_smart, system, user)
    return data or _fallback_plan(title, goal)


def generate_material_plan(title: str, goal: str, chunks: list[str]) -> dict[str, Any]:
    excerpt = "\n\n".join(chunks[:3])[:6000]
    system = (
        "You convert learning materials into guided study plans. Return only JSON with keys "
        "knowledge_points and lessons. Lessons must be grounded in the supplied material."
    )
    user = (
        f"Project title: {title}\nGoal: {goal}\nMaterial excerpt:\n{excerpt}\n\n"
        "Return 3 lessons, 3-8 knowledge points, and one quiz item per lesson."
    )
    data = _response_json(settings.openai_model_fast, system, user)
    return data or _fallback_plan(title, goal, excerpt)


def grade_answer(prompt: str, expected: str, submitted: str) -> dict[str, Any]:
    if not submitted.strip():
        return {"is_correct": False, "feedback": "Please provide an answer."}

    system = (
        "You grade short learning answers. Return only JSON with keys "
        "is_correct and feedback."
    )
    user = (
        f"Question: {prompt}\nExpected answer: {expected}\nLearner answer: {submitted}\n"
        "Mark correct only if the core idea is present."
    )
    data = _response_json(settings.openai_model_smart, system, user)
    if data and isinstance(data.get("is_correct"), bool):
        return {
            "is_correct": data["is_correct"],
            "feedback": str(data.get("feedback") or ""),
        }

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

