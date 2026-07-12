# Kế hoạch Refactor & Lộ trình Cải tiến — `sky.py`

Dựa trên phân tích Phase 1–11 (`docs/aoi-analysis/00`–`19`, `07_camera_io_sfis.md`, `10_risks_and_bugs.md`).

**Phạm vi:** Chỉ kế hoạch cải tiến kỹ thuật — **không thay đổi code sản xuất trong phase này.**

**Nguyên tắc:** Ổn định tăng dần và modular hóa. **Không viết lại toàn bộ.**

---

## 1. Tóm tắt Điều hành

`sky.py` (~5.571 dòng) là **ứng dụng AOI PyQt5 khổng lồ**: một class `Demo` sở hữu GUI, camera, IO sensor PCI-1756 tùy chọn, vision Cambrian/OCR/barcode, và upload MES SFIS tùy chọn. Hành vi sản phẩm được chọn bằng chuỗi `select_model` và recipe JSON.

**Rủi ro lớn nhất hiện tại không phải thuật toán vision** mà là:

- **Điều phối** — vòng lặp chặn luồng UI, đường treo `wait_test`, tách sensor vs manual
- **Quản lý trạng thái** — cờ boolean (`wait_test`, `stepN`, biến SN cũ)
- **Ranh giới SFIS/MES** — lệnh gọi không guard, SN sai khi upload fail, khối upload trùng lặp
- **Phụ thuộc bên ngoài** — import bị comment vẫn dùng, thiếu gói triển khai, đường dẫn asset hardcode

**Chiến lược đề xuất:** **Ổn định trước** (sửa an toàn Tháng 1), rồi **cứng hóa runtime** (Tháng 2), rồi **chuẩn hóa pipeline** (Tháng 3). Modular hóa cấu trúc trải Q2–Q4 không dừng sản xuất.

Tham chiếu chi tiết: `04_state_machine.md`, `05_runtime_flow.md`, `07_camera_io_sfis.md`, `10_risks_and_bugs.md`, pipeline `13`–`19`.

---

## 2. Xếp hạng Rủi ro Hàng đầu

| Hạng | Rủi ro | Mức độ | Bằng chứng | Model ảnh hưởng | Ưu tiên đề xuất |
|------|------|----------|----------|-----------------|-------------------|
| 1 | Chế độ sensor luôn MR6500 | Nghiêm trọng | `go_run2` L829 `show_image_MR6500` — không `select_model` | Mọi non-MR6500 với `is_sensor=True` | Q1 — ghi tài liệu + sửa dispatch |
| 2 | Import `IoCard` bị comment nhưng vẫn dùng | Nghiêm trọng | L29 `#`, L673 `IoCard(...)` | Chế độ sensor (tất cả) | Tháng 1 — sửa import một dòng |
| 3 | SFIS MR6500 không guard | Nghiêm trọng | L2032–2035 không kiểm tra `sfis_choose` | MR6500 | Tháng 1 |
| 4 | Cambrian tắt nhưng vẫn dùng `self.client` | Nghiêm trọng | L290–293 không client; SKY/Cisco/WP/Button_check gọi `get_inference_result` | SKY, Cisco, WP, Button_check | Tháng 1 guard + chính sách init Tháng 2 |
| 5 | Đường treo `wait_test` | Cao | Model không xác định không `else` L834–1911; exception HH4K L993; Button_check từ chối Flip L1450 | HH4K, recipe không xác định, Button_check | Tháng 1 |
| 6 | Upload SFIS fail SN cũ/sai | Nghiêm trọng | Button_check L1441 `thissn`; Cisco `SN_8P` cũ L1358; WP/Nanook `"None"` L1668 | Button_check, Cisco, WP, Nanook | Tháng 1 |
| 7 | OCR/PaddleOCR chặn UI | Cao | SKY L2864; Nanook L1685; Cisco sync L3530 | SKY, Nanook, Cisco | Tháng 2 |
| 8 | Thiếu gói triển khai/asset | Cao | Repo = chỉ `sky.py`; `point/`, `sample/`, `source/` hardcode | Tất cả | Tháng 1 manifest + Q1 |
| 9 | `cambrian_space` trả `None` khi exception | Cao | L2643–2645 `None` ngầm định | SKY, Cisco, WP, Button_check, Nanook | Tháng 2 |
| 10 | Model không xác định — không `else` cuối trong `go_run3` | Cao | L834–1911 return với `wait_test=False` | Bất kỳ `select_model` chưa nối | Tháng 1 |
| 11 | SKY STEP 6 false pass + upload SFIS | Nghiêm trọng | L3060–3096 Cambrian pass dù cờ fail | SKY, SKY_4G | Tháng 1–2 |
| 12 | Import `ipex_check` bị comment | Nghiêm trọng | L37 `#`, L871 gọi | ipex_check | Tháng 1 |
| 13 | `time.sleep(5)` trên luồng UI | Cao | L813 `go_run2` | Chế độ sensor | Tháng 2 |
| 14 | `startprogram` chặn luồng UI | Cao | L687 `while True` trên slot nút | Tất cả | Tháng 2–Q2 |
| 15 | WP `check_result_OK` không đặt khi route fail | Cao | L4462–4507 | WP_check, C9105AXW_E | Tháng 1 |

