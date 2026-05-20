"""
differentiation_agent.py — Bloom's Taxonomy Differentiation Engine
====================================================================
Generates two cognitively differentiated variants of a lesson's
practice sections, based on the revised Bloom's Taxonomy
(Anderson & Krathwohl, 2001).

  Support level    — Bloom levels 1-2: Remember & Understand
  Extension level  — Bloom levels 4-6: Analyze, Evaluate & Create

The agent reads from the new 10-section lesson structure
(guided_practice, independent_practice, closing, homework)
but outputs in the schema expected by the Streamlit render_diff function:
  application.teacher_activity
  application.student_activity
  application.scaffolding
  evaluation.activity
  evaluation.success_criteria
  homework

This output schema must match what render_diff() in ailevated_app.py reads.
If you change the output structure here, update render_diff() too.
"""

import os
import json
from dotenv import load_dotenv
from core.llm_provider import call_llm

load_dotenv()

# Default provider from .env — same as agents.py
DEFAULT_PROVIDER = os.getenv("LLM_PROVIDER") or None


def generate_differentiation(original_lesson: dict, level: str, language: str,
                              provider=None) -> dict:
    """
    Rewrites practice sections of a lesson for a specific Bloom cognitive level.

    The differentiation only rewrites HOW students engage with content —
    never WHAT they learn. The topic, objective, and subject stay identical.
    Only the cognitive demand of the activities changes.

    Args:
        original_lesson: Complete lesson dict from assemble_lesson
                         Must contain a "sections" key with guided_practice,
                         independent_practice, closing, homework, objective
        level:           "support" (Bloom 1-2) or "extension" (Bloom 4-6)
        language:        Output language: "ar" | "fr" | "en"
        provider:        LLM provider override. None = use DEFAULT_PROVIDER

    Returns:
        dict with keys:
          level, bloom_focus,
          application: {teacher_activity, student_activity, scaffolding}
          evaluation:  {activity, success_criteria}
          homework

    Raises:
        ValueError: if level is not "support" or "extension"
        json.JSONDecodeError: if the LLM returns malformed JSON
    """

    # ── Bloom Level Definitions ─────────────────────────────────────────────
    # Each level specifies:
    #   name     — display label in the UI (3 languages)
    #   bloom    — which Bloom levels are targeted (3 languages)
    #   verbs    — Bloom action verbs that constrain the type of activities (3 languages)
    #   strategy — pedagogical approach for this level (3 languages)
    #
    # The verbs are the critical mechanism: by specifying which action verbs
    # to use, we constrain the cognitive type of the task the model designs.
    # "identify" forces recognition tasks; "design" forces creative tasks.
    # This is more reliable than asking the model to "make it harder/easier".
    levels = {
        "support": {
            "name": {
                "ar": "مستوى الدعم",
                "fr": "Niveau Soutien",
                "en": "Support Level"
            },
            # Bloom levels 1 (Remember) and 2 (Understand)
            "bloom": {
                "ar": "تذكر وفهم — المستويان 1 و2",
                "fr": "Mémoriser et Comprendre — niveaux 1 et 2",
                "en": "Remember and Understand — levels 1 and 2"
            },
            # Action verbs from Anderson & Krathwohl (2001) taxonomy
            "verbs": {
                "ar": "يذكر، يعرف، يسمي، يصف، يشرح، يلخص، يعيد",
                "fr": "identifier, nommer, lister, décrire, expliquer, résumer, reconnaître",
                "en": "identify, name, list, recall, describe, explain, summarize, recognize"
            },
            # Pedagogical scaffolding strategy for struggling learners
            "strategy": {
                "ar": "تبسيط المهام إلى خطوات مرحلية واضحة، استخدام وسائل بصرية ونماذج، أسئلة موجهة، تقديم أمثلة قبل كل تمرين",
                "fr": "décomposer les tâches en étapes guidées, utiliser des supports visuels et modèles, poser des questions dirigées, fournir des exemples avant chaque exercice",
                "en": "break tasks into guided steps, use visual supports and models, ask scaffolded questions, provide worked examples before each exercise"
            }
        },
        "extension": {
            "name": {
                "ar": "مستوى التوسيع",
                "fr": "Niveau Enrichissement",
                "en": "Extension Level"
            },
            # Bloom levels 4 (Analyze), 5 (Evaluate), 6 (Create)
            "bloom": {
                "ar": "تحليل وتقييم وإبداع — المستويات 4 و5 و6",
                "fr": "Analyser, Évaluer et Créer — niveaux 4, 5 et 6",
                "en": "Analyze, Evaluate and Create — levels 4, 5 and 6"
            },
            # Higher-order thinking verbs from the taxonomy
            "verbs": {
                "ar": "يحلل، يقارن، يميز، يقيّم، يبرر، يصمم، يبتكر، ينتقد، يبني",
                "fr": "analyser, comparer, différencier, évaluer, justifier, concevoir, créer, critiquer, construire",
                "en": "analyze, compare, differentiate, evaluate, justify, design, create, critique, construct, argue"
            },
            # Strategy for advanced learners — open-ended, complex challenges
            "strategy": {
                "ar": "مسائل معقدة غير روتينية، تفكير نقدي ومناقشة مفتوحة، مشاريع إبداعية، تحديات متعددة الخطوات",
                "fr": "problèmes complexes non routiniers, pensée critique et débat ouvert, projets créatifs, défis multi-étapes",
                "en": "complex non-routine problems, critical thinking and open debate, creative projects, multi-step challenges"
            }
        }
    }

    # Validate level before making any API calls
    selected = levels.get(level)
    if not selected:
        raise ValueError(f"Unknown level: '{level}'. Use 'support' or 'extension'.")

    # Fall back to French if an unsupported language code is passed
    lang = language if language in ["ar", "fr", "en"] else "fr"

    # ── Extract source sections from the 10-section lesson structure ────────
    # We only rewrite the practice and assessment sections.
    # Objective, key_points, opening, introduction_to_material are kept identical
    # across all differentiation levels — only practice changes.
    original_sections = original_lesson.get("sections", {})
    guided    = original_sections.get("guided_practice", "")
    indep     = original_sections.get("independent_practice", "")
    closing   = original_sections.get("closing", "")
    homework  = original_sections.get("homework", "")
    objective = original_sections.get("objective", "")  # Context for the model

    # ── System Prompt ───────────────────────────────────────────────────────
    # The output schema here (application/evaluation) must match what
    # render_diff() in ailevated_app.py reads. Do not change field names
    # without updating the Streamlit rendering function.
    system = f"""You are a Bloom's Taxonomy differentiation expert for Moroccan secondary schools.
Write EXCLUSIVELY in {language}. Never mix languages. Not a single word in any other language.

Cognitive Level: {selected['name'][lang]}
Bloom's Focus: {selected['bloom'][lang]}
Action Verbs to Use: {selected['verbs'][lang]}
Pedagogical Strategy: {selected['strategy'][lang]}

You will receive sections from a lesson plan.
Rewrite the practice activities so cognitive demand matches the level above.
Do NOT change the topic or subject matter — only HOW students engage with it.

Return ONLY a valid JSON object with EXACTLY this structure. No markdown. No explanation.

{{
  "level": "{selected['name'][lang]}",
  "bloom_focus": "{selected['bloom'][lang]}",
  "application": {{
    "teacher_activity": "string — what the teacher does during practice at this level",
    "student_activity": "string — what students do during practice at this level",
    "scaffolding": "string — specific support or challenge provided at this level"
  }},
  "evaluation": {{
    "activity": "string — the assessment task adapted to this cognitive level",
    "success_criteria": "string — how you know a student at this level succeeded"
  }},
  "homework": "string — homework assignment adapted to this cognitive level"
}}"""

    # ── User Prompt ─────────────────────────────────────────────────────────
    # Pass each section separately so the model clearly understands
    # what it is rewriting vs what stays the same
    user = f"""Lesson objective: {objective}

Sections to adapt:

Guided Practice:
{guided}

Independent Practice:
{indep}

Closing:
{closing}

Homework:
{homework}

Rewrite all of the above for: {selected['name'][lang]}
Apply these action verbs: {selected['verbs'][lang]}
Use this strategy: {selected['strategy'][lang]}"""

    raw = call_llm(
        system_prompt=system,
        user_prompt=user,
        provider=provider or DEFAULT_PROVIDER,
        tier="balanced",    # Full model needed — quality matters for differentiation
        temperature=0.5,    # Some creativity allowed within Bloom constraints
        max_tokens=1200     # Enough for all 5 output fields
    )

    raw = raw.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)