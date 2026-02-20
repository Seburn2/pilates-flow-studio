"""
pilates_logic.py — The Pilates Flow Brain
Exercise database, bell-curve generator, and smart-swap logic.
"""

import random
import json
from dataclasses import dataclass, field, asdict
from typing import Optional

# ─────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────

@dataclass
class Exercise:
    slug: str
    name: str
    apparatus: str          # "Reformer", "Mat", "Chair", "Cadillac", "Tower"
    category: str           # e.g. "Supine Abdominals", "Hip Work", "Arm Work"
    phase: str              # "warmup", "foundation", "peak", "cooldown"
    energy: int             # 1-5 intensity scale
    default_springs: str    # e.g. "2 Red" or "N/A" for mat
    duration_min: float     # typical minutes
    cues: list[str] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)  # "Core", "Flexibility", etc.
    image: str = ""         # filename in /assets

    def to_dict(self):
        return asdict(self)


# ─────────────────────────────────────────────
# Exercise Library
# ─────────────────────────────────────────────

EXERCISE_DB: list[Exercise] = [
    # ═══════════════════════════════════════════
    # REFORMER EXERCISES
    # ═══════════════════════════════════════════

    # --- Warmup ---
    Exercise("ref_footwork_parallel", "Footwork – Parallel", "Reformer", "Footwork",
             "warmup", 1, "3 Red + 1 Blue", 3.0,
             ["Heels together, toes apart", "Press evenly through all 10 toes",
              "Keep pelvis neutral – no tucking"],
             ["Core", "Lower Body", "Full Body"], "footwork_parallel.png"),
    Exercise("ref_footwork_v", "Footwork – V Position", "Reformer", "Footwork",
             "warmup", 1, "3 Red + 1 Blue", 2.0,
             ["Small V with heels touching", "Wrap outer hips",
              "Lengthen through the crown of the head"],
             ["Core", "Lower Body"], "footwork_v.png"),
    Exercise("ref_footwork_wide", "Footwork – Wide Second", "Reformer", "Footwork",
             "warmup", 2, "3 Red + 1 Blue", 2.0,
             ["Wider than hip-width on the bar", "Track knees over second toe",
              "Feel the inner thigh connection"],
             ["Lower Body", "Flexibility"], "footwork_wide.png"),
    Exercise("ref_footwork_toes", "Footwork – On Toes", "Reformer", "Footwork",
             "warmup", 2, "3 Red + 1 Blue", 2.0,
             ["Lift heels high", "Maintain ankle stability",
              "Press through the ball of the foot"],
             ["Lower Body", "Balance"], "footwork_toes.png"),
    Exercise("ref_hundred_prep", "Hundred Prep", "Reformer", "Supine Abdominals",
             "warmup", 2, "1 Red", 2.0,
             ["Chin to chest, eyes on belly", "Pump arms with control",
              "Breathe: inhale 5 counts, exhale 5 counts"],
             ["Core"], "hundred_prep.png"),
    Exercise("ref_warmup_bridging", "Bridging", "Reformer", "Supine Hip Work",
             "warmup", 1, "2 Red", 3.0,
             ["Articulate spine one vertebra at a time", "Press heels into bar",
              "Lengthen knees over toes at the top"],
             ["Core", "Lower Body", "Flexibility"], "bridging.png"),
    Exercise("ref_ribcage_arms", "Ribcage Arms", "Reformer", "Arm Work",
             "warmup", 1, "1 Blue", 2.0,
             ["Keep ribs anchored to the mat", "Arms float to ceiling then overhead",
              "Don't let the back arch"],
             ["Upper Body", "Core", "Flexibility"], "ribcage_arms.png"),

    # --- Foundation ---
    Exercise("ref_short_spine", "Short Spine Massage", "Reformer", "Supine Abdominals",
             "foundation", 3, "2 Red", 4.0,
             ["Use the straps to guide legs overhead", "Roll down one bone at a time",
              "Keep the carriage still as you fold"],
             ["Core", "Flexibility", "Full Body"], "short_spine.png"),
    Exercise("ref_coordination", "Coordination", "Reformer", "Supine Abdominals",
             "foundation", 3, "1 Red + 1 Blue", 3.0,
             ["Curl up, extend arms and legs simultaneously",
              "Open-close legs while holding the curl", "Everything returns together"],
             ["Core", "Full Body"], "coordination.png"),
    Exercise("ref_pulling_straps", "Pulling Straps", "Reformer", "Prone Back Extension",
             "foundation", 3, "1 Red", 3.0,
             ["Lie prone on the box", "Pull straps alongside the body",
              "Lift chest with back muscles, not arms"],
             ["Upper Body", "Core"], "pulling_straps.png"),
    Exercise("ref_backstroke", "Backstroke", "Reformer", "Supine Abdominals",
             "foundation", 3, "1 Red", 3.0,
             ["Start in a ball position", "Reach arms and legs to ceiling then open",
              "Circle everything back to start"],
             ["Core", "Full Body"], "backstroke.png"),
    Exercise("ref_long_stretch", "Long Stretch", "Reformer", "Plank / Full Body",
             "foundation", 3, "1 Red + 1 Blue", 3.0,
             ["Plank position, hands on the bar", "Push out through heels",
              "Pull carriage home with abdominals"],
             ["Core", "Upper Body", "Full Body"], "long_stretch.png"),
    Exercise("ref_elephant", "Elephant", "Reformer", "Standing Hip Work",
             "foundation", 2, "2 Red + 1 Blue", 3.0,
             ["Round the spine, head between arms", "Push carriage back with legs",
              "Pull the carriage home with deep abs"],
             ["Core", "Flexibility", "Lower Body"], "elephant.png"),
    Exercise("ref_knee_stretches_round", "Knee Stretches – Round Back", "Reformer", "Kneeling Core",
             "foundation", 3, "2 Red", 2.5,
             ["Kneel on carriage, hands on bar", "Round the spine like an angry cat",
              "Push and pull with control"],
             ["Core", "Full Body"], "knee_stretches_round.png"),
    Exercise("ref_scooter", "Scooter", "Reformer", "Standing Hip Work",
             "foundation", 3, "1 Red + 1 Blue", 3.0,
             ["One foot on platform, one on carriage", "Press standing leg back",
              "Keep hips level and square"],
             ["Lower Body", "Balance", "Core"], "scooter.png"),
    Exercise("ref_mermaid", "Mermaid Stretch", "Reformer", "Lateral Flexion",
             "foundation", 2, "1 Red", 3.0,
             ["Sit sideways, hand on bar", "Stretch over into a side bend",
              "Breathe into the top ribs"],
             ["Flexibility", "Core"], "mermaid.png"),
    Exercise("ref_arm_circles_straps", "Arm Circles in Straps", "Reformer", "Arm Work",
             "foundation", 2, "1 Blue", 3.0,
             ["Lie supine, arms in straps", "Circle arms down and around",
              "Keep shoulders stable on the mat"],
             ["Upper Body", "Core"], "arm_circles_straps.png"),

    # --- Peak ---
    Exercise("ref_snake_twist", "Snake / Twist", "Reformer", "Plank / Full Body",
             "peak", 5, "1 Red + 1 Blue", 4.0,
             ["Side plank on the reformer", "Push out and twist under",
              "Control the return – no momentum"],
             ["Core", "Upper Body", "Full Body"], "snake_twist.png"),
    Exercise("ref_control_front", "Control Front", "Reformer", "Plank / Full Body",
             "peak", 5, "1 Red", 3.5,
             ["Stand on bar, hands on platform", "Push carriage out to plank",
              "Pull back with deep abdominal connection"],
             ["Core", "Upper Body", "Full Body"], "control_front.png"),
    Exercise("ref_long_back_stretch", "Long Back Stretch", "Reformer", "Arm Work",
             "peak", 4, "1 Red + 1 Blue", 3.0,
             ["Sit on carriage facing foot bar", "Hands on bar, lift and push out",
              "Tricep dip meets spine articulation"],
             ["Upper Body", "Core"], "long_back_stretch.png"),
    Exercise("ref_star", "Star", "Reformer", "Lateral Flexion",
             "peak", 5, "1 Red", 3.0,
             ["Side-lying on the box", "Top arm and leg reach long",
              "Balance and control are everything"],
             ["Core", "Balance", "Full Body"], "star.png"),
    Exercise("ref_arabesque", "Arabesque on Reformer", "Reformer", "Standing Hip Work",
             "peak", 4, "1 Red + 1 Blue", 3.0,
             ["Stand on carriage, one hand on bar", "Extend free leg behind",
              "Hinge from the hip with length"],
             ["Lower Body", "Balance", "Core"], "arabesque.png"),
    Exercise("ref_tendon_stretch", "Tendon Stretch", "Reformer", "Plank / Full Body",
             "peak", 5, "2 Red", 3.0,
             ["Stand on carriage, hands on bar", "Round down lifting hips high",
              "Push carriage back with feet, pull with abs"],
             ["Core", "Full Body"], "tendon_stretch.png"),
    Exercise("ref_semi_circle", "Semi-Circle", "Reformer", "Supine Hip Work",
             "peak", 4, "1 Red + 1 Blue", 4.0,
             ["Lie with shoulders on mat, feet on bar", "Articulate through bridge",
              "Circle the hips down-out-up-in"],
             ["Core", "Flexibility", "Lower Body"], "semi_circle.png"),

    # --- Cooldown ---
    Exercise("ref_running", "Running on Reformer", "Reformer", "Footwork",
             "cooldown", 1, "3 Red", 3.0,
             ["Alternate pressing heels under the bar", "Like jogging in place",
              "Find a smooth, even rhythm"],
             ["Lower Body", "Flexibility"], "running.png"),
    Exercise("ref_pelvic_lift", "Pelvic Lift / Calf Raises", "Reformer", "Footwork",
             "cooldown", 1, "3 Red", 2.0,
             ["Both heels under the bar", "Press up and lower with control",
              "Stretch the calves and Achilles"],
             ["Lower Body", "Flexibility"], "pelvic_lift.png"),
    Exercise("ref_chest_expansion_kneel", "Chest Expansion – Kneeling", "Reformer", "Arm Work",
             "cooldown", 2, "1 Red", 2.5,
             ["Kneel facing the straps", "Pull arms back and hold",
              "Open across the collarbones"],
             ["Upper Body", "Flexibility"], "chest_expansion_kneel.png"),
    Exercise("ref_hip_flexor_stretch", "Hip Flexor Stretch on Carriage", "Reformer", "Stretch",
             "cooldown", 1, "1 Blue", 3.0,
             ["One knee on carriage, other foot on platform", "Let the carriage glide back",
              "Sink into the front of the hip"],
             ["Flexibility", "Lower Body"], "hip_flexor_stretch.png"),
    Exercise("ref_mermaid_cooldown", "Mermaid Cooldown", "Reformer", "Lateral Flexion",
             "cooldown", 1, "1 Blue", 2.5,
             ["Gentle side stretch", "Breathe deeply into the ribs",
              "Let gravity do the work"],
             ["Flexibility"], "mermaid_cooldown.png"),

    # ═══════════════════════════════════════════
    # MAT EXERCISES
    # ═══════════════════════════════════════════

    # --- Warmup ---
    Exercise("mat_breathing", "Pilates Breathing", "Mat", "Breathing",
             "warmup", 1, "N/A", 2.0,
             ["Lateral thoracic breathing", "Expand ribs sideways on inhale",
              "Knit ribs together on exhale"],
             ["Core", "Flexibility"], "mat_breathing.png"),
    Exercise("mat_pelvic_curl", "Pelvic Curl", "Mat", "Supine Hip Work",
             "warmup", 1, "N/A", 3.0,
             ["Imprint, then roll up bone by bone", "Squeeze glutes at the top",
              "Roll down like laying a pearl necklace"],
             ["Core", "Lower Body", "Flexibility"], "pelvic_curl.png"),
    Exercise("mat_spine_twist_supine", "Supine Spine Twist", "Mat", "Supine Abdominals",
             "warmup", 1, "N/A", 2.5,
             ["Knees together, drop to one side", "Keep both shoulders on the mat",
              "Use abs to bring knees back to center"],
             ["Core", "Flexibility"], "spine_twist_supine.png"),
    Exercise("mat_cat_cow", "Cat-Cow Stretch", "Mat", "Kneeling Core",
             "warmup", 1, "N/A", 2.0,
             ["Hands under shoulders, knees under hips", "Round up into cat, then arch into cow",
              "Move with your breath"],
             ["Flexibility", "Core"], "cat_cow.png"),

    # --- Foundation ---
    Exercise("mat_hundred", "The Hundred", "Mat", "Supine Abdominals",
             "foundation", 3, "N/A", 3.0,
             ["Curl up, legs at tabletop or extended", "Pump arms vigorously",
              "100 counts: inhale 5, exhale 5"],
             ["Core"], "mat_hundred.png"),
    Exercise("mat_roll_up", "Roll Up", "Mat", "Supine Abdominals",
             "foundation", 3, "N/A", 3.0,
             ["Arms overhead to start", "Peel up one vertebra at a time",
              "Reach past toes, then roll back down"],
             ["Core", "Flexibility"], "mat_roll_up.png"),
    Exercise("mat_single_leg_circle", "Single Leg Circles", "Mat", "Supine Hip Work",
             "foundation", 2, "N/A", 3.0,
             ["One leg to ceiling, other long on mat", "Circle the leg — keep pelvis still",
              "5 each direction"],
             ["Core", "Lower Body", "Flexibility"], "single_leg_circle.png"),
    Exercise("mat_single_leg_stretch", "Single Leg Stretch", "Mat", "Supine Abdominals",
             "foundation", 3, "N/A", 3.0,
             ["Curl up, one knee in", "Switch legs with control",
              "Elbows wide, gaze at navel"],
             ["Core"], "single_leg_stretch.png"),
    Exercise("mat_double_leg_stretch", "Double Leg Stretch", "Mat", "Supine Abdominals",
             "foundation", 3, "N/A", 3.0,
             ["Everything reaches long", "Circle arms back and hug knees in",
              "Maintain the curl throughout"],
             ["Core", "Full Body"], "double_leg_stretch.png"),
    Exercise("mat_swimming", "Swimming", "Mat", "Prone Back Extension",
             "foundation", 3, "N/A", 3.0,
             ["Lie prone, arms and legs lifted", "Flutter opposite arm/leg",
              "Keep length — don't crunch the low back"],
             ["Core", "Upper Body", "Full Body"], "mat_swimming.png"),
    Exercise("mat_side_kick_series", "Side Kick Series", "Mat", "Side-Lying Hip Work",
             "foundation", 2, "N/A", 4.0,
             ["Lie on side, legs slightly forward", "Front/back kicks with control",
              "Up/down lifts, circles"],
             ["Lower Body", "Core", "Balance"], "side_kick_series.png"),
    Exercise("mat_spine_stretch", "Spine Stretch Forward", "Mat", "Seated Flexion",
             "foundation", 2, "N/A", 2.5,
             ["Sit tall, legs wide, arms forward", "Round forward from the top of the head",
              "Stack back up to sitting"],
             ["Core", "Flexibility"], "spine_stretch.png"),

    # --- Peak ---
    Exercise("mat_teaser", "Teaser", "Mat", "Supine Abdominals",
             "peak", 5, "N/A", 3.0,
             ["Roll up to a V-sit", "Arms reach past toes",
              "Roll down with control — the harder part"],
             ["Core", "Full Body"], "mat_teaser.png"),
    Exercise("mat_boomerang", "Boomerang", "Mat", "Supine Abdominals",
             "peak", 5, "N/A", 3.5,
             ["Roll over, switch legs, roll up to teaser",
              "Clasp hands behind back", "Lower with control"],
             ["Core", "Flexibility", "Full Body"], "mat_boomerang.png"),
    Exercise("mat_control_balance", "Control Balance", "Mat", "Supine Abdominals",
             "peak", 5, "N/A", 3.0,
             ["From rollover, split legs", "One leg to ceiling, hold ankle",
              "Switch with control"],
             ["Core", "Flexibility", "Balance"], "control_balance.png"),
    Exercise("mat_push_up", "Pilates Push-Up", "Mat", "Plank / Full Body",
             "peak", 4, "N/A", 3.0,
             ["Roll down to plank", "Three push-ups with elbows tight",
              "Walk hands back and roll up"],
             ["Upper Body", "Core", "Full Body"], "mat_push_up.png"),
    Exercise("mat_jackknife", "Jackknife", "Mat", "Supine Abdominals",
             "peak", 5, "N/A", 3.0,
             ["Roll over then shoot legs to ceiling", "Body in one diagonal line",
              "Roll down with control"],
             ["Core", "Full Body"], "mat_jackknife.png"),

    # --- Cooldown ---
    Exercise("mat_seal", "Seal", "Mat", "Seated Flexion",
             "cooldown", 1, "N/A", 2.5,
             ["Balance on sit bones, hold ankles", "Roll back and clap feet 3 times",
              "Roll up and clap 3 times — playful!"],
             ["Core", "Flexibility"], "mat_seal.png"),
    Exercise("mat_child_pose", "Rest Position / Child's Pose", "Mat", "Stretch",
             "cooldown", 1, "N/A", 2.0,
             ["Knees wide, toes together", "Reach arms forward and breathe",
              "Let the spine release completely"],
             ["Flexibility"], "mat_child_pose.png"),
    Exercise("mat_roll_down", "Standing Roll Down", "Mat", "Standing Stretch",
             "cooldown", 1, "N/A", 2.0,
             ["Chin to chest, roll down vertebra by vertebra",
              "Hang at the bottom, breathe",
              "Rebuild the spine from the base up"],
             ["Flexibility", "Core"], "mat_roll_down.png"),
    Exercise("mat_hip_circles", "Hip Circles Stretch", "Mat", "Supine Hip Work",
             "cooldown", 1, "N/A", 2.5,
             ["Hug one knee to chest", "Circle the hip gently",
              "Release and switch sides"],
             ["Flexibility", "Lower Body"], "mat_hip_circles.png"),

    # ═══════════════════════════════════════════
    # CHAIR EXERCISES
    # ═══════════════════════════════════════════

    Exercise("chair_footwork_seated", "Footwork – Seated", "Chair", "Footwork",
             "warmup", 2, "1 High + 1 Low", 3.0,
             ["Sit tall on the chair", "Press pedal down with control",
              "Resist on the way up"],
             ["Lower Body", "Core"], "chair_footwork_seated.png"),
    Exercise("chair_pump_one_leg", "Single Leg Pump", "Chair", "Standing Hip Work",
             "foundation", 3, "1 High", 3.0,
             ["Stand facing the chair", "One foot presses pedal",
              "Square hips, don't lean"],
             ["Lower Body", "Balance", "Core"], "chair_pump_one_leg.png"),
    Exercise("chair_swan", "Swan on Chair", "Chair", "Prone Back Extension",
             "foundation", 3, "1 High + 1 Low", 3.5,
             ["Lie prone over the chair seat", "Hands press pedal down",
              "Lift chest using back extensors"],
             ["Upper Body", "Core"], "chair_swan.png"),
    Exercise("chair_pike", "Pike / Pull-Up", "Chair", "Plank / Full Body",
             "peak", 5, "1 High", 3.0,
             ["Stand on pedal, hands on seat", "Pike up lifting hips to ceiling",
              "Control the pedal's return"],
             ["Core", "Upper Body", "Full Body"], "chair_pike.png"),
    Exercise("chair_side_body_twist", "Side Body Twist", "Chair", "Lateral Flexion",
             "peak", 4, "1 Low", 3.0,
             ["Sit sideways on the chair", "Press pedal while rotating",
              "Feel the oblique connection"],
             ["Core", "Flexibility"], "chair_side_body_twist.png"),
    Exercise("chair_hamstring_press", "Hamstring Press Back", "Chair", "Standing Hip Work",
             "foundation", 3, "1 High", 3.0,
             ["Stand facing away from chair", "Press pedal down behind you",
              "Keep standing leg strong and tall"],
             ["Lower Body", "Balance"], "chair_hamstring_press.png"),
    Exercise("chair_stretch_forward", "Forward Stretch on Chair", "Chair", "Stretch",
             "cooldown", 1, "1 Low", 2.0,
             ["Sit on the chair, feet on pedal", "Round forward pressing pedal gently",
              "Let gravity lengthen the spine"],
             ["Flexibility"], "chair_stretch_forward.png"),

    # ═══════════════════════════════════════════
    # CADILLAC / TOWER EXERCISES
    # ═══════════════════════════════════════════

    Exercise("cad_roll_down_bar", "Roll Down with Push-Through Bar", "Cadillac", "Supine Abdominals",
             "warmup", 2, "Top Spring", 3.0,
             ["Hold the bar, curl chin to chest", "Articulate down one bone at a time",
              "The spring assists — use it wisely"],
             ["Core", "Flexibility"], "cad_roll_down_bar.png"),
    Exercise("cad_leg_springs_series", "Leg Springs Series", "Cadillac", "Supine Hip Work",
             "foundation", 3, "Leg Springs", 5.0,
             ["Supine with legs in springs", "Circles, frogs, walking",
              "Keep pelvis stable throughout"],
             ["Lower Body", "Core", "Flexibility"], "cad_leg_springs.png"),
    Exercise("cad_monkey", "Monkey", "Cadillac", "Supine Hip Work",
             "foundation", 2, "Bottom Spring", 3.0,
             ["Feet on push-through bar, knees bent", "Press bar to ceiling",
              "Articulate spine up into a bridge"],
             ["Core", "Lower Body", "Flexibility"], "cad_monkey.png"),
    Exercise("cad_breathing_push_thru", "Breathing with Push-Through Bar", "Cadillac", "Seated Flexion",
             "foundation", 2, "Top Spring", 3.0,
             ["Sit tall facing the bar", "Push through and round forward",
              "Stack spine to return"],
             ["Core", "Flexibility"], "cad_breathing_push_thru.png"),
    Exercise("cad_cat_on_cadillac", "Cat Stretch", "Cadillac", "Kneeling Core",
             "peak", 4, "Top Spring", 3.5,
             ["Kneel facing the tower", "Hold bar overhead, round and push through",
              "Deep flexion against the spring"],
             ["Core", "Flexibility", "Full Body"], "cad_cat_stretch.png"),
    Exercise("cad_tower", "Tower", "Cadillac", "Supine Hip Work",
             "peak", 4, "Leg Springs", 4.0,
             ["Feet in push-through bar", "Roll over then press legs to ceiling",
              "Articulate down one vertebra at a time"],
             ["Core", "Flexibility", "Full Body"], "cad_tower.png"),
    Exercise("cad_hanging_back", "Hanging Back", "Cadillac", "Prone Back Extension",
             "peak", 5, "Top Spring", 3.0,
             ["Hold fuzzy loops from the top", "Lean back into an arch",
              "Trust the springs, open the chest"],
             ["Upper Body", "Flexibility", "Core"], "cad_hanging_back.png"),
    Exercise("cad_arm_springs", "Arm Springs – Supine", "Cadillac", "Arm Work",
             "cooldown", 2, "Arm Springs", 3.0,
             ["Lie supine holding arm springs", "Press arms to hips and lift back",
              "Control the spring's return"],
             ["Upper Body", "Core"], "cad_arm_springs.png"),
]


