# Pipeline WP — `show_image_WP`

Dòng: L4379–4746 (`sky.py`). Điều phối: nhánh WP `go_run3` L1456–1681. Helper: `ReadDataMatrixCode` L5500+, `get_inference_result` L630, `cambrian_space` L2595, `UI_show` L5235, `updatecount` L415, `resultcolor` L584.

**Không dùng đường WP:** `Runthread`, PaddleOCR (Nanook dùng OCR; WP không), `scaninfo`, `SN_8P`.

**Chế độ sensor:** WP/C9105AXW_E **không** đến được qua `go_run2` (MR6500 L829). Chỉ `go_run3` manual.

---

## 1. Mục đích

**AOI manual 6 bước dùng chung** cho `WP_check` và `C9105AXW_E`: operator chụp sáu tư thế; mỗi bước chạy phân loại Cambrian trên ROI recipe/hardcode. STEP 1 thêm decode SN đơn vị và validate route SFIS trước Cambrian.

| Khía cạnh | Chi tiết |
|--------|--------|
| Pipeline dùng chung | Có — một hàm `show_image_WP`; hai model dùng nhánh `go_run3` L1456 |
| Khác biệt model | **Chỉ decode SN STEP 1:** `WP_check` = DataMatrix (`ReadDataMatrixCode`); `C9105AXW_E` = `pyzbar` + regex `$SN:` |
| Bước 2–6 | Logic giống hệt; hardcode `point/WP_check_step3–6.json` cho cả hai model |
| Engine AI | **Cambrian** (`get_inference_result` + `cambrian_space`; biến tên `yolo_stepN`) |

---

## 2. Model Hỗ trợ / Ánh xạ Dispatch

| select_model | Dòng nhánh | Pipeline | Ghi chú |
|--------------|------------:|----------|-------|
| `WP_check` | L1456 | `show_image_WP` ×6 | DataMatrix trên ROI `WP_QR` |
| `C9105AXW_E` | L1456 | same | pyzbar + `$SN:[0-9a-zA-Z]{11}` L4420–4428 |

Xác minh ảnh mẫu tải (bị comment) từ `sample/C9105AXW_E/1–6.jpg` L1464–1469 — sản xuất dùng camera live L1479+.

---

## 3. Caller và Đường Điều khiển

| Caller | Dòng | Điều kiện | Sau return |
|--------|-----:|-----------|--------------|
| `go_run3` | L1486 | STEP 1 accept | `step1==True` → STEP 2; `step1==False` → fail + SFIS `BDFA01` + `wait_test` L1652–1675 |
| `go_run3` | L1494 | `step1`, STEP 2 | `step2==True` → STEP 3; `step2==False` → fail L1628–1646 |
| `go_run3` | L1502 | `step2`, STEP 3 | `step3==True` → STEP 4; `step3==False` → fail L1604–1622 |
| `go_run3` | L1510 | `step3`, STEP 4 | `step4==True` → STEP 5; `step4==False` → fail L1580–1598 |
| `go_run3` | L1519 | `step4`, STEP 5 | `step5==True` → STEP 6; `step5==False` → fail L1556–1574 |
| `go_run3` | L1528 | `step5`, STEP 6 | `step6==True` → `wait_test` L1530; `step6==False` → fail L1531–1550 |

**Không có call site khác.**

### Vị trí `wait_test=True`

| Đường | Dòng |
|------|-------|
| step6 pass | L1530 |
| step1–6 fail (mỗi `elif stepN==False`) | L1550, L1574, L1598, L1622, L1646, L1675 |
| User reject + xác nhận thoát | L1554, L1578, L1602, L1626, L1650, L1680 |

**step1 fail** có SFIS try/except L1665–1674; **step2–6 fail** upload L1546+ phần lớn **không** try/except (rủi ro treo kiểu Cisco khi exception SFIS).

---

## 4. Đầu vào

