# Pipeline Cisco — `show_image_C1000_8FP_E_2G_L`

Dòng: L3457–4218 (`sky.py`). Điều phối: nhánh Cisco `go_run3` L1292–1398. Helper: `Runthread` L5514–5538, `call_backlog`/`call_backlog1` L3452–3456, `get_inference_result` L630, `cambrian_space` L2595, `UI_show` L5235.

Danh sách kiểm tra cấp module: L53–103 (`check_ocr_*`, `check_label_*`, `model_and_90` L106–107).

**Chế độ sensor:** Cisco **không** đến được qua `go_run2` (hardcode MR6500 L829). Cisco chỉ chạy **chế độ manual** qua `go_run3`.

---

## 1. Mục đích

`show_image_C1000_8FP_E_2G_L` là **pipeline AOI 2 bước dùng chung** cho 12 model switch Cisco (họ C1000 / C1200 / C1300). Dù tên hàm tham chiếu `C1000-8FP-E-2G-L`, mọi giá trị `select_model` liệt kê đều dispatch tới hàm này từ `go_run3` L1292–1340.

| Khía cạnh | Chi tiết |
|--------|--------|
| Pipeline dùng chung | Có — một hàm phân nhánh theo `self.select_model` cho quy tắc barcode, danh sách OCR và logic ROI |
| Tên gây nhầm | Lịch sử — hàm đặt theo biến thể đầu; xử lý mọi model Cisco trong chuỗi `elif` |
| STEP 1 | Mặt nhãn: pyzbar barcode + PaddleOCR (sync + QThread) + xác minh model mã 90 SFIS tùy chọn + Cambrian trên ROI `warn` |
| STEP 2 | Mặt trên/khác: Cambrian trên ROI `warn` từ `model_point` + OCR `topdate` tùy chọn (ngày 8 chữ số) |
| Engine AI | **Cambrian** qua `get_inference_result` + `cambrian_space` (biến đặt tên `yolo_stepN`) |

Comment header file L4 ghi triển khai 8P một phần — code sản xuất khá đầy đủ nhưng giữ tên legacy.

---

## 2. Model Hỗ trợ / Ánh xạ Dispatch

| select_model | Dòng nhánh | Pipeline | Ghi chú |
|--------------|------------:|----------|-------|
| C1000-8FP-E-2G-L | L1292 | `show_image_C1000_8FP_E_2G_L` | 4 barcode; OCR1+OCR2+OCR3 đầy đủ |
| C1000-8P-2G-L | L1292 | same | `check_label_C1000_8P_2G_L` |
| C1000-8T-2G-L | L1292 | same | |
| C1000-8FP-2G-L | L1292 | same | |
| C1000-8P-E-2G-L | L1292 | same | |
| C1000-8T-E-2G-L | L1292 | same | |
| C1200-8FP-2G | L1292 | same | 4 barcode; chỉ OCR1 + regex MfgDate; bypass ocr3 L3993 |
| C1200-8P-E-2G | L1292 | same | |
| C1200-8T-E-2G | L1292 | same | |
| C1300-8P-E-2G | L1292 | same | **5** barcode; index SN khác L3718–3729 |
| C1300-8T-E-2G | L1292 | same | |
| C1300-8FP-2G | L1292 | same | |

Cả 12 model dùng một điều kiện `elif` L1292 và điều phối giống hệt (2 lần chụp, 2 lần gọi vision).

---

## 3. Caller và Đường Điều khiển

### Caller của `show_image_C1000_8FP_E_2G_L`

| Caller | Dòng | Điều kiện | Sau return |
|--------|-----:|-----------|--------------|
| `go_run3` | L1332 | Nhánh Cisco, STEP 1 accept → `get_image` lần 1 | `step1==True` → prompt STEP 2; `step1==False` → fail UI + SFIS `BDFA01` + `wait_test=True` L1369–1392 |
| `go_run3` | L1340 | `step1==True`, STEP 2 accept → `get_image` lần 2 | `step2==True` → `wait_test=True` L1342; `step2==False` → fail UI + SFIS + `wait_test=True` L1343–1362 |

**Không có call site khác.**

### Điều phối `go_run3` (L1292–1398)

