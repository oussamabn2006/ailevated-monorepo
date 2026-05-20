"""
AILEVATED — Streamlit Testing Interface
Run: streamlit run ailevated_app.py
Requires FastAPI running: cd apps/brain && uvicorn main:app --reload --port 8000
"""

import streamlit as st
import requests
import json
import time

st.set_page_config(
    page_title="AILEVATED",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; }

:root {
    --bg:         #ffffff;
    --surface:    #ffffff;
    --border:     #e5e7eb;
    --border-2:   #d1d5db;
    --ink:        #111827;
    --ink-2:      #374151;
    --ink-3:      #6b7280;
    --ink-4:      #9ca3af;
    --primary:    #7c3aed;
    --primary-light: #a855f7;
    --secondary:  #fbbf24;
    --success:    #10b981;
    --warning:    #f59e0b;
    --error:      #ef4444;
    --radius:     8px;
    --radius-lg:  12px;
    --shadow-sm:  0 1px 2px 0 rgba(0,0,0,0.05);
    --shadow:     0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
}

html, body,
[data-testid="stApp"],
[data-testid="stAppViewContainer"],
.stApp, .main {
    background: var(--bg) !important;
    color: var(--ink) !important;
    font-family: 'Inter', sans-serif !important;
}

.block-container {
    padding-top: 2rem !important;
    padding-bottom: 4rem !important;
    max-width: 1180px !important;
}

section[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] > div { padding: 1.5rem 1.2rem !important; }
section[data-testid="stSidebar"] * {
    color: var(--ink) !important;
    font-family: 'Inter', sans-serif !important;
}

.stSelectbox > div > div,
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea > div > div > textarea {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    color: var(--ink) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.9rem !important;
    box-shadow: var(--shadow-sm) !important;
    transition: border-color 0.15s !important;
}
.stSelectbox > div > div:focus-within,
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px rgba(124,58,237,0.08) !important;
}

.stFormSubmitButton > button {
    background: var(--primary) !important;
    color: #fff !important;
    border: none !important;
    border-radius: var(--radius) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.92rem !important;
    font-weight: 600 !important;
    padding: 0.7rem 2rem !important;
    width: 100% !important;
    box-shadow: 0 2px 8px rgba(124,58,237,0.3) !important;
    transition: all 0.15s !important;
    letter-spacing: 0.01em !important;
}
.stFormSubmitButton > button:hover {
    background: var(--primary-light) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 14px rgba(124,58,237,0.35) !important;
}

.stButton > button {
    background: var(--surface) !important;
    color: var(--ink) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    box-shadow: var(--shadow-sm) !important;
}
.stButton > button:hover {
    border-color: var(--primary) !important;
    color: var(--primary) !important;
}

div[data-testid="metric-container"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-lg) !important;
    padding: 1rem 1.2rem !important;
    box-shadow: var(--shadow-sm) !important;
}
div[data-testid="metric-container"] label {
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    color: var(--ink-3) !important;
}

.stTabs [data-baseweb="tab-list"] {
    background: var(--bg) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    padding: 3px !important;
    gap: 2px !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--ink-3) !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    border: none !important;
    padding: 0.45rem 1.1rem !important;
    font-family: 'Inter', sans-serif !important;
}
.stTabs [aria-selected="true"] {
    background: var(--surface) !important;
    color: var(--ink) !important;
    font-weight: 600 !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.1) !important;
}

