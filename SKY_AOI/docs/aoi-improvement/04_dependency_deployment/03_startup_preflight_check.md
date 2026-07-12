# Preflight Khi Khởi Động — Compact Playbook

**File:** `sky.py` · **Workstream:** `04_dependency_deployment`  
**Nguồn:** `07_camera_io_sfis.md` §10–11, `10_risks_and_bugs.md`, `11_refactor_plan.md` §3.10, `02_external_imports_and_assets.md`  
**Luật:** `run_preflight()` chạy **đầu `startprogram`**, trước `camera()` / `IoCard` / `while True` — fail → `return`, **Start vẫn enabled**.

**Điều kiện:** DEP-001/002/003 từ `02_external_imports_and_assets.md`; SENSOR-002 từ `03_sensor_dispatch/01_sensor_mode_guard.md`.

> Hook: `startprogram` G617. Camera exit sớm G168–171 (analysis G211–214). **Ctrl+F** `def startprogram`.

---

## Improvement Purpose

Mục tiêu của cải tiến này là thêm `run_preflight()` đầu `startprogram` — validate config, camera, point/sample JSON, writable dirs, sensor policy trước khi mở camera/IoCard/while loop. Fail → return sớm, Start vẫn enabled, operator thấy danh sách lỗi rõ.

## Before Improvement

Trước cải tiến, Start không validate bundle: thiếu `point/step1.json`, `sample/*.jpg`, camera_id sai, `source/` không ghi được → exception mid-cycle hoặc stall `wait_test`. Engineer debug từng crash; operator không biết thiếu gì cho đến khi test fail giữa DUT.

## After Improvement

Sau cải tiến, `run_preflight()` check P-01→P-18 theo model: config, JSON, camera, point files, sample stub, ROI recipe, dirs writable, sensor guard, ipex module. Fail → MessageBox liệt kê lỗi, Start enabled. Optional warning khi đổi recipe thiếu file. First-run và đổi recipe an toàn hơn.

## Improvement Value

| Area                        | Value |
| --------------------------- | ----- |
| Production stability        | Chặn Start khi thiếu asset — giảm exception/stall mid-cycle |
| Operator experience         | Thông báo lỗi liệt kê rõ thay vì crash im lặng giữa test |
| MES/SFIS integrity          | N/A |
| Maintainability             | Ma trận check tập trung; dễ thêm model vào dict |
| Debugging / troubleshooting | Preflight log list errors — không cần reproduce mid-DUT |

## Before / After Summary

| Aspect           | Before | After |
| ---------------- | ------ | ----- |
| Runtime behavior | Start → crash/stall khi thiếu file giữa cycle | Preflight fail fast trước camera/loop |
| Error handling   | Exception trong vision/orchestration | Structured error list at Start |
| Operator impact  | Treo giữa test không rõ nguyên nhân | Blocked Start với message actionable |
| Production risk  | First-run/đổi recipe risky | Giảm downtime debug setup |

---

## Per-Fix Detail

### DEP-P01

#### Code Location

| Item | Value |
|------|-------|
| File | `sky.py` |
| Class | `Demo` |
| Function | (new `run_preflight`), before `startprogram` |
| Anchor | G617 / F `def startprogram` |
| Insert point | Ngay trước `def startprogram` · **Sai:** file `preflight.py` riêng (phase 2) |

#### Current Problem

Không có method tập trung validate bundle/config/camera/point/sample/writable dirs/sensor policy trước Start.

#### Before Improvement

Mọi check rải rác hoặc không tồn tại — thiếu file phát hiện mid-cycle.

#### Required Change

**Chèn** `MODEL_POINT_FILES`, `MODEL_SAMPLE_FILES`, `CISCO_MODELS`, helper `_import_available`, và method `run_preflight(self)` trả `(ok, errors, warnings)` — logic P-01→P-18 theo ma trận kiểm tra.

#### After Improvement

