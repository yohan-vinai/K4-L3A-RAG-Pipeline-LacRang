"""
Bonus — HyDE / Query Expansion (Nguyễn Tiến Tuân).

Thí sinh hỏi rất ngắn và đầy tiếng lóng: "cntt lấy nhiêu điểm", "kv1 cộng mấy
điểm". Câu ngắn như vậy embed ra vector nghèo nàn, dense search dễ trượt.

HyDE (Hypothetical Document Embeddings) đảo ngược vấn đề: thay vì embed câu
hỏi, sinh ra một đoạn văn *giả định trả lời* câu hỏi đó rồi embed đoạn văn.
Đoạn giả định dùng đúng từ vựng hành chính của văn bản pháp quy ("Điều",
"khoản", "điểm ưu tiên khu vực") nên nằm gần chunk thật hơn trong không gian
vector.

Bản giả định KHÔNG bao giờ được đưa cho người dùng — nó chỉ là vector truy vấn.
Câu trả lời cuối vẫn do Task 10 sinh từ context thật.

Bật bằng USE_HYDE=true trong .env. Mặc định tắt để test và demo không gọi LLM.
"""

import os

from dotenv import load_dotenv


load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
LLM_MODEL = os.getenv("LLM_MODEL") or "gpt-4o-mini"
HYDE_TIMEOUT = float(os.getenv("HYDE_TIMEOUT") or 10.0)

# Giữ ngắn: đoạn giả định chỉ cần đủ từ khoá để kéo vector về đúng vùng.
HYDE_PROMPT = """Bạn là chuyên viên tuyển sinh đại học Việt Nam.
Viết MỘT đoạn văn 2-3 câu trả lời câu hỏi dưới đây theo đúng văn phong văn bản
pháp quy (Thông tư, Quy chế tuyển sinh): dùng các từ như "Điều", "khoản",
"thí sinh", "cơ sở đào tạo", "tổ hợp xét tuyển", "điểm ưu tiên".
Viết như thể đang trích quy chế, không rào đón, không nói "tôi không biết".
Nếu không chắc số liệu thì vẫn viết dạng tổng quát.

Câu hỏi: {query}

Đoạn văn:"""


def _call_llm(
    prompt: str,
    provider: str = LLM_PROVIDER,
    model: str = LLM_MODEL,
) -> str:
    """Gọi LLM theo LLM_PROVIDER. Chỉ dùng cho HyDE, không phải cho generation."""
    if provider == "openai":
        from openai import OpenAI

        client = OpenAI(timeout=HYDE_TIMEOUT)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=200,
        )
        return response.choices[0].message.content or ""

    if provider == "gemini":
        from google import genai

        client = genai.Client()
        return client.models.generate_content(model=model, contents=prompt).text or ""

    if provider == "anthropic":
        import anthropic

        client = anthropic.Anthropic(timeout=HYDE_TIMEOUT)
        message = client.messages.create(
            model=model,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in message.content if block.type == "text")

    raise ValueError(f"LLM_PROVIDER không hỗ trợ: {provider}")


def expand_query(query: str) -> str:
    """Trả về query đã mở rộng bằng HyDE, hoặc query gốc nếu LLM lỗi.

    Nối cả câu hỏi gốc lẫn đoạn giả định: giữ câu gốc để BM25 vẫn bắt được mã
    ngành/khối thi người dùng gõ, thêm đoạn giả định để dense có ngữ cảnh.
    """
    if not query.strip():
        return query
    try:
        hypothetical = _call_llm(HYDE_PROMPT.format(query=query)).strip()
    except Exception as error:
        # LLM lỗi hay hết quota không được làm sập retrieval.
        print(f"[hyde] Bỏ qua mở rộng, dùng query gốc: {type(error).__name__}: {error}")
        return query
    if not hypothetical:
        return query
    return f"{query}\n{hypothetical}"


def expand_query_configured(query: str, provider: str, model: str) -> str:
    """HyDE using request-scoped provider/model without mutating module globals."""
    if not query.strip():
        return query
    try:
        hypothetical = _call_llm(
            HYDE_PROMPT.format(query=query), provider=provider, model=model
        ).strip()
    except Exception as error:
        print(f"[hyde] Bỏ qua mở rộng, dùng query gốc: {type(error).__name__}: {error}")
        return query
    return f"{query}\n{hypothetical}" if hypothetical else query


if __name__ == "__main__":
    import sys

    for raw in sys.argv[1:] or ["cntt lấy nhiêu điểm", "kv1 cộng mấy điểm"]:
        print("=" * 72)
        print("Gốc     :", raw)
        print("Mở rộng :", expand_query(raw).replace("\n", "\n          "))
