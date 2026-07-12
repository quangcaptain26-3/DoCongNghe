# Import Ngoài & Asset Hardcode — Compact Playbook

**File:** `sky.py` + bundle trạm · **Workstream:** `04_dependency_deployment`  
**Nguồn:** `07_camera_io_sfis.md` §1, §8, `10_risks_and_bugs.md`, `00_project_overview.md`  
**Luật:** Mọi đường dẫn tương đối resolve từ `os.getcwd()` (`basicdir` G46) — khởi chạy app từ thư mục gốc trạm.

> Line repo hiện tại: import G7/G29/G37, `IoCard(...)` G630, `ipex_check` G727/G738, `basicdir` G46. Analysis drift ~40 dòng so với `07`. **Ctrl+F anchor** trước khi sửa.

### Pre-check repo

| Kiểm tra | Anchor | Kỳ vọng |
|----------|--------|---------|
| Class `Demo` + `__init__` | F `class Demo` hoặc F `def __init__` trong class chính | Có wrapper class — không phải `self.` ở module level G117 |
| `python_obj` load | F `python_obj` + `config.json` | `python_obj = json.load(...)` ở đầu `__init__` |
| Sensor IO | F `IoCard(` | Import không bị comment nếu trạm sensor |

---

## Improvement Purpose

Mục tiêu của cải tiến này là sửa import comment nhưng vẫn gọi (`IoCard`, `ipex_check_yolo`), tạo folder `source/` tự động, và fix syntax asset — tránh crash khi Start trên trạm production/station mới thiếu dependency hoặc thư mục.

## Before Improvement

Trước cải tiến: `#from ioCardNew import IoCard` (G29) nhưng `IoCard(...)` vẫn gọi (G630) → NameError sensor Start; tương tự `ipex_check_yolo` comment (G37) nhưng dùng G738; thiếu `source/` → `cv2.imwrite` crash; `model_and_90` dict syntax sai. Trạm mới hoặc clone thiếu file → crash ngay Start hoặc mid-cycle.

## After Improvement

Sau cải tiến: uncomment import đúng module; `os.makedirs("source", "source/8P", exist_ok=True)` tại `__init__`; fix dict syntax; bundle checklist đi kèm. Start sensor/ipex không NameError; imwrite an toàn; message lỗi rõ nếu module ngoài repo vẫn thiếu.

## Improvement Value

| Area                        | Value |
| --------------------------- | ----- |
| Production stability        | Giảm crash Start do import/folder thiếu |
| Operator experience         | Start sensor/ipex không NameError — lỗi rõ nếu bundle thiếu |
| MES/SFIS integrity          | N/A |
| Maintainability             | Import table reference; rollback từng DEP item |
| Debugging / troubleshooting | Biết chính xác module/path thiếu từ import table |

## Before / After Summary

| Aspect           | Before | After |
| ---------------- | ------ | ----- |
| Runtime behavior | Sensor Start → NameError; imwrite crash no source/ | Import OK; source/ auto-created |
| Error handling   | Crash opaque | Fail fast với ImportError rõ hoặc mkdir prevent |
| Operator impact  | Không Start được sensor line | Start OK khi bundle đủ |
| Production risk  | P0 crash trên trạm mới | Giảm lỗi triển khai; dễ audit env |

---

## Per-Fix Detail

### DEP-001

#### Code Location

| Item | Value |
|------|-------|
| File | `sky.py` |
| Anchor | G29 / F `#from ioCardNew` |
| Insert point | Dòng import đầu file, cạnh `basler_my` |
| Call site | G630 `IoCard(...)` trong `startprogram` sensor branch |

#### Current Problem

`#from ioCardNew import IoCard` bị comment nhưng `IoCard(...)` vẫn gọi khi sensor Start → **NameError**.

#### Before Improvement

Sensor trạm không Start được; crash opaque ngay khi vào sensor branch.

#### Required Change

**Bỏ `#`** — uncomment `from ioCardNew import IoCard`. Bundle: `ioCardNew.py`, driver Advantech, `profile\pci1756.xml`.

