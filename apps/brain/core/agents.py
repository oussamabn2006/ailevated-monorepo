"""
agents.py — Core AI Agents for AILEVATED Curriculum Engine
=============================================================
Contains three LLM-powered agents and one pure Python assembler:

  Agent 1 (curriculum_agent)  — Extracts objectives from Ministry PDF chunks
  Agent 2 (architect_agent)   — Designs the 10-section lesson structure
  Assembler (assemble_lesson) — Builds final JSON deterministically (no LLM)
  Evaluator (evaluate_lesson) — Scores lesson quality on 5 criteria

All agents call the unified LLM interface from llm_provider.py,
so the underlying model (Groq / Gemini / Anthropic) is swappable
without touching this file.
"""

import os
import json
from dotenv import load_dotenv
from core.llm_provider import call_llm

load_dotenv()

# Default provider read from .env (LLM_PROVIDER=groq|gemini|anthropic)
# If not set, llm_provider.py auto-selects the first available key
DEFAULT_PROVIDER = os.getenv("LLM_PROVIDER") or None

# ── Section Labels ─────────────────────────────────────────────────────────────
# Python controls ALL section labels — the LLM never generates them.
# This is the key design decision that eliminates language mixing:
# the model only generates semantic content, never structural text.
# Adding a new language = add a new key here, nothing else changes.
LABELS = {
    "ar": {
        "title": "خطة الدرس",
        "subject": "المادة", "grade": "المستوى", "topic": "الموضوع",
        "objective": "الهدف",
        "assessment": "التقويم",
        "key_points": "النقاط الأساسية",
        "opening": "التمهيد",
        "introduction_to_material": "عرض المحتوى الجديد",
        "guided_practice": "التطبيق الموجه",
        "independent_practice": "التطبيق الحر",
        "closing": "الإغلاق",
        "extension_activity": "نشاط إثرائي",
        "homework": "الواجب المنزلي",
        "standards_addressed": "المعايير والكفايات",
        "prerequisites": "المكتسبات القبلية",
        "competencies": "الكفايات المستهدفة",
        "materials": "الوسائل التعليمية",
    },
    "fr": {
        "title": "Fiche Pédagogique",
        "subject": "Matière", "grade": "Niveau", "topic": "Sujet",
        "objective": "Objectif",
        "assessment": "Évaluation",
        "key_points": "Points clés",
        "opening": "Ouverture",
        "introduction_to_material": "Introduction du nouveau contenu",
        "guided_practice": "Pratique guidée",
        "independent_practice": "Pratique indépendante",
        "closing": "Conclusion",
        "extension_activity": "Activité d'enrichissement",
        "homework": "Devoir maison",
        "standards_addressed": "Standards et compétences",
        "prerequisites": "Prérequis",
        "competencies": "Compétences visées",
        "materials": "Supports didactiques",
    },
    "en": {
        "title": "Lesson Plan",
        "subject": "Subject", "grade": "Grade", "topic": "Topic",
        "objective": "Objective",
        "assessment": "Assessment",
        "key_points": "Key Points",
        "opening": "Opening",
        "introduction_to_material": "Introduction to New Material",
        "guided_practice": "Guided Practice",
        "independent_practice": "Independent Practice",
        "closing": "Closing",
        "extension_activity": "Extension Activity",
        "homework": "Homework",
        "standards_addressed": "Standards Addressed",
        "prerequisites": "Prerequisites",
        "competencies": "Target Competencies",
        "materials": "Teaching Materials",
    }
}


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 1 — Curriculum Analyst
# Role: Extract structured learning objectives from raw Ministry PDF chunks.
# Input:  curriculum_context (retrieved chunks from Supabase RAG search)
# Output: JSON with prerequisites, competencies, materials, key_concepts
#
# Uses Chain-of-Thought prompting (Wei et al., 2022) — the model is forced
# to reason step-by-step before extracting, which improves accuracy on
# noisy OCR text from scanned Ministry documents.
# ══════════════════════════════════════════════════════════════════════════════
def curriculum_agent(curriculum_context, subject, grade, topic, language, provider=None):
    """
    Agent 1 — Extracts structured learning objectives from Ministry curriculum chunks.

    Args:
        curriculum_context: Raw text chunks retrieved from Supabase vector search
        subject:            Subject identifier (e.g. "math", "physique_chimie")
        grade:              Grade level (e.g. "2ème Bac")
        topic:              Lesson topic (e.g. "les limites et continuité")
        language:           Output language: "ar" | "fr" | "en"
        provider:           LLM provider override. None = use DEFAULT_PROVIDER

    Returns:
        dict with keys: prerequisites, competencies, materials, key_concepts
    """

    # Chain-of-Thought: forces model to read → identify → extract → return
    # rather than pattern-matching keywords, which fails on noisy OCR text
    system = f"""You are a Moroccan curriculum analyst.
Write ONLY in {language}. No other language.

Follow these steps before responding:
Step 1: Read the curriculum context carefully.
Step 2: Identify which parts are relevant to the subject and topic.
Step 3: Extract ONLY the specific competencies, prerequisites and key concepts.
Step 4: Return your result as JSON.

Return ONLY a JSON object. No markdown. No explanation.
{{
  "prerequisites": ["string", "string"],
  "competencies": ["string", "string", "string"],
  "materials": ["string", "string", "string"],
  "key_concepts": ["string", "string"]
}}"""

    user = f"""Curriculum context:
{curriculum_context}

Extract for:
Subject: {subject} | Grade: {grade} | Topic: {topic}"""

    raw = call_llm(
        system_prompt=system,
        user_prompt=user,
        provider=provider or DEFAULT_PROVIDER,
        tier="balanced",    # Medium model — quality matters here
        temperature=0.3,    # Low temperature = deterministic extraction
        max_tokens=600
    )

    # Strip markdown fences in case the model adds them despite instructions
    raw = raw.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


