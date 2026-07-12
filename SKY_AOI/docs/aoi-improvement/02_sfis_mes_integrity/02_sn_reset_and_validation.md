# SN Reset & Validation — Compact Playbook

**File:** `sky.py` · **Workstream:** `02_sfis_mes_integrity`  
**Nguồn:** `10_risks_and_bugs.md`, pipelines `16`–`19`  
**Luật:** Fail/pass upload cùng biến SN của DUT hiện tại; SN rỗng/`"None"` → không upload MES.

> Line grep từ `sky.py` repo hiện tại (2026-07-12). **Ctrl+G** tới dòng → **Ctrl+F** xác nhận anchor trước khi sửa.

---

## Improvement Purpose

Mục tiêu của cải tiến này là đảm bảo dữ liệu SFIS/MES gắn đúng SN của DUT hiện tại — không dùng SN cũ, literal `"None"`, hoặc scan rỗng. Đây là nhóm cải tiến data integrity: lỗi có thể ảnh hưởng truy vết sản phẩm trên MES, không chỉ là lỗi code nội bộ.

## Before Improvement

Trước cải tiến: Button_check fail upload dùng `thissn` (stale từ DUT trước) trong khi pass dùng `scaninfo` (L1308 vs L4180); Cisco `SN_8P` không reset đầu chu kỳ — fail sớm upload PVN DUT trước; WP/Nanook reset `thissn="None"` → MES nhận chữ `"None"`; SKY không reset `thissn` giữa DUT; `go_run1` chấp nhận scan rỗng. Truy vết MES sai SN, audit fail không khớp sản phẩm thực.

## After Improvement

Sau cải tiến: mọi upload fail/pass dùng cùng biến SN đúng pipeline (`scaninfo` Button_check, reset `SN_8P`/`thissn` đầu chu kỳ); SN rỗng/`"None"` → skip upload hoặc re-prompt; scan rỗng bị reject với warning. MES record khớp DUT trên line; engineer audit SN chính xác.

## Improvement Value

| Area                        | Value |
| --------------------------- | ----- |
| Production stability        | Giảm rework do MES SN sai; tránh hold lot vì trace mismatch |
| Operator experience         | Scan rỗng được nhắc lại thay vì chạy fail im lặng |
| MES/SFIS integrity          | Đảm bảo dữ liệu MES đúng SN, đúng pass/fail — giảm rủi ro sai truy vết |
| Maintainability             | Reset SN pattern thống nhất đầu mỗi model branch |
| Debugging / troubleshooting | Dễ đối chiếu MES vs scan thực tế trên line |

## Before / After Summary

| Aspect           | Before | After |
| ---------------- | ------ | ----- |
| Runtime behavior | Fail upload có thể dùng SN DUT trước hoặc `"None"` | Reset SN đầu chu kỳ; validate trước upload |
| Error handling   | Empty scan accepted; stale SN im lặng | Re-prompt scan rỗng; skip upload SN invalid |
| Operator impact  | MES sai SN — khó giải thích với QA | Scan/SN rõ; fail MES khớp sản phẩm |
| Production risk  | Rủi ro traceability, recall khó | Truy vết chính xác; giảm rủi ro audit MES |

---

## Per-Fix Detail

## Fix SN-001 — Button_check fail dùng `scaninfo`

### Code Location

| Field | Detail |
|---|---|
| File | sky.py |
| Function / Block | `go_run3` → `Button_check` → `elif self.step1==False` |
| Current lines | **L1308** (`data_upload(self.thissn, ...)`) |
| Suggested patch location | L1308 — đổi `thissn` → `scaninfo` (1 từ) |

### Current Problem

Button_check fail upload dùng `thissn` (stale từ DUT trước) trong khi pass dùng `scaninfo` (L4180) — MES fail record gắn SN sai sản phẩm.

### Before Improvement

Fail path L1308: `self.mysfis.data_upload(self.thissn, self.data, error="BDFA01")`. Pass path L4180/L4234: `scaninfo` ✓.

### Required Change

