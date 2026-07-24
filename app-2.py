import streamlit as st
import json
import os
import random

st.set_page_config(page_title="Exam Prep Quiz", page_icon="📝", layout="centered")

DATA_DIR = "data"

TOPIC_LABELS = {
    "bank_quant": "🏦 Bank - Quant",
    "bank_reasoning": "🏦 Bank - Reasoning",
    "bank_verbal": "🏦 Bank - Verbal",
    "bank_di": "🏦 Bank - Data Interpretation",
    "it_aptitude": "💻 IT - Aptitude/Reasoning",
    "ds_da": "📊 DS/DA - Conceptual",
}


DATA_FILE = os.path.join(DATA_DIR, "all_questions.json")


@st.cache_data
def load_all_questions():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_topic(topic_key):
    all_qs = load_all_questions()
    return [q for q in all_qs if q.get("topic") == topic_key]


def init_state():
    defaults = {
        "quiz_started": False,
        "questions": [],
        "current_idx": 0,
        "score": 0,
        "answered": False,
        "selected_option": None,
        "wrong_list": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def start_quiz(topic_key, num_questions, shuffle):
    qs = load_topic(topic_key)
    if shuffle:
        qs = qs.copy()
        random.shuffle(qs)
    st.session_state.questions = qs[:num_questions]
    st.session_state.current_idx = 0
    st.session_state.score = 0
    st.session_state.answered = False
    st.session_state.selected_option = None
    st.session_state.wrong_list = []
    st.session_state.quiz_started = True


def reset_quiz():
    st.session_state.quiz_started = False
    st.session_state.questions = []
    st.session_state.current_idx = 0
    st.session_state.score = 0
    st.session_state.answered = False
    st.session_state.selected_option = None
    st.session_state.wrong_list = []


def main():
    init_state()
    st.title("📝 Exam Prep Quiz App")

    # Sidebar - topic counts
    st.sidebar.header("📚 Available Topics")
    available_topics = {}
    for key, label in TOPIC_LABELS.items():
        qs = load_topic(key)
        available_topics[key] = len(qs)
        st.sidebar.write(f"{label}: **{len(qs)}** questions")

    if not st.session_state.quiz_started:
        st.subheader("Start a Quiz")
        topic_choice = st.selectbox(
            "Select topic",
            options=list(TOPIC_LABELS.keys()),
            format_func=lambda k: TOPIC_LABELS[k],
        )
        max_q = available_topics.get(topic_choice, 0)
        if max_q == 0:
            st.warning("Is topic mein abhi koi question nahi hai. data/ folder mein JSON add karo.")
            return
        num_q = st.slider("Number of questions", 1, max_q, min(10, max_q))
        shuffle = st.checkbox("Shuffle questions", value=True)
        if st.button("Start Quiz 🚀"):
            start_quiz(topic_choice, num_q, shuffle)
            st.rerun()
        return

    questions = st.session_state.questions
    idx = st.session_state.current_idx
    total = len(questions)

    if idx >= total:
        st.success(f"Quiz complete! Score: {st.session_state.score} / {total}")
        pct = (st.session_state.score / total * 100) if total else 0
        st.metric("Accuracy", f"{pct:.1f}%")
        if st.session_state.wrong_list:
            with st.expander("❌ Review incorrect answers"):
                for w in st.session_state.wrong_list:
                    st.markdown(f"**Q: {w['question']}**")
                    st.write(f"Your answer: {w['selected']}")
                    st.write(f"Correct answer: {w['answer']}")
                    st.caption(w.get("explanation", ""))
                    st.divider()
        if st.button("🔄 Try Another Quiz"):
            reset_quiz()
            st.rerun()
        return

    q = questions[idx]
    st.progress((idx) / total)
    st.caption(f"Question {idx + 1} of {total} | Score: {st.session_state.score}")
    st.subheader(q["question"])

    options = q["options"]
    selected = st.radio("Choose an answer:", options, index=None, key=f"radio_{idx}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Submit", disabled=st.session_state.answered):
            if selected is None:
                st.warning("Pehle ek option select karo.")
            else:
                st.session_state.answered = True
                st.session_state.selected_option = selected
                if selected == q["answer"]:
                    st.session_state.score += 1
                else:
                    st.session_state.wrong_list.append({
                        "question": q["question"],
                        "selected": selected,
                        "answer": q["answer"],
                        "explanation": q.get("explanation", ""),
                    })
                st.rerun()

    if st.session_state.answered:
        if st.session_state.selected_option == q["answer"]:
            st.success(f"✅ Correct! {q.get('explanation', '')}")
        else:
            st.error(f"❌ Wrong. Correct answer: {q['answer']}")
            st.info(q.get("explanation", ""))
        with col2:
            if st.button("Next ➡️"):
                st.session_state.current_idx += 1
                st.session_state.answered = False
                st.session_state.selected_option = None
                st.rerun()


if __name__ == "__main__":
    main()
