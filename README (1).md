# Topic-wise Quiz App (Streamlit)

## Isme kya hai
- `app.py` — poora Streamlit app
- `questions_master_all.json` — aapke 2374 questions (15 topics)
- `requirements.txt` — dependencies

## Features
- **Topic-wise tests**: har topic ke questions ko 30-30 ke groups mein baant kar tests bante hain (jaise 300 questions wale topic mein 10 tests).
- **Live timer**: test shuru hote hi timer chalna start ho jata hai aur continuously chalta rehta hai — kabhi rukta nahi, chahe aap kuch bhi karo.
- **Tick mark**: jo test user complete kar chuka hai uspe home page par ✅ aur uska score dikhta hai.
- **Analysis + PDF**: test submit karne ke baad score, time, aur question-wise (correct/wrong + English & Hindi solution) analysis milta hai, aur "Download PDF Analysis Report" button se PDF bhi ban jata hai.
- **Multi-user**: login screen par naam daal kar har user ki progress alag se track hoti hai (SQLite DB — `progress.db`, app ke folder mein automatically ban jaata hai).

## Local run
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Community Cloud par deploy karna
1. Ye teeno files (`app.py`, `questions_master_all.json`, `requirements.txt`) ek GitHub repo mein daal do.
2. https://share.streamlit.io par jao, GitHub se login karo.
3. "New app" -> apna repo select karo -> main file `app.py` daalo -> Deploy.
4. 2-3 minute mein app live ho jayegi.

## Note
- Progress `progress.db` (SQLite) file mein save hota hai jo app ke folder mein hi ban jaati hai. Streamlit Cloud ka free tier restart/redeploy hone par filesystem reset ho sakta hai — agar aapko progress hamesha ke liye persistent chahiye (app restart ke baad bhi), to ise koi external DB (jaise Supabase/Postgres) se replace karna padega. Normal usage (same running session) ke liye ye theek se kaam karega.
- Agar kabhi PDF me koi special character dikhe missing, wo isliye hai kyunki PDF ka default font sirf English/Latin characters support karta hai (aapke saare questions/solutions already English script mein hain, to koi issue nahi aayega).
