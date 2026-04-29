## ĐỀ THI VÒNG 1

```
**Cuộc thi Khoa học Dữ liệu đầu tiên tại VinUniversity**

```
Biến Dữ liệu thành Giải pháp cho Doanh nghiệp
```

## Contents

- 1 Mô tả Dữ liệu
   - 1.1 Giới thiệu
   - 1.2 Tổng quan các bảng dữ liệu
   - 1.3 Bảng Master
      - 1.3.1 products.csv — Danh mục sản phẩm
      - 1.3.2 customers.csv — Khách hàng
      - 1.3.3 promotions.csv — Chương trình khuyến mãi
      - 1.3.4 geography.csv — Địa lý
   - 1.4 Bảng Transaction
      - 1.4.1 orders.csv — Đơn hàng
      - 1.4.2 order_items.csv — Chi tiết đơn hàng
      - 1.4.3 payments.csv — Thanh toán
      - 1.4.4 shipments.csv — Vận chuyển
      - 1.4.5 returns.csv — Trả hàng
      - 1.4.6 reviews.csv — Đánh giá
   - 1.5 Bảng Analytical
      - 1.5.1 sales.csv — Dữ liệu doanh thu
   - 1.6 Bảng Operational
      - 1.6.1 inventory.csv — Tồn kho
      - 1.6.2 web_traffic.csv — Lưu lượng truy cập
   - 1.7 Quan hệ giữa các bảng
- 2 Đề Bài
   - 2.1 Phần 1 — Câu hỏi Trắc nghiệm
   - 2.2 Phần 2 — Trực quan hoá và Phân tích Dữ liệu
      - 2.2.1 Yêu cầu
   - 2.3 Phần 3 — Mô hình Dự báo Doanh thu (Sales Forecasting)
      - 2.3.1 Bối cảnh kinh doanh
      - 2.3.2 Định nghĩa bài toán
      - 2.3.3 Dữ liệu
      - 2.3.4 Chỉ số đánh giá
      - 2.3.5 Định dạng file nộp
      - 2.3.6 Ràng buộc
- 3 Thang điểm Chấm thi
- 4 Hướng dẫn Nộp bài
   - 4.1 Checklist nộp bài


**Mô tả Dữ liệu**

```
Giới thiệu
```
Bộ dữ liệu mô phỏng hoạt động của một doanh nghiệp thời trang thương mại điện tử tại Việt
Nam trong giai đoạn từ **04/07/2012** đến **31/12/2022**. Dữ liệu bao gồm 15 file CSV, được
chia thành 4 lớp: _Master_ (dữ liệu tham chiếu), _Transaction_ (giao dịch), _Analytical_ (phân tích)
và _Operational_ (vận hành).

```
Phân chia dữ liệu cho bài toán dự báo:
```
- sales_train.csv: 04/07/2012 → 31/12/
- sales_test.csv: 01/01/2023 → 01/07/

```
Tổng quan các bảng dữ liệu

# File Lớp Mô tả
1 products.csv Master Danh mục sản phẩm
2 customers.csv Master Thông tin khách hàng
3 promotions.csv Master Các chiến dịch khuyến mãi
4 geography.csv Master Danh sách mã bưu chính các vùng
5 orders.csv Transaction Thông tin đơn hàng
6 order_items.csv Transaction Chi tiết từng dòng sản phẩm trong đơn
7 payments.csv Transaction Thông tin thanh toán tương ứng 1:1 với đơn hàng
8 shipments.csv Transaction Thông tin vận chuyển
9 returns.csv Transaction Các sản phẩm bị trả lại
10 reviews.csv Transaction Đánh giá sản phẩm sau giao hàng
11 sales.csv Analytical Dữ liệu doanh thu huấn luyện
12 sample_submission.csv Analytical Định dạng file nộp bài (mẫu)
13 inventory.csv Operational Ảnh chụp tồn kho cuối tháng
14 inventory_enhanced.csv Operational Tồn kho mở rộng với các chỉ số dẫn xuất
15 web_traffic.csv Operational Lưu lượng truy cập website hàng ngày

