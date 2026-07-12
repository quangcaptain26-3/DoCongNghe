# Cache PaddleOCR — Compact Playbook

**File:** `sky.py` · **Workstream:** `05_ai_ocr_runtime`  
**Nguồn:** `07_camera_io_sfis.md` §6, `09_threading_and_ui.md`, `10_risks_and_bugs.md`, pipeline `14`, `16`, `18`  
**Luật:** `PaddleOCR(...)` **một lần mỗi lang** mỗi session — `get_ocr(lang)` singleton; không init mới trên UI thread mỗi DUT/bước.

> Repo: Nanook G1552, SKY STEP3 G2731, Cisco sync G3397, `ocr_finction_8P` G5033, `Runthread` G5401. **Ctrl+F** `PaddleOCR(`.

---

## Improvement Purpose

Mục tiêu của cải tiến này là giảm UI freeze do PaddleOCR init mỗi DUT/bước trên main thread — cache singleton `get_ocr(lang)` một lần mỗi session. Cải thiện throughput và phản hồi operator trên Nanook, SKY STEP 3, Cisco OCR.

## Before Improvement

Trước cải tiến, `PaddleOCR(...)` tạo mới mỗi chu kỳ Nanook (G1552), mỗi SKY STEP 3 (G2731), mỗi Cisco sync OCR (G3397), mỗi `Runthread.run` (G5401) — load model 2–10s trên UI thread. DUT đầu và DUT 2+ đều chậm; operator thấy UI đóng băng; Stop trễ trong OCR load.

## After Improvement

Sau cải tiến, `get_ocr(lang)` class-level cache — init một lần, reuse mọi caller. Nanook DUT 2+ nhanh rõ; SKY STEP 3 không reload; Cisco thread dùng cache. UI mượt hơn; throughput tăng trên line OCR-heavy.

## Improvement Value

| Area                        | Value |
| --------------------------- | ----- |
| Production stability        | Giảm UI block duration — ít cảm giác treo |
| Operator experience         | DUT 2+ khởi động OCR nhanh; UI phản hồi tốt hơn |
| MES/SFIS integrity          | N/A |
| Maintainability             | Single get_ocr entry; dễ đổi lang/gpu policy |
| Debugging / troubleshooting | Log "PaddleOCR loading" một lần per lang — dễ verify cache |

## Before / After Summary

| Aspect           | Before | After |
| ---------------- | ------ | ----- |
| Runtime behavior | PaddleOCR init mỗi DUT/step trên UI thread | Singleton cache per lang |
| Error handling   | N/A | N/A |
| Operator impact  | UI freeze 2–10s mỗi OCR step | DUT 2+ STEP nhanh; freeze chỉ lần đầu |
| Production risk  | Throughput thấp; operator Stop giữa load | Cải thiện khả năng vận hành line OCR |

---

## Bảng tổng

| ID | Vấn đề | Đi tới | Anchor (đúng chỗ khi thấy…) | Thao tác | Test |
|----|--------|--------|-----------------------------|----------|------|
| **AI-O01** | Không có cache helper | G587 / F `def get_inference_result` | Trước `get_inference_result` hoặc sau imports class · **Sai:** module mới | **Chèn** `get_ocr(lang)` singleton | 2× gọi → 1 log "loading" |
| **AI-O02** | Nanook init mỗi DUT | G1552 / F `elif self.select_model == "Nanook"` | Dòng `self.nanook_ocr = PaddleOCR` · **Sai:** trong `show_image_Nanook` STEP 3 | **Đổi** → `self.get_ocr("en")` | DUT 2 nhanh hơn DUT 1 |
| **AI-O03** | SKY STEP 3 init mỗi lần | G2731 / F `ocr = PaddleOCR` trong `show_image_SKY` | Nhánh `stepname == "STEP 3"` · **Sai:** STEP 1/2 | **Đổi** → `self.get_ocr("ch")` | SKY DUT 2 STEP3 nhanh |
| **AI-O04** | Cisco sync OCR init | G3397 / F `ocr1 = PaddleOCR` | Cisco STEP 1 sync ocr3 block · **Sai:** `Runthread` | **Đổi** → `self.get_ocr("ch")` | Cisco STEP1 không regression |
| **AI-O05** | `ocr_finction_8P` + Runthread | G5033 / G5401 | Helper G5033; `Runthread.run` G5401 · **Sai:** đổi thread model | **Đổi** hoặc thread-local cache | Cisco OCR thread OK |

