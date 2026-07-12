# Pipeline HH4K — `show_image_HH4K`

Dòng: L2145–2527 (`sky.py`). Điều phối: nhánh HH4K `go_run3` L971–1033. Helper: `HH4K_compare` L5318–5353; `pHash` L5383+, `cmHash` L5374+.

**Không dùng:** Cambrian, YOLO, SFIS (`mysfis`), `UI_show`, barcode/DataMatrix, ROI recipe `model_point`/`barcode_point`.

**Chế độ sensor:** HH4K **không** đến được qua `go_run2` (hardcode MR6500 L829). Chỉ chế độ manual + `go_run3`.

---

## 1. Mục đích

AOI manual 4 bước cho `select_model=="HH4K"`: operator đặt DUT bốn lần; mỗi lần chụp so sánh ROI frame camera với mẫu vàng cố định bằng chênh lệch mean PIL + dung sai pixel màu HSV.

| Khía cạnh | Chi tiết |
|--------|--------|
| Nhiều bước | Có — 4 lần chụp, 4 QMessageBox trong `go_run3` |
| Engine so sánh | `HH4K_compare` — pHash/cmHash tính nhưng **không dùng** trong pass/fail |
| Tiêu chí pass | `pil_spec` và `color_spec` từ model JSON (`self.HH4K`) |
| Sau bước 4 | Modal `QInputDialog` scan nhãn trong `show_image_HH4K` (không trong `go_run3`) |

### Ghi chú ngữ nghĩa `step1`–`step4`

Khác SKY (`show_image_SKY` đặt `stepN=False` khi inspection fail L2787+), HH4K đặt `stepN=True` **vô điều kiện** sau mỗi nhánh bước hoàn tất (L2243, L2324, L2402, L2481) bất kể `my_inference_result`. Cờ nghĩa **"bước N đã chạy"**, không phải **"bước N pass"**. Vision fail vẫn cập nhật UI (`resultcolor`, `updatecount`) nhưng không chặn chuỗi QMessageBox.

---

## 2. Caller và Đường Điều khiển

### Caller của `show_image_HH4K`

| Caller | Dòng | Điều kiện |
|--------|------|-----------|
| `go_run3` | L993 | HH4K, QMessageBox STEP 1 accept → sau `get_image` lần 1 |
| `go_run3` | L1000 | `step1==True` → STEP 2 accept → chụp lần 2 |
| `go_run3` | L1008 | `step2==True` → STEP 3 accept → chụp lần 3 |
| `go_run3` | L1015 | `step3==True` → STEP 4 accept → chụp lần 4 |

**Không có call site khác** trong codebase (grep xác nhận 4 lần gọi + định nghĩa).

### Đường điều khiển HH4K `go_run3` (L971–1033)

```text
select_model=="HH4K"
  reset step1–4 = False (L972–975)
  QMessageBox "STEP 1"
    Reject (65536) → xác nhận thoát tùy chọn → wait_test=True (L1030–1033)
    Accept (16384):
      get_image → shan1 → show_image_HH4K(shan1)
      if step1==True → QMessageBox "STEP 2"
        Reject → xác nhận thoát → wait_test (L1026–1029)
        Accept → get_image → shan2 → show_image_HH4K(shan2)
          if step2==True → STEP 3 … (L1001–1008)
            if step3==True → STEP 4 … (L1009–1015)
              if step4==True → wait_test=True (L1016–1017)
              [không elif step4==False]
            [không elif step3==False]
        [không elif step2==False]
      [không elif step1==False]  ← treo nếu step1 vẫn False
```

**`wait_test=True` chỉ đặt khi:**

| Đường | Dòng |
|------|-------|
| Hoàn tất cả 4 bước (`step4==True`) | L1017 |
| User từ chối QMessageBox STEP N + xác nhận thoát | L1021, L1025, L1029, L1033 |
| Hủy scan nhãn trong `show_image_HH4K` bước 4 | L2523–2524 (`stop_program=True` nữa) |

**Không đặt khi:** `show_image_HH4K` raise trước khi đặt `stepN=True`; không handler fail `elif stepN==False` (khác SKY L1256–1283).

---

## 3. Đầu vào

