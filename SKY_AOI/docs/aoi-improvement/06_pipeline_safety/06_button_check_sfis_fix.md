# Button_check SFIS & Scan — Compact Playbook

**File:** `sky.py` · **Workstream:** `06_pipeline_safety`  
**Nguồn:** `19_button_check_pipeline.md`, `10_risks_and_bugs.md` Phase 10, `05_ai_ocr_runtime/03_cambrian_space_fail_policy.md`  
**Luật:** Mọi upload Button_check (pass **và** fail) dùng `scaninfo`; reject Flip → `wait_test=True`; reset `check_result_OK` mỗi chu kỳ.

> Repo: fail upload G1308 `thissn`; pass G4180/4234 `scaninfo`; Flip dialog G1272; reject G1317. **go_run1 scan corrupted G725** — fix syntax trước test. **Ctrl+F** `Button_check`.

---

## Improvement Purpose

Mục tiêu của cải tiến này là Button_check pipeline đảm bảo MES SN đúng (`scaninfo` pass **và** fail), reject Flip không stall, reset state mỗi chu kỳ, validate scan rỗng — tránh upload SN stale và pass giả Cambrian.

## Before Improvement

Trước cải tiến: fail upload dùng `thissn` (SN DUT/model trước) trong khi pass dùng `scaninfo` (G1308 vs G4180); reject Flip dialog không `wait_test=True` (G1317) → stall; `check_result_OK` stale sau SKY route; empty scan accepted; empty ximian ROI → pass giả + SFIS. MES audit fail không khớp scan; operator kẹt sau Flip reject.

## After Improvement

Sau cải tiến: fail/pass upload đều `scaninfo`; Flip reject set `wait_test=True` (RT-003); reset `check_result_OK` đầu chu kỳ; validate scan non-empty; ximian precheck (AI-005). MES SN = scan operator vừa nhập; cycle tiếp sau reject Flip; không pass giả empty ROI.

## Improvement Value

| Area                        | Value |
| --------------------------- | ----- |
| Production stability        | Giảm stall Flip reject; giảm false pass empty ROI |
| Operator experience         | Re-prompt scan rỗng; DUT tiếp sau reject Flip |
| MES/SFIS integrity          | Fail/pass MES cùng SN scaninfo — truy vết chính xác |
| Maintainability             | Align fail SN với pass path |
| Debugging / troubleshooting | Dễ đối chiếu MES vs scan dialog |

## Before / After Summary

| Aspect           | Before | After |
| ---------------- | ------ | ----- |
| Runtime behavior | Fail MES ≠ scan; Flip reject stall | scaninfo both paths; wait_test on reject |
| Error handling   | Empty scan OK; stale check_result_OK | Validate scan; reset flags |
| Operator impact  | MES sai SN; kẹt sau Flip | SN đúng; cycle continues |
| Production risk  | P0 MES integrity + stall | Giảm rủi ro audit Button_check |

---

## Bảng tổng

| ID | Vấn đề | Đi tới | Anchor (đúng chỗ khi thấy…) | Thao tác | Test |
|----|--------|--------|-----------------------------|----------|------|
| **PIPE-B01** | Fail upload SN sai | G1308 / F `data_upload(self.thissn` Button_check fail | Trong `elif self.step1==False` go_run3 · **Sai:** pass G4234 `scaninfo` | **Đổi** `thissn` → `scaninfo` | B-02 MES = scaninfo |
| **PIPE-B02** | Reject Flip stall | G1317 / F `elif mychoose == 65536` sau Flip | Trước `QMessageBox.question` exit · **Sai:** SFIS block | **+1 dòng** `wait_test=True` — **RT-003** | B-05 cycle tiếp |
| **PIPE-B03** | `check_result_OK` stale | G1267 / F `elif self.select_model == "Button_check"` | Đầu nhánh, trước Flip dialog · **Sai:** vision only | **Chèn** `check_result_OK=False` | B-07 no Cambrian after SKY |
| **PIPE-B04** | Empty scan accepted | G693 / F `go_run1` Button_check | Trong scan loop — **repo G725 corrupt** · **Sai:** go_run3 | **Validate** `strip()` non-empty | B-04 re-prompt |
| **PIPE-B05** | Empty ximian pass giả | G4097 / F `point/Button_check_model.json` | `show_image_Button_check` STEP1 — **AI-005** | Xem `05_ai_ocr_runtime/03` | B-08 Fail |
| **PIPE-B06** | Sensor + wrong vision | — | `03_sensor_dispatch` SENSOR-002 | Sensor guard | B-10 blocked |

