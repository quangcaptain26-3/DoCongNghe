# Tổng quan pipeline thị giác

Giai đoạn 4+ đi sâu từng hàm `show_image_*`. Các pipeline khác TBD.

---

## show_image_MR6500

- **Được dùng bởi:** `select_model=="MR6500"` (thủ công qua `go_run3` L858); **mọi** lần chụp chế độ sensor qua `go_run2` L829 (hardcode, bỏ qua công thức)
- **Đầu vào:** `image_numpy` (BGR từ `ekkoshan.get_image()`); `self.barcode_point`, `self.model_point`; `self.mysfis`; `self.pciture_save`, `self.img_time`, `todaytime`; hardcode `sample/{liaohao}.jpg`
- **Kiểm tra chính:** Giải mã ISN DataMatrix → tra cứu SFIS SN + mã 90 → so sánh ROI mẫu (pHash + chênh lệch trung bình PIL)
- **Barcode/DataMatrix:** ROI nhãn `ISN` từ `barcode_point`; `pylibdmtx` qua `ReadDataMatrixCode` (timeout 500ms)
- **SFIS:** Chỉ `get_sfis_SN`, `get_sfis_90` — **không có `data_upload`** trong pipeline này
- **Hash/mẫu:** `pHash` + `cmHash` (≥0.85) VÀ `ImageStat.Stat.mean` (≤30); mẫu từ `sample/{liaohao}.jpg` ROI CHECK
- **Đầu ra:** Lưu JPG có chú thích; tableWidget so sánh 2 cột; `lineEdit_8` (mbsn), `lineEdit_9` (số đo hoặc "Fail"); `resultcolor`; `updatecount`
- **Ảnh hưởng trạng thái:** Không bên trong hàm — caller đặt `wait_test=True` (go_run2 L830, go_run3 L859); không có `stepN`
- **Rủi ro chính:** SFIS gọi không có guard `sfis_choose`; thiếu nhãn ROI; parse chuỗi SFIS mong manh; ngưỡng/đường dẫn hardcode; hardcode go_run2 cho công thức sensor không phải MR6500
- **Kiểm thử đề xuất:** Giải mã fail; SFIS tắt; thiếu JPG mẫu; hash sát ngưỡng 0.84/0.86; chênh lệch trung bình 29/31; khung camera rỗng; model sai `is_sensor` + không phải MR6500

**Chi tiết:** `13_mr6500_pipeline.md`

---

## show_image_SKY

- **Được dùng bởi:** `select_model` SKY / SKY_4G qua `go_run3` L1034–1131 (chỉ chế độ thủ công); **không** chế độ sensor (`go_run2` → MR6500)
- **Đầu vào:** `image_numpy`, `stepname` BƯỚC 1–6; hardcode `point/SKY_*.json` hoặc `SKY_4G_*.json`; dict `sky_clei`; Cambrian `self.client`; `self.mysfis` tùy chọn
- **Kiểm tra chính:** Chuỗi 6 bước — barcode (pyzbar) → route SFIS → phân loại ROI Cambrian → đối chiếu OCR (BƯỚC 3) → lưu trữ (BƯỚC 5) → Cambrian cuối + tổng hợp cờ
- **AI/OCR:** **Cambrian** (`get_inference_result` + `cambrian_space`); **PaddleOCR** chỉ BƯỚC 3; **YOLO không dùng** trên nhánh hoạt động (`show_image_SKY_yolo` chết L3109)
- **SFIS:** `check_route`/`repair_SN` trong thị giác; đạt `data_upload` BƯỚC 6 L3083; không đạt `data_upload error=BDFA0` chỉ trong **go_run3**
- **Đầu ra:** `_pass/_fail.jpg` mỗi bước; `UI_show`; `lineEdit_8/9`; BƯỚC 6 `resultcolor`+`updatecount`; đặt `step1–step6`
- **Ảnh hưởng trạng thái:** Không có `wait_test` — go_run3 đặt khi đạt/không đạt; các bước cổng chuỗi QMessageBox
- **Rủi ro chính:** BƯỚC 6 đạt giả nếu Cambrian OK nhưng cờ OCR/barcode false L3060–3096; cambrian_space except trả None; JSON điểm hardcode; xử lý fail SFIS trùng lặp
- **Kiểm thử đề xuất:** Đủ 6 bước đạt; barcode bước 1 fail; OCR BƯỚC 3 lệch; SFIS tắt/bật; BƯỚC 6 tổng hợp fail khi Cambrian đạt
- **Chi tiết:** `14_sky_pipeline.md`

---

## show_image_HH4K

