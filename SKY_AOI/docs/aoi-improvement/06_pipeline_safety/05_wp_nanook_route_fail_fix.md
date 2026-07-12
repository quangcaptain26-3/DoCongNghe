# WP & Nanook — Route Fail, SN & Upload — Compact Playbook

**File:** `sky.py` · **Workstream:** `06_pipeline_safety`  
**Nguồn:** `17_wp_pipeline.md`, `18_nanook_pipeline.md`, `10_risks_and_bugs.md`, `02_sfis_mes_integrity/`  
**Luật:** `thissn=""` (không `"None"`); route fail → `check_result_OK=False` rõ ràng; upload fail skip SN rỗng/None; Nanook OCR rỗng → không IndexError.

> Repo: WP entry G1323 `thissn="None"`; Nanook G1551; route WP G4329; Nanook OCR STEP3 G4810; `nanook_model_tan` G4891. **Ctrl+F** `show_image_WP`, `show_image_Nanook`.

---

## Improvement Purpose

Mục tiêu của cải tiến này là WP/Nanook pipeline fail an toàn khi route fail, SN stale, OCR rỗng, hoặc upload literal `"None"` — reset `thissn=""`, clear `check_result_OK`, skip upload SN invalid, guard IndexError/KeyError.

## Before Improvement

Trước cải tiến: WP/Nanook entry set `thissn="None"` (G1324/G1551) → MES nhận chữ "None"; route fail không set `check_result_OK=False` → Cambrian chạy với state cũ; fail upload dùng stale SN; Nanook OCR rỗng → IndexError `result[0][0]`; STEP5 KeyError `nanook_model_tan`. False pass hoặc crash mid-cycle.

## After Improvement

Sau cải tiến: `thissn=""` + `check_result_OK=False` đầu chu kỳ; route fail explicit clear flag; `safe_upload_fail` skip empty SN; Nanook empty OCR guard; STEP5 dict lookup guard. Fail path an toàn; MES không "None"; operator thấy Fail rõ; line recover.

## Improvement Value

| Area                        | Value |
| --------------------------- | ----- |
| Production stability        | Giảm crash IndexError/KeyError Nanook; giảm stall |
| Operator experience         | Fail rõ route/OCR thay vì crash |
| MES/SFIS integrity          | Không upload `"None"` hoặc stale SN; route fail không pass giả |
| Maintainability             | Reset pattern thống nhất WP/Nanook entry |
| Debugging / troubleshooting | Log route fail vs OCR empty vs KeyError |

## Before / After Summary

| Aspect           | Before | After |
| ---------------- | ------ | ----- |
| Runtime behavior | thissn="None"; route fail stale state; OCR crash | Reset SN; explicit flags; guards |
| Error handling   | IndexError/KeyError unhandled | Empty guard; dict key check |
| Operator impact  | Crash hoặc MES "None" | Fail message; correct skip upload |
| Production risk  | MES trace wrong; line down | Cải thiện WP/Nanook data integrity |

---

## Bảng tổng

| ID | Vấn đề | Đi tới | Anchor (đúng chỗ khi thấy…) | Thao tác | Test |
|----|--------|--------|-----------------------------|----------|------|
| **PIPE-W01** | `thissn="None"` literal | G1324 / G1551 | Đầu nhánh WP / Nanook orchestration · **Sai:** trong vision decode | **Đổi** → `self.thissn=""` + `check_result_OK=False` | W-02 không upload "None" |
| **PIPE-W02** | Route fail không clear flag | G4329 / F `check route FAIL` trong `show_image_WP` | Trong `if sfisreturn[0]=="0":`, khi **không** repair match · **Sai:** chỉ repair branches | **+1 dòng** `check_result_OK=False` | W-01 không Cambrian |
| **PIPE-W03** | Fail upload `thissn` stale | G1535+ / G1764+ | go_run3 fail handlers WP/Nanook · **Sai:** pass upload vision | **Đổi** `safe_upload_fail` + skip empty SN | W-03 SFIS throw → wait_test |
| **PIPE-N01** | Nanook OCR rỗng → crash | G4810 / F `nanook_ocr.ocr` STEP 3 | Trước `result[0][0][1][0]` · **Sai:** STEP 5 | **Chèn** empty guard | N-03 no IndexError |
| **PIPE-N02** | `nanook_model_tan` KeyError | G4891 / F `nanook_model_tan[self.nanook_ocr_model]` | Trước dict lookup STEP 5 · **Sai:** module dict | **Chèn** `if key not in dict` | N-04 step5 False |

