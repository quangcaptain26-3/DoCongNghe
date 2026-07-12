# Phân phối model

Chỉ bản đồ cấp điều phối. Chi tiết thị giác hoãn sang Giai đoạn 4.

## Chủ sở hữu phân phối

- **Chính:** `go_run3` (L834–1911) — chế độ thủ công (`is_sensor=False`) và mọi luồng nhiều bước
- **Ngoại lệ:** `go_run2` (L795–832) — chế độ sensor chạy thị giác trực tiếp, **hardcode** thành `show_image_MR6500`

## Bảng phân phối

| select_model | Nhánh (L#) | Bước | Lần chụp | Hàm pipeline | Hộp thoại QMessageBox | Cờ step | SFIS trong go_run3 | Xử lý fail | Ghi chú/Rủi ro |
|--------------|------------|-----:|---------:|--------------|----------------------|---------|-------------------|------------|----------------|
| MR6500 | L839 | 1 | 1× `get_image` | `show_image_MR6500` | Không | Không | Không | Trong thị giác | Chỉ chế độ thủ công; sensor dùng go_run2 |
| ipex_check | L860 | 1 | 1× | inline `camera_check_ipex` | QInputDialog tùy chọn nếu barcode fail | Không | Không | **go_run3** L926–949 Đạt/Không đạt | Import đã comment L37; không SFIS |
| HH4K | L971 | 4 | 4× | `show_image_HH4K` ×4 | BƯỚC 1–4 | step1–4 | Không | Exception: **không wait_test**; fail thị giác vẫn nối chuỗi | Treo nếu exception trước stepN=True L993; chi tiết `15_hh4k_pipeline.md` |
| SKY | L1034 | 6 | 6× | `show_image_SKY` ×6 | BƯỚC 1–6 | step1–6 | **Có** fail L1150+ (`BDFA0`) | go_run3 + upload đạt thị giác BƯỚC 6 | Chỉ thủ công; Cambrian không phải YOLO; chi tiết `14_sky_pipeline.md` |
| SKY_4G | L1034 | 6 | 6× | `show_image_SKY` ×6 | Giống | step1–6 | Giống | Giống | Dùng file điểm `SKY_4G_*.json` |
| C1000-8FP-E-2G-L | L1292 | 2 | 2× | `show_image_C1000_8FP_E_2G_L` ×2 | BƯỚC 1–2 | step1–2 | **Có** fail `BDFA01` L1357/L1385 | go_run3 + đạt thị giác L4205 | Hàm chung; `SN_8P`; chi tiết `16_cisco_pipeline.md` |
| C1000-8P-2G-L | L1292 | 2 | 2× | giống | giống | step1–2 | Có | giống | Đường OCR 4-barcode C1000 |
| C1000-8T-2G-L | L1292 | 2 | 2× | giống | giống | step1–2 | Có | giống | Nhánh chung |
| C1000-8FP-2G-L | L1292 | 2 | 2× | giống | giống | step1–2 | Có | giống | Nhánh chung |
| C1000-8P-E-2G-L | L1292 | 2 | 2× | giống | giống | step1–2 | Có | giống | Nhánh chung |
| C1000-8T-E-2G-L | L1292 | 2 | 2× | giống | giống | step1–2 | Có | giống | Nhánh chung |
| C1200-8FP-2G | L1292 | 2 | 2× | giống | giống | step1–2 | Có | giống | Chỉ OCR1+MfgDate; bỏ qua ocr3 |
| C1200-8P-E-2G | L1292 | 2 | 2× | giống | giống | step1–2 | Có | giống | Nhánh chung |
| C1200-8T-E-2G | L1292 | 2 | 2× | giống | giống | step1–2 | Có | giống | Nhánh chung |
| C1300-8P-E-2G | L1292 | 2 | 2× | giống | giống | step1–2 | Có | giống | Biến thể 5-barcode L3705 |
| C1300-8T-E-2G | L1292 | 2 | 2× | giống | giống | step1–2 | Có | giống | Nhánh chung |
| C1300-8FP-2G | L1292 | 2 | 2× | giống | giống | step1–2 | Có | giống | Nhánh chung |
| Button_check | L1400 | 1 | 1× | `show_image_Button_check` | "Flip model" L1405 | step1 cổng đạt | **Có** fail L1440+ (`BDFA01`, **lỗi `thissn`**) | go_run3 | **Duy nhất** quét thật trong go_run1 L737; chỉ thủ công; chi tiết `19_button_check_pipeline.md` |
| WP_check | L1456 | 6 | 6× | `show_image_WP` ×6 | BƯỚC 1–6 | step1–6 | **Có** fail `BDFA01` L1546+ | go_run3 + đạt thị giác BƯỚC 6 L4724 | `thissn`; SN DataMatrix; chi tiết `17_wp_pipeline.md` |
| C9105AXW_E | L1456 | 6 | 6× | giống | giống | step1–6 | Có | giống | pyzbar `$SN:` BƯỚC 1; JSON bước 2–6 chung |
| Nanook | L1683 | 6 | 6× | `show_image_Nanook` ×6 | SETP 1–6 (lỗi chính tả UI) | step1–6 | **Có** fail `BDFA01` L1774+ | go_run3 + đạt L5136 | PaddleOCR tại nhánh L1685; BƯỚC 2/3 cổng theo đã thực thi; chi tiết `18_nanook_pipeline.md` |

## Ngoại lệ chế độ sensor

Khi `is_sensor=True`:

```text
startprogram → go_run1 → go_run2 (KHÔNG go_run3)
go_run2 L829: show_image_MR6500(self.shan)  # luôn
```

| Kỳ vọng | Thực tế |
|---------|---------|
| Phân phối theo `select_model` | Luôn pipeline MR6500 |
| Model nhiều bước | Không hỗ trợ trên nhánh sensor |

**Ảnh hưởng:** SKY, Cisco, HH4K, v.v. không chạy đúng với chế độ sensor. SKY cần chế độ thủ công (`is_sensor=False`) + `go_run3`.

### show_image_SKY_yolo (nhánh chết)

- Định nghĩa L3109; dùng `yolov5_inference` thay Cambrian
- **Không có điểm gọi** — sản xuất chỉ dùng `show_image_SKY`
- Sẽ fail nếu bật: import `predict_change` đã comment L7

## Đặt lại Đạt/Không đạt và wait_test (Điều phối)

| Model | wait_test=True đặt khi |
|-------|------------------------|
| MR6500 (go_run3) | Luôn L859 sau thị giác |
| MR6500 (go_run2) | Sau thị giác L830 |
| ipex_check | Luôn L969 (kể cả khi exception) |
| HH4K | bước 4 xong L1017; người dùng xác nhận thoát L1021+; hủy nhãn trong thị giác L2523 |
| SKY+ | bước 6 đạt L1133; nhánh fail/thoát L1154+ |
| Cisco | bước 2 đạt L1342; bước 1/2 fail L1362/L1392; người dùng thoát L1366/L1397 |
| Button_check | bước 1 đạt L1423; fail L1448 |
| WP/Nanook | bước 6 đạt L1530/1759; bước 1–6 fail L1550+; người dùng thoát |

## Vị trí tải lên SFIS (Tầng điều phối)

| Vị trí | Model | Biến SN | Mã lỗi (mẫu) |
|--------|-------|---------|--------------|
| Handler fail go_run3 | SKY | `thissn` | **BDFA0** L1150+ |
| Handler fail go_run3 | Button_check | **`thissn` (đáng lẽ scaninfo)** | **BDFA01** L1441 — upload đạt dùng `scaninfo` L4313 |
| Handler fail go_run3 | WP_check, C9105AXW_E, Nanook | `thissn` | **BDFA01** L1546+ / L1775+ |
| Handler fail go_run3 | Cisco | `SN_8P` | **BDFA01** L1358, L1385 |
| show_image_SKY đạt | SKY BƯỚC 6 | `thissn` | Không tham số error L3083 |
| show_image_WP đạt | WP BƯỚC 6 | `thissn` | Không tham số error L4724 |
| show_image_Nanook đạt | Nanook BƯỚC 6 | `thissn` | Không tham số error L5136 (chỉ khi Cambrian bật) |
| show_image_Button_check đạt | Button_check BƯỚC 1 | `scaninfo` | Không tham số error L4313 |
| show_image_C1000 đạt | Cisco BƯỚC 2 | `SN_8P` | Không tham số error L4205 |

Khối fail+upload trùng lặp giữa các nhánh SKY/Nanook/Cisco/WP (rủi ro bảo trì).

## Model không xác định

Không có `else` cuối trong `go_run3`. `select_model` không có trong danh sách + chế độ thủ công → hàm trả về, **`wait_test` vẫn False** → vòng lặp startprogram treo.

## Tóm tắt quét go_run1

| select_model | Hành vi go_run1 |
|--------------|-----------------|
| `Button_check` | Vòng lặp `QInputDialog` → `scaninfo`, `scan_sta=True`; hủy → `wait_test`+`stop_program` |
| Tất cả khác | "Bypass Scan" → `scan_sta=True` ngay |

## Đề xuất đi sâu tiếp theo

1. **Bên ngoài / gói triển khai** — `07_externals.md`
2. **Kế hoạch tái cấu trúc** — `11_refactor_plan.md`
3. **Nhánh chết** — `show_image` L1913, `show_image_SKY_yolo` L3109
