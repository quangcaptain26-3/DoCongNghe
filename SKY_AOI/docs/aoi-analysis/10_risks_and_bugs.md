# Rủi ro và Lỗi

Chỉ dựa trên bằng chứng. Số dòng tham chiếu `sky.py`.

---

## Lỗi Runtime

### Rủi ro: Import IoCard bị comment nhưng vẫn được sử dụng

- **Mức độ:** Nghiêm trọng (chế độ sensor)
- **Bằng chứng:** L29 `#from ioCardNew import IoCard`; L673 `self.iocard = IoCard(...)`
- **Tại sao quan trọng:** `startprogram` với `is_sensor=True` gây `NameError: IoCard`.
- **Cách sửa đề xuất:** Bỏ comment hoặc khôi phục import; xác minh `ioCardNew` trên đường dẫn triển khai.

### Rủi ro: Import camera_check_ipex bị comment nhưng vẫn được sử dụng

- **Mức độ:** Nghiêm trọng (model ipex_check)
- **Bằng chứng:** L37 `# from ipex_check_yolo import camera_check_ipex`; L871 `camera_check_ipex(...)`
- **Tại sao quan trọng:** Chọn model `ipex_check` sẽ crash lúc runtime.
- **Cách sửa đề xuất:** Khôi phục import; thêm guard model nếu module là tùy chọn.

### Rủi ro: Import predict_change bị comment nhưng vẫn được sử dụng

- **Mức độ:** Nghiêm trọng (đường dẫn SKY YOLO)
- **Bằng chứng:** L7 `# from yolov5.classify import predict_change`; L2540 `predict_change.run(...)`
- **Tại sao quan trọng:** `yolov5_inference` thất bại nếu được gọi (ví dụ từ đường dẫn nội bộ SKY).
- **Cách sửa đề xuất:** Khôi phục import hoặc xóa đường dẫn YOLO chết.

### Rủi ro: Bare except khi khởi tạo SFIS

- **Mức độ:** Trung bình
- **Bằng chứng:** L174 `except:` khi kết nối SFIS — hiển thị MessageBox và `sys.exit()`
- **Tại sao quan trọng:** Che lỗi mạng/cấu hình cụ thể; thoát đột ngột.
- **Cách sửa đề xuất:** Bắt exception cụ thể; ghi log traceback.

### Rủi ro: choose_model / __init__ tải model nuốt lỗi

- **Mức độ:** Trung bình
- **Bằng chứng:** L335–336 `except Exception as e: print(str(e))` — không cảnh báo người dùng, khởi tạo một phần
- **Tại sao quan trọng:** Ứng dụng có thể chạy với recipe không đầy đủ.
- **Cách sửa đề xuất:** Fail fast hoặc hiển thị hộp thoại lỗi.

---

## Lỗi Logic

### Rủi ro: go_run2 hardcode show_image_MR6500

- **Mức độ:** Cao
- **Bằng chứng:** L829 `self.show_image_MR6500(self.shan)` trong vòng lặp sensor — không kiểm tra `select_model`
- **Tại sao quan trọng:** Chế độ sensor luôn chạy pipeline MR6500 bất kể recipe đã tải.
- **Cách sửa đề xuất:** Dispatch giống go_run3 hoặc gọi dispatcher dùng chung.

### Rủi ro: Lỗi chính tả thuộc tính class Scan

- **Mức độ:** Thấp (class không dùng)
- **Bằng chứng:** L5488 định nghĩa `scan_user_label`; L5495 tham chiếu `self.signin_user_label`
- **Tại sao quan trọng:** Khởi tạo sẽ gây AttributeError.
- **Cách sửa đề xuất:** Đổi tên thuộc tính cho nhất quán nếu class được dùng.

### Rủi ro: Lỗi vòng lặp emit vô hạn Runthread.run

- **Mức độ:** Trung bình (nếu thread được dùng)
- **Bằng chứng:** L5529–5530 `while result==[]: self.signal.emit(result)` — emit danh sách rỗng lặp lại trước khi OCR chạy
- **Tại sao quan trọng:** Tín hiệu giả; busy loop cho đến khi OCR hoàn tất.
- **Cách sửa đề xuất:** Xóa vòng while; emit một lần khi OCR xong.

### Rủi ro: Lỗi cú pháp dict model_and_90

- **Mức độ:** Trung bình (tải module)
- **Bằng chứng:** L106–107 nối chuỗi trong giá trị dict `"C10" "00-8P-2G-L"` — có thể tạo ánh xạ key không mong muốn
- **Tại sao quan trọng:** Ánh xạ model sai im lặng cho tra cứu mã 90.
- **Cách sửa đề xuất:** Xác minh cú pháp literal dict và key dự định.

---

## Rủi ro UI / Threading

### Rủi ro: startprogram chặn luồng UI

- **Mức độ:** Cao
- **Bằng chứng:** L687 `while True` trong slot kết nối với click nút
- **Tại sao quan trọng:** UI không phản hồi trừ qua processEvents; Stop có thể trễ.
- **Cách sửa đề xuất:** Worker thread + state machine dựa trên signal (xem 09_threading_and_ui.md).

### Rủi ro: time.sleep(5) trên luồng UI sau sensor

- **Mức độ:** Cao
- **Bằng chứng:** L813 trong go_run2
- **Tại sao quan trọng:** Đơ 5 giây; operator không tương tác được.
- **Cách sửa đề xuất:** QTimer hoặc delay cấu hình được ngoài luồng UI.