Một callable audit bundle; errors chặn Start; warnings (sample stub) không chặn. Tích hợp sensor guard (P-17), IoCard (P-16), ipex (P-18), Cisco `source/8P` (P-04/DEP-P04).

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Fail fast trước camera/IoCard/loop |
| Operator experience | Danh sách lỗi actionable |
| MES/SFIS integrity | N/A |
| Maintainability | Dict mở rộng per model |
| Debugging / troubleshooting | Unit call `run_preflight()` liệt kê thiếu sót |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-P01 | Gọi tay `run_preflight()` bundle thiếu point | Unit call | `(False, errors, warnings)` đúng file |
| T-P01b | Bundle đầy đủ | Unit call | `(True, [], warnings?)` |

#### Rollback

Xóa method + dict constants `MODEL_*_FILES`. Rollback cùng DEP-P02/P03 callers.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 2 | Sau DEP-001/002/003 + SENSOR-002 prerequisite |

---

### DEP-P02

#### Code Location

| Item | Value |
|------|-------|
| File | `sky.py` |
| Class | `Demo` |
| Function | `startprogram` |
| Anchor | G617 / F `self.ekkoshan=camera` |
| Insert point | Đầu `try:`, **trước** `ekkoshan=camera()` · **Sau** sensor guard SENSOR-002 nếu đã có |

#### Current Problem

Start không gọi preflight — thiếu `point/step1.json`, camera_id sai, dirs not writable → exception/stall sau khi mở camera.

#### Before Improvement

`startprogram` mở camera ngay; lỗi asset xuất hiện giữa DUT cycle.

#### Required Change

**Chèn** block: `pf_ok, pf_errors, pf_warnings = self.run_preflight()`; emit warnings; nếu `not pf_ok` → MessageBox critical + `return` (Start stays enabled).

#### After Improvement

Thiếu asset → blocked trước camera open; operator thấy bullet list lỗi; T-10 Start enabled sau fail.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Giảm exception mid-cycle |
| Operator experience | "Cannot start test — configuration problem" rõ |
| MES/SFIS integrity | N/A |
| Maintainability | Thứ tự: sensor guard → preflight → camera |
| Debugging / troubleshooting | Log error list một lần tại Start |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-P02 | Đổi tên `point/step1.json`, HH4K | Click Start | Blocked; tên file trong message; Start enabled |
| T-P02b | T-01 bundle OK | Start | Preflight OK; không regression |

#### Rollback

Xóa block `run_preflight()` trong `startprogram`. Lỗi asset quay lại giữa chu kỳ.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 2 | Cùng PR DEP-P01; test bundle thiếu trên clone |

---

### DEP-P03

#### Code Location

| Item | Value |
|------|-------|
| File | `sky.py` |
| Class | `Demo` |
| Function | `choose_model` |
| Anchor | G422 / F `self.is_sensor=modelinfo.get` |
| Insert point | Cuối load model, trước `#check camera` |
| Maps from | PREFLIGHT warning at recipe change (user alias) |

#### Current Problem

Operator/engineer đổi recipe không thấy thiếu file cho đến khi bấm Start.

#### Before Improvement

`choose_model` load model im lặng dù point/sample thiếu.

#### Required Change

**Chèn** (optional) gọi `run_preflight()` sau load; emit `WARNING:` / `RECIPE ISSUE:` trên textbox — **không** `QMessageBox.critical` chặn UI. Set `self.model_json_path = selected_file` (sync SENSOR-003B).

#### After Improvement

Early feedback khi đổi recipe; DEP-P02 vẫn chặn cứng tại Start.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Giảm Start với recipe broken |
| Operator experience | WARNING trên textbox ngay khi load |
| MES/SFIS integrity | N/A |
| Maintainability | Tái dùng `run_preflight` từ DEP-P01 |
| Debugging / troubleshooting | Không cần reproduce Start để thấy thiếu file |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-P03 | Đổi recipe thiếu file qua `choose_model` | Load recipe | WARNING/RECIPE ISSUE trên textbox; không chặn dialog |

#### Rollback

