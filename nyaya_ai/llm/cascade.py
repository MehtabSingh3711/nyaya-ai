"""Confidence-threshold LLM cascade for Nyaya AI (ADR-004, ADR-005).

Week 2 scope: Tier 1 only (Phi-3 Mini via Ollama).
Tier 2 (Gemma-2-9B) and Tier 3 (OpenRouter) are placeholders for later.

Flow:
1. Format context chunks into a numbered list
2. Call Phi-3 via Ollama's OpenAI-compatible endpoint with JSON mode
3. Parse response with CitedAnswer.model_validate_json()
4. On validation failure: one retry at same tier
5. On second failure: return cite-or-refuse fallback
6. On confidence < CONFIDENCE_THRESHOLD: set can_answer=False
"""

from __future__ import annotations

import json

from rich.console import Console

from nyaya_ai.config import (
    CONFIDENCE_THRESHOLD,
    MAX_RETRIES,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)
from nyaya_ai.llm.prompts import build_system_prompt
from nyaya_ai.schemas import CitedAnswer

console = Console()


def _format_context(context_chunks: list[dict]) -> str:
    """Format retrieved chunks into a numbered context block for the LLM.

    Args:
        context_chunks: List of payload dicts from Qdrant search
                        (each has act_name, section_number, text, score, etc.)

    Returns:
        Formatted string with numbered sections.
    """
    if not context_chunks:
        return "(No context sections available)"

    parts = []
    for i, chunk in enumerate(context_chunks, 1):
        act = chunk.get("act_name", "Unknown Act")
        section = chunk.get("section_number", "?")
        text = chunk.get("text", "")
        score = chunk.get("score", 0.0)
        parts.append(
            f"[Section {i}] {act}, Section {section} (relevance: {score:.2f})\n{text}"
        )
    return "\n\n".join(parts)


def _call_ollama(
    question: str,
    context_str: str,
    system_prompt: str,
) -> str:
    """Call Phi-3 via Ollama's OpenAI-compatible chat completions endpoint.

    Args:
        question: The user's legal question.
        context_str: Formatted context sections.
        system_prompt: The system prompt.

    Returns:
        Raw response content string from the LLM.

    Raises:
        ConnectionError: If Ollama is not reachable.
    """
    from openai import OpenAI

    try:
        client = OpenAI(
            base_url=OLLAMA_BASE_URL,
            api_key="ollama",  # Ollama doesn't need a real key
        )

        response = client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"## Context Sections\n\n{context_str}\n\n"
                        f"## Question\n\n{question}\n\n"
                        f"Answer in JSON format following the schema in the system prompt."
                    ),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        content = response.choices[0].message.content
        if content is None:
            raise ValueError("LLM returned empty response")
        return content

    except Exception as e:
        # Check if it's a connection error vs an API error
        error_str = str(e).lower()
        if any(
            term in error_str
            for term in ["connection", "refused", "timeout", "unreachable"]
        ):
            raise ConnectionError(
                f"Cannot connect to Ollama at {OLLAMA_BASE_URL}. "
                f"Is Ollama running? Start with: ollama serve\n"
                f"Error: {e}"
            ) from e
        raise


def _extract_json(raw: str) -> str:
    """Extract JSON object from noisy LLM output.

    Handles common issues:
    - Markdown fences: ```json ... ```
    - Text before/after the JSON object
    - Leading/trailing whitespace
    """
    import re

    text = raw.strip()

    # Strip markdown fences: ```json ... ``` or ``` ... ```
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    # Find the outermost { ... } pair
    start = text.find("{")
    if start == -1:
        raise ValueError(f"No JSON object found in LLM response: {raw[:200]}")

    # Count braces to find the matching closing brace
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    raise ValueError(f"Unbalanced braces in LLM response: {raw[:200]}")


def _parse_response(raw: str) -> CitedAnswer:
    """Parse and validate the raw LLM response into a CitedAnswer.

    Extracts JSON from noisy output before validating with Pydantic.

    Raises:
        ValueError: If the response is not valid JSON or fails Pydantic validation.
    """
    cleaned = _extract_json(raw)
    return CitedAnswer.model_validate_json(cleaned)


def _make_fallback(reason: str) -> CitedAnswer:
    """Create a cite-or-refuse fallback response."""
    return CitedAnswer(
        answer=reason,
        citations=[],
        confidence=0.0,
        can_answer=False,
    )


def cascade_query(
    question: str,
    context_chunks: list[dict],
) -> CitedAnswer:
    """Run the LLM cascade to answer a legal question with citations.

    Currently Tier 1 only (Phi-3 Mini via Ollama).

    Args:
        question: The user's legal question.
        context_chunks: List of payload dicts from Qdrant search.

    Returns:
        A validated CitedAnswer — either a real answer or a cite-or-refuse fallback.
        Never raises — all errors are caught and returned as fallbacks.
    """
    system_prompt = build_system_prompt()
    context_str = _format_context(context_chunks)

    # -----------------------------------------------------------------------
    # Tier 1 — Phi-3 Mini via Ollama (local, free)
    # -----------------------------------------------------------------------
    try:
        raw = _call_ollama(question, context_str, system_prompt)
    except ConnectionError as e:
        console.print(f"[red]{e}[/]")
        return _make_fallback(
            "Unable to reach the language model. Please ensure Ollama is running."
        )
    except Exception as e:
        console.print(f"[red]  Unexpected error calling LLM: {e}[/]")
        return _make_fallback(
            "An unexpected error occurred while calling the language model."
        )

    # Parse + validate with Pydantic
    for attempt in range(1 + MAX_RETRIES):
        try:
            answer = _parse_response(raw)

            # Check confidence threshold — cite-or-refuse
            if answer.confidence < CONFIDENCE_THRESHOLD:
                answer.can_answer = False

            return answer

        except (ValueError, json.JSONDecodeError) as e:
            if attempt < MAX_RETRIES:
                console.print(
                    f"[yellow]  Tier 1 parse failed (attempt {attempt + 1}), "
                    f"retrying: {e}[/]"
                )
                # Retry: call the LLM again
                try:
                    raw = _call_ollama(question, context_str, system_prompt)
                except ConnectionError as conn_err:
                    console.print(f"[red]{conn_err}[/]")
                    return _make_fallback(
                        "Unable to reach the language model on retry."
                    )
            else:
                console.print(
                    f"[red]  Tier 1 parse failed after {1 + MAX_RETRIES} attempts: {e}[/]"
                )

    # -----------------------------------------------------------------------
    # Tier 2 — Gemma-2-9B via Ollama (placeholder for Week 3)
    # -----------------------------------------------------------------------
    # TODO: Wire Tier 2 escalation here.
    # If Tier 1 fails to produce valid output after retries, escalate to
    # Gemma-2-9B. Same _call_ollama() with model="gemma2:9b".
    # console.print("[yellow]  Escalating to Tier 2 (Gemma-2-9B)...[/]")

    # -----------------------------------------------------------------------
    # Tier 3 — OpenRouter free tier (placeholder for Week 3)
    # -----------------------------------------------------------------------
    # TODO: Wire Tier 3 escalation here.
    # If Tier 2 also fails, escalate to OpenRouter free tier.
    # Use a separate _call_openrouter() function with the OpenAI client
    # pointed at https://openrouter.ai/api/v1.
    # console.print("[yellow]  Escalating to Tier 3 (OpenRouter)...[/]")

    # All tiers exhausted — return fallback
    return _make_fallback(
        "Unable to parse a valid response from the language model. "
        "Please try rephrasing your question."
    )
