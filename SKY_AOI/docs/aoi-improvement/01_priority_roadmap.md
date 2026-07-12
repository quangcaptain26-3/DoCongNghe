# Roadmap Ưu tiên — AOI Improvement Playbook

Thứ tự triển khai dựa trên `11_refactor_plan.md`, `10_risks_and_bugs.md`, `07_camera_io_sfis.md`, `08_model_dispatch.md`, `12_project_memory.md`.

**Quy tắc ship:** Hoàn thành Priority 0 trên line clone trước khi chạm Priority 2+. Mỗi patch tuân format `00_index.md` §3: **Improvement Value sections** + **Patch Guidance** (đi tới, sửa cái nào, code trước–sau).

---

## Improvement Purpose

Roadmap này sắp xếp thứ tự triển khai cải tiến P0→P4 — ưu tiên crash/stall trước, MES integrity tiếp theo, dispatch/deployment/UX sau. Giúp team chọn đúng owner doc và first action theo rủi ro production.

## Before Improvement

Trước cải tiến, các fix rải rác trong analysis (`10_risks_and_bugs.md`) không có thứ tự ship rõ — dễ patch UX trước khi fix stall P0, hoặc deploy MES change trước SN validation. Khó trả lời "tuần này ship gì" cho quản lý/operator.

## After Improvement

Sau cải tiến, bảng priority map issue → line evidence → owner doc → first action; phase Week 1–2 P0, Week 2–3 P1, Month 2 P4, Month 3 P2 dispatcher. Mỗi item link playbook có Before/After/Value. Team ship theo phase; rollback per-item.

## Improvement Value

| Area                        | Value |
| --------------------------- | ----- |
| Production stability        | P0 stall/crash ship trước — giảm downtime line |
| Operator experience         | P4 UX deferred đúng lúc — không trade stability |
| MES/SFIS integrity          | P1 gom SN/upload/error code — audit traceability |
| Maintainability             | Owner doc per workstream; trace fix ID |
| Debugging / troubleshooting | Line evidence column — biết mở file nào |

## Before / After Summary

| Aspect           | Before | After |
| ---------------- | ------ | ----- |
| Runtime behavior | Ad-hoc fix order | P0→P4 phased ship |
| Error handling   | Risk patch wrong priority | Stall/MES before dispatch refactor |
| Operator impact  | Unclear what's deploying when | Phase smoke per priority |
| Production risk  | High if P1 before P0 | Controlled rollout with rollback SOP |

---

## Bảng ưu tiên tổng hợp

