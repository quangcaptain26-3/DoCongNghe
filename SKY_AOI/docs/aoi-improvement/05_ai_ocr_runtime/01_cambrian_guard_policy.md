# Chính Sách Guard Cambrian — Compact Playbook

**File:** `sky.py` · **Workstream:** `05_ai_ocr_runtime`  
**Nguồn:** `07_camera_io_sfis.md` §5, `10_risks_and_bugs.md`, pipeline `14`–`19`  
**Luật:** Pipeline bắt buộc Cambrian + `is_cambrian=false` → **chặn Start**; `get_inference_result` không gọi `self.client` khi `cambrian_is_open=False`.

> Repo: `cambrian_is_open=False` G247/G473; `get_inference_result` G587; caller mẫu Button_check G4380. Analysis drift ~50 dòng. **Ctrl+F anchor.**

---

## Improvement Purpose

Mục tiêu của cải tiến này là tránh crash khi Cambrian disabled (`is_cambrian:false`) — pipeline bắt buộc AI vẫn gọi `self.client` dù không init. Chặn Start sớm hoặc guard `get_inference_result`; policy block/bypass rõ cho debug station.

## Before Improvement

Trước cải tiến, `is_cambrian:false` → app start OK nhưng không `self.client`; SKY/Cisco/WP/Button_check vẫn gọi `get_inference_result` → AttributeError mid-cycle. Operator thấy crash không rõ; không phân biệt config sai vs server down. Nanook một phần bypass STEP 6 — thiếu MES/count khi off.

## After Improvement

Sau cải tiến, `validate_cambrian_policy()` chặn Start khi model bắt buộc Cambrian + off; `get_inference_result` guard `cambrian_is_open` — không gọi client khi off; optional UI status ON/OFF. Debug bypass có cờ config. Không crash; operator thấy message config cần sửa.

## Improvement Value

| Area                        | Value |
| --------------------------- | ----- |
| Production stability        | Giảm crash mid-cycle trên trạm config sai Cambrian |
| Operator experience         | Blocked Start với message rõ thay vì AttributeError |
| MES/SFIS integrity          | Tránh pass/fail ambiguous khi AI path crash giữa chừng |
| Maintainability             | Policy tập trung `CAMBRIAN_REQUIRED_MODELS` + validate |
| Debugging / troubleshooting | Phân biệt config off vs server down; status label |

## Before / After Summary

| Aspect           | Before | After |
| ---------------- | ------ | ----- |
| Runtime behavior | Cambrian off → crash khi inference | Block Start hoặc guard return Fail |
| Error handling   | AttributeError opaque | validate_cambrian_policy + get_inference guard |
| Operator impact  | Crash giữa STEP | Message "Cambrian required" trước test |
| Production risk  | False state / crash trên clone debug | Config sai bị chặn sớm |

---

## Bảng tổng

| ID | Vấn đề | Đi tới | Anchor (đúng chỗ khi thấy…) | Thao tác | Test |
|----|--------|--------|-----------------------------|----------|------|
| **AI-G01** | Thiếu validate Cambrian | G617 / F `def startprogram` | Trước `def startprogram` · **Sai:** trong `show_image_SKY` | **Chèn** `validate_cambrian_policy` + `CAMBRIAN_REQUIRED_MODELS` | SKY+off → `(False,msg)` |
| **AI-G02** | Start với Cambrian off → crash | G617 / F `self.ekkoshan=camera` | Đầu `try:` sau sensor guard · **Sai:** sau `while True` | **Chèn** guard + `return` | C-01 SKY blocked |
| **AI-G03** | `get_inference_result` không guard | G587 / F `def get_inference_result` | Đầu hàm, trước `self.client.predict_images` · **Sai:** sửa từng pipeline | **Chèn** check `cambrian_is_open` | Không AttributeError nếu lọt |
| **AI-G04** | UI không hiện trạng thái Cambrian | G284 / F `self.lineEdit_2.setText` | Sau load model trong `__init__`/`choose_model` · **Sai:** mỗi vision | **+1 dòng** status label (optional) | Operator thấy ON/OFF |

**Ship:** AI-G01 → AI-G02 → AI-G03 → AI-G04 (optional)

**Pipeline bắt buộc Cambrian:** SKY, SKY_4G, Button_check, WP_check, C9105AXW_E, Nanook, Cisco ×12.

**OK khi off:** MR6500, HH4K, ipex_check.

---

## Context — hành vi hiện tại

| `is_cambrian` | Init (G247/G473) | Runtime inference |
|---------------|------------------|-------------------|
| `true` + server down | MessageBox + `sys.exit()` G243–245 | — |
| `false` | App start OK, **không** `self.client` | `get_inference_result` G590 → **AttributeError** |

