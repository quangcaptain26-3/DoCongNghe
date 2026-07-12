# SFIS Upload Helper — Compact Playbook

**File:** `sky.py` · **Workstream:** `02_sfis_mes_integrity`  
**Nguồn:** `07_camera_io_sfis.md` §4, `10_risks_and_bugs.md`  
**Luật:** Fail upload dù SFIS throw vẫn phải tới `wait_test=True` — line không treo.

> Line grep từ `sky.py` repo hiện tại (2026-07-12). **Ctrl+G** → **Ctrl+F** xác nhận anchor.

---

## Improvement Purpose

Mục tiêu của cải tiến này là đảm bảo mọi fail upload SFIS/MES đều an toàn khi SOAP throw exception — line không treo và chu kỳ test luôn recover. Dài hạn chuẩn hóa qua helper `safe_upload_fail/pass` để giảm duplicate và dễ audit upload path.

## Before Improvement

Trước cải tiến, 16+ block fail upload trong `go_run3` gọi `data_upload` trực tiếp không bọc try/except. Khi SFIS timeout hoặc SOAP lỗi, exception bỏ qua `wait_test=True` phía sau — vòng test kẹt. Operator phải Stop/restart; MES có thể thiếu bản ghi fail hoặc upload dở dang không rõ.

## After Improvement

Sau cải tiến, mọi fail block bọc try/except với `wait_test=True` **luôn ngoài** except — SFIS throw vẫn log lỗi, báo operator "cycle continues", line sẵn sàng DUT tiếp. Month 2: helper `safe_upload_fail`/`safe_upload_pass` thay inline duplicate, dễ thêm model mới và audit upload.

## Improvement Value

| Area                        | Value |
| --------------------------- | ----- |
| Production stability        | Giảm stall khi SFIS/network lỗi — line không treo sau upload fail |
| Operator experience         | Thấy thông báo SFIS failed thay vì app đứng im |
| MES/SFIS integrity          | Upload fail vẫn có log; giảm rủi ro chu kỳ treo giữa chừng MES |
| Maintainability             | Pattern try/finally chung; helper Month 2 giảm 16+ copy-paste |
| Debugging / troubleshooting | Log SFIS exception kèm step/model — dễ truy vết SOAP lỗi |

## Before / After Summary

| Aspect           | Before | After |
| ---------------- | ------ | ----- |
| Runtime behavior | SFIS throw → skip `wait_test` → line treo | SFIS throw → log → `wait_test=True` → DUT tiếp |
| Error handling   | Bare `data_upload` trên fail path | try/except + finally wait_test |
| Operator impact  | Stop/restart sau SFIS lỗi | Chu kỳ tiếp tục; thông báo rõ trên textbox |
| Production risk  | Downtime khi MES/network không ổn | Line recover; throughput ổn định hơn khi SFIS flaky |

---

## Per-Fix Detail

## Fix SFIS-001 — Bọc try/except fail upload (16 sites)

### Code Location

| Field | Detail |
|---|---|
| File | sky.py |
| Function / Block | `go_run3` → fail upload blocks (SKY/Cisco/WP/Nanook step2–6) |
| Current lines | L1016–1020, L1040–1044, L1064–1068, L1088–1092, L1112–1116, L1224–1228, L1412–1417, L1436–1441, L1460–1465, L1484–1489, L1508–1513, L1641–1646, L1665–1670, L1689–1694, L1713–1718, L1737–1742 |
| Suggested patch location | Mỗi block `if self.sfis_choose==True:` + `data_upload` + `wait_test=True` — bọc try như diff mẫu L1224–1229 |

### Current Problem

Khi SFIS timeout hoặc SOAP throw exception, luồng thoát bỏ qua `wait_test=True` phía sau — vòng test kẹt; operator phải Stop/restart; MES có thể thiếu bản ghi fail hoặc upload dở dang.

### Before Improvement

16 block fail gọi `data_upload` trực tiếp không bọc try/except. Step1 fail (5 site: SKY L1136, Cisco L1249, Button_check L1305, WP L1532, Nanook L1761) đã có try — **bỏ qua**, không bọc thêm.

### Required Change

