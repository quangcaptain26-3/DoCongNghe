# Pipeline MR6500 — `show_image_MR6500`

Dòng: L2003–2143 (`sky.py`). Helper: `ReadDataMatrixCode` L5500–5512, `pHash` L5383–5396, `cmHash` L5374–5381, `updatecount` L415–427, `resultcolor` L584–592.

`HH4K_compare` **không** được dùng. `UI_show` **không** được gọi — bảng điền inline.

---

## 1. Mục đích

Kiểm tra nhãn sản phẩm MR6500 bằng cách:

1. Giải mã DataMatrix ISN từ ROI barcode
2. Tra SN sản xuất và mã 90 (liaohao) qua SFIS
3. So sánh ROI CHECK với ảnh mẫu vàng bằng perceptual hash + chênh lệch mean pixel

### Caller

| Caller | Dòng | Điều kiện |
|--------|------|-----------|
| `go_run2` | L829 | `is_sensor=True` — **luôn** gọi pipeline MR6500 sau grab sensor |
| `go_run3` | L858 | `select_model=="MR6500"` — chế độ manual sau `get_image()` |

**Ghi chú config sản xuất:** Không có `config.json` hoặc model JSON trong repo. Không thể xác minh recipe nào đặt `is_sensor=True`. Nếu chỉ MR6500 dùng chế độ sensor trên sản xuất, hardcode `go_run2` có thể tiềm ẩn; nếu model khác dùng `is_sensor=True`, pipeline sai chạy (xem Rủi ro).

---

## 2. Đầu vào

| Đầu vào | Nguồn | Bắt buộc |
|-------|--------|----------|
| `image_numpy` | Caller (`self.shan` từ camera) | Có |
| `self.barcode_point["shapes"]` | Model JSON → barcode_path | Có — cần shape `label=="ISN"` |
| `self.model_point["shapes"]` | Model JSON → model_path | Có — cần shape `label=="CHECK"` |
| `self.mysfis` | Init `sfisapi` trong `__init__` | Dùng khi decode thành công — **không guard bởi `sfis_choose`** |
| `self.data` | Mẫu CSV L155 | Không dùng trong MR6500 |
| `self.count_object` / `self.count_path` | Model JSON | Qua `updatecount` |
| `self.pciture_save`, `todaytime`, `self.img_time` | Runtime | Đường lưu ảnh |
| `sample/{liaohao}.jpg` | Filesystem | Từ phản hồi mã 90 SFIS |
| `source/MR6500.jpg` | Ghi lúc runtime | Xem trước UI của ảnh chụp có chú thích |

### Phụ thuộc bên ngoài

`pylibdmtx`, OpenCV, PIL (`Image`, `ImageChops`, `ImageStat`), SFIS (`get_sfis_SN`, `get_sfis_90`), widget Qt.

---

## 3. Đầu ra / Tác dụng phụ

| Tác dụng | Điều kiện | Vị trí |
|--------|-----------|----------|
| `lineEdit_8` | Decode + SFIS OK | L2034 — `mbsn` |
| `lineEdit_9` | Pass/fail so sánh | L2099 metric; L2125 `"Fail"` khi decode fail |
| `resultcolor` | Pass / Fail | L2102, L2110, L2128 |
| `updatecount` | Pass / Fail / decode fail | L2103–2115, L2129–2134 |
| `tableWidget` | So sánh 2 cột | L2077–2097 |
| Lưu ảnh | Đường thành công | L2071–2072 `{mbsn}_{img_time}_{pass\|fail}.jpg` |
| `self.mbsn`, `self.max_val` | Thuộc tính instance | L2033, L2045 |
| Log / textbox | Xuyên suốt | `logging`, `myuihand.textbox` |
| Upload SFIS | — | **Không** — không `data_upload` trong L2003–2143 |
| `wait_test` / `stepN` | — | **Không đặt tại đây** — trách nhiệm caller |

---

## 4. Luồng Từng bước

