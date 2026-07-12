# Pipeline SKY — `show_image_SKY`

Dòng: L2647–3106 (`sky.py`). Liên quan: nhánh SKY `go_run3` L1034–1291; helper `get_inference_result` L630, `cambrian_space` L2595, `UI_show` L5235, `updatecount` L415, `resultcolor` L584.

**Đường SKY active không dùng:** `yolov5_inference` (chỉ trong `show_image_SKY_yolo` chết L3109+), `pHash`/`cmHash`, `HH4K_compare`.

**Chế độ sensor:** SKY **không** đến được qua `go_run2` (hardcode MR6500 L829). Chỉ chế độ manual + `go_run3`.

---

## 1. Mục đích

Pipeline AOI 6 bước cho `select_model` **`SKY`** hoặc **`SKY_4G`**: đọc barcode → kiểm tra route SFIS → phân loại Cambrian trên ROI vít/linh kiện → OCR + đối chiếu barcode (STEP 3) → bước lưu trữ ảnh → upload pass cuối.

| Khía cạnh | Chi tiết |
|--------|--------|
| Nhiều bước | Có — 6 lần chụp camera do `go_run3` điều phối, một lần gọi `show_image_SKY` mỗi bước |
| Engine AI (active) | **Cambrian** qua `get_inference_result` + `cambrian_space` |
| Thay thế (chết) | `show_image_SKY_yolo` dùng YOLO — **không caller trong codebase** |

---

## 2. Caller và Đường Điều khiển

| Caller | Dòng | Điều kiện | Sau return |
|--------|------|-----------|--------------|
| `go_run3` | L1073 | SKY/SKY_4G, QMessageBox STEP 1 accept | Nếu `step1`: chuỗi STEP 2; elif `step1==False`: fail UI + SFIS `BDFA0` + `wait_test=True` L1256–1283 |
| `go_run3` | L1097 | `step1==True`, STEP 2 | Nếu `step2`: STEP 3; elif fail: SFIS fail L1232–1250 |
| `go_run3` | L1105 | `step2==True`, STEP 3 | Nếu `step3`: STEP 4; elif fail: SFIS L1208–1226 |
| `go_run3` | L1113 | `step3==True`, STEP 4 | Chuỗi STEP 5/6 hoặc fail L1184+ |
| `go_run3` | L1122 | `step4==True`, STEP 5 | STEP 6 nếu `step5` |
| `go_run3` | L1131 | `step5==True`, STEP 6 | `step6==True` → `wait_test=True` L1133; `step6==False` → fail + SFIS L1135–1154 |
| `go_run2` | — | **Không gọi SKY** | — |
| `show_image_SKY_yolo` | L3109 | **Chết** — zero call site | — |

---

## 3. Đầu vào

| Đầu vào | Nguồn | Dùng cho | Bắt buộc? | Rủi ro nếu thiếu |
|-------|--------|----------|-----------|-----------------|
| `image_numpy` | Camera qua `go_run3` | Mọi bước | Có | Frame rỗng → decode/inference fail |
| `stepname` | Caller `"STEP 1"`…`"STEP 6"` | Bộ chọn nhánh | Có | Nhánh sai / no-op |
| `point/SKY_*.json` hoặc `SKY_4G_*.json` | Đường hardcode L2658+ | Shape ROI | Có | FileNotFound → except L3104 |
| `self.select_model` | Model JSON | Chọn file SKY vs SKY_4G | Có | File point sai |
| `sky_clei` | Dict module L112 | Barcode CLEI vs map nhãn STEP 3 | Có STEP 3 | KeyError nếu clei không xác định |
| `self.mysfis` | Init SFIS | `check_route`, `repair_SN`, `data_upload` | Nếu `sfis_choose` | AttributeError nếu SFIS tắt + kiểm route |
| `self.client` | Cambrian | `get_inference_result` | Có cho bước AI | Fail nếu Cambrian tắt |
| `self.data` | Mẫu CSV L155 | Upload SFIS | Bước upload | — |
| `self.sfis_choose` | config.json | Cổng route/upload SFIS | Không | Bypass offline L2789 |
| `self.barcode_point` / `self.model_point` | Model JSON | **Không dùng** — SKY dùng `point/*.json` | — | Recipe JSON bỏ qua cho ROI |