Bọc `if self.sfis_choose` + upload + log trong `try:`; `except Exception as e:` log + emit `"SFIS upload failed — cycle continues"`; `self.wait_test = True` **luôn ngoài** except. Copy pattern diff Cisco step2 L1224–1229; SKY dùng `thissn` + `BDFA0`; WP/Nanook dùng `thissn` + `BDFA01`.

### After Improvement

SFIS throw → log lỗi → operator thấy thông báo → `wait_test=True` → line sẵn sàng DUT tiếp; không treo sau upload fail.

### Improvement Value

| Area | Value |
| --- | --- |
| Production stability | Giảm stall khi SFIS/network lỗi — line không treo sau upload fail |
| Operator experience | Thấy thông báo SFIS failed thay vì app đứng im |
| MES/SFIS integrity | Upload fail vẫn có log; giảm rủi ro chu kỳ treo giữa chừng MES |
| Maintainability | Pattern try/finally chung; bước đệm trước helper Month 2 |
| Debugging / troubleshooting | Log SFIS exception kèm step/model — dễ truy vết SOAP lỗi |

### Verification

| Test ID | Setup | Action | Expected result |
| --- | --- | --- | --- |
| T-SFIS-001a | Mock `data_upload` raise; Cisco step2 fail (L1224) | Chạy fail cycle | Log lỗi; `wait_test=True`; DUT tiếp |
| T-SFIS-001b | Mock throw; SKY step3 fail (L1088) | Fail cycle | Loop tiếp; không treo |
| T-SFIS-001c | Mock throw; WP step2 (L1509) + Nanook step2 (L1738) | Fail cycle | Loop tiếp mỗi site |
| T-SFIS-001d | `sfis_choose=False` | Fail cycle bất kỳ | Không crash; không gọi SFIS |

### Rollback

Bỏ try/except từng site (16 chỗ — revert theo PR). Behavior cũ: SFIS throw → skip `wait_test` → line treo khi MES/network lỗi.

### Suggested Implementation Window

| Window | Reason |
| --- | --- |
| Week 1–2 | P0; chia theo model (Cisco → SKY → WP → Nanook), mock test từng PR |

---

## Fix SFIS-002 — Chèn helper `safe_upload_fail`

### Code Location

| Field | Detail |
|---|---|
| File | sky.py |
| Function / Block | Sau `clear_showing` (trước `go_run1`) |
| Current lines | L691–692 (khoảng trống giữa `clear_showing` và `def go_run1`) |
| Suggested patch location | Chèn **giữa L691 và L693** (sau `def clear_showing`, trước `def go_run1`) |

### Current Problem

16+ block fail upload duplicate cùng pattern try/except + `data_upload` + log — khó audit, thêm model mới dễ sót site.

### Before Improvement

Mỗi fail block inline: `if sfis_choose`, `data_upload(..., error=...)`, log, try/except riêng lẻ (sau SFIS-001).

### Required Change

Month 2: chèn helper `safe_upload_fail(self, sn, error=None)` bọc try/except, log, skip empty SN; tích hợp `resolve_fail_code` (EC-003). **Không làm** cho đến khi SN-* xong.

### After Improvement

Một helper duy nhất cho mọi fail upload; thêm model = gọi helper thay copy 10+ dòng; dễ audit upload path.

### Improvement Value

| Area | Value |
| --- | --- |
| Production stability | N/A (behavior giữ nguyên sau SFIS-001) |
| Operator experience | N/A |
| MES/SFIS integrity | Upload path thống nhất; giảm sót site khi thêm model |
| Maintainability | Thay 16+ copy-paste bằng 1 helper |
| Debugging / troubleshooting | Log tập trung trong helper |

### Verification

| Test ID | Setup | Action | Expected result |
| --- | --- | --- | --- |
| T-SFIS-002 | (Month 2) helper deployed trên clone | Fail cycle SKY | Upload qua helper; behavior MES không đổi |

### Rollback

Xóa helper block. **Ảnh hưởng mọi call site đã chuyển** (16+ fail) — revert phải đồng bộ toàn bộ site.

### Suggested Implementation Window

| Window | Reason |
| --- | --- |
| Month 2 | Helper — chờ SN-* xong để không đổi 2 thứ cùng lúc |

---

## Fix SFIS-003 — Thay inline fail bằng helper call

