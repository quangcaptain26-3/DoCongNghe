# Ma Trận Kiểm Thử Hồi Quy

**Luồng công việc:** `07_testing_and_release`  
**Nguồn:** `11_refactor_plan.md` §9, `10_risks_and_bugs.md`, pipeline `13`–`19`, `docs/aoi-improvement/`

**Môi trường:** Trạm clone line — cùng lớp phần cứng, endpoint SFIS/Cambrian test, recipe gần production.

**Nhịp chạy:**

| Bộ | Khi nào | Dòng |
|-------|------|------|
| **Smoke** | Hàng tuần + trước mỗi release | Ưu tiên P0 |
| **Full** | Release hàng tháng + sau bundle patch lớn | Mọi dòng |
| **Spot theo model** | Chỉ patch một model | P0 của model đó + P0 dùng chung |

---

## Improvement Purpose

Mục tiêu của cải tiến này là cung cấp ma trận nghiệm thu formal cho mọi cải tiến — mỗi fix ID có test case, priority P0–P2, và setup/kỳ vọng rõ. Trước đây fix có thể triển khai nhưng thiếu regression matrix thống nhất.

## Before Improvement

Trước cải tiến, verification chủ yếu ad-hoc: engineer test tay scenario quen thuộc, không có bảng map fix → test case, không có smoke subset 19 P0 bắt buộc trước deploy. Rủi ro regression lọt production; khó audit "fix X đã test chưa"; release không có gate rõ.

## After Improvement

Sau cải tiến, ma trận 40+ dòng map khu vực → setup → kỳ vọng → priority → related fix; smoke subset 19 P0 bắt buộc; mock guide SFIS/OCR/Cambrian; ký duyệt QA/MES/operator/engineering. Mỗi release chạy matrix trên clone; P0 fail = block release.

## Improvement Value

| Area                        | Value |
| --------------------------- | ----- |
| Production stability        | Giảm regression lọt lên line nhờ gate P0 |
| Operator experience         | Giám sát 1 ca không treo là tiêu chí sign-off |
| MES/SFIS integrity          | Audit 10 pass + 10 fail SN là tiêu chí MES |
| Maintainability             | Traceability fix ID ↔ test case |
| Debugging / troubleshooting | Fail test → map ngay owner doc và fix ID |

## Before / After Summary

| Aspect           | Before | After |
| ---------------- | ------ | ----- |
| Runtime behavior | N/A (test doc) | Verify behavior per fix after patch |
| Error handling   | Ad-hoc verify | Matrix covers fail/exception paths |
| Operator impact  | Không formal sign-off | Operator 1-ca monitor in checklist |
| Production risk  | Deploy without full smoke | 19 P0 smoke blocks bad release |

---

## Per-Fix Test Mapping

Mỗi test case trong ma trận map tới Fix ID chính. Chi tiết setup/expected per-fix nằm trong `## Verification` của owner playbook.

## Fix TEST-MAP-001 — Unknown model (RT-001)

### Verification

| Test ID | Setup | Action | Expected result |
|---|---|---|---|
| T-RT-001 / Matrix row 1 | Manual mode; fake `model` in JSON | Start | Log error; `wait_test=True`; no Stop needed |
| Smoke #1 | Same | Start | Pass |

### Suggested Implementation Window

| Window | Reason |
|---|---|
| Week 1 | P0 smoke before every release |

---

## Fix TEST-MAP-002 — Sensor guard (SENSOR-002)

### Verification

| Test ID | Setup | Action | Expected result |
|---|---|---|---|
| T-SENSOR-002 / Matrix row 3 | `is_sensor=True`, SKY recipe | Start | Blocked; Start enabled |
| Smoke #3 | Same | Start | Pass |

---

## Fix TEST-MAP-003 — SFIS exception (SFIS-001)

### Verification

| Test ID | Setup | Action | Expected result |
|---|---|---|---|
| T-SFIS-001 / Matrix row 18 | Mock `data_upload` raise | Fail cycle Cisco step2 | `wait_test=True`; loop continues |
| Smoke #18 | Same | Fail cycle | Pass |

---

## Fix TEST-MAP-004 — Button_check MES SN (SN-001 / PIPE-B01)

### Verification

| Test ID | Setup | Action | Expected result |
|---|---|---|---|
| T-SN-001 / Matrix row 8 | SKY then Button_check fail | Fail Button_check | MES fail SN = `scaninfo` |
| Smoke #8, #19 | Scan + pass/fail | Cycle | Pass |

---

## Fix TEST-MAP-005 — SKY STEP 6 aggregate (PIPE-S01)

### Verification

| Test ID | Setup | Action | Expected result |
|---|---|---|---|
| T-S02 / Matrix row 16 | Cambrian pass + aggregate fail flags | STEP 6 | Fail; no SFIS pass upload |
| Smoke #16 | Same | STEP 6 | Pass |

