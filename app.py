import streamlit as st
import json, os, time
from datetime import datetime
from fpdf import FPDF
from streamlit_autorefresh import st_autorefresh

# ---------------- CONFIG ----------------
QUESTIONS_PER_TEST = 30
DATA_FILE = os.path.join(os.path.dirname(__file__), "questions.json")
PROGRESS_FILE = os.path.join(os.path.dirname(__file__), "progress.json")
PDF_DIR = os.path.join(os.path.dirname(__file__), "pdf_reports")
os.makedirs(PDF_DIR, exist_ok=True)

st.set_page_config(page_title="MCQ Test Portal", page_icon="📝", layout="wide")

# ---------------- HELPERS ----------------
def load_questions():
    if not os.path.exists(DATA_FILE):
        st.error("questions.json nahi mila. Pehle generate_questions.py chalayein ya apni file daalein.")
        st.stop()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_progress(progress):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


def chunk_questions(qlist, size=QUESTIONS_PER_TEST):
    return [qlist[i:i + size] for i in range(0, len(qlist), size)]


def fmt_time(seconds):
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def clean(text):
    # fpdf classic fonts only support latin-1; replace unsupported chars safely
    return text.encode("latin-1", "replace").decode("latin-1")


def generate_pdf(username, topic, test_no, score, total, time_taken_str, details):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, clean("Test Result Report"), ln=True, align="C")
    pdf.ln(2)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, clean(f"Name: {username}"), ln=True)
    pdf.cell(0, 8, clean(f"Topic: {topic}    Test No: {test_no}"), ln=True)
    pdf.cell(0, 8, clean(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}"), ln=True)
    pdf.cell(0, 8, clean(f"Score: {score} / {total}"), ln=True)
    pdf.cell(0, 8, clean(f"Time Taken: {time_taken_str}"), ln=True)
    pdf.ln(4)
    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 8, clean("Question-wise Analysis"), ln=True)
    pdf.ln(1)

    for i, d in enumerate(details, 1):
        status = "Correct" if d["correct"] else ("Not Attempted" if d["selected"] is None else "Wrong")
        pdf.set_font("Arial", "B", 10)
        pdf.multi_cell(0, 6, clean(f"Q{i}. {d['question']}"))
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 6, clean(f"   Your Answer: {d['selected'] or '-'}"))
        pdf.multi_cell(0, 6, clean(f"   Correct Answer: {d['answer']}   [{status}]"))
        pdf.ln(1)

    safe_user = "".join(c for c in username if c.isalnum() or c in ("_", "-")) or "user"
    out_path = os.path.join(PDF_DIR, f"{safe_user}_{topic}_test{test_no}_result.pdf")
    pdf.output(out_path)
    return out_path