Xóa block preflight warning trong `choose_model`. Giữ `model_json_path` nếu SENSOR-003B deployed.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 2–3 (optional) | Warning UX sau P01/P02 stable |

---

### DEP-P04

#### Code Location

| Item | Value |
|------|-------|
| File | `sky.py` |
| Class | `Demo` |
| Function | `run_preflight` (logic trong DEP-P01) |
| Check | `os.path.isdir("source/8P")` nếu `select_model in CISCO_MODELS` |
| Related | DEP-003 auto-mkdir; DEP-B08 bundle |

#### Current Problem

Cisco family cần `source/8P/` cho OCR imwrite — thiếu → fail mid-step không rõ.

#### Before Improvement

Cisco Start OK nhưng STEP imwrite/OCR crash hoặc fail opaque.

#### Required Change

Trong `run_preflight`: nếu Cisco model → error nếu `source/8P` missing (hoặc OK sau DEP-003 auto-mkdir). Không patch riêng — nằm trong logic P01.

#### After Improvement

Cisco blocked tại Start nếu thiếu `source/8P` và DEP-003 chưa ship; hoặc pass sau DEP-003 tạo folder.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Cisco OCR path sẵn sàng trước cycle |
| Operator experience | Lỗi rõ "Missing source/8P/" |
| MES/SFIS integrity | N/A |
| Maintainability | Một check trong `run_preflight` |
| Debugging / troubleshooting | T-07 matrix Cisco |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-P04 | Cisco family, xóa `source/8P` | Start | Blocked hoặc OK sau DEP-003 |
| T-P04b | T-07 | Cisco + DEP-003 | Start OK |

#### Rollback

Xóa Cisco `source/8P` check khỏi `run_preflight` (không khuyến nghị). Hoặc rollback toàn DEP-P01.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 2 | Nằm trong logic DEP-P01; phụ thuộc DEP-003 |

---

## Bảng tổng

| ID | Vấn đề | Đi tới | Anchor (đúng chỗ khi thấy…) | Thao tác | Test |
|----|--------|--------|-----------------------------|----------|------|
| **DEP-P01** | Không có `run_preflight` | G617 / F `def startprogram` | Trước `def startprogram` · **Sai:** trong `create_log` | **Chèn** method + bảng `MODEL_*_FILES` | Gọi tay → list errors |
| **DEP-P02** | Start không validate bundle | G617 / F `self.ekkoshan=camera` | Đầu `try:` `startprogram`, **trước** `ekkoshan` · **Sai:** sau `pushButton_2.setEnabled(False)` | **Chèn** preflight block + `return` | Thiếu `point/step1.json` → blocked |
| **DEP-P03** | Operator không thấy sớm lúc đổi recipe | G422 / F `self.is_sensor=modelinfo.get` trong `choose_model` | Cuối load model, trước `#check camera` · **Sai:** `QMessageBox.critical` chặn UI | **Chèn** warning only | Đổi recipe thiếu file → WARNING |
| **DEP-P04** | Cisco thiếu `source/8P` | Trong P-01 logic | Check `os.path.isdir("source/8P")` nếu Cisco family | DEP-003 auto-mkdir hoặc P-02 error | Cisco Start OK |

**Ship:** DEP-003 (`02`) → DEP-001/002 → SENSOR-002 → DEP-P01 → DEP-P02 → DEP-P03 (optional)

### Ma trận kiểm tra (trong `run_preflight`)

