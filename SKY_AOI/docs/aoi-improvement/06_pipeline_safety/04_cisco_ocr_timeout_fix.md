# Cisco OCR Timeout & SN_8P — Compact Playbook

**File:** `sky.py` · **Workstream:** `06_pipeline_safety`  
**Nguồn:** `16_cisco_pipeline.md`, `10_risks_and_bugs.md`, `01_runtime_stability/01_wait_test_stall_fix.md`  
**Luật:** OCR timeout → `step1=False` + `wait_test`; `SN_8P` reset đầu chu kỳ; fail upload chỉ khi SN hợp lệ; STEP2 upload trong try.

> Repo: Cisco branch G1159; OCR poll G3614–3622; index G3697; fail step2 upload G1224–1228; `Runthread` G5394. **Ctrl+F** `show_image_C1000_8FP_E_2G_L`.

---

## Improvement Purpose

Mục tiêu của cải tiến này là Cisco pipeline fail an toàn khi OCR timeout, buffer chưa init, hoặc SN_8P stale — tránh IndexError crash và upload fail với PVN DUT trước. Chuẩn hóa init buffer và timeout branch.

## Before Improvement

Trước cải tiến: cold start Cisco thiếu `ocr_8P_result` init → AttributeError; OCR poll 60×0.5s timeout không set `step1=False` → index vào empty list crash (G3697); `SN_8P` không reset đầu chu kỳ — DUT2 fail sớm upload PVN DUT1; STEP2 fail upload không try/except; Runthread busy loop trên `[]`.

## After Improvement

Sau cải tiến: init `ocr_8P_result=[]`, `SN_8P=""` đầu nhánh Cisco; timeout → `step1=False` + Fail UI + `wait_test`; fail upload STEP2 bọc try (SFIS-001); Runthread không busy spin. Operator thấy Fail rõ; line recover; MES không nhận SN stale.

## Improvement Value

| Area                        | Value |
| --------------------------- | ----- |
| Production stability        | Giảm crash IndexError/AttributeError trên Cisco line |
| Operator experience         | OCR timeout → Fail message thay vì crash |
| MES/SFIS integrity          | Không upload fail với SN_8P DUT trước |
| Maintainability             | Init pattern đầu branch; timeout branch tái dùng |
| Debugging / troubleshooting | Log timeout vs index error — dễ trace OCR path |

## Before / After Summary

| Aspect           | Before | After |
| ---------------- | ------ | ----- |
| Runtime behavior | OCR timeout → crash; stale SN_8P upload | Timeout fail path; SN reset each cycle |
| Error handling   | No buffer init; no try on step2 fail upload | Init buffers; try/except SFIS |
| Operator impact  | Crash/restart Cisco line | Fail + wait_test; cycle continues |
| Production risk  | MES SN wrong + line down | Đảm bảo dữ liệu MES Cisco chính xác hơn |

---

## Bảng tổng

| ID | Vấn đề | Đi tới | Anchor (đúng chỗ khi thấy…) | Thao tác | Test |
|----|--------|--------|-----------------------------|----------|------|
| **PIPE-C01** | Buffer OCR chưa init | G1159 / F `elif self.select_model == "C1000` | Đầu nhánh Cisco, sau `step1=False` · **Sai:** trong vision | **Chèn** `ocr_8P_result=[]`, `SN_8P=""` | C-01 no AttributeError |
| **PIPE-C02** | OCR timeout → index crash | G3622 / F `for ttime in range(60)` | Sau vòng poll `ocr_8P_result`, trước `if self.step1_1` · **Sai:** trong Runthread | **Chèn** timeout fail branch | C-02 step1 False |
| **PIPE-C03** | STEP2 fail upload no try | G1224 / F `data_upload(self.SN_8P` step2 fail | Block `elif self.step2 == False` · **Sai:** step1 fail G1249 (đã có try) | **Bọc** try/except — copy SFIS-001 | C-05 mock throw |
| **PIPE-C04** | `Runthread` busy emit | G5396 / F `while result==[]` trong `Runthread.run` | Trong `run()` · **Sai:** Cisco vision | **Xóa** busy loop; OCR trực tiếp | C-01 poll ổn |

**Ship:** PIPE-C01 → PIPE-C04 → PIPE-C02 → PIPE-C03

---

## Diff patches

### PIPE-C01 · init buffers G1159

```python
# TRƯỚC
        elif self.select_model == "C1000-8FP-E-2G-L" or ...:
            self.step1 = False
            self.step2 = False

# SAU
        elif self.select_model == "C1000-8FP-E-2G-L" or ...:
            self.step1 = False
            self.step2 = False
            self.ocr_8P_result = []
            self.ocr1_8P_result = []
            self.SN_8P = ""
```

---

### PIPE-C02 · timeout sau poll G3614–3636

**Đúng chỗ:** sau vòng `for ttime in range(60)` đầu tiên (và thứ hai nếu C1000), trước `logging.info("label ocr finish1111")` · **Sai:** trong `for each_ocr_check`

