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
    THEMES, APPARATUS_OPTIONS, ENERGY_LEVELS, PHASE_ORDER,
)

# ─────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Pilates Flow Studio",
    page_icon="🧘",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# Custom Styling
# ─────────────────────────────────────────────

st.markdown("""
<style>
    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #faf5f0 0%, #f0e6d8 100%);
    }

    /* Phase headers */
    .phase-warmup { color: #e8913a; font-weight: 700; font-size: 1.1rem; }
    .phase-foundation { color: #c0392b; font-weight: 700; font-size: 1.1rem; }
    .phase-peak { color: #8e44ad; font-weight: 700; font-size: 1.1rem; }
    .phase-cooldown { color: #2980b9; font-weight: 700; font-size: 1.1rem; }

    /* Exercise card */
    .exercise-card {
        background: white;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 0.8rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        border-left: 4px solid #c0946e;
    }
    .exercise-card h4 { margin: 0 0 0.4rem 0; color: #3d2b1f; }
    .exercise-card .meta { color: #8b7d6b; font-size: 0.85rem; }
    .exercise-card .cue { color: #5a4e42; font-size: 0.9rem; padding-left: 0.6rem;
                          border-left: 2px solid #d4c4b0; margin: 0.3rem 0; }

    /* Timer display */
    .timer-display {
        font-size: 2.5rem;
        font-weight: 300;
        text-align: center;
        color: #3d2b1f;
        font-family: 'Courier New', monospace;
        padding: 0.5rem;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #3d2b1f 0%, #5a4232 100%);
    }
    section[data-testid="stSidebar"] .stMarkdown { color: #f0e6d8; }
    section[data-testid="stSidebar"] label { color: #f0e6d8 !important; }

    /* Header */
    .studio-header {
        text-align: center;
        padding: 1rem 0 0.5rem 0;
    }
    .studio-header h1 {
        color: #3d2b1f;
        font-weight: 300;
        font-size: 2.2rem;
        letter-spacing: 0.05em;
    }
    .studio-header p { color: #8b7d6b; font-style: italic; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# Google Sheets Connection
# ─────────────────────────────────────────────

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@st.cache_resource
def get_gspread_client():
    """Authenticate with Google using Streamlit secrets.
    
    Supports TWO formats:
    1. Simple: gcp_service_account_json = '{...entire JSON key...}'
    2. Traditional: [gcp_service_account] section with individual fields
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
        if sheet_url:
            return client.open_by_url(sheet_url)
        elif sheet_id:
            return client.open_by_key(sheet_id)
        else:
            return client.open("Pilates Flow Studio")
    except Exception as e:
        st.error(f"Could not open spreadsheet: {e}")
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
    "view": "generator",       # "generator", "player", "history"
    "chat_messages": [],
    "workout_rated": False,
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
    nav = st.radio(
        "Navigate",
        ["🎲 Generate Workout", "📖 Workout History"],
        label_visibility="collapsed",
    )

    if nav == "📖 Workout History":
        st.session_state.view = "history"
    elif st.session_state.view == "history":
        st.session_state.view = "generator"

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
# View: Generator
# ─────────────────────────────────────────────

if st.session_state.view == "generator":
    st.markdown("### Build Your Session")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        duration = st.slider("Duration (min)", 30, 90, 50, step=5)
    with col2:
        apparatus = st.selectbox("Apparatus", APPARATUS_OPTIONS)
    with col3:
        theme = st.selectbox("Theme / Focus", THEMES)
    with col4:
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
        total_time = sum(e["duration_min"] for e in workout)
        st.markdown(f"**{len(workout)} exercises** · ~**{total_time:.0f} min** total")

        # Group by phase
        current_phase = None
        for i, ex in enumerate(workout):
            phase = ex["phase_label"]
            if phase != current_phase:
                current_phase = phase
                css_class = f"phase-{phase.lower()}"
                st.markdown(f'<div class="{css_class}">▸ {phase.upper()}</div>',
                            unsafe_allow_html=True)

            with st.container():
                c1, c2, c3 = st.columns([6, 2, 1])
                with c1:
                    springs = f" · {ex['default_springs']}" if ex['default_springs'] != 'N/A' else ""
                    st.markdown(
                        f"""<div class="exercise-card">
                        <h4>{i+1}. {ex['name']}</h4>
                        <div class="meta">{ex['apparatus']}{springs} · {ex['duration_min']} min · Energy {ex['energy']}/5</div>
                        <div class="cue">{'</div><div class="cue">'.join(ex['cues'][:2])}</div>
                        </div>""",
                        unsafe_allow_html=True,
                    )
                with c2:
                    st.caption(ex["category"])
                with c3:
                    if st.button("🔄", key=f"swap_{i}", help="Swap this exercise"):
                        new_ex = smart_swap(workout, i)
                        if new_ex:
                            st.session_state.workout[i] = new_ex
                            st.rerun()
                        else:
                            st.toast("No alternative found for this slot.")

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
        css_class = f"phase-{ex['phase_label'].lower()}"
        st.markdown(f'<span class="{css_class}">{ex["phase_label"].upper()}</span>',
                    unsafe_allow_html=True)

        # Exercise title and info
        st.markdown(f"## {ex['name']}")

        info_cols = st.columns(3)
        with info_cols[0]:
            st.metric("Apparatus", ex["apparatus"])
        with info_cols[1]:
            st.metric("Springs", ex["default_springs"])
        with info_cols[2]:
            st.metric("Duration", f"{ex['duration_min']} min")

        # Cues
        st.markdown("#### Teaching Cues")
        for cue in ex["cues"]:
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
    total_time = sum(e["duration_min"] for e in workout)
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
            with st.expander(f"📋 {row['Date']} — {row['Theme']} ({row['Duration']} min)"):
                try:
                    exercises = json_to_workout(row["Full_JSON_Data"])
                    for j, ex in enumerate(exercises):
                        st.markdown(
                            f"**{j+1}. {ex['name']}** ({ex['apparatus']}) — "
                            f"{ex.get('phase_label', '')} · {ex['duration_min']} min"
                        )
                except (json.JSONDecodeError, KeyError):
                    st.caption("Could not parse workout data.")
                if row.get("Notes"):
                    st.markdown(f"*Notes: {row['Notes']}*")

