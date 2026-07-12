# Sensor Mode Guard — Compact Playbook

**File:** `sky.py` · **Workstream:** `03_sensor_dispatch`  
**Nguồn:** `08_model_dispatch.md`, `05_runtime_flow.md`, `10_risks_and_bugs.md` §Logic, `07_camera_io_sfis.md` §3  
**Luật:** `is_sensor=True` chỉ được Start khi `select_model == "MR6500"` — mọi combo khác chặn trước `IoCard` + vòng `while`.

> Line analysis: `go_run2` L795–832, hardcode L829. Repo hiện tại: `startprogram` G617, `is_sensor` G195/G422, `test2.emit` G654. **Ctrl+F anchor** trước khi sửa — line drift thường xuyên.

### Pre-check repo (bắt buộc trước patch)

| Kiểm tra | Anchor | Kỳ vọng |
|----------|--------|---------|
| Sensor handler tồn tại | F `def go_run2` | Thấy hàm poll IO + `show_image_MR6500` |
| Manual dispatch tồn tại | F `def go_run3` | Thấy chuỗi `elif self.select_model` |
| Bug gốc còn | F `show_image_MR6500(self.shan)` **trong** `go_run2` | Không check `select_model` |

Nếu **không** thấy `go_run2`/`go_run3` (repo lỗi/merge sai) → khôi phục `sky.py` sạch trước khi ship guard. Evidence bug: `10_risks_and_bugs.md` L829.

---

## Improvement Purpose

Mục tiêu của cải tiến này là tránh sensor mode chạy sai pipeline — hiện `go_run2` hardcode `show_image_MR6500` bất kể `select_model`. Short-term guard chặn cấu hình sai trước Start; đây là biện pháp an toàn production cho đến khi shared dispatcher (dài hạn) ship.

## Before Improvement

Trước cải tiến, `is_sensor=True` luôn đi `go_run2` → `show_image_MR6500(self.shan)` (L829) — bỏ qua `select_model`. Recipe SKY/WP/Button_check + sensor: operator thấy UI/recipe đúng model nhưng vision chạy MR6500 (hash/barcode sai). Rủi ro kiểm sản phẩm bằng logic sai — false pass/fail không phát hiện được từ UI.

## After Improvement

Sau cải tiến, `validate_sensor_mode()` chặn Start khi `is_sensor=True` và model ≠ MR6500 — MessageBox rõ, Start vẫn enabled. Chỉ MR6500 + sensor được phép chạy. Log recipe path giúp audit config. Optional warning khi load recipe sai combo. Production an toàn trong khi chờ dispatcher dài hạn.

## Improvement Value

| Area                        | Value |
| --------------------------- | ----- |
| Production stability        | Chặn combo config nguy hiểm trước khi chạy vision sai |
| Operator experience         | Thông báo rõ "Sensor mode supports MR6500 only" thay vì pass/fail im lặng sai |
| MES/SFIS integrity          | Tránh upload MES từ pipeline sai model |
| Maintainability             | Guard tập trung `startprogram`; dễ mở rộng `SENSOR_SUPPORTED_MODELS` |
| Debugging / troubleshooting | Log model + recipe path khi guard chặn |

## Before / After Summary

| Aspect           | Before | After |
| ---------------- | ------ | ----- |
| Runtime behavior | Sensor luôn MR6500 dù recipe SKY/WP | Non-MR6500 + sensor blocked at Start |
| Error handling   | Không validate combo is_sensor/model | validate_sensor_mode + early return |
| Operator impact  | Test sai pipeline không biết | Blocked với message rõ trước IoCard/loop |
| Production risk  | Kiểm sản phẩm bằng logic sai | Giảm rủi ro wrong pipeline trên line |

---

## Per-Fix Detail

### SENSOR-001

#### Code Location

| Item | Value |
|------|-------|
| File | `sky.py` |
| Class | `Demo` |
| Function | (new method, before `startprogram`) |
| Anchor | G617 / F `def startprogram` |
| Insert point | Ngay **trước** `def startprogram(self):` |

#### Current Problem

Không có hàm tập trung kiểm tra combo `is_sensor` + `select_model`. Logic validate phải duplicate hoặc không tồn tại — caller không có API chung để chặn cấu hình sai.

#### Before Improvement

`startprogram` và `choose_model` không gọi validate. `is_sensor=True` với model ≠ MR6500 vẫn có thể Start → vào `go_run2` → hardcode MR6500 pipeline.

