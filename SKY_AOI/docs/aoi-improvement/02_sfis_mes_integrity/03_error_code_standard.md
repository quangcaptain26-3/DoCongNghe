# Chuẩn Mã Lỗi MES — Compact Playbook

**File:** `sky.py` · **Workstream:** `02_sfis_mes_integrity`  
**Nguồn:** `07_camera_io_sfis.md` §4, `10_risks_and_bugs.md`  
**Luật:** Giữ `BDFA0` (SKY) và `BDFA01` (model khác) — **không đổi giá trị** cho đến MES sign-off.

> Line grep từ `sky.py` repo hiện tại (2026-07-12).

---

## Improvement Purpose

Mục tiêu của cải tiến này là chuẩn hóa mã lỗi MES (`BDFA0` vs `BDFA01`) theo model — giữ giá trị hiện tại cho đến MES sign-off, sau đó centralize qua dict `SFIS_FAIL_CODES` và helper `resolve_fail_code`. Đảm bảo defect bucket trên MES nhất quán và dễ audit.

## Before Improvement

Trước cải tiến, mã lỗi fail upload là literal rải rác trong `go_run3`: SKY dùng `BDFA0`, model khác dùng `BDFA01` — 19+ dòng hardcode không có single source of truth. Thêm model mới dễ copy sai mã; engineer phải grep từng block; MES chưa xác nhận liệu hai mã có phải bucket defect khác nhau.

## After Improvement

Sau cải tiến: EC-001 checklist MES xác nhận spec; EC-002 dict `SFIS_FAIL_CODES` + `resolve_fail_code()` tại module level; EC-003 helper `safe_upload_fail` dùng resolve thay literal. Thêm model = thêm 1 dòng dict; audit grep một chỗ; MES defect report nhất quán theo model family.

## Improvement Value

| Area                        | Value |
| --------------------------- | ----- |
| Production stability        | N/A |
| Operator experience         | N/A (mã lỗi hiển thị trên SFIS UI, không đổi operator flow) |
| MES/SFIS integrity          | Defect code đúng spec MES; giảm rủi ro gán sai bucket khi thêm model |
| Maintainability             | Single dict thay 19+ literal; dễ review và sign-off MES |
| Debugging / troubleshooting | Tra mã lỗi theo model từ một bảng thay vì grep rải rác |

## Before / After Summary

| Aspect           | Before | After |
| ---------------- | ------ | ----- |
| Runtime behavior | Upload fail gửi literal hardcode per block | Helper resolve mã theo `select_model` |
| Error handling   | SKY `BDFA0`, others `BDFA01` — không document tập trung | Dict + resolve function; MES checklist |
| Operator impact  | Không đổi trực tiếp | Không đổi trực tiếp |
| Production risk  | Thêm model sai mã → MES report lệch | Chuẩn hóa giảm rủi ro config drift |

---

## Per-Fix Detail

## Fix EC-001 — Checklist MES xác nhận spec mã lỗi

### Code Location

| Field | Detail |
|---|---|
| File | — (không sửa code) |
| Function / Block | Liaison MES — doc/checklist |
| Current lines | N/A |
| Suggested patch location | Gửi 4 câu hỏi § diff EC-001 trước Month 2 code change |

### Current Problem

Hai mã `BDFA0` (SKY) vs `BDFA01` (model khác) hardcode 19+ chỗ nhưng chưa có MES sign-off liệu đúng spec defect bucket.

### Before Improvement

Literal rải rác; engineer giả định hai mã khác bucket; MR6500/Button_check edge case chưa xác nhận.

### Required Change

Gửi checklist MES 4 câu: (1) `BDFA0` vs `BDFA01` — 2 bucket khác nhau? (2) Button_check giữ `BDFA01`? (3) MR6500 cần fail upload? (4) SN rỗng — skip hay vẫn gửi error?

### After Improvement

Spec văn bản từ MES owner trước khi đổi giá trị hoặc centralize dict; giảm rủi ro đổi nhầm bucket.

### Improvement Value

| Area | Value |
| --- | --- |
| Production stability | N/A |
| Operator experience | N/A |
| MES/SFIS integrity | Xác nhận defect bucket trước refactor |
| Maintainability | Baseline spec cho EC-002/003 |
| Debugging / troubleshooting | Doc tham chiếu khi audit MES report |

### Verification