# ---------------- SESSION STATE INIT ----------------
defaults = {
    "username": "",
    "page": "login",
    "current_topic": None,
    "current_test_no": None,
    "start_time": None,
    "answers": {},
    "result": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

questions_bank = load_questions()
progress = load_progress()

# ---------------- LOGIN ----------------
if st.session_state.page == "login":
    st.title("📝 MCQ Test Portal")
    st.write("Shuru karne ke liye apna naam likhein.")
    name = st.text_input("Aapka naam", value=st.session_state.username)
    if st.button("Continue ➡️", type="primary"):
        if name.strip():
            st.session_state.username = name.strip()
            st.session_state.page = "home"
            st.rerun()
        else:
            st.warning("Naam likhna zaroori hai.")
    st.stop()

username = st.session_state.username
user_progress = progress.get(username, {})

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.markdown(f"👤 **{username}**")
    if st.button("🏠 Home"):
        st.session_state.page = "home"
        st.rerun()
    if st.button("🔓 Logout"):
        for k in defaults:
            st.session_state[k] = defaults[k]
        st.rerun()

# ---------------- HOME: TOPIC & TEST SELECTION ----------------
if st.session_state.page == "home":
    st.title("📚 Topics")
    st.caption("Har topic 30-30 questions ke tests mein baata gaya hai (jaise 300 questions = 10 tests).")

    for topic, qlist in questions_bank.items():
        tests = chunk_questions(qlist, QUESTIONS_PER_TEST)
        completed_count = sum(
            1 for t in range(1, len(tests) + 1)
            if user_progress.get(topic, {}).get(str(t), {}).get("completed")
        )
        with st.expander(f"📘 {topic}  —  {len(qlist)} questions  —  {len(tests)} tests  ({completed_count}/{len(tests)} complete)", expanded=False):
            cols = st.columns(5)
            for idx, test_qs in enumerate(tests, start=1):
                tinfo = user_progress.get(topic, {}).get(str(idx), {})
                done = tinfo.get("completed", False)
                label = f"{'✅' if done else '▶️'} Test {idx}"
                if done:
                    label += f"\n{tinfo.get('score')}/{tinfo.get('total')}"
                col = cols[(idx - 1) % 5]
                with col:
                    if st.button(label, key=f"{topic}_test_{idx}"):
                        st.session_state.current_topic = topic
                        st.session_state.current_test_no = idx
                        st.session_state.start_time = time.time()
                        st.session_state.answers = {}
                        st.session_state.result = None
                        st.session_state.page = "test"
                        st.rerun()
    st.stop()

# ---------------- TEST PAGE ----------------
if st.session_state.page == "test":
    topic = st.session_state.current_topic
    test_no = st.session_state.current_test_no
    tests = chunk_questions(questions_bank[topic], QUESTIONS_PER_TEST)
    test_qs = tests[test_no - 1]

    # auto-refresh every second so the timer keeps counting up continuously
    # and never stops until the user submits
    st_autorefresh(interval=1000, key="timer_refresh")

    elapsed = time.time() - st.session_state.start_time
    top_l, top_r = st.columns([3, 1])
    with top_l:
        st.subheader(f"{topic} — Test {test_no}  ({len(test_qs)} questions)")
    with top_r:
        st.metric("⏱️ Time", fmt_time(elapsed))

    st.progress(len([1 for q in test_qs if st.session_state.answers.get(q["id"])]) / len(test_qs))

    with st.form("test_form", clear_on_submit=False):
        for i, q in enumerate(test_qs, 1):
            st.markdown(f"**Q{i}. {q['question']}**")
            prev = st.session_state.answers.get(q["id"])
            choice = st.radio(
                "Answer chunein",
                options=q["options"],
                index=q["options"].index(prev) if prev in q["options"] else None,
                key=f"radio_{q['id']}",
                label_visibility="collapsed",
            )
            st.session_state.answers[q["id"]] = choice
            st.divider()

        submitted = st.form_submit_button("✅ Submit Test", type="primary")

    if submitted:
        total = len(test_qs)
        score = 0
        details = []
        for q in test_qs:
            selected = st.session_state.answers.get(q["id"])
            correct = (selected == q["answer"])
            if correct:
                score += 1
            details.append({
                "question": q["question"],
                "selected": selected,
                "answer": q["answer"],
                "correct": correct,
            })

        time_taken = time.time() - st.session_state.start_time

        # save progress with tick mark
        progress.setdefault(username, {}).setdefault(topic, {})[str(test_no)] = {
            "completed": True,
            "score": score,
            "total": total,
            "time_taken": fmt_time(time_taken),
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        save_progress(progress)

        st.session_state.result = {
            "topic": topic,
            "test_no": test_no,
            "score": score,
            "total": total,
            "time_taken": fmt_time(time_taken),
            "details": details,
        }
        st.session_state.page = "analysis"
        st.rerun()

    st.stop()

# ---------------- ANALYSIS PAGE ----------------
if st.session_state.page == "analysis":
    res = st.session_state.result
    if not res:
        st.session_state.page = "home"
        st.rerun()

    st.title("📊 Test Analysis")
    st.success(f"{res['topic']} — Test {res['test_no']} complete! ✅")

    c1, c2, c3 = st.columns(3)
    c1.metric("Score", f"{res['score']} / {res['total']}")
    pct = round(res['score'] / res['total'] * 100, 1)
    c2.metric("Percentage", f"{pct}%")
    c3.metric("Time Taken", res["time_taken"])

    correct_n = sum(1 for d in res["details"] if d["correct"])
    wrong_n = sum(1 for d in res["details"] if not d["correct"] and d["selected"] is not None)
    skipped_n = sum(1 for d in res["details"] if d["selected"] is None)
    st.write(f"✅ Correct: **{correct_n}**   ❌ Wrong: **{wrong_n}**   ⏭️ Skipped: **{skipped_n}**")

    with st.expander("📋 Question-wise details", expanded=False):
        for i, d in enumerate(res["details"], 1):
            icon = "✅" if d["correct"] else ("⏭️" if d["selected"] is None else "❌")
            st.markdown(f"{icon} **Q{i}. {d['question']}**")
            st.caption(f"Your answer: {d['selected'] or '-'}  |  Correct answer: {d['answer']}")

    pdf_path = generate_pdf(
        username, res["topic"], res["test_no"], res["score"], res["total"], res["time_taken"], res["details"]
    )
    with open(pdf_path, "rb") as f:
        st.download_button(
            "⬇️ Download PDF Report",
            data=f,
            file_name=os.path.basename(pdf_path),
            mime="application/pdf",
            type="primary",
        )

    if st.button("🏠 Back to Home"):
        st.session_state.page = "home"
        st.rerun()