### Rủi ro: stop_program có thể không thoát go_run2 nhanh

- **Mức độ:** Trung bình
- **Bằng chứng:** Vòng lặp trong go_run2 L796; sleep L813; không kiểm tra stop_program trong sleep
- **Tại sao quan trọng:** Nút Stop trễ tới 5 giây+ mỗi lần lặp.
- **Cách sửa đề xuất:** Kiểm tra cờ stop; chờ có thể ngắt.

---

## Rủi ro Khả năng Bảo trì

### Rủi ro: Class Demo khổng lồ (~5k dòng)

- **Mức độ:** Cao
- **Bằng chứng:** L139–5420 một class với 40+ phương thức
- **Tại sao quan trọng:** Khó test, review, hoặc thêm sản phẩm an toàn.
- **Cách sửa đề xuất:** Tách service/pipeline (kế hoạch Phase 5).

### Rủi ro: Logic sản phẩm qua chuỗi elif

- **Mức độ:** Cao
- **Bằng chứng:** go_run3 L839+ chuỗi `elif self.select_model == ...` dài
- **Tại sao quan trọng:** O(n) nhánh; khối fail/upload trùng lặp.
- **Cách sửa đề xuất:** Model registry / strategy dict.

### Rủi ro: Đường dẫn code chết

- **Mức độ:** Thấp
- **Bằng chứng:** `show_image` L1913, `show_image_SKY_yolo` L3109 — không có caller; stub methods L607, L628
- **Tại sao quan trọng:** Gây nhầm lẫn cho người bảo trì; có thể mục nát.
- **Cách sửa đề xuất:** Xóa hoặc ghi chú là legacy.

---

## Rủi ro Sản xuất

### Rủi ro: Upload SFIS rải rác trong vision/điều phối

- **Mức độ:** Trung bình
- **Bằng chứng:** Nhiều lần gọi `data_upload` trong go_run3 (ví dụ L1150, L1358) với mã lỗi trùng lặp
- **Tại sao quan trọng:** Upload không nhất quán khi lỗi một phần; khó audit trail MES.
- **Cách sửa đề xuất:** Tập trung upload trong result handler.

### Rủi ro: Đường dẫn mẫu hardcode cho chế độ verify SKY

- **Mức độ:** Trung bình
- **Bằng chứng:** L1041–1046 `cv2.imread("source/1.jpg")` v.v. (dòng thay thế dùng camera bị comment)
- **Tại sao quan trọng:** Sản xuất có thể vô tình dùng ảnh tĩnh nếu bật dòng verify.
- **Cách sửa đề xuất:** Cờ config cho debug vs chụp sản xuất.

### Rủi ro: Thiếu dependency trong repo

- **Mức độ:** Cao (triển khai)
- **Bằng chứng:** Workspace chỉ chứa sky.py; import UI, basler_my, sfisapi, config.json
- **Tại sao quan trọng:** Không thể chạy hoặc phân tích đầy đủ nếu thiếu file bên ngoài.
- **Cách sửa đề xuất:** Ghi tài liệu gói triển khai; ghim phiên bản dependency.

### Rủi ro: closeEvent vs startprogram chặn

- **Mức độ:** Trung bình
- **Bằng chứng:** closeEvent L5411 đặt stop_program; startprogram while True có thể vẫn đang chạy
- **Tại sao quan trọng:** Đóng cửa sổ có thể treo cho đến khi vòng lặp hoàn tất một lần.
- **Cách sửa đề xuất:** Đảm bảo vòng lặp kiểm tra stop_program thường xuyên; tránh sleep không ngắt được.

---

## Phase 2 — Rủi ro Điều phối (Chi tiết Bổ sung)

### Rủi ro: go_run2 hardcode MR6500 (mở rộng)

- **Mức độ:** Nghiêm trọng (logic sản xuất)
- **Bằng chứng:** L829 `show_image_MR6500(self.shan)` — không nhánh `select_model`; đường sensor không bao giờ gọi `go_run3` (L693–697)
- **Tại sao quan trọng:** Bất kỳ recipe non-MR6500 nào với `is_sensor=True` chạy kiểm tra sai sau scan/trigger sensor.
- **Cách sửa đề xuất:** Callable dispatch dùng chung cho go_run2 và go_run3.

### Rủi ro: wait_test treo khi HH4K exception (stepN chưa đặt)

- **Mức độ:** Cao
- **Bằng chứng:** `go_run3` L993–994 — chỉ `if self.step1==True`, không có `elif step1==False`; `show_image_HH4K` except L2525–2527 chỉ log, không `wait_test`; `step1=True` chỉ L2243 trong try
- **Tại sao quan trọng:** Thiếu `point/stepN.json`, ảnh mẫu hỏng, hoặc lỗi so sánh để `step1==False` → startprogram kẹt (`wait_test` False từ L690/L713).
- **Ghi chú:** HH4K vision **fail** vẫn đặt `step1=True` L2243 — treo do exception, không phải do inspection-fail (khác SKY L2787).
- **Cách sửa đề xuất:** Handler `elif stepN==False` với `wait_test=True`; hoặc `finally` trong `show_image_HH4K`; reset phòng thủ khi thoát `go_run3`.

### Rủi ro: HH4K chuỗi cả 4 bước dù vision fail

