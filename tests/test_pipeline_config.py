import pytest

from src.pipeline_config import PipelineConfig


def test_pipeline_config_merges_defaults_and_validates_types():
    config = PipelineConfig.from_payload(
        {"strategy": "bm25", "top_k": 3, "temperature": 0.0}
    )
    assert config.strategy == "bm25"
    assert config.top_k == 3
    assert config.temperature == 0.0
    assert config.rrf_k >= 1


@pytest.mark.parametrize(
    "payload",
    [
        {"strategy": "unknown"},
        {"top_k": True},
        {"score_threshold": 1.1},
        {"rrf_k": 0},
        {"provider": "local"},
        {"temperature": "0.3"},
        {"unexpected": 1},
    ],
)
def test_pipeline_config_rejects_invalid_payload(payload):
    with pytest.raises(ValueError):
        PipelineConfig.from_payload(payload)