---

## Fix TEST-MAP-006 — HH4K missing JSON (RT-002A / PIPE-H01)

### Verification

| Test ID | Setup | Action | Expected result |
|---|---|---|---|
| T-RT-002A / Matrix row 14–15 | Rename `point/step1.json` or sample | Start HH4K | Fail UI; `wait_test=True` |
| Smoke #15 | Missing point OR sample | Start | Pass |

---

*Remaining matrix rows map similarly: column "Sửa liên quan" → owner playbook `## Fix <ID>` Verification table.*

---

## Cách dùng

1. Sao chép bảng sang phiếu chạy test (thêm cột: Ngày, Người test, Pass/Fail, Ghi chú).
2. Đánh dấu từng dòng sau khi patch trong **Related fix** đã triển khai (hoặc N/A trước sửa).
3. **Chặn release** nếu bất kỳ dòng P0 nào fail trên clone.
4. Lỗi P1/P2 → chấp nhận rủi ro có ký engineering hoặc hoãn patch.

---

## Ma trận

| Khu vực | Test case | Setup | Kỳ vọng | Ưu tiên | Sửa liên quan |
|------|-----------|-------|----------|----------|-------------|
| Orchestration | Model không biết | Manual mode; model JSON `model` = chuỗi giả không có trong go_run3 | Log lỗi; `wait_test=True`; prompt chu kỳ tiếp; không cần Stop | P0 | B-01, `01_wait_test_stall_fix` |
| Sensor | Sensor MR6500 | `is_sensor=True`, recipe MR6500, IoCard + profile OK | IO trigger → grab → vision MR6500; `wait_test` reset; bộ đếm Pass/Fail | P0 | `01_mr6500_sfis_off_fix`, sensor guard |
| Sensor | Chặn sensor non-MR6500 | `is_sensor=True`, recipe SKY (hoặc WP) | **Sau guard:** Start bị chặn có thông báo; Start vẫn bật. **Trước guard:** ghi chạy sai MR6500 — fail audit | P0 | `01_sensor_mode_guard` |
| SFIS | SFIS tắt MR6500 | `sfis_choose=False`, MR6500, decode hợp lệ | Không crash; thông báo Fail/offline có cấu trúc; count cập nhật | P0 | A-04, `01_mr6500_sfis_off_fix` |
| Cambrian | Cambrian tắt SKY | `is_cambrian:false`, SKY manual | **Sau guard:** Start bị chặn. **Nếu debug bypass:** banner; không MES pass | P0 | A-05, `01_cambrian_guard_policy` |
| Cambrian | Cambrian tắt WP | `is_cambrian:false`, WP_check | Giống SKY — chặn Start hoặc bypass có kiểm soát | P0 | `01_cambrian_guard_policy` |
| Cambrian | Cambrian tắt Button_check | `is_cambrian:false`, Button_check | Tương tự — không AttributeError STEP 1 | P0 | `01_cambrian_guard_policy` |
| MES | Button_check fail sau SKY | Chạy SKY pass/fail (set `thissn`); rồi quét Button_check + fail | SN MES fail = **`scaninfo` hiện tại**, không phải `thissn` SKY | P0 | A-03, `06_button_check_sfis_fix` |
| Scan | Button_check quét rỗng | OK dialog rỗng/khoảng trắng | Nhắc lại hoặc lỗi; không `scan_sta`; không route SFIS | P0 | C-05, `06_button_check_sfis_fix` |
| UX | Button_check từ chối Flip | Từ chối "Flip model" không xác nhận exit | `wait_test=True`; DUT tiếp không cần Stop | P0 | B-04, `06_button_check_sfis_fix` |
| Cisco | Timeout OCR Cisco | Đường OCR chậm/chặn hoặc mock delay >30s STEP 1 | `step1=False`; fail có cấu trúc; `wait_test=True`; không IndexError | P0 | `04_cisco_ocr_timeout_fix` |
| MES | SN_8P cũ Cisco | DUT1 pass (set SN_8P); DUT2 fail STEP 1 trước khi set SN | Bỏ qua upload fail hoặc SN rỗng; **không** PVN DUT1 | P0 | C-06, `04_cisco_ocr_timeout_fix` |
| WP | WP route fail không repair | Mock `check_route` trả `"0"` không tag repair | `check_result_OK=False`; bỏ Cambrian; `step1=False`; không pass cũ | P0 | `05_wp_nanook_route_fail_fix` |
| Nanook | OCR rỗng Nanook STEP 3 | `source/Nanook_ocr.jpg` trống/hỏng hoặc không ROI chữ | `step3=False`; không IndexError; chu kỳ phục hồi | P0 | `05_wp_nanook_route_fail_fix` |
| HH4K | HH4K thiếu point JSON | Đổi tên `point/step1.json` | UI Fail; `wait_test=True`; Start chu kỳ tiếp | P0 | B-03, `03_hh4k_exception_stall_fix` |
| HH4K | HH4K thiếu sample | Đổi tên `sample/step1.jpg` | Tương tự — không treo | P0 | `03_hh4k_exception_stall_fix`, D-02 |
| SKY | SKY STEP 6 aggregate fail | DUT Cambrian STEP 6 pass nhưng `sncheck`/`modelcheck`/`checksn` false | **Fail**; không upload SFIS pass; `step6=False` | P0 | A-06, `02_sky_step6_aggregate_gate` |
| Assets | Thiếu `source/` | Xóa `source/` trước Cisco hoặc SKY STEP 3 | Preflight fail hoặc tự tạo; không crash im lặng | P0 | D-01, `03_startup_preflight_check` |
| Assets | Thiếu `point/*.json` | Đổi tên ví dụ `point/SKY_barcode.json` | Preflight hoặc UI Fail; không treo `wait_test` | P0 | D-02, preflight |
| SFIS | Exception upload SFIS | Mock `data_upload` raise khi fail Cisco step2 (hoặc WP step3) | Log lỗi; **`wait_test=True`** trong finally | P0 | B-02, `01_sfis_upload_helper` |
| UI/Stop | Stop khi sensor sleep | Sensor trigger; bấm Stop trong 5s sau trigger | **Trước sửa:** trễ tới 5s. **Sau E-01:** thoát &lt;1s | P1 | E-01, `02_ui_thread_and_stop_sop` |
| OCR perf | Smoke cache PaddleOCR | Nanook 3 DUT liên tiếp (hoặc SKY 2× STEP 3) | DUT 2–3 khởi động OCR nhanh rõ hơn DUT 1 | P1 | E-03, `02_paddleocr_cache_sop` |
| MES | SN pass Button_check | Quét hợp lệ + pass | SN MES pass = `scaninfo` | P0 | `06_button_check_sfis_fix` |
| Scan | Hủy quét Button_check | Hủy QInputDialog | `stop_program`; Start bật lại | P1 | `19_button_check_pipeline` |
| SFIS | WP fail upload không "None" | WP STEP 1 decode fail | Không bản ghi MES literal `"None"` | P0 | `05_wp_nanook_route_fail_fix` |
| SFIS | Nanook route fail | Barcode OK, route FAIL | `step1=False`; không Cambrian pass giả | P1 | `05_wp_nanook_route_fail_fix` |
| Cambrian | Exception cambrian_space | Ép lỗi inference/vẽ giữa bước | Trả `"Fail"`; stepN False; không None | P1 | E-02, `03_cambrian_space_fail_policy` |
| Button_check | Pass rỗng ROI ximian | JSON không nhãn `ximian` | Fail; không SFIS pass | P1 | `06_button_check_sfis_fix` |
| Button_check | check_result_OK cũ | SKY route pass rồi Button_check route fail | Không Cambrian trên Button_check | P1 | `06_button_check_sfis_fix` |
| MR6500 | Thiếu sample liaohao | SFIS trả liaohao không có `sample/{liaohao}.jpg` | Fail có cấu trúc; không chỉ except | P1 | `01_mr6500_sfis_off_fix` |
| Cisco | Cold start ocr_8P_result | Test Cisco đầu sau launch app | Không AttributeError trước callback | P1 | C-03, `04_cisco_ocr_timeout_fix` |
| Cisco | Runthread không busy loop | OCR pass STEP 1 | Một emit; không spin trên `[]` | P2 | D-04 |
| Nanook | KeyError Nanook STEP 5 | Chuỗi model OCR không có trong `nanook_model_tan` | `step5=False`; không crash | P1 | `05_wp_nanook_route_fail_fix` |
| Nanook | Barcode Nanook ≠3 | Sai số barcode STEP 1 | Fail; không upload `"None"` | P1 | `05_wp_nanook_route_fail_fix` |
| SKY | SKY pass golden đủ bước | DUT tốt 6 bước, SFIS bật | UI Pass; SFIS pass STEP 6; bộ đếm OK | P1 | Hồi quy `14_sky_pipeline` |
| SKY | SKY step fail BDFA0 | STEP 3 fail | go_run3 upload fail `BDFA0`; `wait_test=True` | P1 | `03_error_code_standard` |
| HH4K | HH4K vision fail vẫn nối | So sánh step 1 fail | Có thể nối STEP 2–4 (đã biết); kết thúc có `wait_test` | P2 | Chính sách `03_hh4k_exception_stall_fix` |
| HH4K | Hủy nhãn HH4K step 4 | Hủy dialog nhãn | `stop_program`; Start bật lại | P1 | `15_hh4k_pipeline` |
| Cisco | MES pass Cisco STEP 2 | Pass đủ STEP 1+2 | MES pass `SN_8P`; `wait_test` | P1 | `16_cisco_pipeline` |
| WP | WP STEP 6 pass | Pass đủ 6 bước | MES pass `thissn` | P1 | `17_wp_pipeline` |
| Nanook | Nanook STEP 6 pass Cambrian bật | Pass đủ | MES pass; bộ đếm Pass local | P1 | `18_nanook_pipeline` |
| Nanook | Cambrian tắt STEP 6 | `is_cambrian:false` + debug | Không step6 pass im lặng không count/MES trừ khi có cờ debug | P1 | `01_cambrian_guard_policy` |
| Preflight | Preflight chặn config lỗi | camera_id không hợp lệ hoặc thiếu point | Start bị chặn; thông báo liệt kê lỗi | P1 | `03_startup_preflight_check` |
| Preflight | Preflight pass bundle tốt | Trạm đầy đủ | Start tiếp tục | P1 | `01_deployment_bundle_checklist` |
| IO | Import IoCard sensor | `is_sensor=True`, import đã sửa | Start; init IO OK | P0 | A-01 |
| ipex | Một chu kỳ ipex_check | Model ipex, import đã sửa | Không NameError; Pass/Fail | P2 | A-02 |
| UI | except startprogram Start vẫn bật | Ép exception sau khi tắt Start | Nút Start bật lại | P1 | B-06 |
| MES | SKY manual SFIS tắt | `sfis_choose=False`, SKY | Pass/fail local; không gọi SFIS | P1 | `01_sfis_upload_helper` |
| MR6500 | MR6500 manual pass | `is_sensor=False`, MR6500 | Vision go_run3; `wait_test=True` | P1 | `13_mr6500_pipeline` |
| Count | Yield baseline không đổi | 50 DUT cùng recipe trước/sau patch | Lệch Total/Pass/Fail trong ngưỡng đã thỏa | P1 | Chấp nhận `02_release_sop` |

