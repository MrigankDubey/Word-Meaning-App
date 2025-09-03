# Word Meaning (Daily 20) — Streamlit App

A Streamlit web application for students to learn new words daily. Each day, users get a quiz of 20 *definitions* with 5 options each to select the correct *word*. If a user scores 20/20, a fresh set of 20 unseen words is immediately served. If they miss any, the app shows a **review** of their incorrect questions (with the correct answers) and then starts a **new quiz of 20** words made of *only new* words for that day. For a given user, **words never repeat in the same day**.

## Quick start

```bash
# 1) Install deps (Python 3.10+ recommended)
pip install -r requirements.txt

# 2) Initialize the local SQLite DB and seed words (optional, done on first run)
streamlit run app.py
```

## Admin account

- First user created can optionally be an admin (toggle on sign up). Admins can upload word lists (`CSV`) from the **Admin > Words** page.
- Sample `data/words.csv` is included. You can keep appending new rows.

## Data model

- SQLite DB at `app/data/app.db`
- Tables:
  - `users` — basic auth (bcrypt hashed passwords)
  - `words` — master word bank
  - `user_day_words` — which words a user has been shown today (no repeats per day)
  - `user_attempts` — per-question attempts for audit / spaced repetition metadata
  - `sessions` — each 20-question run for a user/day
  - `session_items` — each item served in a session

## Daily logic (high level)

- At login, the app computes the local date using Asia/Kolkata and either resumes today's open session or creates a new session of 20 items.
- During a session, each item is a **definition** with **5 word options** (1 correct + 4 distractors from the same part-of-speech if possible).
- After all 20 answered:
  - If **all correct** → instantly start a **new 20** completely unseen today.
  - If **any wrong** → show a Review page listing wrong answers with the correct mapping, then start a **new 20** unseen today.
- Words never repeat per user per local day.

## Environment

- Streamlit for UI
- SQLite3 + the app's backend module for data
- pytz for India time
- bcrypt for password hashing

## Deploy

- Streamlit Community Cloud, HuggingFace Spaces, or any VM/container should work.
- For Heroku/Docker, add the `Procfile` and `Dockerfile` as needed (not included by default).

## Notes

- This is a single-repo app organized into modules. No external API is required.
- Import your own CSV with columns: `text,definition,part_of_speech,language`.
