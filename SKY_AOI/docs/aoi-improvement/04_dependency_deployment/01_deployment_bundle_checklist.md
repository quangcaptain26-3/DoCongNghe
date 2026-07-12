# Checklist Gói Triển Khai — Compact Playbook

**File:** bundle trạm + `sky.py` · **Workstream:** `04_dependency_deployment`  
**Nguồn:** `07_camera_io_sfis.md` §11, `00_project_overview.md`, `11_refactor_plan.md` §3.14  
**Luật:** Repo git ≈ chỉ `sky.py` — mọi module/asset/directory phải đóng gói riêng; CWD = thư mục gốc trạm (`basicdir` G46).

> Không phải patch code — **verify + ship bundle**. Patch code: `02_external_imports_and_assets.md`, `03_startup_preflight_check.md`.

---

## Improvement Purpose

Mục tiêu của cải tiến này là chuẩn hóa checklist gói triển khai trạm AOI — repo git chỉ có `sky.py` nhưng runtime cần UI/, basler_my, config, point/, sample/, source/, ioCardNew, v.v. Giảm lỗi triển khai trạm mới, dễ bàn giao và audit môi trường.

## Before Improvement

Trước cải tiến, không có manifest formal: engineer copy `sky.py` nhưng thiếu `point/*.json`, `sample/*.jpg`, `source/8P/`, module `ioCardNew`, hoặc chạy sai CWD. Trạm mới crash first-run (`NameError`, `imwrite` fail, missing JSON) — mất thời gian debug từng thiếu sót, khó audit đủ bundle trước go-live.

## After Improvement

Sau cải tiến, checklist DEP-B01→B14 map từng hạng mục → anchor verify trong `sky.py` → smoke test. Quy trình 8 bước setup trạm: OS → driver → bundle → config/recipe → assets → network → preflight → smoke Pass+Fail. Mỗi trạm có manifest auditable trước production.

## Improvement Value

| Area                        | Value |
| --------------------------- | ----- |
| Production stability        | Giảm crash first-run do thiếu file/folder |
| Operator experience         | Trạm setup đúng ngay — ít downtime chờ engineer fix thiếu asset |
| MES/SFIS integrity          | SFIS/Cambrian endpoint verify trước Start |
| Maintainability             | Manifest theo model; dễ onboard trạm mới |
| Debugging / troubleshooting | Biết chính xác thiếu gì thay vì crash opaque |

## Before / After Summary

| Aspect           | Before | After |
| ---------------- | ------ | ----- |
| Runtime behavior | Start với bundle thiếu → crash/stall | Checklist verify trước; preflight chặn nếu thiếu |
| Error handling   | ImportError/imwrite fail không hướng dẫn | Manifest + smoke chỉ rõ hạng mục thiếu |
| Operator impact  | Chờ engineer debug setup | Trạm ready sau checklist chuẩn |
| Production risk  | Deploy thiếu asset → line down | Giảm rủi ro triển khai; dễ bàn giao ca |

---

## Per-Fix Detail

### DEP-B01

#### Code Location

| Item | Value |
|------|-------|
| Bundle | `sky.py` + `UI/` |
| Anchor `sky.py` | G10 `from UI import Ui_MainWindow` |
| Verify command | `python -c "from UI import Ui_MainWindow"` |
| Patch doc | Bundle (không patch code) |

#### Current Problem

Repo git chỉ có `sky.py` — trạm mới copy thiếu `UI/` → ImportError ngay launch.

#### Before Improvement

Không manifest formal; engineer copy ad hoc, thiếu module UI.

#### Required Change

Verify + ship bundle: `sky.py`, thư mục `UI/` đầy đủ trên PYTHONPATH/CWD trạm.

#### After Improvement

Launch không ImportError; checklist tick DEP-B01 trước go-live.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | App khởi động được — nền tảng mọi test khác |
| Operator experience | UI hiện, không crash silent |
| MES/SFIS integrity | N/A |
| Maintainability | Manifest item #1 mọi trạm |
| Debugging / troubleshooting | Fail sớm, rõ thiếu `UI/` |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-B01 | VM sạch, chỉ cài theo checklist | Launch app | Không ImportError; UI hiện |
| T-B01b | Thiếu `UI/` | Launch | ImportError ngay — fail sớm |

#### Rollback