```text
reset step1=False, step2=False (L1293–1294)
QMessageBox STEP 1
  Reject → xác nhận thoát → wait_test + stop_program (L1394–1398)
  Accept → get_image → show_image_C1000_8FP_E_2G_L(..., "STEP 1")
    step1==True  → QMessageBox STEP 2
      Reject → xác nhận thoát → wait_test + stop_program (L1363–1367)
      Accept → get_image → show_image_C1000_8FP_E_2G_L(..., "STEP 2")
        step2==True  → wait_test=True (L1342)
        step2==False → Fail UI + SFIS BDFA01 + wait_test=True (L1343–1362)
    step1==False → Fail UI + SFIS BDFA01 (try/except) + wait_test=True (L1369–1392)
```

Khác HH4K, Cisco **có** handler `elif step1==False` và `elif step2==False` rõ với reset `wait_test`.

**Khoảng trống:** Nếu vision except trước khi đặt `step1`/`step2`, cờ vẫn `False` → handler fail chạy (chấp nhận được). Nếu STEP 2 except sau `step1=True` nhưng trước gán `step2`, `step2` vẫn `False` → handler fail step2 chạy.

---

## 4. Đầu vào

| Đầu vào | Nguồn | Dùng cho | Bắt buộc? | Rủi ro nếu thiếu |
|-------|--------|----------|-----------|-----------------|
| `image_numpy` | Camera qua `go_run3` | Cả hai bước | Có | Frame rỗng → decode/inference fail |
| `stepname` | Caller `"STEP 1"` / `"STEP 2"` | Bộ chọn nhánh L3464/L4104 | Có | Bước sai / no-op |
| `self.barcode_point["shapes"]` | Model JSON `barcode_path` | ROI STEP 1: nhãn `warn`, `ocr*` | Có | Thiếu shape → kiểm tra rỗng |
| `self.model_point["shapes"]` | Model JSON `model_path` | STEP 2: `warn*`, `topdate` | Có STEP 2 | `step2_check` rỗng → auto pass L4143–4146 |
| `self.select_model` | Model JSON | Danh sách barcode/OCR theo biến thể L3571+ | Có | Danh sách kiểm sai |
| `check_ocr_*` / `check_label_*` | Hằng module L53–103 | Chuỗi kỳ vọng theo model | Có | KeyError nếu model chưa nối |
| `model_and_90` | Dict module L106–107 | liaohao SFIS → chuỗi model | Nếu SFIS bật | Rủi ro lỗi cú pháp L106–107; KeyError liaohao không xác định |
| `self.client` | Init Cambrian | `get_inference_result` | Có cho bước AI | Fail nếu Cambrian tắt |
| `self.mysfis` | Init SFIS | `get_sfis_90` STEP 1; `data_upload` | Nếu `sfis_choose` | AttributeError nếu SFIS tắt nhưng vào nhánh |
| `self.sfis_choose` | config.json | Cổng kiểm model SFIS + upload | Không | Bypass offline L3947–3948 |
| `self.data` | Mẫu CSV L155 | Payload upload SFIS | Bước upload | — |
| `self.ocr_8P_result` / `ocr1_8P_result` | Signal `call_backlog*` | Khớp text OCR | STEP 1 C1000 | **Không khởi tạo trong `__init__`** — AttributeError nếu truy cập trước callback |
| `Runthread` + `QThread` | L3499–3524 | PaddleOCR async trên `source/8P/ocr1.jpg`, `ocr2.jpg` | Model C1000 | Race / timeout / `return` sớm L3506 |
| `pyzbar` | L3543 | Decode barcode 1D trên crop ROI `ocr` cuối | STEP 1 | ROI sai nếu nhiều nhãn `ocr` |
| `PaddleOCR` | Sync L3530 (ocr3), L4148 (topdate); async trong `Runthread` | OCR text nhãn | STEP 1/2 | Đơ UI khi tải model |
| `scaninfo` | — | **Không dùng** cho SN Cisco | — | — |

Đường tạm hardcode: `source/8P/ocr1.jpg`, `ocr2.jpg`, `ocr3.jpg`, `topdate.jpg`.

---

## 5. Đầu ra / Tác dụng phụ