| Test ID | Setup | Action | Expected result |
| --- | --- | --- | --- |
| T-EC-001 | Gửi checklist 4 câu cho MES owner | Nhận trả lời văn bản | Spec `BDFA0`/`BDFA01` xác nhận trước khi đổi giá trị |

### Rollback

N/A — không có code change.

### Suggested Implementation Window

| Window | Reason |
| --- | --- |
| Week 1 (gửi câu hỏi) | Chỉ liaison MES — không code; cần trước Month 2 |

---

## Fix EC-002 — Dict `SFIS_FAIL_CODES` + `resolve_fail_code`

### Code Location

| Field | Detail |
|---|---|
| File | sky.py |
| Function / Block | Module level — sau `sky_clei=` |
| Current lines | **Chèn sau L112** (`sky_clei={...}`) |
| Suggested patch location | Ngay sau L112, trước comment `# DEFAULT_BARCODE_WIDTH` |

### Current Problem

Mã lỗi fail upload là literal rải rác 19+ dòng trong `go_run3` — không single source of truth; thêm model dễ copy sai mã.

### Before Improvement

SKY: `error="BDFA0"` (L1018, L1042, L1066, L1090, L1114, L1140). Others: `error="BDFA01"` (bảng ma trận literal).

### Required Change

Chèn `SFIS_FAIL_CODES` dict + `resolve_fail_code(select_model)` — giá trị khớp 100% literal hiện tại; **không đổi giá trị** cho đến MES sign-off EC-001.

### After Improvement

Thêm model = 1 dòng dict; grep một chỗ; audit MES defect report theo model family.

### Improvement Value

| Area | Value |
| --- | --- |
| Production stability | N/A (dict alone không đổi runtime) |
| Operator experience | N/A |
| MES/SFIS integrity | Single source defect codes |
| Maintainability | Thay 19+ literal bằng dict |
| Debugging / troubleshooting | Tra mã theo model từ một bảng |

### Verification

| Test ID | Setup | Action | Expected result |
| --- | --- | --- | --- |
| T-EC-002 | Dict deployed trên clone | Grep + so bảng literal | `resolve_fail_code(model)` khớp 100% literal hiện tại |

### Rollback

Xóa dict + `resolve_fail_code`. Literal vẫn nguyên nếu chưa có EC-003 — không đổi behavior.

### Suggested Implementation Window

| Window | Reason |
| --- | --- |
| Month 2 | Dict thêm mới không đổi behavior; đi cùng helper SFIS-002 |

---

## Fix EC-003 — Helper `safe_upload_fail` dùng `resolve_fail_code`

### Code Location

| Field | Detail |
|---|---|
| File | sky.py |
| Function / Block | Trong `safe_upload_fail` (sau SFIS-002, ~L691+) |
| Current lines | Line needs re-check in sky.py before patch (helper chưa tồn tại — tạo cùng SFIS-002) |
| Suggested patch location | Trong body `safe_upload_fail` — gọi `resolve_fail_code(self.select_model)` thay literal `error=` |

### Current Problem

Sau SFIS-002 helper vẫn có thể nhận literal error — chưa tích hợp dict EC-002; drift giữa helper và inline sites.

### Before Improvement

Helper hoặc inline pass `error="BDFA0"|"BDFA01"` hardcode per call.

### Required Change

`safe_upload_fail(self, sn)`: `code = resolve_fail_code(self.select_model)`; `data_upload(..., error=code)`. Thay SFIS-003 inline sites. Phụ thuộc EC-001 sign-off + SFIS-002.

### After Improvement

Mọi fail upload resolve mã theo `select_model`; SKY vẫn `BDFA0`, others `BDFA01` — behavior MES không đổi nếu dict đúng.

### Improvement Value

| Area | Value |
| --- | --- |
| Production stability | N/A |
| Operator experience | N/A (mã hiển thị SFIS UI không đổi) |
| MES/SFIS integrity | Defect code nhất quán qua resolve |
| Maintainability | Helper + dict = 2 điểm thay 19+ |
| Debugging / troubleshooting | Đổi mã 1 chỗ dict sau MES sign-off |

### Verification

| Test ID | Setup | Action | Expected result |
| --- | --- | --- | --- |
| T-EC-003 | Helper dùng resolve; SKY fail trên clone | Fail cycle | SFIS UI vẫn hiện `BDFA0`; model khác `BDFA01` |

### Rollback

Helper quay lại literal per-site — phải revert đồng bộ với SFIS-002/003.

### Suggested Implementation Window