Đổi L1308: `self.mysfis.data_upload(self.scaninfo, self.data, ...)`. Giữ try block L1305 nguyên.

### After Improvement

Fail và pass Button_check cùng biến `scaninfo` — MES record khớp scan operator vừa nhập.

### Improvement Value

| Area | Value |
| --- | --- |
| Production stability | Giảm rework/hold lot do MES SN mismatch |
| Operator experience | Fail MES khớp label vừa scan |
| MES/SFIS integrity | **P0** — đảm bảo fail record đúng DUT hiện tại |
| Maintainability | Đồng bộ SN variable fail/pass |
| Debugging / troubleshooting | Đối chiếu MES vs scan dialog dễ hơn |

### Verification

| Test ID | Setup | Action | Expected result |
| --- | --- | --- | --- |
| T-SN-001 | Chạy SKY (set `thissn`) rồi Button_check scan mới | Fail Button_check | MES fail SN = `scaninfo` vừa scan, không phải SN SKY |

### Rollback

L1308 đổi lại `thissn`. **Không khuyến nghị** — MES SN sai quay lại.

### Suggested Implementation Window

| Window | Reason |
| --- | --- |
| Week 1–2 | Đổi 1 từ nhưng cần MES verify 10 fail record trên clone |

---

## Fix SN-002 — Reset `SN_8P` đầu chu kỳ Cisco

### Code Location

| Field | Detail |
|---|---|
| File | sky.py |
| Function / Block | `go_run3` → nhánh Cisco (12 model) entry |
| Current lines | **Chèn L1160** (sau L1159 `elif ... C1000-8FP-E-2G-L`, trước L1160 `step1=False`) |
| Suggested patch location | Ngay sau dòng `elif self.select_model == "C1000-8FP-E-2G-L" or ...` — thêm `self.SN_8P = ""` |

### Current Problem

Cisco `SN_8P` không reset đầu chu kỳ — fail sớm (trước vision set SN L3802/L3922) upload PVN DUT trước lên MES.

### Before Improvement

Nhánh Cisco vào thẳng `self.step1 = False` không clear `SN_8P`.

### Required Change

Chèn 1 dòng `self.SN_8P = ""` giữa elif Cisco và `self.step1 = False`.

### After Improvement

Mỗi DUT Cisco bắt đầu với SN rỗng; fail sớm không upload stale PVN; SN rỗng → skip upload (kết hợp SFIS helper).

### Improvement Value

| Area | Value |
| --- | --- |
| Production stability | Giảm MES record orphan/stale trên Cisco |
| Operator experience | N/A |
| MES/SFIS integrity | **P0** — chặn PVN DUT trước lên MES |
| Maintainability | Pattern reset SN đầu model branch |
| Debugging / troubleshooting | Trace Cisco SN từ đầu chu kỳ rõ ràng |

### Verification

| Test ID | Setup | Action | Expected result |
| --- | --- | --- | --- |
| T-SN-002 | Cisco DUT đầu ca fail STEP 1 trước khi set `SN_8P` | Fail cycle | Không upload PVN DUT trước; SN rỗng skip |

### Rollback

Xóa dòng `self.SN_8P = ""`. PVN cũ có thể upload khi fail sớm.

### Suggested Implementation Window

| Window | Reason |
| --- | --- |
| Week 1 | 1 dòng chèn; chặn PVN stale — P0 MES wrong SN |

---

## Fix SN-003a — WP reset `thissn` (không dùng `"None"`)

### Code Location

| Field | Detail |
|---|---|
| File | sky.py |
| Function / Block | `go_run3` → `WP_check` / `C9105AXW_E` entry |
| Current lines | **L1324** (`self.thissn="None"`) |
| Suggested patch location | L1324 — thay `"None"` → `""`; thêm L1325 `check_result_OK=False` |

### Current Problem

WP branch gán `thissn="None"` — MES nhận literal chuỗi `"None"` thay vì skip upload.

### Before Improvement

`self.thissn="None"` ngay đầu WP branch; decode barcode thật ở `show_image_WP` sau.

### Required Change

```python
self.thissn = ""
self.check_result_OK = False
```

