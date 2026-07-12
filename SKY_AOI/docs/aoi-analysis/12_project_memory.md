# Bộ nhớ Dự án

Tham chiếu ngắn cho các phase phân tích tiếp theo. Chi tiết nằm ở tài liệu khác — không trùng lặp tại đây.

## Ý tưởng Cốt lõi

Ứng dụng AOI PyQt5 một file (`sky.py`, ~5.571 dòng). Class `Demo` điều phối camera Basler, IO sensor PCI-1756 tùy chọn, kiểm tra vision, và MES SFIS tùy chọn — hành vi sản phẩm chọn bằng chuỗi recipe `select_model`.

## Luồng Runtime Chính

```text
Start → startprogram (luồng UI while True)
  → go_run1 (scan/bypass, scan_sta=True)
  → [sensor] go_run2 → grab → show_image_MR6500 (hardcode)
  → [manual] go_run3 → dispatch theo select_model → show_image_*
  → wait_test=True → DUT tiếp theo
Stop → stop_program → break vòng lặp → cleanup IO/camera
```

## Class Quan trọng

`Demo`, `Uihand`, `ReadDataMatrixCode`, `Runthread`

## Hàm Quan trọng

| Hàm | Ghi chú Phase 2 |
|----------|--------------|
| `startprogram` | Vô hiệu Start; sensor→test2, manual→test3 |
| `go_run1` | Chỉ Button_check scan; cancel→stop_program |
| `go_run2` | Poll sensor; sleep(5); **luôn MR6500** |
| `go_run3` | Dispatcher chính L834–1911; không nhánh else |
| `stopprogram` | Chỉ cờ; không bật lại Start |

## Cờ Quan trọng

`wait_test` cổng chu kỳ tiếp; `scan_sta` nối scan→vision; `stop_program` thoát vòng lặp; `step1–6` chuỗi test nhiều bước.

**Rủi ro treo:** Exception HH4K trước `stepN=True` hoặc model không xác định → `wait_test` không reset. Fail vision HH4K **không** để stepN False (khác SKY).

## Dispatch Model

Xem `08_model_dispatch.md`. Chế độ sensor bỏ qua go_run3 hoàn toàn.

## Phát hiện Phase 2

- Sensor vs manual: khác biệt duy nhất là test2 (go_run2) vs test3 (go_run3) sau scan
- go_run2 L829 hardcode MR6500 — lệch nghiêm trọng cho non-MR6500 + is_sensor
- Pass/Fail: ipex_check trong go_run3; hầu hết khác trong show_image_* + fail handler go_run3
- Upload SFIS fail trùng trong go_run3 (SKY, Cisco, WP, Nanook, Button_check)
- stopprogram/closeEvent: đặt cờ + cleanup; Stop trễ trong sleep(5)/modal
- Handler except startprogram có thể để Start bị vô hiệu

## Rủi ro Đã biết (Hàng đầu)

1. Import IoCard bị comment, dùng L673
2. go_run2 hardcode MR6500 L829
3. Treo wait_test (fail HH4K, model không xác định)
4. Chặn luồng UI + sleep(5) L813
5. Thiếu module bên ngoài (basler_my, sfisapi, …)

## Dependency Thiếu

`UI`, `basler_my`, `sfisapi`, `ioCardNew`, `ipex_check_yolo`, `yolov5`, `config.json`, model JSON.

## Phát hiện Phase 4 — MR6500

- Decode ISN → SN SFIS/mã 90 (liaohao) → hash+diff vs `sample/{liaohao}.jpg`; ngưỡng 0.85/30 hardcode
- Không `data_upload`; chỉ `get_sfis_SN`/`get_sfis_90` — không guard `sfis_choose`
- Caller luôn đặt `wait_test=True`; MR6500 không đặt stepN
- Chi tiết: `13_mr6500_pipeline.md`

## Phát hiện Phase 5 — SKY

- 6 bước manual: Cambrian + pyzbar + PaddleOCR (STEP 3); KHÔNG YOLO trên đường active
- `show_image_SKY_yolo` chết L3109; SFIS fail `BDFA0` trong go_run3; pass upload STEP 6 L3083
- Nghiêm trọng: STEP 6 Cambrian pass có thể SFIS-upload dù cờ tổng hợp fail L3060–3096
- Chế độ sensor không đến SKY — chi tiết `14_sky_pipeline.md`

## Phát hiện Phase 6 — HH4K

- 4 bước manual: mean PIL + màu HSV vs `sample/stepN.jpg`; pHash `HH4K_compare` không dùng
- `stepN=True` nghĩa bước đã chạy, không phải pass — chuỗi tiếp dù vision fail
- Treo: exception trong `show_image_HH4K` trước `stepN=True`; không `elif step1==False` trong go_run3 L993
- Không SFIS; nhãn bước 4 `QInputDialog` trong vision; hủy nhãn → `stop_program`
- Chi tiết: `15_hh4k_pipeline.md`

## Phát hiện Phase 7 — Cisco