| Window | Reason |
| --- | --- |
| Month 2 | Phụ thuộc EC-001 sign-off + SFIS-002 helper |

---

## Fix EC-004 — MR6500 không thêm fail upload

### Code Location

| Field | Detail |
|---|---|
| File | sky.py |
| Function / Block | `show_image_MR6500` |
| Current lines | **L1899** (`get_sfis_SN` query only) |
| Suggested patch location | **Không sửa** — xác nhận spec: MR6500 chỉ query, không `data_upload` fail |

### Current Problem

Risk thêm fail upload/code cho MR6500 khi spec hiện tại chỉ query SN — có thể gây MES record không mong muốn.

### Before Improvement

MR6500: chỉ `get_sfis_SN` L1899 — không fail upload block trong `go_run3`.

### Required Change

**Không làm** — giữ nguyên; EC-001 câu 3 xác nhận MR6500 có cần fail upload hay không.

### After Improvement

MR6500 behavior unchanged; tránh scope creep defect codes.

### Improvement Value

| Area | Value |
| --- | --- |
| Production stability | Tránh thêm upload path chưa spec |
| Operator experience | N/A |
| MES/SFIS integrity | Giữ MR6500 query-only cho đến MES quyết định |
| Maintainability | Giảm surface area EC refactor |
| Debugging / troubleshooting | N/A |

### Verification

| Test ID | Setup | Action | Expected result |
| --- | --- | --- | --- |
| — | MR6500 regression | Chạy cycle MR6500 | Chỉ query SN; không fail upload mới |

### Rollback

N/A — no change planned.

### Suggested Implementation Window

| Window | Reason |
| --- | --- |
| Không làm | MR6500 không fail upload theo spec hiện tại |

---

## Bạn phải sửa gì?

| ID | Tuần này? | File | Vị trí | Việc |
|----|-----------|------|--------|------|
| **EC-001** | Không sửa code | — | — | Hỏi MES 4 câu checklist § dưới |
| **EC-002** | Month 2 | `sky.py` | **Chèn sau L112** (`sky_clei=`) | Thêm `SFIS_FAIL_CODES` dict |
| **EC-003** | Month 2 | `sky.py` | Trong `safe_upload_fail` (sau L691) | `resolve_fail_code(model)` |
| **EC-004** | Không | `sky.py` L1899 | `show_image_MR6500` | Không thêm fail code |

**Làm SN + SFIS-001 trước.** File này không blocker P0/P1.

---

## Ma trận literal hiện tại — từng dòng `go_run3`

### SKY / SKY_4G — `error="BDFA0"`

| Step fail | Dòng `error=` | Block |
|-----------|---------------|-------|
| step6 | **L1018** | `elif self.step6 == False` SKY |
| step5 | **L1042** | `elif self.step5 == False` |
| step4 | **L1066** | `elif self.step4 == False` |
| step3 | **L1090** | `elif self.step3 == False` |
| step2 | **L1114** | `elif self.step2==False` |
| step1 | **L1140** | `elif self.step1==False` (có try L1136) |

### Cisco — `error="BDFA01"`

| Step fail | Dòng `error=` |
|-----------|---------------|
| step2 | **L1226** |
| step1 | **L1253** (có try L1249) |

### WP_check / C9105AXW_E — `error="BDFA01"`

| Step fail | Dòng `error=` |
|-----------|---------------|
| step6 | **L1414** |
| step5 | **L1438** |
| step4 | **L1462** |
| step3 | **L1486** |
| step2 | **L1510** |
| step1 | **L1536** (có try L1532) |

### Nanook — `error="BDFA01"`

| Step fail | Dòng `error=` |
|-----------|---------------|
| step6 | **L1643** |
| step5 | **L1667** |
| step4 | **L1691** |
| step3 | **L1715** |
| step2 | **L1739** |
| step1 | **L1765** (có try L1761) |

### Button_check — `error="BDFA01"`

| Step fail | Dòng `error=` | Ghi chú |
|-----------|---------------|---------|
| step1 | **L1309** | Có try L1305; SN đổi ở **L1308** (`02_…` SN-001) |

### Không có fail upload

| Model | Ghi chú |
|-------|---------|
| MR6500 | Chỉ query L1899 `get_sfis_SN` — không `data_upload` fail |
| HH4K / ipex | Không SFIS |

---

## Bảng tổng

