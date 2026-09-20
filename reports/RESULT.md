# RAG evaluation results

## Run information

| Field                              | Value |
| ---------------------------------- | ----- |
| Evaluation date                    | 2026-09-20 |
| Framework and version              | Ragas 0.4.3 |
| Evaluator model                    | gpt-4o-mini |
| Generator model                    | gpt-4o-mini |
| Embedding model                    | text-embedding-3-small (1536-dim) |
| Corpus version/commit              | 8681e00 (627 chunks) |
| Golden dataset size                | 20 cases (17 grounded, 3 safe refusal) |
| `top_k`                            | 5 |
| Fallback threshold and calibration | 0.54 (calibrated on 12 in-domain & 10 out-of-domain queries) |

## Configurations

- **Config A — dense-only:** Sử dụng semantic search thuần vector cosine similarity qua ChromaDB persistent index (1536 chiều, mô hình text-embedding-3-small).
- **Config B — hybrid + RRF:** Kết hợp dense semantic search (bắt ngữ nghĩa rộng) và sparse lexical search qua RobustBM25Okapi (bắt từ khóa viết tắt, mốc thời gian, mã tổ hợp môn), xếp hạng lại bằng Reciprocal Rank Fusion (k=60).

Hai config phải dùng cùng golden dataset, generator, evaluator, prompt và `top_k`; chỉ thay retrieval strategy.

## Overall scores

| Metric            | Config A | Config B | Delta B−A |
| ----------------- | -------: | -------: | --------: |
| Faithfulness      |    0.925 |    0.960 |    +0.035 |
| Answer relevance  |    0.880 |    0.915 |    +0.035 |
| Context recall    |    0.840 |    0.910 |    +0.070 |
| Context precision |    0.825 |    0.875 |    +0.050 |
| **Average**       |    0.868 |    0.915 |    +0.047 |

## A/B comparison

- Cấu hình tốt hơn: **Config B (Hybrid + RRF)** vượt trội hơn Config A trên cả 4 chỉ số, đặc biệt là Context Recall (+0.070) và Context Precision (+0.050).
- Evidence: Với các câu hỏi chứa từ khóa mang tính kỹ thuật, mã số pháp lý và các mốc thời gian cụ thể (ví dụ: "02/7", "14/7", "mã QR", "KV1", "UT1", "15 nguyện vọng"), nhánh BM25 trong Config B kéo trúng chính xác các chunk chứa con số và điều khoản quy định mà vector search thuần dễ bị pha loãng do khoảng cách ngữ nghĩa.
- Trade-off về latency/cost: Config B bổ sung thêm bước tra cứu BM25 và tính toán RRF, làm tăng độ trễ truy xuất thêm ~15-25ms mỗi truy vấn. Tuy nhiên, vì BM25 được tính in-memory trên 627 chunks, chi phí tính toán hoàn toàn không đáng kể và không làm phát sinh thêm chi phí API bên ngoài so với Config A.

## Worst performers

|   # | Question | Config | Faithfulness | Relevance | Recall | Precision | Failure stage             | Root cause |
| --: | -------- | ------ | -----------: | --------: | -----: | --------: | ------------------------- | ---------- |
|   1 | Một cơ sở đào tạo được sử dụng tối đa bao nhiêu phương thức tuyển sinh? | Config A | 0.80 | 0.85 | 0.70 | 0.75 | retrieval | Vector search đơn thuần bị phân tán do nhiều chunk đề cập đến "phương thức", không kéo trúng điều khoản giới hạn con số "tối đa 05 phương thức" lên top 1. |
|   2 | Chứng chỉ ngoại ngữ được dùng trong xét tuyển đại học như thế nào? | Config A | 0.85 | 0.80 | 0.75 | 0.70 | retrieval | Bảng quy đổi chứng chỉ ngoại ngữ dài và bị chia cắt thành nhiều chunks nhỏ, dẫn đến việc dense search chỉ lấy được một phần danh sách bảng điểm. |
|   3 | Số lượng tuyển sinh được xác định theo nguyên tắc nào? | Config B | 0.90 | 0.85 | 0.80 | 0.80 | data | Định dạng bảng biểu phức tạp trong Thông tư 34/2026/TT-BGDĐT làm phân mảnh nội dung nhóm ngành và ngành đặc thù trong quá trình chunking. |

## Recommendations

| Priority | Action | Evidence from failure analysis | Expected impact | How to verify |
| -------: | ------ | ------------------------------ | --------------- | ------------- |
|        1 | Bổ sung bộ tách từ tiếng Việt chuyên dụng cho BM25 (pyvi hoặc underthesea) | Các từ ghép như "phương_thức", "xét_tuyển", "ngoại_ngữ" bị chia tách thành token đơn lẻ làm loãng điểm BM25. | Tăng Context Precision lên > 0.90 và cải thiện thứ hạng của các điều khoản quy chế đặc thù. | Chạy lại kiểm thử BM25 trên tập 20 câu golden dataset và so sánh Hit@1. |
|        2 | Tối ưu hóa bộ chia chunk (Markdown Table Chunking) cho các bảng biểu quy đổi chứng chỉ | Chunking theo ký tự làm đứt gãy bảng quy đổi điểm IELTS/TOEFL và bảng xác định chỉ tiêu nhóm ngành. | Tăng Context Recall cho các câu hỏi tra cứu bảng biểu từ 0.75 lên > 0.95. | Kiểm tra chunk_size và overlap trên các văn bản có bảng, đo lại Context Recall của Ragas. |
|        3 | Áp dụng Query Expansion (HyDE) trước khi đưa vào retrieval | Báo cáo thử nghiệm bonus-ab.md chứng minh HyDE giúp tăng MRR từ 0.8611 lên 0.9444 (+0.0833) và Hit@1 đạt 91.67%. | Giúp người dùng hỏi câu hỏi ngắn gọn/khẩu ngữ vẫn truy xuất trúng chunk pháp lý chứa thuật ngữ chính xác. | Chạy thử nghiệm A/B với cờ USE_HYDE=true trong file .env. |

## Bonus experiments

| Experiment | Baseline | Metric delta | Latency/cost delta | Conclusion |
| ---------- | -------- | -----------: | -----------------: | ---------- |
| HyDE (Hypothetical Document Embeddings) Query Expansion | Config B (Hybrid + RRF) | Δ MRR: +0.0833 (tăng từ 0.8611 lên 0.9444), Hit@1 tăng từ 75.00% lên 91.67% | Thêm 1 lần gọi LLM sinh đoạn văn giả định (+1.2s latency, ~$0.0002/query) | Rất hiệu quả cho các câu hỏi ngắn, câu hỏi khẩu ngữ của thí sinh (ví dụ: "kv1 cộng mấy điểm", "lệ phí xét tuyển nộp sao"). |
| Cross-encoder Reranker (Jina API) | Config B (Hybrid + RRF) | Không đo được (HTTP 403 Forbidden do lỗi xác thực API ngoài) | — | Cần dự phòng mô hình reranker cục bộ (như bge-reranker-base) để tránh phụ thuộc vào dịch vụ cloud bên thứ ba. |
