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

from .task9_retrieval_pipeline import retrieve


load_dotenv()

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_MODEL = os.getenv("LLM_MODEL", "")

SAFE_REFUSAL = (
    "Tôi không thể xác minh thông tin này từ nguồn tài liệu tuyển sinh hiện có."
)

SYSTEM_PROMPT = """Trả lời chỉ từ context được cung cấp.
Mỗi khẳng định phải có citation. Nếu thiếu evidence, hãy từ chối xác minh."""


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Đưa chunks quan trọng về đầu và cuối context."""
    if len(chunks) <= 2:
        return list(chunks)

    # Keep the highest-ranked item first, then move alternating lower-ranked
    # chunks to the end. This mitigates the LLM "lost in the middle" effect
    # without mutating the retrieval results or their stable IDs.
    return list(chunks[::2]) + list(chunks[1::2])[::-1]


def format_context(chunks: list[dict]) -> str:
    """Tạo context có title và source label."""
    parts: list[str] = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk["metadata"]
        parts.append(
            f"[Document {index} | ID: {chunk['id']} | "
            f"Title: {metadata['title']} | Source: {metadata['source']}]\n"
            f"{chunk['content']}"
        )
    return "\n\n---\n\n".join(parts)


def call_llm(system_prompt: str, user_message: str) -> str:
    """Gọi OpenAI, Gemini hoặc Anthropic theo cấu hình."""
    provider = LLM_PROVIDER.strip().lower()
    model = LLM_MODEL.strip()
    if not model:
        raise ValueError("LLM_MODEL must be configured in .env")

    if provider == "openai":
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY must be configured in .env")
        response = OpenAI(api_key=api_key).chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        return (response.choices[0].message.content or "").strip()

    if provider == "gemini":
        from google import genai
        from google.genai import types

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY must be configured in .env")
        response = genai.Client(api_key=api_key).models.generate_content(
            model=model,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=TEMPERATURE,
                top_p=TOP_P,
            ),
        )
        return (response.text or "").strip()

    if provider == "anthropic":
        from anthropic import Anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY must be configured in .env")
        response = Anthropic(api_key=api_key).messages.create(
            model=model,
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        return "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        ).strip()

    raise ValueError(f"Unsupported LLM_PROVIDER: {LLM_PROVIDER}")


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Trả về GenerationResult."""
    try:
        chunks = retrieve(query, top_k=top_k)
    except Exception:
        chunks = []

    if not chunks:
        return {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}

    context = format_context(reorder_for_llm(chunks))
    user_message = (
        f"Context:\n{context}\n\nQuestion: {query}\n\n"
        "Trả lời bằng tiếng Việt. Với mỗi thông tin thực tế, hãy ghi citation "
        "dạng [Document N] tương ứng với context."
    )
    try:
        answer = call_llm(SYSTEM_PROMPT, user_message)
    except Exception:
        return {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}

    if not answer:
        return {"answer": SAFE_REFUSAL, "sources": [], "retrieval_source": "none"}

    retrieval_source = chunks[0].get("retrieval_method")
    if retrieval_source not in {"hybrid", "pageindex"}:
        retrieval_source = "hybrid"
    return {
        "answer": answer,
        "sources": chunks,
        "retrieval_source": retrieval_source,
    }


if __name__ == "__main__":
    print(generate_with_citation("Thí sinh khu vực 1 được cộng bao nhiêu điểm ưu tiên?"))
