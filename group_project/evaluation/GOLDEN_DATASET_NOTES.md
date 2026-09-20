# Golden Dataset Notes

## Phạm vi

- Dataset chính: `golden_dataset.json`
- Số lượng: 24 câu hỏi - trả lời, mã từ `GQ-001` đến `GQ-024`
- Nguồn: 3 văn bản pháp lý và 5 bài viết đã chuẩn hóa trong `data/standardized/`
- Mỗi mẫu ghi riêng nguồn hình thành câu hỏi (`question_source`) và một hoặc nhiều nguồn dùng để xác lập câu trả lời (`answer_sources`).
- `expected_context` mô tả bằng chứng mà retriever nên tìm thấy; `note` ghi bẫy diễn giải hoặc ranh giới phạm vi.

## Phân bố

| Nhóm | Số câu |
|---|---:|
| Easy | 8 |
| Medium | 10 |
| Hard | 6 |
| Dùng từ hai nguồn trả lời trở lên | 7 |

Dataset bao phủ mốc tuyển sinh 2026, nguyện vọng, lệ phí, ưu tiên, điểm học bạ, phương thức xét tuyển, chứng chỉ ngoại ngữ, bảo lưu, công khai dữ liệu tuyển sinh, quy tắc chỉ tiêu và phạm vi áp dụng của quy chế ĐHQGHN.

## Các case khó cần giữ nguyên khi đánh giá

| ID | Vấn đề | Cách xác lập đáp án |
|---|---|---|
| `GQ-001` | Cùng bài tổng hợp có số 16 điểm ở phần dự thảo, trong khi quy chế chính thức chốt 15 điểm. | Ưu tiên Thông tư 06/2026/TT-BGDĐT đã ban hành; coi 16 điểm là thông tin dự thảo cũ. |
| `GQ-008` | Hướng dẫn thanh toán 2026 nói nhóm xét bằng điểm thi THPT phải nộp phí; quy chế diễn đạt nghĩa vụ lệ phí ở mức chung. | Trả lời đúng phạm vi câu hỏi “theo hướng dẫn thanh toán vận hành năm 2026”, đồng thời nêu khác biệt với quy định chung. |
| `GQ-016` | Chứng chỉ ngoại ngữ có thể dùng để quy đổi điểm hoặc làm điểm khuyến khích. | Không cộng đồng thời hai lợi ích cho cùng chứng chỉ; giữ từ “hoặc” của văn bản làm ranh giới. |
| `GQ-021` | Thông tư 34 có hiệu lực trong 2026 nhưng một số mốc dữ liệu mới áp dụng từ 2027. | Tách ngày hiệu lực văn bản khỏi thời điểm bắt đầu áp dụng điều khoản cụ thể. |
| `GQ-022` | Quy tắc chỉ tiêu mới chưa áp dụng toàn bộ ngay cho tuyển sinh 2026. | Dùng điều khoản chuyển tiếp: năm 2026 tiếp tục xác định chỉ tiêu theo Thông tư 03/2022 và Thông tư 10/2023. |
| `GQ-023` | Quyết định 955 là quy chế của ĐHQGHN, còn Thông tư 06 là quy chế tuyển sinh cấp quốc gia. | Không suy rộng quy định nội bộ ĐHQGHN thành quy định cho mọi cơ sở đào tạo. |

## Quy tắc xử lý nguồn khi chấm

1. Ưu tiên văn bản pháp lý chính thức đã ban hành hơn nội dung dự thảo hoặc bài tóm tắt.
2. Không ghép hai phát biểu khác phạm vi thành một kết luận tuyệt đối; câu trả lời phải giữ điều kiện về năm, đối tượng và cơ quan áp dụng.
3. Khi nguồn vận hành cụ thể hóa quy tắc chung, nêu rõ câu trả lời đang theo nguồn nào.
4. Tách ngày văn bản có hiệu lực khỏi ngày một điều khoản bắt đầu được áp dụng.
5. Không chấm đúng chỉ dựa trên con số; câu trả lời phải giữ các ngoại lệ quan trọng nếu câu hỏi yêu cầu.

## Trường dùng trong mỗi mẫu

- `id`: mã ổn định để theo dõi kết quả đánh giá.
- `question`: câu hỏi người dùng có thể đặt.
- `expected_answer`: đáp án chuẩn.
- `expected_context`: nội dung bằng chứng tối thiểu retriever cần trả về.
- `question_source`: đường dẫn corpus và vị trí làm căn cứ tạo câu hỏi.
- `answer_sources`: danh sách nguồn trả lời, gồm ID, đường dẫn, tiêu đề, locator và URL gốc.
- `difficulty`: `easy`, `medium` hoặc `hard`.
- `case_type`: kiểu năng lực hoặc xung đột được kiểm tra.
- `note`: lưu ý để tránh chấm sai ở case khó.