Khôi phục bundle cũ từ backup trạm. Checklist là tài liệu — không code rollback.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 2 | Audit env trạm hiện tại song song P0 code fixes |

---

### DEP-B02

#### Code Location

| Item | Value |
|------|-------|
| Bundle | `basler_my/`, `sfisapi` |
| Anchor `sky.py` | G11, G28 |
| Verify | File trên PYTHONPATH |
| Patch doc | Bundle |

#### Current Problem

Module camera Basler và SFIS API ngoài repo — thiếu → ImportError hoặc SFIS init fail.

#### Before Improvement

Copy `sky.py` không kèm `basler_my`, `sfisapi`.

#### Required Change

Ship `basler_my` (camera wrapper) + `sfisapi` cùng bundle; verify import trước launch.

#### After Improvement

`from basler_my import camera` và SFIS init OK khi bundle đủ.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Camera + MES stack sẵn sàng |
| Operator experience | Launch OK khi bundle đủ |
| MES/SFIS integrity | SFIS client importable |
| Maintainability | Item #2 manifest |
| Debugging / troubleshooting | ImportError chỉ rõ module thiếu |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-B01 | Cùng T-B01 | Launch | `basler_my`, `sfisapi` import OK |

#### Rollback

Restore bundle modules từ backup trạm.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 2 | Cùng DEP-B01 audit |

---

### DEP-B03

#### Code Location

| Item | Value |
|------|-------|
| Bundle | `config.json` |
| Anchor `sky.py` | G117+ SFIS keys, `choose_model` |
| Verify | `os.path.isfile("config.json")` |

#### Current Problem

Thiếu hoặc sai `config.json` → crash `__init__` hoặc SFIS keys missing.

#### Before Improvement

Không checklist key bắt buộc (`sfisinfo`, `choose_model`, `choose_route`).

#### Required Change

Tạo/verify `config.json` hợp lệ tại CWD trạm; keys theo §Config keys.

#### After Improvement

Launch load config OK; paths recipe và SFIS resolve đúng.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Boot không crash config |
| Operator experience | Model path và SFIS settings đúng |
| MES/SFIS integrity | `sfisinfo.is_open`, endpoint URLs present |
| Maintainability | Template config per trạm |
| Debugging / troubleshooting | Preflight P-01 bắt thiếu file |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-B03 | Xóa `config.json` | Launch / Start | Fail sớm (preflight hoặc crash có hướng dẫn) |

#### Rollback

Khôi phục `config.json` backup trạm.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 2 | Bước 4 quy trình setup 8 bước |

---

### DEP-B04

#### Code Location

| Item | Value |
|------|-------|
| Bundle | Model JSON + ROI recipe files |
| Anchor `sky.py` | G181, `path_json` trong model JSON |
| Verify | Path `choose_model` readable; ROI files exist |

#### Current Problem

Recipe path trong config trỏ file không tồn tại hoặc thiếu `path_json`/`count_json`.

#### Before Improvement

Deploy `sky.py` + config nhưng quên pack model JSON và barcode/count JSON.

#### Required Change

Copy model JSON đúng model trạm + mọi file ROI referenced trong `path_json`.

#### After Improvement

Load model OK; preflight P-08 pass cho ROI paths.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Vision có ROI config |
| Operator experience | Đúng model hiện trên UI |
| MES/SFIS integrity | Count/barcode JSON cho upload |
| Maintainability | Recipe pack per product |
| Debugging / troubleshooting | Preflight liệt kê file ROI thiếu |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-B04 | Model đã chọn | Preflight / Start | Pass P-08; thiếu ROI → blocked |

#### Rollback

Restore recipe pack từ backup hoặc trạm reference.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 2 | Sau B03, trước smoke Pass+Fail |

---

### DEP-B05

#### Code Location

| Item | Value |
|------|-------|
| Hardware | Basler camera |
| Anchor `sky.py` | G166–176 `search_get_device`, G253–256 `camera_id` |
| Verify | Pylon Viewer thấy camera; `allcameras` non-empty |

#### Current Problem

`camera_id` trong model JSON không khớp camera thật → grab fail hoặc wrong camera.

#### Before Improvement

Không verify camera list vs `camera_id` trước production.

#### Required Change

Cài driver Basler; verify `camera_id` ∈ `allcameras` (preflight P-05).

#### After Improvement