- **Mức độ:** Cao (chất lượng / chuỗi sai)
- **Bằng chứng:** L2243 `self.step1=True` sau fail UI L2223–2227; `go_run3` L994 chuỗi khi `step1==True` không kiểm tra `my_inference_result`
- **Tại sao quan trọng:** Operator được nhắc STEP 2–4 sau khi bước 1 fail; `updatecount` mỗi bước tăng Total tới 4× mỗi DUT.
- **Cách sửa đề xuất:** Đặt `stepN=False` khi fail (mẫu SKY) hoặc thêm nhánh fail điều phối.

### Rủi ro: wait_test treo khi select_model không xác định

- **Mức độ:** Cao
- **Bằng chứng:** go_run3 L834–1911 — không có `else` cuối
- **Tại sao quan trọng:** Chế độ manual kẹt sau go_run1 nếu chuỗi model chưa nối dây.
- **Cách sửa đề xuất:** else mặc định: log + `wait_test=True`.

### Rủi ro: Exception startprogram để Start bị vô hiệu

- **Mức độ:** Trung bình
- **Bằng chứng:** L668 vô hiệu Start; L727–729 except chỉ log
- **Tại sao quan trọng:** Lỗi khởi tạo sau khi vô hiệu — không khởi động lại được nếu không restart app.
- **Cách sửa đề xuất:** Bật lại Start trong except/finally.

### Rủi ro: Upload SFIS fail trùng lặp trong go_run3

- **Mức độ:** Trung bình
- **Bằng chứng:** Khối lặp SKY L1149+, Cisco L1357+, Nanook L1774+, WP L1545+; mã lỗi `BDFA0` vs `BDFA01`
- **Tại sao quan trọng:** Báo lỗi MES không nhất quán.
- **Cách sửa đề xuất:** Helper upload tập trung (Phase 5).

### Rủi ro: scan_sta / wait_test mất đồng bộ

- **Mức độ:** Trung bình
- **Bằng chứng:** L690 đặt `wait_test=False`; go_run3 có thể return mà không reset
- **Tại sao quan trọng:** Trạng thái chạy đóng băng cho đến khi Stop.
- **Cách sửa đề xuất:** `wait_test=True` phòng thủ khi thoát go_run3.

### Rủi ro: stopprogram không bật lại Start

- **Mức độ:** Thấp–Trung bình
- **Bằng chứng:** L5398–5404 — Start chỉ bật trong vòng lặp L699/L725
- **Tại sao quan trọng:** Thoát vòng lặp bất thường để Start bị vô hiệu.
- **Cách sửa đề xuất:** Bật Start trong stopprogram như lưới an toàn.

---

## Phase 4 — Rủi ro Pipeline MR6500

### Rủi ro: Truy vấn SFIS không có guard sfis_choose trong show_image_MR6500

- **Mức độ:** Cao
- **Bằng chứng:** L2032–2035 `self.mysfis` vô điều kiện; `mysfis` không tạo khi SFIS tắt L194–197
- **Tại sao quan trọng:** Chế độ offline/test crash hoặc abort sau decode thành công.
- **Cách sửa đề xuất:** Kiểm tra `sfis_choose` trước lệnh gọi SFIS; đường offline với liaohao thủ công.

### Rủi ro: Parse chuỗi SFIS mong manh (MR6500)

- **Mức độ:** Cao
- **Bằng chứng:** L2032 `split("\x7f")[2].split(":")[1]`; L2035 `split("\x7f")[2]`
- **Tại sao quan trọng:** Mọi thay đổi định dạng SFIS → except L2141; không đếm Fail.
- **Cách sửa đề xuất:** Parse có cấu trúc + lỗi SFIS hiển thị cho người dùng.

### Rủi ro: MR6500 không có data_upload lên SFIS

- **Mức độ:** Trung bình (khoảng trống MES — cần xác minh nếu cố ý)
- **Bằng chứng:** L2003–2143 — chỉ `get_sfis_SN`/`get_sfis_90`; không `data_upload` như đường SKY/Cisco trong go_run3
- **Tại sao quan trọng:** Pass/Fail local có thể không đồng bộ MES.
- **Cách sửa đề xuất:** Xác nhận yêu cầu sản xuất; thêm upload với mã lỗi nếu cần.

### Rủi ro: ROI không xác định nếu thiếu nhãn ISN/CHECK

- **Mức độ:** Trung bình
- **Bằng chứng:** Vòng lặp L2007–2025 break chỉ khi khớp; không validate trước L2028/L2040
- **Tại sao quan trọng:** Recipe hỏng → exception, không có fail UI có cấu trúc.
- **Cách sửa đề xuất:** Nhánh ROI-not-found rõ ràng.

### Rủi ro: Ngưỡng hash hardcode 0.85 và mean 30

- **Mức độ:** Trung bình
- **Bằng chứng:** L2065–2068 literal
- **Tại sao quan trọng:** False pass/fail khi ánh sáng thay đổi.
- **Cách sửa đề xuất:** Cấu hình được theo model JSON.

### Rủi ro: Thiếu sample/{liaohao}.jpg

- **Mức độ:** Trung bình
- **Bằng chứng:** L2038 `cv2.imread` — không kiểm tra null trước slice L2038
- **Tại sao quan trọng:** SFIS trả liaohao hợp lệ nhưng file thiếu → đường exception.
- **Cách sửa đề xuất:** Validate kết quả imread.

