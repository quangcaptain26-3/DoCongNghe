# Quality Audit — AOI Improvement Per-Fix Detail Pass

**Ngày audit:** 2026-07-12  
**Phạm vi:** Toàn bộ `docs/aoi-improvement/` (25 file `.md`)  
**Tiêu chí PASS:** Mỗi Fix ID có Code Location · Current Problem · Before Improvement · Required Change · After Improvement · Improvement Value · Verification · Rollback · Suggested Implementation Window — **ở cấp từng Fix ID**, không chỉ ở đầu file.

---

## 1. Audit Summary

| Metric | Count |
|--------|------:|
| Tổng file `.md` trong folder | 25 |
| File playbook/workstream được rà soát | 19 |
| File meta/process (không chấm per-fix) | 6 (`00_*`, `01_priority_roadmap`, `99_*`) |
| Tổng Fix ID / issue block đã kiểm tra | **~118** (unique IDs across workstreams; một số ID xuất hiện cross-ref ở nhiều file) |
| Fix ID đạt đủ 9 tiêu chí per-fix | **~118** |
| Fix ID được cập nhật trong đợt audit này | **~118** |
| Fix ID cần re-check line trong `sky.py` | **12** (xem §3) |

**Kết quả:** Mọi file playbook workstream (01–07) đã có section **Per-Fix Detail** hoặc **## Fix &lt;ID&gt;** với đủ 9 mục bắt buộc. File-level summaries (Improvement Purpose, Before/After, Value) được **giữ nguyên** — không thay thế per-fix detail.

**Định dạng header:**
- File `01_runtime_stability`, `02_sfis_mes_integrity`, `07_testing_and_release`: dùng `## Fix <ID> — <title>` (chuẩn đầy đủ).
- File `03`–`06`: dùng `## Per-Fix Detail` + `### <ID>` hoặc `### <ID> — title` với cùng 9 subsection — nội dung đạt, header level khác một bậc.

---

## 2. Per-file Compliance Checklist

Cột: **Loc** = per-fix code location · **Prob** = current problem · **Patch** = suggested patch location · **B/A** = before/after per fix · **Val** = improvement value · **Ver** = verification per fix · **Rb** = rollback per fix · **TL** = timeline per fix

| File | Fix IDs reviewed | Loc | Prob | Patch | B/A | Val | Ver | Rb | TL | Status |
|------|----------------:|-----|------|-------|-----|-----|-----|----|----|--------|
| `01_priority_roadmap.md` | Roadmap (no per-fix IDs) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ (link matrix) | ✓ (link SOP) | ✓ | PASS |
| `01_runtime_stability/01_wait_test_stall_fix.md` | 6 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | UPDATED |
| `01_runtime_stability/02_ui_thread_and_stop_sop.md` | 5 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | UPDATED |
| `02_sfis_mes_integrity/01_sfis_upload_helper.md` | 4 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | UPDATED |
| `02_sfis_mes_integrity/02_sn_reset_and_validation.md` | 6 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | UPDATED |
| `02_sfis_mes_integrity/03_error_code_standard.md` | 4 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | UPDATED |
| `03_sensor_dispatch/01_sensor_mode_guard.md` | 5 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | UPDATED |
| `03_sensor_dispatch/02_shared_dispatcher_design.md` | 7 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | UPDATED |
| `04_dependency_deployment/01_deployment_bundle_checklist.md` | 14 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | UPDATED |
| `04_dependency_deployment/02_external_imports_and_assets.md` | 6 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | UPDATED |
| `04_dependency_deployment/03_startup_preflight_check.md` | 4 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | UPDATED |
| `05_ai_ocr_runtime/01_cambrian_guard_policy.md` | 4 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | UPDATED |
| `05_ai_ocr_runtime/02_paddleocr_cache_sop.md` | 5 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | UPDATED |
| `05_ai_ocr_runtime/03_cambrian_space_fail_policy.md` | 5 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | UPDATED |
| `06_pipeline_safety/01_mr6500_sfis_off_fix.md` | 3 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | UPDATED |
| `06_pipeline_safety/02_sky_step6_aggregate_gate.md` | 3 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | UPDATED |
| `06_pipeline_safety/03_hh4k_exception_stall_fix.md` | 3 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | UPDATED |
| `06_pipeline_safety/04_cisco_ocr_timeout_fix.md` | 4 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | UPDATED |
| `06_pipeline_safety/05_wp_nanook_route_fail_fix.md` | 5 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | UPDATED |
| `06_pipeline_safety/06_button_check_sfis_fix.md` | 6 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | UPDATED |
| `07_testing_and_release/01_regression_test_matrix.md` | 6 TEST-MAP + 40 matrix rows | ✓ | ✓ | N/A | ✓ | ✓ | ✓ | ✓ (link) | ✓ | UPDATED |
| `07_testing_and_release/02_release_sop.md` | Process | N/A | ✓ | N/A | ✓ | ✓ | ✓ | ✓ | ✓ | PASS |
| `07_testing_and_release/03_rollback_sop.md` | 5 RB-G groups | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | UPDATED |

---

## 3. Fix IDs Needing Line Re-check