---

## 3. Tháng 1 — Sửa An toàn

Thay đổi nhỏ, cục bộ. **Mục tiêu:** loại bỏ crash, treo, và bản ghi MES sai mà không đổi logic vision.

---

### 3.1 `else` cuối trong `go_run3` → reset `wait_test`

| Trường | Chi tiết |
|-------|--------|
| **Vấn đề** | `select_model` không trong danh sách thoát `go_run3` không có `wait_test=True` → vòng Start đóng băng. |
| **Bằng chứng** | L834–1911 không có `else` cuối; `08_model_dispatch.md` |
| **Tác động** | Operator phải Stop/restart; line có vẻ treo. |
| **Thay đổi đề xuất** | Thêm `else:` log model không xác định + `wait_test=True` + MessageBox tùy chọn. |
| **Mức rủi ro** | Thấp — chỉ bổ sung. |
| **Test bắt buộc** | Tải chuỗi `select_model` giả; xác nhận chu kỳ tiếp bắt đầu. |
| **Rollback** | Xóa khối `else`; hành vi quay về treo (ghi là đã biết). |

---

### 3.2 Bọc upload SFIS fail trong try/finally với `wait_test=True`

| Trường | Chi tiết |
|-------|--------|
| **Vấn đề** | Cisco step2 fail L1357, WP/Nanook step2–6 fail L1546+ — exception `data_upload` bỏ qua `wait_test`. |
| **Bằng chứng** | `10_risks_and_bugs.md` Phase 7–9; Button_check L1438 có try (mẫu tốt). |
| **Tác động** | Sự cố mạng SFIS → treo vĩnh viễn. |
| **Thay đổi đề xuất** | Tách mẫu: `try: upload if sfis_choose` / `finally: wait_test=True`. Áp dụng cho khối fail go_run3 trùng lặp. |
| **Mức rủi ro** | Thấp — cùng logic upload, đảm bảo reset cờ. |
| **Test bắt buộc** | Mock `data_upload` raise trên đường fail mỗi model; vòng lặp tiếp tục. |
| **Rollback** | Khôi phục khối inline; giữ try Button_check làm tham chiếu. |

---

### 3.3 Reset biến SN khi bắt đầu nhánh/chu kỳ

| Trường | Chi tiết |
|-------|--------|
| **Vấn đề** | `thissn`, `SN_8P`, `scaninfo`, `check_result_OK` cũ từ DUT/model trước. |
| **Bằng chứng** | Button_check L1441; Cisco L1358; WP L1457/L1668; Nanook L1684 |
| **Tác động** | Fail MES gắn SN sai hoặc literal `"None"`. |
| **Thay đổi đề xuất** | Mỗi lần vào nhánh `go_run3`: reset SN theo model (`thissn=""`, `SN_8P=""`, `check_result_OK=False`). Button_check: đặt `thissn=scaninfo` cho fail upload hoặc dùng `scaninfo` trực tiếp. |
| **Mức rủi ro** | Thấp — init rõ ràng. |
| **Test bắt buộc** | Chạy SKY fail rồi Button_check fail — SN MES khớp scan. |
| **Rollback** | Xóa reset; ghi quy trình audit SN. |