**Ship:** AI-O01 → AI-O02 → AI-O03 → AI-O04 → AI-O05

**Không ảnh hưởng:** MR6500, HH4K, Button_check (không PaddleOCR active path).

---

## Bản đồ init hiện tại (TRƯỚC)

| Site | G | Thread | Mỗi DUT? |
|------|---|--------|----------|
| Nanook entry | G1552–1553 | UI | ✅ mỗi chu kỳ |
| SKY STEP 3 | G2731–2732 | UI | ✅ mỗi STEP 3 |
| SKY YOLO dead path | G3118 | UI | (dead) |
| Cisco ocr3 sync | G3397–3398 | UI | ✅ |
| Cisco STEP2 topdate | G4015 | UI | ✅ |
| `ocr_finction_8P` | G5033 | UI | ✅ mỗi gọi |
| `Runthread.run` | G5401 | QThread | ✅ mỗi thread run |

---

## Diff patches

### AI-O01 · `get_ocr` singleton

**Đúng chỗ:** class chính, trước `get_inference_result` G587 · **Sai:** global ngoài class

```python
# TRƯỚC
    def get_inference_result(self, img_list):
        image_result_list = []

# SAU
    _ocr_cache = {}  # class-level: lang -> PaddleOCR instance

    def get_ocr(self, lang="ch", use_gpu=False):
        key = f"{lang}_{use_gpu}"
        if key not in Demo._ocr_cache:
            logging.info(f"PaddleOCR loading lang={lang} ...")
            Demo._ocr_cache[key] = PaddleOCR(
                use_gpu=use_gpu,
                use_angle_cls=True,
                lang=lang,
            )
            logging.info("PaddleOCR ready")
        return Demo._ocr_cache[key]

    def get_inference_result(self, img_list):
        image_result_list = []
```

Rollback: xóa `_ocr_cache` + `get_ocr`.

---

### AI-O02 · Nanook G1552

**Đúng chỗ:** nhánh Nanook orchestration, dòng `PaddleOCR(lang="en")` · **Sai:** `show_image_Nanook` STEP 3/5 (đã reuse `self.nanook_ocr`)

```python
# TRƯỚC
        elif self.select_model == "Nanook":
            self.thissn = "None"
            self.nanook_ocr = PaddleOCR(use_gpu=False, use_angle_cls=True,
                            lang="en", )
            self.step1 = False

# SAU
        elif self.select_model == "Nanook":
            self.thissn = "None"
            self.nanook_ocr = self.get_ocr("en")
            self.step1 = False
```

---

### AI-O03 · SKY STEP 3 G2731

**Đúng chỗ:** trong `show_image_SKY`, block STEP 3, trước `img_path = "source/model.jpg"` · **Sai:** STEP 1 Cambrian block

```python
# TRƯỚC
                ocr = PaddleOCR(use_gpu=False, use_angle_cls=True,
                                lang="ch", )

                img_path = "source/model.jpg"

# SAU
                ocr = self.get_ocr("ch")

                img_path = "source/model.jpg"
```

Lặp tương tự nếu có duplicate trong `show_image_SKY_yolo` G3118 (dead path — optional).

---

### AI-O04 · Cisco sync ocr3 G3397

**Đúng chỗ:** sau `barcode OCR start`, trước `result3 = ocr1.ocr` · **Sai:** trong `Runthread`

```python
# TRƯỚC
                    ocr1 = PaddleOCR(use_angle_cls=True,
                                    lang="ch")
                    result3 = ocr1.ocr("source/8P/ocr3.jpg", cls=True)

# SAU
                    ocr1 = self.get_ocr("ch")
                    result3 = ocr1.ocr("source/8P/ocr3.jpg", cls=True)
```

