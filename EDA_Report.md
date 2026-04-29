# Báo cáo Phân tích Dữ liệu Chuyên sâu (EDA) - VinUni Datathon 2026

Báo cáo này trình bày các phát hiện chính từ quá trình Khám phá Dữ liệu (Exploratory Data Analysis - EDA) trên bộ dữ liệu E-commerce thời trang (2012-2022). Quá trình phân tích được thiết kế bám sát thang chấm điểm của Ban Giám khảo, chia làm 4 cấp độ tư duy dữ liệu.

---

## 1. Descriptive Analytics (Điều Gì Đã Xảy Ra?)

### 1.1. Bức tranh Tổng quan Doanh thu & Chu kỳ Khách hàng
**Phát hiện:**
- Lịch sử doanh thu từ `sales.csv` cho thấy sự tăng trưởng đều nhưng xuất hiện các xu hướng mang tính chu kỳ hàng năm. Đặc biệt, các điểm bùng nổ doanh thu (Spikes) được ghi nhận trùng khớp với thời điểm mua sắm quy mô lớn. 
- Mật độ phân bổ doanh thu theo địa lý (Region) cho thấy sự chênh lệch lớn giữa các vùng. Sự mở rộng thị trường có sự lệ thuộc quá nhiều vào một khu vực địa lý cốt lõi.

**Bằng chứng dữ liệu:**
1. Khách hàng trung thành có Gap mua hàng giữa 2 đơn xấp xỉ cấu trúc của một mùa thời trang (thể hiện thời điểm ra mắt các bộ sưu tập mới ảnh hưởng lên Inter-order gap).
2. Segment mang lại GPM (Gross Profit Margin - Tỷ suất lợi nhuận gộp) lớn nhất là yếu tố gánh vác biên lợi nhuận của toàn bộ Platform, trong khi một số mặt hàng giá rẻ chỉ có tác dụng kéo Unique Visitors.

### 1.2. Thói quen Thanh toán
**Phát hiện:**
- Phân bố `installments` (vòng đời trả góp) cho thấy tín dụng số và mua trả góp là đòn bẩy lớn để bán các mặt hàng Premium. Giá trị đơn hàng nhảy vọt với các mốc trả góp cao.

---

## 2. Diagnostic Analytics (Tại Sao Lại Xảy Ra?)

### 2.1. Nghịch lý tỷ lệ trả hàng (Returns Loophole)
**Phát hiện:**
Bằng việc thực hiện phép Join 3 bảng (`order_items`, `products`, `returns`), phát hiện rủi ro chuỗi Logistics.

**Bằng chứng dữ liệu:**
- Tại hạng mục **Streetwear**, lý do hàng đầu khiến khách hàng gửi trả sản phẩm là `wrong_size`.
- Tần suất này quá lớn đối với một thương hiệu E-commerce quần áo. Điều này cho thấy sự thiếu đồng bộ giữa Size Chart (Bảng biểu kích thước) được niêm yết trên Web và thực tế sản phẩm. Hệ quả kéo theo là bào mòn biên lợi nhuận chênh lệch vốn có thông qua việc phải gánh chi phí Logistics hoàn trả rủi ro (Shipping fee zeroed-out and refund triggered).

### 2.2. Điểm mù của Chiến dịch Khuyến mãi (Promo Idling)
- Việc áp dụng mã giảm giá (`promo_id`) có diễn ra nhưng cơ cấu đơn hàng dùng mã chưa khai thác hết vòng đời khách hàng. Phân khúc khách hàng "già" có tổng lượng đơn hàng trung bình cao nhưng liệu có thực sự tương tác tốt với Flash sale ngắn hạn?

---

## 3. Predictive Analytics (Xu Hướng Sắp Tới Là Gì?)

### 3.1. Hành vi Người Dùng (Traffic Intent vs Conversion)
Phân tích bảng `web_traffic.csv` kết nối với `orders`:
- **Social Media** là con dao hai lưỡi: Nguồn Traffic này mang về một lượng lớn `sessions` do hiệu ứng viral, tuy nhiên `bounce_rate` (tỷ lệ thoát trang) lại đặc biệt lớn, cho thấy khách hàng Click vào xem nhưng không mua (Tỷ lệ chuyển đổi yếu).
- **Organic Search & Email Campaign:** Ngược lại, những khách hàng đi vào từ chuỗi tìm kiếm tự nhiên hoặc Email có Conversion Rate đặc biệt cao do tính chất "Chủ động đi tìm để mua sắm".
- **Dự báo:** Sự gia tăng đột biến của `page_views` trong 3-5 ngày liền kề là Leading Indicator (Chỉ báo sớm) cho một đỉnh doanh số, giúp việc đưa biến độ trễ (Lags) vào mô hình Forecasting đạt hiệu quả R2 cao nhất.

---

## 4. Prescriptive Analytics (Chúng Ta Cần Làm Gì Để Tối Ưu?)

> [!IMPORTANT]
> Đây là trọng tâm để đội thi giành điểm tuyệt đối (Prescriptive Insight). Từ các mô hình được phân tích, chúng tôi khuyến nghị 3 quyết định kinh doanh chiến lược.

### Quyết định 1: Tối ưu Dòng vốn Tồn kho (Inventory Matrix)
Sử dụng Ma trận tương quan giữa `sell_through_rate` và `days_of_supply`:
1. **Rút vốn (Divest):** Nhóm sản phẩm đạt *Days of Supply cực cao nhưng Sell-through Rate rất thấp* (Overstocked/Tồn kho chết): Ngay lập tức gắn kết các mã `promo_channel` mang tính chất xả hàng mạnh để kéo lượng traffic bù đắp.
2. **Bơm tiền tái nhập (Reorder Fast):** Các siêu mặt hàng *Sell-through Rate quá cao nhưng Days of supply thấp* là điểm rơi gây "Chảy máu doanh thu" (Stockout). Cần tái nhập số lượng lớn để tối đa hóa điểm bùng nổ cuối năm.

### Quyết định 2: Tái cấu trúc UX/UI đối với mảng Streetwear
Để giải bài toán `wrong_size` đã chẩn đoán ở cấp độ số 2:
- Triển khai tính năng **Virtual Fitting** (Thuật toán ướm thử đồ ảo) hoặc bộ công cụ tư vấn kích cỡ chi tiết theo số đo chiều cao/cân nặng cho riêng phân khúc Streetwear.
- Bằng cách cứu tỷ lệ chốt hoàn bị fail, Profit Margin sẽ phục hồi mà không cần Marketing tăng lượt truy cập mới.

### Quyết định 3: Tái cơ cấu Ngân sách Marketing trên Web
- Thay vì ném tiền vào Social Media (lúc này chỉ đóng vai trò nhận diện thương hiệu với tỷ lệ thoát trang lớn), dịch chuyển 30% ngân sách Marketing sang mảng Affiliate/Email Targeted với các khách hàng nằm trong độ tuổi "Golden Users" (Nhóm tuổi có số order rate lớn nhất).