---

## Tập con smoke (tối thiểu trước deploy production)

Chạy **19** dòng P0 này trong một phiên:

1. Unknown model  
2. Sensor MR6500  
3. Sensor non-MR6500 blocked  
4. SFIS off MR6500  
5. Cambrian off SKY  
6. Cambrian off WP  
7. Cambrian off Button_check  
8. Button_check fail after prior SKY  
9. Button_check empty scan  
10. Button_check Flip reject  
11. Cisco OCR timeout  
12. Cisco stale SN_8P  
13. WP route fail no repair  
14. Nanook OCR empty  
15. HH4K missing point/sample (một trong hai)  
16. SKY STEP 6 aggregate fail  
17. Missing source OR point JSON  
18. SFIS upload exception  
19. Button_check pass SN  

Thêm **cache PaddleOCR** và **Stop khi sleep** khi patch Tháng 2 ra.

---

## Dữ liệu test & mock

| Mock | Cách |
|------|-----|
| SFIS upload throw | Patch tạm hoặc test double trên `data_upload` |
| SFIS route fail | SN test trong route QA SFIS |
| Timeout OCR | Đổi tên `source/8P/ocr1.jpg` giữa poll hoặc throttle CPU |
| Cambrian tắt | Model JSON `is_cambrian: false` chỉ trên clone |
| Unknown model | Bản sao model JSON với trường `model` sai |

**Không chạy test phá hoại trên line production chính.**

---

## Verification / Rollback / Timeline (compliance note)

- **Verification:** Chính file này là ma trận verification tổng — mỗi dòng map với Fix ID trong cột "Sửa liên quan"; test chi tiết per-fix nằm trong section `## Verification` của từng playbook workstream.
- **Rollback:** Không có code — quy trình rollback tại `03_rollback_sop.md`. Nếu ma trận phát hiện regression, dòng fail map trực tiếp về owner doc + Fix ID cần revert.
- **Implementation Window:** Smoke 19 P0 chạy trước **mỗi** release (Week 1 trở đi); ma trận full theo nhịp monthly; dòng E-01/E-03 thêm khi patch Month 2 ra.

---

## Ký duyệt

| Vai trò | Tiêu chí |
|------|----------|
| QA / Engineer | Mọi smoke P0 pass trên clone |
| MES | Mẫu audit 10 pass + 10 fail SN |
| Operator | Giám sát 1 ca không treo |
| Engineering lead | Checklist release đầy đủ (`02_release_sop.md`) |

---

## Tham chiếu

`11_refactor_plan.md` §9–10, `01_priority_roadmap.md`, mọi playbook sửa trong `docs/aoi-improvement/*`
