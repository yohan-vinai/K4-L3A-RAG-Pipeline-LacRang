from src.pipeline_config import PipelineConfig


def _result(item_id: str, score: float, method: str) -> dict:
    return {
        "id": item_id,
        "content": "Bằng chứng tuyển sinh",
        "score": score,
        "metadata": {
            "source": "source.md",
            "title": "Nguồn",
            "doc_type": "legal",
            "url": "https://example.com",
            "chunk_index": 0,
        },
        "retrieval_method": method,
    }


def test_configured_retrieval_selects_dense_bm25_and_pageindex(monkeypatch):
    import src.task9_retrieval_pipeline as pipeline

    calls = {"dense": 0, "bm25": 0, "pageindex": 0}

    def dense(query, top_k):
        calls["dense"] += 1
        return [_result("dense-0", 0.9, "dense")]

    def bm25(query, top_k):
        calls["bm25"] += 1
        return [_result("bm25-0", 4.0, "bm25")]

    def pageindex(query, top_k):
        calls["pageindex"] += 1
        return [_result("page-0", 0.95, "pageindex")]

    monkeypatch.setattr(pipeline, "semantic_search", dense)
    monkeypatch.setattr(pipeline, "lexical_search", bm25)
    monkeypatch.setattr(pipeline, "pageindex_search", pageindex)

    dense_output = pipeline.retrieve_configured(
        "query", PipelineConfig(strategy="dense", use_pageindex=False)
    )
    bm25_output = pipeline.retrieve_configured(
        "query", PipelineConfig(strategy="bm25", use_pageindex=False)
    )
    page_output = pipeline.retrieve_configured(
        "query", PipelineConfig(strategy="pageindex")
    )

    assert dense_output[0]["retrieval_method"] == "dense"
    assert bm25_output[0]["retrieval_method"] == "bm25"
    assert page_output[0]["retrieval_method"] == "pageindex"
    assert calls == {"dense": 1, "bm25": 1, "pageindex": 1}


def test_configured_hybrid_passes_custom_rrf_k(monkeypatch):
    import src.task9_retrieval_pipeline as pipeline

    dense = [_result("dense-0", 0.9, "dense")]
    sparse = [_result("bm25-0", 4.0, "bm25")]
    seen = {}
    monkeypatch.setattr(pipeline, "semantic_search", lambda query, top_k: dense)
    monkeypatch.setattr(pipeline, "lexical_search", lambda query, top_k: sparse)

    def fuse(lists, top_k, k):
        seen.update({"lists": lists, "top_k": top_k, "k": k})
        return [_result("hybrid-0", 0.03, "hybrid")]

    monkeypatch.setattr(pipeline, "rerank_rrf", fuse)
    output = pipeline.retrieve_configured(
        "query",
        PipelineConfig(
            strategy="hybrid", rrf_k=42, score_threshold=0.1, use_pageindex=False
        ),
    )
    assert output[0]["retrieval_method"] == "hybrid"
    assert seen["lists"] == [dense, sparse]
    assert seen["k"] == 42


def test_configured_generation_uses_provider_model_temperature_and_style(monkeypatch):
    import src.task10_generation as generation

    sources = [_result("dense-0", 0.9, "dense")]
    captured = {}
    monkeypatch.setattr(generation, "retrieve_configured", lambda query, config: sources)

    def fake_call(system_prompt, user_message, **settings):
        captured.update(settings)
        captured["system_prompt"] = system_prompt
        return "Câu trả lời có căn cứ [1]"

    monkeypatch.setattr(generation, "call_llm_configured", fake_call)
    config = PipelineConfig(
        strategy="dense",
        provider="gemini",
        model="gemini-test",
        temperature=0.1,
        response_style="steps",
    )
    result = generation.generate_with_config("Câu hỏi", config)

    assert result["answer"].endswith("[1]")
    assert captured["provider"] == "gemini"
    assert captured["model"] == "gemini-test"
    assert captured["temperature"] == 0.1
    assert "các bước" in captured["system_prompt"]
