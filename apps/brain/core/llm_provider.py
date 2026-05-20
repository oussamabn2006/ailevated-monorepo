"""
llm_provider.py — Unified LLM Provider Abstraction
====================================================
Provides a single call_llm() interface that works across three providers:
  - Groq       (Llama 3.3 70B — default, fastest via LPU hardware)
  - Google Gemini (gemini-2.0-flash / gemini-1.5-pro)
  - Anthropic Claude (haiku / sonnet / opus)

Each provider supports three performance tiers:
  - fast      — smallest/cheapest model, used for evaluation (Node 5)
  - balanced  — main model, used for all generation agents (Nodes 2-4)
  - powerful  — largest model, available for future high-stakes calls

Provider selection priority:
  1. Explicit provider arg in call_llm()
  2. LLM_PROVIDER env var
  3. Auto-select: first provider with a valid API key in .env

Automatic fallback:
  If the selected provider hits a quota/rate-limit error (HTTP 429),
  the system automatically retries with the next available provider.
  This ensures continuity of service during API quota exhaustion.

To add a new provider:
  1. Add it to the PROVIDERS dict with models and key_env
  2. Add a _call_<provider>() function
  3. Add the elif branch in call_llm()
"""

import os
from dotenv import load_dotenv
from groq import Groq
import google.generativeai as genai

load_dotenv()

# ── Provider Registry ──────────────────────────────────────────────────────────
# Maps provider names to their model identifiers and API key env var names.
# To swap a model version, change it here — no other file needs to change.
PROVIDERS = {
    "groq": {
        "models": {
            "fast":     "llama-3.1-8b-instant",     # Small, fast — for evaluation
            "balanced": "llama-3.3-70b-versatile",   # Main generation model
            "powerful": "llama-3.3-70b-versatile"    # Same as balanced for Groq
        },
        "key_env": "GROQ_API_KEY"
    },
    "gemini": {
        "models": {
            "fast":     "gemini-2.0-flash",   # Fast and free tier
            "balanced": "gemini-2.0-flash",   # Same — flash is sufficient
            "powerful": "gemini-1.5-pro"      # Pro for high-quality generation
        },
        "key_env": "GEMINI_API_KEY"
    },
    "anthropic": {
        "models": {
            "fast":     "claude-haiku-4-5-20251001",  # Cheapest Claude
            "balanced": "claude-sonnet-4-6",           # Main Claude model
            "powerful": "claude-opus-4-6"              # Highest quality, highest cost
        },
        "key_env": "ANTHROPIC_API_KEY"
    }
}