| Đầu vào | Nguồn | Dùng cho | Bắt buộc? | Rủi ro nếu thiếu |
|-------|--------|----------|-----------|-----------------|
| `image_numpy` | Camera `go_run3` | Mọi bước | Có | Frame rỗng |
| `stepname` | `"STEP 1"`…`"STEP 6"` | Bộ chọn nhánh | Có | Nhánh sai / no-op |
| `self.barcode_point` | Model JSON | STEP 1: `WP_QR`, label/screw/net ROIs | Có | Thiếu `WP_QR` → `cut_img` không xác định L4408 |
| `self.model_point` | Model JSON | STEP 2: `WP_Logo`, `WP_PASS` | Có STEP 2 | Rỗng → không crop, Cambrian trên `[]` |
| `point/WP_check_step3.json` … `step6.json` | Hardcode L4552+ | ROI STEPS 3–6 | Có | FileNotFound → except |
| `self.select_model` | Model JSON | Nhánh decode SN L4406/4419 | Có | — |
| `self.client` | Cambrian | Mọi bước AI | Có | Inference fail |
| `self.mysfis` | Init SFIS | `check_route`, `repair_SN`, `data_upload` | Nếu `sfis_choose` | AttributeError nếu SFIS tắt + nhánh route |
| `self.sfis_choose` | config.json | Cổng SFIS | Không | Bypass offline L4526–4545 |
| `self.data` | Mẫu CSV L155 | Upload SFIS | Bước upload | — |
| `self.thissn` | Reset `"None"` L1457; đặt STEP 1 | SN cho lưu/upload | Có cho MES | `"None"` cũ khi fail upload sớm |
| `scaninfo` | — | **Không dùng** | — | — |
| `check_result_OK` | Đặt trong khối route SFIS | Cổng Cambrian sau route | SFIS bật | **Không khởi tạo** — cũ/AttributeError L4507 |

---

## 5. Đầu ra / Tác dụng phụ

| Tác dụng phụ | Vị trí | Điều kiện |
|-------------|-------|-----------|
| Lưu thô mỗi bước | L4382 | `{thissn}_{stepname}_{img_time}.jpg` — **trước** decode SN vẫn dùng `"None"` |
| JPG pass/fail Cambrian | `cambrian_space` + `UI_show` | Mỗi bước |
| Lưu ALL PASS | L4730–4732 | STEP 6 Cambrian pass |
| `lineEdit_8` | L4457 | Sau decode SN OK |
| `lineEdit_9` | Chỉ fail go_run3 | `"Fail"` |
| `resultcolor` + `updatecount` | L4716–4722 | Chỉ pass STEP 6 (trong vision) |
| `step1`–`step6` | Mỗi bước L4520+, L4608+, v.v. | **Pass-gated** (`True`/`False` từ Cambrian) |
| Upload SFIS pass | L4723–4724 | STEP 6 + `sfis_choose` — không mã lỗi |
| Upload SFIS fail | go_run3 L1546+ | `error="BDFA01"` |
| `wait_test` | Chỉ go_run3 | Không đặt trong vision |
| Log / textbox | Xuyên suốt | — |

---

## 6. Luồng Từng bước

### Điều phối

1. `thissn="None"`; reset `step1–6=False` L1457–1463.
2. Sáu QMessageBox → `get_image` → `show_image_WP(shanN, "STEP N")`.
3. Chuỗi khi `stepN==True`; mỗi cấp fail có `elif stepN==False` + `wait_test`.

### Vision — STEP 1 (`stepname=="STEP 1"` L4384)

1. Grayscale; tải ROI từ `self.barcode_point`.
2. **`WP_QR`:** crop để decode SN.
3. **Nhãn khác** (`WP_Label`, `WP_Screw`, `WP_Net`, `WP_PASS`, `Label`, `tem`): crop cho Cambrian `step1_check`.
4. **Decode SN:**
   - `WP_check`: `ReadDataMatrixCode().decode(cut_img)` → `thissn = isn.split(";")[0]` L4418.
   - `C9105AXW_E`: `pyzbar.decode(cut_img)` → regex `$SN:` + 11 alnum L4422–4428.
