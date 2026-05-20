"""
graph.py — LangGraph Pipeline Orchestrator
==========================================
Defines the 5-node state machine that orchestrates lesson generation.

Pipeline flow:
  [START]
    → retrieve_node         (Node 1) — Vector search in Supabase
    → curriculum_agent_node (Node 2) — Extract objectives from chunks
    → architect_agent_node  (Node 3) — Design + assemble lesson
    → differentiate_node    (Node 4) — Generate Bloom variants
    → evaluate_node         (Node 5) — Score lesson quality
  [END]

State is passed as a typed dict (LessonState) between nodes.
Each node receives the full state and returns only the fields it modifies.
If a node sets state["error"], subsequent nodes skip their LLM calls.

The provider field flows through all nodes so the same LLM model
is used consistently across the entire pipeline for a single request.
"""

from typing import TypedDict, Optional, Any
from langgraph.graph import StateGraph, START, END


# ── Shared State Schema ────────────────────────────────────────────────────────
# TypedDict enforces the contract between nodes at type-check time.
# Every field that any node reads or writes must be declared here.
# Undeclared fields will raise errors during development, not at runtime.
class LessonState(TypedDict):
    # ── Input fields (set by the API before invoking the graph) ──
    subject:     str            # e.g. "math", "physique_chimie"
    grade:       str            # e.g. "2ème Bac"
    topic:       str            # e.g. "les limites et continuité"
    duration:    int            # Lesson duration in minutes
    language:    str            # "ar" | "fr" | "en"
    lesson_type: str            # "new_concept" | "review" | "lab" | "discussion" | "assessment"
    track:       str            # "sm_a" | "sm_b" | "svt" | "spc" | "lettres" | "economie" | "tech"
    provider:    Optional[str]  # "groq" | "gemini" | "anthropic" | None (auto)
    objective:   Optional[str]  # Optional custom teacher objective

    # ── Pipeline intermediate fields (set by nodes as pipeline runs) ──
    curriculum_context:  str    # Raw text chunks from Supabase (set by retrieve_node)
    learning_objectives: Any    # Structured objectives dict (set by curriculum_agent_node)
    lesson_structure:    str    # Raw architect_agent output, stored for debugging
    chunks_used:         list   # List of Supabase chunks with similarity scores

    # ── Output fields (set by nodes, returned in the API response) ──
    lesson_plan:       Any      # Complete assembled lesson dict
    support_variant:   Any      # Bloom support differentiation
    extension_variant: Any      # Bloom extension differentiation
    quality_score:     Any      # Auto-evaluation scores dict

    # ── Error handling ──
    error: str                  # If set, downstream nodes skip their LLM calls