#### Required Change

**Chèn** class constant `SENSOR_SUPPORTED_MODELS = {"MR6500"}` và method `validate_sensor_mode(self)` trả `(ok: bool, message: str)` ngay trước `def startprogram`.

#### After Improvement

Một method tái sử dụng cho SENSOR-002 (Start guard) và SENSOR-004 (load warning). MR6500 + sensor → `(True, "")`; mọi combo khác → `(False, msg)` với hướng dẫn operator rõ.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Nền tảng guard tập trung — dễ mở rộng `SENSOR_SUPPORTED_MODELS` |
| Operator experience | Message chuẩn một chỗ, không copy-paste QMessageBox |
| MES/SFIS integrity | N/A trực tiếp (chặn ở SENSOR-002) |
| Maintainability | Single source of truth cho sensor policy |
| Debugging / troubleshooting | Message + log format nhất quán |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-SENSOR-001 | Gọi tay `validate_sensor_mode()` với SKY + `is_sensor=True` | Unit call | Trả `(False, msg)` |
| T-SENSOR-001b | MR6500 + `is_sensor=True` | Unit call | Trả `(True, "")` |
| T-SENSOR-001c | SKY + `is_sensor=False` | Unit call | Trả `(True, "")` |

#### Rollback

Xóa `SENSOR_SUPPORTED_MODELS` + method `validate_sensor_mode`. Chỉ rollback an toàn nếu rollback đồng thời SENSOR-002/004 (caller).

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 1 | Method mới, không đổi runtime flow — merge trước SENSOR-002 |

---

### SENSOR-002

#### Code Location

| Item | Value |
|------|-------|
| File | `sky.py` |
| Class | `Demo` |
| Function | `startprogram` |
| Anchor | G617 / F `def startprogram` |
| Insert point | Đầu `try:`, **trước** `self.ekkoshan=camera()` và **trước** `pushButton_2.setEnabled(False)` |

#### Current Problem

Start sensor với model non-MR6500 không bị chặn. Operator thấy UI/recipe đúng model nhưng vision chạy MR6500 (hash/barcode sai) — false pass/fail không phát hiện từ UI.

#### Before Improvement

`startprogram` mở camera và IoCard ngay, không check combo. Path sensor: `go_run2` → `show_image_MR6500(self.shan)` hardcode bất kể `select_model`.

#### Required Change

**Chèn** block gọi `validate_sensor_mode()`; nếu `not ok` → log `SENSOR_GUARD_BLOCK`, emit textbox, `QMessageBox.critical`, `return` (không disable Start button).

#### After Improvement

Non-MR6500 + sensor blocked tại Start — không init camera/IoCard/while loop. Operator nhận message actionable; Start vẫn enabled để sửa recipe.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Chặn combo config nguy hiểm trước khi chạy vision sai |
| Operator experience | Thông báo rõ thay vì pass/fail im lặng sai |
| MES/SFIS integrity | Tránh upload MES từ pipeline sai model |
| Maintainability | Guard một chỗ đầu `startprogram` |
| Debugging / troubleshooting | Log `SENSOR_GUARD_BLOCK` với model + recipe path |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-SENSOR-002 | `is_sensor=True`, recipe SKY | Click Start | Blocked QMessageBox; Start enabled; không init IoCard |
| T-SENSOR-002b | MR6500 + sensor | Click Start | Sensor loop bình thường (G-01) |
| T-SENSOR-002c | SKY manual (`is_sensor=False`) | Click Start | Manual `go_run3` — không regression (G-05) |

#### Rollback

Xóa block `ok, msg = self.validate_sensor_mode()` → `return`. **Wrong pipeline quay lại** — chỉ rollback nếu guard chặn sai MR6500 hợp lệ.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 1 | Guard production an toàn; **audit recipe `is_sensor=true` trước deploy** |

---

### SENSOR-003A

#### Code Location

| Item | Value |
|------|-------|
| File | `sky.py` |
| Class | `Demo` |
| Function | `__init__` |
| Anchor | G181 / F `python_obj["choose_model"]` |
| Insert point | Ngay sau `selected_file = python_obj["choose_model"]` |

#### Current Problem

Khi guard chặn Start, log thiếu đường dẫn recipe JSON — engineer không biết file model nào gây block mà không mở UI.

#### Before Improvement