**Ship:** PIPE-B01 (P0 MES) → PIPE-B02 → PIPE-B03 → PIPE-B04 → PIPE-B05/B06

---

## Diff patches

### PIPE-B01 · fail upload SN G1305–1311

**Đúng chỗ:** `elif self.select_model == "Button_check"`, block `elif self.step1==False` · **Sai:** pass path `scaninfo` G4234 (đã đúng)

```python
# TRƯỚC
                    try:
                        if self.sfis_choose == True:
                            self.mysfis.data_upload(self.thissn, self.data,
                                                    error="BDFA01")
                            logging.error("fail upload OK")
                            self.myuihand.textbox.emit("fail upload OK")

# SAU
                    try:
                        if self.sfis_choose == True:
                            self.mysfis.data_upload(self.scaninfo, self.data,
                                                    error="BDFA01")
                            logging.error("fail upload OK")
                            self.myuihand.textbox.emit("fail upload OK")
```

Rollback: **không khuyến nghị** — khôi phục SN MES sai.

---

### PIPE-B02 · Flip reject wait_test G1317 (RT-003)

```python
# TRƯỚC
            elif mychoose == 65536:
                mychoose = QMessageBox.question(self, "Warning", "Yes for exit")

# SAU
            elif mychoose == 65536:
                self.wait_test = True
                mychoose = QMessageBox.question(self, "Warning", "Yes for exit")
```

**Đúng chỗ:** reject Flip **trước** chụp — nhánh `elif mychoose == 65536` sau dialog "Please Flip the model" G1272.

---

### PIPE-B03 · reset flags G1267

```python
# TRƯỚC
        elif self.select_model == "Button_check" :
            self.step1 = False

# SAU
        elif self.select_model == "Button_check" :
            self.step1 = False
            self.check_result_OK = False
```

---

### PIPE-B04 · validate scan `go_run1` (sau sửa syntax G725)

**Pre-check:** `go_run1` Button_check G693–726 hiện **syntax error** (`input_dialof.shan)`) — khôi phục loop scan trước patch.

```python
# SAU — trong loop sau input_dialog.exec_() == Accepted
                text = input_dialog.textValue().strip()
                if not text:
                    QMessageBox.warning(self, "Scan", "Label SN cannot be empty")
                    continue
                self.scaninfo = text
                self.lineEdit_8.setText(self.scaninfo)
                self.scan_sta = True
                break
```

---

## Evidence pass vs fail SN

| Path | G | SN dùng |
|------|---|---------|
| Pass vision | G4180, G4234 | `scaninfo` ✓ |
| Fail go_run3 | G1308 | `thissn` ✗ → **PIPE-B01** |

---

## Verification

| Test ID | Fix ID | Setup | Action | Expected result |
|---------|--------|-------|--------|-----------------|
| T-B01 | PIPE-B01 | Chạy SKY trước (set `thissn`), Button_check scan mới, fail | Fail cycle | MES fail SN = `scaninfo` hiện tại, không phải SN SKY |
| T-B02 | PIPE-B02 | Tới dialog Flip | Reject (65536), reject exit | `wait_test=True`; DUT tiếp không cần Stop |
| T-B03 | PIPE-B03 | SKY route pass rồi Button_check route fail | Button_check cycle | Không Cambrian với `check_result_OK` stale |
| T-B04 | PIPE-B04 | Scan dialog (sau sửa syntax G725) | OK chuỗi rỗng | Warning; re-prompt; không route |
| T-B05 | PIPE-B05 | Point JSON không ximian | STEP 1 | Fail sớm — xem AI-005 |
| T-B06 | PIPE-B06 | `is_sensor=true` + Button_check | Start | Blocked — SENSOR-002 |

Chi tiết matrix B-01…B-10 bên dưới.

## Test matrix

| # | Scenario | Kỳ vọng |
|---|----------|---------|
| B-01 | Pass sau scan | MES pass = scaninfo |
| B-02 | Fail sau scan | MES fail = **scaninfo** |
| B-03 | Fail sau SKY test trước | MES = scaninfo hiện tại |
| B-05 | Reject Flip, reject exit | wait_test True |
| B-07 | Route fail after SKY OK flag | No Cambrian |
| B-10 | is_sensor=true | SENSOR guard block |