| Pipeline | Guard `cambrian_is_open`? | `is_cambrian=false` |
|----------|---------------------------|---------------------|
| SKY, Cisco, WP, Button_check | **Không** | Crash G4380 |
| Nanook | **Một phần** G4780, G5022 | STEP 6 bypass — thiếu MES/count |

---

## Diff patches

### AI-G01 · `validate_cambrian_policy`, trước `startprogram` G617

**Đúng chỗ:** class chính, trước `def startprogram` · **Sai:** trong `get_inference_result`

```python
# TRƯỚC
    def get_inference_result(self, img_list):
        ...

    def startprogram(self):

# SAU
    CISCO_CAMBRIAN_MODELS = (
        "C1000-8FP-E-2G-L", "C1000-8P-2G-L", "C1000-8T-2G-L",
        "C1200-8FP-2G", "C1200-8P-E-2G", "C1200-8T-E-2G",
        "C1300-8P-E-2G", "C1300-8T-E-2G", "C1000-8FP-2G-L",
        "C1000-8P-E-2G-L", "C1300-8FP-2G", "C1000-8T-E-2G-L",
    )
    CAMBRIAN_REQUIRED_MODELS = {
        "SKY", "SKY_4G", "Button_check", "WP_check", "C9105AXW_E", "Nanook",
        *CISCO_CAMBRIAN_MODELS,
    }

    def validate_cambrian_policy(self):
        """Returns (ok: bool, message: str)."""
        if self.select_model not in self.CAMBRIAN_REQUIRED_MODELS:
            return True, ""
        if getattr(self, "cambrian_is_open", False):
            return True, ""
        if getattr(self, "debug_offline_bypass", False):  # config.json optional
            return True, "DEBUG_OFFLINE"
        return False, (
            f"Cambrian is required for {self.select_model} but is_cambrian=false.\n\n"
            "Enable Cambrian in model JSON or use a debug station profile.\n"
            "Do not test parts until configuration is fixed."
        )

    def startprogram(self):
```

Rollback: xóa constants + method.

---

### AI-G02 · guard `startprogram` G617

**Đúng chỗ:** đầu `try:`, **trước** `self.ekkoshan=camera()` · **Sau** SENSOR-002 nếu có · **Sai:** trong vision

```python
# TRƯỚC
    def startprogram(self):
        try:
            self.ekkoshan=camera()

# SAU
    def startprogram(self):
        try:
            ok, msg = self.validate_cambrian_policy()
            if not ok:
                logging.error(
                    f"CAMBRIAN_GUARD_BLOCK model={self.select_model} "
                    f"cambrian_is_open={getattr(self, 'cambrian_is_open', None)}"
                )
                self.myuihand.textbox.emit(msg.replace("\n", " | "))
                QMessageBox.critical(self, "Configuration Error", msg)
                return

            self.ekkoshan=camera()
```

Tích hợp `run_preflight()` (`04/03`): gọi `validate_cambrian_policy` trong preflight thay vì duplicate.

Rollback: xóa block guard.

---

### AI-G03 · guard `get_inference_result` G587

**Đúng chỗ:** đầu `get_inference_result`, trước `self.client.predict_images` · **Sai:** wrap từng caller SKY/Cisco

```python
# TRƯỚC
    def get_inference_result(self, img_list):
        image_result_list = []
        response_predict = self.client.predict_images(img_list)

# SAU
    def get_inference_result(self, img_list):
        if not getattr(self, "cambrian_is_open", False):
            if getattr(self, "debug_offline_bypass", False):
                logging.warning("get_inference_result: debug offline stub")
                return ["NG"] * len(img_list)  # hoặc stub khớp label — chỉ debug
            logging.error("get_inference_result called with Cambrian disabled")
            raise RuntimeError("Cambrian disabled — inference blocked")
        image_result_list = []
        response_predict = self.client.predict_images(img_list)
```

Rollback: xóa block `if not cambrian_is_open`.

---

### AI-G04 · status UI (optional) G284

**Đúng chỗ:** sau `self.lineEdit_2.setText(self.select_model)` khi load model · **Sai:** trong `cambrian_space`

```python
# SAU — ví dụ append vào lineEdit_2 hoặc textbox
        status = "CAMBRIAN:ON" if self.cambrian_is_open else "CAMBRIAN:OFF"
        if getattr(self, "debug_offline_bypass", False):
            status = "CAMBRIAN:DEBUG"
        self.get_rightnow(status)
```

---

## Evidence caller (không patch từng chỗ — AI-G03 bảo vệ)

**Button_check SFIS on** G4380 — crash khi off:

```python
                            inference_result = self.get_inference_result(step1_check)
                            ...
                            yolo_step1=self.cambrian_space(inference_result,image_numpy,step1_check_draw)
```

**Button_check SFIS off** G4401 — vẫn gọi client:

```python
                        inference_result1 = self.get_inference_result(step1_check)
```

**Nanook STEP 6 bypass** G5022 — thiếu MES khi off:

```python
                elif self.cambrian_is_open==False:
                    self.step6 = True   # ← không Pass UI, không data_upload
```

Sau AI-G02: Nanook+off **blocked tại Start** (trừ `debug_offline_bypass`).

---

## Verification

| Test ID | Fix ID | Setup | Action | Expected result |
|---------|--------|-------|--------|-----------------|
| T-AI-G01 | AI-G01 | Gọi tay `validate_cambrian_policy()` SKY + `is_cambrian:false` | Unit call | `(False, msg)`; HH4K/MR6500 trả `(True, "")` |
| T-AI-G02 | AI-G02 | SKY, `is_cambrian:false` | Click Start | Blocked QMessageBox; Start enabled; log `CAMBRIAN_GUARD_BLOCK` |
| T-AI-G03 | AI-G03 | Ép gọi `get_inference_result` khi off (bypass guard) | Runtime call | RuntimeError rõ — không AttributeError `self.client` |
| T-AI-G04 | AI-G04 | Load model bất kỳ | Xem UI | Status CAMBRIAN:ON/OFF/DEBUG hiển thị |

Chi tiết matrix C-01…C-10 bên dưới.

## Test matrix

| # | Model | `is_cambrian` | `debug_offline` | Kỳ vọng |
|---|-------|---------------|-----------------|---------|
| C-01 | SKY | false | false | **Blocked** Start |
| C-02 | SKY | true | — | Cambrian steps OK |
| C-03 | Nanook | false | false | **Blocked** |
| C-04 | HH4K | false | — | Start OK |
| C-05 | Button_check | false | false | **Blocked** |
| C-06 | Cisco * | false | false | **Blocked** |
| C-10 | Gọi `get_inference_result` khi off | — | false | RuntimeError, không AttributeError |

---

## Rollback

| Fix ID | Rollback | Behavior cũ quay lại | Rủi ro nếu rollback |
|--------|----------|----------------------|---------------------|
| AI-G01 | Xóa method + `CAMBRIAN_REQUIRED_MODELS` | Không validate | Rollback cùng G02 (caller) |
| AI-G02 | Xóa block guard `startprogram` | Cambrian off → crash mid-cycle | AttributeError quay lại trên trạm config sai |
| AI-G03 | Xóa block `if not cambrian_is_open` | Gọi `self.client` không guard | Crash nếu lọt qua guard Start |
| AI-G04 | Xóa status line | Không hiện trạng thái | Thấp |

Nếu guard chặn nhầm trạm debug hợp lệ: bật `debug_offline_bypass` trong config trên clone — không rollback guard production.

## Implementation Window

| Fix ID | Suggested window | Reason |
|--------|------------------|--------|
| AI-G01 | Week 1–2 | Method mới, không đổi flow |
| AI-G02 | Week 1–2 | P3 crash prevention; audit recipe `is_cambrian` trước deploy |
| AI-G03 | Week 2 | Defense-in-depth sau G02 |
| AI-G04 | Week 3–4 (optional) | UX |

## Smoke (5 phút)

- [ ] C-01 SKY+off blocked, Start enabled
- [ ] C-02 SKY+on một step Pass không regression
- [ ] C-04 HH4K+off Start OK

## Per-Fix Detail

### AI-G01 — `validate_cambrian_policy` method

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | Trước `def startprogram` G617 |
| Lines | ~G617 (chèn constants + method) |
| Legacy alias | — |

#### Current Problem

Không có method tập trung kiểm tra model bắt buộc Cambrian vs `is_cambrian:false`. Mỗi pipeline gọi inference độc lập; config sai chỉ phát hiện khi crash mid-cycle.

#### Before Improvement

`is_cambrian:false` → app start OK, không `self.client`; SKY/Cisco/WP/Button_check vẫn gọi `get_inference_result` → AttributeError. Không phân biệt config sai vs server down.

#### Required Change

Chèn `CISCO_CAMBRIAN_MODELS`, `CAMBRIAN_REQUIRED_MODELS`, và `validate_cambrian_policy()` trả `(ok, message)` — trước `def startprogram`. Hỗ trợ `debug_offline_bypass` optional.

#### After Improvement

Policy tập trung: model trong `CAMBRIAN_REQUIRED_MODELS` + `cambrian_is_open=False` → `(False, msg)` rõ. HH4K/MR6500/ipex_check trả `(True, "")`.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Chặn config sai trước runtime |
| Operator experience | Message cấu hình thay vì crash opaque |
| Maintainability | Single source `CAMBRIAN_REQUIRED_MODELS` |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-AI-G01 | Gọi tay `validate_cambrian_policy()` SKY + `is_cambrian:false` | Unit call | `(False, msg)` |
| T-AI-G01b | HH4K/MR6500 + off | Unit call | `(True, "")` |

