Demo này làm gì
- Bảng điều khiển cho đội CRM/marketing. Tab Khách hàng: hồ sơ khách, nhắc mua lại (kèm chu kỳ mua và cờ "đến hạn" khi đã qua
  80–200 % chu kỳ của chính khách), gợi ý món mới kèm lý do, và màn hình app mà khách sẽ thấy.
- Tab Chiến dịch: chọn loại chiến dịch (nhắc mua lại đến hạn, bán chéo món mới, mở rộng ngành hàng), lọc theo quốc gia và phân
  khúc, xuất danh sách khách kèm món gợi ý và thông điệp ra CSV.
- Nhận lịch sử mua (CSV) của một hoặc nhiều khách, trả về top-K mẫu sản phẩm cho mỗi khách, kèm nguồn và lý do của từng gợi ý.
- Ba nguồn: mua lại (lịch sử của chính khách, giảm dần theo thời gian), mua kèm (láng giềng EASE), xu hướng (độ phổ biến gần đây
  trong ngành hàng khách hay mua). Ba nguồn được trộn bằng hạn ngạch theo thứ hạng, giống bộ trộn ứng viên của pipeline.
- Demo chỉ chạy tầng retrieval với bảng tham chiếu đóng băng tại ngày as-of; nó không chạy các mô hình xếp hạng đã huấn luyện,
  nên không tái hiện độ chính xác bên dưới.

Kết quả offline của pipeline (tập test 2026-02 … 07, TH + VN, Δ = 30 ngày, giao thức không điều kiện)
- Hệ tham chiếu ban đầu: NDCG@20 0,095; 40,7 % anchor không có món nào khách mua trong danh sách ứng viên.
- Retrieval học được (8 nguồn, K = 300): độ phủ món khách mua 0,370 → 0,450; riêng món khám phá 0,307 → 0,400.
- Xếp hạng: GBDT tinh chỉnh 0,101; mô hình sâu một đầu 0,102 (cao nhất, +0,0009 so với GBDT); baseline mạnh nhất TIFU-KNN 0,079.
- So với quy tắc đơn giản (HR@10): gấp 1,8 lần "bán chạy", 1,5 lần "mua lại đúng món cũ".
- Theo loại khách: 79 % trúng trong top 10 khi khách sắp mua lại một món cũ, nhưng chỉ khoảng 10 % khi khách chỉ mua món mới
  (ngang danh sách bán chạy): gợi ý món mới là phần mô hình còn yếu.
- GMV là proxy offline, không phải hiệu quả nhân quả.

Quyền riêng tư
- Mã mẫu sản phẩm là hash có muối; ngành hàng dùng nhãn chung; độ phổ biến hiển thị dạng phần trăm; khách mẫu là dữ liệu tổng hợp.
- File CSV bạn tải lên được xử lý ngay trong trình duyệt, không gửi lên máy chủ.