---

### 3.4 Sửa upload fail Button_check: `thissn` → `scaninfo`

| Trường | Chi tiết |
|-------|--------|
| **Vấn đề** | Upload pass dùng `scaninfo` L4313; fail dùng `thissn` L1441 (không bao giờ đặt). |
| **Bằng chứng** | `19_button_check_pipeline.md` |
| **Tác động** | Toàn vẹn dữ liệu MES nghiêm trọng — fail trên SN model trước. |
| **Thay đổi đề xuất** | L1441: `data_upload(self.scaninfo, self.data, error="BDFA01")`. |
| **Mức rủi ro** | Rất thấp — một dòng, khớp đường pass. |
| **Test bắt buộc** | Button_check Cambrian fail sau test SKY; SFIS nhận SN đã scan. |
| **Rollback** | Hoàn tác một dòng. |

---

### 3.5 Guard MR6500 với `sfis_choose`

| Trường | Chi tiết |
|-------|--------|
| **Vấn đề** | `sfis_choose=False` → `mysfis` không xác định → crash sau decode barcode. |
| **Bằng chứng** | L2032–2035; `07_camera_io_sfis.md` §4 |
| **Tác động** | Chế độ offline/test không dùng được cho MR6500. |
| **Thay đổi đề xuất** | Nếu không `sfis_choose`: bỏ qua tra cứu SFIS; dùng đường liaohao thủ công hoặc Fail UI có cấu trúc. |
| **Mức rủi ro** | Thấp–trung bình — cần quy tắc sản phẩm cho nguồn liaohao offline. |
| **Test bắt buộc** | MR6500 với SFIS tắt: không crash; thông báo operator rõ. |
| **Rollback** | Khôi phục SFIS vô điều kiện; yêu cầu SFIS bật cho MR6500. |

---

### 3.6 Khởi tạo `check_result_OK=False` khi bắt đầu nhánh

| Trường | Chi tiết |
|-------|--------|
| **Vấn đề** | Cổng route WP/SKY/Button_check đọc `check_result_OK` cũ từ test trước. |
| **Bằng chứng** | WP L4507; Button_check L1401 chỉ reset `step1` |
| **Tác động** | Cambrian chạy sau route fail; rủi ro false pass. |
| **Thay đổi đề xuất** | `self.check_result_OK = False` khi bắt đầu mỗi nhánh route SFIS. |
| **Mức rủi ro** | Rất thấp. |
| **Test bắt buộc** | WP route fail sau pass trước; Cambrian bị bỏ qua. |
| **Rollback** | Xóa dòng init. |

---

### 3.7 Khởi tạo Cisco `ocr_8P_result=[]` khi vào STEP 1

| Trường | Chi tiết |
|-------|--------|
| **Vấn đề** | `AttributeError` nếu poll chạy trước callback. |
| **Bằng chứng** | L3748; `16_cisco_pipeline.md` |
| **Tác động** | Test Cisco đầu có thể crash. |
| **Thay đổi đề xuất** | `self.ocr_8P_result = []` tại nhánh Cisco / bắt đầu STEP 1. |
| **Mức rủi ro** | Rất thấp. |
| **Test bắt buộc** | Cold start Cisco STEP 1. |
| **Rollback** | Xóa init. |

---

### 3.8 Sửa vòng emit rỗng `Runthread`

| Trường | Chi tiết |
|-------|--------|
| **Vấn đề** | Busy loop `while result==[]: emit([])` L5529–5530. |
| **Bằng chứng** | `10_risks_and_bugs.md` |
| **Tác động** | Tín hiệu giả; race với poll OCR Cisco. |
| **Thay đổi đề xuất** | Xóa while; emit một lần khi OCR xong. |
| **Mức rủi ro** | Thấp — xác minh vòng poll vẫn nhận kết quả. |
| **Test bắt buộc** | Cisco STEP 1 OCR pass/fail/timeout. |
| **Rollback** | Khôi phục while (không khuyến nghị). |

