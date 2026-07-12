"""3-Tier Cloud LLM Cascade for Nyaya AI (ADR-004, ADR-005).

Escalation order:
    Tier 1: Groq API (Llama 3.3 70B) — fast, free tier
    Tier 2: Gemini 2.0 Flash — Google AI, generous free tier
    Tier 3: OpenRouter free-tier (Qwen/GLM/Kimi)

Flow per tier:
1. Format context chunks into a numbered list
2. Call LLM via OpenAI-compatible endpoint with JSON mode
3. Parse response with CitedAnswer.model_validate_json()
4. On validation failure: up to MAX_RETRIES retries at same tier
5. On exhausted retries or ConnectionError: escalate to next tier
6. On confidence < CONFIDENCE_THRESHOLD: set can_answer=False
7. If all 3 tiers fail: return cite-or-refuse fallback
"""

from __future__ import annotations

import json
import re

from rich.console import Console

from nyaya_ai.config import (
    CONFIDENCE_THRESHOLD,
    GEMINI_API_KEY,
    GEMINI_BASE_URL,
    GEMINI_MODEL,
    GROQ_API_KEY,
    GROQ_BASE_URL,
    GROQ_MODEL,
    MAX_RETRIES,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
)
from pydantic import BaseModel
from nyaya_ai.llm.prompts import build_system_prompt, build_risk_assessment_prompt
from nyaya_ai.schemas import CitedAnswer, RiskAssessment

console = Console()


# ===================================================================
# Context formatting
# ===================================================================

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


def _build_user_message(question: str, context_str: str) -> str:
    """Build the user message for the LLM."""
    return (
        f"## Context Sections\n\n{context_str}\n\n"
        f"## Question\n\n{question}\n\n"
        f"Answer in JSON format following the schema in the system prompt."
    )


# ===================================================================
# Tier 1 — Groq (Llama 3.3 70B)
# ===================================================================

def _call_groq(
    question: str,
    context_str: str,
    system_prompt: str,
) -> str:
    """Call Llama 3.3 70B via Groq's OpenAI-compatible endpoint.

    Raises:
        ConnectionError: If Groq is not reachable or API key is missing.
    """
    from openai import OpenAI

    if not GROQ_API_KEY:
        raise ConnectionError("GROQ_API_KEY not set. Export it: set GROQ_API_KEY=gsk_...")

    try:
        client = OpenAI(
            base_url=GROQ_BASE_URL,
            api_key=GROQ_API_KEY,
        )

        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": _build_user_message(question, context_str)},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Groq returned empty response")
        return content

    except Exception as e:
        error_str = str(e).lower()
        if any(
            term in error_str
            for term in ["connection", "refused", "timeout", "unreachable", "api_key", "authentication"]
        ):
            raise ConnectionError(f"Groq API error: {e}") from e
        raise


# ===================================================================
# Tier 2 — Gemini 2.0 Flash (via OpenAI-compatible endpoint)
# ===================================================================

def _call_gemini(
    question: str,
    context_str: str,
    system_prompt: str,
) -> str:
    """Call Gemini 2.0 Flash via Google's OpenAI-compatible endpoint.

    Uses the generativelanguage.googleapis.com/v1beta/openai/ endpoint
    so we can reuse the OpenAI SDK — zero new dependencies.

    Raises:
        ConnectionError: If Gemini is not reachable or API key is missing.
    """
    from openai import OpenAI

    if not GEMINI_API_KEY:
        raise ConnectionError("GEMINI_API_KEY not set. Export it: set GEMINI_API_KEY=AI...")

    try:
        client = OpenAI(
            base_url=GEMINI_BASE_URL,
            api_key=GEMINI_API_KEY,
        )

        response = client.chat.completions.create(
            model=GEMINI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": _build_user_message(question, context_str)},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Gemini returned empty response")
        return content

    except Exception as e:
        error_str = str(e).lower()
        if any(
            term in error_str
            for term in ["connection", "refused", "timeout", "unreachable", "api_key", "authentication"]
        ):
            raise ConnectionError(f"Gemini API error: {e}") from e
        raise


# ===================================================================
# Tier 3 — OpenRouter (free-tier model)
# ===================================================================