#### After Improvement

Import resolve; IoCard init khi `is_sensor=True` và bundle đủ.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | P0 — sensor line runnable |
| Operator experience | Start sensor không NameError |
| MES/SFIS integrity | N/A |
| Maintainability | Import table DEP-B10 aligned |
| Debugging / troubleshooting | Fail rõ nếu module vẫn thiếu (ImportError) |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-DEP-001 | `is_sensor=True`, `ioCardNew` + profile trên trạm | Click Start | Không `NameError: IoCard`; IO init |

#### Rollback

Comment lại import; set `is_sensor=false` trên trạm không có IO hardware.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 1 | P0 — sensor Start NameError |

---

### DEP-002

#### Code Location

| Item | Value |
|------|-------|
| File | `sky.py` |
| Anchor | G37 / F `# from ipex_check_yolo` |
| Insert point | Block import L37 |
| Call site | G738 `camera_check_ipex(...)` nhánh `ipex_check` G727 |

#### Current Problem

`ipex_check_yolo` import comment nhưng `camera_check_ipex` vẫn gọi → NameError trên trạm ipex.

#### Before Improvement

Trạm `ipex_check` crash mid-cycle khi vào vision branch.

#### Required Change

**Bỏ `#`** — uncomment `from ipex_check_yolo import camera_check_ipex`. Ship module `ipex_check_yolo` trên bundle.

#### After Improvement

ipex branch gọi module OK; Pass/Fail cycle bình thường.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | P0 cho trạm ipex active |
| Operator experience | Không NameError |
| MES/SFIS integrity | N/A |
| Maintainability | Cùng PR pattern DEP-001 |
| Debugging / troubleshooting | Preflight P-18 catches missing module |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-DEP-002 | Model `ipex_check`, module bundle đủ | 1 chu kỳ | Pass/Fail bình thường |

#### Rollback

Comment import; không deploy model `ipex_check`.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 1 | P0 nếu trạm ipex active; cùng PR DEP-001 |

---

### DEP-003

#### Code Location

| Item | Value |
|------|-------|
| File | `sky.py` |
| Class | `Demo` |
| Function | `__init__` |
| Anchor | G312 / F `self.pushButton_2.clicked.connect` |
| Insert point | Trong `__init__`, trước `#頁面語言轉換` / signal connect |

#### Current Problem

Thiếu `source/`, `source/8P/` → `cv2.imwrite` crash (MR6500 G1938, Cisco G3354+, SKY G2698+, Nanook G4801+).

#### Before Improvement

Trạm mới clone không có thư mục — vision mid-cycle exception.

#### Required Change

**Chèn** `os.makedirs(os.path.join(basicdir, "source"), exist_ok=True)` và `source/8P` tương tự trong `__init__`.

#### After Improvement

Folders tự tạo lúc boot; imwrite an toàn; hỗ trợ DEP-P04 Cisco check.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Giảm imwrite crash first-run |
| Operator experience | Cycle hoàn tất, ảnh lưu được |
| MES/SFIS integrity | N/A |
| Maintainability | 2 dòng, không scatter mkdir trong pipeline |
| Debugging / troubleshooting | Xóa `source/` + restart → verify auto-create |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-DEP-003 | Xóa `source/` rồi restart app | SKY STEP 3 / Cisco cycle | imwrite không crash; folder tự tạo |

#### Rollback

Xóa 2 dòng `os.makedirs`; tạo thư mục thủ công trên trạm.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 1–2 | 2 dòng low-risk; prerequisite DEP-P02 writable checks |

---

### DEP-004

#### Code Location

| Item | Value |
|------|-------|
| File | `sky.py` |
| Scope | Module level |
| Anchor | G106 / F `model_and_90={` |
| Usage | G3450, G3479, G3518, G3557, G3599 |

#### Current Problem

Dict `model_and_90` syntax sai — Python nối chuỗi `"C10"+"00-8P-2G-L"` → key lệch, barcode Cisco match silent wrong.

#### Before Improvement

liaohao `90BBA61002G0` map tới key sai → false pass/fail barcode.