---

### 3.9 Validate scan rỗng (Button_check `go_run1`)

| Trường | Chi tiết |
|-------|--------|
| **Vấn đề** | Chuỗi rỗng được chấp nhận tại QInputDialog L770–775. |
| **Bằng chứng** | `19_button_check_pipeline.md` |
| **Tác động** | Route/upload SFIS với SN rỗng. |
| **Thay đổi đề xuất** | Từ chối rỗng/khoảng trắng; nhắc lại hoặc hiển thị lỗi. |
| **Mức rủi ro** | Thấp — chỉ thay đổi UX operator. |
| **Test bắt buộc** | OK với trường rỗng → không `scan_sta`. |
| **Rollback** | Xóa validation. |

---

### 3.10 Thêm guard ROI/file thiếu

| Trường | Chi tiết |
|-------|--------|
| **Vấn đề** | Thiếu `point/*.json`, `sample/*.jpg` → exception; `stepN` không đặt → treo. |
| **Bằng chứng** | HH4K L2149+; MR6500 L2038; `07_camera_io_sfis.md` §10 |
| **Tác động** | Bỏ qua im lặng hoặc treo tùy đường dẫn. |
| **Thay đổi đề xuất** | Pre-flight: `os.path.exists` + Fail hiển thị; `stepN=False` + `wait_test=True` trong vision `except`. Tạo `source/`, `source/8P/` khi khởi động. |
| **Mức rủi ro** | Thấp. |
| **Test bắt buộc** | Đổi tên `point/step1.json` → fail có cấu trúc, không treo. |
| **Rollback** | Xóa guard; dựa vào log exception. |

---

### 3.11 Sửa treo từ chối Flip Button_check

| Trường | Chi tiết |
|-------|--------|
| **Vấn đề** | Từ chối "Flip model" không xác nhận thoát → `wait_test` vẫn False. |
| **Bằng chứng** | L1450–1454 |
| **Tác động** | Operator kẹt cho đến Stop. |
| **Thay đổi đề xuất** | Khi reject (65536): `wait_test=True` ngay, hoặc hiện lại prompt Flip. |
| **Mức rủi ro** | Thấp. |
| **Test bắt buộc** | Từ chối Flip → prompt DUT tiếp có sẵn. |
| **Rollback** | Khôi phục đường chỉ thoát. |

---

### 3.12 Bỏ comment/sửa import hỏng (IoCard, ipex)

| Trường | Chi tiết |
|-------|--------|
| **Vấn đề** | `NameError` lúc runtime cho chế độ sensor và ipex_check. |
| **Bằng chứng** | L29, L37, L673, L871 |
| **Tác động** | Crash ngay khi Start hoặc test ipex. |
| **Thay đổi đề xuất** | Khôi phục import; xác minh module trên đường triển khai; guard model tùy chọn nếu thiếu module. |
| **Mức rủi ro** | Thấp nếu module có sẵn; triển khai phải ship `ioCardNew`, `ipex_check_yolo`. |
| **Test bắt buộc** | Start sensor; ipex_check một chu kỳ. |
| **Rollback** | Comment lại import; tắt sensor/ipex trong config. |

---

### 3.13 HH4K: thêm `elif step1==False` + vision `finally` cho `stepN`

| Trường | Chi tiết |
|-------|--------|
| **Vấn đề** | Exception trước `step1=True` → treo L993. |
| **Bằng chứng** | `15_hh4k_pipeline.md` |
| **Tác động** | Thiếu sample/JSON đóng băng line. |
| **Thay đổi đề xuất** | go_run3: `elif self.step1==False: wait_test=True` + Fail UI; vision except: `step1=False`. |
| **Mức rủi ro** | Thấp — khớp mẫu Cisco/WP. |
| **Test bắt buộc** | Hỏng `point/step1.json` → chu kỳ phục hồi được. |
| **Rollback** | Xóa elif. |

---

### 3.14 Manifest triển khai (không code — quy trình)