### After Improvement

SN invalid = empty string; upload skip hoặc guard; không bản ghi MES chứa `"None"`.

### Improvement Value

| Area | Value |
| --- | --- |
| Production stability | Giảm audit fail do literal None trên MES |
| Operator experience | N/A |
| MES/SFIS integrity | **P0** — chặn `"None"` lên MES |
| Maintainability | Thống nhất empty SN convention |
| Debugging / troubleshooting | MES query không còn SN="None" |

### Verification

| Test ID | Setup | Action | Expected result |
| --- | --- | --- | --- |
| T-SN-003 | WP decode fail sớm | Fail cycle | Không bản ghi MES chứa literal `"None"` |

### Rollback

Khôi phục `"None"`. MES nhận literal None quay lại.

### Suggested Implementation Window

| Window | Reason |
| --- | --- |
| Week 1 | 2 dòng/site; chặn `"None"` lên MES ngay — P0 |

---

## Fix SN-003b — Nanook reset `thissn` (không dùng `"None"`)

### Code Location

| Field | Detail |
|---|---|
| File | sky.py |
| Function / Block | `go_run3` → `Nanook` entry |
| Current lines | **L1551** (`self.thissn = "None"`) |
| Suggested patch location | L1551 — thay `"None"` → `""`; thêm `check_result_OK=False` |

### Current Problem

Nanook branch gán `thissn = "None"` — cùng rủi ro MES literal `"None"` như WP.

### Before Improvement

`self.thissn = "None"` ngay đầu Nanook branch; decode thật ở `show_image_Nanook`.

### Required Change

```python
self.thissn = ""
self.check_result_OK = False
```

### After Improvement

Empty SN đầu chu kỳ; fail sớm không pollute MES với `"None"`.

### Improvement Value

| Area | Value |
| --- | --- |
| Production stability | Giảm MES audit noise Nanook |
| Operator experience | N/A |
| MES/SFIS integrity | **P0** — chặn `"None"` lên MES |
| Maintainability | Đối xứng SN-003a WP |
| Debugging / troubleshooting | Trace Nanook SN sạch từ entry |

### Verification

| Test ID | Setup | Action | Expected result |
| --- | --- | --- | --- |
| T-SN-003 | Nanook decode fail sớm | Fail cycle | Không bản ghi MES chứa literal `"None"` |

### Rollback

Khôi phục `"None"`.

### Suggested Implementation Window

| Window | Reason |
| --- | --- |
| Week 1 | 2 dòng/site; ship cùng SN-003a |

---

## Fix SN-004 — Reject scan rỗng Button_check

### Code Location

| Field | Detail |
|---|---|
| File | sky.py |
| Function / Block | `go_run1` → `Button_check` scan dialog loop |
| Current lines | **L724–726** (sau `setTextValue`, trước `exec_`) — Line needs re-check in sky.py before patch (L725 corrupt `input_dialof.shan)`) |
| Suggested patch location | Sau `input_dialog.exec_() == Accepted` — validate `text.strip()` trước gán `scaninfo` |

### Current Problem

`go_run1` chấp nhận scan rỗng/whitespace — route test với SN invalid, upload MES rỗng hoặc im lặng fail.

### Before Improvement

`self.scaninfo = input_dialog.textValue()` không validate; repo L725 có syntax corrupt.

### Required Change

Sửa corrupt L725 trước; chèn validate: `if not text: QMessageBox.warning(...); continue`. Pattern tham chiếu ipex L779.

### After Improvement

Scan rỗng → warning "SN cannot be empty" → re-prompt; không route/upload SN rỗng.

### Improvement Value

| Area | Value |
| --- | --- |
| Production stability | Tránh chu kỳ test với SN invalid |
| Operator experience | Nhắc scan lại thay vì fail im lặng |
| MES/SFIS integrity | Không upload SN rỗng |
| Maintainability | Validate pattern tái dùng (ipex tương tự) |
| Debugging / troubleshooting | Operator error rõ trước khi vào pipeline |

### Verification