#### Required Change

**Sửa** value thành một string đầy đủ `"C1000-8P-2G-L"` (verify key khớp SFIS production).

#### After Improvement

`model_and_90[liaohao] in barcode_list[...]` match đúng model string.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Cisco barcode gate đúng |
| Operator experience | Pass/fail phản ánh đúng model |
| MES/SFIS integrity | Fail upload đúng lý do |
| Maintainability | Một dict module-level |
| Debugging / troubleshooting | DUT thật `90BBA61002G0` verify match |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-DEP-004 | Cisco DUT `90BBA61002G0` | STEP barcode match | Key `"C1000-8P-2G-L"` match đúng |

#### Rollback

Git restore dict block. **Không khuyến nghị** — barcode match sai quay lại.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 2 | Cần verify key khớp SFIS production trước merge |

---

### DEP-005

#### Code Location

| Item | Value |
|------|-------|
| File | `sky.py` |
| Anchor import | G7 / F `predict_change` |
| Anchor caller | G2407 `yolov5_inference`; G2976 `show_image_SKY_yolo` |
| Production path | `show_image_SKY` (Cambrian) — không gọi YOLO |

#### Current Problem

YOLO import comment + dead path `yolov5_inference` — nếu bật nhầm → NameError; production SKY không dùng YOLO nhưng code path tồn tại.

#### Before Improvement

Dev có thể gọi `show_image_SKY_yolo` → crash hoặc behavior không support.

#### Required Change

**P3 — chọn một:** Option A — giữ comment + SOP "không gọi YOLO path"; Option B — guard `raise RuntimeError` đầu `yolov5_inference`.

#### After Improvement

Production SKY không ảnh hưởng; dead path explicit disabled hoặc documented.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Không accidental YOLO invoke |
| Operator experience | N/A (production dùng Cambrian) |
| MES/SFIS integrity | N/A |
| Maintainability | Doc dead path rõ |
| Debugging / troubleshooting | RuntimeError rõ nếu Option B |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-DEP-005 | Option B guard deployed | Gọi `yolov5_inference` | RuntimeError rõ |
| T-DEP-005b | Production SKY | Full cycle | Cambrian path không regression |

#### Rollback

Xóa guard; restore import nếu cần dev only.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 2–3 (P3) | Doc/guard — không blocker production |

---

### DEP-006

#### Code Location

| Item | Value |
|------|-------|
| File | `sky.py` |
| Scope | Module level |
| Anchor | G47 / F `todaytime = datetime` |
| Call sites | G569 `create_log`; imwrite `pciture_save//todaytime`; G302 mkdir |

#### Current Problem

`todaytime` set lúc import — app chạy qua nửa đêm ghi log/ảnh vào folder ngày cũ.

#### Before Improvement

Date folder frozen tại process start time.

#### Required Change

**P2 optional:** helper `get_todaytime()`; dần thay call sites; giữ `todaytime = get_todaytime()` compat.

#### After Improvement

Log và ảnh sau 0h vào folder ngày mới (khi call sites migrated).

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Đúng date partition cho archive |
| Operator experience | Tìm ảnh/log đúng ngày |
| MES/SFIS integrity | N/A |
| Maintainability | Incremental call site migration |
| Debugging / troubleshooting | Mock time test qua midnight |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-DEP-006 | App qua nửa đêm (hoặc mock time) | Test cycle sau 0h | Log/ảnh folder ngày mới |

#### Rollback

Khôi phục constant module-level `todaytime`.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Month 1 (P2 optional) | Rollover hiếm; cần đổi call site dần |

---

## Bảng tổng

