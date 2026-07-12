# SOP Viết Playbook Cải tiến AOI

**Mục đích:** Tài liệu này tổng hợp logic từ Phase A + các vòng chỉnh sửa (Before/After, vị trí patch, compact). **Dán vào chat mới** khi cần tạo/cập nhật file trong `docs/aoi-improvement/`.

**Mẫu tham chiếu:** `01_runtime_stability/01_wait_test_stall_fix.md`

---

## 1. Phân vai 2 folder docs

| | `docs/aoi-analysis/` | `docs/aoi-improvement/` |
|---|---------------------|-------------------------|
| Là gì | Evidence, architecture, pipeline internals | SOP sửa code, test, rollback |
| Trả lời | Code làm gì? Bug ở đâu? | **Sửa gì, ở đâu, dòng nào, trước/sau thế nào, test/rollback** |
| Nguồn line | Đọc `sky.py`, ghi evidence | **Trích** từ analysis — không bịa line, không viết analysis mới |
| Sửa code? | Không | Không (chỉ doc) — trừ khi user yêu cầu implement |

---

## 2. Cấu trúc folder

```text
docs/aoi-improvement/
  00_index.md              ← mục lục + link
  00_playbook_sop.md       ← file này (meta / prompt chat sau)
  01_priority_roadmap.md   ← P0–P4, owner doc, first action

  01_runtime_stability/
  02_sfis_mes_integrity/
  03_sensor_dispatch/
  04_dependency_deployment/
  05_ai_ocr_runtime/
  06_pipeline_safety/
  07_testing_and_release/
```

**Luồng làm việc:** `01_priority_roadmap.md` → chọn Priority → mở owner doc workstream → patch theo Fix ID.

---

## 3. Logic một file improvement (compact — chuẩn mặc định)

Mỗi file playbook = **5 section giá trị** + **1 bảng tổng** + **N block diff**.

### 3.0 Improvement Value sections (bắt buộc — rule 2026-07-12)

Đặt sau header, trước bảng tổng. Viết tiếng Việt, ngắn, thực dụng.

```markdown
## Improvement Purpose
## Before Improvement
## After Improvement
## Improvement Value        ← bảng 5 area, N/A nếu không liên quan
## Before / After Summary   ← bảng 4 aspect
```

Mẫu: `01_runtime_stability/01_wait_test_stall_fix.md`. Không xóa Patch Guidance / diff / rollback có sẵn.

### 3.1 Header file (4 dòng)

```markdown
# [Tên] — Compact Playbook
**File:** sky.py · **Workstream:** `0X_...` · **Nguồn:** [analysis docs]
**Luật / invariant:** [1 câu bất biến sau patch]
> Line từ repo hiện tại. Ctrl+F anchor trước khi sửa.
```

### 3.2 Bảng tổng (bắt buộc — 1 bảng duy nhất)

Gộp: Fix Map + navigation + test + ship order.

| ID | Vấn đề | Đi tới | Anchor (đúng chỗ khi thấy…) | Thao tác | Test |
|----|--------|--------|-----------------------------|----------|------|

**Cột bắt buộc:**

| Cột | Ghi gì |
|-----|--------|
| **ID** | Fix ID có prefix (§4) |
| **Vấn đề** | 1 câu — symptom production |
| **Đi tới** | `G1910` = Ctrl+G line · `F \`text\`` = Ctrl+F |
| **Anchor** | Landmark text + **đúng chỗ** / **sai chỗ** (1 dòng mỗi loại) |
| **Thao tác** | **Chèn** / **+1 dòng** / **Bọc try** / **Đổi X→Y** + indent nếu chèn block |
| **Test** | 1 scenario smoke |

**Sub-bảng** (nếu nhiều site cùng pattern): SFIS sites, dependency imports, v.v.

**Ship order:** 1 dòng cuối bảng hoặc dòng text `AI-001 → RT-001 → …`

### 3.3 Block patch (mỗi Fix — chỉ diff)

```markdown
### [ID] · [Function/block] Lxxx

**Đúng chỗ:** … · **Sai:** …

​```python
# TRƯỚC
...

# SAU
...
​```

Rollback: [1 câu]
```

**Quy tắc diff:**

- Copy snippet **thật** từ `sky.py` (5–15 dòng quanh anchor)
- `# TRƯỚC` / `# SAU` trong **một** code block — dev diff trực tiếp
- Không lặp lại nội dung đã có trong bảng tổng
- Multi-site cùng pattern: 1 diff mẫu + bảng site (G/F/try sẵn?)

### 3.4 Kết file

```markdown
## Smoke (5 phút)
- [ ] item ngắn

## Ref
analysis docs · roadmap · 00_playbook_sop.md
```

---

## 4. Fix ID prefix