| Trường | Chi tiết |
|-------|--------|
| **Vấn đề** | Không tái tạo môi trường từ repo. |
| **Bằng chứng** | `07_camera_io_sfis.md` §11 |
| **Tác động** | Lỗi setup station mới; khoảng trống audit. |
| **Thay đổi đề xuất** | File checklist theo họ model: module, `point/`, `sample/`, `source/`, endpoint Cambrian/SFIS. |
| **Mức rủi ro** | Không (tài liệu). |
| **Test bắt buộc** | Cài VM sạch từ manifest. |
| **Rollback** | N/A |

---

## 4. Tháng 2 — Ổn định Runtime

**Mục tiêu:** Giảm đơ UI, thống nhất xử lý lỗi, tập trung MES — vẫn trong `sky.py`, thay đổi API tối thiểu.

| Hạng mục | Vấn đề | Thay đổi đề xuất | Test | Rollback |
|------|---------|-----------------|------|----------|
| Xóa đơ UI `sleep(5)` | L813 chặn Stop | `QTimer.singleShot` hoặc worker wait với poll `stop_program` | Stop trong delay sensor | Khôi phục sleep |
| `cambrian_space` return `"Fail"` khi except | `None` mơ hồ L2643 | `return "Fail"` rõ + log | Ép exception Cambrian | Hoàn tác return |
| Cache instance PaddleOCR | SKY/Nanook tải lại mỗi bước/chu kỳ | Singleton khi tải model hoặc lazy một lần mỗi phiên | Đo thời gian đơ UI | Init mỗi lần gọi |
| Tập trung helper upload SFIS | Khối trùng SKY/Cisco/WP/Nanook/Button_check | `sfis_upload_fail(sn, code)` / `sfis_upload_pass(sn)` với guard `sfis_choose` | Mọi đường fail + exception | Khôi phục inline |
| Tập trung đếm Pass/Fail | `updatecount` trùng trong go_run3 | Helper `record_result(passed: bool)` | Độ chính xác đếm mỗi model | Khôi phục inline |
| Đối tượng kết quả fail có cấu trúc | Vision đặt cờ; điều phối đọc không nhất quán | `StepResult(passed, sn, error_code, message)` nhẹ trả từ vision | Cổng HH4K vs SKY | Giữ boolean |
| Chính sách Cambrian tắt | Crash trên `self.client` | Init stub hoặc guard mọi `get_inference_result`; căn với bypass Nanook | `is_cambrian:false` mỗi model | Yêu cầu Cambrian bật |
| Cổng tổng hợp SKY STEP 6 | False pass + upload L3060–3096 | Chặn pass/upload trừ khi `checksn`, `modelcheck`, `sncheck` true | STEP 6 fail một phần | Hoàn tác cổng |
| `stopprogram` log lỗi cleanup | Bare except L5403 | Log exception; guard `hasattr(iocard)` | Stop có/không sensor | Bare except |
| Bật lại Start trong except `startprogram` | L727–729 | `finally: pushButton_2.setEnabled(True)` khi thoát vòng fatal | Ép exception tại Start | Xóa finally |

---

## 5. Tháng 3 — Chuẩn hóa Pipeline

**Mục tiêu:** Giảm trùng lặp và drift config — vẫn tăng dần, không viết lại.

| Hạng mục | Thay đổi đề xuất | Lợi ích |
|------|-----------------|---------|
| Dispatcher sensor/manual dùng chung | `run_vision(select_model, image)` gọi từ `go_run2` và `go_run3` | Sửa hardcode MR6500 sensor |
| Dict registry model | `{ "SKY": SkyPipeline, ... }` thay vì `elif` 1000 dòng | Sản phẩm mới an toàn hơn |
| Chuẩn hóa ngữ nghĩa step | Ghi + ép pass-gated vs executed-gated theo model | Sửa tùy chọn HH4K chain-on-fail |
| Chuẩn hóa nguồn SN | Thuộc tính `active_sn` mỗi pipeline: `thissn` / `scaninfo` / `SN_8P` | Nhất quán MES |
| Chuẩn hóa mã lỗi | Bảng `select_model` → `BDFA0` / `BDFA01` / tùy chỉnh | Audit MES |
| Chuyển `point/*.json` hardcode vào recipe JSON | `path_json.step3_path` v.v. | Triển khai theo recipe |
| Chính sách scan `go_run1` trong registry | `requires_scan: true` chỉ Button_check | Scan mở rộng được |
| Xóa hoặc cách ly đường chết | `show_image_SKY_yolo`, `show_image` L1913, class `Scan` không dùng | Ít nhầm lẫn |