#### Rollback

Xóa constants + `validate_cambrian_policy` method. **Rủi ro:** rollback cùng AI-G02 (caller).

#### Suggested Implementation Window

Week 1–2 — method mới, không đổi flow runtime.

---

### AI-G02 — Start guard `startprogram`

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | `def startprogram` G617 |
| Lines | Đầu `try:`, trước `self.ekkoshan=camera()` |
| Legacy alias | C-01…C-06 (test matrix) |

#### Current Problem

Start với Cambrian off trên model bắt buộc AI → crash giữa STEP khi gọi `self.client`.

#### Before Improvement

`startprogram` mở camera ngay; không validate Cambrian. Operator click Start → crash AttributeError mid-cycle (Button_check G4380).

#### Required Change

Đầu `try:` trong `startprogram`: gọi `validate_cambrian_policy()`; nếu `not ok` → log `CAMBRIAN_GUARD_BLOCK`, QMessageBox, `return`. Tích hợp `run_preflight()` nếu có.

#### After Improvement

SKY/Nanook/Cisco/Button_check + `is_cambrian:false` → **Blocked** Start với message rõ; Start button enabled lại. Nanook STEP 6 bypass không còn path im lặng.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | P3 crash prevention — chặn sớm |
| Operator experience | QMessageBox "Cambrian required" |
| MES/SFIS integrity | Tránh pass/fail ambiguous khi AI crash giữa chừng |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-AI-G02 | SKY, `is_cambrian:false` | Click Start | Blocked QMessageBox; log `CAMBRIAN_GUARD_BLOCK` |
| C-01 | SKY + off | Start | **Blocked** |
| C-03 | Nanook + off | Start | **Blocked** |
| C-04 | HH4K + off | Start | Start OK |

#### Rollback

Xóa block guard `startprogram`. **Rủi ro:** AttributeError quay lại trên trạm config sai.

#### Suggested Implementation Window

Week 1 (P0) — audit recipe `is_cambrian` trước deploy.

---

### AI-G03 — `get_inference_result` guard

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | `def get_inference_result` G587 |
| Lines | Đầu hàm, trước `self.client.predict_images` |
| Legacy alias | C-10 (test matrix) |

#### Current Problem

`get_inference_result` gọi `self.client` không kiểm tra `cambrian_is_open` — defense-in-depth thiếu nếu lọt qua guard Start.

#### Before Improvement

Mọi caller (SKY, Cisco, WP, Button_check G4380/G4401) gọi trực tiếp → AttributeError khi Cambrian off.

#### Required Change

Đầu `get_inference_result`: nếu `not cambrian_is_open` → `debug_offline_bypass` stub hoặc `raise RuntimeError("Cambrian disabled")`. Không patch từng caller.

#### After Improvement

Một guard bảo vệ mọi pipeline; RuntimeError rõ thay vì AttributeError `self.client`.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Defense-in-depth sau AI-G02 |
| Debugging | Phân biệt config off vs server down |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-AI-G03 | Ép gọi `get_inference_result` khi off | Runtime call | RuntimeError — không AttributeError |
| C-10 | Gọi khi off | Runtime | RuntimeError, không AttributeError |

#### Rollback

Xóa block `if not cambrian_is_open`. **Rủi ro:** crash nếu lọt qua guard Start.

#### Suggested Implementation Window

Week 2 — sau AI-G02 ổn định.

---

### AI-G04 — Cambrian status UI (optional)

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G284 / sau `self.lineEdit_2.setText` khi load model |
| Lines | ~G284 trong `__init__`/`choose_model` |
| Legacy alias | — |

#### Current Problem

Operator không thấy trạng thái Cambrian ON/OFF trên UI — khó debug config vs server.

#### Before Improvement

Chỉ load model name; không indicator Cambrian.

#### Required Change

Sau load model: append status `CAMBRIAN:ON` / `OFF` / `DEBUG` qua `get_rightnow(status)`.

#### After Improvement

Operator thấy trạng thái Cambrian ngay khi chọn model.

#### Improvement Value

| Area | Value |
|------|-------|
| Operator experience | ON/OFF/DEBUG visible |
| Debugging | Giảm nhầm lẫn config |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-AI-G04 | Load model bất kỳ | Xem UI | Status CAMBRIAN:ON/OFF/DEBUG |

#### Rollback

Xóa status line. **Rủi ro:** thấp.

#### Suggested Implementation Window

Week 3–4 (optional) — UX, không blocker.

---

## Ref

`03_cambrian_space_fail_policy.md` · `04_dependency_deployment/03_startup_preflight_check.md` · `07_camera_io_sfis.md` §5
