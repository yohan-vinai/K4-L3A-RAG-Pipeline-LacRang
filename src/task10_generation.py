"""
Task 10 — Generation có citation.

Hướng dẫn:
    1. Retrieve top-k chunks.
    2. Reorder để giảm lost-in-the-middle.
    3. Format context kèm title và source.
    4. Gọi provider được chọn trong .env.
    5. Trả answer, sources và retrieval_source.

Nếu context không đủ hoặc provider lỗi, trả safe refusal; không bịa thông tin.
"""

import os

from dotenv import load_dotenv

from .pipeline_config import PipelineConfig
from .task9_retrieval_pipeline import retrieve, retrieve_configured


load_dotenv()

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_MODEL = os.getenv("LLM_MODEL", "")

SYSTEM_PROMPT = """Trả lời chỉ từ context được cung cấp.
Mỗi khẳng định phải có citation. Nếu thiếu evidence, hãy từ chối xác minh."""

STYLE_INSTRUCTIONS = {
    "concise": "Trả lời ngắn gọn, đi thẳng vào câu hỏi.",
    "detailed": "Giải thích chi tiết, nêu rõ điều kiện và ngoại lệ quan trọng.",
    "steps": "Trình bày thành các bước hành động rõ ràng, dễ làm theo.",
}


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Đưa chunks quan trọng về đầu và cuối context."""
    if len(chunks) <= 2:
        return list(chunks)
    front = chunks[::2]
    back = chunks[1::2]
    return front + back[::-1]


def format_context(chunks: list[dict]) -> str:
    """Tạo context có title và source label."""
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk["metadata"]
        location = metadata.get("section") or metadata.get("page")
        suffix = f" | Vị trí: {location}" if location not in (None, "") else ""
        parts.append(
            f"[Tài liệu {index} | Tiêu đề: {metadata['title']} | "
            f"Nguồn: {metadata['source']}{suffix}]\n{chunk['content']}"
        )
    return "\n\n---\n\n".join(parts)


def call_llm(system_prompt: str, user_message: str) -> str:
    """Gọi OpenAI, Gemini hoặc Anthropic theo cấu hình."""
    return call_llm_configured(
        system_prompt,
        user_message,
        provider=LLM_PROVIDER,
        model=LLM_MODEL,
        temperature=TEMPERATURE,
    )


def call_llm_configured(
    system_prompt: str,
    user_message: str,
    *,
    provider: str,
    model: str,
    temperature: float,
) -> str:
    """Call one configured provider without mutating process-level settings."""
    if not model:
        raise ValueError("LLM_MODEL chưa được cấu hình")

    if provider == "openai":
        from openai import OpenAI

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=30.0)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature,
        )
        return response.choices[0].message.content or ""

    if provider == "gemini":
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model=model,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
                top_p=TOP_P,
            ),
        )
        return response.text or ""

    if provider == "anthropic":
        import anthropic

        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"), timeout=30.0)
        response = client.messages.create(
            model=model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=temperature,
            top_p=TOP_P,
            max_tokens=1200,
        )
        return "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )

    raise ValueError(f"LLM_PROVIDER không hỗ trợ: {provider}")


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Trả về GenerationResult."""
    chunks = retrieve(query, top_k=top_k)
    if not chunks:
        return _safe_refusal()
    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    user_message = f"Context:\n{context}\n\nCâu hỏi: {query}"
    answer = call_llm(SYSTEM_PROMPT, user_message).strip()
    if not answer:
        return _safe_refusal()
    return _generation_result(answer, chunks)


def generate_with_config(query: str, config: PipelineConfig) -> dict:
    """Generate using fully request-scoped retrieval and LLM settings."""
    chunks = retrieve_configured(query, config)
    if not chunks:
        return _safe_refusal()
    context = format_context(reorder_for_llm(chunks))
    style = STYLE_INSTRUCTIONS[config.response_style]
    system_prompt = f"{SYSTEM_PROMPT}\n{style}"
    user_message = f"Context:\n{context}\n\nCâu hỏi: {query}"
    answer = call_llm_configured(
        system_prompt,
        user_message,
        provider=config.provider,
        model=config.model,
        temperature=config.temperature,
    ).strip()
    if not answer:
        return _safe_refusal()
    return _generation_result(answer, chunks)


def _generation_result(answer: str, chunks: list[dict]) -> dict:
    method = chunks[0]["retrieval_method"]
    retrieval_source = "pageindex" if method == "pageindex" else "hybrid"
    return {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": retrieval_source,
    }


def _safe_refusal() -> dict:
    return {
        "answer": "Tôi không thể xác minh thông tin này từ nguồn tài liệu hiện có.",
        "sources": [],
        "retrieval_source": "none",
    }


if __name__ == "__main__":
    print(generate_with_citation("test query"))
