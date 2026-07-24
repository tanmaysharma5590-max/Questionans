import streamlit as st
import json, time, sqlite3, os
from datetime import datetime
from io import BytesIO
import streamlit.components.v1 as components
from fpdf import FPDF

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
QUESTIONS_PER_TEST = 30
DB_PATH = os.path.join(os.path.dirname(__file__), "progress.db")
DATA_PATH = os.path.join(os.path.dirname(__file__), "questions_master_all.json")

st.set_page_config(page_title="Topic-wise Quiz App", page_icon="📝", layout="wide")

# ---------------------------------------------------------------------------
# DATABASE
# ---------------------------------------------------------------------------
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attempts (
            user TEXT NOT NULL,
            topic TEXT NOT NULL,
            test_no INTEGER NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            time_seconds INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            answers_json TEXT NOT NULL,
            PRIMARY KEY (user, topic, test_no)
        )
    """)
    conn.commit()
    return conn

conn = get_conn()

def save_attempt(user, topic, test_no, score, total, time_seconds, answers):
    conn.execute(
        "REPLACE INTO attempts (user, topic, test_no, score, total, time_seconds, timestamp, answers_json) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (user, topic, test_no, score, total, time_seconds,
         datetime.now().strftime("%Y-%m-%d %H:%M:%S"), json.dumps(answers))
    )
    conn.commit()

def get_attempt(user, topic, test_no):
    row = conn.execute(
        "SELECT score, total, time_seconds, timestamp, answers_json FROM attempts "
        "WHERE user=? AND topic=? AND test_no=?", (user, topic, test_no)
    ).fetchone()
    if not row:
        return None
    return {"score": row[0], "total": row[1], "time_seconds": row[2],
            "timestamp": row[3], "answers": json.loads(row[4])}

def get_completed_set(user):
    rows = conn.execute("SELECT topic, test_no FROM attempts WHERE user=?", (user,)).fetchall()
    return set((r[0], r[1]) for r in rows)

# ---------------------------------------------------------------------------
# DATA LOADING
# ---------------------------------------------------------------------------
@st.cache_data
def load_questions():
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    topics = {}
    for q in data:
        topics.setdefault(q["topic"], []).append(q)
    for t in topics:
        topics[t].sort(key=lambda x: x["id"])
    return topics

TOPICS = load_questions()

def get_test_questions(topic, test_no):
    qs = TOPICS[topic]
    start = (test_no - 1) * QUESTIONS_PER_TEST
    end = start + QUESTIONS_PER_TEST
    return qs[start:end]

def num_tests(topic):
    n = len(TOPICS[topic])
    return -(-n // QUESTIONS_PER_TEST)  # ceil division

# ---------------------------------------------------------------------------
# TIMER (client-side, never stops / never pauses the test)
# ---------------------------------------------------------------------------
def render_live_timer(start_ts):
    components.html(f"""
        <div style="font-size:22px;font-weight:700;color:#1f6feb;
                    padding:8px 14px;border:2px solid #1f6feb;border-radius:8px;
                    display:inline-block;font-family:monospace;">
            ⏱️ <span id="timer">00:00:00</span>
        </div>
        <script>
            const start = {int(start_ts * 1000)};
            function pad(n) {{ return n.toString().padStart(2,'0'); }}
            function tick() {{
                const now = Date.now();
                let diff = Math.floor((now - start) / 1000);
                const h = Math.floor(diff / 3600);
                const m = Math.floor((diff % 3600) / 60);
                const s = diff % 60;
                document.getElementById('timer').innerText = pad(h)+":"+pad(m)+":"+pad(s);
            }}
            setInterval(tick, 1000);
            tick();
        </script>
    """, height=60)

# ---------------------------------------------------------------------------
# PDF REPORT
# ---------------------------------------------------------------------------
def _safe(text):
    """Core PDF fonts only support latin-1; replace anything outside that range."""
    return str(text).encode("latin-1", "replace").decode("latin-1")

def build_pdf(user, topic, test_no, questions, answers, score, total, time_seconds):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.multi_cell(0, 10, "Quiz Test Analysis Report")
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 7, _safe(f"User: {user}"))
    pdf.multi_cell(0, 7, _safe(f"Topic: {topic}   |   Test No: {test_no}"))
    mins, secs = divmod(time_seconds, 60)
    pdf.multi_cell(0, 7, f"Score: {score} / {total}   |   Time Taken: {mins}m {secs}s")
    pdf.multi_cell(0, 7, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    pdf.ln(4)

    for i, q in enumerate(questions, 1):
        user_ans = answers.get(str(q["id"]), "Not Answered")
        correct = q["answer"]
        is_correct = user_ans == correct

        pdf.set_font("Helvetica", "B", 11)
        pdf.multi_cell(0, 6, _safe(f"Q{i}. {q['question']}"))
        pdf.set_font("Helvetica", "", 10)
        for opt, text in q["options"].items():
            pdf.multi_cell(0, 6, _safe(f"   {opt}. {text}"))

        pdf.set_font("Helvetica", "B", 10)
        status = "Correct" if is_correct else "Wrong"
        pdf.set_text_color(0, 130, 0) if is_correct else pdf.set_text_color(200, 0, 0)
        pdf.multi_cell(0, 6, _safe(f"   Your Answer: {user_ans}   |   Correct Answer: {correct}   ({status})"))
        pdf.set_text_color(0, 0, 0)

        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(0, 5, _safe(f"   Solution (EN): {q['solution_en']}"))
        pdf.multi_cell(0, 5, _safe(f"   Solution (HI): {q['solution_hi']}"))
        pdf.ln(3)

    out = pdf.output()
    return bytes(out)

# ---------------------------------------------------------------------------
# SESSION STATE INIT
# ---------------------------------------------------------------------------
defaults = {
    "page": "login", "user": "", "current_topic": None, "current_test_no": None,
    "test_questions": [], "test_answers": {}, "test_start_ts": None,
    "last_result": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def go_home():
    st.session_state.page = "home"
    st.session_state.current_topic = None
    st.session_state.current_test_no = None
    st.session_state.test_questions = []
    st.session_state.test_answers = {}
    st.session_state.test_start_ts = None

# ---------------------------------------------------------------------------
# PAGE: LOGIN
# ---------------------------------------------------------------------------
if st.session_state.page == "login":
    st.title("📝 Topic-wise Quiz App")
    st.write("Apna naam / user ID daalein taaki aapki progress track ho sake.")
    name = st.text_input("User Name")
    if st.button("Start", type="primary"):
        if name.strip():
            st.session_state.user = name.strip()
            go_home()
            st.rerun()
        else:
            st.warning("Please naam daalein.")

# ---------------------------------------------------------------------------
# PAGE: HOME (topic + test list with tick marks)
# ---------------------------------------------------------------------------
elif st.session_state.page == "home":
    st.title("📝 Topic-wise Quiz App")
    col1, col2 = st.columns([4, 1])
    with col1:
        st.write(f"👤 **User:** {st.session_state.user}")
    with col2:
        if st.button("Switch User"):
            st.session_state.page = "login"
            st.session_state.user = ""
            st.rerun()

    completed = get_completed_set(st.session_state.user)
    total_q = sum(len(v) for v in TOPICS.values())
    total_tests = sum(num_tests(t) for t in TOPICS)
    done_tests = len(completed)
    st.progress(done_tests / total_tests if total_tests else 0,
                text=f"Overall Progress: {done_tests}/{total_tests} tests completed")
    st.caption(f"Total Questions: {total_q}  |  Total Topics: {len(TOPICS)}  |  {QUESTIONS_PER_TEST} questions per test")
    st.divider()

    for topic in sorted(TOPICS.keys()):
        n_q = len(TOPICS[topic])
        n_t = num_tests(topic)
        topic_done = sum(1 for i in range(1, n_t + 1) if (topic, i) in completed)
        with st.expander(f"**{topic}**  —  {n_q} questions  —  {n_t} tests  ({topic_done}/{n_t} done)"):
            cols = st.columns(5)
            for i in range(1, n_t + 1):
                is_done = (topic, i) in completed
                label = f"✅ Test {i}" if is_done else f"Test {i}"
                with cols[(i - 1) % 5]:
                    if is_done:
                        att = get_attempt(st.session_state.user, topic, i)
                        st.caption(f"Score: {att['score']}/{att['total']}")
                    if st.button(label, key=f"{topic}_{i}"):
                        st.session_state.current_topic = topic
                        st.session_state.current_test_no = i
                        st.session_state.test_questions = get_test_questions(topic, i)
                        st.session_state.test_answers = {}
                        st.session_state.test_start_ts = time.time()
                        st.session_state.page = "test"
                        st.rerun()

# ---------------------------------------------------------------------------
# PAGE: TEST (timer keeps running, never stops)
# ---------------------------------------------------------------------------
elif st.session_state.page == "test":
    topic = st.session_state.current_topic
    tno = st.session_state.current_test_no
    questions = st.session_state.test_questions

    top_l, top_r = st.columns([3, 1])
    with top_l:
        st.subheader(f"{topic} — Test {tno}")
        st.caption(f"{len(questions)} Questions | User: {st.session_state.user}")
    with top_r:
        render_live_timer(st.session_state.test_start_ts)

    st.info("Timer chalta rahega — yeh kabhi ruknega nahi. Jab poora ho jaaye to niche Submit karein.")
    st.divider()

    for idx, q in enumerate(questions, 1):
        st.markdown(f"**Q{idx}. {q['question']}**")
        opt_keys = list(q["options"].keys())
        opt_labels = [f"{k}. {v}" for k, v in q["options"].items()]
        prev = st.session_state.test_answers.get(str(q["id"]))
        default_idx = opt_keys.index(prev) if prev in opt_keys else None
        choice = st.radio(
            "Select answer", opt_labels, index=default_idx,
            key=f"radio_{q['id']}", label_visibility="collapsed"
        )
        if choice:
            st.session_state.test_answers[str(q["id"])] = choice.split(".")[0]
        st.write("")

    st.divider()
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("⬅ Save & Exit (without submitting)"):
            go_home()
            st.rerun()
    with c2:
        if st.button("✅ Submit Test", type="primary"):
            elapsed = int(time.time() - st.session_state.test_start_ts)
            score = sum(
                1 for q in questions
                if st.session_state.test_answers.get(str(q["id"])) == q["answer"]
            )
            total = len(questions)
            save_attempt(st.session_state.user, topic, tno, score, total,
                         elapsed, st.session_state.test_answers)
            st.session_state.last_result = {
                "topic": topic, "test_no": tno, "questions": questions,
                "answers": dict(st.session_state.test_answers),
                "score": score, "total": total, "time_seconds": elapsed,
            }
            st.session_state.page = "result"
            st.rerun()

# ---------------------------------------------------------------------------
# PAGE: RESULT / ANALYSIS + PDF
# ---------------------------------------------------------------------------
elif st.session_state.page == "result":
    r = st.session_state.last_result
    if not r:
        go_home()
        st.rerun()

    st.title("📊 Test Analysis")
    st.subheader(f"{r['topic']} — Test {r['test_no']}")

    mins, secs = divmod(r["time_seconds"], 60)
    c1, c2, c3 = st.columns(3)
    c1.metric("Score", f"{r['score']} / {r['total']}")
    c2.metric("Percentage", f"{round(r['score']/r['total']*100, 1)}%")
    c3.metric("Time Taken", f"{mins}m {secs}s")

    pdf_bytes = build_pdf(
        st.session_state.user, r["topic"], r["test_no"], r["questions"],
        r["answers"], r["score"], r["total"], r["time_seconds"]
    )
    st.download_button(
        "⬇️ Download PDF Analysis Report", data=pdf_bytes,
        file_name=f"{r['topic'].replace(' ', '_')}_Test{r['test_no']}_Report.pdf",
        mime="application/pdf", type="primary"
    )

    st.divider()
    st.write("### Question-wise Review")
    for idx, q in enumerate(r["questions"], 1):
        user_ans = r["answers"].get(str(q["id"]), "Not Answered")
        correct = q["answer"]
        is_correct = user_ans == correct
        icon = "✅" if is_correct else "❌"
        with st.expander(f"{icon} Q{idx}. {q['question'][:80]}..."):
            for k, v in q["options"].items():
                st.write(f"{k}. {v}")
            st.write(f"**Your Answer:** {user_ans}  |  **Correct Answer:** {correct}")
            st.write(f"**Solution (EN):** {q['solution_en']}")
            st.write(f"**Solution (HI):** {q['solution_hi']}")

    st.divider()
    if st.button("🏠 Back to Home", type="primary"):
        go_home()
        st.rerun()