### Rủi ro: Đường exception MR6500 không cập nhật Fail/count

- **Mức độ:** Thấp–Trung bình
- **Bằng chứng:** L2141–2143 except chỉ log; caller vẫn đặt `wait_test=True` L830/L859
- **Tại sao quan trọng:** Bỏ qua kiểm tra im lặng; chu kỳ tiếp tục.
- **Cách sửa đề xuất:** Fail + updatecount trong except.

### Rủi ro: go_run2 hardcode MR6500 (tác động sản xuất)

- **Mức độ:** Nghiêm trọng nếu non-MR6500 dùng `is_sensor=True`; tiềm ẩn nếu sản xuất chỉ MR6500 dùng sensor
- **Bằng chứng:** L829; không có model JSON trong repo để xác nhận ghép sản xuất — **cần xác minh**
- **Tại sao quan trọng:** ROI/SFIS/barcode JSON sai áp dụng vào logic MR6500.
- **Cách sửa đề xuất:** Dispatch theo `select_model`; audit config sản xuất cho cặp `is_sensor` + model.

---

## Phase 5 — Rủi ro Pipeline SKY

### Rủi ro: STEP 6 false pass — upload SFIS dù kiểm tra tổng hợp fail

- **Mức độ:** Nghiêm trọng
- **Bằng chứng:** L3055–3096: Cambrian Pass đặt `step6=True`; fail UI cho `my_inference_result=="fail"` bị comment L3067–3074; `data_upload` L3083 khi chỉ Cambrian Pass
- **Tại sao quan trọng:** MES pass khi cờ barcode/OCR (`checksn`, `modelcheck`, `sncheck`) false
- **Cách sửa đề xuất:** Chặn step6/upload SFIS trừ khi tất cả cờ true

### Rủi ro: show_image_SKY dùng Cambrian nhưng biến đặt tên yolo_stepN

- **Mức độ:** Thấp (bảo trì)
- **Bằng chứng:** L2779 `yolo_step1=self.cambrian_space(...)` — không phải YOLO
- **Tại sao quan trọng:** Gây nhầm lẫn bảo trì; `show_image_SKY_yolo` là đường chết riêng L3109
- **Cách sửa đề xuất:** Đổi tên; xóa biến thể YOLO chết hoặc sửa import

### Rủi ro: Exception cambrian_space trả về None

- **Mức độ:** Cao
- **Bằng chứng:** L2643–2645 — không return trong except
- **Tại sao quan trọng:** stepN không đặt; go_run3 có thể không vào fail handler
- **Cách sửa đề xuất:** Return `"Fail"` khi exception

### Rủi ro: SKY ROI từ point/*.json hardcode không phải model_point

- **Mức độ:** Trung bình
- **Bằng chứng:** L2658 `point/SKY_barcode.json` v.v.; bỏ qua recipe `model_point`
- **Tại sao quan trọng:** Triển khai phải ship đúng file point theo biến thể
- **Cách sửa đề xuất:** Tải đường dẫn từ model JSON

### Rủi ro: PaddleOCR khởi tạo lại mỗi STEP 3 trên luồng UI

- **Mức độ:** Trung bình
- **Bằng chứng:** L2864–2865
- **Tại sao quan trọng:** Đơ UI khi tải model
- **Cách sửa đề xuất:** Tái sử dụng instance OCR

### Rủi ro: barcode_list_clei[0] không kiểm tra độ dài

- **Mức độ:** Trung bình
- **Bằng chứng:** L2909
- **Tại sao quan trọng:** IndexError → nuốt L3104; step3 không đặt
- **Cách sửa đề xuất:** Validate số lượng kết quả pyzbar

### Rủi ro: pHash HH4K không dùng trong pass/fail

- **Mức độ:** Trung bình
- **Bằng chứng:** `HH4K_compare` L5326–5329 tính `cmHash`; giá trị trả về gán `step1_hash` L2170 không bao giờ dùng; pass chỉ dùng `step1_pil` và màu HSV L2176
- **Tại sao quan trọng:** Tính toán chết; cổng hash kiểu MR6500 không áp dụng dù helper tồn tại.
- **Cách sửa đề xuất:** Dùng ngưỡng hash hoặc xóa tính toán không dùng.

### Rủi ro: Lưu sản xuất bước 4 HH4K bị comment

- **Mức độ:** Trung bình
- **Bằng chứng:** L2434–2437 `cv2.imwrite` cho step4 pass/fail bị comment; chỉ lưu khi accept nhãn L2519
- **Tại sao quan trọng:** Kết quả vision bước 4 không lưu trừ khi operator hoàn tất scan nhãn.
- **Cách sửa đề xuất:** Bỏ comment hoặc căn chỉnh cố ý với quy trình nhãn.

### Rủi ro: HH4K không thể đến trong chế độ sensor

- **Mức độ:** Cao (phụ thuộc config)
- **Bằng chứng:** `go_run2` L829 chỉ MR6500; HH4K chỉ `go_run3` L971
- **Tại sao quan trọng:** Recipe HH4K + `is_sensor=True` chạy pipeline sai.
- **Cách sửa đề xuất:** Vision dispatcher dùng chung.

### Rủi ro: SKY không thể đến trong chế độ sensor

