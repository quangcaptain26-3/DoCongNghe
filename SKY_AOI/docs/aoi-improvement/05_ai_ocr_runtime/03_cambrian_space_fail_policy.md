# Chính Sách Fail `cambrian_space` — Compact Playbook

**File:** `sky.py` · **Workstream:** `05_ai_ocr_runtime`  
**Nguồn:** `07_camera_io_sfis.md` §5, `10_risks_and_bugs.md`, `19_button_check_pipeline.md`  
**Luật:** `cambrian_space` chỉ trả `"Pass"` hoặc `"Fail"` — **không** `None`; ROI list rỗng = `"Fail"`.

> Repo: `cambrian_space` G2462–2512; except G2510–2512; empty-pass G2502. Trùng **AI-001** trong `01_wait_test_stall_fix.md`. **Ctrl+F** `def cambrian_space`.

---

## Improvement Purpose

Mục tiêu của cải tiến này là chuẩn hóa `cambrian_space` chỉ trả `"Pass"` hoặc `"Fail"` — không `None`; ROI rỗng hoặc exception → Fail rõ. Tránh false pass và stall khi caller không xử lý `None`.

## Before Improvement

Trước cải tiến: except cuối `cambrian_space` im lặng → implicit `None` (G2510); ROI list rỗng `[]` → `False not in []` = True → **pass giả** (G2502); Button_check thiếu ximian ROI → pass + SFIS upload sai. Caller chỉ check Pass/Fail — `None` không set `stepN` rõ → stall hoặc ambiguous state.

## After Improvement

Sau cải tiến: except → `return "Fail"`; guard empty ROI + len mismatch → Fail; caller thêm `else: stepN=False` cho legacy None; Button_check ximian precheck. Mọi path AI → Pass hoặc Fail rõ; operator thấy Fail UI; không upload pass giả.

## Improvement Value

| Area                        | Value |
| --------------------------- | ----- |
| Production stability        | Giảm stall từ None return; giảm false pass |
| Operator experience         | Fail rõ thay vì ambiguous/step không advance |
| MES/SFIS integrity          | Tránh SFIS pass upload khi Cambrian fail/empty ROI |
| Maintainability             | Contract rõ: Pass/Fail only |
| Debugging / troubleshooting | Log exception + Fail path; dễ trace AI lỗi |

## Before / After Summary

| Aspect           | Before | After |
| ---------------- | ------ | ----- |
| Runtime behavior | except → None; [] → Pass | except/empty → Fail |
| Error handling   | Implicit None; empty list pass bug | Explicit Fail; caller else branch |
| Operator impact  | Pass giả hoặc treo step | Fail UI rõ; count cập nhật |
| Production risk  | MES pass sai; line stall | Đảm bảo AI fail an toàn |

---

## Bảng tổng

| ID | Vấn đề | Đi tới | Anchor (đúng chỗ khi thấy…) | Thao tác | Test |
|----|--------|--------|-----------------------------|----------|------|
| **AI-001** | except → `None` | G2510 / F `def cambrian_space` | `except` cuối hàm, trước `def show_image_SKY` · **Sai:** `get_inference_result` | **+1 dòng** `return "Fail"` | Exception → Fail path |
| **AI-002** | ROI rỗng → Pass giả | G2462 / F `def cambrian_space` | **Đầu** hàm, trước `try:` · **Sai:** trong vòng `for each_label` | **Chèn** guard empty list | `[]` labels → Fail |
| **AI-003** | Count mismatch result/label | G2468 / F `for each_label in range` | Sau guard empty, trước loop · **Sai:** caller | **Chèn** len check | Mismatch → Fail |
| **AI-004** | Caller không xử lý `None` | G4383 / F `yolo_step1=self.cambrian_space` Button_check | Sau `cambrian_space`, nhánh `if Pass` / `elif Fail` · **Sai:** SKY STEP 6 gate | **Thêm** `else: stepN=False` | None legacy → Fail |
| **AI-005** | Button_check thiếu ximian ROI | G4097 / F `point/Button_check_model.json` | Trong `show_image_Button_check` STEP 1, sau load `ok1`, trước SFIS · **Sai:** `cambrian_space` | **Chèn** ximian precheck | JSON không ximian → Fail sớm |

**Ship:** AI-001 → AI-002 → AI-003 → AI-005 → AI-004 (caller từng pipeline)

---

## Context — bug hiện tại

### AI-001: except im lặng G2510–2512

```python
        except Exception as e:
            logging.error(str(e))
            self.myuihand.textbox.emit(str(e))
            # implicit None → caller stepN không set rõ
```

### AI-002: empty list pass G2502

```python
            if False not in AOI_inference_step:   # [] → True in Python!
                ...
                return "Pass"
```