---

## 6. Lộ trình Theo Quý

| Quý | Chủ đề | Sản phẩm bàn giao | Tác động kỳ vọng |
|---------|-------|--------------|-----------------|
| **Q1** | Ổn định & an toàn sản xuất | Ship fix Tháng 1; manifest triển khai; audit SFIS/SN; sửa import; loại treo | Ít dừng line, SN fail MES đúng, test MR6500 offline được |
| **Q2** | Runtime & modular hóa (phase 1) | Worker thread hoặc state machine cho vòng test; helper SFIS; cache OCR; delay sensor ngắt được; bắt đầu tách package `app/` (chỉ wrapper) | UI phản hồi; Stop < 1s; lớp MES dễ bảo trì |
| **Q3** | Pipeline theo recipe | Model registry; dispatcher dùng chung; đường point từ JSON; bảng mã lỗi; sensor dispatch theo recipe | Model mới không sửa nhánh 500 dòng |
| **Q4** | Test harness & quan sát | Ma trận tích hợp (§9); log có cấu trúc; metric chu kỳ; chế độ replay headless tùy chọn | An toàn regression; dữ liệu báo cáo tháng |

---

## 7. Kiến trúc Mục tiêu Đề xuất

Trạng thái cuối tăng dần — **tách từ `Demo` theo quý**, không big-bang.

```text
app/
  ui/                 # MainWindow, dialogs, resultcolor, tableWidget — lớp Demo mỏng
  orchestration/      # startprogram, go_run1/2/3, cờ, chuỗi QMessageBox
  hardware/           # CameraService (basler_my), IoCardService, debounce sensor
  vision/             # get_inference_result, cambrian_space, OCR, barcode helpers
  pipelines/          # Một module mỗi họ sản phẩm (mr6500, sky, cisco, …)
  sfis/               # Wrapper SfisClient: route, repair, upload, mã lỗi
  config/             # config.json, loader model JSON, resolver đường asset
  storage/            # Lưu ảnh, đường log, persist count JSON
  tests/              # Ma trận §9 — mock SFIS/Cambrian/camera
```

| Module | Vai trò |
|--------|------|
| `ui/` | Chỉ hiển thị; phát Start/Stop; nhận signal cho log/kết quả |
| `orchestration/` | Sở hữu `wait_test`, `scan_sta`, `stop_program`; không toán vision |
| `hardware/` | Mở/đóng camera một lần; poll IO; không quy tắc sản phẩm |
| `vision/` | Primitive AI/OCR/so sánh dùng chung |
| `pipelines/` | Logic bước theo sản phẩm; trả `StepResult` |
| `sfis/` | Một cổng cho `sfis_choose`; validate SN trước upload |
| `config/` | Resolve đường `point/` từ recipe; validate bundle khi tải |
| `storage/` | `pciture_save`, `log/`, `source/` mkdir, ghi count atomic |
| `tests/` | Regression cho treo, SN, SFIS tắt, thiếu asset |

**`Demo` trở thành:** keo nối UI ↔ điều phối ↔ dịch vụ (~500 dòng mục tiêu Q2–Q4).

---

## 8. Thứ tự Refactor An toàn Tối thiểu

**Không** bỏ qua bước sớm — mỗi lớp phụ thuộc lớp trước.

