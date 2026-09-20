"""Pure helpers used by the web admissions assistant UI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from ..contracts import validate_generation_result


ROOT = Path(__file__).resolve().parents[2]
STANDARDIZED = ROOT / "data" / "standardized"
GOLDEN_DATASET = ROOT / "group_project" / "evaluation" / "golden_dataset.json"
EVALUATION_REPORT = ROOT / "group_project" / "evaluation" / "RESULT.md"


def _frontmatter(path: Path) -> dict[str, str]:
    """Read the simple scalar YAML frontmatter used by the corpus."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    metadata: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, separator, value = line.partition(":")
        if separator:
            metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata


def load_corpus_catalog() -> list[dict]:
    """Return actual standardized corpus entries, never prototype counters."""
    catalog: list[dict] = []
    for doc_type in ("legal", "news"):
        directory = STANDARDIZED / doc_type
        for path in sorted(directory.glob("*.md")):
            metadata = _frontmatter(path)
            catalog.append(
                {
                    "title": metadata.get("title") or path.stem.replace("_", " "),
                    "source": metadata.get("source") or path.name,
                    "doc_type": metadata.get("doc_type") or doc_type,
                    "url": metadata.get("url") or None,
                    "publisher": metadata.get("publisher") or "",
                    "document_number": metadata.get("document_number") or "",
                    "path": str(path.relative_to(ROOT)),
                }
            )
    return catalog


def load_evaluation_status() -> dict:
    """Summarize checked-in evaluation artifacts without inventing metrics."""
    try:
        dataset = json.loads(GOLDEN_DATASET.read_text(encoding="utf-8"))
        golden_count = len(dataset) if isinstance(dataset, list) else 0
    except (FileNotFoundError, json.JSONDecodeError):
        golden_count = 0

    try:
        report = EVALUATION_REPORT.read_text(encoding="utf-8")
    except FileNotFoundError:
        report = ""

    todo_count = report.count("TODO")
    return {
        "golden_count": golden_count,
        "todo_count": todo_count,
        "report_ready": bool(report) and todo_count == 0,
    }


def run_generation(
    query: str,
    top_k: int,
    generator: Callable[[str, int], dict],
) -> dict:
    """Call Task 10 and normalize its public result into explicit UI states."""
    try:
        result = generator(query, top_k)
        validate_generation_result(result)
    except NotImplementedError:
        return {
            "status": "unavailable",
            "answer": (
                "Pipeline sinh câu trả lời chưa được thành viên phụ trách hoàn thiện. "
                "Giao diện đã kết nối đúng contract và sẽ hoạt động khi Task 10 sẵn sàng."
            ),
            "sources": [],
            "retrieval_source": "none",
        }
    except Exception as error:
        return {
            "status": "error",
            "answer": "Hệ thống chưa thể hoàn tất truy vấn. Vui lòng thử lại sau.",
            "sources": [],
            "retrieval_source": "none",
            "error_type": type(error).__name__,
        }

    sources = result["sources"]
    retrieval_source = result["retrieval_source"]
    status = "refused" if retrieval_source == "none" or not sources else "answered"
    return {"status": status, **result}


def retrieval_label(method: str) -> str:
    return {
        "dense": "Dense",
        "bm25": "BM25",
        "hybrid": "Hybrid + RRF",
        "pageindex": "PageIndex fallback",
        "none": "Không đủ bằng chứng",
    }.get(method, method or "Không xác định")
