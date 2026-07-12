# Luồng và UI

Phân tích mô hình đồng thời trong `sky.py`.

## Quyền sở hữu luồng UI

| Chạy trên luồng UI | Bằng chứng |
|--------------------|------------|
| Toàn bộ app Qt | `app.exec_()` L5563 |
| Vòng lặp `while` của `startprogram()` | Gọi từ slot `pushButton_2.clicked` — cùng luồng |
| `go_run1/2/3` | Kết nối qua tín hiệu Uihand — cùng luồng |
| Mọi `show_image_*` | Gọi đồng bộ từ go_run3 |
| Hầu hết lệnh gọi PaddleOCR | Nhúng inline trong hàm thị giác |
| Cambrian `get_inference_result` | HTTP/RPC đồng bộ trong thị giác |
| Poll sensor `go_run2` | `while not stop_program` trên luồng UI L796 |

**Kết luận:** Hầu như toàn bộ logic AOI chạy trên **luồng chính Qt (UI)**.

## Cấu trúc chặn luồng

| Cấu trúc | Vị trí | Ảnh hưởng |
|----------|--------|-----------|
| `while True` | `startprogram` L687, L703 | Chặn UI suốt phiên kiểm thử |
| `while True` | `go_run1` Button_check L738 | Chặn đến khi quét OK/hủy |
| `while not stop_program` | `go_run2` L796 | Busy-poll sensor |
| `time.sleep(5)` | `go_run2` L813 | UI đóng băng 5s sau kích sensor |
| `QMessageBox.question` | prompt bước go_run3 | Modal — chặn đến khi người dùng nhấn |
| `QInputDialog` | go_run1, ipex_check | Modal |
| `input_dialog.exec_()` | go_run1 L770 | Modal |

## QApplication.processEvents()

Dùng để giữ UI phản hồi trong công việc chặn luồng:

| Vùng | Dòng (mẫu) |
|------|------------|
| go_run2 | L798 |
| go_run3 | L835, L864, L876, L880, L955 |
| yolov5_inference | L2547 |
| show_image_C1000_* | L3528, L3540, L3567+ (nhiều) |

**Mẫu:** Workaround tái nhập thủ công — không phải đa luồng thật. Rủi ro tác dụng phụ vòng lặp sự kiện lồng nhau.

## Dùng QThread

### Runthread + QThread (nhánh OCR C1000)

```text
show_image_C1000_8FP_E_2G_L (xấp xỉ L3500)
  self.thread = QThread(self)
  self.myT = Runthread(ocr_img)
  self.myT.moveToThread(self.thread)
  self._startThread.connect(self.myT.run)
  self.myT.signal.connect(self.call_backlog)
  self.thread.start()
  self._startThread.emit()
```

- `Runthread.run()` (L5527): chạy PaddleOCR, emit kết quả qua tín hiệu.
- Luồng thứ hai `thread1` / `myT1` cho OCR song song trên một số nhánh C1000 (L3515+).

**Lưu ý:** Caller vẫn có thể chặn chờ kết quả OCR tùy logic phía sau (cần xác minh Giai đoạn 4 cho điểm đồng bộ chính xác).

### Mytest (không dùng)

```text
# L679-681 đã comment:
# self.mytest = Mytest()
# self.mytest.timeout.connect(self.go_run)
# self.mytest.start()
```

### threading.Thread (không dùng)

```text
# L683-685 đã comment:
# main_thread = threading.Thread(target=self.go_run, name="main_proc")
```

## Tóm tắt suy luận bất đồng bộ

| Thành phần | Bất đồng bộ? | Cơ chế |
|------------|--------------|--------|
| Cambrian AI | Không | `client.predict_images` đồng bộ |
| YOLO | Không | `predict_change.run` đồng bộ + chdir |
| PaddleOCR (hầu hết nhánh) | Không | Khởi tạo inline |
| PaddleOCR (C1000) | Một phần | QThread + callback tín hiệu |
| Chụp camera | Không | `get_image()` đồng bộ |
| Poll IO | Không | Vòng lặp đồng bộ trên luồng UI |

## Rủi ro đóng băng UI