```text
1. Wrapper không đổi hành vi
   └─ sfis_upload_*, record_result(), mkdir_runtime_dirs() — gọi code hiện có

2. Đối tượng kết quả
   └─ Dataclass StepResult; vision trả về; go_run3 đọc .passed (song song stepN)

3. Helper SFIS
   └─ Mọi upload/route trong module sfis/; sửa lỗi SN trong helper

4. Helper dispatcher
   └─ dispatch_vision(select_model, image) dùng bởi go_run2 + go_run3

5. Tách class pipeline
   └─ Chuyển thân show_image_SKY → pipelines/sky.py từng cái một

6. Worker thread / state machine
   └─ Chuyển while True khỏi luồng UI cuối cùng — sau khi tập trung cờ
```

**Quy tắc:** Ship fix Tháng 1 **trước** wrapper bước 1 — an toàn sản xuất độc lập kiến trúc.

---

## 9. Kế hoạch Kiểm thử

| Lĩnh vực | Test | Kỳ vọng |
|------|------|----------|
| Sensor MR6500 | `is_sensor=True`, recipe MR6500, trigger IO | Vision MR6500 chạy; `wait_test` reset |
| Sensor non-MR6500 | `is_sensor=True`, recipe SKY | **Hiện sai** — MR6500 chạy; sau sửa dispatcher → SKY hoặc chặn có ghi |
| SFIS tắt MR6500 | `sfis_choose=False`, decode OK | Không crash; kết quả offline có cấu trúc |
| Cambrian tắt SKY | `is_cambrian:false`, SKY manual | Không `AttributeError`; thông báo rõ hoặc bypass kiểu Nanook |
| Cambrian tắt WP/Button_check | Tương tự | Không crash ở inference STEP 1 |
| Upload fail Button_check | Fail sau test SKY trước | SN MES = `scaninfo` |
| Timeout OCR Cisco | Chặn OCR > 30s | `step1=False`, `wait_test=True`, không IndexError |
| Route fail WP | SFIS route FAIL | `check_result_OK=False`, không Cambrian; SN fail upload hợp lệ hoặc bỏ qua |
| Route fail Nanook | Barcode OK, route FAIL | step1 False; không upload `"None"` nếu thiếu SN |
| Exception HH4K trước step True | Thiếu `sample/step1.jpg` | `wait_test=True`, Start phục hồi |
| Model không xác định | `select_model` chưa nối | Log + `wait_test=True` (sau fix Tháng 1) |
| Thiếu point JSON | Đổi tên `point/SKY_barcode.json` | Fail UI, không treo |
| Thiếu thư mục source | Xóa `source/` trước Cisco | Tự tạo hoặc lỗi rõ |
| Hủy scan Button_check | Hủy dialog | `stop_program`, Start bật |
| Từ chối Flip Button_check | Từ chối không thoát | `wait_test=True` (sau sửa) |
| Exception upload SFIS fail | Mock throw trên Cisco step2 fail | `wait_test=True` trong finally |
| Stop trong sleep(5) | Stop trong 5s sau trigger sensor | Vòng thoát trong thời gian giới hạn (sau Tháng 2) |
| Cache PaddleOCR | Nanook 3 DUT liên tiếp | Chu kỳ 2/3 khởi động nhanh hơn |

**Nhịp regression:** Chạy ma trận đầy đủ trước mỗi release tháng; smoke subset (dòng in đậm) hàng tuần trên bản clone line sản xuất.

---

## 10. Mẫu Báo cáo cho Quản lý

*Dùng cho báo cáo cải tiến tháng/quý — có thể copy sang `20_improvement_report_vi.md`.*

### Hiện trạng

Hệ thống AOI hiện vận hành trên một file Python tập trung (`sky.py`, khoảng 5.500 dòng), điều khiển camera Basler, cảm biến IO (tùy công đoạn), kiểm tra hình ảnh và đồng bộ kết quả lên SFIS/MES. Đã hỗ trợ nhiều model sản phẩm (MR6500, SKY, HH4K, Cisco, WP, Nanook, Button_check, …). Phân tích mã nguồn Phase 1–11 đã hoàn tất; tài liệu kỹ thuật nằm tại `docs/aoi-analysis/`.

### Vấn đề phát hiện

