# Individual contribution report

## 1. Thông tin

- Họ và tên: Nguyễn Tiến Tuân
- Mã học viên: 2A202602595
- Nhóm: K4-L3A—LacRang
- Repository/branch: `K4-L3A-RAG-Pipeline-LacRang` / `feat/task7-9-fusion-fallback`

## 2. Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Task 7 — RRF | Lập trình thuật toán giúp kết hợp kết quả tìm kiếm từ nhiều nguồn, sắp xếp lại danh sách sao cho những tài liệu liên quan nhất luôn nằm ở đầu. | `src/task7_reranking.py` · `7436d96` | Done |
| Task 8 — PageIndex fallback | Xây dựng cơ chế tra cứu dự phòng trực tiếp trên tài liệu PDF (dùng PageIndex) khi hệ thống chính không tìm thấy câu trả lời đủ độ tin cậy. Tối ưu tốc độ tra cứu và xử lý lỗi tự động.| `src/task8_pageindex_vectorless.py` · `1cb7321` | Done |
| Task 9 — Pipeline | Ghép nối các phần lại thành một quy trình tra cứu hoàn chỉnh: tìm kiếm $\rightarrow$ tổng hợp kết quả $\rightarrow$ đánh giá độ tin cậy $\rightarrow$ chuyển sang cơ chế dự phòng nếu cần.| `src/task9_retrieval_pipeline.py` · `44f6460` | Done |
| Hiệu chỉnh ngưỡng | Thử nghiệm trên 22 câu hỏi mẫu để tìm ra "ngưỡng độ tin cậy" chuẩn xác nhất ($0.54$), giúp bot phân biệt rõ câu hỏi thuộc chuyên môn và câu hỏi ngoài phạm vi.| `scripts/calibrate_threshold.py` · `reports/threshold-calibration.md` · `f8f350c` | Done |
| Bonus — HyDE | Áp dụng kỹ thuật giả lập câu trả lời để mở rộng câu hỏi gốc, giúp hệ thống tìm kiếm chính xác hơn (chỉ số chính xác tăng thêm 8.33%)| `src/bonus_query_expansion.py` · `reports/bonus-ab.md` | Done |
| Bonus — Reranker | Tích hợp mô hình chấm điểm chuyên sâu để tái sắp xếp kết quả. Đã xác minh hoạt động tốt với tiếng Việt. | `src/task7_reranking.py` · `3106db4` | Hoàn thành một phần (Do hết token jina) |

---

## 3. Các quyết định quan trọng và Lý do

### 1. Chọn ngưỡng an toàn là $0.54$
- **Ý nghĩa đơn giản:** Ngưỡng này giống như "thước đo độ tự tin" của bot. Nếu độ tự tin trên $0.54$, bot sẽ tự trả lời. Nếu dưới $0.54$, bot hiểu rằng đây là câu hỏi ngoài tầm hiểu biết và sẽ chuyển sang tra cứu tài liệu dự phòng hoặc từ chối trả lời.
- **Lý do chọn:** Khi thử nghiệm với câu hỏi ngoài phạm vi như *"Điểm chuẩn Đại học Bách Khoa Paris năm nay bao nhiêu?"*, hệ thống đạt độ tin cậy $0.4630$. Nếu dùng ngưỡng cũ ($0.38$), bot sẽ tưởng mình biết và trả lời sai thành "điểm chuẩn tuyển sinh tại Việt Nam" (hiện tượng "bốc phét/bịa đặt" của AI). Với ngưỡng $0.54$, bot phân biệt chính xác $100\%$ các câu hỏi trong và ngoài phạm vi.
- **Đánh đổi:** Với một số câu hỏi trong phạm vi nhưng có cách diễn đạt quá lạ, bot có thể hơi "cẩn thận quá mức" và tốn thêm khoảng 20 giây để tra cứu tài liệu dự phòng. Tuy nhiên, điều này giúp loại bỏ hoàn toàn rủi ro bot trả lời sai lệch.

