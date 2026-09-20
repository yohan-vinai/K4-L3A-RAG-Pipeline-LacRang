"""Integrity and provenance checks for the golden admissions Q&A dataset."""

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).parent.parent
DATASET_PATH = ROOT / "group_project" / "evaluation" / "golden_dataset.json"
NOTES_PATH = ROOT / "group_project" / "evaluation" / "GOLDEN_DATASET_NOTES.md"
REQUIRED_FIELDS = {
    "id",
    "question",
    "expected_answer",
    "expected_context",
    "question_source",
    "answer_sources",
    "difficulty",
    "case_type",
    "note",
}
REQUIRED_SOURCE_FIELDS = {"source_id", "path", "title", "locator", "url"}


def load_dataset() -> list[dict]:
    return json.loads(DATASET_PATH.read_text(encoding="utf-8"))


def test_dataset_has_at_least_twenty_unique_complete_cases():
    dataset = load_dataset()
    assert len(dataset) >= 20
    assert len({item["id"] for item in dataset}) == len(dataset)
    assert len({item["question"] for item in dataset}) == len(dataset)

    for item in dataset:
        assert REQUIRED_FIELDS <= item.keys()
        for field in REQUIRED_FIELDS - {"answer_sources"}:
            assert str(item[field]).strip(), f"{item.get('id')} has an empty {field}"
        assert item["difficulty"] in {"easy", "medium", "hard"}
        assert item["answer_sources"], f"{item['id']} has no answer source"


def test_every_question_and_answer_source_resolves_to_the_corpus():
    for item in load_dataset():
        question_path = item["question_source"].split("#", 1)[0]
        assert (ROOT / question_path).is_file(), f"Missing question source for {item['id']}"

        for source in item["answer_sources"]:
            assert REQUIRED_SOURCE_FIELDS <= source.keys()
            assert all(str(source[field]).strip() for field in REQUIRED_SOURCE_FIELDS)
            source_path = ROOT / source["path"]
            assert source_path.is_file(), f"Missing answer source for {item['id']}: {source_path}"
            source_text = source_path.read_text(encoding="utf-8")
            assert source["url"] in source_text, f"Source URL mismatch for {item['id']}"


def test_dataset_includes_difficult_and_multi_source_cases():
    dataset = load_dataset()
    difficulties = Counter(item["difficulty"] for item in dataset)
    assert difficulties["hard"] >= 5
    assert sum(len(item["answer_sources"]) >= 2 for item in dataset) >= 5
    assert {"draft_vs_final", "transitional_rule", "scope_disambiguation"} <= {
        item["case_type"] for item in dataset
    }


def test_notes_document_the_known_source_conflicts():
    notes = NOTES_PATH.read_text(encoding="utf-8")
    for case_id in ("GQ-001", "GQ-008", "GQ-016", "GQ-021", "GQ-022", "GQ-023"):
        assert case_id in notes
    assert "văn bản pháp lý chính thức" in notes
    assert "điều khoản chuyển tiếp" in notes