### Code Location

| Field | Detail |
|---|---|
| File | sky.py |
| Function / Block | `go_run3` → mọi fail block có `error="BDFA0"` / `error="BDFA01"` |
| Current lines | F `error="BDFA0"` (SKY L1018, L1042, L1066, L1090, L1114, L1140); F `error="BDFA01"` (Cisco/WP/Nanook/Button_check — bảng EC ma trận) |
| Suggested patch location | Thay block inline upload bằng 1 dòng `self.safe_upload_fail(sn, ...)` sau SFIS-002 helper tồn tại |

### Current Problem

Fail upload logic rải rác 19+ chỗ với literal error code — duplicate và khó đồng bộ khi đổi spec MES.

### Before Improvement

Sau SFIS-001: mỗi site vẫn inline try/except + `data_upload(..., error="BDFA0"|"BDFA01")`.

### Required Change

Month 2: thay mỗi inline fail block bằng `self.safe_upload_fail(thissn_or_SN_8P)` (helper tự resolve error qua EC-003); giữ `wait_test=True` ngoài helper hoặc trong helper theo thiết kế cuối.

### After Improvement

1 dòng helper thay 8–12 dòng inline; mã lỗi resolve từ dict; thêm model = 1 call site.

### Improvement Value

| Area | Value |
| --- | --- |
| Production stability | N/A |
| Operator experience | N/A |
| MES/SFIS integrity | Defect code nhất quán qua `resolve_fail_code` |
| Maintainability | 19+ literal → 1 helper call per site |
| Debugging / troubleshooting | Grep `safe_upload_fail` thay grep `error=` rải rác |

### Verification

| Test ID | Setup | Action | Expected result |
| --- | --- | --- | --- |
| T-SFIS-002 | (Month 2) helper + inline replacement trên clone | Fail + pass cycle SKY | Upload qua helper; MES defect code không đổi |

### Rollback

Khôi phục inline upload từng site — phải revert đồng bộ với SFIS-002.

### Suggested Implementation Window

| Window | Reason |
| --- | --- |
| Month 2 | Phụ thuộc SFIS-002 helper + EC-003 resolve |

---

## Fix SFIS-004 — Helper `safe_upload_pass`

### Code Location

| Field | Detail |
|---|---|
| File | sky.py |
| Function / Block | `show_image_SKY` → pass upload |
| Current lines | L2950–2951 (`if self.sfis_choose==True:` + `data_upload(self.thissn, self.data)`) |
| Suggested patch location | **G2951** trong `def show_image_SKY` — thay inline pass bằng `safe_upload_pass` |

### Current Problem

Pass upload inline không bọc try/except — SFIS throw trên pass path có thể gây exception không xử lý (ít gặp hơn fail nhưng cùng pattern).

### Before Improvement

Inline `self.mysfis.data_upload(self.thissn, self.data)` không error code; không helper chung với fail path.

### Required Change

Month 2: chèn `safe_upload_pass(self, sn)` (try/except + log); thay L2951 và các pass site tương tự (L3295, L4591, L5003 — Line needs re-check in sky.py before patch).

### After Improvement

Pass upload qua helper; SFIS throw trên pass → log, cycle tiếp tục; dễ MES verify sample trước rollout.

### Improvement Value

| Area | Value |
| --- | --- |
| Production stability | Giảm rủi ro exception trên pass path khi SFIS flaky |
| Operator experience | Thông báo rõ nếu pass upload lỗi |
| MES/SFIS integrity | Pass upload path audit được |
| Maintainability | Cặp fail/pass helper đối xứng |
| Debugging / troubleshooting | Log pass upload tập trung |

### Verification

| Test ID | Setup | Action | Expected result |
| --- | --- | --- | --- |
| T-SFIS-002 | (Month 2) `safe_upload_pass` trên clone | Pass cycle SKY | MES pass record; không crash nếu mock throw |

### Rollback

Inline pass upload tại L2951 — duplicate quay lại nếu revert không đồng bộ pass sites khác.

### Suggested Implementation Window

| Window | Reason |
| --- | --- |
| Month 2 | Pass upload — cần MES verify sample trước |

---

## Bạn phải sửa gì?

### Tuần này (P0) — chỉ **SFIS-001**: bọc try/except