# ─────────────────────────────────────────────
# Generator Engine
# ─────────────────────────────────────────────

# Phase proportions for the bell-curve class structure
PHASE_RATIOS = {
    "warmup":     0.20,
    "foundation": 0.30,
    "peak":       0.30,
    "cooldown":   0.20,
}

PHASE_ORDER = ["warmup", "foundation", "peak", "cooldown"]

THEMES = ["Core", "Flexibility", "Lower Body", "Upper Body", "Full Body", "Balance"]
APPARATUS_OPTIONS = ["Reformer", "Mat", "Chair", "Cadillac", "Mixed"]
ENERGY_LEVELS = {
    "Gentle (1-2)": (1, 2),
    "Moderate (2-3)": (2, 3),
    "Challenging (3-4)": (3, 4),
    "Intense (4-5)": (4, 5),
}


def get_exercises_for_apparatus(apparatus: str) -> list[Exercise]:
    """Filter exercises by apparatus. 'Mixed' returns everything."""
    if apparatus == "Mixed":
        return EXERCISE_DB[:]
    return [e for e in EXERCISE_DB if e.apparatus == apparatus]


def generate_workout(
    duration_minutes: int,
    apparatus: str,
    theme: str,
    energy_label: str,
) -> list[dict]:
    """
    Build a workout using the bell-curve class structure.
    Returns a list of exercise dicts with an added 'phase_label' key.
    """
    energy_min, energy_max = ENERGY_LEVELS.get(energy_label, (1, 5))
    pool = get_exercises_for_apparatus(apparatus)

    # Filter by theme (allow exercises that list this theme)
    if theme != "Full Body":
        themed = [e for e in pool if theme in e.themes]
        # Keep at least some from each phase even if theme is narrow
        for phase in PHASE_ORDER:
            phase_themed = [e for e in themed if e.phase == phase]
            if len(phase_themed) < 2:
                # backfill with any exercise from that phase
                extras = [e for e in pool if e.phase == phase and e not in themed]
                themed.extend(extras[:3])
        pool = themed if themed else pool

    # Calculate time budget per phase
    time_budget = {}
    for phase, ratio in PHASE_RATIOS.items():
        time_budget[phase] = duration_minutes * ratio

    workout = []
    used_slugs = set()

    for phase in PHASE_ORDER:
        budget = time_budget[phase]
        candidates = [e for e in pool if e.phase == phase and e.slug not in used_slugs]

        # Soft-filter by energy for foundation/peak phases
        if phase in ("foundation", "peak"):
            energy_filtered = [e for e in candidates if energy_min <= e.energy <= energy_max]
            if len(energy_filtered) >= 2:
                candidates = energy_filtered

        random.shuffle(candidates)
        phase_time = 0.0

        for ex in candidates:
            if phase_time + ex.duration_min <= budget + 1.0:  # allow slight overflow
                entry = ex.to_dict()
                entry["phase_label"] = phase.capitalize()
                workout.append(entry)
                used_slugs.add(ex.slug)
                phase_time += ex.duration_min

    return workout


def smart_swap(workout: list[dict], index: int) -> Optional[dict]:
    """
    Swap exercise at `index` with another from the same category + phase.
    Returns the new exercise dict, or None if no swap is available.
    """
    current = workout[index]
    used_slugs = {e["slug"] for e in workout}

    candidates = [
        e for e in EXERCISE_DB
        if e.category == current["category"]
        and e.phase == current["phase"].lower()
        and e.slug not in used_slugs
    ]

    # Broaden: same phase, similar energy if category match fails
    if not candidates:
        candidates = [
            e for e in EXERCISE_DB
            if e.phase == current["phase"].lower()
            and e.apparatus == current["apparatus"]
            and e.slug not in used_slugs
            and abs(e.energy - current["energy"]) <= 1
        ]

    if not candidates:
        return None

    replacement = random.choice(candidates)
    entry = replacement.to_dict()
    entry["phase_label"] = current["phase_label"]
    return entry


def workout_to_json(workout: list[dict]) -> str:
    """Serialize a workout for Google Sheets storage."""
    return json.dumps(workout, default=str)


def json_to_workout(json_str: str) -> list[dict]:
    """Deserialize a workout from Google Sheets."""
    return json.loads(json_str)
