"""
LLM-as-judge grader with strict JSON schema validation.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

import jsonschema
from dotenv import load_dotenv
from openai import OpenAI

from ..types import GradeResult

# Load schema
SCHEMA_PATH = Path(__file__).parent.parent / "schemas" / "judge_output.schema.json"


def load_judge_schema() -> Dict[str, Any]:
    """Load the JSON schema for judge output."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def model_judge_grader(
    question: str,
    answer: str,
    sources: list,
    ground_truth: Optional[str] = None,
    rubric: Optional[str] = None,
    model: str = "gpt-3.5-turbo"
) -> GradeResult:
    """
    Use LLM-as-judge to grade the answer.
    
    Returns GradeResult with uncertainty_flag support.
    """
    # Check for API key
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        return GradeResult(
            passed=False,
            evidence="OPENAI_API_KEY not set - cannot run model judge",
            uncertainty_flag=True,
            failure_reason="Missing API key",
            details={"error": "API key not available"}
        )
    
    try:
        client = OpenAI(api_key=api_key)
    except Exception as e:
        return GradeResult(
            passed=False,
            evidence=f"Failed to initialize OpenAI client: {e}",
            uncertainty_flag=True,
            failure_reason="Client initialization failed",
            details={"error": str(e)}
        )
    
    # Build context text from sources
    context_text = "\n\n---\n\n".join(
        s.get("text", "") for s in sources if s.get("text")
    )
    
    # Build judge prompt
    system_prompt = (
        "You are an impartial evaluator for a question-answering system over an "
        "insurance claim. You will receive:\n"
        "- the user question\n"
        "- the system's answer\n"
        "- the retrieved context\n"
    )
    
    if ground_truth:
        system_prompt += "- the ground truth answer (for reference)\n"
    
    if rubric:
        system_prompt += f"\nAdditional rubric:\n{rubric}\n"
    
    system_prompt += (
        "\nEvaluate correctness on a scale from 1 to 5 (integers):\n"
        "1 = Completely incorrect or irrelevant\n"
        "2 = Mostly incorrect with minor correct elements\n"
        "3 = Partially correct but missing key information\n"
        "4 = Mostly correct with minor issues\n"
        "5 = Completely correct and complete\n\n"
        "IMPORTANT: If you lack sufficient evidence to make a confident judgment, "
        "set uncertainty_flag to true. Do not guess.\n\n"
        "Return ONLY a JSON object with the following keys:\n"
        "{\n"
        "  \"correctness\": int (1-5),\n"
        "  \"evidence\": str (explanation),\n"
        "  \"uncertainty_flag\": bool,\n"
        "  \"pass\": bool (true if correctness >= 4 and not uncertain),\n"
        "  \"failure_reason\": str or null\n"
        "}\n"
    )
    
    user_content = f"Question: {question}\n\nSystem answer: {answer}\n\nRetrieved context:\n{context_text}\n"
    
    if ground_truth:
        user_content += f"\nGround truth (for reference): {ground_truth}\n"
    
    try:
        response = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            temperature=0.0,
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)
        
        # Validate against schema
        schema = load_judge_schema()
        jsonschema.validate(instance=data, schema=schema)
        
        # Extract fields
        correctness = data.get("correctness", 0)
        evidence = data.get("evidence", "")
        uncertainty_flag = data.get("uncertainty_flag", False)
        passed = data.get("pass", False)
        failure_reason = data.get("failure_reason")
        
        return GradeResult(
            passed=passed,
            score=float(correctness),
            evidence=evidence,
            uncertainty_flag=uncertainty_flag,
            failure_reason=failure_reason,
            details={
                "correctness": correctness,
                "model": model,
                "raw_response": data
            }
        )
        
    except jsonschema.ValidationError as e:
        return GradeResult(
            passed=False,
            evidence=f"Judge output did not match schema: {e.message}",
            uncertainty_flag=True,
            failure_reason="Schema validation failed",
            details={"error": str(e), "raw_content": content if 'content' in locals() else None}
        )
    except json.JSONDecodeError as e:
        return GradeResult(
            passed=False,
            evidence=f"Failed to parse judge JSON: {e}",
            uncertainty_flag=True,
            failure_reason="JSON parse error",
            details={"error": str(e), "raw_content": content if 'content' in locals() else None}
        )
    except Exception as e:
        return GradeResult(
            passed=False,
            evidence=f"Error calling judge model: {e}",
            uncertainty_flag=True,
            failure_reason="API call failed",
            details={"error": str(e)}
        )