| ID | Vấn đề | Đi tới | Anchor (đúng chỗ khi thấy…) | Thao tác | Test |
|----|--------|--------|-----------------------------|----------|------|
| **DEP-001** | `IoCard` comment nhưng sensor gọi | G29 / F `#from ioCardNew` | Dòng import đầu file, cạnh `basler_my` · **Sai:** sửa G630 | **Bỏ `#`** uncomment import | Sensor Start → không NameError |
| **DEP-002** | `ipex_check_yolo` comment | G37 / F `# from ipex_check_yolo` | Block import L37 · **Sai:** sửa trong `show_image_*` | **Bỏ `#`** uncomment import | `ipex_check` Start → không NameError |
| **DEP-003** | Thiếu `source/` → `imwrite` crash | G312 / F `self.pushButton_2.clicked.connect` | Trong `__init__`, **trước** `#頁面語言轉換` / signal connect · **Sai:** trong pipeline vision | **Chèn** `os.makedirs` ×2 | Cisco/SKY `imwrite` OK |
| **DEP-004** | `model_and_90` dict syntax sai | G106 / F `model_and_90={` | Module level dict Cisco 90-code · **Sai:** `nanook_model_tan` | **Sửa** string key `"C1000-8P-2G-L"` | Cisco barcode match đúng |
| **DEP-005** | YOLO dead path + import comment | G7 / F `predict_change` | Import L7 + caller G2407 trong `yolov5_inference` · **Sai:** `show_image_SKY` production | **P3:** giữ comment + doc dead path HOẶC guard raise | Production SKY không gọi YOLO |
| **DEP-006** | `todaytime` đóng băng lúc import | G47 / F `todaytime = datetime` | Module level · **Sai:** trong `create_log` only | **P2 optional:** helper `get_todaytime()` | Qua nửa đêm → folder đúng |

**Ship:** DEP-001 → DEP-002 → DEP-003 → DEP-004 → (bundle `UI/`, `basler_my`, `sfisapi` theo checklist `01`)

---

## Bảng import (reference)

| Import | G | Trạng thái | Gọi từ | Lỗi nếu thiếu |
|--------|---|------------|--------|---------------|
| `UI.Ui_MainWindow` | 10 | ✅ | Class chính | ImportError |
| `sfisapi` | 11 | ✅ | `__init__` SFIS | ImportError |
| `basler_my.camera` | 28 | ✅ | Init, `startprogram` | ImportError |
| **`ioCardNew.IoCard`** | 29 `#` | ❌ comment, **dùng** G630 | `startprogram` sensor | **NameError** |
| **`ipex_check_yolo.camera_check_ipex`** | 37 `#` | ❌ comment, **dùng** G738 | `ipex_check` branch G727 | **NameError** |
| **`yolov5.classify.predict_change`** | 7 `#` | ❌ dead path G2407 | `yolov5_inference` | NameError nếu bật YOLO |
| `PaddleOCR`, `pyzbar`, `pylibdmtx` | 30–35 | ✅ | Pipeline OCR/barcode | Fail theo model |

---

## Diff patches

### DEP-001 · uncomment `IoCard` G29

**Đúng chỗ:** đầu file, sau `from basler_my import camera` · **Sai:** copy `IoCard` vào `startprogram`

```python
# TRƯỚC
from basler_my import camera
#from ioCardNew import IoCard
from pylibdmtx import pylibdmtx

# SAU
from basler_my import camera
from ioCardNew import IoCard
from pylibdmtx import pylibdmtx
```

**Bundle trạm (không code):** file `ioCardNew.py` (hoặc package) trên PYTHONPATH + driver Advantech + `profile\pci1756.xml` (dùng tại G630).

Rollback: comment lại dòng import; tắt sensor (`is_sensor=false`) trên trạm không có IO.

---

### DEP-002 · uncomment `ipex_check` G37

**Đúng chỗ:** block import module local · **Sai:** inline class trong `sky.py`

```python
# TRƯỚC
from queue import Queue
# from ipex_check_yolo import camera_check_ipex

# SAU
from queue import Queue
from ipex_check_yolo import camera_check_ipex
```

**Gọi từ (không sửa nếu import OK):** G738 `mycheck_ipex= camera_check_ipex(self.shan,self.model_point)` trong nhánh `elif self.select_model=="ipex_check"` G727.

Rollback: comment import; không deploy model `ipex_check`.

---

### DEP-003 · `mkdir source/` trong `__init__` G312