| Đầu vào | Nguồn | Dùng cho | Bắt buộc? | Rủi ro nếu thiếu |
|-------|--------|----------|-----------|-----------------|
| `image_numpy` | `ekkoshan.get_image()` qua `go_run3` | Cả 4 bước | Có | Frame rỗng → lỗi so sánh |
| `self.step1`–`self.step4` | Reset điều phối + lần gọi trước | Bộ chọn nhánh trong hàm | Có | Nhánh sai / no-op |
| `point/step1.json` … `step4.json` | Hardcode L2149–2152 | Shape ROI mỗi bước | Có | `FileNotFoundError` → except L2525 |
| `sample/step1.jpg` … `step4.jpg` | Hardcode L2157+ | Tham chiếu vàng mỗi bước | Có | `cv2.imread` None → lỗi slice trong `HH4K_compare` |
| `self.HH4K` | Toàn bộ model JSON L239/L466 | Ngưỡng `pil_spec`, `color_spec` | Có cho ngưỡng hợp lý | Thiếu key → `int(False)==0` (rất chặt) |
| `self.pciture_save`, `todaytime`, `self.img_time` | Runtime | Lưu thô + chú thích | Có | — |
| `self.count_object` / `self.count_path` | Model JSON | Qua `updatecount` | Cho thống kê | — |
| `self.barcode_point` / `self.model_point` | Model JSON | **Không dùng** | — | ROI recipe bỏ qua |
| SFIS / Cambrian | — | **Không dùng** | — | — |

### Trường model JSON (bằng chứng)

- `self.HH4K=modelinfo` khi tải L239, L466 — lưu toàn bộ JSON
- Ngưỡng: `self.HH4K.get("pil_spec",False)`, `self.HH4K.get("color_spec",False)` L2176+

---

## 4. Đầu ra / Tác dụng phụ

| Tác dụng phụ | Vị trí | Điều kiện |
|-------------|-------|-----------|
| Lưu frame thô | L2148 | Mỗi lần gọi: `{pciture_save}/{todaytime}/{img_time}.jpg` |
| Lưu pass/fail chú thích | L2195–2198, L2276–2279, L2355–2358 | Bước 1–3: `{img_time}_pass\|fail.jpg` |
| Lưu chú thích bước 4 | L2519 | Chỉ sau accept `QInputDialog` nhãn: `{scaninfo}_{img_time}_{pass\|fail}.jpg` |
| Lưu pass/fail bước 4 | L2434–2437 | **Bị comment** — không auto-save chỉ từ vision bước 4 |
| `source/HH4K.jpg` | L2187+ | Xem trước UI ảnh chụp chú thích |
| `tableWidget` 2 cột | L2200–2218+ | Mẫu vs chụp mỗi bước |
| `lineEdit_9` | L2220+ | `{color_sample};{color_cam};{pil_mean}` ROI cuối |
| `lineEdit_8` | L2517 | Text scan nhãn (chỉ bước 4) |
| `resultcolor` + `updatecount` | Mỗi bước L2223–2237+ | Mỗi bước cập nhật counter (pass hoặc fail) |
| `step1`–`step4` | L2243, L2324, L2402, L2481 | Đặt `True` sau khi nhánh chạy (không pass-gated) |
| `scan_sta` | L2518 | `True` khi accept dialog nhãn (bước 4) |
| `wait_test` / `stop_program` | L2523–2524 | Chỉ hủy dialog nhãn (trong vision) |
| Log / textbox | Xuyên suốt | `logging`, `myuihand.textbox` |
| SFIS | — | **Không** |

**Không** đặt `wait_test` khi hoàn tất bình thường — `go_run3` L1017 làm sau `step4==True`.

---

## 5. Luồng Từng bước

### Điều phối (`go_run3`)

1. Reset `step1`–`step4` thành `False` (L972–975).
2. Mỗi STEP 1–4: modal QMessageBox → khi accept, `get_image()` → gán `shanN` → `show_image_HH4K(shanN)`.
3. Chuỗi bước tiếp chỉ nếu `stepN==True` sau khi vision return.
4. Sau vision bước 4: nếu `step4==True`, đặt `wait_test=True` (L1016–1017).

### Vision (`show_image_HH4K`) — chọn nhánh

Dùng **instance** `step1`–`step4` làm con trỏ tiến độ (không đối số `stepname`):

| Điều kiện | Bước chạy | Đặt |
|-----------|----------|------|
| `step1==False` | Bước 1 | `step1=True` L2243 |
| `step1!=False and step2==False` | Bước 2 | `step2=True` L2324 |
| `step1!=False and step2!=False and step3==False` | Bước 3 | `step3=True` L2402 |
| `step1!=False … and step4==False` | Bước 4 + dialog nhãn | `step4=True` L2481 |

### Vision mỗi bước (bước 1–4, cùng mẫu)