| Tác dụng phụ | Vị trí | Điều kiện |
|-------------|-------|-----------|
| Lưu frame thô | L3460 | Mỗi lần gọi |
| JPG chú thích barcode/OCR | L3818+, L3852+, L3921+, L3996+, L4023+ | Mỗi sub-check pass |
| JPG pass/fail Cambrian | `cambrian_space` + `UI_show` | STEP 1 warn / STEP 2 warn |
| Composite ALL PASS | L4191–4193 | STEP 2 cả hai sub-check pass |
| `tableWidget` qua `UI_show` | Nhiều chỗ | Hàng 6 cột 1–6 |
| `lineEdit_8` | L3936, L4056 | `SN_8P` sau barcode+OCR pass |
| `lineEdit_9` | Chỉ fail go_run3 L1347, L1373 | `"Fail"` khi fail điều phối |
| `resultcolor` + `updatecount` | L4197–4203 | Chỉ pass tổng hợp STEP 2 (trong vision) |
| Đếm Fail UI | go_run3 L1349–1356, L1375–1381 | fail step1/step2 |
| `step1` | L3946–3952, L4067–4073, L4088 | Pass/fail có cổng; kiểm SFIS model có thể chặn L3944–3946 |
| `step2` | L4208, L4213 | `True` chỉ khi `step2_1 and step2_2` L4188 |
| Upload SFIS pass | L4204–4207 | STEP 2 pass + `sfis_choose` — **không mã lỗi** |
| Upload SFIS fail | go_run3 L1357–1359, L1384–1386 | `error="BDFA01"` |
| `wait_test` | Chỉ go_run3 | Không đặt trong hàm vision |
| Log / textbox | Xuyên suốt | — |

---

## 6. Luồng Từng bước

### Luồng điều phối

1. `go_run3` L1292: khớp bất kỳ giá trị `select_model` Cisco nào trong 12.
2. Reset `step1`, `step2` thành `False`.
3. QMessageBox STEP 1 → `get_image` → `show_image_C1000_8FP_E_2G_L(shan1, "STEP 1")`.
4. Nếu `step1==True`: QMessageBox STEP 2 → `get_image` → `show_image_C1000_8FP_E_2G_L(shan2, "STEP 2")`.
5. Nếu `step2==True`: `wait_test=True` L1342.
6. Đường fail đặt UI + SFIS tùy chọn + `wait_test=True`.

### Luồng vision — STEP 1 (`stepname=="STEP 1"` L3464)

1. Frame grayscale; lặp shape `barcode_point`:
   - `warn` → crop cho Cambrian `step1_check`
   - `ocr*` → crop, xoay 90° tùy chọn (model C1000 L3483–3485), lưu `source/8P/{label}.jpg`
2. Khởi động `Runthread` trên `ocr1.jpg` (QThread + signal L3499–3510).
3. **Chỉ model C1000:** `Runthread` thứ hai trên `ocr2.jpg` L3514–3524; PaddleOCR sync trên `ocr3.jpg` L3530–3533.
4. `pyzbar.decode(cut_img_step1)` — dùng crop ROI `ocr` **cuối** từ vòng lặp L3543.
5. Validate barcode theo model (4 hoặc 5 mã) L3571–3745; đặt `step1_1=True` khi khớp.
6. SFIS tùy chọn: `get_sfis_90(PVN barcode)` → đối chiếu `model_and_90[liaohao]` → `step1_sfis=True` L3581–3593+.
7. Poll tối đa 60×0.5s cho `ocr_8P_result` / `ocr1_8P_result` L3747–3766.
8. Nếu `step1_1`:
   - **C1000:** Khớp nhãn OCR3 → OCR1 một phần → OCR2 một phần + regex MfgDate → đặt `SN_8P=barcode_list[-1]` L3935 → Cambrian trên ROI warn → đặt `step1` theo Cambrian + cổng SFIS L3941–3948.
   - **C1200/C1300:** Bypass OCR3 L3993 → chỉ regex MfgDate OCR1 L4004–4073 → cùng đường SN + Cambrian.
9. Nếu không `step1_1`: `step1=False` L4087–4088.

### Luồng vision — STEP 2 (`step1==True and stepname=="STEP 2"` L4104)