# ══════════════════════════════════════════════════════════════════════════════
# NODE 1 — Retrieval
# Queries Supabase with subject + topic as a semantic search query.
# Applies a 3-level fallback strategy to guarantee results even when
# the knowledge base has incomplete coverage for a given combination:
#   Level 1: Filter by grade + subject + track  (most precise)
#   Level 2: Filter by grade + subject only     (drop track constraint)
#   Level 3: No filter at all                   (global fallback)
# Each fallback level is logged so alignment issues can be diagnosed.
# ══════════════════════════════════════════════════════════════════════════════
def retrieve_node(state: LessonState) -> dict:
    """
    Node 1 — Semantic vector search in Supabase with metadata filtering.

    Returns:
        curriculum_context: Formatted string of retrieved chunks
        chunks_used:        Raw chunk list with similarity scores (for API response)
    """
    print(f"📚 [Node 1] Retrieving context for {state['subject']} | track={state.get('track')}...")

    try:
        # Import here (not at module level) to avoid circular imports
        # and to allow the module to load even if Supabase is not yet configured
        from scripts.ingest import embed_model, supabase

        # Combine subject + topic for a richer semantic query
        # e.g. "math les limites et continuité" retrieves more relevant chunks
        # than just "les limites et continuité" alone
        search_query = f"{state['subject']} {state['topic']}"
        query_embedding = embed_model.encode(search_query).tolist()

        # ── Grade normalization ──────────────────────────────────────────────
        # Teachers may type "2ème Bac", "2eme bac", "2éme Bac" etc.
        # We normalize all variants to the canonical form stored in Supabase: "2bac"
        grade_filter = state['grade'].lower().strip()
        grade_filter = (grade_filter
                        .replace("ème bac", "bac")
                        .replace("eme bac", "bac")
                        .replace("ème", "bac")
                        .replace(" ", ""))

        # ── Subject normalization ────────────────────────────────────────────
        # Teachers and the Streamlit UI may send subject names in Arabic, French,
        # or English. This map normalizes all variants to the canonical identifiers
        # stored in Supabase (which match the folder structure of ingested PDFs).
        subject_map = {
            "english": "english", "anglais": "english",
            "français": "french", "french": "french", "francais": "french",
            "الفلسفة": "philosophie", "philosophie": "philosophie",
            "الفيزياء والكيمياء": "physique_chimie", "physique": "physique_chimie",
            "physique_chimie": "physique_chimie", "physique chimie": "physique_chimie",
            "الرياضيات": "math", "math": "math",
            "mathématiques": "math", "mathematiques": "math",
            "svt": "svt", "علوم الحياة والأرض": "svt",
            "اللغة العربية": "arabic", "arabic": "arabic", "arabe": "arabic",
            "histoire_geo": "histoire_geo", "histoire": "histoire_geo",
            "التاريخ والجغرافيا": "histoire_geo",
            "sciences_ingenieur": "sciences_ingenieur",
            "economie_generale": "economie_generale",
            "comptabilite": "comptabilite", "comptabilité": "comptabilite",
            "organisation_entreprise": "organisation_entreprise",
            "education_islamique": "education_islamique",
            "التربية الإسلامية": "education_islamique",
            "sport": "sport"
        }

        subject_filter = subject_map.get(state['subject'].lower().strip())
        track_filter   = state.get('track') if state.get('track') else None

        # ── Level 1: Full filter (grade + subject + track) ───────────────────
        result = supabase.rpc("match_curriculum_chunks", {
            "query_embedding": query_embedding,
            "match_threshold": 0.18,    # Minimum cosine similarity to include a chunk
            "match_count":     8,       # Max chunks to retrieve
            "filter_grade":    grade_filter,
            "filter_subject":  subject_filter,
            "filter_track":    track_filter
        }).execute()
        all_chunks = result.data

        # ── Level 2: Drop track filter ───────────────────────────────────────
        if not all_chunks:
            print("⚠️ No results with track filter, trying without track...")
            result = supabase.rpc("match_curriculum_chunks", {
                "query_embedding": query_embedding,
                "match_threshold": 0.18,
                "match_count":     8,
                "filter_grade":    grade_filter,
                "filter_subject":  subject_filter,
                "filter_track":    None
            }).execute()
            all_chunks = result.data

        # ── Level 3: Global fallback — no metadata filters at all ────────────
        if not all_chunks:
            print("⚠️ No results with subject filter, falling back to unfiltered...")
            result = supabase.rpc("match_curriculum_chunks", {
                "query_embedding": query_embedding,
                "match_threshold": 0.18,
                "match_count":     5,
                "filter_grade":    None,
                "filter_subject":  None,
                "filter_track":    None
            }).execute()
            all_chunks = result.data

        print(f"✅ Retrieved {len(all_chunks)} chunks")

        # Format chunks as a readable context string for the LLM prompt
        # Each chunk includes its source file and similarity score for transparency
        context = "\n\n---\n\n".join([
            f"[Source: {c['source']} | Similarity: {c['similarity']:.2f}]\n{c['content']}"
            for c in all_chunks
        ])

        return {
            "curriculum_context": context,
            "chunks_used": all_chunks  # Passed through to the API response for alignment score
        }

    except Exception as e:
        print(f"❌ Retrieval error: {e}")
        # Set error in state — downstream nodes will check this and skip
        return {"error": str(e), "chunks_used": []}