---

## 4. Đầu ra / Tác dụng phụ

| Tác dụng phụ | Vị trí | Điều kiện |
|-------------|-------|-----------|
| Lưu frame thô | L2650 | Mỗi lần gọi |
| `_pass.jpg` / `_fail.jpg` | `cambrian_space` L2636–2641 | Sau bước Cambrian |
| `UI_show` | Nhiều bước | Pass/fail mỗi bước |
| `lineEdit_8` | L2709 | STEP 1 barcode OK — `thissn` |
| `lineEdit_9` | L3061 STEP 6; đường fail go_run3 | Chuỗi model hoặc `"Fail"` |
| `resultcolor` + `updatecount` | STEP 6 pass L3075–3082; fail điều phối | Pass tổng hợp / fail điều phối |
| SFIS `data_upload` pass | L3083–3084 | STEP 6 Cambrian pass + `sfis_choose` — **không mã lỗi** |
| Upload SFIS fail | **chỉ go_run3** | `error="BDFA0"` L1150+ |
| `step1`–`step6` | Mỗi bước trong hàm | Xem §8 |
| `thissn`, `thismodel`, `thisclei` | Barcode STEP 1 L2699–2703 | 4 barcode decode |
| `checksn`, `modelcheck`, `sncheck` | STEP 1/3 | Cờ đối chiếu chéo |
| Log / textbox | Xuyên suốt | — |

**Không** đặt `wait_test` hoặc `scan_sta`.

---

## 5. Luồng Từng bước

### Trước inference (mỗi lần gọi)

1. Lưu frame BGR; chuyển grayscale L2650–2652.
2. Tải JSON hardcode theo bước từ `point/`.
3. Crop ROI theo nhãn shape.

### Theo stepname

| Bước | Kiểm tra trước | Inference / kiểm tra | Kết quả | stepN |
|------|-----------|----------------------|--------|-------|
| **STEP 1** | pyzbar trên ROI SN; cần 4 mã không-QR L2694 | SFIS `check_route`/`repair_SN` L2711–2748; Cambrian trên ROI mylar/rubber/cover/screw L2776–2779 | `cambrian_space` → step1 | L2783/2787 |
| **STEP 2** | Cần `step1==True` L2950 | Cambrian trên ROI vít từ `SKY_model1.json` L2970–2974 | step2 L2980/2985 | |
| **STEP 3** | Cần `step2==True` L2813 | PaddleOCR model+topsn L2864–2896; pyzbar CLEI; khớp SN/model/clei L2921; Cambrian L2926–2930 | step3 | |
| **STEP 4** | `step3==True` L2987 | Cambrian ROI vít `SKY_model3.json` | step4 | |
| **STEP 5** | `step4==True` L3024 | **Không AI** — chỉ `UI_show` L3025 | step5=True L3028 | |
| **STEP 6** | `step5==True` L3029 | Cambrian `SKY_model5.json`; tổng hợp checksn/modelcheck/sncheck L3060–3065 | step6; Pass UI + SFIS upload L3075–3096 | |

### Xử lý sau caller (`go_run3`)

- Chuỗi QMessageBox → grab tiếp khi `stepN==True`.
- Khi `stepN==False`: Fail UI, `data_upload(..., error="BDFA0")`, `wait_test=True`.
- Khi thành công đầy đủ (`step6==True`): chỉ `wait_test=True` L1133.

---

## 6. Luồng Vision / AI Inference