**Site thứ hai:** G4015 `ocr_step2 = PaddleOCR(...)` → `self.get_ocr("ch")`.

---

### AI-O05 · `ocr_finction_8P` G5033 + `Runthread` G5401

**Helper G5033:**

```python
# TRƯỚC
        ocr = PaddleOCR(use_angle_cls=True, lang="ch")

# SAU
        ocr = self.get_ocr("ch")
```

**Runthread** — PaddleOCR có thể không thread-safe; **Option A (an toàn):** giữ init trong thread nhưng cache thread-local:

```python
# SAU — trong Runthread.run G5401
            ocr = self._parent.get_ocr("ch")  # cần truyền parent ref vào Runthread
```

**Option B (tối thiểu):** chỉ sửa UI-thread sites O02–O04 trước; Runthread giữ nguyên đến PR riêng.

Rollback: khôi phục `PaddleOCR(...)` inline từng site.

---

## Pre-load optional (sau O01)

**Đúng chỗ:** cuối `choose_model`, sau load model · **Sai:** blocking trước `exec_`

```python
# SAU — non-blocking warm-up
        if self.select_model == "Nanook":
            QTimer.singleShot(0, lambda: self.get_ocr("en"))
        elif self.select_model in ("SKY", "SKY_4G"):
            QTimer.singleShot(0, lambda: self.get_ocr("ch"))
```

---

## SOP operator (trước khi ship code)

| Triệu chứng | Nguyên nhân | Hành động |
|-------------|-------------|-----------|
| Đơ lâu Nanook STEP 1 prompt | Load OCR DUT đầu | Chờ 10–30s; báo engineering nếu DUT 2 vẫn chậm |
| Đơ SKY STEP 2→3 | Tương tự | Không double-click |

**Engineer:** cache model PaddleOCR trên disk cho trạm air-gapped (`01_deployment_bundle_checklist.md`).

---

## Verification

| Test ID | Fix ID | Setup | Action | Expected result |
|---------|--------|-------|--------|-----------------|
| T-AI-O01 | AI-O01 | `get_ocr("ch")` gọi 2 lần | Check log | Chỉ 1× "PaddleOCR loading"; cùng instance |
| T-AI-O02 | AI-O02 | Nanook 3 DUT liên tiếp | Đo thời gian tới STEP 1 | DUT 2–3 nhanh hơn DUT 1 rõ rệt (&lt;2s) |
| T-AI-O03 | AI-O03 | SKY 2 DUT, STEP 3 | So OCR text 2 DUT | Không regression accuracy; DUT 2 nhanh |
| T-AI-O04 | AI-O04 | Cisco STEP 1 Pass cycle | So kết quả OCR | Accuracy không đổi |
| T-AI-O05 | AI-O05 | Cisco OCR qua Runthread | 1 cycle | Không crash thread; kết quả đúng |

Chi tiết matrix O-01…O-07 bên dưới.

## Test matrix

| # | Scenario | Kỳ vọng sau cache |
|---|----------|-------------------|
| O-01 | Nanook DUT 1 | Baseline (chậm lần đầu) |
| O-02 | Nanook DUT 2–3 | **&lt; 2s** tới STEP 1 vs DUT 1 |
| O-03 | SKY STEP 3 DUT 2 | Nhanh hơn DUT 1 |
| O-05 | Cisco STEP 1 | Accuracy không đổi |
| O-07 | Đổi SKY → Nanook | Cache `ch` + `en` độc lập |

---

## Rollback

| Fix ID | Rollback | Behavior cũ quay lại | Rủi ro nếu rollback |
|--------|----------|----------------------|---------------------|
| AI-O01 | Xóa `_ocr_cache` + `get_ocr` | Không cache | Rollback cùng O02–O05 (caller) |
| AI-O02–O04 | Khôi phục `PaddleOCR(...)` inline từng site | UI freeze mỗi DUT/step quay lại | Perf regression, không sai kết quả |
| AI-O05 | Giữ init trong Runthread như cũ | Thread tự load | Revert riêng PR nếu thread-safety issue |

## Implementation Window