# ══════════════════════════════════════════════════════════════════════════════
# AGENT 2 — Lesson Architect
# Role: Design the complete 10-section lesson plan based on extracted objectives.
# Input:  learning_objectives (output of Agent 1) + lesson parameters
# Output: JSON with all 10 pedagogical sections
#
# Uses Few-Shot prompting (Brown et al., 2020) — a complete biology example
# anchors the model to the expected level of specificity and detail.
# Without this example the model produces vague, generic descriptions.
#
# The 10-section format (objective → assessment → key_points → opening →
# introduction → guided_practice → independent_practice → closing →
# extension_activity → homework) is derived from analysis of professional
# lesson planning frameworks used in international edtech platforms.
# ══════════════════════════════════════════════════════════════════════════════
def architect_agent(learning_objectives, subject, grade, topic, duration, language,
                    lesson_type="new_concept", objective=None, provider=None):
    """
    Agent 2 — Designs the complete 10-section lesson structure.

    Args:
        learning_objectives: dict output from curriculum_agent
        subject:             Subject identifier
        grade:               Grade level
        topic:               Lesson topic
        duration:            Lesson duration in minutes
        language:            Output language: "ar" | "fr" | "en"
        lesson_type:         Pedagogical type: new_concept | review | lab |
                             discussion | assessment
        objective:           Optional custom objective from the teacher
                             (injected directly into the prompt)
        provider:            LLM provider override

    Returns:
        dict with keys: sections (10-section dict), labels (language-specific labels)
    """

    lang = language if language in LABELS else "fr"

    # If teacher provided a custom objective, prepend it to the user prompt
    # so the model uses it as the primary anchor for the lesson design
    objective_hint = f"Custom Objective: {objective}\n\n" if objective else ""

    # Few-shot example: one complete lesson in English anchors the format.
    # The model learns what "specific" means from this example —
    # not just "students practice" but exactly what they do, with what, in groups of how many.
    few_shot = """
EXAMPLE (Biology — Food Webs, Grade 8):

Objective: Students will be able to describe how food webs depict feeding relationships between organisms in an ecosystem.
Assessment: Students complete a worksheet identifying organisms as producers, primary consumers, secondary consumers, or decomposers.
Key Points:
- Food webs show feeding relationships between organisms in an ecosystem.
- Producers use photosynthesis to create energy from sunlight.
- Primary consumers eat producers; secondary consumers eat primary consumers.
- Decomposers break down dead matter and return nutrients to the soil.
- Removing one organism from a food web affects the entire ecosystem.
Opening: Display an image of a food web and ask students: "How are these organisms connected to each other?" Allow 2 minutes of pair discussion.
Introduction to New Material: Define food web and distinguish it from a food chain. Walk through a sample food web on the board — label each organism, draw arrows showing energy flow, explain what arrows represent. Address the common misconception that arrows show "what eats what" rather than "where energy flows."
Guided Practice: In groups of 3, students receive a printed food web diagram and answer guided questions: identify one producer, trace a food chain with 4 links, and predict what happens if rabbits disappear.
Independent Practice: Students complete a worksheet where they label a new food web, identify the trophic level of each organism, and explain one consequence of removing a named species.
Closing: Cold-call 3 students to share one thing they learned. Summarize the 4 key points on the board. Connect to the next lesson: "Next class we explore how human activity disrupts food webs."
Extension Activity: Provide a more complex food web with 12 organisms. Students must identify all producers, construct two complete food chains of 4+ links, and write a paragraph predicting the cascade effect of removing the top predator.
Homework: Research a real ecosystem (rainforest, ocean, desert). Identify 5 organisms and draw or describe the food web connecting them.
Standards Addressed: NGSS MS-LS2-3 — Develop a model to describe the cycling of matter and flow of energy.

Now design in this same clear, specific, document-like format.
"""

    # Strict language enforcement in system prompt.
    # Note: section labels are NOT generated by the LLM — they come from
    # the LABELS dict in assemble_lesson. The model only generates content.
    system = f"""You are a professional lesson plan writer for Moroccan secondary schools.
Write ONLY in {language}. No other language. Not a single word in any other language.
Return ONLY a valid JSON object. No markdown fences. No explanation before or after.

{{
  "objective": "string — one sentence, starts with students will be able to",
  "assessment": "string — one sentence describing how learning is measured",
  "key_points": ["string", "string", "string", "string"],
  "opening": "string — specific hook activity with teacher actions and expected student response",
  "introduction_to_material": "string — detailed explanation of new content, specific teacher moves",
  "guided_practice": "string — structured activity with teacher support, specific steps",
  "independent_practice": "string — student solo work, specific task description",
  "closing": "string — synthesis activity, how teacher wraps up and previews next lesson",
  "extension_activity": "string — for early finishers, higher complexity task",
  "homework": "string — specific take-home assignment",
  "standards_addressed": ["string", "string"]
}}"""

    user = f"""{few_shot}

Learning Objectives extracted from curriculum:
{json.dumps(learning_objectives, ensure_ascii=False)}

{objective_hint}Design a complete lesson for:
Subject: {subject} | Grade: {grade} | Topic: {topic}
Lesson type: {lesson_type}
Duration: {duration} minutes

Be specific, practical, and appropriate for a Moroccan classroom.
Use concrete examples, real student actions, and measurable activities."""

    raw = call_llm(
        system_prompt=system,
        user_prompt=user,
        provider=provider or DEFAULT_PROVIDER,
        tier="balanced",    # Most important call — uses the best balanced model
        temperature=0.5,    # Slightly higher temp for creative lesson design
        max_tokens=2000     # Needs room for all 10 sections
    )

    raw = raw.strip().replace("```json", "").replace("```", "").strip()
    sections = json.loads(raw)

    # Return sections alongside the correct language labels
    # Labels are passed to assemble_lesson which builds the final JSON
    L = LABELS[lang]
    return {
        "sections": sections,
        "labels": L
    }