def _call_openrouter(
    question: str,
    context_str: str,
    system_prompt: str,
) -> str:
    """Call a free-tier model via OpenRouter's OpenAI-compatible endpoint.

    Raises:
        ConnectionError: If OpenRouter is not reachable or API key is missing.
    """
    from openai import OpenAI

    if not OPENROUTER_API_KEY:
        raise ConnectionError("OPENROUTER_API_KEY not set. Export it: set OPENROUTER_API_KEY=sk-or-...")

    try:
        client = OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=OPENROUTER_API_KEY,
            default_headers={
                "HTTP-Referer": "https://github.com/nyaya-ai",
                "X-Title": "Nyaya AI",
            },
        )

        response = client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": _build_user_message(question, context_str)},
            ],
            temperature=0.1,
            # OpenRouter free models may not support response_format
        )

        content = response.choices[0].message.content
        if content is None:
            raise ValueError("OpenRouter returned empty response")
        return content

    except Exception as e:
        error_str = str(e).lower()
        if any(
            term in error_str
            for term in ["connection", "refused", "timeout", "unreachable", "api_key", "authentication"]
        ):
            raise ConnectionError(f"OpenRouter API error: {e}") from e
        raise


# ===================================================================
# JSON extraction + parsing
# ===================================================================

def _extract_json(raw: str) -> str:
    """Extract JSON object from noisy LLM output.

    Handles common issues:
    - Markdown fences: ```json ... ```
    - Text before/after the JSON object
    - Leading/trailing whitespace
    """
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


def _parse_response(raw: str, schema_cls: type[BaseModel] = CitedAnswer) -> BaseModel:
    """Parse and validate the raw LLM response into schema_cls.

    Extracts JSON from noisy output before validating with Pydantic.

    Raises:
        ValueError: If the response is not valid JSON or fails Pydantic validation.
    """
    cleaned = _extract_json(raw)
    return schema_cls.model_validate_json(cleaned)


def _make_fallback(reason: str) -> CitedAnswer:
    """Create a cite-or-refuse fallback response."""
    return CitedAnswer(
        answer=reason,
        citations=[],
        confidence=0.0,
        can_answer=False,
    )


# ===================================================================
# Circuit breaker to dynamically skip rate-limited or offline tiers during a batch scan
_DISABLED_TIERS: set[str] = set()


def _try_tier(
    tier_name: str,
    call_fn,
    tier_label: str,
    question: str,
    context_str: str,
    system_prompt: str,
    schema_cls: type[BaseModel] = CitedAnswer,
) -> BaseModel | None:
    """Attempt a single tier with retries. Returns parsed model or None to escalate."""
    if tier_name in _DISABLED_TIERS:
        console.print(f"[yellow]  Skipping {tier_name} (circuit breaker active due to rate limit/connection error)[/]")
        return None

    # First call
    try:
        raw = call_fn(question, context_str, system_prompt)
    except Exception as e:
        err_str = str(e).lower()
        if "rate limit" in err_str or "429" in err_str or isinstance(e, (ConnectionError, ConnectionRefusedError)):
            console.print(f"[red]  {tier_name} rate limited or offline: {e}. Activating circuit breaker.[/]")
            _DISABLED_TIERS.add(tier_name)
        else:
            console.print(f"[red]  {tier_name} unexpected error: {e}[/]")
        return None

    # Parse + validate with retries
    for attempt in range(1 + MAX_RETRIES):
        try:
            answer = _parse_response(raw, schema_cls)

            # Confidence threshold — cite-or-refuse
            if schema_cls is CitedAnswer and answer.confidence < CONFIDENCE_THRESHOLD:
                answer.can_answer = False

            console.print(f"[green]  ✓ Answered by {tier_name} ({tier_label})[/]")
            return answer

        except (ValueError, json.JSONDecodeError) as e:
            if attempt < MAX_RETRIES:
                console.print(
                    f"[yellow]  {tier_name} parse failed (attempt {attempt + 1}), "
                    f"retrying: {e}[/]"
                )
                # Retry: call the LLM again
                try:
                    raw = call_fn(question, context_str, system_prompt)
                except Exception as retry_err:
                    retry_err_str = str(retry_err).lower()
                    if "rate limit" in retry_err_str or "429" in retry_err_str or isinstance(retry_err, (ConnectionError, ConnectionRefusedError)):
                        console.print(f"[red]  {tier_name} retry rate limited or offline: {retry_err}. Activating circuit breaker.[/]")
                        _DISABLED_TIERS.add(tier_name)
                    else:
                        console.print(f"[red]  {tier_name} retry failed: {retry_err}[/]")
                    return None
            else:
                console.print(
                    f"[red]  {tier_name} parse failed after {1 + MAX_RETRIES} attempts: {e}[/]"
                )

    # All retries exhausted at this tier
    return None


