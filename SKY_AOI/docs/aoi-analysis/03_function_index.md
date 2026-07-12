# Chỉ mục hàm

File: `sky.py` (~5.571 dòng). Mức quan trọng: **Cao** / **Trung bình** / **Thấp**.

## Class cấp module

| Hàm | Class | Vai trò | Được gọi bởi | Gọi | Mức quan trọng | Ghi chú |
|-----|-------|---------|--------------|-----|-----------------|---------|
| — | `Uihand` | Trung tâm tín hiệu | `Demo.__init__` | (chỉ emit) | Cao | test1/2/3, textbox, clear_show |
| `run` | `Mytest` | Emit timeout | (đã comment) | timeout.emit | Thấp | Không dùng |
| `decode` | `ReadDataMatrixCode` | Giải mã DataMatrix | show_image_MR6500 | pylibdmtx.decode | Trung bình | |
| `getISN` | `ReadDataMatrixCode` | Trả chuỗi ISN | show_image_MR6500 | — | Trung bình | |
| `run` | `Runthread` | Worker PaddleOCR | Tín hiệu QThread | PaddleOCR.ocr | Trung bình | OCR C1000 bất đồng bộ |
| `__init__` | `Scan` | Dialog quét | — | — | Thấp | Lỗi: tên thuộc tính sai L5495 |
| `layout_init` | `Scan` | Bố cục dialog | Scan.__init__ | — | Thấp | |

## Demo — Khởi tạo & Cấu hình

| Hàm | Class | Vai trò | Được gọi bởi | Gọi | Mức quan trọng | Ghi chú |
|-----|-------|---------|--------------|-----|-----------------|---------|
| `__init__` | Demo | Khởi tạo app | main | create_log, SFIS, camera, JSON, tín hiệu | Cao | L146 |
| `get_rightnow` | Demo | Thêm log vào UI | nhiều nơi | text_browser.append | Trung bình | |
| `choose_route` | Demo | Chọn thư mục lưu ảnh | pushButton_4 | QFileDialog, config.json | Trung bình | |
| `clearcount` | Demo | Đặt lại bộ đếm | pushButton_5 | lineEdit, count JSON | Thấp | |
| `updatecount` | Demo | Cập nhật thống kê đạt/không đạt | show_image_* | lineEdit, ghi JSON | Cao | |
| `get_version` | Demo | Phiên bản model Cambrian | __init__, choose_model | client.get_version_json | Trung bình | |
| `choose_model` | Demo | Nạp file công thức | actionchoose | JSON, SampleClientV2 | Cao | |
| `resultcolor` | Demo | Màu Đạt/Không đạt/Chờ | nhiều nơi | stylesheet label_6 | Trung bình | |
| `change_language` | Demo | Chuyển i18n | comboBox_1 | QTranslator | Thấp | |
| `change_camera` | Demo | Handler combo camera | comboBox_2 | — | Thấp | Stub: thân `1` |
| `create_log` | Demo | Thiết lập log file | __init__ | logging.basicConfig | Trung bình | |
| `savelog` | Demo | Lưu log | — | — | Thấp | Stub: thân `1` |
| `get_inference_result` | Demo | Phân loại batch Cambrian | show_image_* | client.predict_images | Cao | |
| `trainstart` | Demo | Dump cấu hình debug | pushButton_1 | print | Thấp | |

## Demo — Điều phối

| Hàm | Class | Vai trò | Được gọi bởi | Gọi | Mức quan trọng | Ghi chú |
|-----|-------|---------|--------------|-----|-----------------|---------|
| `startprogram` | Demo | Vòng lặp kiểm thử chính | pushButton_2 | camera, IoCard, emit go_run* | Cao | while True chặn luồng |
| `clear_showing` | Demo | Xóa trường kết quả | Uihand.clear_show | resultcolor | Thấp | |
| `go_run1` | Demo | Quét nhãn / bỏ qua | Uihand.test1 | QInputDialog | Cao | |
| `go_run2` | Demo | Poll sensor + chụp | Uihand.test2 | IoCard, get_image, show_image_MR6500 | Cao | Hardcode MR6500 |
| `go_run3` | Demo | Phân phối model + thị giác | Uihand.test3 | get_image, show_image_* | Cao | L834–1912 |
| `stopprogram` | Demo | Dừng phiên kiểm thử | pushButton_3 | IoCard dispose, close_camera | Cao | |
| `closeEvent` | Demo | Dọn dẹp khi đóng cửa sổ | Qt | giống stop | Trung bình | |

## Demo — Pipeline thị giác

| Hàm | Class | Vai trò | Được gọi bởi | Gọi | Mức quan trọng | Ghi chú |
|-----|-------|---------|--------------|-----|-----------------|---------|
| `show_image` | Demo | Cambrian từ đường dẫn file | — | get_inference_result | Thấp | Mã chết |
| `show_image_MR6500` | Demo | MR6500: DM + SFIS + hash | go_run2, go_run3 | ReadDataMatrixCode, mysfis, pHash | Cao | |
| `show_image_HH4K` | Demo | So sánh HH4K 4 bước | go_run3 | HH4K_compare | Cao | |
| `yolov5_inference` | Demo | Phân loại ROI YOLO | show_image_SKY (nội bộ) | predict_change.run | Trung bình | Import đã comment |
| `cambrian_space` | Demo | Vẽ kết quả Cambrian | show_image_SKY | cv2 | Trung bình | |
| `show_image_SKY` | Demo | Pipeline SKY 6 bước | go_run3 | pyzbar, PaddleOCR, get_inference_result | Cao | |
| `show_image_SKY_yolo` | Demo | Biến thể SKY YOLO | — | yolov5_inference | Thấp | Mã chết |
| `call_backlog` | Demo | Callback luồng OCR | Runthread.signal | Cập nhật UI | Trung bình | |
| `call_backlog1` | Demo | Callback luồng OCR 2 | Runthread.signal | Cập nhật UI | Trung bình | |
| `show_image_C1000_8FP_E_2G_L` | Demo | Cisco C1000/C1200/C1300 | go_run3 | pyzbar, PaddleOCR, Runthread, Cambrian | Cao | Tên legacy |
| `show_image_Button_check` | Demo | Kiểm tra nút | go_run3 | get_inference_result | Trung bình | |
| `show_image_WP` | Demo | Kiểm tra WP / C9105 | go_run3 | pyzbar, get_inference_result | Cao | |
| `show_image_Nanook` | Demo | Nanook nhiều bước | go_run3 | PaddleOCR, pyzbar, Cambrian | Cao | |
| `ocr_finction_8P` | Demo | Helper OCR cho 8P | show_image_C1000 | PaddleOCR | Trung bình | Lỗi chính tả tên |
| `UI_show` | Demo | Hiển thị ảnh trong bảng | hàm thị giác | QPixmap | Trung bình | |

## Demo — So sánh / Hash

| Hàm | Class | Vai trò | Được gọi bởi | Gọi | Mức quan trọng | Ghi chú |
|-----|-------|---------|--------------|-----|-----------------|---------|
| `HH4K_compare` | Demo | So sánh ROI với mẫu | show_image_HH4K | pHash, PIL ImageChops | Cao | |
| `cmHash` | Demo | Độ tương đồng hash | MR6500, HH4K | numpy | Trung bình | |
| `pHash` | Demo | Hash cảm nhận | MR6500, HH4K | cv2 resize, dct | Trung bình | |