Camera open OK tại `startprogram`; tên model khớp hardware.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Grab image thành công |
| Operator experience | Camera list đúng trên UI |
| MES/SFIS integrity | N/A |
| Maintainability | Document `camera_id` per trạm |
| Debugging / troubleshooting | Preflight báo camera_id mismatch |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-B05 | Camera Basler kết nối | Launch | `allcameras` non-empty; `camera_id` khớp |

#### Rollback

Revert driver/cable; restore known-good `camera_id` in model JSON.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 2 | Bước 2–3 setup (driver trước bundle) |

---

### DEP-B06

#### Code Location

| Item | Value |
|------|-------|
| Bundle | `point/*.json` |
| Anchor `sky.py` | G2016 HH4K; G2525 SKY; G4097 Button_check; G4419+ WP; G4792+ Nanook |
| Verify | Theo bảng §Point files |

#### Current Problem

Multi-step models cần `point/*.json` — thiếu → exception mid-cycle hoặc stall.

#### Before Improvement

Copy `sky.py` không kèm point files theo model.

#### Required Change

Copy đủ point JSON cho model đã chọn (tick một dòng checklist theo model).

#### After Improvement

Preflight P-06 pass; vision có ROI point data.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Không crash thiếu point mid-step |
| Operator experience | Test chạy đủ bước |
| MES/SFIS integrity | N/A |
| Maintainability | Bảng §Point map model → files |
| Debugging / troubleshooting | Preflight tên file thiếu |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-B06 | HH4K, đổi tên `point/step1.json` | Start | Preflight P-06 blocked |

#### Rollback

Restore `point/` từ recipe pack backup.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 2 | Bước 5 setup; theo model tick |

---

### DEP-B07

#### Code Location

| Item | Value |
|------|-------|
| Bundle | `sample/*.jpg` |
| Anchor `sky.py` | G1905 MR6500; G2024+ HH4K; G1270 Button_check; G1331+ C9105; G1560+ Nanook |
| Verify | Theo bảng §Sample files |

#### Current Problem

Golden/stub sample thiếu → `imread` None, crash crop (MR6500) hoặc compare fail.

#### Before Improvement

MR6500: mỗi liaohao mới cần `sample/{liaohao}.jpg` — không preflight hết list.

#### Required Change

Copy sample theo model; MR6500: golden theo liaohao production (vận hành bổ sung khi có code mới).

#### After Improvement

Vision có golden khi cần; preflight P-07 warning cho stub thiếu.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Giảm None crash trên MR6500/HH4K |
| Operator experience | Fail rõ "Missing Sample" thay vì crash |
| MES/SFIS integrity | N/A |
| Maintainability | Sample manifest per model |
| Debugging / troubleshooting | PIPE-M02 pattern cho missing golden |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-B07 | Thiếu `sample/step1.jpg` HH4K | Start | Warning hoặc fail có tên file |

#### Rollback

Restore `sample/` từ backup.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 2 | Cùng B06; MR6500 golden ongoing ops |

---

### DEP-B08

#### Code Location

| Item | Value |
|------|-------|
| Bundle / FS | `source/`, `source/8P/` writable |
| Anchor `sky.py` | G1938, G3354 `imwrite` |
| Patch doc | DEP-003 (`02_external_imports_and_assets.md`) hoặc mkdir tay |

#### Current Problem

`cv2.imwrite` tới `source/` crash nếu thư mục không tồn tại hoặc không ghi được.

#### Before Improvement

Trạm mới không có `source/` — SKY/Cisco/Nanook imwrite fail.

#### Required Change

Tạo `source/`, `source/8P/` writable; khuyến nghị DEP-003 auto-mkdir trong `__init__`.

#### After Improvement

imwrite OK; Cisco cần `source/8P/` (DEP-P04).

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Lưu ảnh debug/OCR không crash |
| Operator experience | Ảnh lưu đúng chỗ |
| MES/SFIS integrity | N/A |
| Maintainability | DEP-003 giảm thao tác tay |
| Debugging / troubleshooting | Preflight P-09 writable check |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-B08 | Xóa `source/`, DEP-003 deployed | SKY/Cisco cycle | imwrite OK; folder tự tạo |

#### Rollback

Xóa DEP-003 patch; mkdir thủ công trên trạm.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 1–2 | DEP-003 code Week 1; bundle verify Week 2 |

---

### DEP-B09