| Check | Điều kiện | Chặn Start? | Evidence |
|-------|-----------|-------------|----------|
| P-01 | `config.json` tồn tại | Có | Load config |
| P-02–03 | Model JSON đọc được + key bắt buộc | Có | `choose_model` path |
| P-04 | `allcameras` non-empty | Có (redundant) | G168–171 đã exit launch |
| P-05 | `camera_id` ∈ `allcameras` | Có | G253–256 / analysis G296 |
| P-06 | `point/*.json` theo model | Có | G2016 HH4K; G2525 SKY |
| P-07 | `sample/*` stub | Cảnh báo | G2024 HH4K; G1560 Nanook |
| P-08 | ROI recipe `path_json` | Có | Model JSON |
| P-09 | `source/`, `source/8P/`, `log/` ghi được | Có | DEP-003 giảm fail |
| P-12 | `choose_route` / `pciture_save` ghi được | Có | G302 |
| P-16 | Sensor: IoCard import + `profile\pci1756.xml` | Có | G29, G630 |
| P-17 | Sensor guard MR6500 only | Có | `validate_sensor_mode` |
| P-18 | `ipex_check` → module import | Có | G37, G738 |

---

## Diff patches

### DEP-P01 · `run_preflight` + bảng file, trước `startprogram` G617

**Đúng chỗ:** class chính, ngay trước `def startprogram` · **Sai:** file `preflight.py` riêng (phase 2)

```python
# TRƯỚC
    def trainstart(self):
        ...

    def startprogram(self):
        try:

# SAU — rút gọn; mở rộng dict theo model
MODEL_POINT_FILES = {
    "HH4K": [f"point/step{i}.json" for i in range(1, 5)],
    "SKY": ["point/SKY_barcode.json", "point/SKY_model1.json", "point/SKY_model2.json",
            "point/SKY_model3.json", "point/SKY_model5.json"],
    "SKY_4G": ["point/SKY_4G_barcode.json", "point/SKY_4G_model1.json", "point/SKY_4G_model2.json",
               "point/SKY_4G_model3.json", "point/SKY_4G_model5.json"],
    "Button_check": ["point/Button_check_model.json"],
    "WP_check": [f"point/WP_check_step{i}.json" for i in range(3, 7)],
    "C9105AXW_E": [f"point/WP_check_step{i}.json" for i in range(3, 7)],
    "Nanook": [f"point/Nanook_model{i}.json" for i in range(1, 5)],
}
MODEL_SAMPLE_FILES = {
    "HH4K": [f"sample/step{i}.jpg" for i in range(1, 5)],
    "Button_check": ["sample/button_check.jpg"],
    "C9105AXW_E": [f"sample/C9105AXW_E/{i}.jpg" for i in range(1, 7)],
    "Nanook": [f"sample/NANOOK/{i}.jpg" for i in range(1, 7)],
}
CISCO_MODELS = frozenset({
    "C1000-8FP-E-2G-L", "C1000-8P-2G-L", "C1000-8T-2G-L",
    "C1200-8FP-2G", "C1200-8P-E-2G", "C1200-8T-E-2G",
    "C1300-8P-E-2G", "C1300-8T-E-2G", "C1000-8FP-2G-L",
    "C1000-8P-E-2G-L", "C1300-8FP-2G", "C1000-8T-E-2G-L",
})

    def _import_available(self, module_name, attr_name):
        try:
            mod = __import__(module_name, fromlist=[attr_name])
            return hasattr(mod, attr_name)
        except ImportError:
            return False

    def run_preflight(self):
        errors, warnings = [], []
        if not os.path.isfile("config.json"):
            errors.append("config.json not found")
            return False, errors, warnings

        model_path = getattr(self, "model_json_path", None)
        if not model_path or not os.path.isfile(model_path):
            errors.append(f"Model JSON not found: {model_path}")
            return False, errors, warnings

        try:
            with open(model_path, encoding="utf8") as f:
                modelinfo = json.load(f)
        except Exception as e:
            errors.append(f"Model JSON invalid: {e}")
            return False, errors, warnings

        if not getattr(self, "allcameras", None):
            errors.append("No Basler cameras detected")
        elif modelinfo.get("camera_id") not in self.allcameras:
            errors.append(f"camera_id {modelinfo.get('camera_id')} not in {self.allcameras}")

        path_json = modelinfo.get("path_json") or {}
        for key in ("barcode_path_json", "model_path_json"):
            p = path_json.get(key)
            if p and not os.path.isfile(p):
                errors.append(f"Missing recipe ROI: {p}")

        for p in MODEL_POINT_FILES.get(self.select_model, []):
            if not os.path.isfile(p):
                errors.append(f"Missing point file: {p}")

        for p in MODEL_SAMPLE_FILES.get(self.select_model, []):
            if not os.path.isfile(p):
                warnings.append(f"Missing sample (verify stub): {p}")

        for folder in ("source", "source/8P", "log"):
            try:
                os.makedirs(folder, exist_ok=True)
                test = os.path.join(folder, ".preflight_write_test")
                with open(test, "w") as fh:
                    fh.write("ok")
                os.remove(test)
            except OSError as e:
                errors.append(f"Not writable: {folder} ({e})")

        if hasattr(self, "pciture_save") and self.pciture_save:
            try:
                os.makedirs(self.pciture_save, exist_ok=True)
            except OSError as e:
                errors.append(f"choose_route not writable: {e}")

        if self.is_sensor:
            ok, msg = self.validate_sensor_mode()
            if not ok:
                errors.append(msg.replace("\n", " "))
            if not self._import_available("ioCardNew", "IoCard"):
                errors.append("ioCardNew.IoCard not importable — fix import L29")
            if not os.path.isfile(r"profile\pci1756.xml"):
                errors.append("Missing profile/pci1756.xml")

        if self.select_model == "ipex_check":
            if not self._import_available("ipex_check_yolo", "camera_check_ipex"):
                errors.append("ipex_check_yolo not importable — fix import L37")

        if self.select_model in CISCO_MODELS:
            if not os.path.isdir("source/8P"):
                errors.append("Missing source/8P/ (required for Cisco OCR)")

        return (len(errors) == 0), errors, warnings

    def startprogram(self):
        try:
```