def cascade_query(
    question: str,
    context_chunks: list[dict],
) -> CitedAnswer:
    """Run the 3-tier LLM cascade to answer a legal question with citations.

    Escalation: Groq → Gemini → OpenRouter → fallback.

    Each tier function is referenced as a bare name so that
    unittest.mock.patch can intercept it at the module level.

    Args:
        question: The user's legal question.
        context_chunks: List of payload dicts from Qdrant search.

    Returns:
        A validated CitedAnswer — either a real answer or a cite-or-refuse fallback.
        Never raises — all errors are caught and returned as fallbacks.
    """
    system_prompt = build_system_prompt()
    context_str = _format_context(context_chunks)

    # -------------------------------------------------------------------
    # Tier 1 — Groq
    # -------------------------------------------------------------------
    console.print("[dim]  Trying Tier 1 (Groq / Llama 3.3 70B)...[/]")
    result = _try_tier(
        "Tier 1", _call_groq, "Groq / Llama 3.3 70B",
        question, context_str, system_prompt,
    )
    if result is not None:
        return result
    console.print("[yellow]  Tier 1 failed — escalating...[/]")

    # -------------------------------------------------------------------
    # Tier 2 — Gemini
    # -------------------------------------------------------------------
    console.print("[dim]  Trying Tier 2 (Gemini 2.0 Flash)...[/]")
    result = _try_tier(
        "Tier 2", _call_gemini, "Gemini 2.0 Flash",
        question, context_str, system_prompt,
    )
    if result is not None:
        return result
    console.print("[yellow]  Tier 2 failed — escalating...[/]")

    # -------------------------------------------------------------------
    # Tier 3 — OpenRouter
    # -------------------------------------------------------------------
    console.print("[dim]  Trying Tier 3 (OpenRouter)...[/]")
    result = _try_tier(
        "Tier 3", _call_openrouter, "OpenRouter",
        question, context_str, system_prompt,
    )
    if result is not None:
        return result
    console.print("[yellow]  Tier 3 failed.[/]")

    # All tiers exhausted
    console.print("[red]  All 3 tiers exhausted.[/]")
    return _make_fallback(
        "Unable to get a valid response from any language model. "
        "Please try rephrasing your question."
    )


def _make_risk_fallback(clause_type: str, reason: str) -> RiskAssessment:
    """Create a default no-risk response on total cascade failure."""
    return RiskAssessment(
        risk_level="none",
        explanation=f"Cascade failed to run risk assessment: {reason}",
        confidence=0.0,
        clause_type=clause_type,
    )


def cascade_risk_assessment(
    clause_text: str,
    context_chunks: list[dict],
    best_guess_type: str,
) -> RiskAssessment:
    """Run the 3-tier LLM cascade to assess contract clause risks.

    Escalation: Groq → Gemini → OpenRouter → fallback.

    Args:
        clause_text: Verbatim contract clause.
        context_chunks: List of payload dicts from Qdrant search.
        best_guess_type: The local best-guess clause type.

    Returns:
        A validated RiskAssessment model.
    """
    system_prompt = build_risk_assessment_prompt()
    context_str = _format_context(context_chunks)

    # Custom question parameter formatted for the generic prompt
    question = (
        f"Clause to Analyze:\n{clause_text}\n\n"
        f"Local Best-Guess Clause Type: {best_guess_type}"
    )

    # -------------------------------------------------------------------
    # Tier 1 — Groq
    # -------------------------------------------------------------------
    console.print("[dim]  Trying Tier 1 (Groq / Llama 3.3 70B)...[/]")
    result = _try_tier(
        "Tier 1", _call_groq, "Groq / Llama 3.3 70B",
        question, context_str, system_prompt,
        schema_cls=RiskAssessment,
    )
    if result is not None:
        return result
    console.print("[yellow]  Tier 1 failed — escalating...[/]")

    # -------------------------------------------------------------------
    # Tier 2 — Gemini
    # -------------------------------------------------------------------
    console.print("[dim]  Trying Tier 2 (Gemini 2.0 Flash)...[/]")
    result = _try_tier(
        "Tier 2", _call_gemini, "Gemini 2.0 Flash",
        question, context_str, system_prompt,
        schema_cls=RiskAssessment,
    )
    if result is not None:
        return result
    console.print("[yellow]  Tier 2 failed — escalating...[/]")

    # -------------------------------------------------------------------
    # Tier 3 — OpenRouter
    # -------------------------------------------------------------------
    console.print("[dim]  Trying Tier 3 (OpenRouter)...[/]")
    result = _try_tier(
        "Tier 3", _call_openrouter, "OpenRouter",
        question, context_str, system_prompt,
        schema_cls=RiskAssessment,
    )
    if result is not None:
        return result
    console.print("[yellow]  Tier 3 failed.[/]")

    # All tiers exhausted
    console.print("[red]  All 3 tiers exhausted for risk assessment.[/]")
    return _make_risk_fallback(
        best_guess_type,
        "Unable to get a valid response from any language model."
    )