5. Nếu `checksn`: `lineEdit_8`; SFIS `check_route` + `repair_SN` tùy chọn L4459–4493.
6. Nếu `check_result_OK` (SFIS) hoặc `sfis_choose==False`: Cambrian trên ROI step1 → `step1=True/False` L4517–4545.
7. Nếu `checksn==False`: `step1` **không đặt** (vẫn False).

### Vision — STEP 2 (`step1==True and stepname=="STEP 2"` L4582)

- ROI từ `self.model_point`: `WP_Logo`, `WP_PASS`.
- Cambrian → `step2=True/False` L4604–4613.

### Vision — STEP 3 (`step2==True and stepname=="STEP 3"` L4548)

- **Lưu ý:** elif xuất hiện trước STEP 2 trong source nhưng guard bởi `stepname`.
- `point/WP_check_step3.json`: `WP_Net`, `WP_PASS` → Cambrian → `step3` L4571–4578.

### Vision — STEP 4 (`step3==True and stepname=="STEP 4"` L4615)

- `point/WP_check_step4.json`: `WP_PASS` → `step4` L4635–4644.

### Vision — STEP 5 (`step4==True and stepname=="STEP 5"` L4646)

- `point/WP_check_step5.json`: `WP_PASS` → `step5` L4666–4675.

### Vision — STEP 6 (`step5==True and stepname=="STEP 6"` L4677)

- `point/WP_check_step6.json`: `WP_PASS`, `WP_USB` → Cambrian.
- Pass: `resultcolor`, `updatecount`, SFIS `data_upload`, lưu ALL PASS, `step6=True` L4700–4736.
- Fail: `step6=False` L4738–4742.

### Ngữ nghĩa Pass/Fail

**`step1`–`step6` là pass-gated** (như SKY/Cisco): `True` chỉ khi Cambrian `"Pass"`; `False` khi `"Fail"`. Không phải cờ kiểu HH4K "đã chạy".

---

## 7. Luồng Barcode / SN

| Trường | Nguồn | Đặt ở đâu | Dùng ở đâu | Rủi ro |
|-------|--------|-----------|------------|------|
| `thissn` | DataMatrix (WP_check) hoặc pyzbar+regex (C9105AXW_E) | L4418 / L4428 | Lưu L4382+; `lineEdit_8`; upload SFIS | Reset `"None"` L1457; fail upload có thể `"None"` L1668 |
| `checksn` | Cờ decode thành công | L4412/4417/4427/4432 | Cổng SFIS+Cambrian L4452 | Không đặt nếu bỏ decode |
| `scaninfo` | — | Không dùng | — | — |

Không fallback scan thủ công trong nhánh WP. Không `SN_8P`.

**Rủi ro C9105AXW_E:** `barcodes[0]` L4420 không kiểm tra rỗng → `IndexError`.

**Rủi ro WP_check:** Thiếu shape `WP_QR` → `cut_img` không xác định trước decode L4408.

---

## 8. Luồng OCR / QThread

**Không.** Pipeline WP chỉ dùng Cambrian (không PaddleOCR, không `Runthread`). SN STEP 1 chỉ decode barcode/DataMatrix.

---

## 9. Luồng SFIS

| Kịch bản | Lệnh gọi SFIS | SN | Upload | Mã lỗi | wait_test | Rủi ro |
|----------|-----------|-----|--------|------------|-----------|------|
| STEP 1 route OK | `check_route` | `thissn` | Không | — | — | — |
| STEP 1 route fail + repair | `repair_SN` | `thissn` | Không | — | — | `check_result_OK` chỉ đặt trong nhánh repair |
| STEP 1 route fail (không repair) | Chỉ `check_route` | `thissn` | Không | — | — | **`check_result_OK` không đặt** L4462–4466 |
| STEP 6 pass | `data_upload` | `thissn` | Pass | Không L4724 | go_run3 L1530 | — |
| step1–6 fail (go_run3) | `data_upload` | `thissn` | Fail | **BDFA01** L1546+ | True | `thissn` có thể `"None"`; step2–6 upload không try/except |
| `sfis_choose=False` | Bỏ qua | — | Chỉ local | — | — | Cambrian chạy L4526+ |