Button_check: không shape `ximian` → `step1_check` rỗng → **pass giả** + SFIS upload.

---

## Diff patches

### AI-001 · except → `return "Fail"` G2510

**Đúng chỗ:** cuối `cambrian_space` · **Sai:** `show_image_SKY` except

```python
# TRƯỚC
        except Exception as e:
            logging.error(str(e))
            self.myuihand.textbox.emit(str(e))

    def show_image_SKY(self, image_numpy,stepname):

# SAU
        except Exception as e:
            logging.error(str(e))
            self.myuihand.textbox.emit(str(e))
            return "Fail"

    def show_image_SKY(self, image_numpy,stepname):
```

Rollback: xóa `return "Fail"`.

---

### AI-002 + AI-003 · guards đầu `cambrian_space` G2462

**Đúng chỗ:** ngay sau `def cambrian_space(...)`, **trước** `try:` · **Sai:** trong từng pipeline

```python
# TRƯỚC
    def cambrian_space(self,cambrian_result_list,cambrian_img,cambrian_label_list):
        try:
            AOI_inference_step=[]
            cambrian_img = cv2.cvtColor(cambrian_img, cv2.COLOR_GRAY2RGB)

            for each_label in range(len(cambrian_label_list)):

# SAU
    def cambrian_space(self,cambrian_result_list,cambrian_img,cambrian_label_list):
        if not cambrian_label_list:
            logging.error("cambrian_space: empty label list")
            self.myuihand.textbox.emit("cambrian_space: empty label list")
            return "Fail"
        if len(cambrian_result_list) != len(cambrian_label_list):
            logging.error("cambrian_space: result/label count mismatch")
            self.myuihand.textbox.emit("cambrian_space: result/label count mismatch")
            return "Fail"
        try:
            AOI_inference_step=[]
            cambrian_img = cv2.cvtColor(cambrian_img, cv2.COLOR_GRAY2RGB)

            for each_label in range(len(cambrian_label_list)):
```

Rollback: xóa 2 guard blocks.

---

### AI-004 · caller Button_check G4383 (mẫu — lặp SKY/Cisco/WP)

**Đúng chỗ:** sau `yolo_step1 = self.cambrian_space(...)`, nhánh SFIS on · **Sai:** chỉ sửa `cambrian_space` without caller

```python
# TRƯỚC
                            yolo_step1=self.cambrian_space(inference_result,image_numpy,step1_check_draw)
                            if yolo_step1 == "Pass":
                                ...
                                self.step1 = True
                            elif yolo_step1 == "Fail":
                                ...
                                self.step1 = False

# SAU
                            yolo_step1=self.cambrian_space(inference_result,image_numpy,step1_check_draw)
                            if yolo_step1 == "Pass":
                                ...
                                self.step1 = True
                            else:  # "Fail", None (legacy), or any other
                                ...
                                self.step1 = False
```

Sites tương tự: mọi `if yolo_stepN == "Pass"` / `elif ... == "Fail"` trong `show_image_SKY`, Cisco, WP, Nanook.

---

### AI-005 · ximian precheck Button_check G4097

**Đúng chỗ:** sau loop build `step1_check`, trước `if self.sfis_choose` · **Sai:** trong `cambrian_space`

```python
# TRƯỚC
                for shape in ok1["shapes"]:
                    ...
                    if "ximian" in label:
                        ...
                        step1_check.append(cut_img_step1)

                self.lineEdit_8.setText(self.scaninfo)
                if self.sfis_choose ==  True:

# SAU
                for shape in ok1["shapes"]:
                    ...
                    if "ximian" in label:
                        ...
                        step1_check.append(cut_img_step1)

                if not step1_check:
                    logging.error("Button_check: no ximian ROIs in point JSON")
                    self.myuihand.textbox.emit("Button_check: no ximian ROIs configured")
                    self.step1 = False
                    return

                self.lineEdit_8.setText(self.scaninfo)
                if self.sfis_choose ==  True:
```

Rollback: xóa `if not step1_check` block.

---

## Luồng trước / sau

```text
TRƯỚC: exception → None → stepN unset → fail handler mơ hồ
SAU:   exception → "Fail" → stepN=False → UI/SFIS path rõ

TRƯỚC: step1_check=[] → cambrian_space → "Pass" → SFIS pass giả
SAU:   step1_check=[] → return sớm (AI-005) hoặc cambrian_space "Fail" (AI-002)
```

---

## Verification

