# Exam Prep — Question Bank App

Real, hand-written questions with full solutions, organized into 6 categories.
Base bank: 48 questions (8 per category). Built to scale to 1500+.

## Structure
```
exam_prep_app/
  app.py                          # Streamlit app
  requirements.txt
  data/
    quantitative_aptitude.json
    logical_reasoning.json
    verbal_ability.json
    data_interpretation.json
    data_analysis_ds.json
    banking_awareness.json
```

## How to add more questions (scale to 180 → 1500)

Open the relevant category's JSON file in `data/` and append new objects
in the same format:

```json
{
  "id": "QA009",
  "question": "Your question text here",
  "options": ["Option A", "Option B", "Option C", "Option D"],
  "answer": "Option A",
  "solution": "Full step-by-step explanation of the correct answer."
}
```

Rules to keep in mind:
- `id` should be unique within the file (prefix + running number, e.g. QA009, QA010...).
- `answer` must exactly match one of the strings in `options`.
- Keep `solution` self-contained — it should explain *why*, not just repeat the answer.
- No need to touch `app.py` — it automatically picks up every question in every
  JSON file each time the app loads.

Suggested batch workflow: add 20-30 real questions to one category at a time,
sanity-check them (answer actually matches solution!), commit, repeat across
categories until each file has 250 questions (6 × 250 = 1500).

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Community Cloud
1. Push this folder to a GitHub repo (e.g. `exam-prep-app`).
2. Go to https://share.streamlit.io → **New app**.
3. Select your repo, branch, and set main file path to `app.py`.
4. Deploy. Streamlit Cloud installs `requirements.txt` automatically.
5. Every time you push new questions to the `data/*.json` files and redeploy
   (or Streamlit auto-detects the git push), the app will include them —
   no code changes needed.