```python
# TRƯỚC
                for ttime in range(60):
                    if self.ocr_8P_result==[]:
                        time.sleep(0.5)
                        ...
                    elif self.ocr_8P_result!=[]:
                        self.thread.quit()
                        ...
                        break
                ...
                logging.info("label ocr finish1111")

# SAU — sau cả hai vòng poll (nếu có)
                ocr_ready = self.ocr_8P_result and self.ocr_8P_result != []
                if self.select_model in (...C1000 variants...):
                    ocr_ready = ocr_ready and self.ocr1_8P_result and self.ocr1_8P_result != []
                if not ocr_ready:
                    logging.error("Cisco OCR timeout")
                    self.myuihand.textbox.emit("Cisco OCR timeout")
                    self.step1 = False
                    return
                if not self.ocr_8P_result[0]:
                    logging.error("Cisco OCR empty result")
                    self.step1 = False
                    return
                logging.info("label ocr finish1111")
```

---

### PIPE-C03 · STEP2 fail upload G1224 (SFIS-001 pattern)

```python
# TRƯỚC
                            if self.sfis_choose==True:
                                self.mysfis.data_upload(self.SN_8P, self.data, error="BDFA01")
                            logging.error("fail upload OK")
                            ...
                            self.wait_test = True

# SAU
                            try:
                                if self.sfis_choose==True and self.SN_8P:
                                    self.mysfis.data_upload(self.SN_8P, self.data, error="BDFA01")
                                    logging.error("fail upload OK")
                                    self.myuihand.textbox.emit("fail upload OK")
                            except Exception as e:
                                logging.error(f"SFIS fail upload error: {e}")
                                self.myuihand.textbox.emit("SFIS upload failed — cycle continues")
                            self.wait_test = True
```

---

### PIPE-C04 · Runthread G5394

```python
# TRƯỚC
    def run(self):
        result = []
        while result==[]:
            self.signal.emit(result)
            ocr = PaddleOCR(use_angle_cls=True, lang="ch")
            ...
            result = ocr.ocr(img_path, cls=True)
            self.signal.emit(result)

# SAU
    def run(self):
        ocr = PaddleOCR(use_angle_cls=True, lang="ch")  # hoặc shared get_ocr — xem 05_ai_ocr_runtime
        result = ocr.ocr(self.ocr_img, cls=True)
        self.signal.emit(result if result else [])
```

Rollback Runthread riêng PR nếu thread-safety concern.

---

## Verification

| Test ID | Fix ID | Setup | Action | Expected result |
|---------|--------|-------|--------|-----------------|
| T-C01 | PIPE-C01 | Cisco DUT đầu sau launch app (cold start) | STEP 1 | Không AttributeError trên `ocr_8P_result` |
| T-C02 | PIPE-C02 | Block/throttle OCR >30s (đổi tên `source/8P/ocr1.jpg` giữa poll) | STEP 1 | `step1=False`; Fail; `wait_test=True`; không IndexError |
| T-C03 | PIPE-C01 | DUT1 pass (set `SN_8P`), DUT2 fail trước set SN | Fail cycle DUT2 | Không upload PVN DUT1; SN rỗng skip |
| T-C04 | PIPE-C03 | Mock `data_upload` throw ở step2 fail | Fail cycle | Log lỗi; `wait_test=True` |
| T-C05 | PIPE-C04 | OCR pass STEP 1 qua Runthread | 1 cycle | Một emit; không busy spin trên `[]` |

Chi tiết matrix C-01…C-05 bên dưới.

## Test matrix

| # | Scenario | Kỳ vọng |
|---|----------|---------|
| C-01 | Cold start STEP 1 | Không AttributeError poll |
| C-02 | Block OCR >30s | step1 False; wait_test |
| C-03 | Fail trước set SN_8P | Không PVN cũ trên MES |
| C-05 | Mock SFIS throw step2 | wait_test True |

## Rollback

| Fix ID | Rollback | Behavior cũ quay lại | Rủi ro nếu rollback |
|--------|----------|----------------------|---------------------|
| PIPE-C01 | Xóa 3 dòng init | Cold start AttributeError; SN stale | MES trace sai — không khuyến nghị |
| PIPE-C02 | Xóa timeout branch | OCR timeout → IndexError crash | Crash Cisco quay lại |
| PIPE-C03 | Bỏ try/except | SFIS throw → stall | Treo khi SFIS lỗi |
| PIPE-C04 | Git restore `Runthread.run` | Busy loop emit | Riêng PR — revert nếu thread issue |

## Implementation Window

| Fix ID | Suggested window | Reason |
|--------|------------------|--------|
| PIPE-C01 | Week 1 | 3 dòng chèn; chặn crash + SN stale (P0/P1) |
| PIPE-C02 | Week 1–2 | Cần simulate timeout trên clone |
| PIPE-C03 | Week 1–2 | Cùng đợt SFIS-001 |
| PIPE-C04 | Week 3–4 / Month 1 | Đổi thread behavior — PR riêng, test kỹ |

## Smoke

- [ ] C-01 một Cisco model Pass cycle
- [ ] C-02 simulate timeout → line recover

## Per-Fix Detail