## Rollback

| Fix ID | Rollback | Behavior cũ quay lại | Rủi ro nếu rollback |
|--------|----------|----------------------|---------------------|
| PIPE-B01 | L1308 đổi lại `thissn` | Fail MES SN stale | **Không khuyến nghị** — MES sai quay lại |
| PIPE-B02 | Xóa `wait_test=True` | Reject Flip stall | Operator kẹt |
| PIPE-B03 | Xóa dòng reset | Stale `check_result_OK` | False Cambrian run |
| PIPE-B04 | Xóa validate block | Empty scan accepted | Route/upload SN rỗng |
| PIPE-B05/B06 | Theo AI-005 / SENSOR-002 owner doc | — | — |

## Implementation Window

| Fix ID | Suggested window | Reason |
|--------|------------------|--------|
| PIPE-B01 | Week 1 | P0 MES wrong SN — 1 từ; verify MES trên clone |
| PIPE-B02 | Week 1 | 1 dòng; P0 stall (RT-003) |
| PIPE-B03 | Week 1–2 | 1 dòng reset |
| PIPE-B04 | Week 2 | Phải sửa syntax corrupt G725 trước |
| PIPE-B05/B06 | Theo owner doc | AI-005 Week 2; SENSOR-002 Week 1 |

## Smoke

- [ ] B-02 fail cycle — verify MES SN = scanned label
- [ ] B-05 reject Flip — Start next DUT without Stop

## Per-Fix Detail

### PIPE-B01 — Button_check fail upload SN = `scaninfo`

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G1308 / `data_upload(self.thissn` Button_check fail |
| Lines | `elif self.step1==False` go_run3, trong try block |
| Legacy alias | B-02, B-03 (test matrix); **SFIS fail path** |

#### Current Problem

Fail upload dùng `thissn` (SN DUT/model trước); pass path dùng `scaninfo` (G4180/G4234) — MES audit fail không khớp scan operator.

#### Before Improvement

| Path | SN |
|------|-----|
| Pass G4180/G4234 | `scaninfo` ✓ |
| Fail G1308 | `thissn` ✗ |

#### Required Change

Đổi `self.thissn` → `self.scaninfo` trong fail upload block G1305–1311.

#### After Improvement

Fail/pass MES cùng SN = scan operator vừa nhập.

#### Improvement Value

| Area | Value |
|------|-------|
| MES/SFIS integrity | **P0** — truy vết MES chính xác |
| Debugging | Đối chiếu MES vs scan dialog |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-B01 | Chạy SKY trước, Button_check scan mới, fail | Fail cycle | MES fail SN = `scaninfo`, không SN SKY |
| B-02 | Fail sau scan | Cycle | MES fail = scaninfo |
| B-03 | Fail sau SKY test | Cycle | MES = scaninfo hiện tại |

#### Rollback

L1308 đổi lại `thissn`. **Rủi ro:** **không khuyến nghị** — MES sai quay lại.

#### Suggested Implementation Window

Week 1 (P0) — 1 từ; verify MES trên clone.

---

### PIPE-B02 — Flip reject `wait_test=True`

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G1317 / `elif mychoose == 65536` sau Flip |
| Lines | Trước `QMessageBox.question` exit |
| Legacy alias | **RT-003**; B-05 (test matrix) |

#### Current Problem

Reject Flip dialog (65536) không set `wait_test=True` → line stall; operator phải Stop.

#### Before Improvement

```python
            elif mychoose == 65536:
                mychoose = QMessageBox.question(self, "Warning", "Yes for exit")
```

#### Required Change

Thêm `self.wait_test = True` trước exit dialog.

#### After Improvement

Reject Flip → cycle tiếp; Start DUT tiếp không Stop.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | P0 stall fix Button_check |
| Operator experience | DUT tiếp sau reject Flip |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-B02 | Tới dialog Flip | Reject (65536), reject exit | `wait_test=True`; DUT tiếp |
| B-05 | Reject Flip, reject exit | Flow | wait_test True |

#### Rollback

Xóa `wait_test=True`. **Rủi ro:** operator kẹt.

#### Suggested Implementation Window

Week 1 (P0) — 1 dòng.

---

### PIPE-B03 — Reset `check_result_OK` mỗi chu kỳ

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G1267 / `elif self.select_model == "Button_check"` |
| Lines | Đầu nhánh, trước Flip dialog |
| Legacy alias | B-07 (test matrix) |

