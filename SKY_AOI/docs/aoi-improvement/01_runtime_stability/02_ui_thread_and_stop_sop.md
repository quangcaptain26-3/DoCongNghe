# UI Thread & Phản hồi Stop — SOP & Kế hoạch Cải tiến

**Luồng công việc:** `01_runtime_stability`  
**Giai đoạn:** SOP ngắn hạn ngay · Fix kỹ thuật Month 2 (Phase E)  
**Nguồn:** `04_state_machine.md`, `05_runtime_flow.md`, `09_threading_and_ui.md`, `10_risks_and_bugs.md`, `11_refactor_plan.md` Month 2

---

## Improvement Purpose

Mục tiêu của cải tiến này là cải thiện phản hồi UI và khả năng Stop trong khi chờ sensor/OCR/Cambrian/modal dialog — giảm cảm giác app bị đóng băng và giúp operator kiểm soát line tốt hơn. Chủ yếu làm flow an toàn hơn trên UI thread, không thay đổi thuật toán vision.

## Before Improvement

Trước cải tiến, hầu hết logic AOI chạy trên Qt main thread: `startprogram` while-loop block cả session; `time.sleep(5)` sau sensor trigger đóng băng UI 5 giây (L813); PaddleOCR init mỗi DUT/bước trên UI thread; modal `QMessageBox`/`QInputDialog` block đến khi click. `stopprogram()` chỉ set flag — không interrupt sleep, không đóng dialog. Operator thấy UI chết, Stop không phản hồi, phải chờ hoặc kill process.

## After Improvement

Sau cải tiến (Month 2): sensor delay dùng sleep cắt nhỏ hoặc QTimer có thể interrupt — Stop phản hồi &lt;1s; PaddleOCR singleton cache — DUT 2–3 khởi động nhanh; `startprogram` finally re-enable Start sau exception; SOP ngắn hạn hướng dẫn operator biết delay 5s là expected pre-fix. UI mượt hơn, Stop dễ kiểm soát, giảm restart không cần thiết.

## Improvement Value

| Area                        | Value |
| --------------------------- | ----- |
| Production stability        | Giảm cảm giác treo; Stop nhanh hơn trong sensor wait — ít kill process |
| Operator experience         | Operator hiểu delay expected; Stop/Start phản hồi rõ; giảm lo app hỏng |
| MES/SFIS integrity          | N/A |
| Maintainability             | Inventory blocking calls; roadmap E-01/E-03/E-07 có anchor rõ |
| Debugging / troubleshooting | Log phase blocking (sleep/OCR/modal) giúp on-call chẩn đoán nhanh |

## Before / After Summary

| Aspect           | Before | After |
| ---------------- | ------ | ----- |
| Runtime behavior | UI block 5s sensor sleep; OCR load mỗi DUT trên main thread | Interruptible wait; OCR cache; optional worker (Q2) |
| Error handling   | Stop không thoát sleep/modal | Poll `stop_program` trong delay; finally enable Start |
| Operator impact  | UI đóng băng; Stop trễ 5–60s | Stop &lt;1s trong sensor wait; DUT 2+ OCR nhanh |
| Production risk  | Operator kill app giữa SFIS upload | SOP + faster Stop giảm thao tác mạo hiểm |

---

## Per-Fix Detail

## Fix E-01 / E-07 — Interruptible sensor sleep

### Code Location

| Field | Detail |
|---|---|
| File | sky.py |
| Function / Block | `go_run2` — sau sensor trigger |
| Current lines | L813 `time.sleep(5)` |
| Suggested patch location | Thay `time.sleep(5)` bằng sliced sleep hoặc QTimer poll `stop_program` mỗi 500ms |

### Current Problem

`time.sleep(5)` trên UI thread đóng băng cứng 5 giây. `stopprogram()` chỉ set flag — không interrupt sleep. Operator bấm Stop không phản hồi trong 5s.

### Before Improvement

Sensor trigger → UI chết 5s → Stop trễ → operator kill process hoặc chờ.

### Required Change