| Test ID | Fix ID | Setup | Action | Expected result |
|---------|--------|-------|--------|-----------------|
| T-AI-001 | AI-001 | Ép exception trong try (ROI crop invalid) | Chạy step Cambrian | Trả `"Fail"`; không None; stepN=False |
| T-AI-002 | AI-002 | `cambrian_label_list=[]` | Gọi `cambrian_space` | Trả `"Fail"` — không pass giả |
| T-AI-003 | AI-003 | len(result) ≠ len(label) | Gọi hàm | Trả `"Fail"` + log mismatch |
| T-AI-004 | AI-004 | Caller Button_check nhận giá trị ngoài Pass/Fail | Chạy STEP 1 | `else` → step1=False; không unset |
| T-AI-005 | AI-005 | Button_check point JSON không nhãn ximian | STEP 1 | Fail sớm trước inference; không SFIS pass |

Chi tiết matrix F-01…F-06 bên dưới.

## Test matrix

| # | Scenario | Kỳ vọng |
|---|----------|---------|
| F-01 | Cambrian Pass bình thường | `"Pass"`; không đổi |
| F-02 | Cambrian Fail (ROI NG) | `"Fail"`; stepN False |
| F-03 | Ép exception trong try | `"Fail"`; không None |
| F-04 | `cambrian_label_list` rỗng | `"Fail"` |
| F-05 | len(result) ≠ len(label) | `"Fail"` |
| F-06 | Button_check JSON không ximian | Fail trước inference (AI-005) |

---

## Rollback

| Fix ID | Rollback | Behavior cũ quay lại | Rủi ro nếu rollback |
|--------|----------|----------------------|---------------------|
| AI-001 | Xóa `return "Fail"` | except → None | Stall/ambiguous caller |
| AI-002/003 | Xóa 2 guard block đầu hàm | `[]` → pass giả | **False pass + SFIS upload sai** — không khuyến nghị |
| AI-004 | Khôi phục `elif == "Fail"` từng caller | None không set stepN | Ảnh hưởng mọi caller đã đổi (SKY/Cisco/WP/Button_check) |
| AI-005 | Xóa block `if not step1_check` | Empty ximian pass giả | MES pass sai Button_check |

## Implementation Window

| Fix ID | Suggested window | Reason |
|--------|------------------|--------|
| AI-001 | Week 1 | 1 dòng — trùng RT stall fix P0 |
| AI-002/003 | Week 1–2 | Guard chặn false pass; test F-04/F-05 trên clone |
| AI-005 | Week 2 | Precheck Button_check; cần point JSON test case |
| AI-004 | Week 2–3 | Nhiều caller — chia PR theo pipeline |

## Smoke (5 phút)

- [ ] F-01 SKY STEP 1 Pass baseline
- [ ] F-03 mock exception (crop ROI invalid) → Fail UI, không treo
- [ ] F-06 Button_check point JSON thiếu ximian → Fail sớm

## Per-Fix Detail

### AI-001 — `cambrian_space` except → `return "Fail"`

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G2510 / `def cambrian_space` except cuối |
| Lines | L2510–2512 |
| Legacy alias | **AI-FAIL-001**; trùng `01_wait_test_stall_fix.md` AI-001 |

#### Current Problem

`except` cuối `cambrian_space` chỉ log — implicit `None` return. Caller chỉ check Pass/Fail → stepN unset → stall hoặc ambiguous state.

#### Before Improvement

```python
        except Exception as e:
            logging.error(str(e))
            self.myuihand.textbox.emit(str(e))
            # implicit None
```

#### Required Change

Thêm `return "Fail"` sau log trong except block.

#### After Improvement

Exception → `"Fail"` rõ; caller vào fail path; không None.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Giảm stall từ None return |
| MES/SFIS integrity | Tránh ambiguous state mid-upload |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-AI-001 | Ép exception trong try (ROI crop invalid) | Chạy step Cambrian | Trả `"Fail"`; không None; stepN=False |
| F-03 | Mock exception trong try | Cambrian step | `"Fail"`; không None |

#### Rollback

Xóa `return "Fail"`. **Rủi ro:** stall/ambiguous caller quay lại.

#### Suggested Implementation Window

Week 1 (P0) — 1 dòng; trùng RT stall fix.

---

### AI-002 — Empty ROI list guard

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G2462 / đầu `def cambrian_space` |
| Lines | Trước `try:`, trước vòng `for each_label` |
| Legacy alias | **AI-FAIL-003** |

#### Current Problem

`if False not in AOI_inference_step` với `[]` → True trong Python → **pass giả** (G2502). Button_check thiếu ximian ROI → SFIS pass sai.

#### Before Improvement

Empty `cambrian_label_list` hoặc `AOI_inference_step=[]` có thể return `"Pass"`.

#### Required Change

Đầu hàm: `if not cambrian_label_list:` → log + `return "Fail"`.

#### After Improvement