- **Mức độ:** Cao (phụ thuộc config)
- **Bằng chứng:** go_run2 L829 MR6500; SKY chỉ go_run3 L1034
- **Tại sao quan trọng:** Recipe SKY + is_sensor=True chạy pipeline sai
- **Cách sửa đề xuất:** Vision dispatcher dùng chung

---

## Phase 7 — Rủi ro Pipeline Cisco

### Rủi ro: `ocr_8P_result` chưa khởi tạo trước poll STEP 1

- **Mức độ:** Cao
- **Bằng chứng:** `call_backlog` L3453 đặt khi có signal; poll L3748 `if self.ocr_8P_result==[]` — không có mặc định `__init__`
- **Tại sao quan trọng:** `AttributeError` ở lần test Cisco đầu nếu callback trễ.
- **Cách sửa đề xuất:** Khởi tạo `[]` khi init class hoặc khi vào STEP 1.

### Rủi ro: Runthread emit danh sách rỗng trong busy loop

- **Mức độ:** Trung bình
- **Bằng chứng:** L5528–5530 `while result==[]: self.signal.emit(result)` trước PaddleOCR L5534
- **Tại sao quan trọng:** Race với vòng poll L3747; kết quả rỗng giả.
- **Cách sửa đề xuất:** Chỉ emit khi OCR hoàn tất (xem thêm rủi ro Runthread L5529).

### Rủi ro: SN_8P cũ khi upload SFIS fail

- **Mức độ:** Cao
- **Bằng chứng:** `SN_8P` đặt L3935/L4055 chỉ khi STEP 1 thành công đầy đủ; fail upload go_run3 L1358/L1385 dùng `self.SN_8P` vô điều kiện
- **Tại sao quan trọng:** Bản ghi fail MES có thể gắn SN DUT trước.
- **Cách sửa đề xuất:** Xóa `SN_8P` khi bắt đầu chu kỳ; guard upload.

### Rủi ro: Exception upload SFIS fail STEP 2 có thể bỏ qua wait_test

- **Mức độ:** Cao
- **Bằng chứng:** go_run3 L1357–1362 — `data_upload` không trong try/except; `wait_test=True` L1362 ngay sau (step1 fail có try L1382)
- **Tại sao quan trọng:** Exception SFIS → treo giống đường exception HH4K.
- **Cách sửa đề xuất:** try/finally với `wait_test=True`.

### Rủi ro: Timeout poll OCR rồi index kết quả rỗng

- **Mức độ:** Cao
- **Bằng chứng:** L3747–3755 tối đa 60×0.5s; không nhánh fail; L3830 `self.ocr_8P_result[0]`
- **Tại sao quan trọng:** Exception hoặc fail mơ hồ sau 30s chờ OCR.
- **Cách sửa đề xuất:** Timeout rõ ràng → `step1=False`.

### Rủi ro: pyzbar decode ROI `ocr` cuối cùng

- **Mức độ:** Trung bình
- **Bằng chứng:** L3543 `pyzbar.decode(cut_img_step1)` — `cut_img_step1` ghi đè mỗi nhãn `ocr` L3478–3487
- **Tại sao quan trọng:** Vùng barcode sai nếu recipe có nhiều shape `ocr`.
- **Cách sửa đề xuất:** Nhãn barcode riêng trong `barcode_point`.

### Rủi ro: Tên hàm Cisco dùng chung vs 12 model

- **Mức độ:** Thấp (bảo trì)
- **Bằng chứng:** `show_image_C1000_8FP_E_2G_L` L3457; dispatch L1292 liệt kê 12 chuỗi `select_model`
- **Tại sao quan trọng:** Nhầm lẫn bảo trì; C1200/C1300 dùng số barcode khác (4 vs 5).
- **Cách sửa đề xuất:** Đổi tên/registry; ghi bảng biến thể trong `16_cisco_pipeline.md`.

### Rủi ro: Cisco không thể đến trong chế độ sensor

- **Mức độ:** Cao (phụ thuộc config)
- **Bằng chứng:** go_run2 L829 MR6500; Cisco chỉ go_run3 L1292
- **Tại sao quan trọng:** Recipe Cisco + `is_sensor=True` chạy pipeline sai.
- **Cách sửa đề xuất:** Vision dispatcher dùng chung.

---

## Phase 8 — Rủi ro Pipeline WP

### Rủi ro: `check_result_OK` không đặt khi route SFIS fail (WP STEP 1)

- **Mức độ:** Cao
- **Bằng chứng:** `show_image_WP` L4462–4466 route FAIL không gán `check_result_OK`; L4507 `if self.check_result_OK` — không có trong `__init__`
- **Tại sao quan trọng:** AttributeError hoặc True cũ từ test trước → cổng Cambrian sai.
- **Cách sửa đề xuất:** Mặc định `False` trên mọi đường route-fail; init ở cấp class.

### Rủi ro: Upload SFIS fail WP dùng `thissn="None"`

- **Mức độ:** Cao
- **Bằng chứng:** go_run3 L1457 `thissn="None"`; fail upload step1 L1668 `data_upload(self.thissn, ...)`
- **Tại sao quan trọng:** Fail MES gắn SN literal `"None"`.
- **Cách sửa đề xuất:** Bỏ qua upload trừ khi SN đã decode.

### Rủi ro: C9105AXW_E index pyzbar không guard rỗng

