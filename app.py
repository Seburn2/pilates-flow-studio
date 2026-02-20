"""
app.py — The Pilates Flow Studio
Main Streamlit application with Google Sheets persistence,
workout generator, player view, and AI instructor chat.
"""

import streamlit as st
import pandas as pd
import gspread
import json
import time as time_module
from datetime import datetime, date
from google.oauth2.service_account import Credentials

from pilates_logic import (
    generate_workout, smart_swap, workout_to_json, json_to_workout,
    THEMES, APPARATUS_OPTIONS, ENERGY_LEVELS, PHASE_ORDER, EXERCISE_DB,
)

# ─────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Pilates Flow Studio",
    page_icon="🧘",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# Custom Styling — Mobile-First, High Contrast
# ─────────────────────────────────────────────

st.markdown("""
<style>
    /* Main background — clean white/light gray */
    .stApp {
        background: linear-gradient(160deg, #f8f9fa 0%, #e9ecef 100%);
    }

    /* ===== NAVIGATION BUTTONS ===== */
    .nav-container {
        display: flex;
        gap: 12px;
        margin: 0.8rem 0 1.5rem 0;
    }
    .nav-btn {
        flex: 1;
        padding: 18px 16px;
        border-radius: 14px;
        text-align: center;
        font-size: 1.15rem;
        font-weight: 700;
        cursor: pointer;
        text-decoration: none;
        border: 3px solid transparent;
        transition: all 0.2s;
    }
    .nav-btn-generate {
        background: linear-gradient(135deg, #6C63FF 0%, #5A52D5 100%);
        color: white !important;
        box-shadow: 0 4px 15px rgba(108,99,255,0.35);
    }
    .nav-btn-history {
        background: linear-gradient(135deg, #00B4D8 0%, #0096B7 100%);
        color: white !important;
        box-shadow: 0 4px 15px rgba(0,180,216,0.35);
    }
    .nav-btn-active {
        border: 3px solid #FFD60A;
        transform: scale(1.02);
    }

    /* ===== PHASE HEADERS ===== */
    .phase-warmup {
        color: #FF6B35; font-weight: 800; font-size: 1.2rem;
        text-transform: uppercase; letter-spacing: 0.08em;
    }
    .phase-foundation {
        color: #E63946; font-weight: 800; font-size: 1.2rem;
        text-transform: uppercase; letter-spacing: 0.08em;
    }
    .phase-peak {
        color: #9B5DE5; font-weight: 800; font-size: 1.2rem;
        text-transform: uppercase; letter-spacing: 0.08em;
    }
    .phase-cooldown {
        color: #00B4D8; font-weight: 800; font-size: 1.2rem;
        text-transform: uppercase; letter-spacing: 0.08em;
    }

    /* ===== EXERCISE CARDS ===== */
    .exercise-card {
        background: white;
        border-radius: 14px;
        padding: 1.2rem 1.4rem;
        margin-bottom: 0.8rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        border-left: 5px solid #6C63FF;
    }
    .exercise-card h4 {
        margin: 0 0 0.5rem 0;
        color: #1a1a2e;
        font-size: 1.15rem;
    }
    .exercise-card .meta {
        color: #555;
        font-size: 0.9rem;
        font-weight: 500;
    }
    .exercise-card .cue {
        color: #333;
        font-size: 0.95rem;
        padding: 0.3rem 0 0.3rem 0.8rem;
        border-left: 3px solid #6C63FF;
        margin: 0.4rem 0;
        background: #f8f7ff;
        border-radius: 0 6px 6px 0;
    }

    /* ===== TIMER ===== */
    .timer-display {
        font-size: 3rem;
        font-weight: 700;
        text-align: center;
        color: #1a1a2e;
        font-family: 'SF Mono', 'Menlo', 'Courier New', monospace;
        padding: 0.8rem;
        background: white;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }

    /* ===== SIDEBAR ===== */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #2d2d44 100%);
    }
    section[data-testid="stSidebar"] .stMarkdown { color: #e9ecef; }
    section[data-testid="stSidebar"] label { color: #e9ecef !important; }

    /* ===== HEADER ===== */
    .studio-header {
        text-align: center;
        padding: 1.2rem 0 0.5rem 0;
    }
    .studio-header h1 {
        color: #1a1a2e;
        font-weight: 700;
        font-size: 2rem;
        letter-spacing: 0.02em;
        margin-bottom: 0.2rem;
    }
    .studio-header p {
        color: #666;
        font-style: italic;
        font-size: 1rem;
    }

    /* ===== MOBILE OPTIMIZATIONS ===== */
    @media (max-width: 768px) {
        .studio-header h1 { font-size: 1.6rem; }
        .nav-btn { padding: 16px 12px; font-size: 1.05rem; }
        .exercise-card { padding: 1rem; }
        .exercise-card h4 { font-size: 1.1rem; }
        .timer-display { font-size: 2.5rem; }

        /* Bigger touch targets for all buttons */
        .stButton > button {
            min-height: 52px !important;
            font-size: 1.05rem !important;
            font-weight: 600 !important;
            border-radius: 10px !important;
        }

        /* Make selectboxes and sliders larger */
        .stSelectbox, .stSlider {
            font-size: 1rem !important;
        }

        /* Stack columns on mobile */
        [data-testid="column"] {
            min-width: 100% !important;
        }
    }

    /* ===== GENERAL BUTTON STYLING ===== */
    .stButton > button {
        min-height: 48px;
        font-weight: 600;
        border-radius: 10px;
    }

    /* Primary action buttons */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #6C63FF 0%, #5A52D5 100%) !important;
        border: none !important;
        font-size: 1.1rem !important;
    }

    /* ===== HISTORY TABLE ===== */
    .stDataFrame {
        font-size: 0.95rem;
    }

    /* Make expanders more visible */
    .streamlit-expanderHeader {
        font-size: 1.05rem !important;
        font-weight: 600 !important;
        background: white !important;
        border-radius: 10px !important;
    }

    /* Chat input styling */
    .stChatInput {
        border-radius: 12px !important;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Google Sheets Connection
# ─────────────────────────────────────────────

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _fix_private_key(key_str):
    """Fix common private key formatting issues from TOML parsing."""
    if not key_str:
        return key_str
    k = key_str.strip()
    # If key has literal \\n instead of real newlines, fix it
    if "\\n" in k and "\n" not in k:
        k = k.replace("\\n", "\n")
    # If key somehow lost all newlines, try to reconstruct
    if "\n" not in k and "-----BEGIN" in k:
        k = k.replace("-----BEGIN PRIVATE KEY-----", "-----BEGIN PRIVATE KEY-----\n")
        k = k.replace("-----END PRIVATE KEY-----", "\n-----END PRIVATE KEY-----\n")
    return k


@st.cache_resource
def get_gspread_client():
    """Authenticate with Google using Streamlit secrets.
    
    Supports TWO formats:
    1. Simple: gcp_service_account_json = '{...entire JSON key...}'
    2. Traditional: [gcp_service_account] section with individual fields
    Auto-fixes common private_key formatting issues.
    """
    try:
        # METHOD 1: Single JSON string (easiest - avoids TOML formatting issues)
        if "gcp_service_account_json" in st.secrets:
            raw = st.secrets["gcp_service_account_json"]
            creds_dict = json.loads(raw)
        # METHOD 2: Traditional TOML section
        elif "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
        else:
            st.error("No Google credentials found in secrets. Add gcp_service_account_json or [gcp_service_account].")
            return None
        
        # Auto-fix private key formatting
        if "private_key" in creds_dict:
            creds_dict["private_key"] = _fix_private_key(creds_dict["private_key"])
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        return gspread.authorize(creds)
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON in gcp_service_account_json: {e}")
        return None
    except Exception as e:
        st.error(f"Could not connect to Google Sheets: {e}")
        return None


def get_sheet():
    """Get the Google Spreadsheet object."""
    client = get_gspread_client()
    if client is None:
        return None
    try:
        sheet_url = st.secrets.get("sheet_url", "")
        sheet_id = st.secrets.get("sheet_id", "")
        sheet_name = st.secrets.get("sheet_name", "")
        if sheet_url:
            return client.open_by_url(sheet_url)
        elif sheet_id:
            return client.open_by_key(sheet_id)
        elif sheet_name:
            return client.open(sheet_name)
        else:
            return client.open("Pilates Flow Studio")
    except Exception as e:
        # Show diagnostic info to help debug
        method = "url" if sheet_url else ("id" if sheet_id else "name")
        value = sheet_url or sheet_id or "Pilates Flow Studio"
        st.error(f"Could not open spreadsheet: {e}")
        with st.expander("Connection diagnostics"):
            st.code(f"Method: {method}\nValue: {value}\nClient OK: {client is not None}")
            if "gcp_service_account" in st.secrets:
                sa = dict(st.secrets["gcp_service_account"])
                st.code(f"Service account: {sa.get('client_email', 'MISSING')}")
                pk = sa.get("private_key", "")
                st.code(f"Private key starts with: {pk[:30]}...\nPrivate key length: {len(pk)} chars\nHas real newlines: {'\\n' in pk}")
        return None


def ensure_worksheets(spreadsheet):
    """Make sure both required tabs exist with headers."""
    existing = [ws.title for ws in spreadsheet.worksheets()]

    if "workouts_log" not in existing:
        ws = spreadsheet.add_worksheet(title="workouts_log", rows=1000, cols=7)
        ws.append_row(["Date", "User", "Theme", "Duration", "Full_JSON_Data", "Rating", "Notes"])
    if "exercise_library" not in existing:
        ws = spreadsheet.add_worksheet(title="exercise_library", rows=500, cols=4)
        ws.append_row(["Slug", "Name", "Default_Springs", "Cues"])


def save_workout(user: str, theme: str, duration: int, workout_json: str,
                 rating: int = 0, notes: str = ""):
    """Append a workout row to the Google Sheet."""
    spreadsheet = get_sheet()
    if spreadsheet is None:
        st.warning("Could not save — Google Sheets not connected. Workout still works locally!")
        return False
    try:
        ensure_worksheets(spreadsheet)
        ws = spreadsheet.worksheet("workouts_log")
        ws.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            user, theme, duration, workout_json, rating, notes,
        ])
        return True
    except Exception as e:
        st.warning(f"Save failed: {e}")
        return False


def load_history(user: str) -> pd.DataFrame:
    """Load workout history for a specific user."""
    spreadsheet = get_sheet()
    if spreadsheet is None:
        return pd.DataFrame()
    try:
        ensure_worksheets(spreadsheet)
        ws = spreadsheet.worksheet("workouts_log")
        records = ws.get_all_records()
        df = pd.DataFrame(records)
        if df.empty:
            return df
        return df[df["User"] == user].sort_values("Date", ascending=False)
    except Exception as e:
        st.warning(f"Could not load history: {e}")
        return pd.DataFrame()


# ─────────────────────────────────────────────
# AI Instructor Chat
# ─────────────────────────────────────────────

def ask_instructor(question: str, exercise_context: dict) -> str:
    """Use Claude to answer questions about the current exercise."""
    try:
        import anthropic
        api_key = st.secrets.get("anthropic_api_key", "")
        if not api_key:
            return "Set your `anthropic_api_key` in Streamlit secrets to enable the AI instructor."

        client = anthropic.Anthropic(api_key=api_key)
        system_prompt = f"""You are a warm, knowledgeable Pilates instructor assisting during a workout session.
The student is currently doing: {exercise_context.get('name', 'Unknown Exercise')}
Apparatus: {exercise_context.get('apparatus', 'N/A')}
Springs: {exercise_context.get('default_springs', 'N/A')}
Cues for this exercise: {', '.join(exercise_context.get('cues', []))}

Answer their question helpfully. Be concise (2-4 sentences unless they ask for more detail).
Focus on form, safety, modifications, and mind-body connection. Use encouraging language."""

        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=300,
            system=system_prompt,
            messages=[{"role": "user", "content": question}],
        )
        return response.content[0].text
    except ImportError:
        return "Install the `anthropic` package to enable AI chat."
    except Exception as e:
        return f"AI instructor unavailable: {e}"


# ─────────────────────────────────────────────
# Session State Initialization
# ─────────────────────────────────────────────

DEFAULTS = {
    "workout": None,
    "current_index": 0,
    "timer_running": False,
    "timer_start": None,
    "elapsed": 0,
    "view": "generator",       # "generator", "player", "history", "ai_chat"
    "chat_messages": [],
    "workout_rated": False,
    "ai_messages": [],         # General AI chat history
}
for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ─────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🧘 Smart Studio")
    st.markdown("---")

    user = st.selectbox(
        "Select User Profile",
        ["Alyssa", "Ted (Test)"],
        help="Choose your profile. History is saved separately per user.",
    )

    st.markdown("---")
    st.caption("Pilates Flow Studio v1.0")
    st.caption(f"Logged in as: **{user}**")


# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────

st.markdown("""
<div class="studio-header">
    <h1>The Pilates Flow Studio</h1>
    <p>Intelligent Pilates programming — your session, your way</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Navigation — Big Bright Buttons
# ─────────────────────────────────────────────

nav_col1, nav_col2, nav_col3 = st.columns(3)
with nav_col1:
    if st.button("🎲  GENERATE", use_container_width=True, type="primary",
                  key="nav_gen"):
        st.session_state.view = "generator"
        st.session_state.workout = None
        st.rerun()
with nav_col2:
    if st.button("📖  HISTORY", use_container_width=True, type="secondary",
                  key="nav_hist"):
        st.session_state.view = "history"
        st.rerun()
with nav_col3:
    if st.button("🤖  AI COACH", use_container_width=True, type="secondary",
                  key="nav_ai"):
        st.session_state.view = "ai_chat"
        st.rerun()

# Show which view is active
if st.session_state.view in ("generator", "player", "finish"):
    st.markdown('<div style="text-align:center; color:#6C63FF; font-weight:700; font-size:0.9rem; margin-bottom:0.5rem;">● Generate Workout</div>', unsafe_allow_html=True)
elif st.session_state.view == "history":
    st.markdown('<div style="text-align:center; color:#00B4D8; font-weight:700; font-size:0.9rem; margin-bottom:0.5rem;">● Workout History</div>', unsafe_allow_html=True)
elif st.session_state.view == "ai_chat":
    st.markdown('<div style="text-align:center; color:#FF6B35; font-weight:700; font-size:0.9rem; margin-bottom:0.5rem;">● AI Pilates Coach</div>', unsafe_allow_html=True)

st.markdown("---")


# ─────────────────────────────────────────────
# View: Generator
# ─────────────────────────────────────────────

if st.session_state.view == "generator":
    st.markdown("### 💪 Build Your Session")

    col1, col2 = st.columns(2)
    with col1:
        duration = st.slider("Duration (min)", 30, 90, 50, step=5)
        apparatus = st.selectbox("Apparatus", APPARATUS_OPTIONS)
    with col2:
        theme = st.selectbox("Theme / Focus", THEMES)
        energy = st.selectbox("Energy Level", list(ENERGY_LEVELS.keys()))

    if st.button("🎲 Generate Workout", type="primary", use_container_width=True):
        workout = generate_workout(duration, apparatus, theme, energy)
        st.session_state.workout = workout
        st.session_state.current_index = 0
        st.session_state.timer_running = False
        st.session_state.elapsed = 0
        st.session_state.chat_messages = []
        st.session_state.workout_rated = False

    # Display generated workout
    if st.session_state.workout:
        workout = st.session_state.workout
        total_time = sum(e.get("duration_min", 5) for e in workout)
        st.markdown(f"**{len(workout)} exercises** · ~**{total_time:.0f} min** total")

        # Group by phase
        current_phase = None
        for i, ex in enumerate(workout):
            phase = ex.get("phase_label", ex.get("phase", "Foundation")).capitalize()
            if phase != current_phase:
                current_phase = phase
                css_class = f"phase-{phase.lower()}"
                st.markdown(f'<div class="{css_class}">▸ {phase.upper()}</div>',
                            unsafe_allow_html=True)

            with st.container():
                c1, c2, c3 = st.columns([6, 2, 1])
                with c1:
                    springs_val = ex.get('default_springs', ex.get('springs', ''))
                    springs = f" · {springs_val}" if springs_val and springs_val != 'N/A' else ""
                    apparatus = ex.get('apparatus', '')
                    duration = ex.get('duration_min', 5)
                    energy = ex.get('energy', '')
                    cues = ex.get('cues', [])
                    if isinstance(cues, list) and cues:
                        filtered_cues = [str(c) for c in cues[:2] if c and str(c).strip()]
                    else:
                        filtered_cues = []
                    energy_str = f" · Energy {energy}/5" if energy else ""
                    cue_lines = "".join(f'<div class="cue">▸ {c}</div>' for c in filtered_cues)
                    card_html = f'<div class="exercise-card"><h4>{i+1}. {ex.get("name", "Exercise")}</h4><div class="meta">{apparatus}{springs} · {duration} min{energy_str}</div>{cue_lines}</div>'
                    st.markdown(card_html, unsafe_allow_html=True)
                with c2:
                    st.caption(ex.get("category", ex.get("reps", "")))
                with c3:
                    if st.button("🔄", key=f"swap_{i}", help="Swap this exercise"):
                        st.session_state[f"swap_open_{i}"] = not st.session_state.get(f"swap_open_{i}", False)
                        st.rerun()

                # Expandable swap panel
                if st.session_state.get(f"swap_open_{i}", False):
                    with st.container():
                        st.markdown(f'<div style="background:#f0eeff; padding:12px; border-radius:10px; margin-bottom:12px;">', unsafe_allow_html=True)
                        st.markdown(f"**Replace: {ex.get('name', 'Exercise')}** ({ex.get('phase_label', ex.get('phase', ''))})")

                        swap_tab1, swap_tab2, swap_tab3 = st.tabs(["🎲 Random Swap", "🔍 Browse & Search", "🤖 AI Suggest"])

                        with swap_tab1:
                            st.caption("Find a similar exercise in the same phase & category")
                            if st.button("Swap randomly", key=f"rand_swap_{i}", use_container_width=True):
                                new_ex = smart_swap(workout, i)
                                if new_ex:
                                    st.session_state.workout[i] = new_ex
                                    st.session_state[f"swap_open_{i}"] = False
                                    st.rerun()
                                else:
                                    st.warning("No alternatives found in this category.")

                        with swap_tab2:
                            # Filter exercises by phase (or show all)
                            current_phase = ex.get("phase_label", ex.get("phase", "")).lower()
                            current_apparatus = ex.get("apparatus", "")

                            filter_col1, filter_col2 = st.columns(2)
                            with filter_col1:
                                phase_filter = st.selectbox(
                                    "Phase", ["All", "Warmup", "Foundation", "Peak", "Cooldown"],
                                    index=["all", "warmup", "foundation", "peak", "cooldown"].index(current_phase) + 1 if current_phase in ["warmup", "foundation", "peak", "cooldown"] else 0,
                                    key=f"phase_filter_{i}"
                                )
                            with filter_col2:
                                app_filter = st.selectbox(
                                    "Apparatus", ["All"] + APPARATUS_OPTIONS,
                                    index=(APPARATUS_OPTIONS.index(current_apparatus) + 1) if current_apparatus in APPARATUS_OPTIONS else 0,
                                    key=f"app_filter_{i}"
                                )

                            # Search box
                            search_text = st.text_input("Search by name or category", key=f"search_{i}",
                                                        placeholder="e.g. arm, footwork, spine, hip...")

                            # Build filtered list
                            used_slugs = {e.get("slug", "") for e in workout}
                            filtered = []
                            for db_ex in EXERCISE_DB:
                                if db_ex.slug in used_slugs:
                                    continue
                                if phase_filter != "All" and db_ex.phase != phase_filter.lower():
                                    continue
                                if app_filter != "All" and db_ex.apparatus != app_filter:
                                    continue
                                if search_text:
                                    search_lower = search_text.lower()
                                    if (search_lower not in db_ex.name.lower()
                                        and search_lower not in db_ex.category.lower()
                                        and not any(search_lower in t.lower() for t in db_ex.themes)):
                                        continue
                                filtered.append(db_ex)

                            if filtered:
                                exercise_options = {f"{e.name} ({e.apparatus} · {e.category})": e for e in filtered}
                                selected = st.selectbox(
                                    f"{len(filtered)} exercises available",
                                    options=list(exercise_options.keys()),
                                    key=f"browse_{i}"
                                )
                                if selected:
                                    preview = exercise_options[selected]
                                    st.caption(f"Springs: {preview.default_springs} · Energy: {preview.energy}/5 · Phase: {preview.phase}")
                                    if preview.cues:
                                        st.caption(f"Cues: {preview.cues[0]}")
                                    if st.button("✅ Use this exercise", key=f"use_{i}", use_container_width=True, type="primary"):
                                        entry = preview.to_dict()
                                        entry["phase_label"] = ex.get("phase_label", ex.get("phase", preview.phase)).capitalize()
                                        st.session_state.workout[i] = entry
                                        st.session_state[f"swap_open_{i}"] = False
                                        st.rerun()
                            else:
                                st.info("No matching exercises. Try broadening your filters.")

                        with swap_tab3:
                            st.caption("Describe what you want and AI will find it from the exercise database")
                            ai_request = st.text_input(
                                "What are you looking for?", key=f"ai_swap_{i}",
                                placeholder="e.g. arm warmups, hip opener, something easier, core challenge..."
                            )
                            if ai_request and st.button("Get AI suggestion", key=f"ai_go_{i}", use_container_width=True):
                                try:
                                    import anthropic
                                    api_key = st.secrets.get("anthropic_api_key", "")
                                    if not api_key:
                                        st.warning("Add your anthropic_api_key to Streamlit secrets to use AI suggestions.")
                                    else:
                                        # Build exercise list for AI
                                        available = [e for e in EXERCISE_DB if e.slug not in used_slugs]
                                        ex_list = "\n".join(
                                            f"- SLUG:{e.slug} | {e.name} ({e.apparatus}) | {e.category} | Phase:{e.phase} | Springs:{e.default_springs} | Energy:{e.energy}/5"
                                            for e in available
                                        )
                                        client = anthropic.Anthropic(api_key=api_key)
                                        response = client.messages.create(
                                            model="claude-sonnet-4-5-20250929",
                                            max_tokens=200,
                                            system=f"""You are a Pilates exercise selector. The user wants to replace an exercise in their workout.
Current exercise: {ex.get('name', 'Unknown')} (Phase: {ex.get('phase_label', ex.get('phase', ''))}, Category: {ex.get('category', '')})

ONLY suggest exercises from this list. Return EXACTLY the SLUG of your top pick, then a brief reason.
Format: SLUG:the_slug_here
REASON:why this is a good fit

Available exercises:
{ex_list}""",
                                            messages=[{"role": "user", "content": ai_request}],
                                        )
                                        ai_text = response.content[0].text

                                        # Parse the slug from AI response
                                        suggested_slug = None
                                        for line in ai_text.split("\n"):
                                            if line.strip().startswith("SLUG:"):
                                                suggested_slug = line.strip().replace("SLUG:", "").strip()
                                                break

                                        # Find the exercise
                                        suggested_ex = None
                                        if suggested_slug:
                                            for db_ex in EXERCISE_DB:
                                                if db_ex.slug == suggested_slug:
                                                    suggested_ex = db_ex
                                                    break

                                        if suggested_ex:
                                            reason = ""
                                            for line in ai_text.split("\n"):
                                                if line.strip().startswith("REASON:"):
                                                    reason = line.strip().replace("REASON:", "").strip()
                                            st.success(f"**Suggestion: {suggested_ex.name}** ({suggested_ex.apparatus})")
                                            if reason:
                                                st.caption(reason)
                                            st.caption(f"Springs: {suggested_ex.default_springs} · Energy: {suggested_ex.energy}/5")
                                            if st.button("✅ Use this", key=f"ai_use_{i}", use_container_width=True, type="primary"):
                                                entry = suggested_ex.to_dict()
                                                entry["phase_label"] = ex.get("phase_label", ex.get("phase", suggested_ex.phase)).capitalize()
                                                st.session_state.workout[i] = entry
                                                st.session_state[f"swap_open_{i}"] = False
                                                st.rerun()
                                        else:
                                            st.info(ai_text)
                                except Exception as e:
                                    st.error(f"AI error: {e}")

                        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")
        col_start, col_save = st.columns(2)
        with col_start:
            if st.button("▶️ Start Workout", type="primary", use_container_width=True):
                st.session_state.view = "player"
                st.session_state.current_index = 0
                st.session_state.timer_running = False
                st.session_state.elapsed = 0
                st.rerun()
        with col_save:
            if st.button("💾 Save to History", use_container_width=True):
                saved = save_workout(
                    user=user,
                    theme=theme,
                    duration=duration,
                    workout_json=workout_to_json(workout),
                )
                if saved:
                    st.toast("Workout saved! ✅")


# ─────────────────────────────────────────────
# View: Player
# ─────────────────────────────────────────────

elif st.session_state.view == "player" and st.session_state.workout:
    workout = st.session_state.workout
    idx = st.session_state.current_index
    total = len(workout)
    ex = workout[idx]

    # Navigation bar
    nav_col1, nav_col2, nav_col3 = st.columns([1, 3, 1])
    with nav_col1:
        if st.button("← Prev", disabled=(idx == 0)):
            st.session_state.current_index -= 1
            st.session_state.chat_messages = []
            st.rerun()
    with nav_col2:
        st.progress((idx + 1) / total, text=f"Exercise {idx + 1} of {total}")
    with nav_col3:
        if idx < total - 1:
            if st.button("Next →"):
                st.session_state.current_index += 1
                st.session_state.chat_messages = []
                st.rerun()
        else:
            if st.button("✅ Finish"):
                st.session_state.view = "finish"
                st.rerun()

    st.markdown("---")

    # Main content area
    main_col, chat_col = st.columns([3, 2])

    with main_col:
        # Phase indicator
        phase = ex.get('phase_label', ex.get('phase', 'Foundation')).capitalize()
        css_class = f"phase-{phase.lower()}"
        st.markdown(f'<span class="{css_class}">{phase.upper()}</span>',
                    unsafe_allow_html=True)

        # Exercise title and info
        st.markdown(f"## {ex.get('name', 'Exercise')}")

        info_cols = st.columns(3)
        with info_cols[0]:
            st.metric("Apparatus", ex.get("apparatus", "Reformer"))
        with info_cols[1]:
            st.metric("Springs", ex.get("default_springs", ex.get("springs", "—")))
        with info_cols[2]:
            st.metric("Duration", f"{ex.get('duration_min', 5)} min")

        # Cues
        cues = ex.get("cues", [])
        if cues and any(c for c in cues if c):
            st.markdown("#### Teaching Cues")
            for cue in cues:
                if cue:
                    st.markdown(f'<div class="cue">▸ {cue}</div>', unsafe_allow_html=True)

        # Timer
        st.markdown("---")
        st.markdown("#### ⏱ Session Timer")

        timer_col1, timer_col2 = st.columns([2, 1])
        with timer_col1:
            if st.session_state.timer_running and st.session_state.timer_start:
                elapsed = st.session_state.elapsed + (
                    time_module.time() - st.session_state.timer_start
                )
            else:
                elapsed = st.session_state.elapsed

            mins, secs = divmod(int(elapsed), 60)
            hrs, mins = divmod(mins, 60)
            st.markdown(
                f'<div class="timer-display">{hrs:02d}:{mins:02d}:{secs:02d}</div>',
                unsafe_allow_html=True,
            )

        with timer_col2:
            if not st.session_state.timer_running:
                if st.button("▶ Start", use_container_width=True):
                    st.session_state.timer_running = True
                    st.session_state.timer_start = time_module.time()
                    st.rerun()
            else:
                if st.button("⏸ Pause", use_container_width=True):
                    st.session_state.elapsed += (
                        time_module.time() - st.session_state.timer_start
                    )
                    st.session_state.timer_running = False
                    st.session_state.timer_start = None
                    st.rerun()

            if st.button("↺ Reset", use_container_width=True):
                st.session_state.elapsed = 0
                st.session_state.timer_running = False
                st.session_state.timer_start = None
                st.rerun()

    # Chat column
    with chat_col:
        st.markdown("#### 💬 Ask Instructor")
        st.caption(f"Context: *{ex['name']}*")

        # Display chat history
        for msg in st.session_state.chat_messages:
            role_icon = "🙋" if msg["role"] == "user" else "🧘"
            st.markdown(f"**{role_icon}** {msg['content']}")

        question = st.text_input(
            "Ask about this exercise...",
            key=f"chat_input_{idx}",
            placeholder="e.g. How do I modify this for a bad knee?",
        )
        if question and st.button("Ask", key=f"ask_btn_{idx}"):
            st.session_state.chat_messages.append({"role": "user", "content": question})
            with st.spinner("Thinking..."):
                answer = ask_instructor(question, ex)
            st.session_state.chat_messages.append({"role": "assistant", "content": answer})
            st.rerun()

    # Quick swap in player view
    st.markdown("---")
    if st.button("🔄 Swap This Exercise", use_container_width=True):
        new_ex = smart_swap(workout, idx)
        if new_ex:
            st.session_state.workout[idx] = new_ex
            st.session_state.chat_messages = []
            st.rerun()
        else:
            st.toast("No alternative found for this slot.")

    # Back to overview
    if st.button("← Back to Workout Overview"):
        st.session_state.view = "generator"
        st.rerun()


# ─────────────────────────────────────────────
# View: Finish / Rate
# ─────────────────────────────────────────────

elif st.session_state.view == "finish" and st.session_state.workout:
    st.markdown("## 🎉 Workout Complete!")
    st.balloons()

    workout = st.session_state.workout
    total_time = sum(e.get("duration_min", 5) for e in workout)
    st.markdown(f"You completed **{len(workout)} exercises** (~{total_time:.0f} min). Amazing work!")

    if not st.session_state.workout_rated:
        st.markdown("### Rate Your Session")
        rating = st.slider("How did it feel?", 1, 5, 3,
                           format="%d ⭐",
                           help="1 = Too easy, 3 = Just right, 5 = Very challenging")
        notes = st.text_area("Any notes? (optional)",
                             placeholder="e.g. Loved the mermaid stretch, skipped snake/twist")

        if st.button("💾 Save & Rate", type="primary"):
            saved = save_workout(
                user=user,
                theme=workout[0].get("themes", [""])[0] if workout else "",
                duration=int(total_time),
                workout_json=workout_to_json(workout),
                rating=rating,
                notes=notes,
            )
            if saved:
                st.toast("Saved with rating! ⭐")
                st.session_state.workout_rated = True
                st.rerun()
    else:
        st.success("Session saved and rated!")

    if st.button("🎲 Generate New Workout"):
        st.session_state.workout = None
        st.session_state.view = "generator"
        st.rerun()


# ─────────────────────────────────────────────
# View: History
# ─────────────────────────────────────────────

elif st.session_state.view == "history":
    st.markdown(f"### 📖 Workout History — {user}")

    df = load_history(user)

    if df.empty:
        st.info("No workouts saved yet. Generate your first session! 🎲")
    else:
        # Summary stats
        stat1, stat2, stat3, stat4 = st.columns(4)
        with stat1:
            st.metric("Total Sessions", len(df))
        with stat2:
            total_mins = pd.to_numeric(df["Duration"], errors="coerce").sum()
            st.metric("Total Minutes", f"{total_mins:.0f}")
        with stat3:
            avg_rating = pd.to_numeric(df["Rating"], errors="coerce").mean()
            st.metric("Avg Rating", f"{avg_rating:.1f} ⭐" if pd.notna(avg_rating) else "—")
        with stat4:
            st.metric("Latest", df.iloc[0]["Date"] if len(df) > 0 else "—")

        st.markdown("---")

        # History table
        display_df = df[["Date", "Theme", "Duration", "Rating", "Notes"]].copy()
        display_df.columns = ["Date", "Theme", "Duration (min)", "Rating ⭐", "Notes"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # Expandable detail view
        st.markdown("#### Session Details")
        for i, row in df.iterrows():
            col_exp, col_btn = st.columns([5, 1])
            with col_exp:
                with st.expander(f"📋 {row['Date']} — {row['Theme']} ({row['Duration']} min)"):
                    try:
                        exercises = json_to_workout(row["Full_JSON_Data"])
                        for j, ex in enumerate(exercises):
                            name = ex.get('name', 'Unknown')
                            apparatus = ex.get('apparatus', '')
                            phase = ex.get('phase_label', ex.get('phase', ''))
                            duration = ex.get('duration_min', '')
                            springs = ex.get('springs', '')
                            reps = ex.get('reps', '')

                            # Build display line
                            parts = [f"**{j+1}. {name}**"]
                            if apparatus:
                                parts[0] += f" ({apparatus})"
                            details = []
                            if phase:
                                details.append(phase)
                            if duration:
                                details.append(f"{duration} min")
                            if springs:
                                details.append(f"Springs: {springs}")
                            if reps:
                                details.append(f"{reps}")
                            if details:
                                parts.append(" · ".join(details))
                            st.markdown(" — ".join(parts))
                    except Exception:
                        st.caption("Could not parse workout data.")
                    if row.get("Notes"):
                        st.markdown(f"*Notes: {row['Notes']}*")
            with col_btn:
                if st.button("🔁", key=f"repeat_{i}", help="Load this workout"):
                    try:
                        exercises = json_to_workout(row["Full_JSON_Data"])
                        st.session_state.workout = exercises
                        st.session_state.view = "player"
                        st.rerun()
                    except Exception:
                        st.error("Could not load this workout.")


# ─────────────────────────────────────────────
# View: AI Pilates Coach
# ─────────────────────────────────────────────

elif st.session_state.view == "ai_chat":
    st.markdown("### 🤖 AI Pilates Coach")
    st.markdown("*Ask me anything about Pilates — exercises, recommendations, form tips, modifications, and more.*")

    # Quick action buttons
    st.markdown("**Quick questions:**")
    qa_col1, qa_col2 = st.columns(2)
    with qa_col1:
        if st.button("🔍 Look up an exercise", use_container_width=True, key="qa_lookup"):
            st.session_state.ai_messages.append({
                "role": "user",
                "content": "I'd like to look up a specific Pilates exercise. Ask me which one!"
            })
            st.rerun()
        if st.button("💡 Suggest a workout", use_container_width=True, key="qa_suggest"):
            st.session_state.ai_messages.append({
                "role": "user",
                "content": "Can you recommend a Pilates workout for me? Ask me about my goals and how much time I have."
            })
            st.rerun()
    with qa_col2:
        if st.button("🩹 Modifications help", use_container_width=True, key="qa_mods"):
            st.session_state.ai_messages.append({
                "role": "user",
                "content": "I need modifications for some exercises. Ask me about my limitations or injuries."
            })
            st.rerun()
        if st.button("📚 Explain springs/setup", use_container_width=True, key="qa_springs"):
            st.session_state.ai_messages.append({
                "role": "user",
                "content": "Can you explain how the spring system works on the Reformer and what the different colors mean?"
            })
            st.rerun()

    st.markdown("---")

    # Build exercise knowledge for the AI
    exercise_names = []
    exercise_details = []
    for ex in EXERCISE_DB:
        exercise_names.append(ex.name)
        exercise_details.append(
            f"- {ex.name} ({ex.apparatus}): Category={ex.category}, Phase={ex.phase}, "
            f"Springs={ex.default_springs}, Energy={ex.energy}/5, "
            f"Cues: {'; '.join(ex.cues[:2])}"
        )
    exercise_knowledge = "\n".join(exercise_details)  # Include all exercises

    # Chat display
    for msg in st.session_state.ai_messages:
        if msg["role"] == "user":
            st.markdown(f'<div style="background:#e8e4ff; padding:12px 16px; border-radius:12px; margin:8px 0; font-size:1rem;"><strong>You:</strong> {msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="background:white; padding:12px 16px; border-radius:12px; margin:8px 0; border-left:4px solid #FF6B35; font-size:1rem;"><strong>🤖 Coach:</strong> {msg["content"]}</div>', unsafe_allow_html=True)

    # Chat input
    user_input = st.chat_input("Ask your Pilates coach anything...")

    if user_input:
        st.session_state.ai_messages.append({"role": "user", "content": user_input})

        try:
            import anthropic
            api_key = st.secrets.get("anthropic_api_key", "")
            if not api_key:
                response_text = ("To enable the AI Coach, add your Anthropic API key to Streamlit secrets:\n\n"
                                 "`anthropic_api_key = \"sk-ant-your-key-here\"`\n\n"
                                 "Get a key at [console.anthropic.com](https://console.anthropic.com)")
            else:
                client = anthropic.Anthropic(api_key=api_key)

                system_prompt = f"""You are a warm, expert Pilates instructor and coach named Coach Flow.
You have deep knowledge of all Pilates apparatus (Reformer, Mat, Chair/Wunda Chair, Cadillac/Trapeze Table).

CRITICAL RULE: When recommending or discussing specific exercises, you must ONLY reference exercises 
from the studio database listed below. NEVER invent or make up exercise names. If someone asks about 
an exercise not in the database, you can explain it generally but be clear it's not in our current studio library.

YOUR CAPABILITIES:
1. EXERCISE LOOKUP: When asked about a specific exercise, explain it in detail — setup, springs, 
   movement, cues, common mistakes, modifications for beginners/injuries, and what muscles it targets.
   Always check if it exists in our database first.
2. WORKOUT RECOMMENDATIONS: When asked for workout ideas, ONLY use exercises from the database below.
   Ask about their goals, time available, apparatus, energy level, and any limitations. Then suggest 
   a structured session using the bell curve: Warmup → Foundation → Peak → Cooldown.
3. GENERAL PILATES KNOWLEDGE: Answer questions about form, breathing, spring settings, 
   equipment setup, anatomy, modifications for injuries/conditions (back pain, knee issues, 
   pregnancy, osteoporosis, etc.), and Pilates philosophy.

OUR COMPLETE STUDIO EXERCISE DATABASE ({len(EXERCISE_DB)} exercises):
{exercise_knowledge}

When recommending workouts, use the exact exercise names from this list.
When someone asks "what exercises do you have for X", search this list and cite the matches.

STYLE:
- Be warm, encouraging, and professional
- Use clear, concise language
- When describing exercises, use vivid cues like a real instructor would
- For modifications, always prioritize safety
- Use bullet points for exercise breakdowns
- If recommending a workout, format it clearly with phases
- Keep responses focused — 3-6 sentences for simple questions, longer for workout plans

The user's name is {user}."""

                # Build message history for context
                api_messages = []
                for msg in st.session_state.ai_messages:
                    api_messages.append({"role": msg["role"], "content": msg["content"]})

                response = client.messages.create(
                    model="claude-sonnet-4-5-20250929",
                    max_tokens=800,
                    system=system_prompt,
                    messages=api_messages,
                )
                response_text = response.content[0].text

        except ImportError:
            response_text = "Install the `anthropic` package to enable AI chat."
        except Exception as e:
            response_text = f"Sorry, I couldn't process that: {e}"

        st.session_state.ai_messages.append({"role": "assistant", "content": response_text})
        st.rerun()

    # Clear chat button
    if st.session_state.ai_messages:
        st.markdown("---")
        if st.button("🗑️ Clear conversation", key="clear_ai"):
            st.session_state.ai_messages = []
            st.rerun()