| Kiểm tra / ROI | Phương pháp | Ngưỡng / quy tắc | Pass | Fail | Bằng chứng |
|-------------|--------|------------------|------|------|----------|
| Barcode SN (STEP 1) | pyzbar | Đúng 4 non-QRCODE L2694 | Đặt thissn/model/clei | Chỉ log; step1 vẫn False | L2678–2696 |
| Route SFIS | `check_route`/`repair_SN` | Return `[0]`/`[1]` + pattern chuỗi L2729 | `check_result_OK=True` → inference | Modal + bỏ inference | L2713–2768 |
| mylar/rubber/cover/screw (STEP 1) | Cambrian | Kết quả == label[4], không "NG" | `cambrian_space` Pass | Fail → step1=False | L2776–2787, cambrian_space L2602 |
| ROI vít (STEP 2,4,6) | Cambrian | Như trên | stepN=True | stepN=False | L2970+, L3008+, L3050+ |
| ROI model (STEP 3) | PaddleOCR | `getmodel in thismodel` L2881 | modelcheck=True | modelcheck=False | L2873–2949 |
| ROI topsn (STEP 3) | PaddleOCR | `thissn in topsn` L2921 | sncheck=True | sncheck=False | L2888–2944 |
| ROI clei (STEP 3) | pyzbar + `sky_clei` | `barcode==sky_clei[thisclei]` L2921 | phần sncheck | sn check fail | L2898–2921 |
| screw_big/yellow/sim (STEP 3) | Cambrian | cambrian_space | step3 | step3=False | L2926–2938 |
| STEP 5 | Không | — | step5=True luôn nếu đến | — | L3024–3028 |
| Tổng hợp cuối (STEP 6) | Cờ | checksn VÀ modelcheck VÀ sncheck | resultcolor Pass L3075 | my_inference_result="fail" nhưng **fail UI bị comment** L3067–3074 | L3060–3074 |

**YOLO:** Không gọi từ `show_image_SKY`. Crop ghi vào `yolov5/classify/` L2967+ nhưng Cambrian dùng mảng trong bộ nhớ.

**Hash/template:** Không dùng.

---

## 7. Luồng SKY và SFIS

| Kịch bản | Lệnh gọi SFIS | Vị trí | Upload | Mã lỗi | Rủi ro |
|----------|-----------|-------|--------|------------|------|
| Route check OK | `check_route(thissn)` | show_image_SKY STEP 1 L2713 | Không | — | — |
| Route fail + repair | `repair_SN(thissn)` | L2730, L2740 | Không | — | Modal chặn UI |
| Bước fail (điều phối) | `data_upload(thissn, data, error=...)` | go_run3 L1150+ | Fail | **`BDFA0`** | Trùng 7× |
| STEP 6 Cambrian pass | `data_upload(thissn, self.data)` | show_image_SKY L3083 | Pass | **Không** | Upload dù cờ tổng hợp false? |
| SFIS tắt STEP 1 | Bypass route L2789 | show_image_SKY | Không | — | Vẫn chạy Cambrian |
| SFIS tắt fail | Không upload | go_run3 | — | — | Chỉ fail local |
| Exception upload STEP 1 fail | try/except | go_run3 L1269–1282 | Có thể fail im lặng log | BDFA0 | wait_test vẫn True L1283 |

**Nguồn SN:** Index danh sách barcode `[1]` → `thissn` L2701 (không scaninfo — SKY bypass scan trong go_run1).

**Không** `get_sfis_SN` / `get_sfis_90` trong đường SKY.

---

## 8. Tương tác Trạng thái

| Trạng thái | Đặt ở đâu | Giá trị | Điều kiện | Rủi ro |
|-------|-----------|-------|-----------|------|
| `step1`–`step6` | show_image_SKY | True/False | Logic mỗi bước | Exception → không đặt |
| `wait_test` | chỉ go_run3 | True | Thành công L1133 hoặc fail L1154+ hoặc step1 fail L1283 | **Không đặt** nếu user hủy giữa chuỗi không có exit handler |
| `scan_sta` | — | Không đổi | — | — |
| `check_result_OK` | SFIS STEP 1 | True/False | Route/repair L2725–2754 | False bỏ qua Cambrian |