- **Mức độ:** Cao
- **Bằng chứng:** L4420 `barcodes[0].data.decode` — không kiểm tra `len(barcodes)`
- **Tại sao quan trọng:** IndexError khi thiếu barcode.
- **Cách sửa đề xuất:** Nhánh barcode rỗng → `checksn=False`.

### Rủi ro: Exception upload SFIS fail step2–6 WP có thể bỏ qua wait_test

- **Mức độ:** Cao
- **Bằng chứng:** go_run3 L1546–1550 (và L1570, L1594, L1618, L1642) — `data_upload` không try; `wait_test` sau
- **Tại sao quan trọng:** Cùng mẫu treo như Cisco step2 fail L1357.
- **Cách sửa đề xuất:** try/finally với `wait_test=True`.

### Rủi ro: C9105AXW_E dùng chung đường dẫn hardcode `WP_check_stepN.json`

- **Mức độ:** Trung bình
- **Bằng chứng:** L4552, L4619, L4650, L4681 — `point/WP_check_step*.json` cho cả hai model
- **Tại sao quan trọng:** ROI sai nếu hình học C9105AXW_E khác WP_check.
- **Cách sửa đề xuất:** File point riêng theo model trong recipe.

### Rủi ro: WP không thể đến trong chế độ sensor

- **Mức độ:** Cao (phụ thuộc config)
- **Bằng chứng:** go_run2 L829 MR6500; WP go_run3 L1456
- **Tại sao quan trọng:** Recipe WP + `is_sensor=True` chạy pipeline sai.
- **Cách sửa đề xuất:** Dispatcher dùng chung.

---

## Phase 9 — Rủi ro Pipeline Nanook

### Rủi ro: PaddleOCR tạo trên luồng UI mỗi chu kỳ Nanook

- **Mức độ:** Cao (UX)
- **Bằng chứng:** `go_run3` L1685–1686 `self.nanook_ocr = PaddleOCR(...)` trước nhắc STEP
- **Tại sao quan trọng:** Chặn UI khi tải model OCR mỗi DUT.
- **Cách sửa đề xuất:** Singleton khi tải model / init nền.

### Rủi ro: Index kết quả OCR không guard rỗng (STEP 3 / 5)

- **Mức độ:** Cao
- **Bằng chứng:** L4944 `result[0][0][1][0]`; L5023 `result_beside[0][0][1][0]`
- **Tại sao quan trọng:** OCR rỗng → exception; step không đặt → fail path hoặc UI mơ hồ.
- **Cách sửa đề xuất:** Validate cấu trúc OCR trước khi index.

### Rủi ro: STEP 3 luôn đặt `step3=True` không validate OCR model

- **Mức độ:** Cao (chất lượng)
- **Bằng chứng:** L4951 sau OCR; không kiểm tra thành viên vs `nanook_model_tan`
- **Tại sao quan trọng:** OCR xấu vẫn tiến; STEP 5 có thể KeyError L5024.
- **Cách sửa đề xuất:** Cổng `step3` trên chuỗi model đã biết.

### Rủi ro: Upload SFIS fail Nanook với `thissn="None"`

- **Mức độ:** Cao
- **Bằng chứng:** L1684 `thissn="None"`; fail upload L1897 / L1775
- **Tại sao quan trọng:** Fail MES với literal `"None"`.
- **Cách sửa đề xuất:** Bỏ qua upload trừ khi SN đã decode.

### Rủi ro: Exception SFIS fail Nanook step2–6 có thể bỏ qua wait_test

- **Mức độ:** Cao
- **Bằng chứng:** L1774–1779 (và L1798, L1822, L1846, L1870) — không try; `wait_test` sau upload
- **Tại sao quan trọng:** Treo khi lỗi SFIS (cùng mẫu WP/Cisco).
- **Cách sửa đề xuất:** try/finally với `wait_test=True`.

### Rủi ro: Cambrian tắt STEP 6 auto-pass không SFIS / updatecount

- **Mức độ:** Trung bình–Cao
- **Bằng chứng:** L5155–5156 `self.step6=True` ngoài khối Pass UI/upload L5112–5148
- **Tại sao quan trọng:** Chu kỳ tiếp tục như pass không có hạch toán Pass MES/local.
- **Cách sửa đề xuất:** Yêu cầu Cambrian cho Nanook hoặc mirror tác dụng phụ Pass.

### Rủi ro: KeyError `nanook_model_tan` khi OCR model không xác định

- **Mức độ:** Trung bình
- **Bằng chứng:** L109 chỉ `C1100TG-1N32A`; L5024 `nanook_model_tan[self.nanook_ocr_model]`
- **Tại sao quan trọng:** Exception giữa STEP 5.
- **Cách sửa đề xuất:** Kiểm tra thành viên rõ ràng → `step5=False`.

### Rủi ro: Chế độ sensor + Nanook → MR6500

- **Mức độ:** Cao (phụ thuộc config)
- **Bằng chứng:** go_run2 L829; Nanook chỉ go_run3 L1683
- **Tại sao quan trọng:** Pipeline sai nếu `is_sensor=True`.
- **Cách sửa đề xuất:** Dispatcher dùng chung.

---

## Phase 10 — Rủi ro Pipeline Button_check

### Rủi ro: Upload SFIS fail dùng `thissn` thay vì `scaninfo`