#### Current Problem

`check_result_OK` stale sau SKY route pass → Button_check route fail vẫn chạy Cambrian.

#### Before Improvement

```python
        elif self.select_model == "Button_check" :
            self.step1 = False
```

#### Required Change

Chèn `self.check_result_OK = False` đầu nhánh.

#### After Improvement

Mỗi chu kỳ Button_check reset flags; route fail không Cambrian với stale state.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Tránh false Cambrian run |
| MES/SFIS integrity | Không pass giả sau SKY OK flag |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-B03 | SKY route pass rồi Button_check route fail | Button_check cycle | Không Cambrian stale |
| B-07 | Route fail after SKY OK | Cycle | No Cambrian |

#### Rollback

Xóa dòng reset. **Rủi ro:** stale `check_result_OK`.

#### Suggested Implementation Window

Week 1–2 — 1 dòng reset.

---

### PIPE-B04 — Empty scan validation `go_run1`

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G693 / `go_run1` Button_check scan loop |
| Lines | Sau `input_dialog.exec_() == Accepted` |
| Legacy alias | B-04; **G725 syntax corrupt** pre-req |

#### Current Problem

Empty scan accepted; `go_run1` G725 có syntax error (`input_dialof.shan)`) — loop scan broken.

#### Before Improvement

Scan OK với chuỗi rỗng → route/upload SN rỗng.

#### Required Change

**Pre:** sửa syntax G725. **Patch:** `text.strip()` non-empty validate; warning + `continue` re-prompt.

#### After Improvement

Empty scan → warning; re-prompt; không route.

#### Improvement Value

| Area | Value |
|------|-------|
| MES/SFIS integrity | Không upload SN rỗng |
| Operator experience | Re-prompt scan rõ |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-B04 | Scan dialog (sau sửa G725) | OK chuỗi rỗng | Warning; re-prompt |

#### Rollback

Xóa validate block. **Rủi ro:** empty scan accepted.

#### Suggested Implementation Window

Week 2 — phải sửa syntax G725 trước.

---

### PIPE-B05 — Empty ximian ROI precheck

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G4097 / `point/Button_check_model.json` |
| Lines | `show_image_Button_check` STEP1 |
| Legacy alias | **AI-005**; B-08 (test matrix) |

#### Current Problem

Point JSON không ximian → empty ROI → pass giả + SFIS (owner: `05_ai_ocr_runtime/03`).

#### Before Improvement

Empty `step1_check` → Cambrian pass giả.

#### Required Change

Xem `03_cambrian_space_fail_policy.md` AI-005: `if not step1_check:` fail sớm.

#### After Improvement

Fail trước inference; không SFIS pass giả.

#### Improvement Value

| Area | Value |
|------|-------|
| MES/SFIS integrity | Tránh pass upload empty ROI |
| Production stability | Fail sớm có cấu trúc |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-B05 | Point JSON không ximian | STEP 1 | Fail sớm — AI-005 |
| B-08 | No ximian JSON | STEP 1 | Fail |

#### Rollback

Theo AI-005 owner doc.

#### Suggested Implementation Window

Week 2 — theo AI-005 owner doc.

---

### PIPE-B06 — Sensor mode guard (cross-workstream)

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | `03_sensor_dispatch` SENSOR-002 |
| Lines | `startprogram` sensor guard |
| Legacy alias | B-10 (test matrix) |

#### Current Problem

`is_sensor=true` + Button_check vision path → wrong handler / unsafe combo.

#### Before Improvement

Không block Start khi sensor + Button_check mismatch.

#### Required Change

SENSOR-002 guard trong `03_sensor_dispatch/01_sensor_mode_guard.md` — block Start với message.

#### After Improvement

`is_sensor=true` + Button_check → Blocked Start.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Tránh wrong vision path |
| Operator experience | Block message rõ |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-B06 | `is_sensor=true` + Button_check | Start | Blocked — SENSOR-002 |
| B-10 | Sensor + Button_check | Start | SENSOR guard block |

#### Rollback

Theo SENSOR-002 owner doc.

#### Suggested Implementation Window

Week 1 — SENSOR-002 owner doc.

---

## Ref

`19_button_check_pipeline.md` · `01_runtime_stability/01_wait_test_stall_fix.md` RT-003 · `03_sensor_dispatch/01_sensor_mode_guard.md` · `05_ai_ocr_runtime/03_cambrian_space_fail_policy.md` AI-005