| Fix ID | Suggested window | Reason |
|--------|------------------|--------|
| SOP operator (không code) | Week 1 | Giảm double-click/kill app ngay |
| AI-O01 | Week 3–4 / Month 1 | Cache có thể ảnh hưởng performance/memory — cần runtime testing |
| AI-O02 (Nanook) | Month 1 | Worst offender trước; đo baseline DUT 1 vs 2 |
| AI-O03 (SKY), AI-O04 (Cisco) | Month 1 | Sau O02 ổn định trên clone |
| AI-O05 (Runthread) | Month 1+ PR riêng | Thread-safety cần verify riêng |

## Smoke (5 phút)

- [ ] O-02 Nanook 3 DUT liên tiếp — log chỉ 1× "PaddleOCR loading lang=en"
- [ ] O-03 SKY STEP 3 hai DUT — không regression OCR text
- [ ] O-05 Cisco một Pass cycle

## Per-Fix Detail

### AI-O01 — `get_ocr` singleton cache helper

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | Trước `def get_inference_result` G587 |
| Lines | ~G587 (class-level `_ocr_cache` + `get_ocr`) |
| Legacy alias | — |

#### Current Problem

Không có cache helper — mỗi caller tạo `PaddleOCR(...)` mới trên UI thread.

#### Before Improvement

`PaddleOCR(...)` init mỗi DUT/bước — load model 2–10s; UI freeze; log không có pattern "loading once".

#### Required Change

Chèn `_ocr_cache = {}` (class-level) và `get_ocr(self, lang, use_gpu)` singleton — init một lần per lang key, reuse mọi caller.

#### After Improvement

`get_ocr("ch")` / `get_ocr("en")` gọi 2× → cùng instance; log chỉ 1× "PaddleOCR loading".

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Giảm UI block duration |
| Maintainability | Single entry point cho OCR init |
| Debugging | Log "loading" một lần per lang |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-AI-O01 | `get_ocr("ch")` gọi 2 lần | Check log | Chỉ 1× "PaddleOCR loading"; cùng instance |
| O-07 | Đổi SKY → Nanook | 2 lang | Cache `ch` + `en` độc lập |

#### Rollback

Xóa `_ocr_cache` + `get_ocr`. **Rủi ro:** rollback cùng AI-O02–O05 (callers).

#### Suggested Implementation Window

Week 3–4 / Month 1 — cần runtime testing memory/perf.

---

### AI-O02 — Nanook OCR init cache

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G1552 / `elif self.select_model == "Nanook"` |
| Lines | L1552–1553 (`self.nanook_ocr = PaddleOCR`) |
| Legacy alias | **OCR-002 Nanook** |

#### Current Problem

Nanook tạo `PaddleOCR(lang="en")` mỗi chu kỳ DUT trên UI thread — worst offender perf.

#### Before Improvement

Mỗi DUT Nanook reload OCR 2–10s; DUT 2+ vẫn chậm như DUT 1.

#### Required Change

Đổi `self.nanook_ocr = PaddleOCR(...)` → `self.nanook_ocr = self.get_ocr("en")`.

#### After Improvement

DUT 2–3 tới STEP 1 &lt;2s vs DUT 1; log chỉ 1× loading lang=en.

#### Improvement Value

| Area | Value |
|------|-------|
| Operator experience | DUT 2+ khởi động nhanh rõ rệt |
| Production stability | Giảm UI freeze mỗi cycle |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-AI-O02 | Nanook 3 DUT liên tiếp | Đo thời gian tới STEP 1 | DUT 2–3 nhanh hơn DUT 1 (&lt;2s) |
| O-01/O-02 | Nanook DUT 1 vs 2–3 | Timing | Baseline chậm lần đầu; sau nhanh |

#### Rollback

Khôi phục `PaddleOCR(...)` inline G1552. **Rủi ro:** perf regression, không sai kết quả.

#### Suggested Implementation Window

Month 1 — worst offender trước; đo baseline DUT 1 vs 2.

---