1. Tải `point/stepN.json` và `sample/stepN.jpg`.
2. Mỗi shape trong JSON: tạo `valuelist` `[y1,y2,x1,x2,label]`.
3. `HH4K_compare(sample, camera, valuelist)` → `(hash, pil_mean, color_val)`.
4. **Pass** nếu `pil_mean <= pil_spec` VÀ `color_cam` trong `[color_sample ± color_spec]` (kênh HSV `[0]` so sánh int).
5. Thêm `"pass"` hoặc `"fail"` vào danh sách `step1_result`; vẽ hình chữ nhật xanh/đỏ.
6. Tổng hợp: `"fail" not in step1_result` → `my_inference_result="pass"`, ngược lại `"fail"`.
7. Cập nhật bảng, `lineEdit_9`, `resultcolor`, `updatecount`.
8. Đặt `stepN=True` vô điều kiện.

### Bước 4 thêm (L2483–2524)

Sau vision và `step4=True`:

1. Modal `QInputDialog` "please scan label".
2. **Accept:** `scaninfo` ← text; `lineEdit_8`; `scan_sta=True`; lưu `{scaninfo}_{img_time}_{result}.jpg`.
3. **Reject:** `MessageBoxW` cảnh báo; `wait_test=True`; `stop_program=True`.

---

## 6. Luồng Vision / So sánh

### `HH4K_compare` (L5318–5353)

Với ROI `center_id` = `[y1,y2,x1,x2,label]`:

| # | Phương pháp | Đầu ra | Dùng trong pass/fail? |
|---|--------|--------|-------------------|
| 1 | Crop ROI → grayscale → `pHash` + `cmHash` | `max_val_hash` (0–1) | **Không** — trả về `step1_hash`, không kiểm tra |
| 2 | PIL grayscale `ImageChops.difference` → `ImageStat.Stat.mean[0]` | `max_val_pil` | **Có** — so với `pil_spec` |
| 3 | Pixel trung tâm HSV `[center_y, center_x]` | `color_val[0]` mẫu, `[1]` camera | **Có** — kênh `[0]` so với dải `color_spec` |

Legacy comment tại L5355–5369 tham chiếu kiểu MR6500 `max_val>=0.85 and mean<=30` — không active trong HH4K.

### Quyết định pass/fail (mỗi ROI)

```text
pass nếu:  pil_mean <= int(HH4K.pil_spec)
      VÀ color_sample - color_spec <= color_cam <= color_sample + color_spec
fail nếu:  pil_mean > pil_spec HOẶC color_cam ngoài dải
          (bước 1 dùng elif rõ; bước 2–4 dùng else)
```

Chỉ bước 1: nếu không khớp `if` hay `elif`, ROI không thêm gì vào `step1_result` (edge case biên).

### Đường dẫn

| Tài sản | Đường |
|-------|------|
| JSON ROI | `point/step1.json` … `point/step4.json` |
| Mẫu vàng | `sample/step1.jpg` … `sample/step4.jpg` |
| Xem trước live | `source/HH4K.jpg` |
| Lưu sản xuất | `{pciture_save}/{todaytime}/…` |

---

## 7. Luồng SFIS

**Không.** Không `mysfis`, `data_upload`, `get_sfis_*`, hoặc kiểm tra `sfis_choose` trong L2145–2527 hoặc nhánh HH4K `go_run3` L971–1033.

---

## 8. Tương tác Trạng thái

| Cờ | Hành vi HH4K |
|------|---------------|
| `wait_test` | Xóa L690/L713 khi bắt đầu chu kỳ; khôi phục L1017 (thành công), xác nhận thoát L1021+, hoặc hủy nhãn L2523 |
| `scan_sta` | Đặt `True` L2518 khi accept nhãn — ảnh hưởng **lần lặp** `startprogram` tiếp (emit test3 lại) |
| `stop_program` | Đặt L2524 khi hủy nhãn |
| `step1`–`step4` | Reset L972–975; vision đặt True sau mỗi bước chạy |
| `select_model` | Phải là `"HH4K"` cho nhánh này |

### Cơ chế treo (đã xác minh)

1. `startprogram` đặt `wait_test=False` khi operator accept prompt test (L690/L713).
2. `go_run3` HH4K chạy vision; nếu `show_image_HH4K` except trước `self.step1=True` (L2243), `step1` vẫn `False`.
3. `go_run3` L994 chỉ kiểm tra `if self.step1==True` — **không** `elif self.step1==False` (SKY có L1256).
4. Hàm return không `wait_test=True` → vòng ngoài kẹt (`wait_test=False`).

**Vision fail không gây điều này:** fail vẫn đặt `step1=True` L2243 và chuỗi tiếp tục.

---