#### Code Location

| Item | Value |
|------|-------|
| FS | `log/`, `choose_route` (→ `pciture_save`) |
| Anchor `sky.py` | G569 `create_log`; G302 mkdir `choose_route` |
| Verify | Writable; OS permission |

#### Current Problem

Log và ảnh production không ghi được → mất audit trail hoặc crash.

#### Before Improvement

`choose_route` trỏ ổ không ghi được; `log/` thiếu quyền.

#### Required Change

Verify writable `log/` và path `choose_route`; tạo nếu thiếu.

#### After Improvement

Ảnh → `pciture_save/{date}/`; log → `log/{date}/` sau smoke.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Logging và image archive hoạt động |
| Operator experience | Ảnh Pass/Fail lưu được |
| MES/SFIS integrity | Log SFIS/upload trace |
| Maintainability | Path chuẩn mọi trạm |
| Debugging / troubleshooting | Preflight P-12 choose_route writable |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-VM | VM acceptance | 1 Pass + 1 Fail | Ảnh và log đúng thư mục |

#### Rollback

Fix OS permissions hoặc restore path config.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 2 | Bước 8 smoke verify paths |

---

### DEP-B10

#### Code Location

| Item | Value |
|------|-------|
| Bundle | `ioCardNew` + `profile\pci1756.xml` |
| Anchor `sky.py` | G29 import, G630 `IoCard(...)` |
| Patch doc | DEP-001 uncomment import |

#### Current Problem

Sensor trạm: import comment nhưng `IoCard` vẫn gọi → NameError; thiếu XML → init fail.

#### Before Improvement

`#from ioCardNew import IoCard` + thiếu profile/driver.

#### Required Change

DEP-001 uncomment; ship `ioCardNew`, `profile\pci1756.xml`, driver Advantech PCI-1756.

#### After Improvement

Sensor Start → IoCard init OK (MR6500 + sensor only per B14).

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Sensor line Start được |
| Operator experience | IO trigger hoạt động |
| MES/SFIS integrity | N/A |
| Maintainability | Sensor bundle checklist riêng |
| Debugging / troubleshooting | Preflight P-16 IoCard + XML |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-B10 | Trạm sensor MR6500, bundle đủ | Start sensor | IoCard init OK |

#### Rollback

Comment import; set `is_sensor=false` nếu không có hardware IO.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 1 (DEP-001) + Week 2 (bundle verify) | P0 NameError fix trước |

---

### DEP-B11

#### Code Location

| Item | Value |
|------|-------|
| Network / config | SFIS SOAP endpoint |
| Anchor `sky.py` | G123–158 SFIS init |
| Verify | Ping/reachability nếu `sfisinfo.is_open` |

#### Current Problem

SFIS bật nhưng network unreachable → timeout/exception mid-upload.

#### Before Improvement

Không verify endpoint trước go-live.

#### Required Change

Verify SFIS reachable hoặc set `is_open: false` cho trạm offline test.

#### After Improvement

Launch SFIS login OK hoặc graceful offline mode.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Giảm surprise SFIS timeout |
| Operator experience | Biết SFIS on/off từ config |
| MES/SFIS integrity | Upload path sẵn sàng khi on |
| Maintainability | Document endpoint per fab |
| Debugging / troubleshooting | SFIS-001 try/except khi flaky |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-B11 | `is_open: true` | Launch | Login OK hoặc logged error rõ |

#### Rollback

Set `is_open: false` tạm; fix network.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 2 | Bước 6 setup (network) |

---

### DEP-B12

#### Code Location

| Item | Value |
|------|-------|
| Network / AI | Cambrian `pega_inference` |
| Anchor `sky.py` | Cambrian block `__init__`, model `cambrian.is_cambrian` |
| Verify | `get_version()` nếu bật |

#### Current Problem

Model bật Cambrian nhưng service unreachable → AI step fail/stall.

#### Before Improvement

Không pre-check Cambrian trước Start.

#### Required Change

Verify Cambrian reachable hoặc `is_cambrian: false` trong model JSON.

#### After Improvement

Load model OK; AI steps có service hoặc disabled rõ.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Giảm Cambrian surprise fail |
| Operator experience | Model load không hang |
| MES/SFIS integrity | N/A |
| Maintainability | Per-model Cambrian flag |
| Debugging / troubleshooting | AI-001/002 guard policies |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-B12 | SKY `is_cambrian: true` | Launch + 1 step | Cambrian OK hoặc Fail có cấu trúc |