### AI-O03 — SKY STEP 3 OCR cache

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G2731 / `ocr = PaddleOCR` trong `show_image_SKY` STEP 3 |
| Lines | L2731–2732 (nhánh `stepname == "STEP 3"`) |
| Legacy alias | **OCR-001 SKY** |

#### Current Problem

SKY STEP 3 init PaddleOCR mỗi lần chạy STEP 3 — UI freeze lặp mỗi DUT.

#### Before Improvement

`ocr = PaddleOCR(use_gpu=False, lang="ch")` mỗi STEP 3; DUT 2 vẫn reload.

#### Required Change

Đổi → `ocr = self.get_ocr("ch")`. Optional: duplicate trong `show_image_SKY_yolo` G3118 (dead path).

#### After Improvement

SKY DUT 2 STEP 3 nhanh; accuracy không đổi.

#### Improvement Value

| Area | Value |
|------|-------|
| Operator experience | STEP 2→3 transition mượt hơn DUT 2+ |
| Production stability | Giảm freeze OCR-heavy SKY line |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-AI-O03 | SKY 2 DUT, STEP 3 | So OCR text 2 DUT | Không regression accuracy; DUT 2 nhanh |
| O-03 | SKY STEP 3 DUT 2 | Timing | Nhanh hơn DUT 1 |

#### Rollback

Khôi phục `PaddleOCR(...)` inline G2731.

#### Suggested Implementation Window

Month 1 — sau AI-O02 ổn định trên clone.

---

### AI-O04 — Cisco sync OCR cache

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G3397 `ocr1 = PaddleOCR`; G4015 `ocr_step2` |
| Lines | G3397–3398 (sync ocr3); G4015 (STEP2 topdate) |
| Legacy alias | — |

#### Current Problem

Cisco sync OCR init mỗi cycle trên UI thread — STEP 1 và STEP 2 topdate.

#### Before Improvement

`ocr1 = PaddleOCR(lang="ch")` mỗi lần; không reuse.

#### Required Change

Đổi G3397 và G4015 → `self.get_ocr("ch")`.

#### After Improvement

Cisco STEP 1 không regression accuracy; init một lần per session.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Giảm freeze Cisco OCR path |
| Maintainability | Cùng cache với SKY `ch` |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-AI-O04 | Cisco STEP 1 Pass cycle | So kết quả OCR | Accuracy không đổi |
| O-05 | Cisco STEP 1 | Full cycle | Không regression |

#### Rollback

Khôi phục `PaddleOCR(...)` inline G3397/G4015.

#### Suggested Implementation Window

Month 1 — cùng đợt AI-O03.

---

### AI-O05 — `ocr_finction_8P` + Runthread cache

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G5033 `ocr_finction_8P`; G5401 `Runthread.run` |
| Lines | G5033 helper; G5396–5401 busy loop |
| Legacy alias | **OCR-004 Runthread** |

#### Current Problem

Helper `ocr_finction_8P` init mỗi gọi; `Runthread.run` init PaddleOCR + busy loop `while result==[]`.

#### Before Improvement

Mỗi thread run tạo OCR mới; busy emit trên `[]` — CPU spin.

#### Required Change

G5033 → `self.get_ocr("ch")`. Runthread Option A: `self._parent.get_ocr("ch")` (cần parent ref); Option B: giữ thread init đến PR riêng. Xóa busy loop — OCR trực tiếp một lần.

#### After Improvement

Cisco OCR thread một emit; không busy spin; shared cache nếu thread-safe verified.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Giảm CPU busy loop |
| Maintainability | Align thread path với UI cache policy |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-AI-O05 | Cisco OCR qua Runthread | 1 cycle | Không crash thread; kết quả đúng |
| PIPE-C04 | OCR pass STEP 1 | Runthread | Một emit; không busy spin |

#### Rollback

Git restore `Runthread.run` + inline `PaddleOCR` G5033. **Rủi ro:** revert riêng PR nếu thread-safety issue.

#### Suggested Implementation Window

Month 1+ PR riêng — thread-safety cần verify riêng.

---

## Ref

`07_camera_io_sfis.md` §6 · `14_sky_pipeline.md` · `16_cisco_pipeline.md` · `18_nanook_pipeline.md`