| Prefix | Nhóm |
|--------|------|
| `RT-` | Runtime / wait_test / UI thread |
| `SFIS-` | MES upload / try-finally |
| `SN-` | Serial validation / reset |
| `SENSOR-` | go_run2 dispatch |
| `DEP-` | Import / deployment / assets |
| `AI-` | Cambrian / OCR |
| `PIPE-{MODEL}-` | Gate pipeline cụ thể |
| `TEST-` | Regression / release |

**Line rules:**

1. Line lấy từ `docs/aoi-analysis/` hoặc grep `sky.py` — không bịa
2. Chưa chắc → `Line needs re-check in sky.py before patch`
3. **Function/Block** phải cụ thể: `go_run3 Button_check branch`, không ghi `sửa go_run3`

---

## 5. Điều hướng trong sky.py (📍)

**Thứ tự ưu tiên:** Ctrl+F anchor text > Ctrl+G line (line drift thường xuyên).

| Ký hiệu | Nghĩa |
|---------|--------|
| `G1910` | Ctrl+G → 1910 |
| `F \`def show_image(\`` | Ctrl+F chuỗi |
| **Đúng chỗ** | Landmark bắt buộc thấy |
| **Sai chỗ** | Nhầm block trùng tên (nhiều `elif mychoose==65536`) |

**Khi chèn block:** ghi indent — VD `else:` **8 spaces** (cùng cột `elif self.select_model`).

---

## 6. Roadmap (`01_priority_roadmap.md`)

Bảng: `Priority | Area | Issue | Line evidence | Owner doc | First action`

| Priority | Ý nghĩa |
|----------|---------|
| P0 | Crash / stall — ship trước |
| P1 | MES/SN integrity |
| P2 | Wrong pipeline (sensor dispatch) |
| P3 | Deployment / guards |
| P4 | UX / performance |

---

## 7. Cấm / nên

| Cấm | Nên |
|-----|-----|
| Analysis mới trong improvement | Trích evidence + link analysis |
| "Sửa trong go_run3" chung chung | G + F + anchor + diff |
| Bịa line number | Verify grep `sky.py` |
| Duplicate pipeline step logic | Link `13`–`19` pipeline docs |
| File dài >~200 dòng khi compact đủ | 1 bảng + diff blocks |

---

## 8. Prompt copy — chat sau

Dán block dưới khi cần AI tạo/cập nhật playbook:

```text
Đọc docs/aoi-improvement/00_playbook_sop.md và áp dụng format compact.

Nguồn analysis: [list docs, vd 10_risks_and_bugs.md, 16_cisco_pipeline.md]
Tạo/cập nhật: docs/aoi-improvement/[workstream]/[tên_file].md

Yêu cầu:
- Header 4 dòng + 5 section Improvement Value (Purpose/Before/After/Value/Summary)
- Bảng tổng (ID|Vấn đề|Đi tới|Anchor|Thao tác|Test)
- Mỗi Fix: diff TRƯỚC/SAU từ sky.py thật (grep verify line)
- G/F anchor + đúng chỗ/sai chỗ
- Fix ID đúng prefix
- Ship order + smoke checklist
- Không sửa code sky.py, không viết analysis mới
- Tiếng Việt kỹ thuật, compact

Mẫu: 01_runtime_stability/01_wait_test_stall_fix.md
```

---

## 9. Checklist trước khi merge doc

- [ ] Mọi Fix có ID + G hoặc F + anchor đúng/sai
- [ ] Diff copy từ `sky.py` thật
- [ ] Line evidence khớp analysis
- [ ] Test smoke 1 dòng/fix
- [ ] Rollback 1 câu/fix
- [ ] Link owner doc trong roadmap (nếu file mới)
- [ ] 5 section Improvement Value (Purpose/Before/After/Value/Summary)
- [ ] `## Verification` — bảng Test ID | Setup | Action | Expected, map Fix ID
- [ ] `## Rollback` — bảng Fix ID | Rollback | Behavior cũ | Rủi ro nếu revert
- [ ] `## Implementation Window` — Fix ID | Week/Month | Reason (P0 → Week 1; helper/integrity → Week 1–2; guard → Week 1; preflight → Week 2; OCR/UI → Month 1; refactor → Month 1+)

---

## 10. Evolution log (tóm tắt các vòng chat)

| Vòng | Thêm gì |
|------|---------|
| Phase A | `00_index`, `01_priority_roadmap`, folder workstream, Fix Map |
| Vòng 2 | Before/After, Patch Guidance chi tiết, Fix ID prefix |
| Vòng 3 | 📍 G/F/landmark — dev biết mở đâu |
| Vòng 4 | **Compact:** 1 bảng tổng + diff blocks — chuẩn mặc định |
| Vòng 5 | **Improvement Value:** Purpose/Before/After/Value/Summary — giải thích *tại sao* sửa |

**Chuẩn hiện tại = §3 compact + §3.0 Value sections.**