**Ship:** PIPE-W01 → PIPE-W02 → PIPE-N01 → PIPE-N02 → PIPE-W03 (SFIS helper)

---

## Diff patches

### PIPE-W01 · reset entry G1323 / G1550

```python
# TRƯỚC (WP)
        elif self.select_model == "WP_check" or self.select_model == "C9105AXW_E":
            self.thissn="None"
            self.step1 = False

# SAU
        elif self.select_model == "WP_check" or self.select_model == "C9105AXW_E":
            self.thissn = ""
            self.check_result_OK = False
            self.step1 = False
            ...
```

```python
# TRƯỚC (Nanook)
        elif self.select_model == "Nanook":
            self.thissn = "None"

# SAU
        elif self.select_model == "Nanook":
            self.thissn = ""
            self.check_result_OK = False
```

---

### PIPE-W02 · route fail explicit G4329

**Đúng chỗ:** `show_image_WP` STEP 1, `if sfisreturn[0] == "0":` khi không vào repair sub-branches · **Sai:** Nanook (copy pattern)

```python
# TRƯỚC
                        if sfisreturn[0] == "0":
                            logging.info(f"check route FAIL")
                            self.myuihand.textbox.emit("check route FAIL")
                            print(sfisreturn)
                            if "[LF#:0]" in sfisreturn and ...:
                                ...
                            elif "[LF#:1]" in sfisreturn and ...:
                                ...

# SAU — thêm else cuối nhánh route fail
                        if sfisreturn[0] == "0":
                            ...
                            if "[LF#:0]" in sfisreturn and ...:
                                ...
                            elif "[LF#:1]" in sfisreturn and ...:
                                ...
                            else:
                                self.check_result_OK = False
```

Lặp tương tự `show_image_Nanook` route block (~G4707+).

---

### PIPE-N01 · Nanook STEP 3 OCR G4810

```python
# TRƯỚC
                result = self.nanook_ocr.ocr("source/Nanook_ocr.jpg", cls=True)
                self.nanook_ocr_model=result[0][0][1][0]
                ...
                self.step3 = True

# SAU
                result = self.nanook_ocr.ocr("source/Nanook_ocr.jpg", cls=True)
                if not result or not result[0] or not result[0][0]:
                    logging.error("Nanook STEP 3 OCR empty")
                    self.myuihand.textbox.emit("Nanook STEP 3 OCR empty")
                    self.step3 = False
                    return
                self.nanook_ocr_model = result[0][0][1][0]
                ...
                self.step3 = True  # optional: gate pass logic Tháng 3
```

---

### PIPE-N02 · dict guard G4891

```python
# TRƯỚC
                if nanook_model_tan[self.nanook_ocr_model] == self.thistan:

# SAU
                if self.nanook_ocr_model not in nanook_model_tan:
                    logging.error(f"Unknown Nanook OCR model: {self.nanook_ocr_model}")
                    self.step5 = False
                    return
                if nanook_model_tan[self.nanook_ocr_model] == self.thistan:
```

---

### PIPE-W03 · fail upload pattern (mẫu WP step1 fail G1535)

```python
# TRƯỚC
                            self.mysfis.data_upload(self.thissn, self.data, error="BDFA01")

# SAU — dùng helper hoặc inline guard
                            sn = (self.thissn or "").strip()
                            if sn and sn != "None" and self.sfis_choose:
                                try:
                                    self.mysfis.data_upload(sn, self.data, error="BDFA01")
                                except Exception as e:
                                    logging.error(f"SFIS upload error: {e}")
```

Lặp Nanook fail sites G1642+, G1764+.

Rollback: không khôi phục `thissn="None"`.

---

## Verification

| Test ID | Fix ID | Setup | Action | Expected result |
|---------|--------|-------|--------|-----------------|
| T-W01 | PIPE-W01 | WP/Nanook decode fail sớm | Fail cycle | Không bản ghi MES `"None"` |
| T-W02 | PIPE-W02 | Mock `check_route` trả `"0"` không repair tag | STEP 1 | `check_result_OK=False`; không chạy Cambrian; step1=False |
| T-W03 | PIPE-W03 | Mock SFIS throw + SN rỗng | Fail cycle | Skip upload SN invalid; log lỗi; `wait_test=True` |
| T-N01 | PIPE-N01 | `source/Nanook_ocr.jpg` trống/hỏng | STEP 3 | `step3=False`; không IndexError; recover |
| T-N02 | PIPE-N02 | Chuỗi OCR không có trong `nanook_model_tan` | STEP 5 | `step5=False`; log unknown model; không KeyError |
| T-W04 | PIPE-W01 | SKY pass rồi WP route fail | WP cycle | Không stale `check_result_OK` từ SKY |