**Reset chu kỳ:** `go_run3` reset mọi step False L1035–1040 khi bắt đầu nhánh.

**Đường treo:** User từ chối prompt STEP 1 L1285–1291 đặt wait_test. Từ chối giữa chuỗi đặt wait_test+stop_program. Nếu `step1==False` sau STEP 1 — xử lý L1256. **Exception trong show_image_SKY** với stepN chưa đặt sau thành công một phần — go_run3 có thể không vào nhánh fail (cần xác minh mỗi bước).

---

## 9. Đường Thất bại

| Điểm thất bại | Phát hiện | Hành vi | UI | SFIS | wait_test | Rủi ro |
|---------------|-----------|----------|-----|------|-----------|------|
| Barcode ≠4 mã | Kiểm len L2694 | Log lỗi | Không trong vision | Không | go_run3 step1==False | OK |
| Route SFIS fail | check_route L2714 | Modal; có thể repair | MessageBox | Không | step1 chưa đặt → đường fail | — |
| Cambrian fail bước N | cambrian_space "Fail" | stepN=False | UI_show fail | go_run3 BDFA0 | True | OK |
| Exception cambrian_space | except L2643 | Trả None | Không | Không | stepN chưa đặt | Điều phối có thể treo |
| OCR/model lệch STEP 3 | L2945–2949 | modelcheck=False | Log | go_run3 nếu step3 False | True | OK |
| SN/CLEI lệch | L2940–2944 | sncheck=False | Log | đường step3 False | True | OK |
| STEP 6 Pass nhưng cờ false | L3064–3065 | my_inference_result=fail | **Pass UI bị comment** | **Vẫn có thể upload** L3083 nếu Cambrian Pass | step6=True | **Rủi ro false pass** |
| Thiếu point JSON | Exception | L3104 log | Lỗi | Không | Tùy stepN | Có thể treo |
| Thiếu nhãn ROI SN | cut_img không xác định | Exception | Lỗi | Không | — | — |
| Upload SFIS fail step1 | except L1280 | Log | Hiện Fail | — | True L1283 | OK |
| Sensor + model SKY | go_run2 MR6500 | Pipeline sai | — | — | — | Lỗi config nghiêm trọng |

---

## 10. Rủi ro

### Rủi ro: show_image_SKY_yolo chết nhưng import yolov5 bị comment

- **Mức độ:** Trung bình (bảo trì / nhầm lẫn)
- **Bằng chứng:** L3109 hàm tồn tại; L3179 gọi `yolov5_inference`; L7 `# from yolov5.classify import predict_change`; zero caller tới `_yolo`
- **Tại sao quan trọng:** Đường active dùng Cambrian; đường YOLO chết sẽ crash nếu nối
- **Cách sửa đề xuất:** Xóa hoặc sửa import; ghi Cambrian là canonical

### Rủi ro: STEP 6 false pass — Cambrian pass ghi đè fail tổng hợp

- **Mức độ:** Nghiêm trọng
- **Bằng chứng:** L3055–3096: `yolo_step6=="Pass"` đặt `step6=True`; fail UI cho `my_inference_result=="fail"` comment L3067–3074; upload SFIS L3083 không kiểm tra tổng hợp
- **Tại sao quan trọng:** MES có thể nhận pass khi kiểm barcode/OCR trước đó fail
- **Cách sửa đề xuất:** Cổng step6/SFIS trên mọi cờ; bỏ comment xử lý fail

### Rủi ro: Exception cambrian_space trả None

- **Mức độ:** Cao
- **Bằng chứng:** L2643–2645 except chỉ log; không giá trị return
- **Tại sao quan trọng:** `yolo_stepN == "Pass"` false và `== "Fail"` false → stepN chưa đặt → go_run3 có thể không tiến hoặc fail sạch
- **Cách sửa đề xuất:** Return "Fail" khi exception

### Rủi ro: Đường point/*.json hardcode