**Không dùng:** `get_sfis_90`, `data_upload` trên fail bước trung gian trong vision (chỉ go_run3).

---

## 10. Tương tác Trạng thái

| Trạng thái | Đặt ở đâu | Ý nghĩa | Rủi ro |
|-------|-----------|---------|------|
| `step1`–`step6` | Vision mỗi bước | Pass-gated | Exception → False → handler fail go_run3 |
| `wait_test` | go_run3 | Mọi thoát đã ghi | except SFIS step2–6 có thể bỏ qua L1550+ |
| `thissn` | L1457 `"None"`; decode STEP 1 | SN đơn vị | Cũ khi fail upload |
| `check_result_OK` | Khối route SFIS | Cổng route | Chưa khởi tạo; cũ từ test model trước |
| `checksn` | Decode STEP 1 | SN hợp lệ | — |
| `stop_program` | Thoát user L1555+ | Abort vòng | — |

**Treo wait_test:** Rủi ro thấp hơn HH4K — có `elif stepN==False` rõ cho cả sáu bước. Còn lại: exception SFIS step2–6 fail không try/except; exception vision để `stepN=False` → handler fail vẫn đặt `wait_test`.

---

## 11. Đường Thất bại

| Thất bại | stepN | UI | Upload SFIS fail | wait_test |
|---------|-------|-----|------------------|-----------|
| Decode SN fail | step1 False | — | `thissn="None"` L1668 | L1675 |
| Route SFIS fail (không repair) | step1 chưa đặt/except | — | — | Không rõ — có thể AttributeError L4507 |
| Cambrian fail bất kỳ bước | stepN=False | UI_show fail | BDFA01 go_run3 | True |
| Thiếu point JSON | except L4744 | chỉ log | Không | stepN False → handler fail |
| User reject STEP N | — | — | Không | True + stop_program |
| Exception trong vision | stepN unset False | log | Không | Handler fail nếu step False |

---

## 12. Rủi ro

### Rủi ro: `check_result_OK` không đặt khi route SFIS fail không repair

- **Mức độ:** Cao
- **Bằng chứng:** L4462–4466 log route FAIL nhưng không gán `check_result_OK`; L4507 `if self.check_result_OK` — biến không init trong `__init__`
- **Tại sao quan trọng:** AttributeError hoặc True cũ từ test SKY/Button_check trước → đường false pass.
- **Cách sửa đề xuất:** Đặt `check_result_OK=False` mọi đường route-fail; init trong `__init__`.

### Rủi ro: Upload SFIS fail với `thissn="None"`

- **Mức độ:** Cao
- **Bằng chứng:** L1457 `thissn="None"`; fail upload step1 L1668 dùng `self.thissn` trước decode
- **Tại sao quan trọng:** MES ghi fail với literal `"None"`.
- **Cách sửa đề xuất:** Bỏ upload nếu SN chưa decode; guard rỗng.

### Rủi ro: Kết quả pyzbar rỗng C9105AXW_E

- **Mức độ:** Cao
- **Bằng chứng:** L4420 `barcodes[0]` — không kiểm tra độ dài
- **Tại sao quan trọng:** IndexError → except; step1 chưa đặt.
- **Cách sửa đề xuất:** Guard `if not barcodes`.

### Rủi ro: Exception upload SFIS fail step2–6 bỏ qua wait_test

- **Mức độ:** Cao
- **Bằng chứng:** L1546–1550 `data_upload` không trong try; `wait_test=True` L1550 sau (cùng mẫu Cisco L1357)
- **Tại sao quan trọng:** Treo khi lỗi SFIS giữa fail-handler.
- **Cách sửa đề xuất:** try/finally với `wait_test=True`.

### Rủi ro: C9105AXW_E dùng tên hardcode `WP_check_stepN.json`

- **Mức độ:** Trung bình
- **Bằng chứng:** L4552, L4619, L4650, L4681 — đường ghi `WP_check_*` cho cả hai model
- **Tại sao quan trọng:** C9105AXW_E có thể ROI sai nếu hình học khác WP_check.
- **Cách sửa đề xuất:** File point riêng model trong recipe JSON.