Chi tiết matrix W/N bên dưới.

## Test matrix

| # | Pipeline | Scenario | Kỳ vọng |
|---|----------|----------|---------|
| W-01 | WP | Route fail | check_result_OK False; no Cambrian |
| W-02 | WP | Decode fail | No MES "None" |
| N-01 | Nanook | Route fail | Giống W-01 |
| N-03 | Nanook | OCR empty STEP 3 | step3 False; no crash |
| N-04 | Nanook | Unknown OCR model | step5 False |
| W-04 | WP | After SKY pass, route fail | No stale check_result_OK |

## Rollback

| Fix ID | Rollback | Behavior cũ quay lại | Rủi ro nếu rollback |
|--------|----------|----------------------|---------------------|
| PIPE-W01 | Khôi phục `thissn="None"` | MES nhận literal None | **Không khuyến nghị** — audit MES fail |
| PIPE-W02 | Xóa `else: check_result_OK=False` | Route fail dùng state cũ | False pass Cambrian với DUT route fail |
| PIPE-W03 | Bỏ guard SN + try | Upload SN rỗng/stale; throw → stall | MES sai + treo |
| PIPE-N01 | Xóa empty guard | OCR rỗng → IndexError | Crash Nanook STEP 3 |
| PIPE-N02 | Xóa dict guard | KeyError STEP 5 | Crash Nanook STEP 5 |

## Implementation Window

| Fix ID | Suggested window | Reason |
|--------|------------------|--------|
| PIPE-W01 | Week 1 | 2 dòng/site; chặn `"None"` MES (P1) |
| PIPE-W02 | Week 1–2 | 1 dòng else; cần mock route fail test |
| PIPE-N01 | Week 1–2 | Guard crash; cần ảnh OCR trống test |
| PIPE-N02 | Week 2 | Guard KeyError |
| PIPE-W03 | Week 2 / Month 2 | Đi cùng SFIS helper (`02_sfis_mes_integrity/01`) |

## Smoke

- [ ] W-01 mock route fail → không "inference finish" Cambrian
- [ ] N-03 empty OCR image → no IndexError

## Per-Fix Detail

### PIPE-W01 — Reset `thissn` entry WP/Nanook

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G1324 (WP) / G1551 (Nanook) |
| Lines | Đầu nhánh WP_check/C9105AXW_E và Nanook orchestration |
| Legacy alias | W-02, N-01 (test matrix) |

#### Current Problem

Entry set `thissn="None"` literal → MES nhận chữ "None"; stale SN từ cycle trước.

#### Before Improvement

```python
            self.thissn="None"   # WP
            self.thissn = "None" # Nanook
```

#### Required Change

Đổi → `self.thissn = ""` + `self.check_result_OK = False` đầu mỗi chu kỳ.

#### After Improvement

Decode fail sớm → không upload `"None"`; flags reset.

#### Improvement Value

| Area | Value |
|------|-------|
| MES/SFIS integrity | P1 — không literal "None" MES |
| Production stability | Clean state mỗi cycle |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-W01 | WP/Nanook decode fail sớm | Fail cycle | Không bản ghi MES `"None"` |
| W-02 | WP decode fail | Cycle | No MES "None" |

#### Rollback

Khôi phục `thissn="None"`. **Rủi ro:** **không khuyến nghị** — audit MES fail.

#### Suggested Implementation Window

Week 1 (P0/P1) — 2 dòng/site.

---

### PIPE-W02 — WP route fail `check_result_OK` clear

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G4329 / `check route FAIL` trong `show_image_WP` |
| Lines | Trong `if sfisreturn[0]=="0":`, khi không repair match |
| Legacy alias | W-01, W-04 (test matrix) |

#### Current Problem

Route fail không set `check_result_OK=False` → Cambrian chạy với state cũ từ SKY pass.

#### Before Improvement

Route fail chỉ log "check route FAIL" — không clear flag.

#### Required Change

Thêm `else:` cuối nhánh route fail → `self.check_result_OK = False`. Lặp Nanook ~G4707+.

#### After Improvement

Route fail → không Cambrian; step1=False; không false pass.

#### Improvement Value