**Đúng chỗ:** cuối block load `choose_route`, **trước** `self.trans = QTranslator` / signal connect · **Sai:** trong `show_image_Cisco` / từng `imwrite`

```python
# TRƯỚC
            try:
                os.makedirs(self.pciture_save + '\\' + todaytime)
            except FileExistsError:
                pass


        # self.imagesource_barcode = ImageSourceAgent(...

# SAU
            try:
                os.makedirs(self.pciture_save + '\\' + todaytime)
            except FileExistsError:
                pass

        os.makedirs(os.path.join(basicdir, "source"), exist_ok=True)
        os.makedirs(os.path.join(basicdir, "source", "8P"), exist_ok=True)

        # self.imagesource_barcode = ImageSourceAgent(...
```

**Đường dẫn bị ảnh hưởng nếu thiếu:**

| Path | G (mẫu) | Model |
|------|---------|-------|
| `source/MR6500.jpg` | G1938 | MR6500 |
| `source/8P/*.jpg` | G3354+ | Cisco |
| `source/model.jpg`, `topsn.jpg`, `clei.jpg` | G2698+ | SKY |
| `source/Nanook_*.jpg` | G4801+ | Nanook |

Rollback: xóa 2 dòng `os.makedirs`; tạo thư mục thủ công trên trạm.

---

### DEP-004 · sửa `model_and_90` G106

**Đúng chỗ:** dict module-level Cisco 90-code · **Sai:** `sky_clei` G112

```python
# TRƯỚC — Python nối chuỗi "C10"+"00-8P-2G-L" → key lệch
model_and_90={"90BBA61002G0":"C10"
                             "00-8P-2G-L","90BBA61002H0":"C1000-8T-2G-L", ...

# SAU — một string value đầy đủ (verify key khớp SFIS production)
model_and_90={"90BBA61002G0":"C1000-8P-2G-L","90BBA61002H0":"C1000-8T-2G-L", ...
```

**Dùng tại:** G3450, G3479, G3518, G3557, G3599 — `if model_and_90[liaohao] in barcode_list[...]`.

Rollback: git restore block dict; rủi ro match barcode Cisco sai.

---

### DEP-005 · YOLO dead path (P3 — chọn một)

**Đúng chỗ:** `yolov5_inference` G2396, caller `show_image_SKY_yolo` G2976 · **Sai:** `show_image_SKY` (production dùng Cambrian)

**Option A — giữ dead (khuyến nghị production):** không uncomment G7; ghi SOP "không gọi `show_image_SKY_yolo`".

**Option B — guard nếu phải giữ hàm:**

```python
# SAU — đầu yolov5_inference
    def yolov5_inference(self,yolo_name,yolo_list,yolo_img):
        raise RuntimeError("YOLO path disabled in production — use show_image_SKY (Cambrian)")
```

Rollback: xóa guard; restore import nếu cần dev.

---

### DEP-006 · `todaytime` rollover (P2 optional) G47

**Đúng chỗ:** thay module-level constant · **Sai:** chỉ sửa `create_log`

```python
# TRƯỚC
todaytime = datetime.now().strftime("%Y%m%d")

# SAU
def get_todaytime():
    return datetime.now().strftime("%Y%m%d")
todaytime = get_todaytime()  # compat; dần thay call sites bằng get_todaytime()
```

Call sites ưu tiên: `create_log` G569, `cv2.imwrite` path `pciture_save//todaytime`, `choose_route` mkdir G302.

Rollback: khôi phục constant module-level.

---

## Asset hardcode — anchor verify (không patch, bundle trạm)

### `point/*.json`

| File | G | Model |
|------|---|-------|
| `point/step1.json` … `step4.json` | G2016–G2019 | HH4K |
| `point/SKY_barcode.json`, `SKY_model1–3.json`, `SKY_model5.json` | G2525+ | SKY |
| `point/SKY_4G_*.json` | G2527+ | SKY_4G |
| `point/Button_check_model.json` | G4097 | Button_check |
| `point/WP_check_step3–6.json` | G4419+ | WP, C9105AXW_E |
| `point/Nanook_model1–4.json` | G4792+ | Nanook |