- **Được dùng bởi:** `select_model=="HH4K"` qua `go_run3` L971–1033 (chỉ chế độ thủ công); **không** chế độ sensor (`go_run2` → MR6500)
- **Đầu vào:** `image_numpy`; hardcode `point/step1–4.json`, `sample/step1–4.jpg`; ngưỡng `pil_spec`/`color_spec` từ `self.HH4K` (JSON model đầy đủ L239)
- **Kiểm tra chính:** Chuỗi 4 bước — `HH4K_compare` mỗi ROI: chênh lệch trung bình PIL + dải màu HSV trung tâm; pHash/cmHash tính nhưng **không dùng** trong đạt/không đạt
- **AI/OCR:** Không; không Cambrian/YOLO
- **SFIS:** **Không** trong thị giác hay nhánh HH4K go_run3
- **Đầu ra:** `_pass/_fail.jpg` mỗi bước (bước 1–3); bước 4 lưu qua dialog nhãn; `resultcolor`+`updatecount` mỗi bước; đặt `step1–4=True` sau thực thi (**không** cổng theo đạt — khác SKY)
- **Ảnh hưởng trạng thái:** Không có `wait_test` trên đường dẫn thường — `go_run3` L1017; hủy nhãn đặt `wait_test`+`stop_program` L2523–2524 bên trong thị giác
- **Rủi ro chính:** Exception trước `stepN=True` → treo `wait_test` (không có `elif step1==False` trong go_run3); fail thị giác không dừng chuỗi; lưu bước 4 đã comment L2434–2437
- **Kiểm thử đề xuất:** Exception trên JSON bước 1; fail thị giác vẫn nối bước 2; hủy nhãn; đủ 4 bước đạt
- **Chi tiết:** `15_hh4k_pipeline.md`

---

## show_image_C1000_8FP_E_2G_L

- **Được dùng bởi:** 12 model Cisco (`C1000`/`C1200`/`C1300`) qua nhánh `go_run3` chung L1292–1340; **chỉ chế độ thủ công** (sensor → MR6500 L829)
- **Đầu vào:** `image_numpy`, `stepname` BƯỚC 1/2; `barcode_point` (BƯỚC 1), `model_point` (BƯỚC 2); module `check_ocr_*`/`check_label_*`; Cambrian `self.client`; `self.mysfis` tùy chọn
- **Kiểm tra chính:** BƯỚC 1 — barcode pyzbar + PaddleOCR (QThread + đồng bộ) + xác minh model mã 90 SFIS tùy chọn + Cambrian trên ROI `warn`; BƯỚC 2 — Cambrian warn + OCR `topdate` 8 chữ số tùy chọn
- **Barcode/SN:** `pyzbar` trên ROI `ocr` cuối; `SN_8P=barcode_list[-1]` L3935/L4055 (PVN); không có `scaninfo`
- **OCR/QThread:** `Runthread` ×1 (C1200/C1300) hoặc ×2 (C1000) trên `source/8P/ocr*.jpg`; PaddleOCR đồng bộ trên ocr3/topdate; poll 30s L3747
- **SFIS:** `get_sfis_90` kiểm tra model BƯỚC 1; đạt `data_upload` BƯỚC 2 L4205; không đạt `BDFA01` trong **go_run3** L1358/L1385
- **Đầu ra:** JPG có chú thích, `UI_show`, `lineEdit_8` (`SN_8P`); Đạt `resultcolor`+`updatecount` chỉ BƯỚC 2; đặt `step1`/`step2` cổng theo đạt (khác HH4K)
- **Ảnh hưởng trạng thái:** `wait_test` chỉ đặt trong go_run3; handler fail rõ `elif step1/step2==False` với `wait_test`
- **Rủi ro chính:** `ocr_8P_result` chưa khởi tạo; Runthread emit rỗng L5528; SN_8P cũ khi upload fail; exception SFIS bước 2 fail có thể bỏ qua `wait_test` L1362
- **Kiểm thử đề xuất:** Đủ đạt; barcode bước 1 fail; OCR timeout; SFIS tắt; lệch chế độ sensor
- **Chi tiết:** `16_cisco_pipeline.md`

---

## show_image_WP

- **Được dùng bởi:** `WP_check` / `C9105AXW_E` qua `go_run3` L1456–1681 (chỉ thủ công; sensor → MR6500 L829)
- **Đầu vào:** `image_numpy`, `stepname` BƯỚC 1–6; `barcode_point` (BƯỚC 1), `model_point` (BƯỚC 2), hardcode `point/WP_check_step3–6.json`; Cambrian `self.client`
- **Kiểm tra chính:** Cambrian 6 bước trên ROI WP_*; BƯỚC 1 thêm giải mã SN + SFIS `check_route`/`repair_SN`
- **Barcode/SN:** `WP_check` = DataMatrix `WP_QR` → `thissn`; `C9105AXW_E` = pyzbar regex `$SN:`; **`scaninfo` không dùng**; đặt lại `thissn="None"` L1457
- **OCR/QThread:** Không
- **SFIS:** Route/repair BƯỚC 1; đạt `data_upload` BƯỚC 6 L4724; không đạt `BDFA01` go_run3 L1546+
- **Đầu ra:** Lưu mỗi bước; Đạt `resultcolor`+`updatecount` BƯỚC 6; `step1–6` **cổng theo đạt**
- **Ảnh hưởng trạng thái:** `wait_test` trong go_run3; cả sáu bước có handler `elif stepN==False`
- **Rủi ro chính:** `check_result_OK` chưa đặt khi route fail; upload fail với `thissn="None"`; C9105AXW_E `barcodes[0]`; exception SFIS bước 2–6 có thể treo
- **Kiểm thử đề xuất:** Đủ đạt; SN fail; route SFIS fail; C9105AXW_E so với WP_check BƯỚC 1
- **Chi tiết:** `17_wp_pipeline.md`