### PIPE-C01 — Cisco OCR buffer init

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G1159 / `elif self.select_model == "C1000` |
| Lines | Đầu nhánh Cisco, sau `step1=False`/`step2=False` |
| Legacy alias | C-01 (test matrix) |

#### Current Problem

Cold start Cisco thiếu `ocr_8P_result`/`SN_8P` init → AttributeError; `SN_8P` stale từ DUT trước → fail upload PVN DUT1.

#### Before Improvement

Chỉ `step1=False`, `step2=False` — không reset buffers.

#### Required Change

Chèn `self.ocr_8P_result = []`, `self.ocr1_8P_result = []`, `self.SN_8P = ""` đầu nhánh Cisco.

#### After Improvement

Cold start không AttributeError; mỗi chu kỳ SN reset; DUT2 fail không upload PVN DUT1.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Chặn crash + SN stale (P0/P1) |
| MES/SFIS integrity | Không upload SN DUT trước |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-C01 | Cisco DUT đầu cold start | STEP 1 | Không AttributeError poll |
| T-C03 | DUT1 pass, DUT2 fail trước set SN | Fail DUT2 | Không upload PVN DUT1 |
| C-03 | Fail trước set SN_8P | Cycle | Không PVN cũ MES |

#### Rollback

Xóa 3 dòng init. **Rủi ro:** MES trace sai — không khuyến nghị.

#### Suggested Implementation Window

Week 1 (P0) — 3 dòng chèn.

---

### PIPE-C02 — Cisco OCR timeout fail branch

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G3622 / `for ttime in range(60)` |
| Lines | Sau vòng poll `ocr_8P_result`, trước `if self.step1_1` |
| Legacy alias | C-02 (test matrix) |

#### Current Problem

OCR poll 60×0.5s timeout không set `step1=False` → index vào empty list crash (G3697).

#### Before Improvement

Poll loop kết thúc im lặng → `ocr_8P_result[0]` IndexError.

#### Required Change

Sau poll: check `ocr_ready`; nếu timeout/empty → log, `step1=False`, Fail UI, `return`. Check C1000 variants cần cả `ocr1_8P_result`.

#### After Improvement

OCR timeout → `step1=False`; line recover; không IndexError.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Giảm crash IndexError Cisco line |
| Operator experience | "Cisco OCR timeout" message |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-C02 | Block OCR >30s | STEP 1 | `step1=False`; `wait_test=True`; không IndexError |
| C-02 | Throttle OCR | STEP 1 | Fail + recover |

#### Rollback

Xóa timeout branch. **Rủi ro:** crash Cisco quay lại.

#### Suggested Implementation Window

Week 1–2 — simulate timeout trên clone.

---

### PIPE-C03 — Cisco STEP2 fail upload try/except

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G1224 / `data_upload(self.SN_8P` step2 fail |
| Lines | Block `elif self.step2 == False` |
| Legacy alias | **SFIS-001** Cisco #1 |

#### Current Problem

STEP2 fail upload bare `data_upload` — SFIS throw skip `wait_test`; upload có thể dùng SN rỗng.

#### Before Improvement

```python
                            if self.sfis_choose==True:
                                self.mysfis.data_upload(self.SN_8P, ...)
                            self.wait_test = True
```

#### Required Change

Bọc try/except SFIS-001 pattern; guard `self.SN_8P` non-empty; `wait_test` ngoài except.

#### After Improvement

SFIS throw → log; cycle continues; không upload SN rỗng.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Không stall SFIS throw |
| MES/SFIS integrity | Skip upload SN invalid |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-C04 | Mock `data_upload` throw step2 fail | Fail cycle | Log lỗi; `wait_test=True` |
| C-05 | Mock SFIS throw | step2 fail | wait_test True |

#### Rollback

Bỏ try/except. **Rủi ro:** treo khi SFIS lỗi.

#### Suggested Implementation Window

Week 1–2 — cùng đợt SFIS-001.

---

### PIPE-C04 — `Runthread` busy loop fix

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G5396 / `while result==[]` trong `Runthread.run` |
| Lines | G5394–5401 |
| Legacy alias | **OCR-004 Runthread** (AI-O05) |

#### Current Problem

`Runthread.run` busy loop `while result==[]` emit + init PaddleOCR mỗi run — CPU spin.

#### Before Improvement

```python
        while result==[]:
            self.signal.emit(result)
            ocr = PaddleOCR(...)
            result = ocr.ocr(...)
```

#### Required Change

Xóa busy loop; OCR trực tiếp một lần; optional `get_ocr("ch")` shared cache (AI-O05).

#### After Improvement

Một emit; không busy spin trên `[]`.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Giảm CPU busy loop |
| Maintainability | Align với OCR cache SOP |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-C05 | OCR pass STEP 1 qua Runthread | 1 cycle | Một emit; không busy spin |

#### Rollback

Git restore `Runthread.run`. **Rủi ro:** revert riêng PR nếu thread issue.

#### Suggested Implementation Window

Week 3–4 / Month 1 — PR riêng; test thread-safety.

---

## Ref

`16_cisco_pipeline.md` · `02_sfis_mes_integrity/02_sn_reset_and_validation.md` · `05_ai_ocr_runtime/02_paddleocr_cache_sop.md`