#### Rollback

Disable `is_cambrian` in recipe tạm.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 2 | Theo model tick checklist |

---

### DEP-B13

#### Code Location

| Item | Value |
|------|-------|
| Bundle | `ipex_check_yolo` module |
| Anchor `sky.py` | G37, G727/G738 `ipex_check` branch |
| Patch doc | DEP-002 uncomment import |

#### Current Problem

Trạm `ipex_check`: import comment → NameError tại vision call.

#### Before Improvement

`# from ipex_check_yolo import camera_check_ipex` nhưng branch vẫn gọi.

#### Required Change

DEP-002 uncomment + ship `ipex_check_yolo` module trên trạm ipex.

#### After Improvement

ipex cycle Pass/Fail bình thường.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | ipex station runnable |
| Operator experience | Không NameError mid-cycle |
| MES/SFIS integrity | N/A |
| Maintainability | Conditional bundle item |
| Debugging / troubleshooting | Preflight P-18 module check |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-B13 | Model `ipex_check`, bundle đủ | 1 cycle | Pass/Fail OK |

#### Rollback

Comment import; không deploy model `ipex_check`.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 1 (DEP-002) | P0 nếu trạm ipex active |

---

### DEP-B14

#### Code Location

| Item | Value |
|------|-------|
| Policy | Sensor chỉ MR6500 |
| Anchor `sky.py` | `is_sensor` trong model JSON; SENSOR-002 guard |
| Related doc | `01_sensor_mode_guard.md` |

#### Current Problem

Recipe `is_sensor=true` với model ≠ MR6500 → wrong pipeline nếu guard chưa ship.

#### Before Improvement

Default `is_sensor=True` nguy hiểm cho non-MR6500 recipes.

#### Required Change

Audit mọi model JSON; deploy SENSOR-002; verify SKY+sensor blocked.

#### After Improvement

Chỉ MR6500 + sensor được phép production; combo sai blocked tại Start.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Wrong pipeline prevented |
| Operator experience | Message rõ khi config sai |
| MES/SFIS integrity | Đúng vision trước upload |
| Maintainability | Policy doc + guard code |
| Debugging / troubleshooting | Production audit export JSON |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-B10 | Trạm sensor, SKY+sensor recipe | Start | Blocked (SENSOR-002) |
| T-B10b | MR6500+sensor | Start | Sensor loop OK |

#### Rollback

**Không khuyến nghị** rollback SENSOR-002 — wrong pipeline risk.

#### Suggested Implementation Window

| Window | Reason |
|--------|--------|
| Week 1 (guard code) + Week 2 (recipe audit) | Audit `is_sensor=true` trước deploy guard |

---

## Bảng tổng — manifest vs verify

| ID | Hạng mục | Verify (trạm) | Anchor `sky.py` | Patch doc | Smoke |
|----|----------|---------------|-----------------|-----------|-------|
| **DEP-B01** | App lõi `sky.py` + `UI/` | `python -c "from UI import Ui_MainWindow"` | G10 import | Bundle | Launch không ImportError |
| **DEP-B02** | `basler_my`, `sfisapi` | File trên PYTHONPATH | G11, G28 | Bundle | Launch OK |
| **DEP-B03** | `config.json` | `os.path.isfile("config.json")` | G117+ SFIS keys | Tạo file | Launch không crash |
| **DEP-B04** | Model JSON + ROI recipe | Path `choose_model` readable | G181, `path_json` | Recipe pack | Preflight P-08 |
| **DEP-B05** | Camera Basler | Pylon Viewer thấy camera | G166–176 `search_get_device` | Driver | `allcameras` non-empty |
| **DEP-B06** | `point/*.json` | Theo bảng §Point | G2016 HH4K; G2525 SKY | Copy files | Preflight P-06 |
| **DEP-B07** | `sample/*.jpg` | Theo bảng §Sample | G1905 MR6500; G2024 HH4K | Copy files | Vision không None crash |
| **DEP-B08** | `source/`, `source/8P/` | Writable dirs | G1938, G3354 `imwrite` | DEP-003 hoặc mkdir tay | `imwrite` OK |
| **DEP-B09** | `log/`, `choose_route` | Writable | G569 `create_log`; G302 | OS permission | Log + ảnh lưu |
| **DEP-B10** | Sensor: `ioCardNew` + profile | Import + XML exists | G29, G630 | DEP-001 | Sensor Start |
| **DEP-B11** | SFIS SOAP | Ping nếu `is_open` | G123–158 | Network | Login OK launch |
| **DEP-B12** | Cambrian | `get_version()` nếu bật | Cambrian block `__init__` | Network | Load model OK |
| **DEP-B13** | `ipex_check` station | `ipex_check_yolo` module | G37, G738 | DEP-002 | ipex cycle |
| **DEP-B14** | Sensor policy | Chỉ MR6500 + sensor | `is_sensor` JSON | SENSOR-002 | SKY+sensor blocked |