Short-term: sliced sleep 10×0.5s với check `stop_program`. Medium-term: QTimer tick handler (Priority 2 pseudocode trong file).

### After Improvement

Stop trong sensor delay ~500ms; UI event loop chạy giữa các slice.

### Improvement Value

| Area | Value |
|---|---|
| Production stability | Giảm kill process giữa sensor wait |
| Operator experience | Stop phản hồi &lt;1s |
| MES/SFIS integrity | N/A |
| Maintainability | Không đổi kiến trúc |
| Debugging / troubleshooting | Poll `stop_program` trong delay |

### Verification

| Test ID | Setup | Action | Expected result |
|---|---|---|---|
| U-02 | Sensor trigger | Bấm Stop trong sleep 5s | Post-fix: Stop trong 500ms |

### Rollback

Khôi phục `time.sleep(5)`. Rủi ro: Stop chậm lại.

### Suggested Implementation Window

| Window | Reason |
|---|---|
| Month 2 Week 1 | Đổi timing loop — đo Stop latency trên clone |

---

## Fix E-03 — PaddleOCR singleton cache

### Code Location

| Field | Detail |
|---|---|
| File | sky.py |
| Function / Block | Nanook L1685, SKY STEP 3 L2864 — `PaddleOCR(...)` init |
| Current lines | L1685 (Nanook), L2864 (SKY STEP 3) |
| Suggested patch location | Thêm `get_ocr(lang)` singleton; thay inline `PaddleOCR()` tại init sites |

### Current Problem

PaddleOCR tạo mới mỗi DUT/bước trên UI thread — load model 2–10s+ → UI freeze, DUT 2+ chậm như DUT 1.

### Before Improvement

Nanook DUT1 chậm; SKY STEP 3 pause lâu mỗi step; operator nghĩ app hỏng.

### Required Change

`self._ocr_engine` singleton qua `get_ocr(lang)`; Nanook + SKY STEP 3 reuse. Chi tiết: `05_ai_ocr_runtime/02_paddleocr_cache_sop.md`.

### After Improvement

DUT 2–3 OCR khởi động nhanh; UI freeze giảm trên OCR path.

### Improvement Value

| Area | Value |
|---|---|
| Production stability | Giảm UI freeze duration |
| Operator experience | DUT 2+ nhanh hơn; ít lo app treo |
| MES/SFIS integrity | N/A |
| Maintainability | Một helper thay nhiều init |
| Debugging / troubleshooting | Một log "loading" per lang |

### Verification

| Test ID | Setup | Action | Expected result |
|---|---|---|---|
| U-04 | Nanook 3 DUT liên tiếp | Đo thời gian STEP 3 | DUT2/3 &lt;1s OCR init vs baseline |

### Rollback

`PaddleOCR()` mỗi lần gọi. Rủi ro: UI freeze trở lại.

### Suggested Implementation Window

| Window | Reason |
|---|---|
| Month 2 Week 2 | Perf — cần runtime testing |

---

## Fix B-06 / E-08 — `startprogram` finally re-enable Start

### Code Location

| Field | Detail |
|---|---|
| File | sky.py |
| Function / Block | `startprogram` — `try`/`except`/`finally` |
| Current lines | L727 area (sau while loop) |
| Suggested patch location | `finally: self.pushButton_2.setEnabled(True)` sau except fatal |

### Current Problem

Exception fatal trong `startprogram` → nút Start có thể kẹt disabled — operator không restart session mà không đóng app.

### Before Improvement

Crash trong loop → Start disable vĩnh viễn cho session → restart app.

### Required Change

`finally: pushButton_2.setEnabled(True)` trong `startprogram`.

### After Improvement

Exception → Start enabled lại → operator recover nhanh.

### Improvement Value

| Area | Value |
|---|---|
| Production stability | Session recover sau exception |
| Operator experience | Start không kẹt |
| MES/SFIS integrity | N/A |
| Maintainability | Nhỏ, low-risk |
| Debugging / troubleshooting | N/A |

### Verification