1. Lặp shape `model_point`: `warn*` → crop Cambrian; `topdate` → lưu `source/8P/topdate.jpg`.
2. Cambrian trên ROI warn → `step2_1` True/False L4133–4142; danh sách warn rỗng → `step2_1=True` L4143–4146.
3. Nếu ROI `topdate`: PaddleOCR sync + regex 8 chữ số → `step2_2` L4147–4179; không topdate → `step2_2=True` L4183–4186.
4. Nếu `step2_1 and step2_2`: Pass UI, `updatecount`, upload SFIS pass L4188–4207, `step2=True`.
5. Nếu không `step2_1`: `step2=False` L4210–4213.
6. **Khoảng trống:** `step2_1=True` nhưng `step2_2=False` — không `step2=False` rõ; vẫn `False` từ reset → handler fail go_run3.

### Điểm quyết định Pass/Fail

| Kiểm tra | Pass đặt | Fail |
|-------|-----------|------|
| Số lượng/nội dung barcode | `step1_1=True` | chỉ log; `step1=False` L4088 |
| Model SFIS vs barcode | `step1_sfis=True` | chặn `step1=True` dù Cambrian pass L3944–3946 |
| Text OCR1/OCR2/OCR3 | tiếp tục chuỗi | log "ocr N fail"; không `step1` |
| Cambrian STEP 1 warn | `step1=True` (nếu cổng SFIS OK) | `step1=False` L3952 |
| Cambrian STEP 2 warn | `step2_1=True` | `step2_1=False` |
| OCR topdate | `step2_2=True` | `step2_2=False` |
| Tổng hợp STEP 2 | `step2=True` + upload SFIS | `step2=False` L4213 hoặc chưa đặt |

---

## 7. Luồng Barcode / SN

| Trường | Nguồn | Đặt ở đâu | Dùng ở đâu | Rủi ro |
|-------|--------|-----------|------------|------|
| `barcode_list` | `pyzbar.decode` trên ROI `ocr` cuối L3543–3556 | Vòng STEP 1 | Validate L3571+ | ROI sai nếu nhiều nhãn `ocr`; loại QRCODE L3555 |
| `SN_8P` | `barcode_list[-1]` (PVN, 11 ký tự) | L3935 (C1000), L4055 (C1200/C1300) | `lineEdit_8`; upload SFIS L1358, L1385, L4205 | **Cũ** nếu STEP 1 fail trước khi đặt; fail upload có thể dùng SN DUT trước |
| `liaohao` | Parse phản hồi SFIS `get_sfis_90` | L3582+ | Tra cứu `model_and_90` | Parse `split("\x7f")` mong manh |
| `scaninfo` | — | Không dùng đường Cisco | — | — |

Không DataMatrix trên đường Cisco active (`ReadDataMatrixCode` dùng chỗ khác). Không fallback SN thủ công trong nhánh Cisco.

Barcode fail: log "barcode check fail" / "not enough"; không đặt `SN_8P`; `step1_1` vẫn False → `step1=False` L4088.

---

## 8. Luồng OCR / QThread

| Mục OCR | Phương pháp | Threading | Biến kết quả | Quy tắc pass | Rủi ro |
|------------|--------|-----------|-----------------|----------|------|
| `source/8P/ocr1.jpg` | PaddleOCR trong `Runthread` | QThread + `call_backlog` → `ocr_8P_result` | Danh sách từ PaddleOCR | Khớp chuỗi con vs `check_ocr_*` L3830+ hoặc regex MfgDate C1200/C1300 L4004 | Vòng emit rỗng L5528–5530; chờ tối đa 30s rồi tiếp với `[]` |
| `source/8P/ocr2.jpg` | `Runthread` + `call_backlog1` | QThread | `ocr1_8P_result` | Chỉ C1000 L3512+ | Cùng race; không khởi động cho C1200/C1300 |
| `source/8P/ocr3.jpg` | PaddleOCR sync | Luồng UI L3530 | `result3` local | Khớp Label[0], label[1] L3810 | Chặn UI khi tải model |
| `source/8P/topdate.jpg` | PaddleOCR sync STEP 2 | Luồng UI L4148 | `result_step2` | `^\d{8}$` L4156–4158 | IndexError nếu OCR trả rỗng |

### Hành vi `Runthread` (L5527–5538)

