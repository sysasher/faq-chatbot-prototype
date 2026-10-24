"""Unit tests for FAQ retrieval and out-of-scope handling."""

from main import fallback_answer, retrieve_faqs, tokenize

SAMPLE_FAQS = [
    {"question": "How do I reset my password?", "answer": "Use Forgot password on the sign-in page."},
    {"question": "What are your business hours?", "answer": "Monday to Friday, 9 AM to 5 PM."},
]


def test_tokenize_removes_common_words():
    # Common filler words should not dominate relevance matching.
    assert tokenize("How do I reset my password?") == {"reset", "password"}


def test_retrieval_finds_password_faq():
    # The core terms should rank the password FAQ first.
    results = retrieve_faqs("reset password", SAMPLE_FAQS)
    assert results
    assert results[0]["question"] == "How do I reset my password?"
    assert results[0]["coverage"] == 1.0


def test_unrelated_question_has_no_matches():
    # A question about an unrelated topic should not retrieve these FAQs.
    assert retrieve_faqs("Where is the nearest airport?", SAMPLE_FAQS) == []


def test_fallback_mentions_support_address():
    # The fallback should tell customers where to get human assistance.
    assert "support@example.com" in fallback_answer()


def test_partial_overlap_below_threshold_has_no_matches():
    # A single shared word that covers little of a longer FAQ question should not count as a match.
    faqs = [{"question": "How do I cancel my subscription plan?", "answer": "Open Billing settings."}]
    assert retrieve_faqs("subscription", faqs) == []