# ══════════════════════════════════════════════════════════════════════════════
# ASSEMBLER — Pure Python, Zero LLM
# Role: Build the final lesson JSON from Agent 1 + Agent 2 outputs.
# This function makes NO LLM calls — it is 100% deterministic.
#
# Key design principle: Python controls all structure, formatting, and labels.
# The LLM only ever generates the semantic content of each section.
# This eliminates language mixing in structural elements (section headers,
# metadata fields) which was the most persistent quality problem during
# development.
# ══════════════════════════════════════════════════════════════════════════════
def assemble_lesson(subject, grade, topic, duration, language, lesson_type,
                    objectives, structure):
    """
    Pure Python assembler — builds the final lesson JSON with no LLM calls.

    Args:
        subject:      Subject identifier
        grade:        Grade level
        topic:        Lesson topic
        duration:     Duration in minutes (stored in metadata only)
        language:     Output language — used to select correct LABELS
        lesson_type:  Pedagogical type (stored in metadata)
        objectives:   dict from curriculum_agent (prerequisites, competencies, materials)
        structure:    dict from architect_agent (sections + labels)

    Returns:
        Complete lesson plan dict ready to be returned by the API
    """

    # Fall back to French if an unknown language code is passed
    lang = language if language in LABELS else "fr"
    L = LABELS[lang]
    sections = structure["sections"]

    return {
        "metadata": {
            "title":        L["title"],       # e.g. "Fiche Pédagogique"
            "subject":      subject,
            "grade":        grade,
            "topic":        topic,
            "lesson_type":  lesson_type,
            "language":     language
        },
        "labels":       L,                    # Full label dict for the frontend to use
        "prerequisites": objectives.get("prerequisites", []),
        "competencies":  objectives.get("competencies", []),
        "materials":     objectives.get("materials", []),
        "sections": {
            # Preserve insertion order — this is the display order in the UI
            "objective":                sections.get("objective", ""),
            "assessment":               sections.get("assessment", ""),
            "key_points":               sections.get("key_points", []),
            "opening":                  sections.get("opening", ""),
            "introduction_to_material": sections.get("introduction_to_material", ""),
            "guided_practice":          sections.get("guided_practice", ""),
            "independent_practice":     sections.get("independent_practice", ""),
            "closing":                  sections.get("closing", ""),
            "extension_activity":       sections.get("extension_activity", ""),
            "homework":                 sections.get("homework", ""),
            "standards_addressed":      sections.get("standards_addressed", []),
        }
    }


