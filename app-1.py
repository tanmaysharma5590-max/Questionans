import streamlit as st
import json
import random
import time
from pathlib import Path

st.set_page_config(page_title="Exam Prep - Aptitude Mock Test", page_icon="📊", layout="centered")

DATA_PATH = Path(__file__).parent / "questions.json"

@st.cache_data
def load_questions():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

ALL_QUESTIONS = load_questions()
SECTIONS = sorted(set(q["section"] for q in ALL_QUESTIONS), key=lambda s: s)

# ---------------- Session State Setup ----------------
def init_state():
    defaults = {
        "stage": "setup",          # setup -> test -> result
        "quiz_questions": [],
        "current_idx": 0,
        "answers": {},              # qid -> selected option index (or None)
        "start_time": None,
        "duration_min": 40,
        "negative_marking": True,
        "submitted": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ---------------- Helper functions ----------------
def start_quiz(num_q, sections, shuffle, duration_min, negative_marking):
    pool = [q for q in ALL_QUESTIONS if q["section"] in sections]
    if shuffle:
        random.shuffle(pool)
    else:
        pool = sorted(pool, key=lambda q: q["id"])
    selected = pool[:num_q]
    st.session_state.quiz_questions = selected
    st.session_state.current_idx = 0
    st.session_state.answers = {q["id"]: None for q in selected}
    st.session_state.start_time = time.time()
    st.session_state.duration_min = duration_min
    st.session_state.negative_marking = negative_marking
    st.session_state.stage = "test"
    st.session_state.submitted = False

def time_left_seconds():
    elapsed = time.time() - st.session_state.start_time
    total = st.session_state.duration_min * 60
    return max(0, total - elapsed)

def compute_score():
    correct = 0
    wrong = 0
    unattempted = 0
    for q in st.session_state.quiz_questions:
        sel = st.session_state.answers.get(q["id"])
        if sel is None:
            unattempted += 1
        elif sel == q["correct_index"]:
            correct += 1
        else:
            wrong += 1
    if st.session_state.negative_marking:
        score = correct * 1 - wrong * 0.25
    else:
        score = correct * 1
    total = len(st.session_state.quiz_questions)
    return {
        "correct": correct,
        "wrong": wrong,
        "unattempted": unattempted,
        "score": round(score, 2),
        "total": total,
        "max_score": total,
        "accuracy": round((correct / (correct + wrong) * 100), 1) if (correct + wrong) > 0 else 0.0,
    }

def reset_all():
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    init_state()

# ==================================================
# STAGE 1: SETUP
# ==================================================
if st.session_state.stage == "setup":
    st.title("📊 Exam Prep — Aptitude Mock Test")
    st.caption("Bank PO / IT Placement / Data Science round practice")

    st.markdown(
        "Apni settings choose karo aur test start karo — real exam jaisa timer aur "
        "negative marking ke saath."
    )

    with st.form("setup_form"):
        st.subheader("Test Settings")

        sections_selected = st.multiselect(
            "Sections include karo:",
            options=SECTIONS,
            default=SECTIONS,
        )

        max_available = len(
            [q for q in ALL_QUESTIONS if q["section"] in sections_selected]
        ) if sections_selected else 0

        num_q = st.slider(
            "Kitne questions chahiye is attempt mein?",
            min_value=5,
            max_value=max(5, max_available),
            value=min(40, max_available) if max_available else 5,
            step=5,
        )

        duration_min = st.slider(
            "Time limit (minutes):",
            min_value=5, max_value=120, value=40, step=5,
        )

        shuffle = st.checkbox("Questions ko shuffle karo (random order)", value=True)
        negative_marking = st.checkbox(
            "Negative marking on (+1 correct, −0.25 wrong) — real test jaisa", value=True
        )

        submitted = st.form_submit_button("🚀 Start Test", use_container_width=True)

        if submitted:
            if not sections_selected:
                st.error("Kam se kam ek section select karo.")
            else:
                start_quiz(num_q, sections_selected, shuffle, duration_min, negative_marking)
                st.rerun()

    st.divider()
    st.markdown(f"**Total questions available in bank:** {len(ALL_QUESTIONS)}")
    with st.expander("Sections breakdown"):
        for sec in SECTIONS:
            cnt = len([q for q in ALL_QUESTIONS if q["section"] == sec])
            st.write(f"- {sec}: {cnt} questions")

# ==================================================
# STAGE 2: TEST
# ==================================================
elif st.session_state.stage == "test":
    questions = st.session_state.quiz_questions
    total = len(questions)
    idx = st.session_state.current_idx
    q = questions[idx]

    # Auto-submit if time is up
    remaining = time_left_seconds()
    if remaining <= 0 and not st.session_state.submitted:
        st.session_state.submitted = True
        st.session_state.stage = "result"
        st.rerun()

    # Top bar: progress + timer
    col1, col2 = st.columns([3, 1])
    with col1:
        st.progress((idx + 1) / total, text=f"Question {idx+1} of {total}")
    with col2:
        mins, secs = divmod(int(remaining), 60)
        color = "red" if remaining < 60 else "inherit"
        st.markdown(
            f"<div style='text-align:right; font-size:20px; font-weight:bold; color:{color};'>"
            f"⏱ {mins:02d}:{secs:02d}</div>",
            unsafe_allow_html=True,
        )

    st.caption(f"{q['section']} — {q.get('subsection','')}")
    st.markdown(f"### Q{idx+1}. {q['question']}")

    labels = ["A", "B", "C", "D"]
    option_display = [f"({labels[i]}) {opt}" for i, opt in enumerate(q["options"])]

    current_answer = st.session_state.answers.get(q["id"])
    default_idx = current_answer if current_answer is not None else None

    selected = st.radio(
        "Apna answer choose karo:",
        options=list(range(len(option_display))),
        format_func=lambda i: option_display[i],
        index=default_idx,
        key=f"radio_{q['id']}",
    )
    st.session_state.answers[q["id"]] = selected

    st.divider()

    nav1, nav2, nav3, nav4 = st.columns(4)
    with nav1:
        if st.button("⬅️ Previous", use_container_width=True, disabled=(idx == 0)):
            st.session_state.current_idx = max(0, idx - 1)
            st.rerun()
    with nav2:
        if st.button("Clear Answer", use_container_width=True):
            st.session_state.answers[q["id"]] = None
            st.rerun()
    with nav3:
        if st.button("Next ➡️", use_container_width=True, disabled=(idx == total - 1)):
            st.session_state.current_idx = min(total - 1, idx + 1)
            st.rerun()
    with nav4:
        if st.button("✅ Submit Test", use_container_width=True, type="primary"):
            st.session_state.submitted = True
            st.session_state.stage = "result"
            st.rerun()

    # Question palette / jump navigation
    with st.expander("📋 Question Palette (jump to any question)"):
        cols = st.columns(10)
        for i, qq in enumerate(questions):
            answered = st.session_state.answers.get(qq["id"]) is not None
            label = f"{i+1}"
            btn_type = "primary" if i == idx else "secondary"
            with cols[i % 10]:
                if st.button(label, key=f"jump_{qq['id']}", type=btn_type):
                    st.session_state.current_idx = i
                    st.rerun()
        st.caption("🔵 Highlighted = current question. Baaki grey = answered ya unanswered dono same "
                   "dikhte hain, palette sirf navigation ke liye hai.")

# ==================================================
# STAGE 3: RESULT
# ==================================================
elif st.session_state.stage == "result":
    result = compute_score()

    st.title("🎯 Test Result")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Score", f"{result['score']} / {result['max_score']}")
    c2.metric("Correct", result["correct"])
    c3.metric("Wrong", result["wrong"])
    c4.metric("Unattempted", result["unattempted"])

    st.metric("Accuracy (attempted only)", f"{result['accuracy']}%")

    if result["total"] > 0:
        pct = result["score"] / result["max_score"] * 100 if result["max_score"] else 0
        if pct >= 75:
            st.success("Excellent! Ye level real placement/exam round ke liye kaafi strong hai. 🔥")
        elif pct >= 50:
            st.info("Achha attempt hai — thodi aur speed aur accuracy pe kaam karo.")
        else:
            st.warning("Practice zaroori hai — weak sections identify karke unpe focus karo.")

    st.divider()
    st.subheader("📖 Detailed Review")

    filter_choice = st.radio(
        "Filter karo:", ["All", "Wrong only", "Unattempted only", "Correct only"], horizontal=True
    )

    for i, q in enumerate(st.session_state.quiz_questions):
        sel = st.session_state.answers.get(q["id"])
        is_correct = sel == q["correct_index"]
        is_unattempted = sel is None

        if filter_choice == "Wrong only" and (is_correct or is_unattempted):
            continue
        if filter_choice == "Unattempted only" and not is_unattempted:
            continue
        if filter_choice == "Correct only" and not is_correct:
            continue

        labels = ["A", "B", "C", "D"]
        with st.expander(
            f"Q{i+1}. {q['question'][:80]}{'...' if len(q['question'])>80 else ''}  "
            f"{'✅' if is_correct else ('⬜' if is_unattempted else '❌')}"
        ):
            st.write(f"**{q['question']}**")
            for j, opt in enumerate(q["options"]):
                prefix = f"({labels[j]}) {opt}"
                if j == q["correct_index"]:
                    st.markdown(f"✅ **{prefix}**  ← Correct Answer")
                elif j == sel:
                    st.markdown(f"❌ ~~{prefix}~~  ← Your Answer")
                else:
                    st.write(prefix)
            if is_unattempted:
                st.caption("Aapne ye question attempt nahi kiya.")
            st.info(f"**Explanation:** {q['explanation']}")

    st.divider()
    colA, colB = st.columns(2)
    with colA:
        if st.button("🔁 Retake Test (same settings)", use_container_width=True):
            st.session_state.stage = "setup"
            st.rerun()
    with colB:
        if st.button("🆕 Start Fresh", use_container_width=True):
            reset_all()
            st.rerun()
