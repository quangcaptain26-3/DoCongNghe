# Pipeline Nanook — `show_image_Nanook`

Dòng: L4748–5160 (`sky.py`). Điều phối: nhánh Nanook `go_run3` L1683–1910. Helper: `get_inference_result` L630, `cambrian_space` L2595, `UI_show` L5235, `updatecount` L415, `resultcolor` L584. Map module: `nanook_model_tan` / `nanook_model_clei` L109–110.

**Không dùng:** `scaninfo`, `SN_8P`, `Runthread`, `model_point` (bước 3–6 dùng hardcode `point/Nanook_model*.json`).

**Chế độ sensor:** Nanook **không** đến được qua `go_run2` (MR6500 L829). Chỉ `go_run3` manual.

---

## 1. Mục đích

AOI manual 6 bước cho `select_model=="Nanook"`:

| Bước | Vai trò |
|------|------|
| 1 | pyzbar 3× barcode → SN/TAN; route SFIS; Cambrian trên ROI warn/screw |
| 2 | Lưu trữ / chỉ UI — **không kiểm vision** |
| 3 | Chuỗi model PaddleOCR từ ROI `Nanook_model` |
| 4 | Cambrian vít (`Nanook_model2.json`) |
| 5 | OCR CLEI + khớp `nanook_model_tan`/`nanook_model_clei` vs TAN barcode; Cambrian beehive/warn |
| 6 | Cambrian vít; Pass UI + upload SFIS |

| Khía cạnh | Chi tiết |
|--------|--------|
| vs WP | WP Cambrian mọi bước; Nanook trộn **lưu trữ (2)**, **OCR (3,5)**, **Cambrian (1,4,5,6)** |
| vs SKY | Điều phối 6 bước tương tự; Nanook STEP 2 chỉ lưu; STEP 3 luôn đặt `step3=True` sau OCR (không Cambrian); CLEI qua OCR không pyzbar |
| PaddleOCR | Tạo một lần **khi bắt đầu nhánh** L1685–1686 (`lang="en"`); tái dùng `self.nanook_ocr` |

---

## 2. Ánh xạ Dispatch

| select_model | Dòng nhánh | Pipeline | Bước | Lần chụp |
|--------------|------------:|----------|------:|---------:|
| `Nanook` | L1683 | `show_image_Nanook` ×6 | 6 | 6× `get_image` |

Mẫu verify (comment): `sample/NANOOK/1–6.jpg` L1693–1698. Sản xuất dùng camera live L1708+.

Nội dung QMessageBox dùng lỗi chính tả **`SETP`** L1700, L1717, L1725, L1733, L1742, L1751 — tiêu đề cửa sổ vẫn `"STEP N"`; **logic không ảnh hưởng** (caller truyền `"STEP N"`).

---

## 3. Caller và Đường Điều khiển

| Caller | Dòng | Điều kiện | Sau return |
|--------|-----:|-----------|--------------|
| `go_run3` | L1715 | STEP 1 accept | `step1` → STEP 2; else fail + SFIS `BDFA01` + `wait_test` L1881–1904 |
| `go_run3` | L1723 | `step1`, STEP 2 | `step2` → STEP 3; else fail L1857–1875 |
| `go_run3` | L1731 | `step2`, STEP 3 | `step3` → STEP 4; else fail L1833–1851 |
| `go_run3` | L1739 | `step3`, STEP 4 | `step4` → STEP 5; else fail L1809–1827 |
| `go_run3` | L1748 | `step4`, STEP 5 | `step5` → STEP 6; else fail L1785–1803 |
| `go_run3` | L1757 | `step5`, STEP 6 | `step6` → `wait_test` L1759; else fail L1760–1779 |

**Chỉ call site** của `show_image_Nanook`.

### `wait_test=True`

| Đường | Dòng |
|------|-------|
| step6 pass | L1759 |
| step1–6 fail | L1779, L1803, L1827, L1851, L1875, L1904 |
| User reject + thoát | L1783, L1807, L1831, L1855, L1879, L1909 |

step1 fail: SFIS trong **try/except** L1894–1903. step2–6 fail: upload **không** try L1774+ (treo nếu `data_upload` throw trước `wait_test`).

---

## 4. Đầu vào

