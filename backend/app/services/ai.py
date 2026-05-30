from __future__ import annotations

import json
import re
from collections.abc import Callable
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


def _json_from_text(
    text: str,
    expected_keys: set[str] | None = None,
    validator: Callable[[dict[str, Any]], bool] | None = None,
) -> dict[str, Any] | None:
    cleaned = text.strip()
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.S | re.I).strip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        found = _first_json_object(cleaned, expected_keys, validator)
        if found is not None:
            if _valid_payload(found, expected_keys, validator):
                return found
        for fenced in re.finditer(r"```(?:json)?\s*(.*?)```", cleaned, flags=re.S):
            candidate = fenced.group(1).strip()
            try:
                value = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            parsed = _expected_payload(value, expected_keys, validator) if isinstance(value, dict) else None
            if parsed is not None:
                return parsed
        return None
    return _expected_payload(value, expected_keys, validator) if isinstance(value, dict) else None


def _first_json_object(
    text: str,
    expected_keys: set[str] | None = None,
    validator: Callable[[dict[str, Any]], bool] | None = None,
) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text):
        try:
            value, _ = decoder.raw_decode(text[match.start() :])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            payload = _expected_payload(value, expected_keys, validator)
            if payload is not None:
                return payload
    return None


def _looks_like_expected_payload(value: dict[str, Any], expected_keys: set[str] | None = None) -> bool:
    expected = expected_keys or {
        "knowledge_points",
        "lessons",
        "learning_goal",
        "tutor_explanation",
        "question",
        "is_correct",
        "ok",
        "answer",
        "summary",
    }
    return bool(expected & set(value.keys()))


def _valid_payload(
    value: dict[str, Any],
    expected_keys: set[str] | None = None,
    validator: Callable[[dict[str, Any]], bool] | None = None,
) -> bool:
    if not _looks_like_expected_payload(value, expected_keys):
        return False
    return validator(value) if validator else True


def _expected_payload(
    value: dict[str, Any],
    expected_keys: set[str] | None = None,
    validator: Callable[[dict[str, Any]], bool] | None = None,
) -> dict[str, Any] | None:
    if _valid_payload(value, expected_keys, validator):
        return value
    for key in ("data", "result", "response", "content", "json"):
        nested = value.get(key)
        if isinstance(nested, dict) and _valid_payload(nested, expected_keys, validator):
            return nested
    return None


def _response_json(
    model: str,
    system: str,
    user: str,
    expected_keys: set[str] | None = None,
    validator: Callable[[dict[str, Any]], bool] | None = None,
) -> dict[str, Any] | None:
    client = _client()
    if client is None:
        return None
    text = _chat_text(client, model, system, user)
    parsed = _json_from_text(text, expected_keys, validator)
    if parsed is not None:
        return parsed

    repaired_text = _repair_json_text(client, model, system, user, text)
    repaired = _json_from_text(repaired_text, expected_keys, validator)
    if repaired is None:
        raise AIResponseError(
            "LLM response was not valid JSON after an automatic repair attempt. "
            "Check that the configured model supports JSON-only Chat Completions."
        )
    return repaired


def _chat_text(client: OpenAI, model: str, system: str, user: str) -> str:
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
    if not text.strip():
        raise AIResponseError("LLM returned empty content.")
    return text


def _repair_json_text(
    client: OpenAI,
    model: str,
    original_system: str,
    original_user: str,
    invalid_text: str,
) -> str:
    repair_system = (
        "You repair invalid LLM output into strict JSON. Return only one valid JSON object. "
        "Do not include markdown fences, comments, explanations, or extra text."
    )
    repair_user = (
        "Original system instruction:\n"
        f"{original_system}\n\n"
        "Original user instruction:\n"
        f"{original_user}\n\n"
        "Invalid output to repair:\n"
        f"{invalid_text[:12000]}"
    )
    return _chat_text(client, model, repair_system, repair_user)


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


def _fallback_project_brief(goal: str, current_level: str | None) -> dict[str, Any]:
    return {
        "learning_goal": goal,
        "assumed_current_level": _normalized_level(current_level),
        "scope": ["Core concepts", "Practical examples", "Recall practice"],
        "out_of_scope": ["External certification", "Unrelated advanced topics"],
        "recommended_strategy": "Study one concept at a time, answer tutor checks, and review weak points.",
        "success_criteria": ["Explain core ideas in your own words", "Apply concepts in a small exercise"],
    }


