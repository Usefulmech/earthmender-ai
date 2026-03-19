"""
EarthMender AI — Phase 5: Education Module
============================================
Three sub-tabs inside the Learn tab:
  1. Waste Sorting Guide
  2. Recycling Tips
  3. Quiz

Final 5-class system:
    plastic_bottle | water_sachet | polythene_bag | disposable | waste_container
"""

import streamlit as st
import random
from phase5_education.quiz_data import QUIZ_QUESTIONS


# ─── SORTING GUIDE DATA ───────────────────────────────────────────────────────
SORTING_GUIDE = [
    {
        "category": "♻️ Recyclable Waste",
        "color":    "#1a7a4a",
        "bg":       "#e8f5e9",
        "items": [
            "Plastic drink bottles — Eva, Pepsi, La Casera, Voltic, Ragolis, Coke PET",
            "Water sachets — individual sachets and outer nylon bundles (keep dry)",
            "Polythene bags — Shoprite bags, black bags, Milo/biscuit nylon sachets, bread nylons",
            "Clean, dry disposables — uncontaminated plastic cups and containers (rinse first)",
            "Cardboard and paper boxes (must be dry and flat)",
            "Glass bottles and jars (rinsed clean)",
            "Aluminium cans, tins, and scrap metal",
        ],
        "where":  "Wecyclers, RecyclePoints kiosks (many filling stations), local scrap dealers",
        "tip":    "Clean and dry is the rule. Wet or food-contaminated items "
                  "are rejected at sorting facilities.",
    },
    {
        "category": "🍃 Organic / Compostable Waste",
        "color":    "#558b2f",
        "bg":       "#f1f8e9",
        "items": [
            "Food scraps and plate leftovers",
            "Fruit and vegetable peels",
            "Eggshells and nutshells",
            "Garden leaves and grass clippings",
            "Used tea bags and coffee grounds",
        ],
        "where": "Home compost pit, backyard composting, or organic waste bin",
        "tip":   "Composting organic waste at home reduces your household waste by up to 30%.",
    },
    {
        "category": "🗑️ General Waste",
        "color":    "#757575",
        "bg":       "#f5f5f5",
        "items": [
            "Black polythene bags — optical sorters at recycling facilities cannot process them",
            "Food-contaminated disposables — takeaway packs with sauce, used plastic spoons",
            "Styrofoam / polystyrene — no Nigerian recycling facility accepts this yet",
            "Soiled paper, tissue, and napkins",
            "Multi-layer packaging (crisp bags, Tetra Pak juice boxes)",
        ],
        "where": "LAWMA bins (Lagos), AEPB (Abuja), or your PSP collector",
        "tip":   "Keep general waste bagged and sealed. Loose waste blocks gutters "
                 "and causes flooding during rainy season.",
    },
    {
        "category": "⚠️ Hazardous / E-Waste",
        "color":    "#e53935",
        "bg":       "#ffebee",
        "items": [
            "Old phones, batteries, laptops, and chargers",
            "Broken bulbs and fluorescent tubes",
            "Paint cans and chemical containers",
            "Used engine oil jerry cans",
            "Medical waste, syringes, and sharps",
            "Large waste containers and drums that held chemicals",
        ],
        "where": "Hinckley Nigeria e-waste collection, manufacturer take-back schemes",
        "tip":   "NEVER dump e-waste or chemical containers in gutters or open land. "
                 "They leach toxins into groundwater for decades.",
    },
]