| Đầu vào | Nguồn | Dùng cho | Bắt buộc? | Rủi ro nếu thiếu |
|-------|--------|----------|-----------|-----------------|
| `image_numpy` | Camera | Mọi bước | Có | Frame rỗng |
| `stepname` | `"STEP 1"`…`"STEP 6"` | Nhánh | Có | No-op |
| `self.barcode_point` | Model JSON | STEP 1: `Nanook_bar`, `Nanook_warn`/`screw` | Có | Thiếu `Nanook_bar` → `cut_img_bar` không xác định L4775 |
| `point/Nanook_model1.json` | Hardcode L4925 | ROI OCR STEP 3 | Có | FileNotFound |
| `point/Nanook_model2.json` | L4971 | Vít STEP 4 | Có | — |
| `point/Nanook_model3.json` | L5005 | STEP 5 beehive/warn/bar | Có | — |
| `point/Nanook_model4.json` | L5095 | Vít STEP 6 | Có | — |
| `self.nanook_ocr` | Tạo L1685 | OCR STEP 3, 5 | Có | Nhánh phải chạy trước |
| `nanook_model_tan` / `_clei` | Module L109–110 | Khớp STEP 5 | Có | **KeyError** nếu OCR model ≠ `C1100TG-1N32A` |
| `self.client` / `cambrian_is_open` | Model JSON | Bước Cambrian | Nếu Cambrian bật | Tắt → auto-pass bước 1/4/5/6 |
| `self.mysfis` | SFIS | Route/repair/upload | Nếu `sfis_choose` | — |
| `self.thissn` | Reset `"None"` L1684; barcode[1] | Lưu/upload | — | Fail upload với `"None"` |
| `scaninfo` | — | **Không dùng** | — | — |
| `self.model_point` | Recipe | **Không dùng** trong Nanook | — | — |

---

## 5. Đầu ra / Tác dụng phụ

| Tác dụng phụ | Vị trí | Điều kiện |
|-------------|-------|-----------|
| Lưu thô mỗi bước | L4751 | `{thissn}_{stepname}_{img_time}.jpg` — STEP 1 có thể vẫn `"None"` |
| `lineEdit_8` | L4824 | Sau barcode OK |
| `UI_show` | Mỗi bước | Pass/fail crop hoặc thô |
| `resultcolor` + `updatecount` | L5127–5134 | **Chỉ** STEP 6 Cambrian pass |
| Lưu ALL PASS | L5142–5144 | STEP 6 Cambrian pass |
| Upload SFIS pass | L5135–5136 | STEP 6 + `sfis_choose` — không mã lỗi |
| Upload SFIS fail | go_run3 L1775+ | `error="BDFA01"` |
| `step1`–`step6` | Vision | Cổng hỗn hợp — xem §10 |
| `thistan`, `thisclei`, `nanook_ocr_model` | STEP 1 / 3 / 5 | Đối chiếu STEP 5 |
| `wait_test` | Chỉ go_run3 | Không trong vision |

---

## 6. Luồng Từng bước

### Điều phối

1. `thissn="None"`; **`PaddleOCR(...)` trên luồng UI** L1685–1686; reset `step1–6=False`.
2. Sáu QMessageBox (text `SETP N`) → chụp → `show_image_Nanook(..., "STEP N")`.
3. Chuỗi khi `stepN==True`; handler fail đặt Fail UI + SFIS tùy chọn + `wait_test`.

### Vision

**STEP 1** (`stepname=="STEP 1"` L4753)

1. ROI từ `barcode_point`: `Nanook_bar` → crop barcode; `Nanook_warn`/`screw` → danh sách Cambrian.
2. `pyzbar.decode(cut_img_bar)`; giữ non-QRCODE; cần **đúng 3** mã L4790–4797.
3. `thissn=barcode_list[1]`, `thistan=barcode_list[2]`; `checksn=True`.
4. Nếu `checksn` + Cambrian bật: SFIS `check_route`/`repair_SN` → nếu `check_result_OK` → Cambrian → `step1` True/False.
5. Nếu `checksn` + SFIS tắt: Cambrian → `step1`.
6. Nếu `checksn` + Cambrian **tắt**: `step1=True` L4913–4914 (**bypass AI**).
7. Nếu không `checksn`: `step1` vẫn False.

**STEP 2** (`step1 and "STEP 2"` L4916)

- `UI_show` ảnh đã lưu; **`step2=True` luôn** L4920 — chỉ lưu trữ, **executed-gated**.

**STEP 3** (`step2 and "STEP 3"` L4922)

- Tải `point/Nanook_model1.json`; crop `Nanook_model` → `source/Nanook_ocr.jpg`.
- `nanook_ocr.ocr(...)` → `nanook_ocr_model = result[0][0][1][0]` L4943–4944.
- **`step3=True` luôn** sau OCR L4951 — **không validate nội dung**; nhánh Cambrian bị comment.
- OCR rỗng → IndexError → except L5158; `step3` chưa đặt → fail go_run3.