| Area | Value |
|------|-------|
| MES/SFIS integrity | Tránh Cambrian pass khi route fail |
| Production stability | Không stale flag từ model trước |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-W02 | Mock `check_route` trả `"0"` không repair | STEP 1 | `check_result_OK=False`; không Cambrian |
| W-01 | WP route fail | STEP 1 | No Cambrian |
| T-W04 | SKY pass rồi WP route fail | WP cycle | Không stale `check_result_OK` |

#### Rollback

Xóa `else: check_result_OK=False`. **Rủi ro:** false pass Cambrian.

#### Suggested Implementation Window

Week 1–2 — 1 dòng else; mock route fail test.

---

### PIPE-W03 — WP/Nanook fail upload SN guard

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G1535+ (WP) / G1642+, G1764+ (Nanook) go_run3 fail |
| Lines | Fail handlers `data_upload(self.thissn` |
| Legacy alias | **SFIS-001** pattern; W-03 |

#### Current Problem

Fail upload dùng stale/empty `thissn`; không try/except — SFIS throw stall.

#### Before Improvement

```python
                            self.mysfis.data_upload(self.thissn, self.data, error="BDFA01")
```

#### Required Change

`sn = (self.thissn or "").strip()`; skip nếu rỗng/`"None"`; try/except; `wait_test` ngoài except. Dùng `safe_upload_fail` khi helper có (Month 2).

#### After Improvement

Skip upload SN invalid; SFIS throw → log + cycle continues.

#### Improvement Value

| Area | Value |
|------|-------|
| MES/SFIS integrity | Không upload SN rỗng/stale |
| Production stability | Không stall SFIS throw |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-W03 | Mock SFIS throw + SN rỗng | Fail cycle | Skip upload; log; `wait_test=True` |

#### Rollback

Bỏ guard SN + try. **Rủi ro:** MES sai + treo.

#### Suggested Implementation Window

Week 2 / Month 1 — đi cùng SFIS helper.

---

### PIPE-N01 — Nanook STEP 3 OCR empty guard

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G4810 / `nanook_ocr.ocr` STEP 3 |
| Lines | Trước `result[0][0][1][0]` |
| Legacy alias | N-03 (test matrix) |

#### Current Problem

OCR rỗng → `result[0][0]` IndexError crash mid-cycle.

#### Before Improvement

```python
                result = self.nanook_ocr.ocr(...)
                self.nanook_ocr_model=result[0][0][1][0]
```

#### Required Change

`if not result or not result[0] or not result[0][0]:` → log, `step3=False`, `return`.

#### After Improvement

Empty OCR → `step3=False`; không IndexError; recover.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Giảm crash Nanook STEP 3 |
| Operator experience | "Nanook STEP 3 OCR empty" message |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-N01 | `source/Nanook_ocr.jpg` trống/hỏng | STEP 3 | `step3=False`; không IndexError |
| N-03 | Empty OCR image | STEP 3 | step3 False; no crash |

#### Rollback

Xóa empty guard. **Rủi ro:** crash Nanook STEP 3.

#### Suggested Implementation Window

Week 1–2 — cần ảnh OCR trống test.

---

### PIPE-N02 — Nanook `nanook_model_tan` KeyError guard

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G4891 / `nanook_model_tan[self.nanook_ocr_model]` |
| Lines | Trước dict lookup STEP 5 |
| Legacy alias | N-04 (test matrix) |

#### Current Problem

OCR string không có trong dict → KeyError crash STEP 5.

#### Before Improvement

```python
                if nanook_model_tan[self.nanook_ocr_model] == self.thistan:
```

#### Required Change

`if self.nanook_ocr_model not in nanook_model_tan:` → log unknown, `step5=False`, `return`.

#### After Improvement

Unknown OCR model → `step5=False`; log rõ; không KeyError.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Giảm crash Nanook STEP 5 |
| Debugging | Log unknown model string |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-N02 | OCR string không trong `nanook_model_tan` | STEP 5 | `step5=False`; không KeyError |
| N-04 | Unknown OCR model | STEP 5 | step5 False |

#### Rollback

Xóa dict guard. **Rủi ro:** crash Nanook STEP 5.

#### Suggested Implementation Window

Week 2 — guard KeyError.

---

## Ref

`17_wp_pipeline.md` · `18_nanook_pipeline.md` · `02_sfis_mes_integrity/02_sn_reset_and_validation.md` · `05_ai_ocr_runtime/01_cambrian_guard_policy.md`