`SENSOR_GUARD_BLOCK` log chỉ có `model=` và `is_sensor=` — không có `recipe=` path.

#### Required Change

**+1 dòng** `self.model_json_path = selected_file` sau gán `selected_file` từ config trong `__init__`.

#### After Improvement

Launch-time load ghi nhớ recipe path; SENSOR-002 log đầy đủ `recipe=` cho audit.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | N/A |
| Operator experience | N/A |
| MES/SFIS integrity | N/A |
| Maintainability | Path dùng chung cho guard + preflight (DEP-P01) |
| Debugging / troubleshooting | Log guard có recipe path ngay từ boot |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-SENSOR-003 | Boot với config `choose_model` hợp lệ | Trigger guard block | Log `SENSOR_GUARD_BLOCK` có `recipe=` path từ `__init__` |

#### Rollback

Xóa dòng `self.model_json_path = selected_file` trong `__init__`. Rủi ro thấp — chỉ mất path trong log.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 1 | 1 dòng, low-risk; ship cùng SENSOR-001/002 |

---

### SENSOR-003B

#### Code Location

| Item | Value |
|------|-------|
| File | `sky.py` |
| Class | `Demo` |
| Function | `choose_model` |
| Anchor | G404 / F `def choose_model` |
| Insert point | Ngay sau `selected_file = "\\".join(...)` |

#### Current Problem

Đổi recipe qua file dialog không cập nhật `model_json_path` — log guard sau đổi recipe vẫn hiện path cũ hoặc `unknown`.

#### Before Improvement

Chỉ `__init__` load path lần đầu; `choose_model` không ghi lại `selected_file`.

#### Required Change

**+1 dòng** `self.model_json_path = selected_file` sau gán `selected_file` trong `choose_model`.

#### After Improvement

Mỗi lần engineer đổi recipe, path mới được track — log và preflight dùng file đúng.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | N/A |
| Operator experience | N/A |
| MES/SFIS integrity | N/A |
| Maintainability | Path sync giữa boot và runtime recipe change |
| Debugging / troubleshooting | Đổi recipe → path mới trong log ngay |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-SENSOR-003b | Đổi recipe qua `choose_model` | Trigger guard block | Log `recipe=` path mới, không path cũ |

#### Rollback

Xóa dòng `self.model_json_path` trong `choose_model`. Giữ SENSOR-003A nếu vẫn cần path lúc boot.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 1 | 1 dòng; ship ngay sau SENSOR-003A |

---

### SENSOR-004

#### Code Location

| Item | Value |
|------|-------|
| File | `sky.py` |
| Class | `Demo` |
| Function | `choose_model` |
| Anchor | G422 / F `self.is_sensor=modelinfo.get` |
| Insert point | Cuối block load model, trước `#check camera` |

#### Current Problem

Operator chỉ thấy cảnh báo combo sai khi bấm Start — không có early warning lúc load recipe.

#### Before Improvement

Load recipe SKY + sensor im lặng; operator có thể không biết config sai cho đến khi Start.

#### Required Change

**Chèn** (optional) gọi `validate_sensor_mode()`; nếu `not ok` → `logging.warning` + emit `WARNING:` trên textbox — **không** `QMessageBox.critical` (không chặn engineer sửa file).

#### After Improvement

WARNING non-blocking khi load recipe sai combo — operator/engineer thấy sớm; SENSOR-002 vẫn chặn cứng tại Start.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Giảm khả năng operator Start mà không đọc recipe |
| Operator experience | Cảnh báo sớm trên textbox khi load |
| MES/SFIS integrity | N/A |
| Maintainability | Tái dùng `validate_sensor_mode` từ SENSOR-001 |
| Debugging / troubleshooting | Warning log lúc load, không cần reproduce Start |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-SENSOR-004 | Load recipe SKY + sensor | Xem textbox | WARNING non-blocking; chưa Start vẫn thấy |
| T-SENSOR-004b | Load MR6500 + sensor | Xem textbox | Không WARNING |

#### Rollback

Xóa block `ok, msg = self.validate_sensor_mode()` warning trong `choose_model`. Rủi ro thấp — SENSOR-002 vẫn chặn tại Start.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 2 (optional) | Warning UX, không blocker production |

---

## Bảng tổng