div[data-testid="stInfo"]    { background: #eff6ff !important; border: 1px solid #bfdbfe !important; border-radius: var(--radius) !important; color: #1e40af !important; }
div[data-testid="stSuccess"] { background: #f0fdf4 !important; border: 1px solid #bbf7d0 !important; border-radius: var(--radius) !important; color: #15803d !important; }
div[data-testid="stWarning"] { background: #fffbeb !important; border: 1px solid #fde68a !important; border-radius: var(--radius) !important; color: #92400e !important; }
div[data-testid="stError"]   { background: #fef2f2 !important; border: 1px solid #fecaca !important; border-radius: var(--radius) !important; }

hr { border: none !important; border-top: 1px solid var(--border) !important; margin: 1.5rem 0 !important; }

.stDownloadButton > button {
    background: var(--surface) !important;
    color: var(--primary) !important;
    border: 1px solid var(--primary) !important;
    border-radius: var(--radius) !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
}
.stDownloadButton > button:hover {
    background: var(--primary) !important;
    color: #fff !important;
}

::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border-2); border-radius: 3px; }

[data-testid="stAppHeader"] { display: none !important; }
header[data-testid="stHeader"] { display: none !important; }

.hero {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    margin-bottom: 1.8rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid var(--border);
}
.hero-wordmark {
    font-family: 'Inter', sans-serif !important;
    font-size: 1.9rem;
    font-weight: 700;
    color: var(--ink);
    letter-spacing: -0.03em;
    line-height: 1;
    margin-bottom: 0.35rem;
}
.hero-wordmark span { color: var(--primary); }
.hero-desc {
    font-size: 0.86rem;
    color: var(--ink-3);
    font-weight: 400;
    max-width: 460px;
    line-height: 1.55;
}
.hero-stat-num {
    font-size: 2.2rem;
    font-weight: 700;
    color: var(--primary);
    line-height: 1;
    text-align: right;
}
.hero-stat-label {
    font-size: 0.7rem;
    color: var(--ink-4);
    font-weight: 500;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-top: 2px;
    text-align: right;
}

.form-label {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--ink-3);
    margin-bottom: 0.25rem;
    margin-top: 0.05rem;
}

.lang-badge {
    display: inline-block;
    background: rgba(124,58,237,0.07);
    border: 1px solid rgba(124,58,237,0.2);
    color: var(--primary);
    border-radius: 999px;
    padding: 0.2rem 0.75rem;
    font-size: 0.75rem;
    font-weight: 600;
    margin-top: 0.4rem;
}

.qbar-wrap {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1rem 1.2rem;
    margin-bottom: 0.5rem;
    box-shadow: var(--shadow-sm);
}
.qbar-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem; }
.qbar-label { font-size: 0.84rem; font-weight: 500; color: var(--ink-2); }
.qbar-score { font-size: 1rem; font-weight: 600; color: var(--ink); }
.qbar-track { background: var(--bg); border-radius: 999px; height: 5px; overflow: hidden; border: 1px solid var(--border); }
.qbar-fill { height: 100%; border-radius: 999px; }

