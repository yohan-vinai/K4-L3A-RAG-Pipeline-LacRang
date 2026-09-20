import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from src.web_server import create_server


def _source():
    return {
        "id": "doc::chunk-0",
        "content": "Bằng chứng kiểm thử",
        "score": 0.91,
        "metadata": {
            "source": "doc.md",
            "title": "Tài liệu kiểm thử",
            "doc_type": "legal",
            "url": "https://example.com/source",
            "chunk_index": 0,
        },
        "retrieval_method": "hybrid",
    }


@pytest.fixture
def api_server():
    def generator(query, top_k):
        return {
            "answer": f"Câu trả lời cho {query} [1]",
            "sources": [_source()],
            "retrieval_source": "hybrid",
        }

    server = create_server(port=0, generator=generator)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def _json(url, *, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=2) as response:
        return response.status, json.loads(response.read())


def test_serves_frontend_health_catalog_and_evaluation(api_server):
    with urlopen(f"{api_server}/", timeout=2) as response:
        html = response.read().decode("utf-8")
        assert response.status == 200
    assert 'id="chatForm"' in html

    status, health = _json(f"{api_server}/api/health")
    assert status == 200
    assert health["status"] == "ok"
    assert health["corpus_sources"] == 8

    _, catalog = _json(f"{api_server}/api/catalog")
    assert catalog["summary"] == {"total": 8, "legal": 3, "news": 5}
    assert len(catalog["sources"]) == 8

    _, evaluation = _json(f"{api_server}/api/evaluation")
    assert isinstance(evaluation["golden_count"], int)
    assert evaluation["golden_count"] >= 0
    assert isinstance(evaluation["report_ready"], bool)


def test_chat_endpoint_uses_public_generation_contract(api_server):
    status, result = _json(
        f"{api_server}/api/chat", payload={"query": "mốc tuyển sinh", "top_k": 5}
    )
    assert status == 200
    assert result["status"] == "answered"
    assert result["retrieval_source"] == "hybrid"
    assert result["sources"][0]["metadata"]["title"] == "Tài liệu kiểm thử"


def test_chat_endpoint_rejects_invalid_input(api_server):
    with pytest.raises(HTTPError) as error:
        _json(f"{api_server}/api/chat", payload={"query": "", "top_k": 5})
    assert error.value.code == 400

    with pytest.raises(HTTPError) as error:
        _json(f"{api_server}/api/chat", payload={"query": "ok", "top_k": 20})
    assert error.value.code == 400