**Không sửa** helper Month 2 (SFIS-002/003/004) cho đến khi xong SN trong `02_sn_reset_and_validation.md`.

**Quy tắc:** Mỗi block có `data_upload` + `wait_test=True` mà **không** có `try:` ngay phía trên `if self.sfis_choose` → bọc try như diff mẫu. `wait_test=True` **luôn ngoài** `except`.

---

## SFIS-001 — bảng từng dòng phải sửa

| # | Model | Step fail | Dòng upload | Dòng `wait_test` | Có `try`? | Hành động |
|---|-------|-----------|-------------|------------------|-----------|-----------|
| 1 | Cisco | step2 | **L1225–1226** | L1229 | **Không** | Bọc L1224–1228 |
| 2 | SKY | step6 | **L1017–1018** | L1021 | Không | Bọc L1016–1020 |
| 3 | SKY | step5 | **L1041–1042** | L1045 | Không | Bọc L1040–1044 |
| 4 | SKY | step4 | **L1065–1066** | L1069 | Không | Bọc L1064–1068 |
| 5 | SKY | step3 | **L1089–1090** | L1093 | Không | Bọc L1088–1092 |
| 6 | SKY | step2 | **L1113–1114** | L1117 | Không | Bọc L1112–1116 |
| 7 | WP | step6 | **L1413–1414** | ~L1417 | Không | Bọc block upload |
| 8 | WP | step5 | **L1437–1438** | ~L1441 | Không | Bọc |
| 9 | WP | step4 | **L1461–1462** | ~L1465 | Không | Bọc |
| 10 | WP | step3 | **L1485–1486** | ~L1489 | Không | Bọc |
| 11 | WP | step2 | **L1509–1510** | ~L1513 | Không | Bọc |
| 12 | Nanook | step6 | **L1642–1643** | ~L1646 | Không | Bọc |
| 13 | Nanook | step5 | **L1666–1667** | ~L1670 | Không | Bọc |
| 14 | Nanook | step4 | **L1690–1691** | ~L1694 | Không | Bọc |
| 15 | Nanook | step3 | **L1714–1715** | ~L1718 | Không | Bọc |
| 16 | Nanook | step2 | **L1738–1739** | ~L1742 | Không | Bọc |

### Đã có try — **bỏ qua** (không bọc thêm)

| Model | Step | Dòng `try:` | Dòng upload | Ghi chú |
|-------|------|-------------|-------------|---------|
| SKY | step1 | **L1136** | L1139–1140 | ✓ |
| Cisco | step1 | **L1249** | L1252–1253 | ✓ |
| Button_check | step1 | **L1305** | L1308–1309 | ✓ — nhớ SN-001 đổi `scaninfo` |
| WP | step1 | **L1532** | L1535–1536 | ✓ |
| Nanook | step1 | **L1761** | L1764–1765 | ✓ |

**Điều hướng nhanh:** `sky.py` → **Ctrl+F** `def go_run3` (hoặc F `elif self.select_model == "SKY"` nếu thiếu def) → nhảy tới dòng trong bảng.

---

## Bảng tổng

| ID | Vấn đề | Đi tới | Thao tác | Test |
|----|--------|--------|----------|------|
| **SFIS-001** | SFIS throw → treo | **G1224** / F `data_upload(self.SN_8P` | Bọc try; `wait_test` ngoài try | Mock throw → DUT tiếp |
| SFIS-002 | (Month 2) helper | **G691** sau `clear_showing` | Chèn `safe_upload_fail` | — |
| SFIS-003 | (Month 2) thay inline | F `error="BDFA0"` | 1 dòng helper | — |
| SFIS-004 | (Month 2) pass | **G2951** `show_image_SKY` | `safe_upload_pass` | — |

**Ship:** SN-* → SFIS-001 (16 chỗ “Không”) → SFIS-002/003/004.

---

## Diff patches

### SFIS-001 · mẫu #1 Cisco step2 — `sky.py` L1224–1229

**Mở:** **Ctrl+G 1210** → scroll tới `elif self.step2 == False` trong nhánh Cisco.

**Đúng chỗ:** sau `updatecount(...)`, trước `elif mychoose == 65536` step2.  
**Sai chỗ:** L1249 `try:` step1 fail (đã có try).