| ID | Vấn đề | Đi tới | Thao tác |
|----|--------|--------|----------|
| EC-001 | Hai mã khác nhau | F `error="BDFA0"` | Chỉ doc — không đổi L1018/L1042/… |
| EC-002 | Literal rải rác | **G112** sau `sky_clei` | Chèn dict (giá trị = bảng trên) |
| EC-003 | Helper chưa resolve | Trong `safe_upload_fail` | `resolve_fail_code` |
| EC-004 | MR6500 | **G1899** | Không thêm |

---

## Diff patches

### EC-002 · `sky.py` chèn sau L112

**Mở:** **Ctrl+G 112** → dòng `sky_clei={...}` → chèn **ngay sau L112**, trước comment `# DEFAULT_BARCODE_WIDTH`.

```python
SFIS_FAIL_CODES = {
    "SKY": "BDFA0",
    "SKY_4G": "BDFA0",
    "Button_check": "BDFA01",
    "WP_check": "BDFA01",
    "C9105AXW_E": "BDFA01",
    "Nanook": "BDFA01",
    "C1000-8FP-E-2G-L": "BDFA01",
    "C1000-8P-2G-L": "BDFA01",
    "C1000-8T-2G-L": "BDFA01",
    "C1200-8FP-2G": "BDFA01",
    "C1200-8P-E-2G": "BDFA01",
    "C1200-8T-E-2G": "BDFA01",
    "C1300-8P-E-2G": "BDFA01",
    "C1300-8T-E-2G": "BDFA01",
    "C1000-8FP-2G-L": "BDFA01",
    "C1000-8P-E-2G-L": "BDFA01",
    "C1300-8FP-2G": "BDFA01",
    "C1000-8T-E-2G-L": "BDFA01",
    "HH4K": None,
    "ipex_check": None,
}

def resolve_fail_code(select_model):
    return SFIS_FAIL_CODES.get(select_model, "BDFA01")
```

Rollback: xóa dict + hàm.

---

### EC-001 · checklist MES (không diff)

1. `BDFA0` vs `BDFA01` — 2 bucket defect khác nhau?
2. Button_check giữ `BDFA01`?
3. MR6500 có cần fail upload?
4. SN rỗng — skip hay vẫn gửi error?

---

## Verification

| Test ID | Fix ID | Setup | Action | Expected result |
|---------|--------|-------|--------|-----------------|
| T-EC-001 | EC-001 | Gửi checklist 4 câu cho MES owner | Nhận trả lời văn bản | Spec `BDFA0`/`BDFA01` xác nhận trước khi đổi giá trị |
| T-EC-002 | EC-002 | Dict `SFIS_FAIL_CODES` deployed trên clone | Grep + so bảng literal | `resolve_fail_code(model)` khớp 100% literal hiện tại |
| T-EC-003 | EC-003 | Helper dùng resolve; SKY fail trên clone | Fail cycle | SFIS UI vẫn hiện `BDFA0`; model khác `BDFA01` |

## Rollback

| Fix ID | Rollback | Behavior cũ quay lại | Rủi ro nếu rollback |
|--------|----------|----------------------|---------------------|
| EC-002 | Xóa dict + `resolve_fail_code` | Literal rải rác (không đổi behavior nếu chưa có EC-003) | Không — literal vẫn nguyên |
| EC-003 | Helper quay lại literal per-site — ảnh hưởng mọi call site đã chuyển qua helper | Mã hardcode từng block | Phải revert đồng bộ với SFIS-002/003 |

## Implementation Window

| Fix ID | Suggested window | Reason |
|--------|------------------|--------|
| EC-001 | Week 1 (gửi câu hỏi) | Chỉ liaison MES — không code; cần trước Month 2 |
| EC-002 | Month 2 | Dict thêm mới không đổi behavior; đi cùng helper |
| EC-003 | Month 2 | Phụ thuộc EC-001 sign-off + SFIS-002 helper |
| EC-004 | Không làm | MR6500 không fail upload theo spec hiện tại |

## Smoke

- [ ] Grep `error="BDFA0"` — 6 dòng SKY (L1018, L1042, L1066, L1090, L1114, L1140)
- [ ] Grep `error="BDFA01"` — 13 dòng fail (bảng trên)
- [ ] Sau EC-003: fail SKY clone vẫn hiện `BDFA0` trên SFIS UI

## Ref

`01_sfis_upload_helper.md` · `02_sn_reset_and_validation.md` · `00_playbook_sop.md`