1. Vào khối `try` với frame camera đầy đủ `image_old = image_numpy` (L2004–2005).
2. Vòng lặp `barcode_point["shapes"]` — tìm `label=="ISN"` đầu tiên, crop `isn_img` (L2007–2015).
3. Vòng lặp `model_point["shapes"]` — tìm `label=="CHECK"` đầu tiên, crop `cut_img`, lưu `valuelist` (L2017–2025).
4. `ReadDataMatrixCode().decode(isn_img)` → `pylibdmtx.decode` timeout 500ms (L2027–2028).
5. **Nếu decode OK** (`getISN()[0]==True`, L2029):
   - `mysfis.get_sfis_SN(isn_string)` → parse `mbsn` qua `split("\x7f")[2].split(":")[1]` (L2032–2034).
   - `mysfis.get_sfis_90(mbsn)` → `liaohao` qua `split("\x7f")[2]` (L2035–2037).
   - Tải `sample/{liaohao}.jpg`, crop cùng tọa độ ROI CHECK (L2038).
   - Grayscale cả hai crop; `pHash` + `cmHash` → `max_val` (L2039–2045).
   - PIL grayscale diff → `stat.mean[0]` (L2048–2055).
   - **Pass** nếu `max_val>=0.85` VÀ `stat.mean[0]<=30` (L2065–2067); ngược lại **fail** (L2068–2070).
   - Vẽ hình chữ nhật xanh/đỏ trên ROI CHECK; lưu ảnh (L2066–2072).
   - Điền tableWidget (mẫu vs chú thích); đặt lineEdit; `resultcolor` + `updatecount` (L2077–2115).
6. **Nếu decode fail** (`getISN()[0]==False`, L2121–2134): log, `lineEdit_9="Fail"`, `resultcolor("Fail")`, `updatecount` tăng fail — không lưu ảnh, không truy vấn SFIS.
7. **Mọi exception** (L2141–2143): log lên UI — không cập nhật Pass/Fail count trừ exception trước nhánh đã xử lý.

---

## 5. Luồng DataMatrix / Barcode

| Khía cạnh | Chi tiết |
|--------|--------|
| Nguồn ROI | JSON `self.barcode_point`, shape đầu `label=="ISN"` |
| Thư viện | `pylibdmtx.decode(img, timeout=500, max_count=1)` L5506 |
| Decode fail | `getISN()` → `(False, None)` L5511–5512 → đường fail UI L2121–2134 |
| Chuỗi ISN | `all_barcode_info[0].data.decode("utf-8")` L5510 |
| Fallback | Không — không scan thủ công trong MR6500 (khác ipex_check) |
| Rủi ro crash | Không có shape `ISN` trong JSON: `isn_img` không xác định → `NameError` → bắt L2141 |
| Thiếu ROI CHECK | `cut_img` không xác định → cùng đường exception |

---

## 6. Luồng SFIS

| Khía cạnh | Chi tiết |
|--------|--------|
| Hàm gọi | `get_sfis_SN(reader.getISN()[1])` L2032; `get_sfis_90(mbsn)` L2035 |
| Nguồn SN | Chuỗi ISN DataMatrix → SFIS ánh xạ sang `mbsn` |
| Mã 90 / model | Chuỗi `liaohao` từ phản hồi SFIS — dùng làm tên file mẫu |
| Upload pass | **Không** |
| Upload fail | **Không** |
| Mã lỗi | **Không** trong MR6500 |
| `sfis_choose=False` | `mysfis` không tạo trong `__init__` L194–197 — đường decode-thành-công gây `AttributeError` → bắt L2141; không cập nhật count |
| Parse SFIS fail | Phản hồi `\x7f` sai định dạng → `IndexError`/`AttributeError` → except L2141 |
| Mạng SFIS fail | Tương tự — nuốt bởi except; caller vẫn đặt `wait_test=True` |

**Ghi chú:** Tài liệu Phase 1 ngụ ý `data_upload` trong MR6500 — **sai**; chỉ dùng API truy vấn.

---

## 7. Luồng So sánh Ảnh / Hash