| ID | Vấn đề | Đi tới | Anchor (đúng chỗ khi thấy…) | Thao tác | Test |
|----|--------|--------|-----------------------------|----------|------|
| **SENSOR-001** | Thiếu hàm validate | G617 / F `def startprogram` | Ngay **trước** `def startprogram` · **Sai:** chèn vào giữa `go_run1` | **Chèn** method `validate_sensor_mode` (class `Demo`) | Gọi tay: SKY+sensor → `(False, msg)` |
| **SENSOR-002** | Start sensor non-MR6500 chạy pipeline sai | G617 / F `def startprogram` | Đầu `try:`, **trước** `self.ekkoshan=camera()` · **Sai:** sau `pushButton_2.setEnabled(False)` | **Chèn** guard + `return` | SKY+sensor → blocked, Start enabled |
| **SENSOR-003A** | Log thiếu recipe path (`__init__`) | G181 / F `python_obj["choose_model"]` | Sau `selected_file = python_obj["choose_model"]` · **Sai:** sau `json.load` | **+1 dòng** `self.model_json_path = selected_file` | Log guard có path |
| **SENSOR-003B** | Log thiếu recipe path (`choose_model`) | G404 / F `def choose_model` | Sau `selected_file = "\\".join(...)` · **Sai:** trong block Cambrian | **+1 dòng** `self.model_json_path = selected_file` | Đổi recipe → path mới trong log |
| **SENSOR-004** | Operator không thấy cảnh báo sớm (optional) | G422 / F `self.is_sensor=modelinfo.get` trong `choose_model` | Cuối block load model, trước `#check camera` · **Sai:** trong `startprogram` | **Chèn** warning non-blocking | Load SKY+sensor → WARNING trên textbox |

**Ship:** SENSOR-001 → SENSOR-003A/B → SENSOR-002 → SENSOR-004 (optional)

**Bug gốc (không sửa trong phase này — chỉ guard):** `go_run2` analysis G829 hardcode MR6500. Xem `02_shared_dispatcher_design.md`.

---

## Context — tại sao guard ở đây

```text
is_sensor=True:  startprogram → go_run1 → test2 → go_run2 → show_image_MR6500  (LUÔN)
is_sensor=False: startprogram → go_run1 → test3 → go_run3 → dispatch theo select_model
```

| Cấu hình sai | Operator thấy | Thực tế chạy |
|--------------|---------------|--------------|
| SKY + `is_sensor=True` | UI/recipe SKY | Pipeline MR6500 (hash/barcode sai) |
| Button_check + sensor | Dialog scan OK | Vision MR6500 — không Cambrian |
| Thiếu key `is_sensor` (default `True`) | Recipe non-MR6500 | **Blocked** sau SENSOR-002 |

---

## Diff patches

### SENSOR-001 · method mới, trước `startprogram` G617

**Đúng chỗ:** ngay trước `def startprogram(self):` · **Sai:** bên trong `go_run1`/`go_run2`

```python
# TRƯỚC
    def trainstart(self):
        ...
        #     if is_ok == 0:
        #         self.preview_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    def startprogram(self):
        try:
            self.ekkoshan=camera()

# SAU — thêm method (4 spaces indent, cùng class Demo)
    SENSOR_SUPPORTED_MODELS = {"MR6500"}

    def validate_sensor_mode(self):
        """Returns (ok: bool, message: str)."""
        if not self.is_sensor:
            return True, ""
        if self.select_model in self.SENSOR_SUPPORTED_MODELS:
            return True, ""
        msg = (
            "Sensor mode currently supports MR6500 only.\n\n"
            f"Loaded model: {self.select_model}\n"
            "Sensor mode: ON\n\n"
            "This station cannot run the selected product with the sensor trigger.\n"
            "Contact engineering to:\n"
            "  • Switch recipe to MR6500, or\n"
            "  • Turn off sensor mode (is_sensor=false) in the model file.\n\n"
            "Do not test parts until configuration is fixed."
        )
        return False, msg

    def startprogram(self):
        try:
            self.ekkoshan=camera()
```

Rollback: xóa `SENSOR_SUPPORTED_MODELS` + `validate_sensor_mode`.

---

### SENSOR-002 · đầu `startprogram` G617

**Đúng chỗ:** dòng đầu `try:`, **trước** `self.ekkoshan=camera()` và **trước** `pushButton_2.setEnabled(False)` · **Sai:** sau `if self.is_sensor:` / sau IoCard G630