- `while result==[]: self.signal.emit(result)` — emit **danh sách rỗng lặp lại** trước khi OCR chạy (lỗi đã biết).
- Không timeout trong thread; parent poll 60×0.5s L3747.
- `if self.thread.isRunning(): return` L3506 — thoát sớm để STEP 1 không hoàn tất, `step1` vẫn False.

### Ghi chú race / treo

- `ocr_8P_result` không khởi tạo trong `__init__` — poll đầu L3748 có thể `AttributeError` nếu signal chưa kết nối.
- Sau 60 lần poll không có kết quả, code có thể index `ocr_8P_result[0]` L3830 → exception → `step1` chưa đặt → đường fail go_run3 (wait_test OK) nhưng không fail UI có cấu trúc từ vision.

---

## 9. Luồng SFIS

| Kịch bản | Lệnh gọi SFIS | SN | Upload kết quả | Mã lỗi | wait_test | Rủi ro |
|----------|-----------|-----|---------------|------------|-----------|------|
| STEP 1 barcode OK + khớp model SFIS | Chỉ `get_sfis_90` | PVN từ barcode | Không upload | — | — | Parse mong manh |
| STEP 1 fail (go_run3) | `data_upload` | `SN_8P` | Fail | **BDFA01** L1385 | True L1392 | `SN_8P` có thể cũ/chưa đặt |
| STEP 2 fail (go_run3) | `data_upload` | `SN_8P` | Fail | **BDFA01** L1358 | True L1362 | Không try/except (khác step1 L1382) |
| STEP 2 pass (vision) | `data_upload` | `SN_8P` | Pass | Không L4205 | Đặt go_run3 L1342 | Upload không tham số error |
| `sfis_choose=False` | Bỏ qua | — | Chỉ pass/fail local | — | — | `step1=True` nếu Cambrian pass L3947–3948 |
| SFIS bật nhưng kiểm model fail | Không upload | — | `step1` bị chặn | — | Đường fail nếu `step1=False` | Fail SFIS im lặng trước Cambrian |

**Không dùng đường Cisco:** `check_route`, `repair_SN` (có trong Button_check / SKY).

Upload fail step1: try/except chỉ log L1389–1391; vẫn `wait_test=True` L1392.

---

## 10. Tương tác Trạng thái

| Trạng thái | Đặt ở đâu | Giá trị | Điều kiện | Rủi ro |
|-------|-----------|-------|-----------|------|
| `step1` | Vision L3946–3952, L4067–4073, L4088 | True/False | Pass = barcode+OCR+Cambrian (+SFIS nếu bật) | Exception → False → fail go_run3 OK |
| `step2` | Vision L4208, L4213 | True/False | `step2_1 ∧ step2_2` | Fail `step2_2` để False → handler fail OK |
| `step1_1` | L3580+ | Nội dung barcode OK | Quy tắc theo model | |
| `step1_sfis` | L3586+ | Khớp model SFIS | Chỉ nếu `sfis_choose` | Chặn step1 khi False |
| `step2_1` / `step2_2` | L4137–4179 | Kết quả sub-step | | Fail `step2_2`: không `step2=False` rõ trong vision |
| `wait_test` | go_run3 L1342, L1362, L1392, L1366, L1397 | True | Mọi đường thoát đã ghi | Exception với `step1` kẹt True hiếm |
| `stop_program` | go_run3 L1367, L1398 | True | User reject + xác nhận thoát | |
| `SN_8P` | L3935, L4055 | Chuỗi PVN | Muộn trong đường thành công STEP 1 | Cũ khi fail sớm |
| `ocr_8P_result` | `call_backlog` L3453 | Đầu ra PaddleOCR | Async | Chưa khởi tạo; race |

**Kiểm tra treo wait_test:** Cisco có handler fail rõ cho `step1==False` và `step2==False` — **rủi ro treo thấp hơn HH4K**. Rủi ro treo còn lại: `select_model` không xử lý (không else trong go_run3) hoặc thoát vòng bất thường — không đặc thù Cisco.

---

## 11. Đường Thất bại

