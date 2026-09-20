from src.ui_support import (
    load_corpus_catalog,
    load_evaluation_status,
    load_golden_questions,
    retrieval_label,
    run_generation,
)


def test_catalog_reflects_the_checked_in_corpus():
    catalog = load_corpus_catalog()
    assert len(catalog) == 8
    assert sum(item["doc_type"] == "legal" for item in catalog) == 3
    assert sum(item["doc_type"] == "news" for item in catalog) == 5
    assert all(item["title"] and item["source"] and item["path"] for item in catalog)
    assert all(item["url"].startswith("https://") for item in catalog)
    assert all(item["chunk_count"] > 0 for item in catalog)
    assert sum(item["chunk_count"] for item in catalog) == 627


def test_generation_success_and_refusal_states_follow_contract():
    source = {
        "id": "doc::chunk-0",
        "content": "Evidence",
        "score": 0.8,
        "metadata": {
            "source": "doc.md",
            "title": "Document",
            "doc_type": "legal",
            "url": "https://example.com",
            "chunk_index": 0,
        },
        "retrieval_method": "hybrid",
    }
    answered = run_generation(
        "question",
        5,
        lambda query, top_k: {
            "answer": "Grounded answer [1]",
            "sources": [source],
            "retrieval_source": "hybrid",
        },
    )
    refused = run_generation(
        "outside scope",
        5,
        lambda query, top_k: {
            "answer": "Không thể xác minh.",
            "sources": [],
            "retrieval_source": "none",
        },
    )
    assert answered["status"] == "answered"
    assert refused["status"] == "refused"


def test_generation_dependency_and_provider_failures_do_not_escape():
    def unfinished(query, top_k):
        raise NotImplementedError

    def failed(query, top_k):
        raise RuntimeError("secret provider detail")

    unavailable = run_generation("question", 5, unfinished)
    error = run_generation("question", 5, failed)
    assert unavailable["status"] == "unavailable"
    assert error["status"] == "error"
    assert "secret provider detail" not in error["answer"]
    assert error["error_type"] == "RuntimeError"


def test_evaluation_and_method_labels_are_truthful():
    status = load_evaluation_status()
    assert isinstance(status["golden_count"], int)
    assert status["golden_count"] >= 0
    assert status["report_ready"] is (status["todo_count"] == 0)
    assert retrieval_label("hybrid") == "Hybrid + RRF"
    assert retrieval_label("pageindex") == "PageIndex fallback"


def test_golden_questions_are_loaded_from_the_checked_in_dataset():
    questions = load_golden_questions()
    assert len(questions) >= 20
    assert questions[0]["id"] == "GQ-001"
    assert all(item["question"].strip() for item in questions)
