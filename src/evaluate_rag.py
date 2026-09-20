"""Run the grounded golden set against dense-only and hybrid retrieval.

The script deliberately writes raw per-question scores to JSON.  Fill RESULT.md
only after a successful run, so the report never contains invented metrics.
"""

import asyncio
import io
import json
import os
import sys
from pathlib import Path
from statistics import mean

if sys.platform == "win32" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from dotenv import load_dotenv

from .task10_generation import (
    SAFE_REFUSAL,
    SYSTEM_PROMPT,
    call_llm,
    format_context,
    generate_with_citation,
    reorder_for_llm,
)
from .task5_semantic_search import semantic_search


load_dotenv()

ROOT = Path(__file__).parent.parent
GOLDEN_DATASET = ROOT / "group_project" / "evaluation" / "golden_dataset.json"
OUTPUT_PATH = ROOT / "group_project" / "evaluation" / "evaluation_results.json"
TOP_K = 5


def dense_only_generation(query: str, top_k: int) -> dict:
    """Generate an answer from dense retrieval alone for the A/B baseline."""
    chunks = semantic_search(query, top_k=top_k)
    if not chunks:
        return {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}

    prompt = (
        f"Context:\n{format_context(reorder_for_llm(chunks))}\n\nQuestion: {query}\n\n"
        "Trả lời bằng tiếng Việt. Với mỗi thông tin thực tế, hãy ghi citation "
        "dạng [Document N] tương ứng với context."
    )
    try:
        answer = call_llm(SYSTEM_PROMPT, prompt)
    except Exception:
        return {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}
    if not answer:
        return {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}
    return {"answer": answer, "sources": chunks, "retrieval_source": "hybrid"}


def make_evaluator_llm():
    """Create the Ragas judge LLM from the configured OpenAI/Anthropic client."""
    from ragas.llms import llm_factory

    provider = os.getenv("LLM_PROVIDER", "openai").lower()
    model = os.getenv("EVALUATOR_MODEL") or os.getenv("LLM_MODEL")
    if not model:
        raise ValueError("Set LLM_MODEL or EVALUATOR_MODEL before running evaluation")

    if provider == "openai":
        from openai import AsyncOpenAI

        return llm_factory(model, client=AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"]))
    if provider == "anthropic":
        from anthropic import AsyncAnthropic

        return llm_factory(
            model,
            provider="anthropic",
            client=AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"]),
        )
    raise ValueError(
        "Evaluation currently supports LLM_PROVIDER=openai or anthropic; "
        "configure one of them for the Ragas judge."
    )


def make_evaluator_embeddings():
    """Create evaluator embeddings for Ragas AnswerRelevancy metric."""
    from openai import AsyncOpenAI
    from ragas.embeddings import OpenAIEmbeddings

    model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY must be set for evaluation embeddings")
    return OpenAIEmbeddings(model=model, client=AsyncOpenAI(api_key=api_key))


async def score_case(metrics: dict, case: dict, generated: dict) -> dict:
    """Score one grounded case with the four required Ragas metrics."""
    contexts = [source["content"] for source in generated["sources"]]
    user_input = case["question"]
    response = generated["answer"]
    reference = case["expected_answer"]

    faithfulness = await metrics["faithfulness"].ascore(
        user_input=user_input, response=response, retrieved_contexts=contexts
    )
    relevance = await metrics["answer_relevance"].ascore(
        user_input=user_input, response=response
    )
    precision = await metrics["context_precision"].ascore(
        user_input=user_input, reference=reference, retrieved_contexts=contexts
    )
    recall = await metrics["context_recall"].ascore(
        user_input=user_input, retrieved_contexts=contexts, reference=reference
    )
    return {
        "faithfulness": faithfulness.value,
        "answer_relevance": relevance.value,
        "context_precision": precision.value,
        "context_recall": recall.value,
    }


async def run_configuration(name: str, cases: list[dict], metrics: dict) -> dict:
    """Run a single retrieval configuration and retain evidence for review."""
    rows = []
    for index, case in enumerate(cases, 1):
        print(f"[{name}] Scoring case {index}/{len(cases)}", flush=True)
        generated = (
            dense_only_generation(case["question"], TOP_K)
            if name == "dense_only"
            else generate_with_citation(case["question"], TOP_K)
        )
        scores = await score_case(metrics, case, generated)
        rows.append(
            {
                "question": case["question"],
                "expected_answer": case["expected_answer"],
                "answer": generated["answer"],
                "source_ids": [source["id"] for source in generated["sources"]],
                "scores": scores,
            }
        )

    metric_names = tuple(metrics)
    return {
        "rows": rows,
        "overall_scores": {
            metric: mean(row["scores"][metric] for row in rows) for metric in metric_names
        },
    }


async def run_evaluation() -> None:
    """Run the fair A/B comparison and write reproducible raw results."""
    from ragas.metrics.collections import (
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
        Faithfulness,
    )

    dataset = json.loads(GOLDEN_DATASET.read_text(encoding="utf-8"))
    grounded_cases = [case for case in dataset if not case["expected_answer"].startswith(SAFE_REFUSAL)]
    if not grounded_cases:
        raise ValueError("Golden dataset has no grounded cases to evaluate")

    evaluator_llm = make_evaluator_llm()
    evaluator_embeddings = make_evaluator_embeddings()
    metrics = {
        "faithfulness": Faithfulness(llm=evaluator_llm),
        "answer_relevance": AnswerRelevancy(llm=evaluator_llm, embeddings=evaluator_embeddings),
        "context_precision": ContextPrecision(llm=evaluator_llm),
        "context_recall": ContextRecall(llm=evaluator_llm),
    }
    results = {
        "dataset_size": len(dataset),
        "grounded_case_count": len(grounded_cases),
        "top_k": TOP_K,
        "config_a_dense_only": await run_configuration("dense_only", grounded_cases, metrics),
        "config_b_hybrid_rrf": await run_configuration("hybrid_rrf", grounded_cases, metrics),
    }
    OUTPUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved evaluation results to {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(run_evaluation())