1. **Ổn định vận hành:** Một số trường hợp khiến chương trình "treo" chờ test tiếp theo (lỗi cấu hình model, hủy thao tác operator, lỗi SFIS khi upload fail).
2. **Dữ liệu MES:** Upload fail đôi khi gắn sai serial (đặc biệt Button_check, Cisco, WP/Nanook).
3. **Phụ thuộc triển khai:** Module IO, ipex bị comment import nhưng vẫn gọi; thiếu gói file `point/`, `sample/`, `source/` chuẩn hóa.
4. **Sensor vs manual:** Chế độ sensor luôn chạy pipeline MR6500 dù đang chọn model khác — rủi ro sai quy trình nếu cấu hình nhầm.
5. **Trải nghiệm operator:** Khởi tạo OCR và `sleep(5)` trên luồng giao diện gây đơ máy vài giây; nút Stop chậm phản hồi.

*Rủi ro lớn nhất không nằm ở thuật toán nhận dạng mà ở điều phối, trạng thái và ranh giới SFIS/phụ thuộc.*

### Kế hoạch cải tiến tháng (Month 1)

- Sửa treo vòng lặp: reset `wait_test` khi model không hỗ trợ; bổ sung xử lý fail cho HH4K và Button_check.
- Chuẩn hóa upload SFIS fail (try/finally); sửa SN Button_check; reset biến SN đầu mỗi chu kỳ.
- Bảo vệ MR6500 khi tắt SFIS; khởi tạo biến trạng thái route/OCR.
- Khôi phục import IO/ipex; kiểm tra scan rỗng; tạo thư mục `source/` khi thiếu.
- Lập **danh mục triển khai** (deployment checklist) theo từng model.

### Kế hoạch cải tiến quý (Q1–Q2)

- **Q1:** Hoàn thành các fix an toàn trên; kiểm thử ma trận §9 trên line clone; audit MES một tuần.
- **Q2:** Giảm đơ UI (bỏ sleep cứng, cache OCR); gom logic SFIS; bắt đầu tách module nhỏ (không thay đổi hành vi).

### Lợi ích kỳ vọng

| Lợi ích | Mô tả |
|---------|--------|
| Giảm downtime | Ít treo chờ test; Stop phản hồi nhanh hơn |
| Dữ liệu MES đúng | Fail/pass gắn đúng SN |
| Triển khai station mới | Checklist rõ ràng, ít lỗi thiếu file |
| Bảo trì | Thêm model mới ít chạm code trùng lặp (Q3) |

### Rủi ro khi triển khai

- Sửa điều phối có thể ảnh hưởng thứ tự bước test — cần chạy regression từng model trước khi lên line chính.
- Thay đổi SN upload cần xác nhận với team MES/SFIS (mã lỗi `BDFA0` vs `BDFA01`).
- Tách module dài hạn — **không** làm trong Month 1; tránh big-bang.

### Cách nghiệm thu

1. **Checklist kỹ thuật:** Ma trận test §9 — 100% case Critical (stall, SN, SFIS off) pass trên môi trường clone.
2. **So sánh sản lượng:** Yield/Total/Fail đếm local không lệch trước/sau (cùng recipe, 50 DUT).
3. **Audit MES:** 10 pass + 10 fail có record SFIS đúng SN (sampling 1 tuần).
4. **Xác nhận người vận hành:** Không treo trong 3 ca vận hành thử.
5. **Rollback:** Giữ bản `sky.py` trước thay đổi; revert từng patch nếu một model fail regression.

---

## Chỉ mục Tài liệu

| Tài liệu | Dùng trong kế hoạch này |
|-----|------------------|
| `07_camera_io_sfis.md` | Triển khai, ranh giới SFIS/Cambrian/OCR |
| `10_risks_and_bugs.md` | Bằng chứng cho mọi hạng mục |
| `08_model_dispatch.md` | Chuẩn hóa dispatcher |
| `13`–`19` | Hành vi SN/step/SFIS theo pipeline |
| `09_threading_and_ui.md` | Công việc luồng UI Tháng 2 |

**Artifact tiếp theo (tùy chọn):** `20_improvement_report_vi.md` — báo cáo tiếng Việt hướng điều hành, ít kỹ thuật, từ §10.