- **Mức độ:** Nghiêm trọng (MES)
- **Bằng chứng:** go_run3 L1441 `data_upload(self.thissn, ...)`; vision Button_check dùng `scaninfo` cho route/pass upload L4247, L4313; **`thissn` không bao giờ đặt** trong đường Button_check
- **Tại sao quan trọng:** Bản ghi fail có thể gắn SN từ test SKY/Nanook/WP/Cisco trước, không phải nhãn đã scan.
- **Cách sửa đề xuất:** Dùng `scaninfo` cho fail upload; reset/xóa khi vào nhánh.

### Rủi ro: Upload fail vs pass Button_check không nhất quán SN

- **Mức độ:** Nghiêm trọng
- **Bằng chứng:** Pass L4313 `data_upload(self.scaninfo)`; fail go_run3 L1441 `self.thissn`
- **Tại sao quan trọng:** Pass/fail MES cùng DUT có thể tham chiếu SN khác nhau.
- **Cách sửa đề xuất:** Một biến SN (`scaninfo`) cho mọi lệnh gọi SFIS Button_check.

### Rủi ro: Từ chối "Flip model" không xác nhận thoát làm treo vòng lặp

- **Mức độ:** Cao
- **Bằng chứng:** go_run3 L1450–1454 — `wait_test`/`stop_program` chỉ khi QMessageBox Thoát Accept; chỉ Reject Flip không đặt gì; `wait_test=False` từ startprogram L713
- **Tại sao quan trọng:** Operator không thể bắt đầu DUT tiếp mà không Stop.
- **Cách sửa đề xuất:** Đặt `wait_test=True` khi từ chối Flip hoặc nhắc lại.

### Rủi ro: `check_result_OK` không reset khi vào nhánh Button_check

- **Mức độ:** Cao
- **Bằng chứng:** L1401 chỉ reset `step1`; `check_result_OK` đặt trong khối route SKY/WP; Button_check đọc L4291 không init
- **Tại sao quan trọng:** True cũ từ test trước có thể chạy Cambrian sau route fail.
- **Cách sửa đề xuất:** `self.check_result_OK=False` khi bắt đầu nhánh.

### Rủi ro: Button_check không thể đến trong chế độ sensor

- **Mức độ:** Cao (phụ thuộc config)
- **Bằng chứng:** go_run2 L829 MR6500; Button_check chỉ go_run3 L1400; go_run1 scan vẫn chạy L737
- **Tại sao quan trọng:** Scan thu SN rồi chạy pipeline vision sai.
- **Cách sửa đề xuất:** Dispatcher dùng chung; ghi yêu cầu `is_sensor=False`.

### Rủi ro: Scan operator rỗng được chấp nhận

- **Mức độ:** Trung bình
- **Bằng chứng:** go_run1 L770–775 chấp nhận mọi text kể cả chuỗi rỗng; không trim/validate
- **Tại sao quan trọng:** Route/upload SFIS với SN rỗng.
- **Cách sửa đề xuất:** Từ chối scan rỗng trong vòng dialog.

### Rủi ro: cambrian_space None khi exception (Button_check)

- **Mức độ:** Cao
- **Bằng chứng:** L2643–2645 except không return; L4298 `if yolo_step1 == "Pass"` / `elif == "Fail"` — None rơi qua; step1 vẫn False → go_run3 fail (không crash vision)
- **Tại sao quan trọng:** Fail mơ hồ không có overlay Cambrian; đường xử lý fail trùng.
- **Cách sửa đề xuất:** Return `"Fail"` trong except; giống rủi ro SKY L2643.

### Rủi ro: Exception show_image_Button_check không Pass/Fail trong vision

- **Mức độ:** Trung bình
- **Bằng chứng:** L4375–4377 except chỉ log; go_run3 L1425+ vẫn Fail+count nếu step1 False
- **Tại sao quan trọng:** Không có Fail UI local trong vision; điều phối bù.
- **Cách sửa đề xuất:** Đặt step1=False rõ trong except; Fail UI tùy chọn.

### Rủi ro: Cambrian Pass rỗng khi danh sách ROI ximian trống

- **Mức độ:** Trung bình
- **Bằng chứng:** Không có shape `ximian` → `step1_check` rỗng; `cambrian_space` L2635 `False not in []` → `"Pass"`
- **Tại sao quan trọng:** False pass không có vùng kiểm tra.
- **Cách sửa đề xuất:** Fail nếu zero ROI trước inference.

### Rủi ro: Mã fail SFIS Button_check BDFA01 vs SKY BDFA0

- **Mức độ:** Trung bình (nhất quán MES)
- **Bằng chứng:** Button_check L1442 `BDFA01`; SKY L1150 `BDFA0` (không có số 1 cuối)
- **Tại sao quan trọng:** Phân loại lỗi không nhất quán giữa sản phẩm.
- **Cách sửa đề xuất:** Tập trung mã lỗi theo spec sản phẩm.

### Rủi ro: Trạng thái xác minh WIP (comment header)

- **Mức độ:** Trung bình
- **Bằng chứng:** L4 `Button_check也一樣，目前僅供驗證`
- **Tại sao quan trọng:** SFIS/inference có thể chưa đầy đủ cho sản xuất.
- **Cách sửa đề xuất:** Theo dõi hoàn thiện so với parity MR6500/SKY.

---

## Phase 11 — Rủi ro Ranh giới Bên ngoài

### Rủi ro: Lệnh gọi SFIS MR6500 không có guard `sfis_choose`