`[]` labels → Fail rõ; không pass giả.

#### Improvement Value

| Area | Value |
|------|-------|
| MES/SFIS integrity | Tránh SFIS pass upload khi ROI rỗng |
| Production stability | Giảm false pass |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-AI-002 | `cambrian_label_list=[]` | Gọi `cambrian_space` | Trả `"Fail"` — không pass giả |
| F-04 | Empty label list | Call | `"Fail"` |

#### Rollback

Xóa guard block. **Rủi ro:** **false pass + SFIS upload sai** — không khuyến nghị.

#### Suggested Implementation Window

Week 1–2 — guard chặn false pass.

---

### AI-003 — Result/label count mismatch guard

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G2468 / sau guard empty, trước loop |
| Lines | Đầu `cambrian_space`, sau AI-002 guard |
| Legacy alias | — |

#### Current Problem

`len(cambrian_result_list) != len(cambrian_label_list)` không check — logic loop có thể sai hoặc pass/fail không đáng tin.

#### Before Improvement

Mismatch im lặng — có thể crash hoặc kết quả sai trong loop.

#### Required Change

Chèn: `if len(cambrian_result_list) != len(cambrian_label_list):` → log mismatch + `return "Fail"`.

#### After Improvement

Count mismatch → Fail + log rõ.

#### Improvement Value

| Area | Value |
|------|-------|
| Debugging | Log mismatch dễ trace AI lỗi |
| Production stability | Contract Pass/Fail only |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-AI-003 | len(result) ≠ len(label) | Gọi hàm | Trả `"Fail"` + log mismatch |
| F-05 | Mismatch counts | Call | `"Fail"` |

#### Rollback

Xóa len check guard. **Rủi ro:** cùng AI-002 — false pass risk.

#### Suggested Implementation Window

Week 1–2 — cùng PR AI-002.

---

### AI-004 — Caller `else` branch for non-Pass

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G4383 / `yolo_step1=self.cambrian_space` Button_check |
| Lines | Sau `cambrian_space`, nhánh Pass/Fail |
| Legacy alias | — |

#### Current Problem

Caller chỉ `if Pass` / `elif Fail` — legacy `None` hoặc giá trị khác không set `stepN=False`.

#### Before Improvement

```python
                            if yolo_step1 == "Pass":
                                self.step1 = True
                            elif yolo_step1 == "Fail":
                                self.step1 = False
```

#### Required Change

Đổi `elif Fail` → `else:` (Fail, None legacy, any other) → `stepN=False`. Lặp SKY/Cisco/WP/Nanook callers.

#### After Improvement

Mọi non-Pass → stepN=False rõ; không unset state.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Giảm stall từ unset stepN |
| Maintainability | Defensive caller pattern |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-AI-004 | Caller nhận giá trị ngoài Pass/Fail | Chạy STEP 1 | `else` → step1=False |
| F-02 | Cambrian Fail ROI NG | Step | stepN False |

#### Rollback

Khôi phục `elif == "Fail"` từng caller. **Rủi ro:** ảnh hưởng mọi pipeline đã đổi.

#### Suggested Implementation Window

Week 2–3 — nhiều caller; chia PR theo pipeline.

---

### AI-005 — Button_check ximian ROI precheck

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G4097 / `show_image_Button_check` STEP 1 |
| Lines | Sau loop build `step1_check`, trước `if self.sfis_choose` |
| Legacy alias | **AI-006 Nanook** (pattern tương tự); PIPE-B05 |

#### Current Problem

Point JSON không nhãn `ximian` → `step1_check=[]` → pass giả + SFIS upload (trước AI-002 guard).

#### Before Improvement

Loop shapes không append → empty list → Cambrian pass giả.

#### Required Change

`if not step1_check:` → log + `step1=False` + `return` trước inference/SFIS.

#### After Improvement

Fail sớm trước inference; không SFIS pass; operator thấy message config.

#### Improvement Value

| Area | Value |
|------|-------|
| MES/SFIS integrity | Tránh pass upload khi JSON sai |
| Operator experience | Fail message "no ximian ROIs" |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-AI-005 | Button_check point JSON không ximian | STEP 1 | Fail sớm; không SFIS pass |
| F-06 | JSON không ximian | STEP 1 | Fail trước inference |
| B-08 | PIPE-B05 | STEP 1 | Fail sớm |

#### Rollback

Xóa `if not step1_check` block. **Rủi ro:** MES pass sai Button_check.

#### Suggested Implementation Window

Week 2 — cần point JSON test case.

---

## Ref

`01_cambrian_guard_policy.md` · `01_runtime_stability/01_wait_test_stall_fix.md` AI-001 · `19_button_check_pipeline.md`