Bảng Master
```
▶ **products.csv — Danh mục sản phẩm**

```
Cột Kiểu Mô tả
product_id int Khoá chính
product_name str Tên sản phẩm
category str Danh mục sản phẩm
segment str Phân khúc thị trường của sản phẩm
size str Kích cỡ sản phẩm
color str Nhãn màu sản phẩm
price float Giá bán lẻ
cogs float Giá vốn hàng bán
```
Ràng buộc: cogs < price với mọi sản phẩm.


▶ **customers.csv — Khách hàng**

```
Cột Kiểu Mô tả
customer_id int Khoá chính
zip int Mã bưu chính (FK → geography.zip)
city str Tên thành phố của khách hàng
signup_date date Ngày đăng ký tài khoản
gender str Giới tính khách hàng (nullable)
age_group str Nhóm tuổi khách hàng (nullable)
acquisition_channel str Kênh tiếp thị khách hàng đăng ký qua (nullable)
```
▶ **promotions.csv — Chương trình khuyến mãi**

```
Cột Kiểu Mô tả
promo_id str Khoá chính
promo_name str Tên chiến dịch kèm năm
promo_type str Loại giảm giá: theo phần trăm hoặc số tiền cố định
discount_value float Giá trị giảm (phần trăm hoặc số tiền tùy promo_type)
start_date date Ngày bắt đầu chiến dịch
end_date date Ngày kết thúc chiến dịch
applicable_category str Danh mục áp dụng, null nếu áp dụng tất cả
promo_channel str Kênh phân phối áp dụng khuyến mãi (nullable)
stackable_flag int Cờ cho phép áp dụng đồng thời nhiều khuyến mãi
min_order_value float Giá trị đơn hàng tối thiểu để áp dụng khuyến mãi (nullable)
```
Công thức giảm giá:

- percentage: discount_amount = quantity× unit_price× (discount_value _/_ 100)
- fixed: discount_amount = quantity× discount_value

▶ **geography.csv — Địa lý**

```
Cột Kiểu Mô tả
zip int Khoá chính (mã bưu chính)
city str Tên thành phố
region str Vùng địa lý
district str Tên quận/huyện
```
```
Bảng Transaction
```
▶ **orders.csv — Đơn hàng**

```
Cột Kiểu Mô tả
order_id int Khoá chính
order_date date Ngày đặt hàng
customer_id int FK → customers.customer_id
zip int Mã bưu chính giao hàng (FK → geography.zip)
order_status str Trạng thái xử lý của đơn hàng
payment_method str Phương thức thanh toán được sử dụng
device_type str Thiết bị khách hàng dùng khi đặt hàng
order_source str Kênh marketing dẫn đến đơn hàng
```

▶ **order_items.csv — Chi tiết đơn hàng**

```
Cột Kiểu Mô tả
order_id int FK → orders.order_id
product_id int FK → products.product_id
quantity int Số lượng sản phẩm đặt mua
unit_price float Đơn giá sau khi áp dụng khuyến mãi
discount_amount float Tổng số tiền giảm giá cho dòng sản phẩm này
promo_id str FK → promotions.promo_id (nullable)
promo_id_2 str FK → promotions.promo_id, khuyến mãi thứ hai (nullable)
```
▶ **payments.csv — Thanh toán**

```
Cột Kiểu Mô tả
order_id int FK → orders.order_id (quan hệ 1:1)
payment_method str Phương thức thanh toán
payment_value float Tổng giá trị thanh toán của đơn hàng
installments int Số kỳ trả góp
```
▶ **shipments.csv — Vận chuyển**

```
Cột Kiểu Mô tả
order_id int FK → orders.order_id
ship_date date Ngày gửi hàng
delivery_date date Ngày giao hàng đến tay khách
shipping_fee float Phí vận chuyển (0 nếu đơn được miễn phí)
```
Chỉ tồn tại cho đơn hàng có trạng thái shipped, delivered hoặc returned.

▶ **returns.csv — Trả hàng**

```
Cột Kiểu Mô tả
return_id str Khoá chính
order_id int FK → orders.order_id
product_id int FK → products.product_id
return_date date Ngày khách gửi trả hàng
return_reason str Lý do trả hàng
return_quantity int Số lượng sản phẩm trả lại
refund_amount float Số tiền hoàn lại cho khách
```
▶ **reviews.csv — Đánh giá**

```
Cột Kiểu Mô tả
review_id str Khoá chính
order_id int FK → orders.order_id
product_id int FK → products.product_id
customer_id int FK → customers.customer_id
review_date date Ngày khách gửi đánh giá
rating int Điểm đánh giá từ 1 đến 5
review_title str Tiêu đề đánh giá của khách hàng
```

```
Bảng Analytical
```
▶ **sales.csv — Dữ liệu doanh thu**

```
Cột Kiểu Mô tả
Date date Ngày đặt hàng
Revenue float Tổng doanh thu thuần
COGS float Tổng giá vốn hàng bán
```
```
Split File Khoảng thời gian
Train sales.csv 04/07/2012 – 31/12/
Test sales_test.csv 01/01/2023 – 01/07/
```
```
Lưu ý: Tập test sẽ không được công bố mà được dùng để đánh giá kết quả mô hình trên
Kaggle. Cấu trúc của file test sẽ giống với sample_submission.csv
```
```
Bảng Operational
```
▶ **inventory.csv — Tồn kho**

```
Cột Kiểu Mô tả
snapshot_date date Ngày chụp ảnh tồn kho (cuối tháng)
product_id int FK → products.product_id
stock_on_hand int Số lượng tồn kho cuối tháng
units_received int Số lượng nhập kho trong tháng
units_sold int Số lượng bán ra trong tháng
stockout_days int Số ngày hết hàng trong tháng
days_of_supply float Số ngày tồn kho có thể đáp ứng nhu cầu bán
fill_rate float Tỷ lệ đơn hàng được đáp ứng đủ từ tồn kho
stockout_flag int Cờ báo tháng có xảy ra hết hàng
overstock_flag int Cờ báo tồn kho vượt mức cần thiết
reorder_flag int Cờ báo cần tái đặt hàng sớm
sell_through_rate float Tỷ lệ hàng đã bán so với tổng hàng sẵn có
product_name str Tên sản phẩm
category str Danh mục sản phẩm
segment str Phân khúc sản phẩm
year int Năm trích từ snapshot_date
month int Tháng trích từ snapshot_date
```
▶ **web_traffic.csv — Lưu lượng truy cập**

```
Cột Kiểu Mô tả
date date Ngày ghi nhận lưu lượng
sessions int Tổng số phiên truy cập trong ngày
unique_visitors int Số lượt khách truy cập duy nhất
page_views int Tổng số lượt xem trang
bounce_rate float Tỷ lệ phiên chỉ xem một trang rồi thoát
avg_session_duration_sec float Thời gian trung bình mỗi phiên (giây)
conversion_rate float Tỷ lệ phiên dẫn đến đặt hàng
traffic_source str Kênh nguồn dẫn traffic về website
```

**Quan hệ giữa các bảng**

```
Table 2: Quy tắc quan hệ (Cardinality)
```
```
Quan hệ Cardinality
orders ↔ payments 1 : 1
orders ↔ shipments 1 : 0 hoặc 1 (trạng thái shipped/delivered/returned)
orders ↔ returns 1 : 0 hoặc nhiều (trạng thái returned)
orders ↔ reviews 1 : 0 hoặc nhiều (trạng thái delivered, ∼20%)
order_items ↔ promotions nhiều : 0 hoặc 1
products ↔ inventory 1 : nhiều (1 dòng/sản phẩm/tháng)
```

**Đề Bài**

```
Phần 1 — Câu hỏi Trắc nghiệm
```
```
Chọn một đáp án đúng nhất cho mỗi câu hỏi. Các câu hỏi yêu cầu tính toán trực tiếp từ
dữ liệu được cung cấp.
```
**Q1.** Trong số các khách hàng có nhiều hơn một đơn hàng, **trung vị số ngày giữa hai lần
mua liên tiếp** (inter-order gap) xấp xỉ là bao nhiêu? (Tính từ orders.csv)

```
A) 30 ngày
```
```
B) 90 ngày
```
```
C) 180 ngày
```
```
D) 365 ngày
```
**Q2.** Phân khúc sản phẩm (segment) nào trong products.csv có **tỷ suất lợi nhuận gộp
trung bình** cao nhất, với công thức ( _price_ − _cogs_ ) _/price_?

```
A) Premium
```
```
B) Performance
```
```
C) Activewear
```
```
D) Standard
```
**Q3.** Trong các bản ghi trả hàng liên kết với sản phẩm thuộc danh mục **Streetwear** (join
returns với products theo product_id), **lý do trả hàng** nào xuất hiện nhiều nhất?

```
A) defective
```
```
B) wrong_size
```
```
C) changed_mind
```
```
D) not_as_described
```
**Q4.** Trong web_traffic.csv, nguồn truy cập (traffic_source) nào có **tỷ lệ thoát trung
bình** (bounce_rate) **thấp nhất** trên tất cả các ngày xuất hiện nguồn đó trong cột traffic_source?

```
A) organic_search
```
```
B) paid_search
```
```
C) email_campaign
```
```
D) social_media
```

**Q5.** Tỷ lệ phần trăm các dòng trong order_items.csv có áp dụng khuyến mãi (tức là promo_id
không null) xấp xỉ là bao nhiêu?

```
A) 12%
```
```
B) 25%
```
```
C) 39%
```
```
D) 54%
```
**Q6.** Trong customers.csv, xét các khách hàng có age_group khác null, nhóm tuổi nào có **số
đơn hàng trung bình trên mỗi khách hàng** cao nhất? (tổng số đơn / số khách hàng trong
nhóm)

```
A) 55+
```
```
B) 25–
```
```
C) 35–
```
```
D) 45–
```
**Q7.** Vùng (region) nào trong geography.csv tạo ra **tổng doanh thu cao nhất** trong
sales_train.csv?

```
A) West
```
```
B) Central
```
```
C) East
```
```
D) Cả ba vùng có doanh thu xấp xỉ bằng nhau
```
**Q8.** Trong các đơn hàng có order_status = ’cancelled’ trong orders.csv, **phương thức
thanh toán** nào được sử dụng nhiều nhất?

```
A) credit_card
```
```
B) cod
```
```
C) paypal
```
```
D) bank_transfer
```
**Q9.** Trong bốn kích thước sản phẩm (S, M, L, XL), kích thước nào có **tỷ lệ trả hàng cao
nhất** , được định nghĩa là số bản ghi trong returns chia cho số dòng trong order_items (join
với products theo product_id)?

```
A) S
```
```
B) M
```
```
C) L
```

### D) XL

**Q10.** Trong payments.csv, **kế hoạch trả góp** nào có **giá trị thanh toán trung bình trên
mỗi đơn hàng** cao nhất?

```
A) 1 kỳ (trả một lần)
```
```
B) 3 kỳ
```
```
C) 6 kỳ
```
```
D) 12 kỳ
```

```
Phần 2 — Trực quan hoá và Phân tích Dữ liệu

