# FAQ Chatbot Prototype

A simple FAQ chatbot prototype built with **FastAPI** and **React + Vite**. It answers customer questions using only the content in your FAQ file, and tells the customer to contact support when the question isn't covered.

This is a working prototype to try locally before putting anything on a live site.

## How it works

1. The FastAPI backend loads `backend/faq.json` (30 example question/answer pairs) into memory on startup.
2. When a customer sends a message, the backend matches it against the FAQ questions using keyword overlap.
3. If there's a good match, the customer gets that FAQ's answer, rephrased conversationally by an LLM (Gemini by default, OpenAI as an alternative) — but still restricted to only the matched FAQ's content.
4. If nothing matches well enough, the bot says it doesn't know and points the customer to the support contact.
5. The React frontend is a single chat page to test this: type a question, or click one of the suggested questions, and see the bot's reply.

No database and no account/sign-up are required — the FAQ content is just a JSON file.

> The FAQ entries and support email in this repo are sample data. Replace them with the client's real content before this is shown as a finished solution.

> **This copy ships with a working demo Gemini API key** (in `backend/.env`) so you can try the conversational mode immediately, with no setup. It's a free-tier key meant only for this review — see [Conversational answers (Gemini / OpenAI)](#conversational-answers-gemini--openai) below to swap in your own key any time.

## Requirements

- Python 3.10+
- Node.js 18+ and npm

## Quick start (one command)

Double-click **`start.bat`** (Windows) or run **`bash start.sh`** (macOS/Linux — if it's not executable, run `chmod +x start.sh` first), or just:

```bash
python run.py
```

The first time you run it, it creates the backend virtual environment and installs both the backend and frontend dependencies (this can take a minute or two). Every time after that, it starts instantly. It automatically:

- picks a free port for the backend if `8000` is already used by something else on your machine
- starts both servers
- opens the chat page in your browser

Press `Ctrl+C` in that terminal window to stop both servers.

If you'd rather run (or understand) each piece yourself, see the manual steps below — `run.py` does the same things automatically.

## Manual setup

### 1. Start the backend

```bash
cd backend

# Create and activate a virtual environment.
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies.
pip install -r requirements.txt

# Create your local environment file.
copy .env.example .env       # Windows
# cp .env.example .env       # macOS/Linux

# Start the API with auto-reload.
uvicorn main:app --reload
```

The API runs at `http://127.0.0.1:8000`. Interactive docs are at `http://127.0.0.1:8000/docs`.

If port 8000 is already used by something else on your machine, start it on another port instead (`uvicorn main:app --reload --port 8010`) and update `VITE_API_URL` in `frontend/.env` to match.

#### Conversational answers (Gemini / OpenAI)

This copy already has a demo `GEMINI_API_KEY` set in `backend/.env`, so conversational answers work out of the box — no setup needed to try it.

To use your own key instead (recommended once you're past the trial stage, since the included key is free-tier and shared with this review period), open `backend/.env` and either:

- replace the existing key: `GEMINI_API_KEY=your_own_gemini_key`, or
- switch to OpenAI instead: clear `GEMINI_API_KEY` and set `OPENAI_API_KEY=your_openai_key` (`OPENAI_MODEL` defaults to `gpt-4o-mini`)

If `GEMINI_API_KEY` is set, Gemini is used; otherwise, if `OPENAI_API_KEY` is set, OpenAI is used; if neither is set, the bot just replies with the FAQ's answer text directly (no LLM call, still fully functional). The model is always instructed to answer only from the matched FAQ entry. Restart the backend after changing `.env`. Never put either key in the frontend.

### 2. Start the frontend

In a second terminal:

```bash
cd frontend
npm install
copy .env.example .env       # Windows, if you haven't already
# cp .env.example .env       # macOS/Linux
npm run dev
```

Open the URL Vite prints, normally `http://localhost:5173`.

## Using the chat page

- Type a question in the input box, or click a suggested question chip.
- The reply is based only on the FAQ content; unrelated questions get a fallback message with the support contact.
- Use the refresh icon in the header to clear the conversation and start over.

## API reference

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/health` | Status, FAQ count, whether AI mode is active, and which provider (`gemini`/`openai`) |
| GET | `/api/faqs` | List of FAQ questions (used for the suggestion chips) |
| POST | `/api/chat` | Send `{"message": "..."}`, get back `{"answer", "matched", "matched_question"}` |

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"How do I reset my password?\"}"
```

## Using your own FAQ content

Edit `backend/faq.json`. Each entry needs a `question` and an `answer`:

```json
[
  {
    "question": "How can I reset my password?",
    "answer": "Select 'Forgot password' on the sign-in page and follow the email instructions."
  }
]
```

Also update `SUPPORT_EMAIL` in `backend/.env`, and restart the backend after any change to `faq.json` or `.env`.

## Running the tests

```bash
cd backend
venv\Scripts\activate         # if not already active
pytest -q
```

Tests cover question matching (`tokenize`, `retrieve_faqs`) and the fallback message.

## Notes and limitations (prototype, not production)

- Matching is keyword-overlap based, not semantic search. It can miss paraphrased questions — test it with real customer phrasing and tune `MATCH_THRESHOLD` in `backend/main.py` if needed.
- No LLM can be perfectly guaranteed to stay on-topic; test out-of-scope questions before relying on this.
- Conversation history lives only in the browser tab (not saved anywhere) and nothing is logged server-side.
- Before any live-site use, add rate limiting, input validation hardening, and a CORS allowlist instead of `allow_origins=["*"]`.
- The shipped `GEMINI_API_KEY` is a free-tier demo key meant only for trying this prototype. It may be rate-limited or revoked after the review period — swap in your own key for anything beyond that (see [Conversational answers (Gemini / OpenAI)](#conversational-answers-gemini--openai)).

## Before handing this off as finished

- [ ] Replace the sample FAQs in `backend/faq.json` with the client's approved content
- [ ] Replace `support@example.com` with the client's real support email
- [ ] Test actual customer phrasing against the matcher and tune the threshold if needed
- [ ] Swap the demo `GEMINI_API_KEY` for a real/owned key (or the client's own key) before any long-term or live use