## 9. Đường Thất bại

| Thất bại | stepN sau return | wait_test | UI |
|---------|-------------------|-----------|-----|
| Thiếu `point/stepN.json` | Không đổi (False lần gọi 1) | Không đặt | except L2525–2527 chỉ log |
| Thiếu `sample/stepN.jpg` / ROI xấu | Không đổi | Không đặt | except — có thể lỗi OpenCV/PIL |
| Thiếu `pil_spec`/`color_spec` | Nếu không except: stepN=True | Đặt L1017 nếu đến | `int(False)==0` → pass/fail chặt |
| Vision ROI fail (bước 1–3) | stepN=True | Đặt khi chuỗi xong L1017 | Màu Fail + updatecount; **chuỗi tiếp tục** |
| Vision ROI fail bước 4 | step4=True | L1017 | Fail UI; vẫn hiện dialog nhãn |
| User từ chối QMessageBox STEP | stepN có thể True từ trước | Xác nhận thoát → wait_test | — |
| Hủy dialog nhãn (bước 4) | step4=True | L2523 + go_run3 L1017 | stop_program=True |
| Exception trong `show_image_HH4K` | stepN chưa đặt | **Không đặt** | Chỉ log/textbox |

---

## 10. Rủi ro

| Rủi ro | Mức độ | Bằng chứng |
|------|----------|----------|
| Treo `wait_test` khi exception trước `stepN=True` | **Cao** | `go_run3` L993–994: không `elif step1==False`; `show_image_HH4K` except L2525–2527 không đặt `wait_test`; `step1` chỉ đặt L2243 trong try |
| `stepN` nghĩa "đã chạy" không "pass" — chuỗi không dừng khi fail | **Cao** (chất lượng) | L2243 `self.step1=True` sau fail UI L2223–2227; `go_run3` L994 chuỗi khi `step1==True` bất kể `my_inference_result` |
| pHash/cmHash tính nhưng bỏ qua | Trung bình | L2170 gán `step1_hash`; pass chỉ dùng `step1_pil`/`step1_color` L2176; `HH4K_compare` L5326–5329 |
| Không handler fail cho exception step2/3/4 | Cao | `go_run3` L1001–1016: chỉ `if stepN==True`; không `elif stepN==False` ở mọi cấp |
| Lưu ảnh bước 4 bị comment | Trung bình | L2434–2437 comment; chỉ lưu qua đường nhãn L2519 |
| Hủy nhãn đặt `stop_program` | Trung bình | L2524 — abort toàn bộ vòng `startprogram` |
| Mặc định `pil_spec`/`color_spec` = 0 nếu thiếu | Trung bình | L2176 `int(self.HH4K.get("pil_spec",False))` → 0 |
| HH4K không đến được chế độ sensor | Cao (config) | `go_run2` L829 chỉ MR6500; HH4K chỉ `go_run3` L971 |
| `updatecount` mỗi bước trên chạy nhiều bước | Thấp | Mỗi 4 bước tăng Total — có thể đếm một DUT như 4 test |
| Đường `point/` và `sample/` hardcode | Trung bình | L2149–2152, L2157 — không từ `path_json` model JSON |

---

## 11. Kiểm thử Đề xuất

1. **Treo exception:** Đổi tên `point/step1.json` → xác nhận `step1` vẫn False, `wait_test` vẫn False, vòng Start đóng băng cho đến Stop.
2. **Chuỗi vision fail:** Ép ROI fail bước 1 → xác nhận `step1==True`, vẫn hiện prompt STEP 2, counter hiện Fail.
3. **Pass đầy đủ:** Cả 4 bước pass → dialog nhãn → `wait_test=True` L1017, `scan_sta=True`.
4. **Hủy nhãn:** Bước 4 xong → hủy nhãn → `wait_test=True`, `stop_program=True` L2523–2524.
5. **Từ chối QMessageBox:** Từ chối STEP 2 → xác nhận thoát → `wait_test=True` L1029.
6. **Thiếu mẫu:** Xóa `sample/step2.jpg` → exception bước 2, xác minh treo nếu `step2` không đặt.
7. **Biên ngưỡng:** Biên `pil_spec`; màu đúng tại `color_sample ± color_spec`.
8. **Chế độ sensor:** `is_sensor=True` + model HH4K → xác nhận MR6500 chạy thay (go_run2 L829).

---

## Tham chiếu chéo

- Điều phối: `05_runtime_flow.md`, `08_model_dispatch.md`
- Cờ treo: `04_state_machine.md`
- Chỉ mục rủi ro: `10_risks_and_bugs.md`