- **Mức độ:** Trung bình
- **Bằng chứng:** L2658, L2817, L2954, v.v. — không từ `model_point` model JSON
- **Tại sao quan trọng:** Đổi recipe cần đổi tên file; phụ thuộc đường triển khai
- **Cách sửa đề xuất:** Tải từ đường model JSON

### Rủi ro: Upload SFIS fail trùng trong go_run3

- **Mức độ:** Trung bình
- **Bằng chứng:** Cùng khối L1150, L1174, L1198, L1222, L1246, L1272 — đều `error="BDFA0"`
- **Tại sao quan trọng:** Drift bảo trì; step3 dùng message "model or sn check fail" L1209
- **Cách sửa đề xuất:** Handler fail tập trung

### Rủi ro: Upload pass không mã lỗi; fail dùng BDFA0

- **Mức độ:** Trung bình
- **Bằng chứng:** Pass L3084 không `error=`; fail go_run3 `error="BDFA0"`
- **Tại sao quan trọng:** MES có thể không phân biệt ngữ nghĩa pass/fail nhất quán
- **Cách sửa đề xuất:** Ghi/căn hợp đồng API SFIS

### Rủi ro: Chế độ sensor không chạy SKY

- **Mức độ:** Cao (nếu is_sensor=True + recipe SKY)
- **Bằng chứng:** go_run2 L829 chỉ MR6500; 08_model_dispatch.md
- **Tại sao quan trọng:** Kiểm tra sản phẩm sai
- **Cách sửa đề xuất:** Dispatcher dùng chung

### Rủi ro: PaddleOCR khởi tạo mỗi lần gọi STEP 3

- **Mức độ:** Trung bình (đơ UI)
- **Bằng chứng:** L2864–2865 PaddleOCR mới trên luồng UI
- **Tại sao quan trọng:** Tải vài giây mỗi STEP 3
- **Cách sửa đề xuất:** Tái dùng instance từ init

### Rủi ro: Truy cập clei barcode_list[0] không kiểm tra rỗng

- **Mức độ:** Trung bình
- **Bằng chứng:** L2909 `barcode_list_clei[0]` — không kiểm len sau pyzbar
- **Tại sao quan trọng:** IndexError → except L3104
- **Cách sửa đề xuất:** Validate số lượng decode

---

## 11. Kiểm thử Đề xuất

| Test case | Thiết lập | Hành vi kỳ vọng |
|-----------|-------|-------------------|
| Ảnh tốt pass đầy đủ | 6 lần chụp hợp lệ, SFIS bật | step6 True, Pass UI, upload SFIS không lỗi, wait_test True |
| STEP 1 một ROI Cambrian fail | Ảnh vít xấu | step1 False, go_run3 fail + BDFA0 + wait_test |
| Barcode ≠4 | Barcode một phần | step1 False, đường fail L1256 |
| Thiếu point JSON | Đổi tên file | Exception; xác minh wait_test / trạng thái step |
| Tọa độ crop không hợp lệ | JSON point xấu | Exception hoặc crop rỗng |
| SFIS tắt | sfis_choose=False | Bypass route L2789; Cambrian chạy; không upload |
| Upload SFIS fail | Mock lỗi upload step1 | Log + wait_test True L1283 |
| Cambrian tắt | cambrian off | get_inference_result fail → except |
| Sensor + model SKY | is_sensor=True, chọn SKY | **MR6500 chạy** — sai (chỉ ghi tài liệu) |
| Manual + SKY | is_sensor=False | Chuỗi 6 bước qua go_run3 |
| STEP 6 Pass + sncheck False | Ép cờ false | Xác minh upload pass SFIS vẫn bắn (kiểm lỗi) |

---

## Code Chết Liên quan

`show_image_SKY_yolo` (L3109–~3450): triển khai song song dùng `yolov5_inference` thay Cambrian cho STEP 1+. **Không bao giờ gọi.** Cần import `predict_change` bỏ comment L7.