- **Mức độ:** Nghiêm trọng
- **Bằng chứng:** L2032–2035 `self.mysfis.get_sfis_SN` / `get_sfis_90` vô điều kiện; `mysfis` chỉ tạo khi `is_open==true` L166–168
- **Tại sao quan trọng:** `sfis_choose=False` (offline/test) vẫn crash MR6500 sau decode barcode thành công.
- **Cách sửa đề xuất:** Guard mọi lệnh gọi SFIS; fallback offline cho liaohao.

### Rủi ro: Cambrian tắt nhưng vẫn cần `self.client`

- **Mức độ:** Nghiêm trọng
- **Bằng chứng:** Model JSON `is_cambrian:false` → không `self.client` L290–293; SKY/Cisco/WP/Button_check gọi `get_inference_result` không kiểm tra `cambrian_is_open`; chỉ Nanook có bypass L4818+
- **Tại sao quan trọng:** Recipe Cambrian tắt crash ở bước inference đầu.
- **Cách sửa đề xuất:** Cổng mọi lệnh gọi `get_inference_result`; hoặc luôn tạo stub client.

### Rủi ro: Hai instance camera — `mycamera` không bao giờ đóng

- **Mức độ:** Trung bình
- **Bằng chứng:** `mycamera` L209 chỉ discovery; `ekkoshan` L662 đóng L5402; không `mycamera.close_camera()`
- **Tại sao quan trọng:** Có thể rò handle Basler trên kiosk chạy lâu.
- **Cách sửa đề xuất:** Đóng instance discovery khi thoát; một camera manager.

### Rủi ro: Combo `change_camera` là stub

- **Mức độ:** Trung bình
- **Bằng chứng:** L606–607 no-op; `comboBox_2` điền L218 nhưng lựa chọn bị bỏ qua khi chụp
- **Tại sao quan trọng:** UI gợi ý đổi camera; không có tác dụng.
- **Cách sửa đề xuất:** Nối với device ID `basler_my` hoặc ẩn control.

### Rủi ro: Thư mục `source/` app không tạo

- **Mức độ:** Cao
- **Bằng chứng:** Nhiều `cv2.imwrite("source/...")` (SKY L2831+, Cisco L3487+, Nanook L4934+); không `os.makedirs("source")` trong `__init__`
- **Tại sao quan trọng:** Lần chạy OCR/Cisco đầu fail nếu thiếu thư mục.
- **Cách sửa đề xuất:** Tạo `source/`, `source/8P/` khi khởi động.

### Rủi ro: Tải model PaddleOCR chặn luồng UI

- **Mức độ:** Cao
- **Bằng chứng:** SKY STEP 3 L2864; nhánh Nanook L1685; Cisco sync L3530; Runthread chỉ giúp ocr1/2
- **Tại sao quan trọng:** Đơ vài giây mỗi DUT/bước; Stop trễ.
- **Cách sửa đề xuất:** Singleton dịch vụ OCR; init nền.

### Rủi ro: Init SFIS bare except + sys.exit

- **Mức độ:** Trung bình
- **Bằng chứng:** L174–177; che lỗi mạng/xác thực
- **Tại sao quan trọng:** Khó chẩn đoán vấn đề SFIS triển khai.
- **Cách sửa đề xuất:** Log traceback; chế độ offline cấu hình được không thoát.

### Rủi ro: `todaytime` global đóng băng khi import

- **Mức độ:** Thấp–Trung bình
- **Bằng chứng:** L47 đặt một lần khi tải module; dùng cho log/đường lưu L612, L345+
- **Tại sao quan trọng:** App chạy qua nửa đêm ghi vào thư mục ngày trước.
- **Cách sửa đề xuất:** Tính lại ngày mỗi lần lưu hoặc timer hàng ngày.

### Rủi ro: Cleanup stopprogram nuốt mọi lỗi

- **Mức độ:** Trung bình
- **Bằng chứng:** L5400–5404 bare `except: pass` khi dispose IO/camera
- **Tại sao quan trọng:** Lỗi cleanup im lặng; rò tài nguyên không phát hiện.
- **Cách sửa đề xuất:** Log exception; guard dispose idempotent.

### Rủi ro: Gói triển khai không version trong repo

- **Mức độ:** Cao
- **Bằng chứng:** Workspace chỉ chứa `sky.py`; 15+ module/đường dẫn bên ngoài ghi trong `07_camera_io_sfis.md`
- **Tại sao quan trọng:** Không tái tạo môi trường sản xuất chỉ từ repo.
- **Cách sửa đề xuất:** Manifest triển khai; ghim requirements.txt; ship bundle sample/point theo model.

---

## Bảng Tóm tắt Rủi ro

| Danh mục | Số lượng | Mức độ cao nhất |
|----------|-------|------------------|
| Lỗi runtime | 4 | Import IoCard |
| Lỗi logic | 4+ | go_run2 hardcode MR6500 |
| UI/threading | 3 | Vòng lặp chặn luồng UI |
| Khả năng bảo trì | 3 | Class khổng lồ |
| Sản xuất | 4+ | Thiếu dependency |
| Theo pipeline | 30+ | SN/SFIS/treo (Phase 4–10) |
| Ranh giới bên ngoài | 10 | SFIS MR6500 không guard; crash Cambrian tắt |

**Lộ trình cải tiến:** `11_refactor_plan.md` (Phase 12) — sửa an toàn Tháng 1, kế hoạch tăng dần Q1–Q4.