def _fallback_knowledge_map(title: str, goal: str, source_excerpt: str | None = None) -> dict[str, Any]:
    plan = _fallback_plan(title, goal, source_excerpt)
    points = []
    for index, item in enumerate(plan["knowledge_points"], start=1):
        key = _client_key(item["name"], index)
        points.append(
            {
                "client_key": key,
                "name": item["name"],
                "explanation": item["explanation"],
                "difficulty": "intro" if index == 1 else "core",
                "estimated_weight": round(1 / len(plan["knowledge_points"]), 3),
                "source_locator": "chunk-1" if source_excerpt else None,
            }
        )
    return {
        "knowledge_points": points,
        "edges": [
            {
                "source_client_key": points[index - 1]["client_key"],
                "target_client_key": points[index]["client_key"],
                "relation_type": "prerequisite",
            }
            for index in range(1, len(points))
        ],
    }


def _fallback_lesson_plan(title: str, goal: str, knowledge_points: list[dict[str, Any]]) -> dict[str, Any]:
    if not knowledge_points:
        knowledge_points = _fallback_knowledge_map(title, goal)["knowledge_points"]
    lessons = []
    for index, point in enumerate(knowledge_points, start=1):
        lessons.append(
            {
                "title": f"{title}: {point['name']}",
                "summary": f"Understand and practice {point['name']}.",
                "order_index": index,
                "covered_knowledge_client_keys": [point["client_key"]],
                "learning_objectives": [f"Explain {point['name']} in your own words"],
                "suggested_activity": "Answer a tutor question and ask for an example.",
            }
        )
    return {"lessons": lessons[:6]}