```python
# TRƯỚC
    def startprogram(self):
        try:
            self.ekkoshan=camera()
            logging.info("camera open,wait grap")
            self.myuihand.textbox.emit("camera open,wait grap")
            self.wait_test=True
            self.scan_sta=False
            self.stop_program=False
            self.pushButton_2.setEnabled(False)
            
            
            if  self.is_sensor:
                
                self.iocard = IoCard(deviceDescription = "PCI-1756,BID#0",profilePath = u"profile\\pci1756.xml")

# SAU
    def startprogram(self):
        try:
            ok, msg = self.validate_sensor_mode()
            if not ok:
                recipe = getattr(self, "model_json_path", "unknown")
                logging.error(
                    f"SENSOR_GUARD_BLOCK model={self.select_model} "
                    f"is_sensor={self.is_sensor} recipe={recipe}"
                )
                self.myuihand.textbox.emit(msg.replace("\n", " | "))
                QMessageBox.critical(self, "Configuration Error", msg)
                return  # Start stays enabled — do NOT disable pushButton_2

            self.ekkoshan=camera()
            logging.info("camera open,wait grap")
            self.myuihand.textbox.emit("camera open,wait grap")
            self.wait_test=True
            self.scan_sta=False
            self.stop_program=False
            self.pushButton_2.setEnabled(False)
            
            
            if  self.is_sensor:
                
                self.iocard = IoCard(deviceDescription = "PCI-1756,BID#0",profilePath = u"profile\\pci1756.xml")
```

Rollback: xóa block `ok, msg = self.validate_sensor_mode()` → `return`.

---

### SENSOR-003A · `__init__` load model G181

**Đúng chỗ:** ngay sau gán `selected_file` từ config · **Sai:** sau `self.is_sensor=...`

```python
# TRƯỚC
                selected_file = python_obj["choose_model"]

                modelinfo=json.load(open(selected_file,'r',encoding="utf8"))

# SAU
                selected_file = python_obj["choose_model"]
                self.model_json_path = selected_file

                modelinfo=json.load(open(selected_file,'r',encoding="utf8"))
```

---

### SENSOR-003B · `choose_model` G404

**Đúng chỗ:** ngay sau `selected_file = "\\".join(...)` · **Sai:** sau block Cambrian init

```python
# TRƯỚC
                selected_file = "\\".join(((self.file_dialog.selectedFiles())[0]).split("/"))

                modelinfo=json.load(open(selected_file,'r',encoding="utf8"))

# SAU
                selected_file = "\\".join(((self.file_dialog.selectedFiles())[0]).split("/"))
                self.model_json_path = selected_file

                modelinfo=json.load(open(selected_file,'r',encoding="utf8"))
```

Rollback SENSOR-003: xóa 2 dòng `self.model_json_path`.

---

### SENSOR-004 · cảnh báo lúc load (optional) G422

**Đúng chỗ:** sau `self.is_sensor=modelinfo.get("is_sensor", True)` trong `choose_model`, trước `#check camera` · **Sai:** dùng `QMessageBox.critical` (chặn engineer sửa file)

```python
# TRƯỚC
                self.is_sensor=modelinfo.get("is_sensor", True)
                self.HH4K=modelinfo


                if cambrian["is_cambrian"] == True:

# SAU
                self.is_sensor=modelinfo.get("is_sensor", True)
                self.HH4K=modelinfo

                ok, msg = self.validate_sensor_mode()
                if not ok:
                    logging.warning(msg.replace("\n", " | "))
                    self.myuihand.textbox.emit(f"WARNING: {msg.replace(chr(10), ' | ')}")

                if cambrian["is_cambrian"] == True:
```

Rollback: xóa block `ok, msg = self.validate_sensor_mode()` warning.

---

## Evidence bug gốc (go_run2 — không patch trong file này)

**Đi tới:** analysis G795 / F `def go_run2` · **Đúng chỗ:** trong `go_run2`, nhánh `sensor_start`, sau `get_image()` · **Sai:** `show_image_MR6500` trong `go_run3` (manual MR6500 branch — đúng behavior)

```python
# HIỆN TRẠNG (analysis L813–830) — đây là bug, guard chặn trước khi vào path này
            elif mysta[0]==int(self.sensor_start) and self.wait_test==False:
                logging.info("DUT FOUND,start camera")
                self.myuihand.textbox.emit("DUT FOUND,start camera")
                time.sleep(5)
                ekko,shan=self.ekkoshan.get_image()
                self.shan=shan
                self.show_image_MR6500(self.shan)   # ← hardcoded, không check select_model
                self.wait_test=True
```