**STEP 4** (`step3 and "STEP 4"` L4967)

- `point/Nanook_model2.json` vít → Cambrian → `step4` True/False; Cambrian tắt → `step4=True` L4998–4999.

**STEP 5** (`step4 and "STEP 5"` L5001)

1. `Nanook_model3.json`: `beehive`/`Nanook_warn_beside` → crop Cambrian; `Nanook_bar_beside` → OCR CLEI L5022–5023.
2. Khớp: `nanook_model_tan[nanook_ocr_model]==thistan` và `nanook_model_clei[...]==thisclei` → `checkmodel_tan_clei`.
3. Nếu khớp + Cambrian: Cambrian → `step5`; Cambrian tắt → `step5=True`.
4. Nếu lệch: `checkmodel_tan_clei=False`; **`step5` không đặt** → vẫn False → handler fail.

**STEP 6** (`step5 and "STEP 6"` L5091)

- `Nanook_model4.json` vít → Cambrian Pass: UI Pass + upload SFIS + `step6=True`; Fail: `step6=False`.
- Cambrian **tắt**: `step6=True` L5155–5156 **không** `resultcolor`/`updatecount`/`data_upload`.

### Tóm tắt quyết định pass

| Bước | Điều kiện pass | Kiểu cổng |
|------|----------------|-------------|
| 1 | Barcode + (route nếu SFIS) + Cambrian Pass (hoặc Cambrian tắt) | Pass-gated (+ bypass Cambrian tắt) |
| 2 | Luôn sau show | **Executed** |
| 3 | OCR chạy không exception | **Executed** (nội dung OCR không kiểm) |
| 4 | Cambrian Pass / Cambrian tắt | Pass-gated / bypass |
| 5 | Khớp TAN/CLEI + Cambrian Pass / Cambrian tắt | Pass-gated (+ cổng khớp) |
| 6 | Cambrian Pass / Cambrian tắt | Pass-gated / bypass (bypass bỏ MES/UI count) |

---

## 7. Luồng SN / Barcode / OCR

| Trường | Nguồn | Đặt ở đâu | Dùng ở đâu | Rủi ro |
|-------|--------|-----------|------------|------|
| `thissn` | `barcode_list[1]` | L4796 | Lưu, `lineEdit_8`, SFIS | Reset `"None"` L1684; fail upload sớm → `"None"` |
| `thistan` | `barcode_list[2]` | L4797 | STEP 5 vs `nanook_model_tan` | Danh sách pyzbar nhạy thứ tự |
| `thisclei` | OCR STEP 5 | L5023 | vs `nanook_model_clei` | OCR rỗng crash |
| `nanook_ocr_model` | OCR STEP 3 | L4944 | Key dict STEP 5 | OCR sai → KeyError L5024 |
| `checksn` | len==3 barcode | L4793/4795 | Cổng STEP 1 AI | — |
| `scaninfo` | — | Không dùng | — | — |

Barcode: chỉ non-QRCODE L4782; kỳ vọng đúng 3. Không DataMatrix. Không fallback scan thủ công.

---

## 8. Luồng PaddleOCR

| Sự kiện | Vị trí | Threading | Ghi chú |
|-------|----------|-----------|-------|
| Khởi tạo | go_run3 L1685–1686 | **Luồng UI** | Mỗi bắt đầu chu kỳ Nanook — chặn UI khi tải model |
| OCR STEP 3 | L4943 `self.nanook_ocr.ocr("source/Nanook_ocr.jpg")` | Sync UI | Chuỗi model |
| OCR STEP 5 | L5022 `...Nanook_bar_beside.jpg` | Sync UI | Chuỗi CLEI |
| lang | `"en"` | — | Khác Cisco `"ch"` |

Không QThread cho OCR Nanook. `result` rỗng / thiếu dòng → IndexError L4944, L5023.

Thiếu ROI → `source/Nanook_ocr.jpg` cũ từ chu kỳ trước hoặc bỏ imwrite → OCR sai / crash.

---

## 9. Luồng SFIS

| Kịch bản | Lệnh gọi SFIS | SN | Lỗi | wait_test | Rủi ro |
|----------|-----------|-----|-------|-----------|------|
| STEP 1 route | `check_route` / `repair_SN` | `thissn` | — | — | `check_result_OK` không đặt nếu route fail không repair L4829–4834 |
| STEP 6 pass (Cambrian bật) | `data_upload` | `thissn` | none L5136 | L1759 | — |
| STEP 6 Cambrian tắt | **Không upload** | — | — | L1759 nếu step6 True | Khoảng trống MES |
| step1 fail go_run3 | `data_upload` | `thissn` | BDFA01 | L1904 (try) | Có thể `"None"` |
| step2–6 fail | `data_upload` | `thissn` | BDFA01 | sau upload | Không try → treo khi throw |