Rollback: xóa method + dict constants.

---

### DEP-P02 · tích hợp `startprogram` G617

**Đúng chỗ:** đầu `try:`, **trước** `self.ekkoshan=camera()` · **Sau** sensor guard nếu đã có SENSOR-002 · **Sai:** trong `while True`

```python
# TRƯỚC
    def startprogram(self):
        try:
            self.ekkoshan=camera()
            logging.info("camera open,wait grap")
            ...
            self.pushButton_2.setEnabled(False)

# SAU — thứ tự khuyến nghị: sensor guard → preflight → camera
    def startprogram(self):
        try:
            ok, msg = self.validate_sensor_mode()
            if not ok:
                ...
                return

            pf_ok, pf_errors, pf_warnings = self.run_preflight()
            for w in pf_warnings:
                logging.warning(w)
                self.myuihand.textbox.emit(f"WARNING: {w}")
            if not pf_ok:
                body = "Cannot start test — configuration problem:\n\n" + "\n".join(
                    f"• {e}" for e in pf_errors
                )
                logging.error(body.replace("\n", " | "))
                self.myuihand.textbox.emit(body.replace("\n", " | "))
                QMessageBox.critical(self, "Preflight Failed", body)
                return  # Start stays enabled

            self.ekkoshan=camera()
            logging.info("camera open,wait grap")
            ...
            self.pushButton_2.setEnabled(False)
```

Rollback: xóa block `run_preflight()` → lỗi giữa chu kỳ như cũ.

---

### DEP-P03 · cảnh báo `choose_model` (optional) G422

**Đúng chỗ:** sau load `is_sensor`, trước `#check camera` · **Sai:** chặn bằng critical dialog

```python
# TRƯỚC
                self.is_sensor=modelinfo.get("is_sensor", True)
                self.HH4K=modelinfo


                if cambrian["is_cambrian"] == True:

# SAU
                self.is_sensor=modelinfo.get("is_sensor", True)
                self.HH4K=modelinfo
                self.model_json_path = selected_file

                pf_ok, pf_errors, pf_warnings = self.run_preflight()
                for w in pf_warnings:
                    self.myuihand.textbox.emit(f"WARNING: {w}")
                for e in pf_errors:
                    self.myuihand.textbox.emit(f"RECIPE ISSUE: {e}")

                if cambrian["is_cambrian"] == True:
```