| Test ID | Setup | Action | Expected result |
| --- | --- | --- | --- |
| T-SN-004 | Button_check scan dialog | OK với chuỗi rỗng/whitespace | Warning "SN cannot be empty"; re-prompt; không route |

### Rollback

Xóa block `if not text`. Scan rỗng accepted quay lại.

### Suggested Implementation Window

| Window | Reason |
| --- | --- |
| Week 2 | Repo G725 corrupt — phải sửa syntax trước, test scan loop |

---

## Fix SN-005 — Reset `thissn` đầu chu kỳ SKY

### Code Location

| Field | Detail |
|---|---|
| File | sky.py |
| Function / Block | `go_run3` → `SKY` / `SKY_4G` entry |
| Current lines | **Chèn L902** (sau L901 `elif ... SKY`, trước L902 `step1=False`) |
| Suggested patch location | Ngay sau elif SKY/SKY_4G — thêm 2 dòng reset |

### Current Problem

SKY không reset `thissn` giữa DUT — fail/pass có thể dính SN DUT trước khi vision decode SN mới.

### Before Improvement

Nhánh SKY vào thẳng `self.step1 = False` không clear `thissn`.

### Required Change

```python
self.thissn = ""
self.check_result_OK = False
```

### After Improvement

Mỗi DUT SKY bắt đầu SN sạch; 2 DUT liên tiếp → MES SN đúng từng DUT.

### Improvement Value

| Area | Value |
| --- | --- |
| Production stability | Giảm trace mismatch SKY multi-DUT |
| Operator experience | N/A |
| MES/SFIS integrity | **P0** — SN đúng per DUT |
| Maintainability | Đối xứng SN-002 Cisco reset pattern |
| Debugging / troubleshooting | SKY SN trace từ entry branch |

### Verification

| Test ID | Setup | Action | Expected result |
| --- | --- | --- | --- |
| T-SN-005 | 2 DUT SKY liên tiếp | Pass/fail mỗi DUT | MES SN đúng từng DUT — không dính SN DUT trước |

### Rollback

Xóa 2 dòng reset. SKY dính SN DUT trước quay lại.

### Suggested Implementation Window

| Window | Reason |
| --- | --- |
| Week 1 | 2 dòng chèn — P0 MES wrong SN |

---

## Bạn phải sửa gì? — bảng dòng cụ thể

| ID | File | Hàm / block | Dòng sửa | Thao tác | Đúng chỗ (phải thấy) | Sai chỗ (đừng sửa) |
|----|------|-------------|----------|----------|----------------------|---------------------|
| **SN-001** | `sky.py` | `go_run3` → `Button_check` → `elif self.step1==False` | **L1308** | `thissn` → `scaninfo` | `data_upload(self.thissn` trong block fail Button_check | Pass upload L4180 (`scaninfo` — đã đúng) |
| **SN-002** | `sky.py` | `go_run3` → nhánh Cisco (12 model) | **Chèn L1160** (sau L1159, trước L1160 `step1=False`) | +1 dòng `self.SN_8P = ""` | `elif … C1000-8FP-E-2G-L` or … | Vision set SN L3802/L3922 |
| **SN-003a** | `sky.py` | `go_run3` → `WP_check` / `C9105AXW_E` entry | **L1324** | `"None"` → `""` + `check_result_OK=False` | `self.thissn="None"` ngay đầu WP branch | Chỗ gán barcode thật trong `show_image_WP` |
| **SN-003b** | `sky.py` | `go_run3` → `Nanook` entry | **L1551** | `"None"` → `""` + `check_result_OK=False` | `self.thissn = "None"` ngay đầu Nanook | `show_image_Nanook` decode |
| **SN-004** | `sky.py` | `go_run1` → `Button_check` | **L724–726** (sau `setTextValue`) | Reject scan rỗng | `please scan label` + `select_model=="Button_check"` | Dialog ipex L752 |
| **SN-005** | `sky.py` | `go_run3` → `SKY` / `SKY_4G` entry | **Chèn L902** (sau L901, trước L902 `step1=False`) | +2 dòng reset SN | `elif self.select_model == "SKY"` | Trong `show_image_SKY` |