| Rủi ro | Mức độ | Bằng chứng |
|--------|--------|------------|
| `startprogram` while True trên luồng UI | **Cao** | L687 — cả phiên chặn idle Qt bình thường |
| Busy-poll sensor | Trung bình | L796–798 — quay CPU + processEvents |
| sleep 5s trên luồng UI | **Cao** | L813 |
| Thị giác nặng trên luồng UI | **Cao** | OCR + suy luận trong show_image_* |
| Dialog bước modal | Trung bình | Người vận hành phải nhấn từng BƯỚC |
| Tái nhập processEvents | Trung bình | Có thể kích hoạt slot lồng nhau trong lúc thị giác |

## Đề xuất (Chỉ tài liệu — Không đổi mã)

1. Chuyển vòng lặp `startprogram` sang worker `QThread` hoặc máy trạng thái điều khiển bởi timer.
2. Thay busy-poll sensor bằng `QTimer` + đọc IO không chặn.
3. Bỏ `time.sleep(5)` — dùng cấu hình trễ kích phần cứng hoặc timer bất đồng bộ.
4. Chuẩn hóa OCR/suy luận trên thread pool với mẫu future/callback.

Theo dõi tái cấu trúc chi tiết → `11_refactor_plan.md` (Giai đoạn 5).

---

# Giai đoạn 2 — Rủi ro luồng điều phối

## Đường dẫn chặn luồng

Toàn bộ điều phối chạy đồng bộ trên luồng UI:

```text
slot pushButton_2 → startprogram [while True]
  → go_run1 [while True cho Button_check]
  → go_run2 [while not stop_program] + sleep(5)
  → go_run3 [chuỗi QMessageBox modal + get_image đồng bộ]
```

`stopprogram` và `closeEvent` chỉ đặt `stop_program=True` — không gỡ chặn sleep hoặc dialog đang chạy.

## Dùng processEvents

| Hàm | Dòng | Mục đích |
|-----|------|----------|
| `go_run2` | L798 | Giữ UI sống trong spin-wait sensor |
| Vào `go_run3` | L835 | Ép refresh trước phân phối |
| `go_run3` ipex_check | L864, L876, L880, L955 | Trong thị giác inline |

Điều phối **không** gọi `processEvents` trong vòng lặp `while` của `startprogram` — chỉ bên trong hàm con.

## Dialog modal (điều phối)

| Dialog | Hàm | Chặn Dừng? |
|--------|-----|------------|
| "Please enter for test" | startprogram thủ công L705 | Có, đến khi người dùng nhấn |
| QMessageBox "BƯỚC N" | go_run3 nhiều bước | Có, mỗi bước |
| "Flip the model" | Button_check L1405 | Có |
| QInputDialog quét | go_run1 L770 | Có |
| QInputDialog fallback barcode | ipex_check L912 | Có |

Khi modal mở, `stop_program` không được poll.

## Đáp ứng Dừng

| Kịch bản | Phản hồi? | Bằng chứng |
|----------|-----------|------------|
| Chờ `wait_test` trong startprogram | Lần lặp tiếp theo | L688 kiểm tra `stop_program` |
| Trong sleep(5) go_run2 | **Không** | L813, không kiểm tra stop |
| Trong poll IO go_run2 | Một phần | L796 kiểm tra `stop_program` mỗi lần lặp |
| Trong QMessageBox go_run3 | **Không** | Modal chặn |
| Sau nhấn stopprogram | Trễ đến khi công việc hiện tại kết thúc | L5399 chỉ đặt cờ |

`stopprogram` bare `except: pass` (L5403) — lỗi dọn dẹp bị bỏ qua im lặng; bật lại Bắt đầu phụ thuộc break vòng lặp.

## Cải thiện tối thiểu an toàn

*(Chỉ tài liệu — không đổi mã trong Giai đoạn 2)*

1. **Poll `stop_program` trong `go_run2` trước/sau sleep** — thay `sleep(5)` bằng lát 500ms kiểm tra cờ (thay đổi hành vi rủi ro thấp nhất).
2. **Đặt `wait_test=True` trên mọi đường thoát go_run3** — gồm fail HH4K và nhánh else model không xác định (tránh treo vòng lặp).
3. **Trong `stopprogram`, gọi `pushButton_2.setEnabled(True)`** làm dự phòng nếu vòng lặp đã thoát bất thường.
4. **Định tuyến thị giác go_run2 qua cùng dispatcher với go_run3** — sửa pipeline sai mà không tái cấu trúc toàn bộ.