# ══════════════════════════════════════════════════════════════════════════════
# EVALUATOR — LLM-as-Evaluator (Node 5 in the LangGraph pipeline)
# Role: Automatically score the generated lesson on 5 pedagogical criteria.
# Input:  The complete assembled lesson plan
# Output: JSON scores (1-5) + one sentence of feedback
#
# Uses the LLM-as-Evaluator pattern (Schulhoff et al., 2024).
# Uses "fast" tier — evaluation is less critical than generation,
# so we use the smaller/cheaper model to save cost and latency.
# ══════════════════════════════════════════════════════════════════════════════
def evaluate_lesson(lesson_plan, language, provider=None):
    """
    Evaluator — Scores the lesson plan on 5 criteria using LLM-as-Evaluator.

    Args:
        lesson_plan: Complete lesson dict from assemble_lesson
        language:    Language for the feedback sentence
        provider:    LLM provider override

    Returns:
        dict with scores (1-5) for: curriculum_alignment, bloom_taxonomy_coverage,
        clarity, moroccan_context, overall — plus a feedback string
    """

    lang = language if language in ["ar", "fr", "en"] else "fr"

    system = f"""You are a Moroccan curriculum quality evaluator.
Write ONLY in {lang}.
Return ONLY a JSON object. No markdown. No explanation.

{{
  "curriculum_alignment": 1-5,
  "bloom_taxonomy_coverage": 1-5,
  "clarity": 1-5,
  "moroccan_context": 1-5,
  "overall": 1-5,
  "feedback": "one constructive sentence"
}}

Scoring: 5=Excellent, 4=Good, 3=Acceptable, 2=Needs improvement, 1=Poor"""

    user = f"Evaluate this lesson plan:\n{json.dumps(lesson_plan, ensure_ascii=False)}"

    raw = call_llm(
        system_prompt=system,
        user_prompt=user,
        provider=provider or DEFAULT_PROVIDER,
        tier="fast",        # Smaller model is sufficient for evaluation scoring
        temperature=0.1,    # Very low — we want consistent, deterministic scores
        max_tokens=300      # Short output — just the JSON scores
    )

    raw = raw.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)