- 12 model dùng chung `show_image_C1000_8FP_E_2G_L` qua go_run3 L1292 (tên hàm gây nhầm)
- 2 bước manual: STEP 1 pyzbar+OCR(QThread)+SFIS kiểm 90+Cambrian; STEP 2 Cambrian+OCR topdate
- `SN_8P=barcode_list[-1]` (PVN); SFIS fail `BDFA01` go_run3; pass upload STEP 2 L4205
- Có `elif step1/step2==False` + `wait_test` (tốt hơn HH4K); rủi ro except SFIS step2 fail L1357
- Chi tiết: `16_cisco_pipeline.md`

## Phát hiện Phase 8 — WP

- `WP_check` + `C9105AXW_E` dùng chung pipeline manual 6 bước `show_image_WP` (go_run3 L1456)
- STEP 1: DataMatrix vs pyzbar `$SN:`; SFIS `check_route`/`repair_SN`; Cambrian trên ROI barcode_point
- STEPS 2–6: Cambrian — `model_point` (step2) + hardcode `WP_check_step3–6.json`
- `step1–6` pass-gated; `thissn` reset `"None"`; SFIS pass STEP 6 L4724; fail `BDFA01` go_run3
- Chi tiết: `17_wp_pipeline.md`

## Phát hiện Phase 9 — Nanook

- 6 bước manual: barcode×3 + route SFIS + Cambrian (1); lưu trữ (2); OCR model (3); Cambrian vít (4); OCR CLEI + map tan/clei + Cambrian (5); Cambrian + SFIS pass (6)
- PaddleOCR tạo mỗi chu kỳ L1685 (chặn UI); tái dùng STEP 3/5; `thissn`/`thistan` từ pyzbar
- Cổng hỗn hợp: STEP 2/3 executed-gated; còn lại pass-gated; Cambrian tắt auto-pass bỏ STEP 6 MES
- Fail `BDFA01` go_run3; pass upload L5136; chi tiết `18_nanook_pipeline.md`

## Phát hiện Phase 10 — Button_check

- **Duy nhất** model có scan thật trong `go_run1` (QInputDialog → `scaninfo`); còn lại bypass
- 1 bước manual: scan SN → prompt Flip → Cambrian trên ROI `ximian`; **không** barcode/OCR/DataMatrix/YOLO
- SFIS: route/repair + pass upload dùng **scaninfo**; fail upload go_run3 dùng **`thissn`** (không đặt) — lỗi nghiêm trọng
- `step1` pass-gated (Cambrian + SFIS upload OK); fail handler có try/except trên SFIS; từ chối Flip không thoát → treo
- Chế độ sensor: scan chạy nhưng vision là MR6500 — cần chế độ manual
- Fail `BDFA01`; WIP theo comment L4; chi tiết `19_button_check_pipeline.md`

## Phát hiện Phase 11 — Ranh giới Bên ngoài

- **Camera:** `mycamera` discovery khi init; `ekkoshan` mỗi chu kỳ Start; chỉ đóng khi Stop/closeEvent; `change_camera` stub
- **IO:** Import `IoCard` comment L29, dùng L673; profile `profile/pci1756.xml`; chế độ sensor → go_run2 → luôn MR6500
- **SFIS:** cổng bởi `sfis_choose`; MR6500 **không guard** `get_sfis_SN`/`get_sfis_90`; route/repair/upload trên SKY/WP/Nanook/Button_check/Cisco
- **Cambrian:** `SampleClientV2` khi `is_cambrian:true`; `get_inference_result` + `cambrian_space`; tắt → crash trừ bypass Nanook
- **PaddleOCR:** SKY STEP 3, Cisco (QThread+sync), Nanook (init mỗi chu kỳ chặn UI); không HH4K/Button_check/MR6500
- **YOLO/ipex:** import comment; crash runtime ipex; YOLO chết (`show_image_SKY_yolo`)
- **Asset:** hardcode `point/`, `sample/`, ghi được `source/`; chi tiết `07_camera_io_sfis.md`

## Phát hiện Phase 12 — Kế hoạch Refactor

- **Chiến lược:** Ổn định trước — không viết lại toàn bộ; Tháng 1 an toàn → Tháng 2 runtime → Tháng 3 chuẩn hóa → Q2–Q4 modular hóa
- **Ưu tiên Tháng 1:** sửa treo `wait_test`, SFIS SN/upload, guard MR6500 `sfis_choose`, sửa import, Button_check `scaninfo`, elif fail HH4K
- **Chủ đề quý:** Q1 an toàn | Q2 worker/helper SFIS | Q3 registry/dispatcher | Q4 test harness
- **Mẫu báo cáo quản lý:** §10 trong `11_refactor_plan.md`; tùy chọn `20_improvement_report_vi.md`

## Module Đề xuất Tiếp theo

**Báo cáo cải tiến điều hành** (`20_improvement_report_vi.md`) — tiếng Việt, ít kỹ thuật, cho quản lý.

## Chỉ mục Tài liệu

00–12, 13–19. Bộ phân tích đầy đủ; deliverable tùy chọn `20_improvement_report_vi.md`.