---

## 10. Tương tác Trạng thái

| Trạng thái | Đặt | Ý nghĩa | Rủi ro |
|-------|-----|---------|------|
| `step1` | L4887–4914 | Pass-gated / bypass Cambrian tắt | Route fail có thể không đặt |
| `step2` | L4920 | Luôn True | Chỉ lưu trữ |
| `step3` | L4951 | Luôn True sau OCR | OCR xấu vẫn tiến |
| `step4`–`step6` | Cambrian | Pass-gated / bypass tắt | STEP 6 tắt bỏ Pass UI/SFIS |
| `wait_test` | go_run3 | Thoát đã ghi | except SFIS step2–6 |
| `thissn` | L1684 / L4796 | SN | `"None"` cũ |
| `check_result_OK` | Khối SFIS | Cổng route | Chưa init / cũ (cùng rủi ro WP) |
| `checkmodel_tan_clei` | L5027–5038 | Cổng STEP 5 | KeyError trước khi đặt |
| `stop_program` | Thoát user | Abort | — |

**Treo wait_test:** Thấp hơn HH4K — có `elif stepN==False` cho cả sáu bước. Còn lại: except SFIS step2–6 fail; exception vision để step False → handler fail vẫn reset (trừ step kẹt True sai — STEP 2/3 luôn True giảm false-fail, không treo).

---

## 11. Đường Thất bại

| Thất bại | Phát hiện | stepN | SFIS fail | wait_test |
|---------|-----------|-------|-----------|-----------|
| Barcode ≠3 | L4790 | step1 False | BDFA01 `"None"` | L1904 |
| Route SFIS fail (không repair) | L4829 | step1 có thể unset / AttributeError | — | Không rõ |
| Cambrian STEP 1 Fail | L4888 | step1 False | BDFA01 | Có |
| OCR rỗng STEP 3 | IndexError | step3 unset | Không | Handler fail |
| Model OCR không xác định | KeyError L5024 | step5 unset | Không | Handler fail |
| Lệch TAN/CLEI | L5031–5038 | step5 False | BDFA01 | L1803 |
| Cambrian STEP 4/5/6 Fail | — | False | BDFA01 | Có |
| Thiếu point JSON | except | unset | Không | Fail nếu step False |
| User reject | QMessageBox | — | Không | + stop_program |
| Sensor + Nanook | go_run2 L829 | — | — | Pipeline MR6500 sai |

---

## 12. Rủi ro

### Rủi ro: PaddleOCR khởi tạo trên luồng UI mỗi chu kỳ

- **Mức độ:** Cao (UX)
- **Bằng chứng:** L1685–1686 trong nhánh Nanook `go_run3` trước khi prompt STEP 1 return
- **Tại sao quan trọng:** Đơ UI vài giây mỗi lần bắt đầu DUT.
- **Cách sửa đề xuất:** Singleton lazy / preload khi chọn model.

### Rủi ro: Index OCR STEP 3 / STEP 5 không guard rỗng

- **Mức độ:** Cao
- **Bằng chứng:** L4944 `result[0][0][1][0]`; L5023 `result_beside[0][0][1][0]`
- **Tại sao quan trọng:** OCR rỗng → exception; step chưa đặt.
- **Cách sửa đề xuất:** Validate độ dài kết quả OCR trước index.

### Rủi ro: STEP 3 luôn tiến (`step3=True`) không validate text model

- **Mức độ:** Cao (chất lượng)
- **Bằng chứng:** L4951 sau OCR; không so với danh sách model kỳ vọng
- **Tại sao quan trọng:** OCR rác vẫn tới STEP 4; chỉ STEP 5 KeyError/lệch có thể bắt.
- **Cách sửa đề xuất:** Yêu cầu `nanook_ocr_model in nanook_model_tan` trước `step3=True`.

### Rủi ro: Fail upload với `thissn="None"`

- **Mức độ:** Cao
- **Bằng chứng:** L1684; fail L1897 / L1775 dùng `self.thissn`
- **Tại sao quan trọng:** Fail MES với literal `"None"`.
- **Cách sửa đề xuất:** Bỏ upload nếu SN chưa decode.

### Rủi ro: Exception SFIS fail step2–6 bỏ qua wait_test