def _fallback_lesson_content(
    lesson_title: str,
    lesson_summary: str,
    knowledge_points: list[dict[str, Any]],
    context_chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    names = ", ".join(str(item.get("name")) for item in knowledge_points) or lesson_title
    citations = []
    for chunk in context_chunks[:2]:
        if chunk.get("id"):
            citations.append(
                {
                    "source_chunk_id": chunk["id"],
                    "label": chunk.get("locator") or chunk.get("title") or "Source",
                    "excerpt": str(chunk.get("content") or "")[:260],
                }
            )
    return {
        "tutor_explanation": (
            f"{lesson_summary}\n\nFocus on {names}. Start by naming the idea, then connect it "
            "to one concrete example before answering the tutor check."
        ),
        "examples": [f"A useful example is to apply {names} to a small realistic task."],
        "practice_suggestions": ["Explain the idea aloud", "Ask the tutor for a follow-up challenge"],
        "source_citations": citations,
    }


def _client_key(name: str, index: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return (slug or f"point-{index}")[:80]


def _normalized_level(value: str | None) -> str:
    text = (value or "unknown").lower()
    if "begin" in text:
        return "beginner"
    if "inter" in text:
        return "intermediate"
    if "advanced" in text or "expert" in text:
        return "advanced"
    return "unknown"


def generate_project_brief(
    title: str,
    goal: str,
    source_type: str,
    current_level: str | None,
    material_context: str | None = None,
) -> dict[str, Any]:
    if settings.apgl_mock_ai:
        return _fallback_project_brief(goal, current_level)
    system = (
        "You create a concise learning project brief. Return only JSON with keys "
        "learning_goal, assumed_current_level, scope, out_of_scope, recommended_strategy, "
        "and success_criteria. assumed_current_level must be beginner, intermediate, advanced, or unknown."
    )
    user = (
        f"Title: {title}\nGoal: {goal}\nSource type: {source_type}\n"
        f"Current level: {current_level or 'unknown'}\n"
        f"Material context:\n{(material_context or '')[:6000]}"
    )
    data = _response_json(_model_smart(), system, user, {"learning_goal"})
    if not data or not str(data.get("learning_goal") or "").strip():
        raise AIResponseError("Project brief response must include learning_goal.")
    return data


def generate_knowledge_map(
    title: str,
    goal: str,
    project_brief: dict[str, Any],
    source_type: str,
    context_chunks: list[str],
) -> dict[str, Any]:
    if settings.apgl_mock_ai:
        return _fallback_knowledge_map(title, goal, "\n\n".join(context_chunks[:2]) if context_chunks else None)
    system = (
        "You build a knowledge map for an AI tutor. Return only JSON with keys knowledge_points "
        "and edges. Do not generate lessons or quiz questions. Each knowledge point must include "
        "client_key, name, explanation, difficulty, estimated_weight, and optional source_locator."
    )
    user = (
        f"Title: {title}\nGoal: {goal}\nSource type: {source_type}\n"
        f"Project brief:\n{json.dumps(project_brief, ensure_ascii=False)}\n\n"
        f"Source context:\n{chr(10).join(context_chunks)[:14000]}"
    )
    data = _response_json(_model_smart(), system, user, {"knowledge_points"})
    if not data or not isinstance(data.get("knowledge_points"), list) or not data["knowledge_points"]:
        raise AIResponseError("Knowledge map response must include knowledge_points.")
    return data


def generate_lesson_plan(
    title: str,
    goal: str,
    project_brief: dict[str, Any],
    knowledge_points: list[dict[str, Any]],
) -> dict[str, Any]:
    if settings.apgl_mock_ai:
        return _fallback_lesson_plan(title, goal, knowledge_points)
    system = (
        "You plan lesson containers for an AI tutor. Return only JSON with key lessons. "
        "Do not write detailed lesson content or quiz questions. Every returned lesson must include "
        "title, summary, order_index, covered_knowledge_client_keys, learning_objectives, and suggested_activity."
    )
    user = (
        f"Title: {title}\nGoal: {goal}\nProject brief:\n{json.dumps(project_brief, ensure_ascii=False)}\n"
        f"Saved knowledge points:\n{json.dumps(knowledge_points, ensure_ascii=False)}"
    )
    data = _response_json(_model_smart(), system, user, {"lessons"})
    if not data or not isinstance(data.get("lessons"), list) or not data["lessons"]:
        raise AIResponseError("Lesson plan response must include at least one lesson.")
    return data


def generate_lesson_content(
    lesson_title: str,
    lesson_summary: str,
    project_goal: str,
    knowledge_points: list[dict[str, Any]],
    context_chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    if settings.apgl_mock_ai:
        return _fallback_lesson_content(lesson_title, lesson_summary, knowledge_points, context_chunks)
    system = (
        "You prepare concise lesson content for an AI tutor. Return only JSON with keys "
        "tutor_explanation, examples, practice_suggestions, and source_citations. Do not generate quiz questions."
    )
    user = (
        f"Lesson: {lesson_title}\nSummary: {lesson_summary}\nProject goal: {project_goal}\n"
        f"Knowledge points:\n{json.dumps(knowledge_points, ensure_ascii=False)}\n"
        f"Source chunks:\n{json.dumps(context_chunks, ensure_ascii=False)[:14000]}"
    )
    data = _response_json(_model_smart(), system, user, {"tutor_explanation"})
    if not data or not str(data.get("tutor_explanation") or "").strip():
        raise AIResponseError("Lesson content response must include tutor_explanation.")
    return data


def generate_assessment_question(
    project_title: str,
    lesson_title: str,
    knowledge_point: dict[str, Any],
    recent_turns: list[dict[str, Any]],
    context_chunks: list[str],
) -> dict[str, Any]:
    if settings.apgl_mock_ai:
        name = str(knowledge_point.get("name") or "this concept")
        return {
            "question": f"In your own words, explain {name} and give one practical example.",
            "expected_idea": str(knowledge_point.get("explanation") or name),
            "citations": [],
        }
    system = (
        "You ask one assessment question for a learner. Return only JSON with keys question, "
        "expected_idea, and citations. The question should check understanding, not trivia."
    )
    user = (
        f"Project: {project_title}\nLesson: {lesson_title}\n"
        f"Knowledge point:\n{json.dumps(knowledge_point, ensure_ascii=False)}\n"
        f"Recent turns:\n{json.dumps(recent_turns, ensure_ascii=False)}\n"
        f"Source context:\n{chr(10).join(context_chunks)[:8000]}"
    )
    data = _response_json(_model_smart(), system, user, {"question"})
    if not data or not str(data.get("question") or "").strip():
        raise AIResponseError("Assessment question response must include question.")
    return data


def evaluate_assessment_answer(
    question: str,
    expected_idea: str,
    learner_answer: str,
    knowledge_point: dict[str, Any],
) -> dict[str, Any]:
    if not learner_answer.strip():
        return {
            "is_correct": False,
            "score": 0.0,
            "feedback": "Please provide an answer so the tutor can evaluate your understanding.",
            "missing_concepts": ["No answer provided"],
            "mastery_delta": -0.02,
            "next_action": "explain_again",
        }
    if settings.apgl_mock_ai:
        graded = _fallback_grade(question, expected_idea, learner_answer)
        return {
            "is_correct": graded["is_correct"],
            "score": 0.86 if graded["is_correct"] else 0.45,
            "feedback": graded["feedback"],
            "missing_concepts": [] if graded["is_correct"] else [str(knowledge_point.get("name") or "Core idea")],
            "mastery_delta": 0.1 if graded["is_correct"] else -0.03,
            "next_action": "move_on" if graded["is_correct"] else "ask_follow_up",
        }
    system = (
        "You evaluate one learner answer. Return only JSON with keys is_correct, score, feedback, "
        "missing_concepts, mastery_delta, and next_action. score must be 0 to 1."
    )
    user = (
        f"Question: {question}\nExpected idea: {expected_idea}\n"
        f"Knowledge point: {json.dumps(knowledge_point, ensure_ascii=False)}\n"
        f"Learner answer: {learner_answer}"
    )
    data = _response_json(_model_smart(), system, user, {"is_correct", "score"})
    if not data or not isinstance(data.get("is_correct"), bool):
        raise AIResponseError("Assessment evaluation must include boolean is_correct.")
    return data


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
        f"Create a multi-session tutor learning path.\nTitle: {title}\nGoal: {goal}\n"
        f"Current level: {current_level or 'unknown'}\n"
        "Return 4-6 lessons and 6-10 knowledge points. Include practical examples, "
        "practice prompts, and one quiz item per lesson."
    )
    return _response_json(_model_smart(), system, user)


def generate_material_plan(title: str, goal: str, chunks: list[str]) -> dict[str, Any]:
    if settings.apgl_mock_ai:
        excerpt = "\n\n".join(chunks[:3])[:6000]
        return _fallback_plan(title, goal, excerpt)

    excerpt = "\n\n".join(chunks[:8])[:14000]
    system = (
        "You convert learning materials into guided study plans. Return only JSON with keys "
        "knowledge_points and lessons. Lessons must be grounded in the supplied material. "
        "Use the same language as the learner's goal or material."
    )
    user = (
        f"Project title: {title}\nGoal: {goal}\nMaterial excerpt:\n{excerpt}\n\n"
        "Return a staged learning plan with 4-8 lessons, 8-12 knowledge points, "
        "and one quiz item per lesson. Make lessons specific to the material."
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


def generate_tutor_reply(
    project_title: str,
    project_goal: str,
    focus: str,
    learner_message: str,
    context_chunks: list[str],
    recent_history: list[dict[str, str]],
    tracker_context: str,
) -> dict[str, Any]:
    if settings.apgl_mock_ai:
        context = context_chunks[0][:500] if context_chunks else project_goal
        return {
            "answer": (
                f"Let's work on {focus or project_title}. Based on your goal, start by "
                f"explaining what you already know. A useful source clue is: {context}"
            ),
            "follow_up_questions": [
                "What part feels unclear right now?",
                "Can you restate the key idea in your own words?",
            ],
            "suggested_actions": ["Answer the follow-up question", "Ask for an example"],
        }

    history = "\n".join(
        f"{item.get('role', 'user')}: {item.get('content', '')}" for item in recent_history[-8:]
    )
    source_context = "\n\n".join(context_chunks)[:12000]
    system = (
        "You are a Socratic AI tutor inside a learning workspace. Return only JSON with keys "
        "answer, follow_up_questions, and suggested_actions. Keep the answer concise, teach in "
        "small steps, ask 1-2 checks, and ground claims in provided source context when available."
    )
    user = (
        f"Project: {project_title}\nGoal: {project_goal}\nFocus: {focus}\n"
        f"Tracker context:\n{tracker_context}\n\nRecent session history:\n{history}\n\n"
        f"Source context:\n{source_context}\n\nLearner message: {learner_message}"
    )
    data = _response_json(_model_smart(), system, user)
    if not data or not str(data.get("answer") or "").strip():
        raise AIResponseError("LLM tutor response must include an answer.")
    return {
        "answer": str(data.get("answer") or ""),
        "follow_up_questions": [
            str(item) for item in (data.get("follow_up_questions") or [])[:3]
        ],
        "suggested_actions": [str(item) for item in (data.get("suggested_actions") or [])[:3]],
    }


def summarize_tutor_session(
    project_title: str,
    project_goal: str,
    focus: str,
    messages: list[dict[str, str]],
) -> dict[str, Any]:
    if settings.apgl_mock_ai:
        user_messages = [item["content"] for item in messages if item.get("role") == "user"]
        return {
            "summary": (
                f"Session on {focus or project_title}. The learner asked about "
                f"{'; '.join(user_messages[-2:]) or project_goal}."
            ),
            "mastered_topics": [focus or project_title],
            "learning_gaps": [
                {
                    "title": "Needs more retrieval practice",
                    "severity": "medium",
                    "evidence": "Session ended before a complete mastery check.",
                }
            ],
            "next_plan": "Review the session summary, answer one check question, then continue the next lesson.",
        }

    transcript = "\n".join(f"{item['role']}: {item['content']}" for item in messages[-20:])
    system = (
        "You summarize a tutoring session. Return only JSON with keys summary, "
        "mastered_topics, learning_gaps, and next_plan. learning_gaps must be a list of "
        "objects with title, severity, and evidence."
    )
    user = (
        f"Project: {project_title}\nGoal: {project_goal}\nFocus: {focus}\n"
        f"Transcript:\n{transcript}"
    )
    data = _response_json(_model_smart(), system, user)
    if not data or not str(data.get("summary") or "").strip():
        raise AIResponseError("LLM session summary must include a summary.")
    return {
        "summary": str(data.get("summary") or ""),
        "mastered_topics": [str(item) for item in (data.get("mastered_topics") or [])[:8]],
        "learning_gaps": [
            item for item in (data.get("learning_gaps") or [])[:8] if isinstance(item, dict)
        ],
        "next_plan": str(data.get("next_plan") or "Continue the next tutor session."),
    }