### 2. So sánh độ tin cậy bằng "điểm tương đồng thực tế" thay vì "điểm thứ hạng"
- **Ý nghĩa đơn giản:** Điểm tương đồng thực tế đo xem câu hỏi và tài liệu "giống nhau bao nhiêu %" (thường từ $0.6$ đến $0.8$). Trong khi đó, điểm thứ hạng (RRF) chỉ phản ánh vị trí đứng thứ mấy (ví dụ: top 1, top 2) nên điểm rất nhỏ (chỉ khoảng $0.03$).
- **Lý do chọn:** Nếu lấy điểm thứ hạng ($0.03$) đi so sánh với ngưỡng an toàn ($0.54$), hệ thống sẽ luôn nghĩ rằng không có câu trả lời nào tốt, dẫn đến việc luôn bật chế độ dự phòng cho mọi câu hỏi.
- **Đánh đổi:** Cần lưu thêm một danh sách điểm gốc trong bộ nhớ giúp hệ thống hoạt động đúng bản thiết kế ban đầu.

---

## 4. Kết quả kiểm thử và Bài học thực tế

### A. Kết quả chạy thử nghiệm
- **Độ chính xác:** Khi kết hợp kỹ thuật mở rộng câu hỏi (HyDE), tỉ lệ đưa đúng tài liệu chuẩn lên ngay vị trí đầu tiên đạt **91.67%** (tăng cao nhất trong các phương án thử nghiệm).
- **Ví dụ thực tế:**
  - Với câu hỏi: *"Thí sinh khu vực 1 được cộng bao nhiêu điểm ưu tiên?"* $\rightarrow$ Bot tìm đúng ngay đoạn văn bản quy định: *"Mức điểm ưu tiên áp dụng cho khu vực 1 (KV1) là 0,75 điểm…"*
  - Với câu hỏi viết tắt: *"kv1 cộng mấy điểm"* $\rightarrow$ Sau khi kích hoạt kỹ thuật HyDE, bot vẫn tìm đúng tài liệu ở ngay vị trí đầu tiên.
  - Với các câu hỏi vô lý/ngoài phạm vi (như vé máy bay, trường nước ngoài) $\rightarrow$ Bot nhận diện đúng là dưới ngưỡng tin cậy và chuyển sang tra cứu tài liệu dự phòng an toàn.

### B. Các sự cố đã phát hiện và xử lý
1. **Lỗi đọc dữ liệu sai dạng:** Dữ liệu trả về từ bộ tra cứu dự phòng có cấu trúc phức tạp khiến bot bị đọc nhầm thành các đoạn mã rác. Tôi đã viết thêm bộ lọc để làm sạch văn bản trước khi gửi cho bot đọc.
2. **Quá tải khi tra cứu cùng lúc:** Khi tìm kiếm đồng thời trên 3 tệp PDF lớn, hệ thống bị chậm và bị nghẽn mạng do gửi quá nhiều yêu cầu liên tục. Tôi đã chỉnh lại để các tài liệu được tra cứu song song (giảm thời gian chờ từ 55 giây xuống còn ~20 giây) và thêm khoảng nghỉ ngắn giữa các lần gửi.

---

## 5. Hạn chế và Hướng cải tiến

- **Chưa tối ưu việc tách từ tiếng Việt:** Hệ thống tìm kiếm theo từ khóa hiện tại đang cắt từ theo khoảng trắng (ví dụ: "sinh" và "viên" tách rời thay vì ghép lại thành "sinh viên"). Điều này làm kéo theo một số tài liệu không liên quan vào kết quả.
- **Giới hạn tài khoản dịch vụ:** Do tài khoản miễn phí của dịch vụ chấm điểm bị hết dung lượng giữa chừng nên chưa có số liệu đo lường hoàn chỉnh cho phần Reranker.
- **Hướng cải tiến tiếp theo:** Sử dụng bộ tách từ chuyên dụng cho tiếng Việt (như `underthesea` hoặc `pyvi`) và điều chỉnh lại trọng số giữa các bộ tìm kiếm. Đây là cách nhanh nhất để nâng cao chất lượng toàn bộ hệ thống.

---

## 6. Xác nhận

Tôi xác nhận toàn bộ nội dung trên phản ánh đúng thực tế phần việc tôi đã hoàn thành và sẵn sàng trình bày, chạy demo minh họa trong buổi báo cáo.

- **Ngày lập báo cáo:** 20/09/2026
- **Người báo cáo:** Nguyễn Tiến Tuân
