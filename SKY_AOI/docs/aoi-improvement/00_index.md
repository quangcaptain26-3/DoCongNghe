# AOI Improvement Playbook — Mục lục

**Cập nhật:** 2026-07-12

---

## Bắt đầu nhanh

| Doc | Dùng khi |
|-----|----------|
| **[00_playbook_sop.md](00_playbook_sop.md)** | **Viết/cập nhật playbook — dán prompt §8 vào chat mới** |
| [01_priority_roadmap.md](01_priority_roadmap.md) | Chọn Priority P0–P4, owner doc |
| `01_runtime_stability/01_wait_test_stall_fix.md` | Mẫu compact chuẩn |
| [99_quality_audit.md](99_quality_audit.md) | Compliance checklist + NEEDS_RECHECK line drift |

---

## 1. Purpose

| | `docs/aoi-analysis/` | `docs/aoi-improvement/` |
|---|---------------------|-------------------------|
| Vai trò | Phân tích, evidence | SOP sửa, test, rollback |
| Câu hỏi | Bug ở đâu? | **Sửa gì, G/F line nào, diff trước/sau, test/rollback** |
| Giá trị | — | **Tại sao sửa, trước/sau thế nào, lợi ích production** |

Playbook **trích** analysis — không bịa line, không duplicate pipeline internals (`13`–`19`).

**Rule bắt buộc (2026-07-12):** Mỗi file improvement (workstream `01`–`07`) phải có 5 section **Improvement Purpose / Before Improvement / After Improvement / Improvement Value / Before–After Summary**. Chi tiết §3.1.

---

## 2. Folder Structure

```text
docs/aoi-improvement/
  00_index.md
  00_playbook_sop.md       ← SOP + prompt chat sau
  01_priority_roadmap.md
  01_runtime_stability/ … 07_testing_and_release/
  99_quality_audit.md      ← audit compliance + follow-up
```

---

## 3. Format file improvement (compact — mặc định)

Chi tiết đầy đủ → **[00_playbook_sop.md §3](00_playbook_sop.md)**

```text
Header (4 dòng: file, workstream, luật, note line drift)
  ↓
Improvement Purpose / Before / After / Value / Summary   ← bắt buộc (rule 2026-07-12)
  ↓
Bảng tổng: ID | Vấn đề | G/F | Anchor | Thao tác | Test  (+ ship order)
  ↓
Block diff từng Fix: TRƯỚC/SAU + đúng/sai chỗ + rollback 1 câu
  ↓
Smoke checklist + Ref
```

### 3.1 Improvement Value sections (bắt buộc)

Mỗi file playbook (workstream `01`–`07`) phải trả lời 4 câu hỏi quản lý:

| Section | Trả lời |
|---------|---------|
| **Improvement Purpose** | Sửa cái này để làm gì? (1–3 câu) |
| **Before Improvement** | Trước sửa hệ thống gặp vấn đề gì? (symptom, evidence ngắn) |
| **After Improvement** | Sau sửa behavior mới, recover, operator/log/MES thay đổi gì? |
| **Improvement Value** | Bảng 5 area: Production / Operator / MES / Maintainability / Debug — ghi N/A nếu không liên quan |
| **Before / After Summary** | Bảng 4 aspect: Runtime / Error handling / Operator / Production risk |

Đặt **sau header**, **trước** bảng tổng / diff. Không thay thế Patch Guidance / Verification / Rollback đã có.

Mẫu tham chiếu: `01_runtime_stability/01_wait_test_stall_fix.md`

---

## 4. Fix ID prefix

| Prefix | Nhóm |
|--------|------|
| `RT-` | Runtime |
| `SFIS-` | MES |
| `SN-` | SN validation |
| `SENSOR-` | Dispatch sensor |
| `DEP-` | Deployment |
| `AI-` | Cambrian/OCR |
| `PIPE-*-` | Pipeline gate |
| `TEST-` | Release |

Line lấy từ analysis / grep `sky.py`. Block phải cụ thể (`go_run3 Button_check`), không ghi chung chung.

---

## 5. Link analysis

| Area | Docs |
|------|------|
| Runtime | `04_state_machine.md`, `05_runtime_flow.md` |
| Dispatch | `08_model_dispatch.md` |
| Risks | `10_risks_and_bugs.md` |
| Refactor / test | `11_refactor_plan.md` |
| External | `07_camera_io_sfis.md` |
| Pipelines | `13`–`19` |

| Workstream | Analysis chính |
|------------|----------------|
| `01_runtime_stability` | `04`, `05`, `09`, `10` §Orchestration |
| `02_sfis_mes_integrity` | `07` §4, `10` Phase 4–10 |
| `03_sensor_dispatch` | `08`, `11` Month 3 |
| `04_dependency_deployment` | `07` §1, §11 |
| `05_ai_ocr_runtime` | `07` §5–6, `10` Phase 11 |
| `06_pipeline_safety` | `13`–`19` |
| `07_testing_and_release` | `11` §9–10 |
