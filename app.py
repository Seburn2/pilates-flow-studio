"""
app.py — The Pilates Flow Studio
Main Streamlit application with Google Sheets persistence,
workout generator, player view, AI instructor chat,
progress dashboard, PDF export, and smart recommendations.
"""

import streamlit as st
import pandas as pd
import gspread
import json
import io
import time as time_module
from datetime import datetime, date, timedelta
from collections import Counter
from google.oauth2.service_account import Credentials

from pilates_logic import (
    generate_workout, smart_swap, workout_to_json, json_to_workout,
    THEMES, APPARATUS_OPTIONS, ENERGY_LEVELS, PHASE_ORDER, EXERCISE_DB,
)

try:
    from streamlit_autorefresh import st_autorefresh
    HAS_AUTOREFRESH = True
except ImportError:
    HAS_AUTOREFRESH = False

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

    /* Dashboard metrics */
    [data-testid="stMetric"] {
        background: white;
        border-radius: 12px;
        padding: 12px 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
    [data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
        font-weight: 800 !important;
    }

    /* Download button styling — make PDF export pop */
    .stDownloadButton > button {
        min-height: 48px;
        font-weight: 700 !important;
        border-radius: 10px;
        background: linear-gradient(135deg, #10B981 0%, #059669 100%) !important;
        color: white !important;
        border: none !important;
        font-size: 1rem !important;
    }
    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #059669 0%, #047857 100%) !important;
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
# PDF Export
# ─────────────────────────────────────────────

def generate_workout_pdf(workout: list[dict], user: str, theme: str = "",
                          duration: int = 0, apparatus: str = "") -> bytes:
    """Generate a clean PDF of a workout plan."""
    from fpdf import FPDF

    def safe_text(text):
        """Sanitize text for fpdf2 latin-1 compatibility."""
        if not isinstance(text, str):
            text = str(text)
        replacements = {
            "\u2013": "-", "\u2014": "-", "\u2015": "-",   # en-dash, em-dash
            "\u2018": "'", "\u2019": "'",                   # smart single quotes
            "\u201c": '"', "\u201d": '"',                   # smart double quotes
            "\u2026": "...",                                 # ellipsis
            "\u2022": "*",                                   # bullet
            "\u00b7": "*",                                   # middle dot
            "\u2192": "->", "\u2190": "<-",                 # arrows
            "\u2248": "~",                                   # approximately
            "\u00b0": " deg",                                # degree
            "\u2212": "-",                                   # minus sign
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        # Strip any remaining non-latin-1 characters
        text = text.encode("latin-1", errors="replace").decode("latin-1")
        return text

    class WorkoutPDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 18)
            self.cell(0, 10, "The Pilates Flow Studio", align="C", new_x="LMARGIN", new_y="NEXT")
            self.set_font("Helvetica", "I", 10)
            self.cell(0, 6, "Intelligent Pilates Programming", align="C", new_x="LMARGIN", new_y="NEXT")
            self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
            self.ln(6)

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    pdf = WorkoutPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)

    # Workout metadata
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, safe_text(f"Workout Plan for {user}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, safe_text(f"Date: {date.today().strftime('%B %d, %Y')}"), new_x="LMARGIN", new_y="NEXT")
    if apparatus:
        pdf.cell(0, 6, safe_text(f"Apparatus: {apparatus}  |  Theme: {theme}  |  Duration: {duration} min"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Exercises grouped by phase
    current_phase = ""
    phase_colors = {
        "Warmup": (255, 107, 53), "Foundation": (230, 57, 70),
        "Peak": (155, 93, 229), "Cooldown": (0, 180, 216),
    }

    for i, ex in enumerate(workout):
        phase = ex.get("phase_label", ex.get("phase", "")).capitalize()
        if phase != current_phase:
            current_phase = phase
            pdf.ln(3)
            r, g, b = phase_colors.get(phase, (100, 100, 100))
            pdf.set_fill_color(r, g, b)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 8, safe_text(f"  {phase.upper()}"), fill=True, new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)

        # Exercise row
        name = ex.get("name", "Exercise")
        springs = ex.get("default_springs", ex.get("springs", ""))
        dur = ex.get("duration_min", 5)
        cues = ex.get("cues", [])

        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, safe_text(f"{i+1}. {name}"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        meta_parts = []
        if springs and springs != "N/A":
            meta_parts.append(f"Springs: {springs}")
        meta_parts.append(f"{dur} min")
        category = ex.get("category", "")
        if category:
            meta_parts.append(category)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 5, safe_text("    " + "  |  ".join(meta_parts)), new_x="LMARGIN", new_y="NEXT")

        # Cues
        if isinstance(cues, list):
            for cue in cues[:3]:
                if cue and str(cue).strip():
                    pdf.set_text_color(80, 80, 80)
                    pdf.set_font("Helvetica", "I", 9)
                    pdf.cell(0, 5, safe_text(f"       {cue}"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(1)

    # Notes section at bottom
    pdf.ln(6)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Notes:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    for _ in range(4):
        pdf.cell(0, 8, "_" * 95, new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())


# ─────────────────────────────────────────────
# Workout Balance Analysis
# ─────────────────────────────────────────────

def analyze_workout_balance(workout: list[dict], theme: str) -> dict:
    """Analyze a workout for balance and coverage. Returns stats + suggestions."""
    if not workout:
        return {"score": 0, "notes": [], "categories": {}}

    phases = Counter(ex.get("phase_label", "").capitalize() for ex in workout)
    categories = Counter(ex.get("category", "Unknown") for ex in workout)
    themes_hit = set()
    for ex in workout:
        for t in ex.get("themes", []):
            themes_hit.add(t)

    total = len(workout)
    notes = []
    score = 100

    # Check phase balance
    warmup_pct = phases.get("Warmup", 0) / total * 100
    cooldown_pct = phases.get("Cooldown", 0) / total * 100
    if warmup_pct < 10:
        notes.append("⚠️ Light on warmup — consider adding a prep exercise")
        score -= 10
    if cooldown_pct < 10:
        notes.append("⚠️ Light on cooldown — add a stretch or mobility move")
        score -= 10

    # Check if theme is covered
    if theme != "Full Body" and theme not in themes_hit:
        notes.append(f"⚠️ Your theme '{theme}' isn't well represented — try swapping in themed exercises")
        score -= 15

    # Check body region balance
    upper = sum(1 for ex in workout if "Upper Body" in ex.get("themes", []))
    lower = sum(1 for ex in workout if "Lower Body" in ex.get("themes", []))
    core = sum(1 for ex in workout if "Core" in ex.get("themes", []))

    if upper == 0:
        notes.append("💡 No upper body work — consider adding arms or pulling straps")
        score -= 10
    if lower == 0:
        notes.append("💡 No lower body work — consider adding footwork or hip exercises")
        score -= 10
    if core == 0:
        notes.append("💡 No core focus — the center of Pilates! Add abdominal work")
        score -= 15

    # Check variety
    if len(categories) < 3:
        notes.append("💡 Low variety — try exercises from different categories for a more complete session")
        score -= 10

    if not notes:
        notes.append("✅ Well-balanced workout! Great mix of phases, body regions, and categories.")

    score = max(0, min(100, score))

    return {
        "score": score,
        "notes": notes,
        "phases": dict(phases),
        "categories": dict(categories),
        "body_regions": {"Upper Body": upper, "Lower Body": lower, "Core": core},
        "themes_covered": list(themes_hit),
    }


# ─────────────────────────────────────────────
# Smart Recommendations
# ─────────────────────────────────────────────

def get_smart_recommendations(history_df: pd.DataFrame, user: str) -> list[str]:
    """Analyze workout history and suggest programming improvements — instructor perspective."""
    recs = []
    if history_df.empty:
        recs.append("🌟 Start with a 30-min Reformer session using 'Core' theme — it's the foundation of every good Pilates practice.")
        return recs

    user_df = history_df[history_df["User"] == user] if "User" in history_df.columns else history_df
    if user_df.empty:
        recs.append("🌟 No workouts logged yet — try a Reformer session to get your baseline.")
        return recs

    # Analyze apparatus coverage
    apparatus_used = []
    for _, row in user_df.iterrows():
        try:
            exercises = json.loads(row.get("Full_JSON_Data", "[]"))
            if isinstance(exercises, dict):
                apparatus_used.append(exercises.get("apparatus", "Unknown"))
            elif isinstance(exercises, list) and exercises:
                apparatus_used.append(exercises[0].get("apparatus", "Unknown"))
        except (json.JSONDecodeError, TypeError):
            pass

    app_counts = Counter(apparatus_used)
    core_apparatus = ["Reformer", "Mat", "Chair", "Cadillac"]
    unused = [a for a in core_apparatus if a not in app_counts]
    if unused:
        recs.append(f"🔄 **Apparatus gap:** You haven't programmed {', '.join(unused)} yet — cross-training across apparatus builds more complete body awareness.")

    most_used = app_counts.most_common(1)
    total_sessions = len(user_df)
    if most_used and total_sessions > 3:
        top_app, top_count = most_used[0]
        pct = top_count / total_sessions * 100
        if pct > 65:
            recs.append(f"⚖️ **Variety check:** {pct:.0f}% of your sessions are {top_app}. Consider alternating with a different apparatus to work different stabilizer patterns.")

    # Theme coverage analysis
    themes_used = [row.get("Theme", "") for _, row in user_df.iterrows() if row.get("Theme")]
    theme_counts = Counter(themes_used)
    key_themes = ["Core", "Flexibility", "Upper Body", "Lower Body"]
    missing_themes = [t for t in key_themes if t not in theme_counts]
    if missing_themes:
        recs.append(f"🎯 **Theme gap:** You haven't focused on {', '.join(missing_themes)} — a well-rounded program cycles through all movement themes over time.")

    # Progression suggestion
    if total_sessions >= 5:
        recs.append("📐 **Progression idea:** After 5+ sessions at a given difficulty, try bumping one phase up — e.g. swap beginner Foundation exercises for intermediate ones while keeping Warmup and Cooldown the same.")

    if total_sessions >= 10 and "Mat" not in app_counts:
        recs.append("🧘 **Mat work builds intelligence:** Even dedicated Reformer practitioners benefit from Mat — it removes spring assistance and reveals where true strength lives.")

    if total_sessions >= 3 and total_sessions < 10:
        recs.append("📝 **Programming tip:** Build a 2-3 session weekly rotation — e.g. Mon: Reformer/Core, Wed: Mat/Flexibility, Fri: Reformer/Full Body — to ensure balanced development.")

    if not recs:
        recs.append("✅ Your programming looks well-rounded — keep varying apparatus and themes to maintain progress.")

    return recs[:5]


# ─────────────────────────────────────────────
# Progress Stats
# ─────────────────────────────────────────────

def calculate_progress_stats(history_df: pd.DataFrame, user: str) -> dict:
    """Calculate streaks, totals, and trends for the progress dashboard."""
    stats = {
        "total_workouts": 0, "total_minutes": 0, "avg_rating": 0,
        "current_streak": 0, "best_streak": 0, "this_week": 0,
        "this_month": 0, "apparatus_breakdown": {}, "theme_breakdown": {},
        "weekly_data": [], "ratings_over_time": [],
    }

    if history_df.empty:
        return stats

    user_df = history_df[history_df["User"] == user] if "User" in history_df.columns else history_df
    if user_df.empty:
        return stats

    stats["total_workouts"] = len(user_df)

    # Total minutes
    durations = pd.to_numeric(user_df.get("Duration", pd.Series(dtype=float)), errors="coerce")
    stats["total_minutes"] = int(durations.sum()) if not durations.empty else 0

    # Average rating
    ratings = pd.to_numeric(user_df.get("Rating", pd.Series(dtype=float)), errors="coerce").dropna()
    stats["avg_rating"] = round(ratings.mean(), 1) if not ratings.empty else 0

    # Dates analysis
    try:
        dates = pd.to_datetime(user_df["Date"], errors="coerce").dropna().sort_values()
        if not dates.empty:
            unique_dates = sorted(set(dates.dt.date))
            today = date.today()

            # This week / month
            week_start = today - timedelta(days=today.weekday())
            month_start = today.replace(day=1)
            stats["this_week"] = sum(1 for d in unique_dates if d >= week_start)
            stats["this_month"] = sum(1 for d in unique_dates if d >= month_start)

            # Streak calculation
            current_streak = 0
            best_streak = 0
            streak = 1
            for i in range(len(unique_dates) - 1, 0, -1):
                diff = (unique_dates[i] - unique_dates[i-1]).days
                if diff <= 3:  # Allow up to 3 days gap (rest days are normal in Pilates)
                    streak += 1
                else:
                    best_streak = max(best_streak, streak)
                    streak = 1
            best_streak = max(best_streak, streak)

            # Current streak (from today backwards)
            if unique_dates and (today - unique_dates[-1]).days <= 3:
                current_streak = 1
                for i in range(len(unique_dates) - 1, 0, -1):
                    diff = (unique_dates[i] - unique_dates[i-1]).days
                    if diff <= 3:
                        current_streak += 1
                    else:
                        break

            stats["current_streak"] = current_streak
            stats["best_streak"] = best_streak

            # Weekly data for chart (last 8 weeks)
            weekly_data = []
            for w in range(7, -1, -1):
                wk_start = today - timedelta(days=today.weekday() + 7 * w)
                wk_end = wk_start + timedelta(days=6)
                count = sum(1 for d in unique_dates if wk_start <= d <= wk_end)
                weekly_data.append({"week": wk_start.strftime("%b %d"), "workouts": count})
            stats["weekly_data"] = weekly_data
    except Exception:
        pass

    # Apparatus breakdown
    for _, row in user_df.iterrows():
        try:
            exercises = json.loads(row.get("Full_JSON_Data", "[]"))
            if isinstance(exercises, dict):
                a = exercises.get("apparatus", "Unknown")
            elif isinstance(exercises, list) and exercises:
                a = exercises[0].get("apparatus", "Unknown")
            else:
                a = "Unknown"
            stats["apparatus_breakdown"][a] = stats["apparatus_breakdown"].get(a, 0) + 1
        except (json.JSONDecodeError, TypeError):
            pass

    # Theme breakdown
    for _, row in user_df.iterrows():
        t = row.get("Theme", "Unknown")
        if t:
            stats["theme_breakdown"][t] = stats["theme_breakdown"].get(t, 0) + 1

    return stats


# ─────────────────────────────────────────────
# Session State Initialization
# ─────────────────────────────────────────────

DEFAULTS = {
    "workout": None,
    "current_index": 0,
    "timer_running": False,
    "timer_start": None,
    "elapsed": 0,
    "view": "generator",       # "generator", "player", "history", "ai_chat", "dashboard"
    "chat_messages": [],
    "workout_rated": False,
    "ai_messages": [],         # General AI chat history
    "workout_meta": {},        # Store theme/apparatus/duration for current workout
    "favorites": [],           # List of favorite workout JSON strings
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
    st.markdown("---")
    if st.button("❓ Help & Features", use_container_width=True, key="nav_help"):
        st.session_state.view = "help"
        # no rerun needed, falls through


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

nav_col1, nav_col2, nav_col3, nav_col4 = st.columns(4)
with nav_col1:
    if st.button("🎲 GENERATE", use_container_width=True, type="primary",
                  key="nav_gen"):
        st.session_state.view = "generator"
        st.session_state.workout = None
        st.rerun()
with nav_col2:
    if st.button("📊 DASHBOARD", use_container_width=True, type="secondary",
                  key="nav_dash"):
        st.session_state.view = "dashboard"
        st.rerun()
with nav_col3:
    if st.button("📖 HISTORY", use_container_width=True, type="secondary",
                  key="nav_hist"):
        st.session_state.view = "history"
        st.rerun()
with nav_col4:
    if st.button("🤖 AI COACH", use_container_width=True, type="secondary",
                  key="nav_ai"):
        st.session_state.view = "ai_chat"
        st.rerun()

# Show which view is active
active_labels = {
    "generator": ("● Generate Workout", "#6C63FF"),
    "player": ("● Generate Workout", "#6C63FF"),
    "finish": ("● Generate Workout", "#6C63FF"),
    "dashboard": ("● Progress Dashboard", "#10B981"),
    "history": ("● Workout History", "#00B4D8"),
    "ai_chat": ("● AI Pilates Coach", "#FF6B35"),
    "help": ("● Help & Features", "#888"),
}
label, color = active_labels.get(st.session_state.view, ("", "#666"))
if label:
    st.markdown(f'<div style="text-align:center; color:{color}; font-weight:700; font-size:0.9rem; margin-bottom:0.5rem;">{label}</div>', unsafe_allow_html=True)

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
        difficulty = st.selectbox("Difficulty", ["All Levels", "Beginner", "Intermediate", "Advanced"])
    with col2:
        theme = st.selectbox("Theme / Focus", THEMES)
        energy = st.selectbox("Energy Level", list(ENERGY_LEVELS.keys()))

    if st.button("🎲 Generate Workout", type="primary", use_container_width=True):
        workout = generate_workout(duration, apparatus, theme, energy)
        # Filter by difficulty if selected
        if difficulty != "All Levels":
            diff_lower = difficulty.lower()
            filtered = [ex for ex in workout if ex.get("level", "all") in (diff_lower, "all")]
            if len(filtered) >= 4:
                workout = filtered
        st.session_state.workout = workout
        st.session_state.current_index = 0
        st.session_state.timer_running = False
        st.session_state.elapsed = 0
        st.session_state.chat_messages = []
        st.session_state.workout_rated = False
        st.session_state.workout_meta = {
            "theme": theme, "apparatus": apparatus,
            "duration": duration, "energy": energy, "difficulty": difficulty,
        }

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

        # ─── Workout Balance Analysis ───
        st.markdown("---")
        meta = st.session_state.get("workout_meta", {})
        w_theme = meta.get("theme", "Full Body")
        analysis = analyze_workout_balance(workout, w_theme)

        score = analysis["score"]
        score_color = "#10B981" if score >= 80 else "#F59E0B" if score >= 60 else "#EF4444"
        st.markdown(f'<div style="text-align:center; margin-bottom:0.5rem;">'
                    f'<span style="font-size:2rem; font-weight:800; color:{score_color};">{score}</span>'
                    f'<span style="color:#666; font-size:0.9rem;">/100 Balance Score</span></div>',
                    unsafe_allow_html=True)

        for note in analysis["notes"]:
            st.caption(note)

        # Body region breakdown
        regions = analysis.get("body_regions", {})
        if any(regions.values()):
            r_cols = st.columns(3)
            for i, (region, count) in enumerate(regions.items()):
                with r_cols[i]:
                    st.metric(region, f"{count} exercises")

        # ─── Action Buttons ───
        st.markdown("---")

        # Row 1: Primary actions
        col_start, col_save = st.columns(2)
        with col_start:
            if st.button("▶️ Start Workout", type="primary", use_container_width=True):
                st.session_state.view = "player"
                st.session_state.current_index = 0
                st.session_state.timer_running = False
                st.session_state.elapsed = 0
                st.rerun()
        with col_save:
            w_apparatus = meta.get("apparatus", "")
            w_duration = meta.get("duration", 0)
            if st.button("💾 Save to History", use_container_width=True):
                saved = save_workout(
                    user=user,
                    theme=w_theme,
                    duration=w_duration,
                    workout_json=workout_to_json(workout),
                )
                if saved:
                    st.toast("Workout saved! ✅")

        # Row 2: Share & Favorite
        col_pdf, col_fav = st.columns(2)
        with col_pdf:
            try:
                pdf_bytes = generate_workout_pdf(
                    workout, user,
                    theme=w_theme,
                    duration=meta.get("duration", 0),
                    apparatus=meta.get("apparatus", ""),
                )
                st.download_button(
                    "📄 SHARE / EXPORT PDF",
                    data=pdf_bytes,
                    file_name=f"pilates_workout_{date.today().isoformat()}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as pdf_err:
                st.button("📄 PDF unavailable", disabled=True, use_container_width=True,
                           help=f"PDF error: {pdf_err}")
        with col_fav:
            if st.button("⭐ Save as Favorite", use_container_width=True, key="fav_gen"):
                fav_data = {
                    "name": f"{w_theme} {meta.get('apparatus', '')} ({meta.get('duration', '')}min)",
                    "date_saved": date.today().isoformat(),
                    "meta": meta,
                    "exercises": workout,
                }
                if "favorites" not in st.session_state:
                    st.session_state.favorites = []
                st.session_state.favorites.append(fav_data)
                st.toast("⭐ Added to favorites!")


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

    # ─── Session Timer (always visible at top) ───
    if st.session_state.timer_running and st.session_state.timer_start:
        elapsed_t = st.session_state.elapsed + (
            time_module.time() - st.session_state.timer_start
        )
        # Auto-refresh every second while running
        if HAS_AUTOREFRESH:
            st_autorefresh(interval=1000, limit=None, key="timer_tick")
    else:
        elapsed_t = st.session_state.elapsed

    mins_t, secs_t = divmod(int(elapsed_t), 60)
    hrs_t, mins_t = divmod(mins_t, 60)

    timer_c1, timer_c2, timer_c3, timer_c4 = st.columns([3, 1, 1, 1])
    with timer_c1:
        st.markdown(
            f'<div class="timer-display">{hrs_t:02d}:{mins_t:02d}:{secs_t:02d}</div>',
            unsafe_allow_html=True,
        )
    with timer_c2:
        if not st.session_state.timer_running:
            if st.button("▶ Start", use_container_width=True, key="timer_start"):
                st.session_state.timer_running = True
                st.session_state.timer_start = time_module.time()
                st.rerun()
        else:
            if st.button("⏸ Pause", use_container_width=True, key="timer_pause"):
                st.session_state.elapsed += (
                    time_module.time() - st.session_state.timer_start
                )
                st.session_state.timer_running = False
                st.session_state.timer_start = None
                st.rerun()
    with timer_c3:
        if st.button("↺ Reset", use_container_width=True, key="timer_reset"):
            st.session_state.elapsed = 0
            st.session_state.timer_running = False
            st.session_state.timer_start = None
            st.rerun()
    with timer_c4:
        est_total = sum(e.get("duration_min", 5) for e in workout)
        st.caption(f"Est. {est_total}min")

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

    # Extra actions row
    fin_col1, fin_col2 = st.columns(2)
    meta = st.session_state.get("workout_meta", {})
    with fin_col1:
        try:
            pdf_bytes = generate_workout_pdf(
                workout, user,
                theme=meta.get("theme", ""),
                duration=int(total_time),
                apparatus=meta.get("apparatus", ""),
            )
            st.download_button(
                "📄 SHARE / EXPORT PDF",
                data=pdf_bytes,
                file_name=f"pilates_workout_{date.today().isoformat()}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as pdf_err:
            st.button("📄 PDF unavailable", disabled=True, use_container_width=True,
                       help=f"PDF error: {pdf_err}")
    with fin_col2:
        if st.button("⭐ Save as Favorite", use_container_width=True, key="fav_finish"):
            fav_data = {
                "name": f"{meta.get('theme', 'Workout')} {meta.get('apparatus', '')} ({int(total_time)}min)",
                "date_saved": date.today().isoformat(),
                "meta": meta,
                "exercises": workout,
            }
            if "favorites" not in st.session_state:
                st.session_state.favorites = []
            st.session_state.favorites.append(fav_data)
            st.toast("⭐ Added to favorites!")


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
            col_exp, col_btn = st.columns([4, 2])
            with col_exp:
                with st.expander(f"📋 {row['Date']} — {row['Theme']} ({row['Duration']} min)"):
                    try:
                        exercises = json_to_workout(row["Full_JSON_Data"])
                        current_phase = ""
                        for j, ex in enumerate(exercises):
                            name = ex.get('name', 'Unknown')
                            apparatus = ex.get('apparatus', '')
                            phase = ex.get('phase_label', ex.get('phase', '')).capitalize() if ex.get('phase_label') or ex.get('phase') else ''
                            duration = ex.get('duration_min', '')
                            springs = ex.get('default_springs', ex.get('springs', ''))
                            reps = ex.get('reps', '')
                            cues = ex.get('cues', [])
                            category = ex.get('category', '')

                            # Phase header
                            if phase and phase != current_phase:
                                current_phase = phase
                                phase_colors = {"Warmup": "#FF6B35", "Foundation": "#E6394A", "Peak": "#9B5DE5", "Cooldown": "#00B4D8"}
                                p_color = phase_colors.get(phase, "#666")
                                st.markdown(f'<div style="background:{p_color}; color:white; padding:4px 10px; border-radius:6px; font-weight:700; font-size:0.8rem; margin:8px 0 4px 0; display:inline-block;">{phase.upper()}</div>', unsafe_allow_html=True)

                            # Exercise line
                            line = f"**{j+1}. {name}**"
                            if apparatus:
                                line += f" ({apparatus})"
                            details = []
                            if duration:
                                details.append(f"{duration} min")
                            if springs and springs != "N/A":
                                details.append(f"Springs: {springs}")
                            if category:
                                details.append(category)
                            if reps:
                                details.append(f"{reps}")
                            if details:
                                line += f" — {' · '.join(details)}"
                            st.markdown(line)

                            # Show cues
                            if isinstance(cues, list) and any(c for c in cues if c):
                                for cue in cues[:3]:
                                    if cue:
                                        st.caption(f"  ▸ {cue}")

                    except Exception:
                        st.caption("Could not parse workout data.")
                    if row.get("Notes"):
                        st.markdown(f"*Notes: {row['Notes']}*")
            with col_btn:
                if st.button("🔁 Repeat", key=f"repeat_{i}", help="Load this workout",
                              use_container_width=True):
                    try:
                        exercises = json_to_workout(row["Full_JSON_Data"])
                        st.session_state.workout = exercises
                        st.session_state.view = "player"
                        st.rerun()
                    except Exception:
                        st.error("Could not load this workout.")
                try:
                    pdf_exercises = json_to_workout(row["Full_JSON_Data"])
                    if pdf_exercises:
                        pdf_data = generate_workout_pdf(
                            pdf_exercises, user,
                            theme=row.get("Theme", ""),
                            duration=int(row.get("Duration", 0)) if row.get("Duration") else 0,
                        )
                        st.download_button(
                            "📄 PDF", data=pdf_data, key=f"pdf_{i}",
                            file_name=f"workout_{row.get('Date', 'export')}.pdf",
                            mime="application/pdf", help="Download PDF",
                            use_container_width=True,
                        )
                except Exception:
                    pass


# ─────────────────────────────────────────────
# View: Progress Dashboard
# ─────────────────────────────────────────────

elif st.session_state.view == "dashboard":
    st.markdown(f"### 📊 Progress Dashboard — {user}")

    history = load_history(user)
    stats = calculate_progress_stats(history, user)

    # ─── Top Metrics Row ───
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Workouts", stats["total_workouts"])
    with m2:
        hrs = stats["total_minutes"] // 60
        mins = stats["total_minutes"] % 60
        st.metric("Total Time", f"{hrs}h {mins}m" if hrs else f"{mins}m")
    with m3:
        avg_r = stats["avg_rating"]
        st.metric("Avg Rating", f"{'⭐' * int(avg_r)} {avg_r}" if avg_r else "—")
    with m4:
        st.metric("Current Streak", f"🔥 {stats['current_streak']}")

    # ─── Secondary Metrics ───
    s1, s2, s3 = st.columns(3)
    with s1:
        st.metric("This Week", stats["this_week"])
    with s2:
        st.metric("This Month", stats["this_month"])
    with s3:
        st.metric("Best Streak", f"{stats['best_streak']} sessions")

    st.markdown("---")

    # ─── Apparatus & Theme Breakdown ───
    breakdown_col1, breakdown_col2 = st.columns(2)

    with breakdown_col1:
        st.markdown("#### 🏋️ Apparatus Breakdown")
        app_data = stats.get("apparatus_breakdown", {})
        if app_data:
            for apparatus_name, count in sorted(app_data.items(), key=lambda x: -x[1]):
                pct = count / stats["total_workouts"] * 100 if stats["total_workouts"] else 0
                label = "session" if count == 1 else "sessions"
                st.markdown(f"**{apparatus_name}**: {count} {label} ({pct:.0f}%)")
                st.progress(min(pct / 100, 1.0))
        else:
            st.caption("No data yet")

    with breakdown_col2:
        st.markdown("#### 🎯 Theme Breakdown")
        theme_data = stats.get("theme_breakdown", {})
        if theme_data:
            for theme_name, count in sorted(theme_data.items(), key=lambda x: -x[1]):
                pct = count / stats["total_workouts"] * 100 if stats["total_workouts"] else 0
                label = "session" if count == 1 else "sessions"
                st.markdown(f"**{theme_name}**: {count} {label} ({pct:.0f}%)")
                st.progress(min(pct / 100, 1.0))
        else:
            st.caption("No data yet")

    st.markdown("---")

    # ─── Programming Insights ───
    st.markdown("#### 📐 Programming Insights")
    recs = get_smart_recommendations(history, user)
    for rec in recs:
        st.markdown(f'<div style="background:white; padding:10px 14px; border-radius:10px; margin:6px 0; border-left:4px solid #6C63FF; font-size:0.95rem;">{rec}</div>', unsafe_allow_html=True)

    st.markdown("---")

    # ─── Calendar View ───
    st.markdown("#### 🗓️ Workout Calendar")
    if not history.empty:
        try:
            cal_dates = pd.to_datetime(history[history["User"] == user]["Date"], errors="coerce").dropna()
            unique_dates = sorted(set(cal_dates.dt.date))

            if unique_dates:
                # Show current month calendar
                today = date.today()
                month_start = today.replace(day=1)
                if today.month == 12:
                    month_end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    month_end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)

                # Build calendar grid
                import calendar
                cal = calendar.monthcalendar(today.year, today.month)
                st.markdown(f"**{today.strftime('%B %Y')}**")

                # Day headers
                header_cols = st.columns(7)
                for i, day_name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
                    with header_cols[i]:
                        st.markdown(f"<div style='text-align:center; font-weight:700; color:#666; font-size:0.8rem;'>{day_name}</div>", unsafe_allow_html=True)

                # Calendar weeks
                for week in cal:
                    week_cols = st.columns(7)
                    for i, day in enumerate(week):
                        with week_cols[i]:
                            if day == 0:
                                st.markdown("")
                            else:
                                d = date(today.year, today.month, day)
                                if d in unique_dates:
                                    st.markdown(f"<div style='text-align:center; background:#6C63FF; color:white; border-radius:50%; width:32px; height:32px; line-height:32px; margin:auto; font-weight:700;'>{day}</div>", unsafe_allow_html=True)
                                elif d == today:
                                    st.markdown(f"<div style='text-align:center; border:2px solid #6C63FF; border-radius:50%; width:32px; height:32px; line-height:32px; margin:auto;'>{day}</div>", unsafe_allow_html=True)
                                else:
                                    st.markdown(f"<div style='text-align:center; color:#aaa; width:32px; height:32px; line-height:32px; margin:auto;'>{day}</div>", unsafe_allow_html=True)
        except Exception:
            st.caption("Could not generate calendar.")
    else:
        st.caption("Complete some workouts to see your calendar!")

    st.markdown("---")

    # ─── Favorites ───
    st.markdown("#### ⭐ Favorite Workouts")
    favorites = st.session_state.get("favorites", [])
    if favorites:
        for fi, fav in enumerate(favorites):
            fav_col1, fav_col2 = st.columns([5, 1])
            with fav_col1:
                st.markdown(f"**{fav.get('name', 'Unnamed')}** — saved {fav.get('date_saved', '')}")
            with fav_col2:
                if st.button("▶️", key=f"play_fav_{fi}", help="Load this workout"):
                    st.session_state.workout = fav.get("exercises", [])
                    st.session_state.workout_meta = fav.get("meta", {})
                    st.session_state.view = "player"
                    st.session_state.current_index = 0
                    st.rerun()
    else:
        st.caption("No favorites yet — generate a workout and tap ⭐ to save it here!")


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


# ─────────────────────────────────────────────
# View: Help & Features
# ─────────────────────────────────────────────

elif st.session_state.view == "help":

    st.markdown("### ❓ Help & Features Guide")
    st.markdown("*Everything you can do in The Pilates Flow Studio*")
    st.markdown("---")

    # ─── Overview ───
    st.markdown("""
    <div style="background:white; padding:16px 20px; border-radius:12px; margin-bottom:16px; box-shadow:0 2px 8px rgba(0,0,0,0.06);">
    <h4 style="margin-top:0;">👋 Welcome to The Pilates Flow Studio!</h4>
    <p style="color:#555;">This app generates smart, balanced Pilates workouts tailored to your time, equipment,
    energy level, and goals. It tracks your history, analyzes your progress, and even has an AI coach
    you can ask questions any time.</p>
    <p style="color:#555;"><strong>193 real Pilates exercises</strong> across Reformer, Mat, Chair, Cadillac, Ladder Barrel, and Spine Corrector — every exercise is from the recognized Pilates repertoire, nothing made up.</p>
    </div>
    """, unsafe_allow_html=True)

    # ─── Generate Workout ───
    with st.expander("🎲 **GENERATE WORKOUT** — Build a custom session", expanded=True):
        st.markdown("""
**How to use:**
1. Choose your **Duration** (30–90 minutes)
2. Select your **Apparatus** — Reformer, Mat, Chair, Cadillac, Ladder Barrel, Spine Corrector, or Mixed
3. Pick a **Theme** — Core, Flexibility, Lower Body, Upper Body, Full Body, or Balance
4. Set your **Energy Level** — Gentle through Intense
5. Choose **Difficulty** — Beginner, Intermediate, Advanced, or All Levels
6. Tap **Generate Workout**

**What happens next:**
- The app builds a session using the **bell curve method**: Warmup (20%) → Foundation (30%) → Peak (30%) → Cooldown (20%)
- Each exercise shows the name, springs, duration, category, and coaching cues
- A **Balance Score** (out of 100) analyzes your workout for phase coverage, body region balance, and variety
- You'll see specific suggestions if the workout is unbalanced

**Customizing your workout:**
- Tap **🔄** on any exercise to swap it out
- Three swap options appear:
  - **🎲 Random Swap** — finds a similar exercise in the same phase and category
  - **🔍 Browse & Search** — filter by phase, apparatus, or type a keyword (e.g. "arm", "hip", "stretch")
  - **🤖 AI Suggest** — describe what you want in plain English (e.g. "something easier for my back") and AI picks from the real database

**Actions:**
- **▶️ Start Workout** — enter the player view to step through exercises one by one
- **💾 Save to History** — log the workout to your Google Sheets history
- **📄 Export PDF** — download a beautifully formatted PDF to text or email to someone
- **⭐ Save as Favorite** — bookmark this workout for quick replay later
        """)

    # ─── Player View ───
    with st.expander("▶️ **PLAYER VIEW** — Step through your workout"):
        st.markdown("""
**How it works:**
- Navigate through exercises one at a time with **← Prev** and **Next →** buttons
- A progress bar shows where you are in the session
- Each exercise shows full details: name, springs, phase, cues, and category

**Timer:**
- The session timer sits at the top of the player view — always visible
- Hit **▶ Start** to begin — it ticks live in real-time
- **⏸ Pause** to stop it, **↺ Reset** to clear it
- Shows estimated total workout time on the right

**AI Instructor:**
- A chat box appears on each exercise
- Ask questions like "How should I set the springs?" or "What if this hurts my knee?"
- The AI knows which exercise you're on and gives specific, contextual answers

**Swap mid-workout:**
- Tap **🔄 Swap This Exercise** to replace the current move without leaving the player

**Finishing:**
- Tap **✅ Finish** on the last exercise
- Rate your session (1–5 stars) and add optional notes
- Your rating and notes are saved to your history
        """)

    # ─── Dashboard ───
    with st.expander("📊 **PROGRESS DASHBOARD** — Track your journey"):
        st.markdown("""
**Metrics at a glance:**
- **Total Workouts** — lifetime count
- **Total Time** — hours and minutes you've practiced
- **Average Rating** — how your sessions have felt
- **Current Streak** — consecutive sessions (allows up to 3 rest days between)
- **This Week / This Month** — recent activity counts
- **Best Streak** — your personal record

**Charts & Breakdowns:**
- **Apparatus Breakdown** — percentage of time on each piece of equipment
- **Theme Breakdown** — which focus areas you've been training

**Calendar View:**
- Purple dots mark days you worked out this month
- A circle marks today's date

**Programming Insights:**
- The app analyzes your history from an instructor perspective
- Flags apparatus gaps, theme imbalances, and progression opportunities
- Examples: "65% Reformer — alternate apparatus", "Build a 2-3 session weekly rotation"

**Favorites:**
- Quick-replay any workout you've starred
- Tap ▶️ next to a favorite to load it into the player
        """)

    # ─── History ───
    with st.expander("📖 **WORKOUT HISTORY** — Review past sessions"):
        st.markdown("""
**What you see:**
- Every saved workout, most recent first
- Date, theme, duration, and rating for each session
- Expandable details showing every exercise in the workout

**Summary metrics at the top:**
- Total sessions, average rating, average duration

**Actions on each workout:**
- **🔁** — Reload this workout into the player to repeat it
- **📄** — Download a PDF of this past workout

**Notes:** Your history is saved to Google Sheets and persists forever — it won't disappear when the app restarts.
        """)

    # ─── AI Coach ───
    with st.expander("🤖 **AI PILATES COACH** — Your personal instructor"):
        st.markdown("""
**What it can do:**
- **Exercise Lookup** — "Tell me about Short Spine Massage" → full breakdown with setup, springs, cues, modifications, muscles
- **Workout Recommendations** — "I have 40 minutes and tight hips" → structured session suggestion
- **Modifications** — "I have a bad knee, what should I avoid?" → safe alternatives
- **Spring Guidance** — "What springs for Stomach Massage on an Allegro?"
- **General Pilates Q&A** — breathing, form, philosophy, anatomy, anything

**Quick-tap buttons:**
- 🔍 Look up an exercise
- 💡 Suggest a workout
- 🩹 Modifications help
- 📚 Explain springs/setup

**Important:** The AI only recommends exercises from the app's real 193-exercise database. It will never make up fictional exercises.

**Requires:** An Anthropic API key in your Streamlit secrets (`anthropic_api_key`).
        """)

    # ─── PDF Export ───
    with st.expander("📄 **PDF EXPORT** — Share workouts"):
        st.markdown("""
**Where to find it:**
- After generating a workout → **📄 Export PDF** button
- After completing a workout → **📄 Export PDF** button
- In Workout History → **📄** icon on each past session

**What the PDF includes:**
- Studio header with date and your name
- All exercises organized by phase with color-coded headers
- Springs, duration, category, and coaching cues for each exercise
- Blank notes section at the bottom

**Use it to:**
- Text a workout to your partner or trainer
- Email a session plan to yourself for the studio
- Print it and bring it to your Pilates session
        """)

    # ─── User Profiles ───
    with st.expander("👤 **USER PROFILES** — Keep histories separate"):
        st.markdown("""
**How it works:**
- Open the sidebar (swipe right on mobile or click the arrow)
- Select your name from the dropdown
- All workout history, dashboard stats, and recommendations are per-user

**Profiles available:** Alyssa, Ted (Test)

Your profile selection is remembered during your session. Each person's workout history is completely separate in the Google Sheet.
        """)

    # ─── Tips ───
    with st.expander("💡 **TIPS FOR BEST RESULTS**"):
        st.markdown("""
**For the best workouts:**
- Start with **Moderate** energy if you're unsure — you can always swap in harder exercises
- Use the **Balance Score** as a guide — aim for 80+ for a well-rounded session
- The **bell curve** structure (Warmup → Foundation → Peak → Cooldown) is how professional studios program classes

**On your phone:**
- The app is optimized for iPhone — buttons are large and easy to tap
- Add it to your home screen: in Safari, tap Share → Add to Home Screen → it'll feel like a native app
- The sidebar collapses by default — all main navigation is in the top buttons

**Building your practice:**
- Aim for 2–3 sessions per week
- Alternate between apparatus (Reformer one day, Mat the next)
- Use different themes to ensure full-body coverage over the week
- Check your Dashboard weekly to spot gaps in your training
        """)

    st.markdown("---")
    st.markdown("""
    <div style="text-align:center; color:#999; font-size:0.85rem; padding:8px;">
        The Pilates Flow Studio v1.0<br>
        193 exercises · 6 apparatus · AI-powered coaching<br>
        Built with ❤️ for balanced movement
    </div>
    """, unsafe_allow_html=True)