| Priority | Improvement area | Main issue | Key line evidence | Owner doc | First action |
|----------|------------------|------------|-------------------|-----------|--------------|
| **P0** | Dependency — IoCard import | Import comment nhưng vẫn gọi → `NameError` khi Start sensor | L29 `#from ioCardNew import IoCard`; L673 `IoCard(...)` | `04_dependency_deployment/02_external_imports_and_assets.md` | Bỏ comment import; verify `ioCardNew` trên PATH triển khai |
| **P0** | Runtime — unknown model stall | `go_run3` không có `else` cuối → `wait_test` không reset | L834–1911 (không `else`); `08_model_dispatch.md` | `01_runtime_stability/01_wait_test_stall_fix.md` | Thêm `else`: log model + `wait_test=True` |
| **P0** | Runtime — wait_test fail path | Exception/thoát bất thường không reset `wait_test` → line treo | HH4K L993 (chỉ `if step1==True`); `04_state_machine.md` | `01_runtime_stability/01_wait_test_stall_fix.md` | Bổ sung `elif stepN==False` + vision `finally` |
| **P0** | Pipeline — Button_check Flip reject | Reject Flip không set `wait_test` → operator kẹt | L1450–1454 (`QMessageBox` reject 65536) | `01_runtime_stability/01_wait_test_stall_fix.md` | Reject Flip: `wait_test=True` hoặc re-prompt |
| **P0** | SFIS — fail upload exception stall | `data_upload` raise bỏ qua `wait_test=True` phía sau | Cisco L1357–1362; WP L1546+; Nanook L1774+ | `02_sfis_mes_integrity/01_sfis_upload_helper.md` | `try: upload` / `finally: wait_test=True` trên mọi fail block |
| **P1** | SFIS — Button_check fail SN sai | Fail upload dùng `thissn` (stale); pass dùng `scaninfo` | Fail L1441 `data_upload(self.thissn)`; pass L4313 `scaninfo` | `06_pipeline_safety/06_button_check_sfis_fix.md` | Đổi L1441 → `data_upload(self.scaninfo, ...)` |
| **P1** | SFIS — Cisco SN_8P stale | `SN_8P` từ DUT trước dùng cho fail upload | Set L3935/L4055; fail L1358/L1385 `self.SN_8P` | `02_sfis_mes_integrity/02_sn_reset_and_validation.md` | Reset `SN_8P=""` đầu chu kỳ Cisco; guard upload |
| **P1** | SFIS — WP/Nanook upload `"None"` | Reset `thissn="None"` → fail MES gắn literal None | WP reset L1457; Nanook reset L1684; fail L1668/L1897 | `06_pipeline_safety/05_wp_nanook_route_fail_fix.md` | Skip upload khi SN empty/None; reset `thissn=""` |
| **P1** | SN — empty scan accepted | `go_run1` chấp nhận chuỗi rỗng → route/upload SN rỗng | L770–775 `QInputDialog` không validate | `02_sfis_mes_integrity/02_sn_reset_and_validation.md` | Reject empty/whitespace; re-prompt hoặc lỗi |
| **P1** | SFIS — error code inconsistency | SKY fail `BDFA0`; các model khác `BDFA01` | SKY L1150 `BDFA0`; Button_check L1442 `BDFA01` | `02_sfis_mes_integrity/03_error_code_standard.md` | Xác nhận spec MES; chuẩn hóa bảng mã theo model |
| **P2** | Dispatch — sensor luôn MR6500 | `go_run2` hardcode `show_image_MR6500`, bỏ qua `select_model` | L829 `show_image_MR6500(self.shan)` | `03_sensor_dispatch/01_sensor_mode_guard.md` | Audit recipe `is_sensor=True`; document constraint |
| **P2** | Dispatch — sensor không gọi go_run3 | Sensor path bỏ qua dispatcher manual | `startprogram` L693–697; `go_run2` L795–832 | `03_sensor_dispatch/02_shared_dispatcher_design.md` | Thiết kế `dispatch_vision(select_model, image)` dùng chung |
| **P2** | Dispatch — Button_check sensor mismatch | Scan chạy (`go_run1` L737) nhưng vision là MR6500 | L829 + Button_check chỉ `go_run3` L1400 | `03_sensor_dispatch/01_sensor_mode_guard.md` | Enforce `is_sensor=False` cho Button_check hoặc fix dispatch |
| **P3** | Deployment — missing `source/` | `cv2.imwrite("source/...")` crash nếu thư mục không tồn tại | Nhiều pipeline; không `makedirs` trong `__init__` | `04_dependency_deployment/03_startup_preflight_check.md` | `os.makedirs("source", "source/8P", exist_ok=True)` tại startup |
| **P3** | Deployment — missing point/sample | Thiếu JSON/JPG → exception, `stepN` không set → stall | HH4K L2149+; MR6500 L2038; `07` §10 | `04_dependency_deployment/03_startup_preflight_check.md` | Pre-flight `os.path.exists` + Fail UI + `wait_test=True` |
| **P3** | Pipeline — MR6500 SFIS off crash | Gọi `mysfis` không guard `sfis_choose` | L2032–2035 `get_sfis_SN`/`get_sfis_90` | `06_pipeline_safety/01_mr6500_sfis_off_fix.md` | Guard `sfis_choose`; offline liaohao path |
| **P3** | AI — Cambrian off crash | `is_cambrian:false` → không `self.client`; vẫn gọi inference | L290–293 init; `get_inference_result` L630–647 | `05_ai_ocr_runtime/01_cambrian_guard_policy.md` | Guard mọi `get_inference_result`; stub hoặc Fail UI rõ |
| **P4** | Runtime — UI thread blocking loop | `startprogram` `while True` trên slot nút Start | L687 | `01_runtime_stability/02_ui_thread_and_stop_sop.md` | Document constraint; Q2: worker thread (không Month 1) |
| **P4** | Runtime — sensor sleep freeze | `time.sleep(5)` trên UI thread trong `go_run2` | L813 | `01_runtime_stability/02_ui_thread_and_stop_sop.md` | `QTimer` hoặc poll `stop_program` trong wait |
| **P4** | AI — PaddleOCR UI block | Khởi tạo PaddleOCR mỗi DUT/bước trên UI thread | SKY L2864–2865; Nanook L1685–1686 | `05_ai_ocr_runtime/02_paddleocr_cache_sop.md` | Singleton/lazy init một lần mỗi session |
| **P4** | Runtime — Stop delayed | Stop không thoát nhanh trong sleep/modal/blocking call | L813; `go_run2` L796; `09_threading_and_ui.md` | `01_runtime_stability/02_ui_thread_and_stop_sop.md` | Poll `stop_program` trong delay; giảm blocking trên UI thread |

---

## Priority 0 — Stop production crash / stall

*Ship trước mọi thứ. Mục tiêu: không `NameError`, không line treo vì `wait_test`, không stall khi SFIS exception.*

| # | Item | Evidence | Owner doc |
|---|------|----------|-----------|
| 1 | IoCard import commented but used | L29, L673 | `04_dependency_deployment/02_external_imports_and_assets.md` |
| 2 | Unknown model — no final `else` in `go_run3` | L834–1911 | `01_runtime_stability/01_wait_test_stall_fix.md` |
| 3 | `wait_test` fail path (HH4K exception, generic exit) | L993; `show_image_HH4K` except L2525–2527 | `01_runtime_stability/01_wait_test_stall_fix.md` |
| 4 | Button_check Flip reject stall | L1450–1454 | `01_runtime_stability/01_wait_test_stall_fix.md` |
| 5 | SFIS fail upload skip `wait_test` | Cisco L1357–1362; WP L1546+; Nanook L1774+ | `02_sfis_mes_integrity/01_sfis_upload_helper.md` |