**Emit sensor** (repo G644–654 / analysis G687–697) — guard chặn **trước** khi tới đây:

```python
# startprogram — sensor branch
                while True:
                    if self.wait_test and self.stop_program==False:
                        ...
                        self.myuihand.test1.emit()          # → go_run1
                        if self.scan_sta and self.stop_program==False:
                            ...
                            self.myuihand.test2.emit()      # → go_run2 (MR6500 only today)
```

---

## Verification

| Test ID | Fix ID | Setup | Action | Expected result |
|---------|--------|-------|--------|-----------------|
| T-SENSOR-001 | SENSOR-001 | Gọi tay `validate_sensor_mode()` với SKY + `is_sensor=True` | Unit call | Trả `(False, msg)`; MR6500 trả `(True, "")` |
| T-SENSOR-002 | SENSOR-002 | `is_sensor=True`, recipe SKY | Click Start | Blocked QMessageBox; Start enabled; **không** init IoCard/MR6500 |
| T-SENSOR-003 | SENSOR-003A/B | Đổi recipe qua `choose_model` | Trigger guard block | Log `SENSOR_GUARD_BLOCK` có `recipe=` path mới |
| T-SENSOR-004 | SENSOR-004 | Load recipe SKY + sensor | Xem textbox | WARNING non-blocking khi load, chưa Start |

Chi tiết matrix G-01…G-09 bên dưới.

## Test matrix

| # | select_model | is_sensor | Action | Kỳ vọng |
|---|--------------|-----------|--------|---------|
| G-01 | MR6500 | True | Start | Sensor loop bình thường; `go_run2` MR6500 |
| G-02 | SKY | True | Start | **Blocked** — QMessageBox; Start enabled; không IoCard |
| G-03 | Button_check | True | Start | **Blocked** |
| G-04 | Cisco * | True | Start | **Blocked** |
| G-05 | SKY | False | Start | Manual `go_run3` — không regression |
| G-06 | MR6500 | False | Start | Manual `go_run3` MR6500 |
| G-07 | SKY | True → sửa JSON `is_sensor:false` | Start | SKY manual OK |
| G-08 | (thiếu key) | non-MR6500 | Start | **Blocked** — default `True` nguy hiểm |
| G-09 | Guard blocked | Check log | — | Có `model=` + `recipe=` path |

**Production audit (trước deploy):** export mọi model JSON → liệt kê `is_sensor=true` AND `model != "MR6500"` → sửa hoặc xác nhận trạm không dùng.

---

## Rollback

| Fix ID | Rollback | Behavior cũ quay lại | Rủi ro nếu rollback |
|--------|----------|----------------------|---------------------|
| SENSOR-001 | Xóa method `validate_sensor_mode` + `SENSOR_SUPPORTED_MODELS` | Không validate combo | Chỉ rollback cùng SENSOR-002/004 (caller) |
| SENSOR-002 | Xóa block guard đầu `startprogram` | Sensor non-MR6500 chạy MR6500 pipeline | **Wrong pipeline quay lại** — chỉ rollback nếu guard chặn sai MR6500 hợp lệ |
| SENSOR-003A/B | Xóa 2 dòng `model_json_path` | Log thiếu recipe path | Thấp |
| SENSOR-004 | Xóa block warning | Không cảnh báo lúc load | Thấp — SENSOR-002 vẫn chặn |

## Implementation Window

| Fix ID | Suggested window | Reason |
|--------|------------------|--------|
| SENSOR-001 | Week 1 | Method mới, không đổi flow — merge trước |
| SENSOR-003A/B | Week 1 | 2 dòng log, low-risk |
| SENSOR-002 | Week 1 | Guard production an toàn; **audit recipe `is_sensor=true` trước deploy** |
| SENSOR-004 | Week 2 (optional) | Warning UX, không blocker |

## Smoke (5 phút)

- [ ] G-02 SKY+sensor blocked, Start vẫn bấm được
- [ ] G-01 MR6500+sensor không regression
- [ ] G-05 SKY manual không regression
- [ ] Log G-09 có `SENSOR_GUARD_BLOCK` + recipe path

## Ref

`00_playbook_sop.md` · `01_priority_roadmap.md` P2 · `02_shared_dispatcher_design.md` (fix dài hạn) · `08_model_dispatch.md` §Sensor exception