| Test ID | Setup | Action | Expected result |
|---|---|---|---|
| U-05 | Ép exception sau disable Start | Fatal trong loop | Start enabled trong finally |

### Rollback

Xóa finally block. Rủi ro: Start kẹt sau crash.

### Suggested Implementation Window

| Window | Reason |
|---|---|
| Month 2 Week 1 | Nhỏ, low-risk |

---

## Fix E-06 — `stopprogram` log cleanup errors

### Code Location

| Field | Detail |
|---|---|
| File | sky.py |
| Function / Block | `stopprogram` — bare except L5403 |
| Current lines | L5398–5403 |
| Suggested patch location | Thay bare `except:` bằng `except Exception as e:` + log |

### Current Problem

Cleanup IO/camera trong `stopprogram` dùng bare except — lỗi cleanup im lặng, khó debug Stop path.

### Before Improvement

Stop có vẻ không phản hồi; cleanup fail không log.

### Required Change

Log cleanup errors thay bare except.

### After Improvement

Stop path có log khi cleanup fail — on-call chẩn đoán nhanh.

### Improvement Value

| Area | Value |
|---|---|
| Production stability | N/A |
| Operator experience | N/A trực tiếp |
| MES/SFIS integrity | N/A |
| Maintainability | Better error visibility |
| Debugging / troubleshooting | Log cleanup failures |

### Verification

| Test ID | Setup | Action | Expected result |
|---|---|---|---|
| U-06 | Mock IO close raise | Bấm Stop | Log cleanup error; Stop vẫn complete |

### Rollback

Khôi phục bare except. Rủi ro thấp.

### Suggested Implementation Window

| Window | Reason |
|---|---|
| Month 2 Week 1 | Nhỏ |

---

## Fix UI-SOP-001 — Operator short-term SOP (no code)

### Code Location

| Field | Detail |
|---|---|
| File | N/A (process) |
| Function / Block | Operator handover / on-call |
| Current lines | N/A |
| Suggested patch location | In SOP ca + bàn giao — section "SOP ngắn hạn" trong file này |

### Current Problem

Operator không biết delay 5s sensor là expected; Stop trong modal/sleep không hoạt động — thao tác sai (double-click Start, kill process).

### Before Improvement

UI đóng băng → operator panic → kill giữa SFIS upload.

### Required Change

Triển khai bảng SOP operator + engineer on-call (đã có trong file). Không code Week 1.

### After Improvement

Operator chờ đúng phase; không kill khi SFIS upload; biết khi nào xem stall SOP (`01_wait_test_stall_fix.md`).

### Improvement Value

| Area | Value |
|---|---|
| Production stability | Giảm kill process mạo hiểm |
| Operator experience | Kỳ vọng delay rõ |
| MES/SFIS integrity | Tránh interrupt upload |
| Maintainability | N/A |
| Debugging / troubleshooting | On-call checklist phase blocking |

### Verification

| Test ID | Setup | Action | Expected result |
|---|---|---|---|
| U-SOP-01 | Bàn giao ca mới | Operator đọc SOP sensor 5s | Không double-click Start trong delay |

### Rollback

N/A — process only.

### Suggested Implementation Window

| Window | Reason |
|---|---|
| Week 1 | Không rủi ro code; giảm thao tác sai ngay |

---

## Hành vi hiện tại

Hầu hết logic AOI chạy trên **Qt main (UI) thread**:

```text
pushButton_2 (Start) slot
  → startprogram() [while True — block cả session]
      → go_run1() [Button_check: while True + modal scan]
      → go_run2() [sensor: while poll + sleep(5) + sync vision]   OR
      → go_run3() [modal STEP prompts + sync grab + sync vision]
```

| Thành phần | Thread | Chặn luồng? |
|-----------|--------|-----------|
| `startprogram` while-loop | UI | Có — cả session test |
| `go_run2` sensor poll | UI | Busy-spin + `processEvents` L798 |
| `time.sleep(5)` sau sensor trigger | UI | **Đóng băng cứng 5s** L813 |
| `get_image()` camera grab | UI | Sync đến khi có frame |
| Cambrian `get_inference_result` | UI | Sync HTTP/RPC |
| PaddleOCR (SKY, Nanook, Cisco) | UI | Load model + inference (vài giây) |
| SFIS `data_upload` / route | UI | Sync SOAP |
| `QMessageBox` / `QInputDialog` | UI | Modal — block đến khi click |