# ══════════════════════════════════════════════════════════════════════════════
# MAIN INTERFACE — All agents call this function, never provider-specific ones
# ══════════════════════════════════════════════════════════════════════════════
def call_llm(
    system_prompt: str,
    user_prompt: str,
    provider: str = None,
    tier: str = "balanced",
    temperature: float = 0.5,
    max_tokens: int = 2000
) -> str:
    """
    Unified LLM call interface with automatic provider fallback.

    Args:
        system_prompt: The system/role instructions for the model
        user_prompt:   The user message / task description
        provider:      "groq" | "gemini" | "anthropic" | None
                       None = auto-select from available keys
        tier:          "fast" | "balanced" | "powerful"
                       Controls which model size is used per provider
        temperature:   0.0-1.0. Lower = more deterministic.
                       Use 0.1-0.3 for extraction, 0.5 for generation
        max_tokens:    Maximum output tokens

    Returns:
        Raw string response from the model

    Raises:
        RuntimeError: If no providers are available or all fail
        Exception:    Provider-specific errors if no fallback is possible
    """

    # Get list of providers with valid API keys in .env
    available_providers = _get_available_providers()

    # Auto-select if no provider specified
    if provider is None:
        provider = _auto_select_provider()

    # Validate the requested provider is actually available
    if provider not in available_providers:
        raise RuntimeError(
            f"Provider '{provider}' is not available (no valid API key). "
            f"Available: {available_providers}"
        )

    # Build fallback order: requested provider first, then all others
    # e.g. if groq is requested and gemini + anthropic are available:
    # fallback_order = ["groq", "gemini", "anthropic"]
    fallback_order = _get_fallback_order(provider, available_providers)
    last_exception = None

    for candidate in fallback_order:
        try:
            print(f"🤖 [{candidate.upper()} / {tier}] Calling LLM... (requested: {provider})")

            if candidate == "groq":
                return _call_groq(system_prompt, user_prompt, tier, temperature, max_tokens)
            elif candidate == "gemini":
                return _call_gemini(system_prompt, user_prompt, tier, temperature, max_tokens)
            elif candidate == "anthropic":
                return _call_anthropic(system_prompt, user_prompt, tier, temperature, max_tokens)

        except Exception as exc:
            last_exception = exc
            msg = str(exc).lower()
            print(f"⚠️ {candidate.upper()} failed: {msg}")

            # Only trigger fallback for quota/rate-limit errors
            # Other errors (bad API key, network, etc.) raise immediately
            is_quota_error = any(keyword in msg for keyword in [
                "quota", "rate limit", "429", "billing", "quota exceeded", "exceeded"
            ])

            if candidate == provider and is_quota_error:
                remaining = [p for p in fallback_order if p != candidate]
                if remaining:
                    print(f"⚠️ Quota hit — falling back to {remaining[0].upper()}")
                    continue  # Try next provider in fallback_order

            # If it's not a quota error, or we've exhausted fallbacks, re-raise
            if candidate != provider:
                continue
            raise

    # All providers in fallback_order failed
    raise RuntimeError(
        f"All providers failed. Last error from {fallback_order[-1].upper()}: {last_exception}"
    )


# ── Helper Functions ───────────────────────────────────────────────────────────

def _get_available_providers() -> list[str]:
    """Returns list of providers that have a valid (non-empty) API key in .env."""
    return [
        name for name, config in PROVIDERS.items()
        if os.getenv(config["key_env"]) and len(os.getenv(config["key_env"])) > 10
    ]


def _get_fallback_order(provider: str, available_providers: list[str]) -> list[str]:
    """
    Returns provider list with requested provider first, others after.
    e.g. _get_fallback_order("groq", ["groq", "gemini"]) → ["groq", "gemini"]
    """
    return [provider] + [p for p in available_providers if p != provider]


def _auto_select_provider() -> str:
    """
    Picks the first provider with a valid API key.
    Order follows PROVIDERS dict insertion order: groq → gemini → anthropic.
    """
    for name, config in PROVIDERS.items():
        key = os.getenv(config["key_env"])
        if key and len(key) > 10:
            return name
    raise RuntimeError(
        "No LLM API key found. Set at least one of: "
        "GROQ_API_KEY, GEMINI_API_KEY, or ANTHROPIC_API_KEY in your .env file."
    )


def _get_model(provider: str, tier: str) -> str:
    """Returns the model identifier for a given provider and performance tier."""
    return PROVIDERS[provider]["models"].get(tier, PROVIDERS[provider]["models"]["balanced"])


# ── Provider-Specific Implementations ─────────────────────────────────────────
# These are internal functions — only call_llm() should call them.
# Adding a new provider = add a new function here + entry in PROVIDERS dict.

def _call_groq(system_prompt, user_prompt, tier, temperature, max_tokens) -> str:
    """Calls Groq API. Groq uses custom LPU hardware for fast inference."""
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    model  = _get_model("groq", tier)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt}
        ],
        temperature=temperature,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content


def _call_gemini(system_prompt, user_prompt, tier, temperature, max_tokens) -> str:
    """Calls Google Gemini API via the google-generativeai library."""
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model_name = _get_model("gemini", tier)

    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_prompt,       # Gemini uses system_instruction, not messages[0]
        generation_config=genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens
        )
    )

    response = model.generate_content(user_prompt)
    return response.text


def _call_anthropic(system_prompt, user_prompt, tier, temperature, max_tokens) -> str:
    """Calls Anthropic Claude API via the anthropic library."""
    import anthropic  # Imported here to keep it optional — only needed if Anthropic key is set
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    model  = _get_model("anthropic", tier)

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )
    return response.content[0].text