- **Mức độ:** Cao
- **Bằng chứng:** L1774–1779 (và anh em) — không try; `wait_test` sau upload
- **Tại sao quan trọng:** Treo (cùng mẫu Cisco/WP).
- **Cách sửa đề xuất:** try/finally.

### Rủi ro: `check_result_OK` không đặt khi route fail không repair

- **Mức độ:** Cao
- **Bằng chứng:** L4829–4834; L4874 `if self.check_result_OK`
- **Tại sao quan trọng:** AttributeError hoặc True cũ.
- **Cách sửa đề xuất:** Mặc định False mọi đường fail.

### Rủi ro: Cambrian tắt STEP 6 đặt `step6=True` không Pass UI / SFIS

- **Mức độ:** Trung bình–Cao
- **Bằng chứng:** L5155–5156 vs khối Pass L5112–5148
- **Tại sao quan trọng:** Chu kỳ local "pass" không MES/count.
- **Cách sửa đề xuất:** Mirror Pass UI/upload hoặc Fail nếu bắt buộc Cambrian.

### Rủi ro: Hardcode `point/Nanook_model*.json` + dict một model

- **Mức độ:** Trung bình
- **Bằng chứng:** L4925, L4971, L5005, L5095; `nanook_model_tan` chỉ `C1100TG-1N32A` L109
- **Tại sao quan trọng:** SKU mới cần sửa code; KeyError nếu không.
- **Cách sửa đề xuất:** Map/đường theo recipe.

### Rủi ro: Thiếu ROI `Nanook_bar` / `Nanook_bar_beside`

- **Mức độ:** Cao
- **Bằng chứng:** L4775 dùng `cut_img_bar`; L5022 luôn OCR file beside
- **Tại sao quan trọng:** UnboundLocalError / OCR file cũ.
- **Cách sửa đề xuất:** Kiểm tra tìm thấy ROI rõ ràng.

### Rủi ro: Chế độ sensor + Nanook → MR6500

- **Mức độ:** Cao (config)
- **Bằng chứng:** go_run2 L829; Nanook chỉ L1683
- **Cách sửa đề xuất:** Dispatcher dùng chung.

### Rủi ro: Lỗi chính tả `SETP`

- **Mức độ:** Thấp
- **Bằng chứng:** Text dialog L1700+
- **Tại sao quan trọng:** Chỉ nhầm operator; `stepname` vẫn `"STEP N"`.
- **Cách sửa đề xuất:** Đổi text thành `STEP`.

---

## 13. Kiểm thử Đề xuất

| Test case | Thiết lập | Kỳ vọng |
|-----------|-------|----------|
| Pass đầy đủ 6 bước | DUT hợp lệ, Cambrian+SFIS bật | step6 True; SFIS L5136; wait_test L1759 |
| Barcode ≠3 | Che barcode | step1 False; upload `"None"`; wait_test |
| OCR rỗng STEP 3 | ROI model trống | Exception; đường fail step3 |
| OCR model sai | Text không C1100TG | KeyError hoặc STEP 5 fail |
| Lệch TAN/CLEI | OCR beside sai | step5 False; BDFA01 |
| Cambrian tắt | `is_cambrian=False` | Auto-pass 1/4/5/6; STEP 6 không SFIS — xác minh |
| Route SFIS fail | Mock `"0"` không repair | Lỗi `check_result_OK` |
| Throw upload SFIS step4 fail | Mock | Treo wait_test? |
| User reject SETP 2 | Từ chối dialog | wait_test + stop |
| Sensor + Nanook | `is_sensor=True` | Pipeline MR6500 sai |
| Thiếu Nanook_model1.json | Xóa file | Exception; đường fail |

---

## So sánh: Nanook vs WP vs SKY

| Khía cạnh | Nanook | WP | SKY |
|--------|--------|-----|-----|
| Bước | 6 | 6 | 6 |
| STEP 2 | Chỉ lưu trữ | Cambrian | Cambrian |
| OCR | STEP 3 model + STEP 5 CLEI | Không | STEP 3 (Paddle) |
| SN | pyzbar ×3 → `[1]` | DataMatrix / `$SN:` | pyzbar ×4 |
| Point JSON | Hardcode `Nanook_model1–4` | Trộn recipe + `WP_check_step*` | Hardcode `SKY_*` |
| Mã fail | BDFA01 | BDFA01 | BDFA0 |
| Cổng step | Hỗn hợp (2/3 executed) | Pass-gated | Pass-gated (+ lỗi tổng hợp STEP 6 SKY) |

---

## Tham chiếu chéo

- WP: `17_wp_pipeline.md`
- SKY: `14_sky_pipeline.md`
- Dispatch: `08_model_dispatch.md`