### `sample/*.jpg`

| Path | G | Ghi chú |
|------|---|---------|
| `sample/{liaohao}.jpg` | G1905 | MR6500 — động theo SFIS 90-code |
| `sample/step1–4.jpg` | G2024+ | HH4K golden |
| `sample/button_check.jpg` | G1270 | Button_check stub |
| `sample/C9105AXW_E/1–6.jpg` | G1331+ | C9105AXW_E |
| `sample/NANOOK/1–6.jpg` | G1560+ | Nanook stub |

### Stub / UX

| Hạng mục | G | Rủi ro |
|----------|---|--------|
| `change_camera` | G563–564 (`1` / pass) | Combo camera không đổi camera thật |
| `profile/pci1756.xml` | G630 | Sensor IoCard init fail |

---

## Verification

| Test ID | Fix ID | Setup | Action | Expected result |
|---------|--------|-------|--------|-----------------|
| T-DEP-001 | DEP-001 | `is_sensor=True`, `ioCardNew` + profile trên trạm | Click Start | Không `NameError: IoCard`; IO init |
| T-DEP-002 | DEP-002 | Model `ipex_check`, module bundle đủ | 1 chu kỳ | Không NameError; Pass/Fail bình thường |
| T-DEP-003 | DEP-003 | Xóa `source/` rồi restart app | SKY STEP 3 / Cisco cycle | `imwrite` không crash; folder tự tạo |
| T-DEP-004 | DEP-004 | Cisco DUT thật với liaohao `90BBA61002G0` | STEP barcode match | Key `"C1000-8P-2G-L"` match đúng, không silent mismatch |
| T-DEP-005 | DEP-005 | Option B guard deployed | Gọi `yolov5_inference` | RuntimeError rõ; production SKY không ảnh hưởng |
| T-DEP-006 | DEP-006 | App chạy qua nửa đêm (hoặc mock time) | Test cycle sau 0h | Log/ảnh vào folder ngày mới |

## Rollback

| Fix ID | Rollback | Behavior cũ quay lại | Rủi ro nếu rollback |
|--------|----------|----------------------|---------------------|
| DEP-001 | Comment lại import; set `is_sensor=false` | NameError khi sensor Start | Trạm sensor không chạy được |
| DEP-002 | Comment lại import | NameError ipex | Trạm ipex không chạy |
| DEP-003 | Xóa 2 dòng makedirs; mkdir tay | Crash nếu quên tạo folder | Phụ thuộc thao tác tay |
| DEP-004 | Git restore dict | Key nối chuỗi lệch | **Barcode Cisco match sai** — không khuyến nghị |
| DEP-005/006 | Xóa guard / khôi phục constant | Dead path + date freeze | Thấp |

## Implementation Window

| Fix ID | Suggested window | Reason |
|--------|------------------|--------|
| DEP-001 | Week 1 | P0 — sensor Start NameError |
| DEP-002 | Week 1 | P0 nếu trạm ipex active; cùng PR DEP-001 |
| DEP-003 | Week 1–2 | 2 dòng; chặn imwrite crash |
| DEP-004 | Week 2 | Cần verify key khớp SFIS production trước merge |
| DEP-005 | Week 2–3 (P3) | Doc/guard dead path — không blocker |
| DEP-006 | Month 1 (P2 optional) | Rollover hiếm; cần đổi call site dần |

## Smoke (5 phút)

- [ ] DEP-001 sensor Start không `NameError: IoCard`
- [ ] DEP-002 `ipex_check` một chu kỳ Pass/Fail
- [ ] DEP-003 xóa `source/` → restart → `imwrite` SKY/Cisco không crash
- [ ] DEP-004 Cisco DUT thật — barcode model match (không silent wrong key)
- [ ] Bundle: thiếu `UI/` → ImportError ngay launch

## Ref

`01_deployment_bundle_checklist.md` · `03_startup_preflight_check.md` · `07_camera_io_sfis.md` §1, §8