| Fix ID | File | Reason | What to re-check in sky.py |
|--------|------|--------|---------------------------|
| SFIS-001 | `01_wait_test_stall_fix.md` vs `01_sfis_upload_helper.md` | Analysis G1357 vs grep L1224 | Ctrl+F `data_upload(self.SN_8P` trong Cisco step2 fail — tin anchor text |
| SN-004 / PIPE-B04 | `02_sn_reset`, `06_button_check` | Repo corrupt L725 `input_dialof.shan)` | Sửa syntax `go_run1` trước patch validate scan |
| SENSOR-001–004 | `03_sensor_dispatch/*` | `go_run2` L795–832 là line analysis | Ctrl+F `def go_run2`, `time.sleep(5)`, `show_image_MR6500(self.shan)` |
| SENSOR-D01–D06 | `02_shared_dispatcher_design.md` | Registry insert point analysis-based | Ctrl+F `def go_run2`, `def go_run3` trước patch |
| SFIS-004 | `01_sfis_upload_helper.md` | Pass upload sites beyond L2951 | Ctrl+F `data_upload(self.thissn, self.data)` không có `error=` |
| EC-003 | `03_error_code_standard.md` | Helper chưa tồn tại trong repo | Verify sau khi SFIS-002 ship |
| DEP-004 | `02_external_imports` | `model_and_90` dict syntax | Ctrl+F `model_and_90={` — confirm key quoting |
| PIPE-C02 | `04_cisco_ocr_timeout_fix.md` | OCR timeout block G3614–3636 | Ctrl+F `for ttime in range(60)` trong Cisco vision |
| PIPE-N01 | `05_wp_nanook_route_fail_fix.md` | Nanook OCR G4810 | Ctrl+F `nanook_ocr.ocr` STEP 3 |
| AI-O03 | `02_paddleocr_cache_sop.md` | SKY STEP 3 L2731 vs L2864 drift | Ctrl+F `PaddleOCR` trong `show_image_SKY` STEP 3 |
| RT-002A | `01_wait_test_stall_fix.md` | HH4K elif insert L1029–1030 | Ctrl+F `show_image_HH4K(self.shan1)` trong `go_run3` |
| DEP-P02 | `03_startup_preflight_check.md` | Preflight insert đầu `startprogram` | Ctrl+F sau sensor/Cambrian guard blocks |

**Quy tắc:** Không bịa line — tin Ctrl+F anchor hơn line number khi drift.

---

## 4. Common Gaps Fixed

| Gap (trước audit) | Cách xử lý |
|-------------------|------------|
| Before/After chỉ ở đầu file, chưa có theo Fix ID | Thêm **Per-Fix Detail** / **## Fix** với Before Improvement + After Improvement riêng từng ID |
| Test chưa map Fix ID | Mỗi Fix ID có bảng Verification; matrix 07 có TEST-MAP blocks |
| Rollback còn chung chung | Mỗi Fix ID có Rollback riêng; `03_rollback_sop.md` có RB-G1–G5 map Fix IDs |
| Timeline chỉ ở cấp folder | Mỗi Fix ID có **Suggested Implementation Window** |
| Patch location chưa rõ hơn current lines | Thêm cột **Suggested patch location** tách khỏi **Current lines** |
| Required Change quá chung | Bổ sung pseudo-code, short/medium-term, diff reference |
| File 07 process docs thiếu per-fix structure | TEST-MAP + RB-G groups với đủ 9 mục |

---

## 5. Recommended Implementation Order

| Window | Fix IDs | Reason |
|--------|---------|--------|
| **Week 1** | AI-001, RT-001, RT-003, SN-003a/b, SN-002, SN-005, SENSOR-001/002/003A/B, DEP-001/002, AI-G02, PIPE-B01/B02, PIPE-C01/C02, PIPE-H01, PIPE-W01, DEP-P02 | P0 crash/stall/MES wrong SN/one-line safety |
| **Week 1–2** | SFIS-001, SN-001, SN-004, EC-001 (MES liaison), RT-002A | SFIS helper pattern, SN validation, HH4K stall |
| **Week 2** | SENSOR-004, DEP-P01/P03, DEP-B01–B14 checklist, PIPE-B04, UI-SOP-001 | Preflight/deployment, optional warnings, scan validate |
| **Week 3–4** | AI-O01, AI-G04, E-01/E-07 (if early), OCR cache smoke | OCR cache, UI responsiveness |
| **Month 1** | PIPE-M01–M03, PIPE-S01–S03, PIPE-C03/C04, PIPE-W02/W03, PIPE-N01/N02, PIPE-H02/H03, RT-002B, AI-002–005 | Pipeline-specific fixes cần regression nhiều model |
| **Month 2** | SFIS-002/003/004, EC-002/003, E-03, E-06, E-08, AI-O02–O05 | Helper chung, error code dict, OCR singleton, startprogram finally |
| **Month 2+** | SENSOR-D01–D06, worker thread Q2 | Shared dispatcher, state machine — không big-bang |

---

## Ref

`00_index.md` · `00_playbook_sop.md` · `01_priority_roadmap.md` · `07_testing_and_release/`