**Ship order setup trạm:** B01→B05 → B03→B04 → B06→B08 → B10 (nếu sensor) → B11→B12 → code patches `02` → preflight `03` → smoke Pass+Fail.

---

## Quy trình thiết lập (8 bước)

```text
1. OS + Python + pip packages (§2)
2. Driver Basler (+ Advantech nếu sensor)
3. DEP-B01/B02: sky.py, UI/, basler_my, sfisapi
4. DEP-B03/B04: config.json + recipe model
5. DEP-B06/B07/B08: point/, sample/, source/
6. DEP-B11/B12: SFIS + Cambrian network
7. DEP-P02 preflight + DEP-001/002 patches
8. Smoke: 1 Pass + 1 Fail; ảnh dưới choose_route; log dưới log/
```

**Khởi chạy:** CWD = thư mục chứa `config.json` và `sky.py` — shortcut phải `cd` đúng.

---

## §2 Pip packages (DEP-B01 deps)

| Package | Dùng cho | Model cần |
|---------|----------|-----------|
| `PyQt5` | GUI | Tất cả |
| `opencv-python`, `numpy`, `Pillow` | Vision | Tất cả |
| `pypylon` | Basler | Tất cả |
| `pylibdmtx` | DataMatrix | MR6500, WP |
| `pyzbar` | Barcode | SKY, Cisco, Nanook, C9105 |
| `paddleocr`, `paddlepaddle` | OCR | SKY, Cisco, Nanook |
| `suds` | SOAP | SFIS |
| `pega_inference` | Cambrian | Model bật AI |

Ghim version trong `requirements.txt` theo image trạm production.

---

## §Point files (DEP-B06) — Ctrl+F verify trong `sky.py`

| Model | Files bắt buộc | Anchor G |
|-------|----------------|----------|
| HH4K | `point/step1.json` … `step4.json` | G2016–G2019 |
| SKY | `point/SKY_barcode.json`, `SKY_model1–3.json`, `SKY_model5.json` | G2525+ |
| SKY_4G | `point/SKY_4G_*` (bộ song song) | G2527+ |
| Button_check | `point/Button_check_model.json` | G4097 |
| WP_check, C9105AXW_E | `point/WP_check_step3–6.json` | G4419+ |
| Nanook | `point/Nanook_model1–4.json` | G4792+ |
| MR6500, Cisco, ipex | ROI từ recipe `path_json` only | Model JSON |

---

## §Sample files (DEP-B07)

| Model | Files | Anchor G | Production |
|-------|-------|----------|------------|
| MR6500 | `sample/{liaohao}.jpg` | G1905 | ✅ Mỗi 90-code SFIS trên line |
| HH4K | `sample/step1–4.jpg` | G2024+ | ✅ Golden compare |
| Button_check | `sample/button_check.jpg` | G1270 | Stub (camera thật prod) |
| C9105AXW_E | `sample/C9105AXW_E/1–6.jpg` | G1331+ | Verify stub |
| Nanook | `sample/NANOOK/1–6.jpg` | G1560+ | Verify stub |

MR6500: **không preflight hết** `sample/*` — quy trình vận hành bổ sung golden khi có liaohao mới.

---

## §Config keys (`config.json` — DEP-B03)

| Key | Mục đích |
|-----|----------|
| `sfisinfo.is_open` | → `sfis_choose` |
| `sfisinfo.service_web_url`, `device`, `opid` | SFIS |
| `choose_model` | Đường dẫn model JSON |
| `choose_route` | Gốc lưu ảnh → `pciture_save` |

