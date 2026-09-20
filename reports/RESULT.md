# Kết quả đánh giá hệ thống RAG

## Thông tin lần chạy

| Hạng mục | Giá trị |
| --- | --- |
| Ngày chạy | 20-09-2026 (sinh câu trả lời 21:33–21:35; chấm điểm hoàn tất 21:47, giờ Việt Nam) |
| Golden dataset | 24 câu hỏi bám corpus, từ `GQ-001` đến `GQ-024` |
| Model sinh câu trả lời / temperature | `gpt-4o-mini` / `0.0` |
| Bộ đánh giá | Ragas `0.4.3` với `gpt-4o-mini` |
| Model embedding | `text-embedding-3-small` |
| Corpus | Chroma index gồm 627 chunks; working tree dựa trên commit `9bf3bfb` |
| Thiết lập retrieval dùng chung | `top_k=5`, `score_threshold=0.30` |
| Thiết lập fallback | Tắt PageIndex, HyDE và reranking ở cả hai cấu hình |
| Evidence thô | `group_project/evaluation/artifacts/golden-benchmark-20260920T143353Z.raw.json` |
| Evidence đã chấm | `group_project/evaluation/artifacts/golden-benchmark-20260920T143353Z.scored.json` |

Hai lần chạy dùng cùng golden dataset, generator, evaluator, prompt, `top_k`, threshold,
model embedding và fallback. Biến duy nhất được thay đổi là chiến lược retrieval.

| Cấu hình | Chiến lược retrieval |
| --- | --- |
| A — dense-only | Embedding câu hỏi bằng OpenAI + Chroma cosine retrieval |
| B — hybrid + RRF | Dense retrieval + BM25, hợp nhất bằng Reciprocal Rank Fusion (`rrf_k=60`) |

Raw trace ghi nhận đủ 24 câu hoàn tất ở mỗi cấu hình, không có lỗi retrieval hay sinh
câu trả lời. Config A có 120 dense source hits và Config B có 120 hybrid source hits
(năm chunks được lấy cho mỗi câu).

## Điểm tổng hợp (Overall scores)

| Metric | Config A: dense-only | Config B: hybrid + RRF | Chênh lệch B − A |
| --- | ---: | ---: | ---: |
| Faithfulness | 0.8090 | 0.8229 | +0.0139 |
| Answer relevance | 0.4999 | 0.4896 | -0.0103 |
| Context recall | 0.7847 | 0.8264 | +0.0417 |
| Context precision | 0.8390 | 0.9042 | +0.0652 |
| Trung bình bốn metric | 0.7332 | 0.7608 | +0.0276 |

## So sánh A/B (A/B comparison)

Hybrid + RRF là retrieval mặc định được chọn cho corpus này: nó tăng độ bao phủ bằng
chứng và giảm nhiễu retrieval, đồng thời cải thiện nhẹ faithfulness. Answer relevance
giảm nhẹ, vì vậy đây không phải thắng lợi tuyệt đối; các câu cần nhiều điều kiện hoặc
nhiều mốc thời gian vẫn phải được kiểm tra ở cấp từng case.

Sinh câu trả lời cho toàn bộ 48 lượt chạy mất khoảng 93 giây. Ragas hoàn tất chấm điểm
khoảng 12 phút sau đó. Artifact không lưu latency hoặc token cost theo từng cấu hình,
nên thí nghiệm này không kết luận cấu hình nào nhanh hơn hoặc rẻ hơn.

## Ba case kém nhất và phân tích lỗi (Worst performers)

| Case / config | Faithfulness | Relevance | Recall | Precision | Tầng lỗi và nguyên nhân quan sát được |
| --- | ---: | ---: | ---: | ---: | --- |
| `GQ-022` / hybrid + RRF | 0.5000 | 0.0000 | 0.0000 | 0.8667 | Retrieval → generation. Corpus có quy định chuyển tiếp quyết định: năm 2026 vẫn theo `TT03/2022` và `TT10/2023` đã sửa đổi, còn một số phần của `TT34/2026` áp dụng từ 2027. Top 5 chunk đúng chủ đề nhưng thiếu phần tiếp nối then chốt tại Điều 9.2 và Điều 10.2–10.3, nên câu trả lời đã kết luận sai rằng cơ chế mới đã áp dụng. Precision cao chỉ nghĩa là các chunk đúng chủ đề, không có nghĩa chúng đủ bằng chứng. |
| `GQ-018` / dense-only | 1.0000 | 0.3957 | 0.0000 | 0.3667 | Retrieval. Yêu cầu đúng là lưu dữ liệu liên tục bốn năm và có thời điểm cập nhật. Dense retrieval lại lấy quy định cũ, không liên quan về “tối thiểu 10 ngày”, rồi câu trả lời bám sát context sai đó. Case này cho thấy faithfulness cao không tự chứng minh câu trả lời đúng. |
| `GQ-024` / dense-only | 0.7500 | 0.3463 | 0.5000 | 0.7500 | Độ bao phủ retrieval. Câu trả lời chỉ lấy được hotline thứ nhất (`1800 8000`, nhánh 2), nhưng thiếu kênh liên hệ thứ hai (`18001096`, cổng thanh toán). Câu hỏi cần bao phủ nhiều fact, không chỉ lấy một chunk phù hợp nhất. |

Một outlier khác của evaluator là `GQ-006` với hybrid + RRF. Context được lấy và câu
trả lời tạo ra khớp thời điểm trong expected answer, nhưng Ragas vẫn chấm faithfulness
0.5000 và answer relevance 0.4720. Case này cần được review thủ công trước khi xem
điểm thấp là lỗi sản phẩm.

## Khuyến nghị và cách kiểm tra lại (Recommendations)

1. Chunk và index lại văn bản pháp lý kèm metadata section, article, clause; tăng trọng
   số cho Điều 9/10 với truy vấn về điều khoản chuyển tiếp. Chạy lại `GQ-022` và kiểm
   tra top 5 context có Điều 9.2 cùng Điều 10.2–10.3, đồng thời context recall lớn hơn 0.
2. Thêm kiểm tra retrieval cho câu hỏi nhiều điều kiện: tách các câu như `GQ-024` và
   `GQ-021` thành những fact bắt buộc, rồi xác nhận context lấy được đủ hotline, mốc
   thời gian và điều kiện áp dụng trước khi generation. Chạy lại chính các golden case
   này và kiểm tra facet bị thiếu trong raw trace.
3. Thêm guard khi thiếu bằng chứng quyết định. Nếu context không có điều khoản chuyển
   tiếp được hỏi, câu trả lời phải nêu thiếu bằng chứng thay vì suy diễn một quy định
   mới. Kiểm tra lại `GQ-022` để bảo đảm không còn claim không được hỗ trợ.
4. Dùng Ragas như tín hiệu thay vì kết luận cuối cùng; review thủ công các outlier như
   `GQ-006` và case lấy sai context như `GQ-018`. Điểm gần 1 phản ánh mức đồng ý với
   định nghĩa metric của evaluator, không tự đảm bảo tính đúng đắn pháp lý hay thực tế.

## Giới hạn và trạng thái bonus

Lần chạy này chỉ so sánh dense-only với hybrid + RRF. Chưa đo PageIndex, HyDE,
reranking, latency theo cấu hình hoặc chi phí theo cấu hình. Cần chạy các biến thể đó
trên cùng golden set trước khi có thể nói chúng cải thiện hệ thống. Report không claim
bất kỳ bonus experiment nào.
