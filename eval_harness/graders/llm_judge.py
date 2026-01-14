import json
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from jsonschema import ValidationError, validate
from openai import OpenAI

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "llm_judge.schema.json"


def _load_schema() -> Dict[str, Any]:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_client() -> OpenAI:
    load_dotenv()
    return OpenAI()


def build_prompt(question: str, answer: str, rubric: str, must_allow_insufficient: bool) -> str:
    insuff_line = (
        "If the answer lacks evidence or is unclear, set verdict=fail and "
        "cites_evidence=false. If appropriate, include insufficient_evidence=true."
        if must_allow_insufficient
        else "If the answer is unsupported or unclear, set verdict=fail."
    )
    return (
        "You are a strict evaluator. Respond with ONLY valid JSON.\n"
        "Use ONLY these keys: score_1_to_5, verdict, rationale, cites_evidence, "
        "and optional insufficient_evidence. Do NOT add any other keys.\n"
        f"Rubric: {rubric}\n"
        f"{insuff_line}\n\n"
        f"Question: {question}\n"
        f"Answer: {answer}\n\n"
        "Return JSON with fields: score_1_to_5 (1-5), verdict (pass|fail), "
        "rationale (brief), cites_evidence (true|false), optional insufficient_evidence."
    )


def judge_answer(
    question: str,
    answer: str,
    rubric: str,
    must_allow_insufficient: bool,
    model: str,
    client: Optional[OpenAI] = None,
) -> Dict[str, Any]:
    if client is None:
        client = build_client()

    prompt = build_prompt(question, answer, rubric, must_allow_insufficient)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "Return JSON only. No markdown. Do not include extra keys.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    content = response.choices[0].message.content or ""
    schema = _load_schema()
    parsed: Optional[Dict[str, Any]] = None
    valid = False
    error: Optional[str] = None

    try:
        parsed = json.loads(content)
        validate(instance=parsed, schema=schema)
        valid = True
    except (json.JSONDecodeError, ValidationError) as exc:
        error = str(exc)

    return {
        "raw": content,
        "parsed": parsed,
        "valid_json": valid,
        "error": error,
    }