# ─── RECYCLING TIPS DATA ──────────────────────────────────────────────────────
RECYCLING_TIPS = [
    {
        "material":     "🍶 Plastic Bottles (Eva, Pepsi, Voltic etc.)",
        "color":        "#2e7d32",
        "tips": [
            "Rinse before recycling — food/drink residue contaminates entire batches.",
            "Remove the cap (different plastic type) and recycle separately if possible.",
            "Crush flat to save storage space before taking to a recycler.",
            "Check the number: #1 PET and #2 HDPE are the most accepted in Nigeria.",
            "All drink bottles — water, soft drinks, juice, energy drinks — recycle the same way.",
            "RecyclePoints kiosks at filling stations pay cash or airtime per kg of bottles.",
        ],
        "did_you_know": "Recycling one PET bottle saves enough energy to power a mobile "
                        "phone for 25 minutes.",
    },
    {
        "material":     "💧 Water Sachets (Pure Water Nylons)",
        "color":        "#1976d2",
        "tips": [
            "Collect 20+ sachets before going to a recycler — payment is per kg.",
            "Keep sachets dry and clean — wet or dirty ones are rejected.",
            "Cut open and shake out remaining water before storing.",
            "RecyclePoints kiosks pay cash or MTN/Airtel airtime for sachet bags.",
            "Outer nylon bundles that sachets come packed in are also recyclable.",
            "Set up a collection bag at home, school, or office — replace when full.",
        ],
        "did_you_know": "Nigeria consumes an estimated 60 million water sachets every single day.",
    },
    {
        "material":     "🛍️ Polythene Bags (All Nylons)",
        "color":        "#ff6f00",
        "tips": [
            "ALL nylons go together — Shoprite bags, black bags, branded pouches, bread nylons.",
            "Never burn polythene — the fumes are highly toxic and damage lungs.",
            "Collect clean, dry nylons in a separate bag; wet nylons are rejected.",
            "Wecyclers runs kerbside pickup in Lagos — register your household for free.",
            "Milo sachets, biscuit wrappers, and snack pouches are all polythene — same pile.",
            "Black polythene bags are the hardest to recycle — minimise their use.",
        ],
        "did_you_know": "A single polythene bag takes up to 1,000 years to break down in a landfill.",
    },
    {
        "material":     "🥤 Disposables (Cups, Takeaway Packs, Cutlery)",
        "color":        "#7b1fa2",
        "tips": [
            "Rinse cups and takeaway containers before disposal — food contamination ruins batches.",
            "Uncontaminated disposables can be taken to your PSP/LAWMA collector.",
            "Avoid single-use plastic cutlery — carry a reusable spoon if you eat out often.",
            "Styrofoam takeaway packs cannot be recycled in Nigeria — push restaurants to switch.",
            "Hard plastic cups (#5 PP) are more recyclable than styrofoam — check the number.",
            "If you run a business, switching to biodegradable packaging reduces your waste footprint.",
        ],
        "did_you_know": "A single styrofoam cup takes over 500 years to break down "
                        "and releases harmful chemicals as it does.",
    },
    {
        "material":     "🛢️ Waste Containers (Dustbins, Jerry Cans, Drums)",
        "color":        "#4e342e",
        "tips": [
            "Seal containers to prevent leaching into nearby soil and groundwater.",
            "Report overflowing bins and drums via EarthMender AI — operators get notified.",
            "Never burn or bury containers that held chemicals or engine oil.",
            "Large metal jerry cans and drums have scrap value — contact a local Ọlọbẹ dealer.",
            "Plastic jerry cans (#2 HDPE) can often be cleaned, reused, or recycled.",
            "Community bins should be emptied before they overflow to prevent spread.",
        ],
        "did_you_know": "One improperly disposed chemical drum can contaminate thousands "
                        "of litres of groundwater affecting the entire neighbourhood.",
    },
]


# ─── RENDER: SORTING GUIDE ────────────────────────────────────────────────────
def render_sorting_guide():
    st.markdown("### 🗂️ Waste Sorting Guide")
    st.caption("Know exactly where your waste belongs — Nigerian context throughout.")
    st.write("")

    for cat in SORTING_GUIDE:
        with st.expander(cat["category"], expanded=False):
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("**What goes here:**")
                for item in cat["items"]:
                    st.markdown(f"- {item}")
            with col2:
                st.markdown("**Where to take it:**")
                st.info(cat["where"])
                st.markdown(
                    f"<div style='background:#fffde7;padding:8px;"
                    f"border-radius:6px;font-size:12px;margin-top:6px;'>"
                    f"💡 {cat['tip']}</div>",
                    unsafe_allow_html=True,
                )