**Smoke P0 (blocker release):** sensor Start không NameError; unknown model recover; mock SFIS fail → loop tiếp; reject Flip → DUT tiếp không cần Stop.

---

## Priority 1 — MES/SFIS data integrity

*Month 1. Không đổi thuật toán vision — chỉ sửa SN upload và validation.*

| # | Item | Evidence | Owner doc |
|---|------|----------|-----------|
| 1 | Button_check fail upload wrong SN | Fail L1441 vs pass L4313 | `06_pipeline_safety/06_button_check_sfis_fix.md` |
| 2 | Cisco `SN_8P` stale on fail upload | Set L3935/L4055; fail L1358/L1385 | `02_sfis_mes_integrity/02_sn_reset_and_validation.md` |
| 3 | WP/Nanook upload `None` | WP L1457; Nanook L1684; fail L1668+ | `06_pipeline_safety/05_wp_nanook_route_fail_fix.md` |
| 4 | Empty scan accepted | `go_run1` L770–775 | `02_sfis_mes_integrity/02_sn_reset_and_validation.md` |
| 5 | Error code `BDFA0` vs `BDFA01` | SKY L1150 vs Button_check L1442 | `02_sfis_mes_integrity/03_error_code_standard.md` |

**Smoke P1:** SKY fail → Button_check fail — MES SN = scan thực tế; audit 10 fail record trên clone.

---

## Priority 2 — Wrong pipeline prevention

*Month 3 / sau P0–P1 ổn định. Rủi ro sai quy trình khi `is_sensor=True` + model non-MR6500.*

| # | Item | Evidence | Owner doc |
|---|------|----------|-----------|
| 1 | Sensor mode always MR6500 | `go_run2` L829 | `03_sensor_dispatch/01_sensor_mode_guard.md` |
| 2 | Sensor path never calls `go_run3` | L693–697, L795–832 | `03_sensor_dispatch/02_shared_dispatcher_design.md` |
| 3 | Button_check sensor: scan OK, vision MR6500 | L737 + L829 + L1400 | `03_sensor_dispatch/01_sensor_mode_guard.md` |

**First action P2:** Audit toàn bộ recipe production có `is_sensor=True` — xác nhận chỉ MR6500 hoặc chặn Start với MessageBox.

---

## Priority 3 — Runtime/deployment hardening

*Song song cuối Month 1. Tránh crash first-run và offline test.*

| # | Item | Evidence | Owner doc |
|---|------|----------|-----------|
| 1 | Missing `source/` folder | `07_camera_io_sfis.md` §1; nhiều `imwrite` | `04_dependency_deployment/03_startup_preflight_check.md` |
| 2 | Missing point/sample assets | HH4K, MR6500, `07` §10 | `04_dependency_deployment/03_startup_preflight_check.md` |
| 3 | MR6500 SFIS off crash | L2032–2035 | `06_pipeline_safety/01_mr6500_sfis_off_fix.md` |
| 4 | Cambrian disabled but client still used | L290–293; L630–647 | `05_ai_ocr_runtime/01_cambrian_guard_policy.md` |

**Deliverable P3:** `04_dependency_deployment/01_deployment_bundle_checklist.md` — manifest theo model.

---

## Priority 4 — Performance/operator UX

*Month 2. Không blocker crash/MES — cải thiện phản hồi UI.*

| # | Item | Evidence | Owner doc |
|---|------|----------|-----------|
| 1 | `startprogram` `while True` on UI thread | L687 | `01_runtime_stability/02_ui_thread_and_stop_sop.md` |
| 2 | `time.sleep(5)` in sensor loop | L813 | `01_runtime_stability/02_ui_thread_and_stop_sop.md` |
| 3 | PaddleOCR init on UI thread | SKY L2864–2865; Nanook L1685–1686 | `05_ai_ocr_runtime/02_paddleocr_cache_sop.md` |
| 4 | Stop delayed during blocking calls | L813, L796; modal dialogs | `01_runtime_stability/02_ui_thread_and_stop_sop.md` |
| 5 | `cambrian_space` return `None` on except | L2643–2645 | `05_ai_ocr_runtime/03_cambrian_space_fail_policy.md` |

**Exit P4:** Stop phản hồi &lt; 1s trong sensor wait; Nanook DUT 2–3 khởi động OCR nhanh hơn.

---

## Thứ tự thực thi đề xuất

```text
Week 1–2   P0 (crash + stall)
Week 2–3   P1 (MES/SN) — chồng một phần P0 item 5 nếu chưa xong
Week 3–4   P3 deployment guards + P1 còn lại
Month 2    P4 UX/runtime
Month 3    P2 dispatcher (F-01 trong 11_refactor_plan.md)
```

**Rollback chung:** Tag `sky.py` + config trước mỗi phase; revert **từng PR/item** — chi tiết `07_testing_and_release/03_rollback_sop.md`.

**Regression tối thiểu:** `07_testing_and_release/01_regression_test_matrix.md` — smoke 10 hàng sau mỗi release P0/P1.