| Khía cạnh | Chi tiết |
|--------|--------|
| Thuật toán | `pHash` (DCT 32×32, hash ROI 10×10) L5383–5396; `cmHash` = bit khớp / 100 L5374–5381 |
| Thêm | Mean `ImageChops.difference` L2052–2055 |
| Nguồn mẫu | `cv2.imread("sample/"+liaohao+".jpg")` — **đường hardcode** L2038 |
| Căn ROI | Cùng `y1,y2,x1,x2` từ `valuelist` CHECK áp lên ảnh mẫu đầy đủ |
| Quy tắc pass | `max_val >= 0.85` **VÀ** `stat.mean[0] <= 30` L2065 |
| Quy tắc fail | `max_val < 0.85` **HOẶC** `stat.mean[0] > 30` L2068 |
| Ngưỡng | **Hardcode** trong hàm — không từ model JSON |
| `cmHash == -1` | Độ dài hash không khớp L5376–5377 → coi là fail (`-1 < 0.85`) |
| Rủi ro false pass/fail | Ngưỡng cố định; không chuẩn hóa ánh sáng; file mẫu phải tồn tại và khớp mã 90 SFIS chính xác |

`HH4K_compare` không gọi — logic hash/diff tương tự nhân đôi inline (bản comment trong HH4K_compare L5359–5364).

---

## 8. Tương tác Trạng thái

| Trạng thái | Đặt trong MR6500? | Caller đặt sau return |
|-------|----------------|----------------------------|
| `wait_test` | Không | `go_run2` L830, `go_run3` L859 → `True` luôn |
| `step1–step6` | Không | N/A |
| `scan_sta` | Không | Không đổi |
| `stop_program` | Không | — |

**Reset chu kỳ:** Caller đặt `wait_test=True` sau khi hàm return (thành công, decode fail, hoặc exception bắt). **Không treo** chỉ từ MR6500 trừ khi caller bỏ sót — cả hai caller đều đặt cờ.

---

## 9. Đường Thất bại

| Điểm thất bại | Phát hiện | Hành vi | Kết quả UI | Upload SFIS | Rủi ro |
|---------------|-----------|----------|-----------|-------------|------|
| Thiếu ROI ISN/CHECK | Exception | Bắt L2141 | Chỉ log lỗi | Không | Không cập nhật count; wait_test vẫn True |
| Ảnh không hợp lệ/rỗng | Crop/decode fail | Nhánh decode fail hoặc exception | Fail + count | Không | — |
| DataMatrix decode fail | `getISN()[0]==False` | L2121–2134 | Fail, count++ fail | Không | Không lưu ảnh |
| SFIS tắt | `AttributeError` trên mysfis | except L2141 | Thông báo lỗi | Không | Decode OK nhưng không kiểm tra |
| Phản hồi SFIS xấu | Exception parse | except L2141 | Thông báo lỗi | Không | — |
| Thiếu JPG mẫu | `cv2.imread` None | Lỗi slice/index → except | Thông báo lỗi | Không | — |
| So sánh hash fail | Ngưỡng L2068 | nhánh fail | Fail, count++ fail | Không | — |
| So sánh hash pass | L2065 | nhánh pass | Pass, count++ pass | Không | — |
| Lưu file fail | IOError có thể | except L2141 | Lỗi | Không | Hiếm |
| Frame camera không hợp lệ | cần xác minh | Tùy decode/so sánh | — | Không | Không validate rõ ràng |

---

## 10. Rủi ro

### Rủi ro: Gọi SFIS không có guard sfis_choose

- **Mức độ:** Cao
- **Bằng chứng:** L2032–2035 dùng `self.mysfis` vô điều kiện khi decode thành công; `__init__` bỏ qua `mysfis` khi SFIS tắt L194–197
- **Tại sao quan trọng:** Decode OK + SFIS tắt → đường exception, không Pass/Fail count, operator chỉ thấy lỗi
- **Cách sửa đề xuất:** Guard với `sfis_choose` hoặc bỏ SFIS ở chế độ offline

