import httpx
import pytest

GATEWAY_URL = "http://127.0.0.1:8001"
ADMIN_KEY = "admin-key-789"  # admin_tool never degrades, ideal for checking real AI answers

# Each entry: (question, required_keywords_that_must_appear_in_the_answer)
GOLDEN_SET = [
    (
        "how do I reset my password?",
        ["settings", "security", "reset"]
    ),
    (
        "what is your refund policy for damaged goods?",
        ["60 days"]
    ),
    (
        "how long does international shipping take?",
        ["7", "14"]
    ),
    (
        "can I change my delivery address after ordering?",
        ["1 hour"]
    ),
    (
        "what happens when I delete my account?",
        ["14", "grace period"]
    ),
]


def ask(question: str) -> str:
    response = httpx.post(
        f"{GATEWAY_URL}/gateway/answer",
        headers={"x-api-key": ADMIN_KEY},
        json={"question": question, "top_k": 3},
        timeout=15.0
    )
    return response.json()["answer"].lower()


@pytest.mark.parametrize("question,required_keywords", GOLDEN_SET)
def test_answer_contains_required_facts(question, required_keywords):
    answer = ask(question)
    for keyword in required_keywords:
        assert keyword.lower() in answer, (
            f"Expected '{keyword}' in answer to '{question}', but got: {answer}"
        )