"""FastAPI backend for a simple FAQ chatbot prototype.

Loads the company's FAQ content from faq.json and answers customer
questions based only on that content. Falls back to a support contact
message when nothing in the FAQ matches the question.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv(Path(__file__).with_name(".env"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "support@example.com").strip()

FAQ_PATH = Path(__file__).with_name("faq.json")
with open(FAQ_PATH, "r", encoding="utf-8") as f:
    FAQS: List[Dict[str, str]] = json.load(f)

STOP_WORDS = {
    "a", "an", "the", "in", "on", "of", "for", "to", "at", "by", "with",
    "is", "are", "do", "does", "did", "i", "my", "we", "our", "you", "your",
    "can", "how", "what", "where", "when", "why", "it", "this", "that",
}

MATCH_THRESHOLD = 0.5

app = FastAPI(title="FAQ Chatbot", version="1.0.0")

# Allow the local Vite frontend (and any origin, for prototype testing) to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request / response models ---
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)


class ChatResponse(BaseModel):
    answer: str
    matched: bool
    matched_question: Optional[str] = None


# --- FAQ matching ---
def tokenize(text: str) -> set:
    """Lowercase, split into words, and drop common filler words."""
    return set(re.findall(r"\b\w{2,}\b", text.lower())) - STOP_WORDS


def retrieve_faqs(query: str, faqs: List[Dict[str, str]] = FAQS) -> List[Dict[str, object]]:
    """Return FAQ entries whose question overlaps the query, best match first.

    Each returned entry carries a "coverage" score: the fraction of the FAQ
    question's meaningful words that the query also contains.
    """
    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    scored = []
    for faq in faqs:
        faq_tokens = tokenize(faq["question"])
        if not faq_tokens:
            continue

        overlap = query_tokens & faq_tokens
        if not overlap:
            continue

        coverage = len(overlap) / len(faq_tokens)
        if coverage >= MATCH_THRESHOLD:
            scored.append({**faq, "coverage": coverage})

    scored.sort(key=lambda entry: entry["coverage"], reverse=True)
    return scored


def fallback_answer() -> str:
    """Response shown when no FAQ entry matches the customer's question."""
    return (
        "I don't have an answer for that in our FAQ yet. "
        f"Please contact our support team at {SUPPORT_EMAIL} and they'll be happy to help."
    )


GREETING_WORDS = {"hi", "hey", "hiya", "howdy", "yo", "hello", "good", "morning", "afternoon", "evening"}


def is_greeting(text: str) -> bool:
    """True for short greetings like "hi", "hello there", "good morning"."""
    words = re.sub(r"[^\w\s]", "", text.lower()).split()
    if not words or len(words) > 3:
        return False
    return all(word in GREETING_WORDS or word == "there" for word in words) and any(
        word in GREETING_WORDS for word in words
    )


def _build_grounding_prompt(faq: Dict[str, object]) -> str:
    return (
        "You are a friendly customer support assistant. Answer the customer's question "
        "conversationally, using ONLY the information in the FAQ entry below. Do not add "
        "any information, policy, or detail that isn't stated in the FAQ entry. Keep the "
        "answer short and natural.\n\n"
        f"FAQ question: {faq['question']}\n"
        f"FAQ answer: {faq['answer']}"
    )


async def _ask_gemini(user_query: str, system_prompt: str) -> Optional[str]:
    model = GEMINI_MODEL.replace("models/", "").strip() or "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(
                url,
                json={
                    "contents": [
                        {"role": "user", "parts": [{"text": f"{system_prompt}\n\nCustomer question: {user_query}"}]}
                    ],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 300,
                        # Disable "thinking" tokens: this is a short grounded Q&A task that
                        # doesn't need extended reasoning, and the thinking budget was eating
                        # into maxOutputTokens and truncating the visible answer.
                        "thinkingConfig": {"thinkingBudget": 0},
                    },
                },
            )
            if res.status_code == 200:
                data = res.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        text = parts[0].get("text", "").strip()
                        if text:
                            return text
    except Exception:
        pass
    return None


async def _ask_openai(user_query: str, system_prompt: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "model": OPENAI_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_query},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 300,
                },
            )
            if res.status_code == 200:
                data = res.json()
                content = data["choices"][0]["message"]["content"].strip()
                if content:
                    return content
    except Exception:
        pass
    return None


async def generate_conversational_answer(user_query: str, faq: Dict[str, object]) -> str:
    """Ask the configured LLM provider to phrase the matched FAQ answer conversationally.

    Strictly grounded in the matched FAQ entry. Tries Gemini first (if configured),
    then OpenAI, and falls back to the FAQ's own answer text if both are unavailable
    or the calls fail.
    """
    system_prompt = _build_grounding_prompt(faq)

    if GEMINI_API_KEY:
        result = await _ask_gemini(user_query, system_prompt)
        if result:
            return result

    if OPENAI_API_KEY:
        result = await _ask_openai(user_query, system_prompt)
        if result:
            return result

    return str(faq["answer"])


# --- Routes ---
@app.get("/")
def root():
    return {"status": "ok", "service": "faq-chatbot"}


@app.get("/api/health")
def health():
    provider = "gemini" if GEMINI_API_KEY else "openai" if OPENAI_API_KEY else None
    return {
        "status": "ok",
        "faq_count": len(FAQS),
        "ai_mode": bool(provider),
        "provider": provider,
    }


@app.get("/api/faqs")
def list_faqs():
    """Return the FAQ questions, e.g. to show as suggested questions in the UI."""
    return {"faqs": [faq["question"] for faq in FAQS]}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    message = req.message.strip()

    if is_greeting(message):
        return ChatResponse(
            answer="Hello! I can answer questions based on our FAQ. What would you like to know?",
            matched=False,
        )

    matches = retrieve_faqs(message, FAQS)
    if not matches:
        return ChatResponse(answer=fallback_answer(), matched=False)

    best = matches[0]
    if GEMINI_API_KEY or OPENAI_API_KEY:
        answer = await generate_conversational_answer(message, best)
    else:
        answer = str(best["answer"])

    return ChatResponse(answer=answer, matched=True, matched_question=str(best["question"]))