### Rủi ro: Parse phản hồi SFIS mong manh

- **Mức độ:** Cao
- **Bằng chứng:** L2032 `split("\x7f")[2].split(":")[1]`; L2035 `split("\x7f")[2]`
- **Tại sao quan trọng:** Định dạng SFIS bất ngờ → exception, abort kiểm tra im lặng
- **Cách sửa đề xuất:** Validate cấu trúc phản hồi; UI lỗi rõ ràng

### Rủi ro: Ngưỡng so sánh hardcode

- **Mức độ:** Trung bình
- **Bằng chứng:** L2065 literal `0.85`, `30`
- **Tại sao quan trọng:** Drift môi trường/ánh sáng gây false pass/fail; không tune theo model
- **Cách sửa đề xuất:** Chuyển vào config model JSON

### Rủi ro: Đường mẫu hardcode

- **Mức độ:** Trung bình
- **Bằng chứng:** L2038 `sample/{liaohao}.jpg`
- **Tại sao quan trọng:** Thiếu file crash đường so sánh; liaohao SFIS sai tải mẫu vàng sai
- **Cách sửa đề xuất:** Kiểm tra kết quả `imread`; gốc mẫu cấu hình được

### Rủi ro: Nhãn ROI thiếu không bắt trước decode

- **Mức độ:** Trung bình
- **Bằng chứng:** Vòng L2007–2025 `break` chỉ khi tìm thấy nhãn; không else — `isn_img`/`cut_img` có thể không xác định
- **Tại sao quan trọng:** Recipe JSON hỏng → exception, không fail có cấu trúc
- **Cách sửa đề xuất:** Validate ROI tìm thấy trước crop

### Rủi ro: Không upload MES SFIS cho kết quả MR6500

- **Mức độ:** Trung bình (sản xuất/MES)
- **Bằng chứng:** Không `data_upload` trong L2003–2143 so với model khác trong go_run3
- **Tại sao quan trọng:** Pass/Fail chỉ local — MES có thể không ghi kiểm tra
- **Cách sửa đề xuất:** Xác nhận có cố ý; thêm upload nếu cần

### Rủi ro: go_run2 hardcode MR6500 cho mọi recipe sensor

- **Mức độ:** Nghiêm trọng (khi non-MR6500 + is_sensor)
- **Bằng chứng:** L829; bảng dispatch `08_model_dispatch.md`
- **Tại sao quan trọng:** JSON barcode/model sai dùng với logic MR6500
- **Cách sửa đề xuất:** Dispatcher dùng chung theo `select_model`

### Rủi ro: Exception nuốt không Pass/Fail

- **Mức độ:** Thấp–Trung bình
- **Bằng chứng:** L2141–2143 chỉ log; không `resultcolor`/`updatecount` trong except
- **Tại sao quan trọng:** Operator có thể bỏ lỡ kiểm tra fail; chu kỳ tiếp tục (`wait_test=True` từ caller)
- **Cách sửa đề xuất:** Đặt Fail + count trong khối except

### Rủi ro: lineEdit_9 hiển thị metric không phải "Pass" khi thành công

- **Mức độ:** Thấp (UX)
- **Bằng chứng:** L2099 `str(max_val)+";"+str(stat.mean[0])` vs L2125 `"Fail"` khi decode fail
- **Tại sao quan trọng:** Hiển thị kết quả không nhất quán
- **Cách sửa đề xuất:** Căn với pipeline khác

---

## Tóm tắt Tương tác Chế độ Sensor

```text
is_sensor=True → go_run2 → show_image_MR6500 (luôn)
is_sensor=False, select_model=MR6500 → go_run3 → show_image_MR6500
is_sensor=False, model khác → go_run3 → pipeline khác (không MR6500)
is_sensor=True, model khác → go_run2 → show_image_MR6500 (SAI)
```

**Cần xác minh:** File model JSON sản xuất cho cặp `is_sensor` + `select_model` — không có trong workspace.