# ─── RENDER: RECYCLING TIPS ───────────────────────────────────────────────────
def render_recycling_tips():
    st.markdown("### 🔄 Recycling Tips by Waste Type")
    st.caption("Practical disposal advice for every class in the EarthMender AI system.")
    st.write("")

    for tip in RECYCLING_TIPS:
        st.markdown(
            f"<div style='border-left:4px solid {tip['color']};"
            f"padding:4px 12px;margin-bottom:6px;'>",
            unsafe_allow_html=True,
        )
        st.markdown(f"#### {tip['material']}")
        for t in tip["tips"]:
            st.markdown(f"✅ {t}")
        st.markdown(
            f"<div style='background:#fff8e1;padding:8px;border-radius:6px;"
            f"font-size:13px;margin-top:6px;'>"
            f"💡 <b>Did you know?</b> {tip['did_you_know']}</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        st.write("")


# ─── RENDER: QUIZ ─────────────────────────────────────────────────────────────
def render_quiz():
    st.markdown("### 🧠 Plastic Waste Knowledge Quiz")
    st.caption("True or False — test what you know about plastic waste in Nigeria.")
    st.write("")

    for key, default in [
        ("quiz_started",   False),
        ("quiz_questions", []),
        ("quiz_index",     0),
        ("quiz_score",     0),
        ("quiz_done",      False),
        ("quiz_answered",  False),
        ("quiz_feedback",  ""),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    # START SCREEN
    if not st.session_state.quiz_started:
        st.markdown("""
        <div style='background:#e8f5e9;padding:24px;border-radius:12px;text-align:center;'>
            <h3 style='color:#1a7a4a;margin-top:0;'>♻️ EarthMender AI Quiz</h3>
            <p style='color:#555;'>12 True/False questions on plastic waste,
            recycling, and the environment in Nigeria.</p>
            <p><b>Can you score 10 or more? 🏆</b></p>
        </div>
        """, unsafe_allow_html=True)
        st.write("")
        if st.button("🚀 Start Quiz", type="primary", use_container_width=True):
            st.session_state.quiz_started   = True
            st.session_state.quiz_questions = random.sample(
                QUIZ_QUESTIONS, len(QUIZ_QUESTIONS))
            st.session_state.quiz_index     = 0
            st.session_state.quiz_score     = 0
            st.session_state.quiz_done      = False
            st.session_state.quiz_answered  = False
            st.rerun()
        return

    # RESULTS SCREEN
    if st.session_state.quiz_done:
        score = st.session_state.quiz_score
        total = len(st.session_state.quiz_questions)
        pct   = int((score / total) * 100)

        if pct >= 83:
            grade, emoji, color = "Excellent!", "🏆", "#1a7a4a"
            msg = "You're an EarthMender champion! Share this app with your community."
        elif pct >= 60:
            grade, emoji, color = "Good Job!", "👍", "#ff9800"
            msg = "Solid knowledge! Review the Recycling Tips tab to go further."
        else:
            grade, emoji, color = "Keep Learning!", "📚", "#e53935"
            msg = "Check the Sorting Guide and Recycling Tips, then try again!"

        st.markdown(f"""
        <div style='background:{color}22;border:2px solid {color};
             padding:28px;border-radius:12px;text-align:center;'>
            <div style='font-size:52px;'>{emoji}</div>
            <h2 style='color:{color};margin:8px 0;'>{grade}</h2>
            <h3 style='margin:4px 0;'>You scored {score} / {total} ({pct}%)</h3>
            <p style='color:#555;margin-top:12px;'>{msg}</p>
        </div>
        """, unsafe_allow_html=True)
        st.write("")
        if st.button("🔁 Retake Quiz", use_container_width=True):
            st.session_state.quiz_started   = True
            st.session_state.quiz_questions = random.sample(
                QUIZ_QUESTIONS, len(QUIZ_QUESTIONS))
            st.session_state.quiz_index     = 0
            st.session_state.quiz_score     = 0
            st.session_state.quiz_done      = False
            st.session_state.quiz_answered  = False
            st.rerun()
        return

    # QUESTION SCREEN
    questions = st.session_state.quiz_questions
    idx       = st.session_state.quiz_index
    q         = questions[idx]
    total     = len(questions)

    st.progress(idx / total, text=f"Question {idx + 1} of {total}")
    st.write("")
    st.markdown(f"""
    <div style='background:#f9f9f9;border:1px solid #ddd;
         padding:20px;border-radius:10px;font-size:16px;line-height:1.7;'>
        <b>Q{idx + 1}.</b> {q['question']}
    </div>
    """, unsafe_allow_html=True)
    st.write("")

    if not st.session_state.quiz_answered:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅  TRUE",  use_container_width=True, type="primary"):
                _check_answer(True, q)
        with col2:
            if st.button("❌  FALSE", use_container_width=True):
                _check_answer(False, q)
    else:
        st.markdown(st.session_state.quiz_feedback, unsafe_allow_html=True)
        st.write("")
        label = "➡️ Next Question" if idx + 1 < total else "🏁 See My Results"
        if st.button(label, type="primary", use_container_width=True):
            st.session_state.quiz_index   += 1
            st.session_state.quiz_answered = False
            st.session_state.quiz_feedback = ""
            if st.session_state.quiz_index >= total:
                st.session_state.quiz_done = True
            st.rerun()

    st.write("")
    answered = idx + (1 if st.session_state.quiz_answered else 0)
    st.caption(f"Score so far: {st.session_state.quiz_score} / {answered}")


def _check_answer(user_answer: bool, question: dict):
    correct = question["answer"]
    if user_answer == correct:
        st.session_state.quiz_score += 1
        fb = (f"<div style='background:#e8f5e9;border-left:4px solid #1a7a4a;"
              f"padding:14px;border-radius:6px;'>"
              f"✅ <b>Correct!</b><br>{question['explanation']}</div>")
    else:
        correct_text = "TRUE" if correct else "FALSE"
        fb = (f"<div style='background:#ffebee;border-left:4px solid #e53935;"
              f"padding:14px;border-radius:6px;'>"
              f"❌ <b>Incorrect.</b> The answer is <b>{correct_text}</b>.<br>"
              f"{question['explanation']}</div>")
    st.session_state.quiz_answered = True
    st.session_state.quiz_feedback = fb
    st.rerun()


# ─── MASTER RENDER ────────────────────────────────────────────────────────────
def render_education_tab():
    sub1, sub2, sub3 = st.tabs([
        "🗂️ Sorting Guide",
        "🔄 Recycling Tips",
        "🧠 Quiz",
    ])
    with sub1:
        render_sorting_guide()
    with sub2:
        render_recycling_tips()
    with sub3:
        render_quiz()