### Rủi ro: Lưu ảnh trước decode SN dùng tiền tố `None`

- **Mức độ:** Thấp
- **Bằng chứng:** L4382 lưu trước L4418 decode trong cùng lần gọi STEP 1
- **Tại sao quan trọng:** Nhầm lẫn đặt tên lưu trữ.
- **Cách sửa đề xuất:** Lưu sau khi đặt SN hoặc chỉ dùng `img_time`.

### Rủi ro: WP không đến được chế độ sensor

- **Mức độ:** Cao (phụ thuộc config)
- **Bằng chứng:** go_run2 L829; WP go_run3 L1456
- **Tại sao quan trọng:** Pipeline sai nếu `is_sensor=True`.
- **Cách sửa đề xuất:** Dispatcher dùng chung.

### Rủi ro: Thông báo fail step3 gây nhầm

- **Mức độ:** Thấp
- **Bằng chứng:** go_run3 L1605 `"model or sn check fail"` cho `step3==False` — STEP 3 chỉ Cambrian
- **Tại sao quan trọng:** Nhầm lẫn operator/debug.
- **Cách sửa đề xuất:** Đổi tên log message.

### Rủi ro: Không guard false-pass tổng hợp STEP 6

- **Mức độ:** Thấp (WP đơn giản hơn SKY)
- **Bằng chứng:** L4715 `my_inference_result = "pass"` hardcode khi Cambrian pass; không kiểm cờ chéo bước
- **Tại sao quan trọng:** Mỗi bước độc lập — ít rủi ro hơn lỗi tổng hợp SKY STEP 6.
- **Cách sửa đề xuất:** N/A trừ khi thêm cờ đa bước sau.

---

## 13. Kiểm thử Đề xuất

| Test case | Thiết lập | Kỳ vọng |
|-----------|-------|----------|
| Pass đầy đủ 6 bước | DUT hợp lệ, SFIS bật | step6 True; upload SFIS L4724; wait_test L1530 |
| STEP 1 SN fail | QR xấu/thiếu | step1 False; upload `"None"`; wait_test L1675 |
| Route SFIS fail (không repair) | Mock route `"0"` không tag repair | Lỗi `check_result_OK` / không Cambrian |
| STEP 3 Cambrian fail | Linh kiện xấu | step3 False; BDFA01; wait_test L1622 |
| SFIS tắt | `sfis_choose=False` | Cambrian STEP 1 không route; đường pass L4526 |
| C9105AXW_E pyzbar rỗng | Không barcode trong frame | Exception hoặc step1 False |
| WP_check vs C9105AXW_E | Cả hai model | Decode STEP 1 khác; JSON bước 2–6 giống |
| User reject STEP 3 | QMessageBox No | wait_test + stop_program L1626 |
| Sensor + model WP | `is_sensor=True` | MR6500 trong go_run2 |
| Exception upload SFIS step4 fail | Mock throw upload | Xác minh treo wait_test L1598 |

---

## Tóm tắt WP_check vs C9105AXW_E

| Khía cạnh | WP_check | C9105AXW_E |
|--------|----------|------------|
| SN STEP 1 | DataMatrix `ReadDataMatrixCode` | pyzbar + regex `$SN:` |
| ROI STEP 1 | `barcode_point` (recipe) | Giống |
| STEPS 2–6 | `model_point` + `WP_check_step3–6.json` | **Giống hệt** |
| Nhánh go_run3 | Dùng chung L1456 | Dùng chung |
| Mẫu verify | Comment `sample/C9105AXW_E/*.jpg` | Cùng đường comment |

Giả định: cả hai sản phẩm dùng chung layout ROI Cambrian trong `WP_check_step*.json`. Chỉ decode STEP 1 khác.

---

## Tham chiếu chéo

- Mẫu 6 bước SKY: `14_sky_pipeline.md`
- Mã fail SFIS: `08_model_dispatch.md`, `16_cisco_pipeline.md`
- Cờ treo: `04_state_machine.md`