# ══════════════════════════════════════════════════════════════════════════════
# NODE 2 — Curriculum Agent
# Calls curriculum_agent() from agents.py.
# Extracts structured learning objectives from the retrieved chunks.
# Skips if state["error"] is already set by retrieve_node.
# ══════════════════════════════════════════════════════════════════════════════
def curriculum_agent_node(state: LessonState) -> dict:
    """Node 2 — Extracts learning objectives from curriculum chunks."""
    print("🎯 [Node 2] Curriculum Agent...")
    print(f"   Provider in state: {state.get('provider')}")

    # Skip if a previous node set an error
    if state.get("error"):
        return {}

    try:
        from core.agents import curriculum_agent
        objectives = curriculum_agent(
            curriculum_context=state["curriculum_context"],
            subject=state["subject"],
            grade=state["grade"],
            topic=state["topic"],
            language=state["language"],
            provider=state.get("provider")   # Pass provider from state
        )
        return {"learning_objectives": objectives}
    except Exception as e:
        return {"error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# NODE 3 — Architect Agent
# Calls architect_agent() then assemble_lesson() from agents.py.
# Two steps in one node:
#   1. architect_agent() — LLM designs the 10 sections
#   2. assemble_lesson() — Pure Python builds the final JSON (no LLM)
# The separation ensures Python controls all formatting and labels.
# ══════════════════════════════════════════════════════════════════════════════
def architect_agent_node(state: LessonState) -> dict:
    """Node 3 — Designs lesson structure and assembles final lesson JSON."""
    print("🏗️  [Node 3] Architect Agent...")

    if state.get("error"):
        return {}

    try:
        from core.agents import architect_agent, assemble_lesson

        # Step 1: LLM generates the 10-section content
        structure = architect_agent(
            learning_objectives=state["learning_objectives"],
            subject=state["subject"],
            grade=state["grade"],
            topic=state["topic"],
            duration=state["duration"],
            language=state["language"],
            lesson_type=state.get("lesson_type", "new_concept"),
            objective=state.get("objective"),   # Optional custom teacher objective
            provider=state.get("provider")
        )

        # Step 2: Pure Python assembles the final lesson JSON
        # No LLM call — Python controls all labels and structure
        lesson = assemble_lesson(
            subject=state["subject"],
            grade=state["grade"],
            topic=state["topic"],
            duration=state["duration"],
            language=state["language"],
            lesson_type=state.get("lesson_type", "new_concept"),
            objectives=state["learning_objectives"],
            structure=structure
        )

        print("✅ Lesson assembled")
        return {
            "lesson_plan":      lesson,
            "lesson_structure": str(structure)  # Store raw structure for debugging
        }
    except Exception as e:
        return {"error": str(e)}


# ══════════════════════════════════════════════════════════════════════════════
# NODE 4 — Differentiation
# Generates two Bloom variants by calling generate_differentiation() twice.
# Support (Bloom 1-2) and Extension (Bloom 4-6) are generated sequentially.
# TODO: Parallelize with asyncio.gather to halve latency (Phase 5 optimization)
# ══════════════════════════════════════════════════════════════════════════════
def differentiate_node(state: LessonState) -> dict:
    """Node 4 — Generates Support and Extension Bloom differentiation variants."""
    print("🧠 [Node 4] Differentiating...")

    # Skip if no lesson was generated (error in previous node)
    if not state.get("lesson_plan"):
        return {}

    try:
        from core.differentiation_agent import generate_differentiation

        # Generate both variants — sequential for now, parallel in Phase 5
        support   = generate_differentiation(
            state["lesson_plan"], "support",   state["language"], state.get("provider")
        )
        extension = generate_differentiation(
            state["lesson_plan"], "extension", state["language"], state.get("provider")
        )

        print("✅ Differentiation Complete")
        return {"support_variant": support, "extension_variant": extension}

    except Exception as e:
        # Differentiation failure is non-fatal — lesson plan still usable
        return {"error": f"Differentiation error: {str(e)}"}


# ══════════════════════════════════════════════════════════════════════════════
# NODE 5 — Quality Evaluator
# Uses the LLM-as-Evaluator pattern to score the generated lesson.
# Failure here is non-fatal — returns None scores rather than crashing.
# Uses "fast" tier (smaller/cheaper model) since evaluation is less critical.
# TODO: Run this in background after streaming starts (Phase 5 optimization)
# ══════════════════════════════════════════════════════════════════════════════
def evaluate_node(state: LessonState) -> dict:
    """Node 5 — Auto-evaluates lesson quality on 5 criteria (LLM-as-Evaluator)."""
    print("🔍 [Node 5] Self-evaluating lesson quality...")

    if not state.get("lesson_plan"):
        return {}

    try:
        from core.agents import evaluate_lesson
        score = evaluate_lesson(
            state["lesson_plan"],
            state["language"],
            state.get("provider")
        )
        print(f"✅ Quality score: {score.get('overall')}/5")
        return {"quality_score": score}

    except Exception as e:
        # Evaluation failure is non-fatal — lesson is still returned without scores
        print(f"⚠️ Evaluation failed (non-fatal): {e}")
        return {"quality_score": None}


# ══════════════════════════════════════════════════════════════════════════════
# GRAPH COMPILATION
# build_lesson_graph() wires the 5 nodes into a linear pipeline.
# The compiled graph is a singleton — compiled once at module import,
# reused for every request. Recompiling on every request would add latency.
# ══════════════════════════════════════════════════════════════════════════════
def build_lesson_graph():
    """Builds and compiles the LangGraph state machine. Called once at startup."""
    graph = StateGraph(LessonState)

    # Register nodes
    graph.add_node("retrieve",          retrieve_node)
    graph.add_node("curriculum_agent",  curriculum_agent_node)
    graph.add_node("architect_agent",   architect_agent_node)
    graph.add_node("differentiate",     differentiate_node)
    graph.add_node("evaluate",          evaluate_node)

    # Wire edges — linear pipeline, no branching
    graph.add_edge(START,              "retrieve")
    graph.add_edge("retrieve",         "curriculum_agent")
    graph.add_edge("curriculum_agent", "architect_agent")
    graph.add_edge("architect_agent",  "differentiate")
    graph.add_edge("differentiate",    "evaluate")
    graph.add_edge("evaluate",         END)

    return graph.compile()


# Compile once at import time — reused for all requests
lesson_graph = build_lesson_graph()