import streamlit as st
import json
import random
import os

st.set_page_config(page_title="Exam Prep — Question Bank", page_icon="📝", layout="centered")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

CATEGORIES = {
    "Quantitative Aptitude": "quantitative_aptitude.json",
    "Logical Reasoning": "logical_reasoning.json",
    "Verbal Ability": "verbal_ability.json",
    "Data Interpretation": "data_interpretation.json",
    "Data Analysis & Data Science": "data_analysis_ds.json",
    "Banking Awareness": "banking_awareness.json",
}


@st.cache_data
def load_category(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        st.error(
            f"⚠️ Could not find `{filename}` at expected path:\n\n`{path}`\n\n"
            "Make sure the `data/` folder sits in the **same directory** as `app.py` "
            "in your GitHub repo (not in a subfolder), and that all 6 JSON files were "
            "committed and pushed."
        )
        st.stop()
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def init_state():
    defaults = {
        "test_started": False,
        "questions": [],
        "current_idx": 0,
        "answers": {},
        "submitted": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()

st.title("📝 Exam Prep — Question Bank")
st.caption("Real, hand-written questions with full solutions. Base bank — growing towards 1500 questions.")

with st.sidebar:
    st.header("Build Your Test")
    selected_categories = st.multiselect(
        "Choose categories", list(CATEGORIES.keys()), default=list(CATEGORIES.keys())
    )
    num_q = st.slider("Number of questions", 5, 48, 20)
    shuffle = st.checkbox("Shuffle questions", value=True)

    if st.button("🚀 Start Test", use_container_width=True):
        pool = []
        for cat in selected_categories:
            data = load_category(CATEGORIES[cat])
            for q in data:
                q = dict(q)
                q["category"] = cat
                pool.append(q)
        if shuffle:
            random.shuffle(pool)
        pool = pool[:num_q]
        st.session_state.questions = pool
        st.session_state.current_idx = 0
        st.session_state.answers = {}
        st.session_state.submitted = False
        st.session_state.test_started = True

    st.divider()
    total_available = sum(len(load_category(f)) for f in CATEGORIES.values())
    st.metric("Total questions in bank", total_available)
    for cat, f in CATEGORIES.items():
        st.caption(f"{cat}: {len(load_category(f))}")


def show_question(q, idx):
    st.subheader(f"Q{idx + 1}. [{q['category']}]")
    st.write(q["question"])
    key = f"q_{idx}"
    prev_answer = st.session_state.answers.get(idx)
    choice = st.radio(
        "Select an answer:",
        q["options"],
        index=q["options"].index(prev_answer) if prev_answer in q["options"] else None,
        key=key,
    )
    if choice is not None:
        st.session_state.answers[idx] = choice


if not st.session_state.test_started:
    st.info("👈 Select categories and number of questions in the sidebar, then click **Start Test**.")
elif not st.session_state.submitted:
    questions = st.session_state.questions
    progress = len(st.session_state.answers) / len(questions) if questions else 0
    st.progress(progress, text=f"Answered {len(st.session_state.answers)} / {len(questions)}")

    for idx, q in enumerate(questions):
        with st.container(border=True):
            show_question(q, idx)

    st.divider()
    if st.button("✅ Submit Test", type="primary", use_container_width=True):
        st.session_state.submitted = True
        st.rerun()
else:
    questions = st.session_state.questions
    correct = 0
    for idx, q in enumerate(questions):
        user_ans = st.session_state.answers.get(idx)
        if user_ans == q["answer"]:
            correct += 1

    total = len(questions)
    score_pct = (correct / total * 100) if total else 0

    st.header("📊 Results")
    col1, col2, col3 = st.columns(3)
    col1.metric("Score", f"{correct} / {total}")
    col2.metric("Percentage", f"{score_pct:.1f}%")
    col3.metric("Attempted", f"{len(st.session_state.answers)} / {total}")

    st.divider()
    st.subheader("Review — Solutions")
    for idx, q in enumerate(questions):
        user_ans = st.session_state.answers.get(idx, "Not attempted")
        is_correct = user_ans == q["answer"]
        icon = "✅" if is_correct else "❌"
        with st.expander(f"{icon} Q{idx + 1}. [{q['category']}] {q['question'][:60]}..."):
            st.write(f"**Question:** {q['question']}")
            st.write(f"**Your answer:** {user_ans}")
            st.write(f"**Correct answer:** {q['answer']}")
            st.write(f"**Solution:** {q['solution']}")

    if st.button("🔄 Take Another Test", use_container_width=True):
        st.session_state.test_started = False
        st.session_state.submitted = False
        st.session_state.answers = {}
        st.rerun()
