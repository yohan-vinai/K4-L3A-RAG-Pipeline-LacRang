"""Validated, request-scoped configuration for the RAG pipeline."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any

from dotenv import load_dotenv


load_dotenv()

STRATEGIES = {"hybrid", "dense", "bm25", "pageindex"}
PROVIDERS = {"openai", "gemini", "anthropic"}
RESPONSE_STYLES = {"concise", "detailed", "steps"}


@dataclass(frozen=True)
class PipelineConfig:
    strategy: str = "hybrid"
    top_k: int = 5
    score_threshold: float = 0.54
    rrf_k: int = 60
    use_pageindex: bool = True
    use_hyde: bool = False
    use_model_rerank: bool = False
    provider: str = "openai"
    model: str = ""
    temperature: float = 0.3
    response_style: str = "concise"
    show_trace: bool = True

    @classmethod
    def defaults(cls) -> "PipelineConfig":
        return cls(
            score_threshold=float(os.getenv("SCORE_THRESHOLD") or 0.54),
            rrf_k=int(os.getenv("RRF_K") or 60),
            use_pageindex=(os.getenv("USE_PAGEINDEX") or "true").lower() == "true",
            use_hyde=(os.getenv("USE_HYDE") or "false").lower() == "true",
            use_model_rerank=(
                os.getenv("USE_MODEL_RERANK") or "false"
            ).lower() == "true",
            provider=(os.getenv("LLM_PROVIDER") or "openai").lower(),
            model=os.getenv("LLM_MODEL") or "",
            temperature=float(os.getenv("TEMPERATURE") or 0.3),
        )

    @classmethod
    def from_payload(cls, payload: object) -> "PipelineConfig":
        if payload is None:
            return cls.defaults()
        if not isinstance(payload, dict):
            raise ValueError("config must be an object")

        defaults = asdict(cls.defaults())
        unknown = set(payload) - set(defaults)
        if unknown:
            raise ValueError(f"unknown config fields: {', '.join(sorted(unknown))}")
        values: dict[str, Any] = {**defaults, **payload}

        if values["strategy"] not in STRATEGIES:
            raise ValueError("strategy must be hybrid, dense, bm25, or pageindex")
        if (
            not isinstance(values["top_k"], int)
            or isinstance(values["top_k"], bool)
            or not 3 <= values["top_k"] <= 10
        ):
            raise ValueError("top_k must be an integer between 3 and 10")
        cls._number_in_range(values, "score_threshold", 0.0, 1.0)
        if (
            not isinstance(values["rrf_k"], int)
            or isinstance(values["rrf_k"], bool)
            or not 1 <= values["rrf_k"] <= 200
        ):
            raise ValueError("rrf_k must be an integer between 1 and 200")
        for key in ("use_pageindex", "use_hyde", "use_model_rerank", "show_trace"):
            if not isinstance(values[key], bool):
                raise ValueError(f"{key} must be boolean")
        if values["provider"] not in PROVIDERS:
            raise ValueError("provider must be openai, gemini, or anthropic")
        if not isinstance(values["model"], str) or len(values["model"].strip()) > 120:
            raise ValueError("model must be a string up to 120 characters")
        values["model"] = values["model"].strip()
        cls._number_in_range(values, "temperature", 0.0, 1.0)
        if values["response_style"] not in RESPONSE_STYLES:
            raise ValueError("response_style must be concise, detailed, or steps")
        return cls(**values)

    @staticmethod
    def _number_in_range(
        values: dict[str, Any], key: str, minimum: float, maximum: float
    ) -> None:
        value = values[key]
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not minimum <= float(value) <= maximum
        ):
            raise ValueError(f"{key} must be between {minimum} and {maximum}")
        values[key] = float(value)

    def public_dict(self) -> dict[str, Any]:
        return asdict(self)


def config_options() -> dict[str, list[str]]:
    return {
        "strategies": sorted(STRATEGIES),
        "providers": sorted(PROVIDERS),
        "response_styles": sorted(RESPONSE_STYLES),
    }