**Thứ tự ship:** SN-003a/b → SN-002 → SN-005 → SN-001 → SN-004.

**So sánh pass vs fail (Button_check):**

| Loại | File | Hàm | Dòng | Biến SN |
|------|------|-----|------|---------|
| Pass | `sky.py` | `show_image_Button_check` | L4180, L4234 | `scaninfo` ✓ |
| Fail | `sky.py` | `go_run3` Button_check | **L1308** | `thissn` ✗ → đổi `scaninfo` |

---

## Bảng tổng

| ID | Vấn đề | Đi tới | Test |
|----|--------|--------|------|
| SN-001 | Fail MES = SN máy trước | **G1308** / F `data_upload(self.thissn` trong Button_check | MES = scan vừa nhập |
| SN-002 | PVN Cisco cũ khi fail sớm | **G1160** / F `C1000-8FP-E-2G-L` (elif dài `go_run3`) | Cold fail không PVN cũ |
| SN-003 | MES nhận chữ `None` | **G1324**, **G1551** / F `thissn="None"` | Không `"None"` trên MES |
| SN-004 | Scan trống vẫn chạy | **G694** / F `select_model=="Button_check"` | Re-prompt |
| SN-005 | SKY dính `thissn` DUT trước | **G902** / F `select_model == "SKY"` | 2 DUT SN đúng |

---

## Diff patches

### SN-001 · `sky.py` L1308 — đổi 1 từ

**Mở:** `sky.py` → **Ctrl+G 1308** → phải thấy `elif self.step1==False` Button_check phía trên (~L1292).

```python
# TRƯỚC — L1308
                            self.mysfis.data_upload(self.thissn, self.data,

# SAU — chỉ đổi dòng 1308
                            self.mysfis.data_upload(self.scaninfo, self.data,
```

Rollback: L1308 đổi lại `thissn`.

---

### SN-002 · `sky.py` chèn L1160

**Mở:** **Ctrl+G 1159** → dòng `elif self.select_model == "C1000-8FP-E-2G-L" or ...` (chuỗi dài 12 Cisco).

```python
# TRƯỚC — L1159–1161
        elif self.select_model == "C1000-8FP-E-2G-L" or self.select_model == "C1000-8P-2G-L" or ...:
            self.step1 = False
            self.step2 = False

# SAU — chèn 1 dòng giữa L1159 và L1160
        elif self.select_model == "C1000-8FP-E-2G-L" or self.select_model == "C1000-8P-2G-L" or ...:
            self.SN_8P = ""
            self.step1 = False
            self.step2 = False
```

Rollback: xóa dòng `self.SN_8P = ""`.

---

### SN-003a · `sky.py` L1324 (WP)

**Mở:** **Ctrl+G 1323** → phải thấy `elif self.select_model == "WP_check"`.

```python
# TRƯỚC — L1324
            self.thissn="None"

# SAU — thay L1324, thêm L1325
            self.thissn = ""
            self.check_result_OK = False
```

### SN-003b · `sky.py` L1551 (Nanook)

**Mở:** **Ctrl+G 1550** → phải thấy `elif self.select_model == "Nanook"`.

```python
# TRƯỚC — L1551
            self.thissn = "None"

# SAU
            self.thissn = ""
            self.check_result_OK = False
```

Rollback: khôi phục `"None"`.

---

### SN-004 · `sky.py` L724 — `go_run1` Button_check

**Mở:** **Ctrl+G 693** (`def go_run1`) → **Ctrl+F** `select_model=="Button_check"`.

> **Cảnh báo repo:** L725 hiện có `input_dialof.shan)` — code corrupt. **Sửa corrupt trước**, rồi chèn validate sau `setTextValue` và trước `exec_`.

**Đúng pattern** (tham chiếu ipex L779 tương tự):