.src-row {
    display: flex; align-items: center; gap: 0.6rem;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 0.55rem 0.9rem;
    margin-bottom: 0.35rem; font-size: 0.82rem; color: var(--ink-2);
}
.src-score {
    display: inline-block; border-radius: 999px;
    padding: 0.12rem 0.5rem; font-size: 0.7rem; font-weight: 700; flex-shrink: 0;
}
.ss-h { background: #d1fae5; color: #065f46; }
.ss-m { background: #fef3c7; color: #92400e; }
.ss-l { background: #fee2e2; color: #991b1b; }

.bloom-badge {
    display: inline-block;
    font-size: 0.67rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
    padding: 0.2rem 0.65rem; border-radius: 4px; margin-bottom: 0.75rem;
}
.bloom-s { background: #dbeafe; color: #1e40af; border: 1px solid #bfdbfe; }
.bloom-e { background: #ede9fe; color: #5b21b6; border: 1px solid #ddd6fe; }

.section-block {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 1.1rem 1.2rem;
    margin-bottom: 0.5rem;
    box-shadow: var(--shadow-sm);
}
.act-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.65rem; }
.act-block {
    background: var(--bg); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 0.85rem 1rem;
}
.act-role {
    font-size: 0.67rem; font-weight: 700;
    letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 0.3rem;
}
.role-t { color: #2563eb; }
.role-s { color: #059669; }
.act-text { font-size: 0.87rem; color: var(--ink-2); line-height: 1.6; }

.sidebar-logo {
    font-family: 'Inter', sans-serif !important;
    font-size: 1.45rem; font-weight: 700;
    color: var(--ink) !important; letter-spacing: -0.02em;
}
.sidebar-logo span { color: var(--primary) !important; }

.status-ok  { display: inline-block; width: 7px; height: 7px; background: #22c55e; border-radius: 50%; margin-right: 5px; vertical-align: middle; }
.status-err { display: inline-block; width: 7px; height: 7px; background: #ef4444; border-radius: 50%; margin-right: 5px; vertical-align: middle; }
</style>
""", unsafe_allow_html=True)


# ── DATA ──────────────────────────────────────────────────────────────────────
TRACKS = {
    "sm_a":     "Sciences Mathématiques A",
    "sm_b":     "Sciences Mathématiques B",
    "svt":      "Sciences de la Vie et de la Terre",
    "spc":      "Sciences Physiques & Chimie",
    "lettres":  "Lettres & Sciences Humaines",
    "economie": "Économie & Gestion",
    "tech":     "Sciences Techniques",
}

SUBJECTS_BY_TRACK = {
    "sm_a":     ["math", "physique_chimie", "svt", "arabic", "french", "english", "education_islamique", "sport"],
    "sm_b":     ["math", "physique_chimie", "sciences_ingenieur", "arabic", "french", "english", "education_islamique"],
    "svt":      ["svt", "physique_chimie", "math", "arabic", "french", "english", "histoire_geo", "education_islamique"],
    "spc":      ["physique_chimie", "math", "svt", "arabic", "french", "english", "education_islamique"],
    "lettres":  ["arabic", "french", "english", "philosophie", "histoire_geo", "education_islamique"],
    "economie": ["economie_generale", "comptabilite", "organisation_entreprise", "math", "arabic", "french", "english", "education_islamique"],
    "tech":     ["sciences_ingenieur", "physique_chimie", "math", "arabic", "french", "english", "education_islamique"],
}

SUBJECT_LABELS = {
    "math":                    "Mathématiques",
    "physique_chimie":         "Physique-Chimie",
    "svt":                     "SVT",
    "arabic":                  "Langue Arabe",
    "french":                  "Langue Française",
    "english":                 "Anglais",
    "philosophie":             "Philosophie",
    "histoire_geo":            "Histoire-Géographie",
    "education_islamique":     "Éducation Islamique",
    "sport":                   "Sport",
    "sciences_ingenieur":      "Sciences de l'Ingénieur",
    "economie_generale":       "Économie Générale",
    "comptabilite":            "Comptabilité",
    "organisation_entreprise": "Organisation de l'Entreprise",
}

# ── Language is determined by subject — teacher does not choose ───────────────
SUBJECT_LANGUAGE = {
    "math":                    "fr",
    "physique_chimie":         "fr",
    "svt":                     "fr",
    "arabic":                  "ar",
    "french":                  "fr",
    "english":                 "en",
    "philosophie":             "ar",
    "histoire_geo":            "ar",
    "education_islamique":     "ar",
    "sport":                   "fr",
    "sciences_ingenieur":      "fr",
    "economie_generale":       "fr",
    "comptabilite":            "fr",
    "organisation_entreprise": "fr",
}

LANGUAGE_LABELS = {
    "fr": "🇫🇷 Français",
    "ar": "🇲🇦 Arabe",
    "en": "🇬🇧 Anglais",
}

LESSON_TYPES = {
    "new_concept": "Nouveau concept",
    "review":      "Révision",
    "lab":         "Travaux pratiques",
    "discussion":  "Discussion / Débat",
    "assessment":  "Évaluation",
}

LESSON_ICONS = {
    "new_concept": "📖",
    "review":      "🔄",
    "lab":         "🧪",
    "discussion":  "💬",
    "assessment":  "📝",
}

LLM_PROVIDERS = {
    "groq":      "Groq — Llama 3.3 70B",
    "gemini":    "Google Gemini",
    "anthropic": "Anthropic Claude",
}

API_BASE = "http://localhost:8000"


# ── HELPERS ───────────────────────────────────────────────────────────────────
def check_api():
    try:
        r = requests.get(f"{API_BASE}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def infer_language_frontend(subject_key: str, objective: str = "") -> str:
    """
    Mirror of backend infer_language — frontend uses this to show the teacher
    which language will be used, and to pass correct language to the API.
    Priority: objective text detection > subject default.
    """
    if objective and objective.strip():
        if any("\u0600" <= ch <= "\u06FF" for ch in objective):
            return "ar"
        french_chars = "éèêëàâîôûùçœæÉÈÊËÀÂÎÔÛÙÇ"
        if any(ch in objective for ch in french_chars):
            return "fr"
        english_words = ["students", "learning", "objective", "assess",
                         "practice", "homework", "describe", "understand",
                         "analyze", "evaluate", "will be able"]
        if any(w in objective.lower() for w in english_words):
            return "en"
    return SUBJECT_LANGUAGE.get(subject_key, "fr")


def bar_color(val, out_of=5):
    pct = val / out_of
    if pct >= 0.8: return "#22c55e"
    if pct >= 0.6: return "#f59e0b"
    return "#ef4444"


def quality_bar(label, val, out_of=5):
    pct   = (val / out_of) * 100
    color = bar_color(val, out_of)
    st.markdown(f"""
    <div class="qbar-wrap">
        <div class="qbar-top">
            <span class="qbar-label">{label}</span>
            <span class="qbar-score">{val}<span style="color:#a8a29e;font-size:0.72rem"> / {out_of}</span></span>
        </div>
        <div class="qbar-track">
            <div class="qbar-fill" style="width:{pct:.0f}%;background:{color}"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_diff(level_label, badge_class, data):
    if not data:
        st.info("Non généré.")
        return
    bloom   = data.get("bloom_focus", "")
    app     = data.get("application", {})
    eva     = data.get("evaluation", {})
    hw      = data.get("homework", "")
    t_act   = app.get("teacher_activity", app.get("student_activity", "—"))
    scaff   = app.get("scaffolding", "—")
    eva_act = eva.get("activity", "—")
    crit    = eva.get("success_criteria", "—")

    st.markdown(f'<span class="bloom-badge {badge_class}">{level_label}</span>', unsafe_allow_html=True)
    if bloom:
        st.caption(f"Bloom : {bloom}")

    st.markdown(f"""
    <div class="section-block" style="margin-bottom:0.5rem">
        <div style="font-weight:600;font-size:0.88rem;margin-bottom:0.6rem;padding-bottom:0.4rem;border-bottom:1px solid var(--border)">Application</div>
        <div class="act-grid">
            <div class="act-block"><div class="act-role role-t">Activité</div><div class="act-text">{t_act}</div></div>
            <div class="act-block"><div class="act-role role-s">Étayage</div><div class="act-text">{scaff}</div></div>
        </div>
    </div>
    <div class="section-block" style="margin-bottom:0.5rem">
        <div style="font-weight:600;font-size:0.88rem;margin-bottom:0.6rem;padding-bottom:0.4rem;border-bottom:1px solid var(--border)">Évaluation</div>
        <div class="act-grid">
            <div class="act-block"><div class="act-role role-t">Activité</div><div class="act-text">{eva_act}</div></div>
            <div class="act-block"><div class="act-role role-s">Critères</div><div class="act-text">{crit}</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    if hw:
        st.markdown(f'<div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:0.8rem 1rem;font-size:0.87rem;color:#78350f;margin-top:0.4rem">📚 <strong>Devoir :</strong> {hw}</div>', unsafe_allow_html=True)


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-logo">AI<span>LEVATED</span></div>', unsafe_allow_html=True)
    st.caption("Moteur Curriculaire — 2BAC Maroc")
    st.divider()

    api_ok = check_api()
    if api_ok:
        st.markdown('<span class="status-ok"></span><small style="color:#166534;font-weight:500"> API connectée</small>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-err"></span><small style="color:#991b1b;font-weight:500"> API hors ligne</small>', unsafe_allow_html=True)
        st.code("cd apps/brain\nuvicorn main:app --reload --port 8000", language="bash")

    st.divider()

    if st.button("🔍 Vérifier les providers"):
        try:
            r = requests.get(f"{API_BASE}/api/providers", timeout=5)
            if r.status_code == 200:
                pdata = r.json()
                for name, info in pdata["providers"].items():
                    icon = "✅" if info["available"] else "❌"
                    st.write(f"{icon} {name}")
            else:
                st.warning("Endpoint /api/providers non disponible.")
        except Exception as e:
            st.error(f"Erreur: {e}")


# ── MAIN ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div>
        <div class="hero-wordmark">AI<span>LEVATED</span></div>
        <div class="hero-desc">
            Génération de fiches pédagogiques ancrées sur les programmes officiels
            du Ministère de l'Éducation Nationale 
        </div>
    </div>
    
</div>
""", unsafe_allow_html=True)


# ── FORM ──────────────────────────────────────────────────────────────────────
with st.form("lesson_form"):
    st.markdown('<p class="form-label">Niveau · Filière · Matière</p>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1.5, 1.5, 2])

    with c1:
        grade = st.selectbox("Niveau", ["2ème Bac"], label_visibility="collapsed")

    with c2:
        track_key = st.selectbox(
            "Filière",
            options=list(TRACKS.keys()),
            format_func=lambda k: TRACKS[k],
            label_visibility="collapsed"
        )

    with c3:
        subject_key = st.selectbox(
            "Matière",
            options=SUBJECTS_BY_TRACK[track_key],
            format_func=lambda k: SUBJECT_LABELS.get(k, k),
            label_visibility="collapsed"
        )

    st.markdown('<p class="form-label" style="margin-top:1rem">Sujet de la séance</p>', unsafe_allow_html=True)
    topic = st.text_input(
        "Sujet",
        placeholder="Ex : Transformations nucléaires · Concept de l'Autre · Suffixes et préfixes...",
        label_visibility="collapsed"
    )

    st.markdown('<p class="form-label" style="margin-top:1rem">Objectif / Standard (optionnel)</p>', unsafe_allow_html=True)
    objective = st.text_area(
        "Objectif",
        placeholder="Entrez l'objectif pédagogique ou le standard à adresser...",
        height=68,
        label_visibility="collapsed"
    )

    with st.expander("⚙️ Paramètres avancés", expanded=False):
        ca, cb = st.columns(2)
        with ca:
            st.markdown('<p class="form-label">Type de séance</p>', unsafe_allow_html=True)
            lesson_type = st.selectbox(
                "Type",
                options=list(LESSON_TYPES.keys()),
                format_func=lambda k: f"{LESSON_ICONS[k]} {LESSON_TYPES[k]}",
                label_visibility="collapsed"
            )
        with cb:
            st.markdown('<p class="form-label">Fournisseur LLM</p>', unsafe_allow_html=True)
            provider_key = st.selectbox(
                "Provider",
                options=list(LLM_PROVIDERS.keys()),
                format_func=lambda k: LLM_PROVIDERS[k],
                label_visibility="collapsed"
            )

    submitted = st.form_submit_button("✨ Générer la fiche", use_container_width=True)


# ── GENERATION ────────────────────────────────────────────────────────────────
if submitted:
    if not topic.strip():
        st.warning("Veuillez saisir le sujet de la séance.")
        st.stop()
    if not api_ok:
        st.error("L'API n'est pas disponible. Lancez le serveur FastAPI.")
        st.stop()

    # Infer language from subject + objective text
    lang_key = infer_language_frontend(subject_key, objective)

    # Show teacher which language will be used
    lang_display = LANGUAGE_LABELS.get(lang_key, lang_key)
    st.markdown(
        f'<div class="lang-badge">Langue détectée : {lang_display}</div>',
        unsafe_allow_html=True
    )

    payload = {
        "subject":      subject_key,
        "grade":        grade,
        "topic":        topic.strip(),
        "duration":     45,
        "language":     lang_key,
        "lesson_type":  lesson_type,
        "track":        track_key,
        "provider":     provider_key,
        "objective":    objective.strip() if objective else "",
    }

    with st.spinner("Récupération curriculaire · Génération en cours..."):
        start = time.time()
        try:
            response_data = requests.post(
                f"{API_BASE}/api/planner",
                json=payload,
                timeout=120
            ).json()
            elapsed = time.time() - start
        except requests.exceptions.Timeout:
            st.error("Timeout — le serveur a pris trop de temps.")
            st.stop()
        except Exception as e:
            st.error(f"Erreur : {e}")
            st.stop()

    if response_data.get("status") != "success":
        st.error(f"Erreur API : {response_data.get('detail', response_data)}")
        st.stop()

    data      = response_data["data"]
    lesson    = data["lesson_plan"]
    diff      = data.get("differentiation", {})
    quality   = data.get("quality_score", {})
    alignment = response_data.get("curriculum_alignment", {})
    meta      = lesson.get("metadata", {})
    sections  = lesson.get("sections", {})
    labels    = lesson.get("labels", {})

    # ── LESSON DOCUMENT ───────────────────────────────────────────────────────
    subj_label = SUBJECT_LABELS.get(meta.get("subject", ""), meta.get("subject", ""))
    st.markdown(f"# {meta.get('topic', topic)}")
    st.caption(f"{subj_label} · {meta.get('grade', grade)} · {TRACKS.get(track_key, track_key)}")
    st.divider()

    # Section order matches Charliie
    SECTION_ORDER = [
        "objective",
        "assessment",
        "key_points",
        "opening",
        "introduction_to_material",
        "guided_practice",
        "independent_practice",
        "closing",
        "extension_activity",
        "homework",
        "standards_addressed",
    ]

    for key in SECTION_ORDER:
        val = sections.get(key)
        if not val:
            continue
        label = labels.get(key, key.replace("_", " ").title())
        st.markdown(f"**{label}:**")

        if isinstance(val, list):
            for item in val:
                st.markdown(f"- {item}")
        else:
            st.markdown(val)
        st.markdown("")

    # Prerequisites and competencies at the bottom
    st.divider()
    prereqs = lesson.get("prerequisites", [])
    comps   = lesson.get("competencies", [])

    if prereqs or comps:
        col_p, col_c = st.columns(2)
        if prereqs:
            with col_p:
                st.markdown(f"**{labels.get('prerequisites', 'Prérequis')}**")
                for p in prereqs:
                    st.markdown(f"- {p}")
        if comps:
            with col_c:
                st.markdown(f"**{labels.get('competencies', 'Compétences visées')}**")
                for c in comps:
                    st.markdown(f"- {c}")

    # ── DIFFERENTIATION ───────────────────────────────────────────────────────
    if diff and (diff.get("support") or diff.get("extension")):
        st.divider()
        with st.expander("🧠 Différenciation — Niveaux Bloom", expanded=False):
            st.caption("Activités adaptées selon les niveaux cognitifs (Taxonomie de Bloom)")
            col_s, col_e = st.columns(2)
            with col_s:
                st.markdown("### Niveau Soutien")
                st.caption("Bloom 1–2 · Mémoriser & Comprendre")
                render_diff("Soutien", "bloom-s", diff.get("support"))
            with col_e:
                st.markdown("### Niveau Enrichissement")
                st.caption("Bloom 5–6 · Évaluer & Créer")
                render_diff("Enrichissement", "bloom-e", diff.get("extension"))

    # ── CURRICULUM DETAILS ────────────────────────────────────────────────────
    st.divider()
    with st.expander("📊 Détails curriculaires", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Temps", f"{elapsed:.1f}s")
        c2.metric("Alignement", f"{alignment.get('alignment_score', 0):.2f} / 1.0")
        c3.metric("Qualité", f"{quality.get('overall', '—')}/5" if quality else "—")
        c4.metric("Sources MEN", len(alignment.get("sources_used", [])))

        if quality:
            st.markdown("#### Détail des scores")
            for key, label in {
                "curriculum_alignment":    "Alignement curriculaire",
                "bloom_taxonomy_coverage": "Couverture Bloom",
                "clarity":                 "Clarté",
                "moroccan_context":        "Contextualisation marocaine",
            }.items():
                val = quality.get(key)
                if isinstance(val, (int, float)):
                    quality_bar(label, val)
            if quality.get("feedback"):
                st.info(f"**Retour :** {quality.get('feedback')}")

        sources = alignment.get("sources_used", [])
        if sources:
            st.markdown("#### Sources curriculaires utilisées")
            for s in sources:
                sim = s.get("similarity", 0)
                sc  = "ss-h" if sim >= 0.6 else "ss-m" if sim >= 0.4 else "ss-l"
                st.markdown(f"""
                <div class="src-row">
                    <span class="src-score {sc}">{sim:.2f}</span>
                    <span style="font-weight:500">{s.get('source','')}</span>
                </div>
                """, unsafe_allow_html=True)
                with st.expander("Voir l'extrait", expanded=False):
                    st.caption(s.get("excerpt", "—"))

    # ── DOWNLOAD ──────────────────────────────────────────────────────────────
    st.divider()
    st.download_button(
        "📥 Télécharger (JSON)",
        data=json.dumps(lesson, ensure_ascii=False, indent=2),
        file_name=f"fiche_{subject_key}_{topic[:30].replace(' ', '_')}.json",
        mime="application/json"
    )