Khám phá bộ dữ liệu để tìm ra các insight có ý nghĩa kinh doanh. Phần này được đánh
giá dựa trên tính sáng tạo , chiều sâu phân tích và chất lượng trình bày. Không có
đáp án đúng duy nhất — ban giám khảo đánh giá khả năng kể chuyện bằng dữ liệu (data
storytelling) của các đội.
```
▶ **Yêu cầu**

Các đội thi tự do lựa chọn góc nhìn phân tích từ bộ dữ liệu. Bài nộp cần bao gồm hai thành
phần:

**1. Trực quan hoá (Visualizations):** Tạo các biểu đồ, đồ thị, bản đồ hoặc dashboard trực
    quan để thể hiện các pattern, xu hướng và mối quan hệ trong dữ liệu. Mỗi hình ảnh cần
    có tiêu đề, nhãn trục rõ ràng và chú thích phù hợp.
**2. Phân tích (Analysis):** Viết phần giải thích đi kèm mỗi trực quan hoá, bao gồm:
    - Mô tả những gì biểu đồ thể hiện và tại sao góc nhìn này quan trọng
    - Các phát hiện chính (key findings) được hỗ trợ bởi số liệu cụ thể
    - Ý nghĩa kinh doanh (business implications) hoặc đề xuất hành động (actionable rec-
       ommendations)

```
Tiêu chí đánh giá Phần 2: Bài nộp được đánh giá theo bốn cấp độ phân tích. Cấp độ
cao hơn bao gồm và nâng cao cấp độ thấp hơn.
```
```
Cấp độ Câu hỏi Ban giám khảo đánh giá
Descriptive What happened? Thống kê tổng hợp chính xác, biểu đồ có
nhãn rõ ràng, tổng hợp dữ liệu đúng
Diagnostic Why did it hap-
pen?
```
```
Giả thuyết nhân quả, so sánh phân khúc,
xác định bất thường có bằng chứng hỗ trợ
Predictive What is likely to
happen?
```
```
Ngoại suy xu hướng, phân tích tính mùa
vụ, phân tích chỉ số dẫn xuất
Prescriptive What should we
do?
```
```
Đề xuất hành động kinh doanh được hỗ
trợ bởi dữ liệu; đánh đổi được định lượng
```
```
Các đội đạt cấp độ Prescriptive nhất quán trên nhiều phân tích sẽ đạt điểm cao nhất.
```

```
Phần 3 — Mô hình Dự báo Doanh thu (Sales Forecasting)
```
▶ **Bối cảnh kinh doanh**

Bạn là nhà khoa học dữ liệu tại một công ty thương mại điện tử thời trang Việt Nam. Doanh
nghiệp cần dự báo nhu cầu chính xác ở mức chi tiết để tối ưu hoá phân bổ tồn kho, lập kế hoạch
khuyến mãi và quản lý logistics trên toàn quốc.

▶ **Định nghĩa bài toán**

**Dự báo cột Revenue** trong khoảng thời gian của sales_test.csv.
Mỗi dòng trong tập test là một bộ (Date,Revenue,COGS) duy nhất trong giai đoạn 01/01/

- 01/07/2024.

▶ **Dữ liệu**

```
Split File Khoảng thời gian
Train sales.csv 04/07/2012 – 31/12/
Test sales_test.csv 01/01/2023 – 01/07/
```
▶ **Chỉ số đánh giá**

Bài nộp được đánh giá bằng ba chỉ số:
**Mean Absolute Error (MAE):**


Root Mean Squared Error (RMSE):


R^2 (Coefficient of Determination):

trong đó _Fi_ là giá trị dự báo, _Ai_ là giá trị thực, _A_ ̄ là trung bình giá trị thực. MAE đo độ
lệch tuyệt đối trung bình, RMSE phạt nặng hơn các sai số lớn, và _R_^2 thể hiện tỷ lệ phương sai
được giải thích bởi mô hình.

```
MAE và RMSE càng thấp càng tốt. R^2 càng cao càng tốt (lý tưởng gần 1).
```
▶ **Định dạng file nộp**

Nộp file submission.csv với các cột sau:

```
Các dòng trong submission.csv phải giữ đúng thứ tự như sample_submission.csv.
Không sắp xếp lại hoặc xáo trộn.
```
**Ví dụ:**


Date,Revenue,COGS
2023-01-01,26607.2,2585.
2023-01-02,1007.89,163.
2023-01-03,1089.51,821.
...

▶ **Ràng buộc**

**1. Không dùng dữ liệu ngoài:** Tất cả đặc trưng phải được tạo từ các file dữ liệu được
    cung cấp.
**2. Tính tái lập (Reproducibility):** Đính kèm toàn bộ mã nguồn. Đặt random seed khi
    cần thiết.
**3. Khả năng giải thích (Explainability):** Trong report, bao gồm một mục giải thích các
    yếu tố dẫn động doanh thu chính được mô hình xác định (vd: feature importances, SHAP
    values, hoặc partial dependence plots). Giải thích những gì mô hình học được bằng ngôn
    ngữ kinh doanh.


**Thang điểm Chấm thi**

```
Tổng điểm tối đa: 100 điểm , phân bổ theo ba phần thi. Điểm thành phần không làm
tròn cho đến khi tính tổng cuối cùng.
```
```
Table 3: Phân bổ điểm tổng quan
```
```
Phần Nội dung Điểm Tỷ trọng
1 Câu hỏi Trắc nghiệm (MCQ) 20 20%
2 Trực quan hoá & Phân tích (EDA) 60 60%
3 Mô hình Dự báo Doanh thu (Forecasting) 20 20%
Tổng 100 100%
```
```
Phần 1 — Câu hỏi Trắc nghiệm (20 điểm)
```
Mỗi câu đúng được **2 điểm**. Không trừ điểm cho câu trả lời sai.

```
Thành phần Số câu Điểm
Câu trả lời đúng 10 câu 2 điểm / câu
Câu trả lời sai — 0 điểm
Không trả lời — 0 điểm
Tổng tối đa 20 điểm
```
```
Phần 2 — Trực quan hoá & Phân tích EDA (60 điểm)
```
Phần này được chấm theo **bốn tiêu chí độc lập** , mỗi tiêu chí tương ứng với một cấp độ phân
tích trong rubric. Ban giám khảo chấm từng tiêu chí trên thang điểm thành phần, sau đó cộng
lại.


```
Tiêu chí Mô tả Điểm tối đa
Chất lượng trực
quan hoá
```
```
Biểu đồ có tiêu đề, nhãn trục, chú
thích đầy đủ; lựa chọn loại biểu đồ
phù hợp; thẩm mỹ trình bày rõ ràng
```
### 15

```
Chiều sâu phân
tích
```
```
Bao phủ đầy đủ bốn cấp độ Descrip-
tive → Diagnostic → Predictive →
Prescriptive; lập luận logic, có số
liệu cụ thể hỗ trợ
```
### 25

```
Insight kinh doanh Phát hiện có giá trị thực tiễn; đề
xuất hành động khả thi; liên kết rõ
ràng giữa dữ liệu và quyết định kinh
doanh
```
### 15

```
Tính sáng tạo & kể
chuyện
```
```
Góc nhìn độc đáo, không lặp lại các
phân tích hiển nhiên; mạch trình
bày coherent; kết nối nhiều bảng dữ
liệu một cách có chủ đích
```
### 5

```
Tổng tối đa 60 điểm
```
Chi tiết thang điểm từng tiêu chí:

```
Tiêu chí Mức
điểm
```
```
Mô tả
```
```
Chất lượng
trực quan hoá
(15đ)
```
```
13–15đ Tất cả biểu đồ đều đạt chuẩn, lựa chọn loại
biểu đồ tối ưu cho từng insight
8–12đ Phần lớn biểu đồ đạt yêu cầu, một số thiếu
nhãn hoặc chú thích
0–7đ Biểu đồ thiếu thông tin, khó đọc hoặc không
phù hợp với dữ liệu
```
```
Chiều sâu
phân tích
(25đ)
```
```
21–25đ Đạt cả bốn cấp độ Descriptive, Diagnostic,
Predictive, Prescriptive một cách nhất quán
14–20đ Đạt ba cấp độ, cấp độ Prescriptive còn hời
hợt
7–13đ Chủ yếu ở cấp Descriptive và Diagnostic
0–6đ Chỉ mô tả bề mặt, thiếu phân tích
Insight
kinh doanh
(15đ)
```
```
13–15đ Đề xuất cụ thể, định lượng được, áp dụng
được ngay
8–12đ Có đề xuất nhưng còn chung chung
0–7đ Thiếu kết nối với bối cảnh kinh doanh
```
```
Tính sáng tạo
(5đ)
```
```
4–5đ Góc nhìn độc đáo, kết hợp nhiều nguồn dữ
liệu, mạch trình bày thuyết phục
2–3đ Có điểm sáng tạo nhưng chưa nhất quán
0–1đ Phân tích dự đoán được, không có điểm nổi
bật
```
```
Phần 3 — Mô hình Dự báo Doanh thu (20 điểm)
```
Điểm Phần 3 được tính từ **hai thành phần** : hiệu suất mô hình trên Kaggle và chất lượng báo
cáo kỹ thuật.


```
Thành phần Mô tả Điểm tối đa
Hiệu suất mô hình Dựa trên điểm MAE, RMSE,
R^2 trên tập test (Kaggle leader-
board); xếp hạng tương đối so
với các đội khác trong cuộc thi
```
### 12

```
Báo cáo kỹ thuật Chất lượng pipeline (feature en-
gineering, cross-validation, xử
lý leakage); giải thích mô hình
bằng SHAP / feature impor-
tance; tuân thủ các ràng buộc
đã nêu
```
### 8

```
Tổng tối đa 20 điểm
```
```
Thành phần Mức
điểm
```
```
Mô tả
```
```
Hiệu suất mô hình
(12đ)
```
```
10–12đ Xếp hạng top leaderboard; MAE và
RMSE thấp, R^2 cao
5–9đ Hiệu suất trung bình; mô hình hoạt động
nhưng chưa tối ưu
3–4đ Bài nộp hợp lệ nhưng hiệu suất thấp; mức
điểm sàn
```
```
Báo cáo kỹ thuật
(8đ)
```
```
7–8đ Pipeline rõ ràng, cross-validation đúng
chiều thời gian, giải thích mô hình cụ thể
bằng SHAP hoặc tương đương, tuân thủ
đầy đủ ràng buộc
4–6đ Pipeline đủ dùng, giải thích còn định tính,
một số ràng buộc chưa được xử lý tường
minh
0–3đ Thiếu giải thích, không kiểm soát leakage,
hoặc không thể tái lập kết quả
```
**Điều kiện loại bài:** Bài nộp sẽ bị **loại toàn bộ Phần 3** nếu vi phạm bất kỳ ràng buộc
nào sau đây: (1) sử dụng Revenue/COGS từ tập test làm đặc trưng; (2) sử dụng dữ liệu
ngoài bộ dữ liệu được cung cấp; (3) không đính kèm mã nguồn hoặc kết quả không thể tái
lập.


**Hướng dẫn Nộp bài**

```
Checklist nộp bài
```
Mỗi đội cần hoàn thành và nộp đầy đủ các mục sau:

**1. Nộp kết quả dự báo trên Kaggle
2. Link Kaggle:** https://www.kaggle.com/competitions/datathon-2026-round-

```
Đảm bảo file submission.csv có đúng số lượng dòng và giữ nguyên thứ tự như
sample_submission.csv. File không đúng định dạng sẽ bị từ chối bởi hệ thống
Kaggle.
```
**3. Báo cáo (Report)**
    Viết báo cáo sử dụng **template LaTeX của NeurIPS** , có thể tải tại:

```
https://neurips.cc/Conferences/2025/CallForPapers
```
```
Yêu cầu báo cáo:
```
- Giới hạn tối đa **4 trang** (không tính references và appendix)
- Bao gồm các nội dung:
    **-** Trực quan hoá và phân tích dữ liệu (Phần 2)
    **-** Phương pháp tiếp cận, pipeline mô hình và kết quả thực nghiệm (Phần 3)
- **Đính kèm link GitHub repository** của nhóm trong báo cáo (chứa toàn bộ mã
    nguồn, notebook, và file submission)

```
Lưu ý: GitHub repository cần được đặt ở chế độ public hoặc cấp quyền truy cập
cho ban tổ chức trước deadline nộp bài. Repository nên có README.md mô tả cấu trúc
thư mục và hướng dẫn chạy lại kết quả.
```
**4. Form nộp bài thi Vòng 1**
    Điền đầy đủ thông tin trong form nộp bài chính thức (link sẽ được cung cấp). Form yêu
    cầu:
       - Chọn đáp án đúng cho câu hỏi trắc nghiệm
       - Upload file báo cáo (PDF)
       - Link GitHub repository
       - Link submission trên Kaggle
       - **Ảnh chụp thẻ sinh viên** của **tất cả** thành viên trong đội
       - **Tickbox xác nhận:** Nhóm thi cam kết có **ít nhất 1 thành viên** có thể tham gia
          trực tiếp Vòng Chung kết vào ngày **23/05/2026** tại **Đại học VinUni** , Hà Nội