Rollback: xóa block preflight warning (giữ `model_json_path` nếu dùng SENSOR-003).

---

## Thông báo operator (mẫu)

**Chặn — thiếu point:**
```text
Cannot start test — configuration problem:
• Missing point file: point/SKY_barcode.json
Contact engineering. Do not run parts until fixed.
```

**Chặn — sensor IoCard:**
```text
• ioCardNew.IoCard not importable — fix import L29
• Missing profile/pci1756.xml
```

---

## Verification

| Test ID | Fix ID | Setup | Action | Expected result |
|---------|--------|-------|--------|-----------------|
| T-P01 | DEP-P01 | Gọi tay `run_preflight()` với bundle thiếu point | Unit call | Trả `(False, errors, warnings)` liệt kê đúng file |
| T-P02 | DEP-P02 | Đổi tên `point/step1.json`, model HH4K | Click Start | Blocked; tên file trong message; Start enabled |
| T-P03 | DEP-P03 | Đổi recipe thiếu file qua `choose_model` | Load recipe | WARNING trên textbox, không chặn |
| T-P04 | DEP-P04 | Cisco family, xóa `source/8P` | Start | Blocked hoặc auto-mkdir (nếu DEP-003) |

Chi tiết matrix T-01…T-10 bên dưới.

## Test matrix

| # | Setup | Action | Kỳ vọng |
|---|-------|--------|---------|
| T-01 | Bundle đầy đủ | Start | Preflight OK |
| T-02 | Đổi tên `point/step1.json` | Start HH4K | Blocked; tên file trong message |
| T-03 | Gỡ quyền ghi `source/` | Start | Blocked |
| T-04 | SKY + `is_sensor=true` | Start | Blocked (sensor guard P-17) |
| T-05 | Sensor MR6500, IoCard comment | Start | Blocked P-16 |
| T-06 | Thiếu count JSON | Start | Warning only (mở rộng P-13 nếu cần) |
| T-07 | Cisco, không `source/8P/` | Start | Blocked hoặc OK sau DEP-003 |
| T-10 | Preflight fail | Check Start button | Vẫn enabled |

---

## Rollback

| Fix ID | Rollback | Behavior cũ quay lại | Rủi ro nếu rollback |
|--------|----------|----------------------|---------------------|
| DEP-P01 | Xóa method + bảng `MODEL_*_FILES` | Không validate bundle | Rollback cùng P02/P03 (caller) |
| DEP-P02 | Xóa block `run_preflight()` trong `startprogram` | Lỗi asset xuất hiện giữa chu kỳ như cũ | Crash/stall mid-cycle quay lại |
| DEP-P03 | Xóa block warning trong `choose_model` | Không cảnh báo lúc đổi recipe | Thấp — P02 vẫn chặn tại Start |

Nếu preflight chặn sai bundle hợp lệ (false positive): sửa bảng `MODEL_*_FILES` trên clone trước, không rollback toàn bộ.

## Implementation Window

| Fix ID | Suggested window | Reason |
|--------|------------------|--------|
| DEP-P01 | Week 2 | Sau DEP-001/002/003 + SENSOR-002 (prerequisite) |
| DEP-P02 | Week 2 | Cùng PR với P01; test bundle thiếu trên clone |
| DEP-P03 | Week 2–3 (optional) | Warning UX |
| DEP-P04 | Week 2 | Nằm trong logic P01 |

## Smoke (5 phút)

- [ ] T-02 HH4K thiếu point → blocked trước camera open
- [ ] T-01 bundle OK → không regression
- [ ] T-10 Start enabled sau fail
- [ ] Warning T-06 trên textbox, vẫn Start được (nếu chỉ warning)

## Ref

`01_deployment_bundle_checklist.md` · `02_external_imports_and_assets.md` · `03_sensor_dispatch/01_sensor_mode_guard.md`