| Điểm thất bại | Phát hiện | Hành vi | Kết quả UI | Upload SFIS | wait_test | Rủi ro |
|---------------|-----------|----------|-----------|-------------|-----------|------|
| Thiếu `barcode_point` / shapes | Exception | Log L4216 | — | Không | fail step1 go_run3 | |
| Decode barcode rỗng | `len(barcode_list)!=4/5` | Log "not enough" | — | Không | đường step1 fail | |
| Nội dung barcode lệch | if theo model L3573+ | `step1_1` chưa đặt | — | Không | step1 fail | |
| Model SFIS lệch | `step1_sfis` False | `step1` không True | — | Không | step1 fail | |
| Timeout OCR (60 poll) | `ocr_8P_result==[]` | Có thể IndexError L3830 | except | Không | step1 fail | |
| Text OCR lệch | counter eeekko/eeeekko | Log "ocr N fail" | — | Không | step1 fail | |
| Cambrian STEP 1 Fail | `yolo_step1=="Fail"` | `step1=False` L3952 | UI_show fail | Không | handler step1 fail | |
| Cambrian STEP 2 Fail | `step2_1=False` | `step2=False` L4213 | UI_show fail | Không | handler step2 fail | |
| OCR topdate fail | regex miss L4176 | `step2_2=False` | log | Không | step2 fail (chưa đặt) | |
| User từ chối STEP 1/2 | QMessageBox 65536 | xác nhận thoát | — | Không | True + stop L1397 | |
| Exception trong vision | except L4216 | Chỉ log | Không Fail/count | Không | Handler fail nếu step chưa đặt | |
| Chế độ sensor + model Cisco | go_run2 L829 | Pipeline MR6500 | Sai | Không | — | Lỗi config |

---

## 12. Rủi ro

### Rủi ro: Vòng emit danh sách rỗng Runthread

- **Mức độ:** Trung bình
- **Bằng chứng:** L5528–5530 `while result==[]: self.signal.emit(result)` trước khi PaddleOCR chạy
- **Tại sao quan trọng:** Tín hiệu giả; `ocr_8P_result=[]` có thể thỏa poll sai theo thời gian.
- **Cách sửa đề xuất:** Xóa emit busy; emit một lần khi OCR xong.

### Rủi ro: `ocr_8P_result` chưa khởi tạo

- **Mức độ:** Cao
- **Bằng chứng:** Chỉ đặt trong `call_backlog` L3453; truy cập đầu L3748 STEP 1; không mặc định `__init__`
- **Tại sao quan trọng:** `AttributeError` trước callback thread.
- **Cách sửa đề xuất:** Khởi tạo `self.ocr_8P_result=[]` trong `__init__` hoặc đầu STEP 1.

### Rủi ro: Timeout OCR rồi index kết quả rỗng

- **Mức độ:** Cao
- **Bằng chứng:** Vòng poll L3747–3755 thoát sau 60 lần không `break`; L3830 `self.ocr_8P_result[0]`
- **Tại sao quan trọng:** Exception hoặc đường fail sai sau 30s chờ.
- **Cách sửa đề xuất:** Nhánh fail timeout rõ; guard trước index.

### Rủi ro: SN_8P cũ khi upload fail

- **Mức độ:** Cao
- **Bằng chứng:** `SN_8P` chỉ đặt L3935/L4055 khi STEP 1 thành công đầy đủ; fail upload dùng `self.SN_8P` L1358, L1385 không guard
- **Tại sao quan trọng:** MES có thể ghi SN sai khi barcode/OCR fail.
- **Cách sửa đề xuất:** Chỉ upload khi `SN_8P` đặt trong chu kỳ này; xóa khi reset.

### Rủi ro: SFIS bật nhưng `step1_sfis` chặn pass im lặng

- **Mức độ:** Trung bình
- **Bằng chứng:** L3944–3946 `if self.sfis_choose: if self.step1_sfis: self.step1=True` — không else fail UI trong vision
- **Tại sao quan trọng:** Operator thấy Cambrian pass nhưng `step1=False` → fail điều phối.
- **Cách sửa đề xuất:** Thông báo fail rõ khi kiểm model SFIS fail.

### Rủi ro: Tên hàm dùng chung gây nhầm

- **Mức độ:** Thấp (bảo trì)
- **Bằng chứng:** Hàm `show_image_C1000_8FP_E_2G_L` L3457; 12 model tại go_run3 L1292
- **Tại sao quan trọng:** Nhầm lẫn onboarding/debug.
- **Cách sửa đề xuất:** Đổi tên `show_image_Cisco` hoặc dispatch registry.