`stopprogram()` (L5398) chỉ set `stop_program=True` và cố cleanup IO/camera. Nó **không**:

- Interrupt `time.sleep(5)`
- Đóng modal dialog đang mở
- Enable lại nút Start trực tiếp (phụ thuộc break loop L699/L725)

---

## Vì sao người vận hành cảm giác app bị đóng băng

| Triệu chứng người vận hành thấy | Nguyên nhân gốc | Bằng chứng |
|----------------------|------------|----------|
| UI chết 5 giây sau khi sensor sáng | `time.sleep(5)` trên UI thread | L813 `go_run2` |
| Bấm Stop — không phản hồi vài giây | Block trong sleep, OCR load, Cambrian, hoặc modal | Bảng Stop `09_threading_and_ui.md` |
| Cửa sổ không đóng ngay | `closeEvent` set flag nhưng loop vẫn trong sleep/dialog | L5411–5419 |
| DUT Nanook đầu tiên rất chậm | `PaddleOCR(...)` tạo mỗi chu kỳ L1685 | Load model trên UI thread |
| SKY STEP 3 pause lâu | PaddleOCR init L2864 mỗi step | UI thread |
| "Please enter for test" — không Stop được | Modal QMessageBox block poll `stop_program` | L705 manual mode |
| Dialog STEP N — Stop bị bỏ qua | Cùng modal blocking | Chuỗi go_run3 |
| App lag khi chờ sensor | Vòng poll IO chặt + `processEvents` | L796–798 |

**Insight chính:** `processEvents()` giữ cửa sổ *vẽ được* nhưng không làm Stop hoặc close **phản hồi nhanh** trong sleep hoặc modal.

---

## SOP ngắn hạn (trước fix Month 2)

### Cho operator

| Tình huống | Hành động | Chờ tối đa |
|-----------|--------|----------|
| Sensor trigger, UI đóng ~5s | **Bình thường** — không double-click Start | 5 giây |
| Stop có vẻ không phản hồi | Chờ sleep/OCR/dialog hiện tại xong, rồi bấm Stop lại | Tới 30–60s khi OCR timeout |
| Kẹt STEP / Flip / scan dialog | Hoàn thành hoặc cancel dialog trước, rồi Stop | Đến khi operator thao tác |
| App không đóng | Bấm Stop, chờ 5s+, thử đóng lại | — |
| Sau Stop, Start bị disable | Chờ 2s; nếu vẫn disable, restart app | — |
| Line có vẻ treo (không dialog) | Xem SOP operator `01_wait_test_stall_fix.md` — có thể stall `wait_test` | Stop → Start |

### Cho engineer on-call

1. Check log trong `log/{YYYYMMDD}/` cho action cuối trước khi freeze.
2. Xác định phase blocking: `sleep`, `PaddleOCR`, `Cambrian`, `QMessageBox`, SFIS.
3. Nếu lặp lại: áp dụng fix stall Phase B trước; lên lịch UI work Month 2.
4. **Không** kill process khi đang SFIS upload nếu tránh được — verify bản ghi MES thủ công.

### Cho bàn giao ca

- Ghi nếu trạm có Stop chậm hoặc delay sensor 5s (expected pre-fix).
- Ghi modal còn mở (prompt STEP) — operator ca sau phải hoàn thành hoặc Stop.

---

## Cải tiến kỹ thuật Month 2 (Phase E)

Từ `11_refactor_plan.md` Month 2 / `01_priority_roadmap.md` Phase E:

| ID | Item | Mục tiêu |
|----|------|--------|
| E-01 | Xóa `time.sleep(5)` | Wait có thể interrupt; Stop &lt; 1s |
| E-03 | Cache PaddleOCR singleton | Không load model mỗi DUT |
| E-06 | `stopprogram` log cleanup errors | Thay bare except L5403 |
| E-07 | Sensor delay có thể interrupt | Poll `stop_program` trong lúc wait |
| E-08 | `startprogram` except re-enable Start | `finally: pushButton_2.setEnabled(True)` L727 |

Dài hạn (Q2): chuyển while-loop `startprogram` sang worker thread — xem Proposed direction bên dưới.

---

## Hướng worker / QTimer đề xuất

### Priority 1 — Rủi ro thấp nhất: sleep có thể interrupt (E-01 / E-07)

Thay L813:

```python
# Before
time.sleep(5)

# After — 500ms slices, check stop flag
for _ in range(10):
    if self.stop_program:
        return
    time.sleep(0.5)
```

**Lợi ích:** Stop trong sensor delay trong ~500ms. **Không đổi kiến trúc.**

### Priority 2 — QTimer cho sensor delay

```python
# Pseudocode — sensor trigger handler
self._sensor_delay_remaining = 10  # 10 × 500ms
self._sensor_timer = QTimer()
self._sensor_timer.timeout.connect(self._on_sensor_delay_tick)
self._sensor_timer.start(500)

def _on_sensor_delay_tick(self):
    if self.stop_program:
        self._sensor_timer.stop()
        return
    self._sensor_delay_remaining -= 1
    if self._sensor_delay_remaining <= 0:
        self._sensor_timer.stop()
        self._do_sensor_grab_and_vision()
```

**Lợi ích:** Event loop UI chạy giữa các tick; Stop được check mỗi 500ms.

### Priority 3 — PaddleOCR service (E-03)

- Tạo `self._ocr_engine` một lần lúc load model hoặc lần dùng đầu.
- Nanook: xóa `PaddleOCR(...)` mỗi chu kỳ L1685.
- SKY STEP 3: tái dùng cùng instance L2864.

Optional: init OCR trong `QThread` lúc app start với splash/progress — load ngoài critical path.

### Priority 4 — Worker thread cho test loop (Q2)

```text
UI thread (Demo)
  Start/Stop buttons → signals
  Displays results ← signals from worker

Worker QThread (TestRunner)
  while not stop:
    wait for DUT trigger / operator signal
    run go_run1/2/3 logic (or decomposed state machine)
    emit wait_test_ready, pass_fail, log_line
```

**Quy tắc:**

- Không chạm Qt widget từ worker — chỉ signals.
- Camera/IO: wrapper thread-safe hoặc worker sở hữu hardware với UI proxy.
- Modal (prompt STEP): ở UI thread — worker pause tại signal `await_step_confirm`.

### Priority 5 — Modal dialog + tương tác Stop

Ngắn hạn: ghi rõ Stop không interrupt modal.

Month 2 option: panel step non-modal trong main window thay `QMessageBox.question` — cho phép poll `stop_program` qua `QTimer` trên UI thread.

---

## Inventory các lời gọi blocking

| Call | Location | Duration | Hành động Month 2 |
|------|----------|----------|----------------|
| `time.sleep(5)` | go_run2 L813 | 5s cố định | QTimer / sliced sleep |
| `PaddleOCR(...)` init | Nanook L1685, SKY L2864 | 2–10s+ | Singleton, background init |
| `get_inference_result` | show_image_* | 1–5s+ | Optional async + callback (Q3) |
| `data_upload` / SFIS route | go_run3, vision | 0.5–5s | Timeout + try/finally (Phase B) |
| `get_image()` | go_run2/3 | 0.1–2s | Chấp nhận được nếu loop check stop |
| `QMessageBox` | startprogram, go_run3 | Đến khi click | Non-modal UI (Q2+) |
| `QInputDialog` | go_run1 L770 | Đến khi click | Validate + cancel path OK |

---

## Verification

### Ngắn hạn (verify SOP chính xác)