```python
# TRƯỚC — L1224–1229
                            if self.sfis_choose==True:
                                self.mysfis.data_upload(self.SN_8P, self.data,
                                                    error="BDFA01")
                            logging.error("fail upload OK")
                            self.myuihand.textbox.emit("fail upload OK")
                            self.wait_test = True

# SAU
                            try:
                                if self.sfis_choose==True:
                                    self.mysfis.data_upload(self.SN_8P, self.data,
                                                        error="BDFA01")
                                    logging.error("fail upload OK")
                                    self.myuihand.textbox.emit("fail upload OK")
                            except Exception as e:
                                logging.error(f"SFIS fail upload error: {e}")
                                self.myuihand.textbox.emit("SFIS upload failed — cycle continues")
                            self.wait_test = True
```

**Copy pattern** cho #2–6 (SKY): thay `SN_8P`→`thissn`, `BDFA01`→`BDFA0`, giữ đúng dòng L1016/L1040/L1064/L1088/L1112.  
**Copy pattern** cho #7–16 (WP/Nanook): `thissn` + `BDFA01`, dòng L1412/L1436/…/L1738.

---

### SFIS-002 · (Month 2) chèn helper — `sky.py` L691–692

**Mở:** **Ctrl+G 688** `def clear_showing` → chèn **giữa L691 và L693** (trước `def go_run1`).

Rollback: xóa helper block.

---

### SFIS-004 · (Month 2) pass — `sky.py` L2951

**Mở:** **Ctrl+F** `def show_image_SKY` → tìm `data_upload(self.thissn, self.data)` **không** có `error=`.

Rollback: inline pass upload.

---

## Verification

| Test ID | Fix ID | Setup | Action | Expected result |
|---------|--------|-------|--------|-----------------|
| T-SFIS-001a | SFIS-001 | Mock `data_upload` raise; Cisco step2 fail (L1224) | Chạy fail cycle | Log lỗi; `wait_test=True`; DUT tiếp |
| T-SFIS-001b | SFIS-001 | Mock throw; SKY step3 fail (L1088) | Fail cycle | Loop tiếp; không treo |
| T-SFIS-001c | SFIS-001 | Mock throw; WP step2 (L1509) + Nanook step2 (L1738) | Fail cycle | Loop tiếp mỗi site |
| T-SFIS-001d | SFIS-001 | `sfis_choose=False` | Fail cycle bất kỳ | Không crash; không gọi SFIS |
| T-SFIS-002 | SFIS-002/003/004 | (Month 2) helper deployed trên clone | Fail + pass cycle SKY | Upload qua helper; behavior MES không đổi |

## Rollback

| Fix ID | Rollback | Behavior cũ quay lại | Rủi ro nếu rollback |
|--------|----------|----------------------|---------------------|
| SFIS-001 | Bỏ try/except từng site (16 chỗ — revert theo PR) | SFIS throw → skip `wait_test` | Line treo khi SFIS lỗi mạng/timeout |
| SFIS-002/003/004 | Xóa helper, khôi phục inline upload — **ảnh hưởng mọi call site đã chuyển** (16+ fail, 5+ pass) | Literal upload rải rác | Duplicate quay lại; revert phải đồng bộ toàn bộ site |

## Implementation Window

| Fix ID | Suggested window | Reason |
|--------|------------------|--------|
| SFIS-001 | Week 1–2 | P0; chia theo model (Cisco → SKY → WP → Nanook), mock test từng PR |
| SFIS-002/003 | Month 2 | Helper — chờ SN-* xong để không đổi 2 thứ cùng lúc |
| SFIS-004 | Month 2 | Pass upload — cần MES verify sample trước |

## Smoke (5 phút)

- [ ] #1 Cisco L1224 + mock throw → `wait_test` reset
- [ ] #5 SKY L1089 step3 + throw → loop tiếp
- [ ] #11 WP L1509 + throw → loop tiếp
- [ ] #16 Nanook L1738 + throw → loop tiếp
- [ ] SFIS off → không crash trên fail path

## Ref

`02_sn_reset_and_validation.md` · `03_error_code_standard.md` · `01_runtime_stability/01_wait_test_stall_fix.md`