Model JSON: `model`, `camera_id`, `cambrian`, `path_json`, `count_json`, `is_sensor`, `sensor_no`, `sensor_start`.

---

## §Sensor trạm (DEP-B10 + DEP-B14)

| Hạng mục | Verify |
|----------|--------|
| `from ioCardNew import IoCard` (không comment) | DEP-001 |
| `profile\pci1756.xml` tại CWD | F `profile\\pci1756.xml` G630 |
| Driver Advantech PCI-1756 | Device Manager |
| `is_sensor=true` **và** `model=MR6500` only | SENSOR-002 |
| Sensor guard deployed | `01_sensor_mode_guard.md` |

---

## Checklist sao chép (mọi trạm)

### Bắt buộc
- [ ] DEP-B01: `sky.py` + `UI/` + `basler_my` + `sfisapi`
- [ ] DEP-B02: pip packages §2
- [ ] DEP-B03: `config.json` hợp lệ
- [ ] DEP-B04: model JSON + barcode/model point + count JSON
- [ ] DEP-B05: camera_id khớp `allcameras`
- [ ] DEP-B08: `source/`, `source/8P/` writable
- [ ] DEP-B09: `log/`, `choose_route` writable
- [ ] DEP-P02: preflight pass hoặc warnings đã ack
- [ ] Smoke Pass + Fail một DUT

### Nếu sensor (MR6500 only)
- [ ] DEP-B10: IoCard import + profile + driver
- [ ] DEP-B14: recipe verified / guard deployed

### Theo model (tick một dòng)
- [ ] DEP-B06 point files cho model đã chọn
- [ ] DEP-B07 sample files (MR6500: golden theo liaohao production)
- [ ] DEP-B12 Cambrian reachable hoặc `is_cambrian: false`
- [ ] DEP-B11 SFIS reachable hoặc `is_open: false`

---

## VM sạch — chấp nhận (`11_refactor_plan` §3.14)

1. Cài **chỉ** theo checklist — không copy ad hoc từ trạm cũ.
2. Launch — không ImportError (DEP-B01).
3. Camera list + tên model trên UI (DEP-B05).
4. Preflight xanh hoặc warnings logged (DEP-P02).
5. Shortest pipeline Pass + Fail cho model đã chọn.
6. Ảnh → `pciture_save/{date}/`; log → `log/{date}/`.
7. Stop — không treo.

---

## Verification

| Test ID | Fix ID | Setup | Action | Expected result |
|---------|--------|-------|--------|-----------------|
| T-B01 | DEP-B01/B02 | VM sạch, chỉ cài theo checklist | Launch app | Không ImportError; UI hiện |
| T-B05 | DEP-B05 | Camera Basler kết nối | Launch | `allcameras` non-empty; camera_id khớp |
| T-B06 | DEP-B06/B07 | Model đã chọn, point/sample copy đủ | Preflight P-06/P-07 | Pass; thiếu file → blocked/warning |
| T-B10 | DEP-B10/B14 | Trạm sensor MR6500 | Start sensor | IoCard init OK; non-MR6500 blocked |
| T-VM | Toàn bundle | VM sạch acceptance §VM | 7 bước checklist | Pass + Fail smoke; ảnh/log đúng thư mục |

## Rollback

Checklist là tài liệu vận hành — không có code rollback. Nếu bundle mới gây lỗi: khôi phục bundle cũ từ backup trạm (folder copy đầy đủ trước thay đổi), verify lại bằng T-VM. Patch code liên quan (DEP-001/002/003) rollback theo `02_external_imports_and_assets.md`.

## Implementation Window

| Hạng mục | Suggested window | Reason |
|----------|------------------|--------|
| Manifest DEP-B01–B14 (doc + verify trạm hiện tại) | Week 2 | Audit env song song với P0 code fixes |
| VM sạch acceptance | Week 2–3 | Cần VM + thời gian setup |
| `requirements.txt` ghim version | Week 2 | Theo image trạm production |

## Smoke (5 phút)

- [ ] VM sạch: checklist §9 step 1–7
- [ ] Thiếu `UI/` → fail sớm DEP-B01
- [ ] Thiếu `point/step1.json` + HH4K → DEP-P02 block

## Ref

`02_external_imports_and_assets.md` · `03_startup_preflight_check.md` · `07_camera_io_sfis.md` §11 · `01_priority_roadmap.md` P0/P3