---

## show_image_Nanook

- **Được dùng bởi:** `select_model=="Nanook"` qua `go_run3` L1683–1910 (chỉ thủ công; sensor → MR6500 L829)
- **Đầu vào:** `image_numpy`, `stepname` BƯỚC 1–6; `barcode_point` (BƯỚC 1); hardcode `point/Nanook_model1–4.json`; `self.nanook_ocr` (tạo L1685); `nanook_model_tan`/`nanook_model_clei` L109–110
- **Kiểm tra chính:** BƯỚC 1 pyzbar×3 + route SFIS + Cambrian; BƯỚC 2 chỉ lưu trữ; BƯỚC 3 OCR model; BƯỚC 4 Cambrian vít; BƯỚC 5 OCR CLEI + map TAN/CLEI + Cambrian; BƯỚC 6 Cambrian + Đạt/SFIS
- **Barcode/SN:** `thissn=barcode_list[1]`, `thistan=barcode_list[2]`; đặt lại `thissn="None"` L1684; **`scaninfo` không dùng**
- **OCR:** PaddleOCR `lang="en"` một lần mỗi chu kỳ L1685; dùng BƯỚC 3 + BƯỚC 5 (đồng bộ luồng UI)
- **SFIS:** Route/repair BƯỚC 1; upload đạt BƯỚC 6 L5136; không đạt `BDFA01` go_run3 L1775+
- **Đầu ra:** Lưu mỗi bước; Đạt `resultcolor`+`updatecount` BƯỚC 6 (chỉ khi Cambrian bật); cổng bước hỗn hợp
- **Ảnh hưởng trạng thái:** `wait_test` trong go_run3; cả sáu `elif stepN==False`; BƯỚC 2/3 **cổng theo đã thực thi**; các bước khác chủ yếu cổng theo đạt
- **Rủi ro chính:** Khởi tạo OCR chặn UI; OCR IndexError; BƯỚC 3 luôn True; upload fail `"None"`; Cambrian tắt BƯỚC 6 bỏ qua MES; KeyError model không xác định
- **Kiểm thử đề xuất:** Đủ đạt; barcode fail; OCR rỗng; TAN/CLEI lệch; Cambrian tắt; lệch sensor
- **Chi tiết:** `18_nanook_pipeline.md`

---

## show_image_Button_check

- **Được dùng bởi:** `select_model=="Button_check"` qua `go_run3` L1400–1454 (chỉ thủ công); quét trong `go_run1` L737 (model duy nhất có quét thật); **không** chế độ sensor (`go_run2` → MR6500 L829)
- **Đầu vào:** `image_numpy`; `scaninfo` từ QInputDialog go_run1; hardcode `point/Button_check_model.json` (ROI `ximian`); Cambrian `self.client`; `self.mysfis` tùy chọn
- **Kiểm tra chính:** SFIS `check_route`/`repair_SN` trên **scaninfo** → Cambrian trên ROI mặt nút — **không** barcode/OCR/DataMatrix từ ảnh
- **AI/OCR:** **Chỉ Cambrian**; **YOLO/OCR/pyzbar/DataMatrix không dùng**; SN là quét thủ công không phải giải mã thị giác
- **SFIS:** Route/repair + đạt `data_upload(scaninfo)` trong thị giác L4313; không đạt `data_upload(thissn, BDFA01)` trong **go_run3** L1441 — **lỗi SN không khớp**
- **Đầu ra:** JPG thô + có chú thích; Đạt `resultcolor`+`updatecount` trong thị giác khi đạt; đặt `step1` cổng theo đạt (Cambrian + upload SFIS OK)
- **Ảnh hưởng trạng thái:** `wait_test` trong go_run3; Từ chối lật không có xác nhận thoát → treo; hủy quét → `stop_program`
- **Rủi ro chính:** Upload fail dùng `thissn` cũ; `check_result_OK` không đặt lại; chế độ sensor pipeline sai; WIP theo ghi chú L4
- **Kiểm thử đề xuất:** Kiểm toán SN đạt/không đạt; hủy quét; treo Từ chối lật; nhiễm `thissn` từ model trước; SFIS tắt/bật
- **Chi tiết:** `19_button_check_pipeline.md`