### Rủi ro: Lỗi cú pháp dict `model_and_90`

- **Mức độ:** Trung bình
- **Bằng chứng:** L106–107 nối chuỗi `"C10""00-8P-2G-L"` trong dict
- **Tại sao quan trọng:** Key sai cho tra cứu liaohao SFIS.
- **Cách sửa đề xuất:** Xác minh literal dict khi triển khai.

### Rủi ro: pyzbar trên ROI sai

- **Mức độ:** Trung bình
- **Bằng chứng:** L3543 dùng `cut_img_step1` từ lần lặp nhãn `ocr` cuối L3478–3487
- **Tại sao quan trọng:** Barcode decode từ crop sai nếu nhiều shape `ocr`.
- **Cách sửa đề xuất:** Nhãn ROI barcode riêng.

### Rủi ro: Cisco không đến được chế độ sensor

- **Mức độ:** Cao (phụ thuộc config)
- **Bằng chứng:** go_run2 L829 chỉ MR6500; Cisco go_run3 L1292
- **Tại sao quan trọng:** Pipeline sai nếu `is_sensor=True`.
- **Cách sửa đề xuất:** Dispatcher dùng chung.

### Rủi ro: Upload fail STEP 2 không try/except

- **Mức độ:** Thấp–Trung bình
- **Bằng chứng:** L1357–1361 không try/except; step1 fail có try L1382–1391
- **Tại sao quan trọng:** Exception SFIS có thể bỏ qua `wait_test` L1362 nếu lan truyền — **xác minh:** L1357 không trong khối try; exception sẽ bỏ qua L1362.

### Rủi ro: Exception upload SFIS step2 bỏ qua wait_test

- **Mức độ:** Cao
- **Bằng chứng:** go_run3 L1343–1362 — `data_upload` L1358 không bọc try/except; `wait_test=True` tại L1362 sau upload
- **Tại sao quan trọng:** Lỗi SFIS step2 fail → có thể treo.
- **Cách sửa đề xuất:** try/finally với `wait_test=True`.

### Rủi ro: Nhiều lần tải PaddleOCR trên luồng UI

- **Mức độ:** Trung bình
- **Bằng chứng:** L3530, L4148, cộng hai instance `Runthread` mỗi cái tải PaddleOCR L5534
- **Tại sao quan trọng:** Đơ UI vài giây mỗi STEP 1/2.
- **Cách sửa đề xuất:** Tái dùng một instance OCR.

---

## 13. Kiểm thử Đề xuất

| Test case | Thiết lập | Hành vi kỳ vọng |
|-----------|-------|-------------------|
| Pass đầy đủ 2 bước | DUT hợp lệ, SFIS bật | step1→step2 True; upload SFIS pass L4205; wait_test L1342 |
| STEP 1 fail (barcode) | Barcode sai/thiếu | step1 False; fail UI go_run3 + BDFA01; wait_test L1392 |
| STEP 2 fail (Cambrian) | warn/top xấu | step2 False; fail UI + BDFA01; wait_test L1362 |
| Decode barcode fail | Che ROI barcode | "not enough"; step1 False |
| Kết quả OCR rỗng | Chặn ocr1.jpg / kill thread | Timeout hoặc exception; đường step1 fail |
| OCR chậm | Trễ PaddleOCR | Poll tới 30s; rồi fail hoặc exception |
| SFIS tắt | `sfis_choose=False` | Không lệnh SFIS; step1 nếu Cambrian pass |
| Upload SFIS fail | Mock exception `data_upload` | step1: wait_test vẫn L1392; **step2: xác minh rủi ro treo** |
| User từ chối STEP 1 | QMessageBox No | wait_test + stop_program L1397 |
| User từ chối STEP 2 | No trên STEP 2 | wait_test + stop_program L1367 |
| Sensor + model Cisco | `is_sensor=True` | MR6500 trong go_run2 — không Cisco |
| Mỗi biến thể | Xoay cả 12 `select_model` | Nhánh `check_label_*` đúng L3571+ |

---

## Tham chiếu chéo

- Dispatch: `08_model_dispatch.md`
- Helper Cambrian: `14_sky_pipeline.md` (`cambrian_space`)
- Mẫu treo: `04_state_machine.md`, `15_hh4k_pipeline.md`