| # | Scenario | Kỳ vọng (pre-fix) | Kỳ vọng (post Month 2) |
|---|----------|-------------------|-------------------------|
| U-01 | Sensor trigger → quan sát UI | Đóng ~5s | Phản hồi; optional countdown |
| U-02 | Bấm Stop trong sleep 5s | Trễ đến khi sleep hết | Stop trong 500ms |
| U-03 | Bấm Stop trong STEP QMessageBox | Không tác dụng đến khi đóng dialog | Giống trừ khi non-modal UI |
| U-04 | Nanook 3 DUT liên tiếp | DUT1 chậm (OCR load), DUT2/3 tương tự | DUT2/3 nhanh hơn (cached OCR) |
| U-05 | Stop → Start được enable | Trong 1 vòng loop | Ngay + finally guard |
| U-06 | closeEvent trong go_run2 sleep | Đóng trễ | Đóng sau interruptible wait |
| U-07 | SFIS upload chậm khi pass | UI đóng trong upload | Giống — thêm timeout Q2 |

### Acceptance Month 2

- [ ] Stop trong sensor delay: phản hồi &lt; 1 giây (E-01/E-07)
- [ ] Nanook DUT 2 khởi động OCR: &lt; 1s so baseline (E-03)
- [ ] Exception fatal `startprogram`: nút Start được enable lại (B-06)
- [ ] Không regression độ chính xác pass/fail hoặc MES upload

---

## Rollback

| Thay đổi | Rollback | Rủi ro nếu revert |
|--------|----------|-------------------|
| Sliced sleep / QTimer | Khôi phục `time.sleep(5)` | Stop chậm lại |
| PaddleOCR singleton | `PaddleOCR()` mỗi lần gọi | UI freeze trở lại |
| `startprogram` finally Enable Start | Xóa finally | Start kẹt sau crash |
| Worker thread (Q2) | Revert về loop UI-thread | Lớn — chỉ khi regression nặng |

**Luôn** giữ `sky.py` đã tag trước thay đổi UI Month 2. Rollback E-01 và E-03 độc lập nếu cần.

---

## Implementation Window

| Fix ID | Suggested window | Reason |
|--------|------------------|--------|
| SOP operator (không code) | Week 1 | Giảm thao tác sai ngay, không rủi ro code |
| E-01/E-07 sliced sleep | Month 2 Week 1 | Đổi timing loop — cần đo Stop latency trên clone |
| B-06 finally re-enable Start | Month 2 Week 1 | Nhỏ, low-risk |
| E-06 log cleanup errors | Month 2 Week 1 | Nhỏ |
| E-03 PaddleOCR singleton | Month 2 Week 2 | Perf — cần runtime testing (xem `05_ai_ocr_runtime/02`) |
| Worker thread Q2 | Q2 (design trước) | Refactor lớn — không big-bang |

## Checklist triển khai (Month 2)

```text
Week 1
  [ ] E-01/E-07: Thay sleep(5) bằng interruptible wait
  [ ] B-06: startprogram finally re-enable Start
  [ ] E-06: Log stopprogram cleanup errors

Week 2
  [ ] E-03: PaddleOCR singleton (Nanook branch trước — worst offender)
  [ ] E-03: SKY STEP 3 reuse

Week 3–4
  [ ] Đo Stop latency trên clone — ghi baseline
  [ ] Xác nhận người vận hành 1 ca
  [ ] Plan Q2 worker thread spike (design doc only)
```

---

## Tài liệu tham chiếu

| Doc | Nội dung liên quan |
|-----|------------------|
| `docs/aoi-analysis/09_threading_and_ui.md` | Full blocking inventory, Runthread, recommendations |
| `docs/aoi-analysis/05_runtime_flow.md` | startprogram, go_run2 sleep, stop behavior |
| `docs/aoi-analysis/04_state_machine.md` | Rủi ro `stop_program` trong sleep/modal |
| `docs/aoi-analysis/10_risks_and_bugs.md` | UI/threading, startprogram blocking |
| `docs/aoi-improvement/01_priority_roadmap.md` | Phase E items |
| `docs/aoi-improvement/01_runtime_stability/01_wait_test_stall_fix.md` | Phân biệt stall vs freeze |