```python
# TRƯỚC — sau input_dialog.setTextValue(a), trước exec_
                input_dialog.setFixedSize(400, 400)
                input_dialog.show()
                if input_dialog.exec_() == input_dialog.Accepted:
                    self.scaninfo = input_dialog.textValue()
                    ...
                    self.scan_sta=True
                    break

# SAU — chèn validate sau Accepted
                if input_dialog.exec_() == input_dialog.Accepted:
                    text = input_dialog.textValue().strip()
                    if not text:
                        QMessageBox.warning(self, "Scan", "SN cannot be empty")
                        continue
                    self.scaninfo = text
                    ...
                    self.scan_sta = True
                    break
```

Rollback: xóa block `if not text`.

---

### SN-005 · `sky.py` chèn L902 (SKY entry)

**Mở:** **Ctrl+G 901** → `elif self.select_model == "SKY" or self.select_model == "SKY_4G":`

```python
# TRƯỚC — L901–902
        elif self.select_model == "SKY" or self.select_model == "SKY_4G":
            self.step1 = False

# SAU — chèn 2 dòng sau L901
        elif self.select_model == "SKY" or self.select_model == "SKY_4G":
            self.thissn = ""
            self.check_result_OK = False
            self.step1 = False
```

Rollback: xóa 2 dòng reset.

---

## Verification

| Test ID | Fix ID | Setup | Action | Expected result |
|---------|--------|-------|--------|-----------------|
| T-SN-001 | SN-001 | Chạy SKY (set `thissn`) rồi Button_check scan mới | Fail Button_check | MES fail SN = `scaninfo` vừa scan, không phải SN SKY |
| T-SN-002 | SN-002 | Cisco DUT đầu ca fail STEP 1 trước khi set `SN_8P` | Fail cycle | Không upload PVN DUT trước; SN rỗng skip |
| T-SN-003 | SN-003a/b | WP/Nanook decode fail sớm | Fail cycle | Không bản ghi MES chứa literal `"None"` |
| T-SN-004 | SN-004 | Button_check scan dialog | OK với chuỗi rỗng/whitespace | Warning "SN cannot be empty"; re-prompt; không route |
| T-SN-005 | SN-005 | 2 DUT SKY liên tiếp | Pass/fail mỗi DUT | MES SN đúng từng DUT — không dính SN DUT trước |

## Rollback

| Fix ID | Rollback | Behavior cũ quay lại | Rủi ro nếu rollback |
|--------|----------|----------------------|---------------------|
| SN-001 | L1308 đổi lại `thissn` | Fail upload dùng SN stale | **Không khuyến nghị** — MES SN sai quay lại |
| SN-002 | Xóa dòng `self.SN_8P = ""` | PVN cũ có thể upload khi fail sớm | MES trace sai Cisco |
| SN-003a/b | Khôi phục `"None"` | MES nhận literal None | Audit MES fail |
| SN-004 | Xóa block `if not text` | Scan rỗng accepted | Route/upload SN rỗng |
| SN-005 | Xóa 2 dòng reset | SKY dính SN DUT trước | MES trace sai SKY |

## Implementation Window

| Fix ID | Suggested window | Reason |
|--------|------------------|--------|
| SN-003a/b | Week 1 | 2 dòng/site; chặn `"None"` lên MES ngay |
| SN-002 | Week 1 | 1 dòng chèn; chặn PVN stale |
| SN-005 | Week 1 | 2 dòng chèn |
| SN-001 | Week 1–2 | Đổi 1 từ nhưng cần MES verify 10 fail record trên clone |
| SN-004 | Week 2 | Repo G725 corrupt — phải sửa syntax trước, test scan loop |

## Smoke (5 phút)

- [ ] SN-001 G1308: SKY → Button_check scan → Fail → MES = `scaninfo`
- [ ] SN-002 G1160: Cisco STEP1 fail đầu ca → không PVN cũ
- [ ] SN-003 G1324/G1551: WP/Nanook fail sớm → không `"None"` MES
- [ ] SN-004: scan rỗng → dialog lại
- [ ] SN-005 G902: 2 DUT SKY liên tiếp → SN đúng từng DUT

## Ref

`01_sfis_upload_helper.md` · `03_error_code_standard.md` · `00_playbook_sop.md`
