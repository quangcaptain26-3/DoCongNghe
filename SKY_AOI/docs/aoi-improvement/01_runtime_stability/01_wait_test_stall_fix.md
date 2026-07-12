# Sửa Stall `wait_test` — Compact Playbook

**File:** `sky.py` · **Workstream:** `01_runtime_stability`  
**Nguồn:** `04_state_machine.md`, `08_model_dispatch.md`, `10_risks_and_bugs.md`, `11_refactor_plan.md`  
**Luật:** Mọi thoát `go_run3`/vision bất thường → `wait_test=True` (trừ `stop_program=True` cố ý).

> Line từ repo hiện tại. **Ctrl+F anchor** trước khi sửa — lệch line thì tin chuỗi text.

---

## Improvement Purpose

Mục tiêu của cải tiến này là tránh tình trạng chương trình bị treo sau lỗi ngoại lệ, lỗi cấu hình hoặc lỗi SFIS/Cambrian, bằng cách đảm bảo mọi nhánh fail/reject/exception đều trả control về vòng test với `wait_test=True`. Đây là nhóm cải tiến ưu tiên cao nhất — ảnh hưởng trực tiếp vận hành line, không thay đổi thuật toán vision.

## Before Improvement

Trước cải tiến, nhiều nhánh thoát bất thường không reset `wait_test`: `select_model` không khớp branch nào trong `go_run3` có thể return im lặng (L1910); HH4K chỉ xử lý `if step1==True` nên exception/thiếu JSON không có fail path (L994); Button_check reject Flip dialog không set flag (L1450); SFIS `data_upload` throw bỏ qua `wait_test=True` phía sau (Cisco L1357); `cambrian_space` except trả `None`. Vòng test chính vẫn nghĩ đang xử lý DUT hiện tại — operator thấy app đứng im, phải Stop/restart.

## After Improvement

Sau cải tiến, mọi path bất thường đều trả control về vòng test: unknown model vào `else` fallback, log model lỗi, báo operator, set `wait_test=True`; HH4K có `elif stepN==False` với Fail UI + count; Flip reject set `wait_test=True` ngay đầu block; SFIS fail upload bọc try/except, `wait_test` luôn ngoài try; Cambrian except trả `"Fail"`. Line recover và sẵn sàng DUT tiếp không cần restart app.

## Improvement Value

| Area                        | Value |
| --------------------------- | ----- |
| Production stability        | Giảm nguy cơ line bị treo sau lỗi model/config/SFIS/Cambrian |
| Operator experience         | Operator nhận lỗi rõ thay vì app đứng im; Stop/Start dễ kiểm soát hơn |
| MES/SFIS integrity          | SFIS throw không còn bỏ qua chu kỳ test — giảm stall kèm upload dở dang |
| Maintainability             | Fallback `else` chung cho unknown model; pattern try/finally tái dùng |
| Debugging / troubleshooting | Log model lỗi, SFIS exception, và thời điểm reset `wait_test` |

## Before / After Summary

| Aspect           | Before | After |
| ---------------- | ------ | ----- |
| Runtime behavior | Vòng test kẹt khi fail path không reset `wait_test` | Mọi fail/reject/exception trả về chờ DUT tiếp |
| Error handling   | SFIS throw, unknown model, HH4K except im lặng | try/except SFIS, else fallback, elif fail rõ ràng |
| Operator impact  | Phải Stop/restart; không biết lý do treo | Thấy Fail/Config Error; DUT tiếp sau lỗi |
| Production risk  | Downtime cao, throughput giảm | Giảm downtime, giảm thao tác restart |

---

## Per-Fix Detail

## Fix AI-001 — `cambrian_space` except returns None

### Code Location

| Field | Detail |
|---|---|
| File | sky.py |
| Function / Block | `cambrian_space` — `except` cuối hàm |
| Current lines | G2595 / L2643 (grep `except` trước `def show_image_SKY`) |
| Suggested patch location | Cuối `except Exception as e:` block, trước `def show_image_SKY` — thêm `return "Fail"` |

### Current Problem

`cambrian_space` except chỉ log + emit textbox, không return. Caller nhận implicit `None` — nhánh `if Pass`/`elif Fail` không match → step state mơ hồ, có thể stall hoặc vacuous pass.

### Before Improvement

Exception trong Cambrian inference/crop → `None` → caller không set `stepN=False` rõ → vòng test có thể kẹt hoặc fail path không recover.

### Required Change

Thêm một dòng `return "Fail"` trong `except`:

```python
        except Exception as e:
            logging.error(str(e))
            self.myuihand.textbox.emit(str(e))
            return "Fail"
```

### After Improvement

Exception → `"Fail"` → caller `elif Fail` chạy → `stepN=False`, UI Fail, `wait_test` reset qua orchestration.

### Improvement Value

| Area | Value |
|---|---|
| Production stability | Chặn stall từ Cambrian except im lặng |
| Operator experience | Fail rõ thay vì app đứng im |
| MES/SFIS integrity | N/A |
| Maintainability | Một dòng, pattern tái dùng cho AI-FAIL-001 |
| Debugging / troubleshooting | Log exception + Fail path rõ |

### Verification

| Test ID | Setup | Action | Expected result |
|---|---|---|---|
| T-AI-001 | Ép exception trong `cambrian_space` (crop ROI invalid) | Chạy step Cambrian | Trả `"Fail"`; stepN=False; không None |

### Rollback

Xóa `return "Fail"`. Behavior cũ: except → implicit None. Rủi ro: caller mơ hồ; có thể stall.

### Suggested Implementation Window

| Window | Reason |
|---|---|
| Week 1 | 1 dòng, rủi ro thấp; chặn None ngay |

---

## Fix RT-001 — Unknown model fallback

### Code Location

| Field | Detail |
|---|---|
| File | sky.py |
| Function / Block | `go_run3` — cuối chuỗi `elif self.select_model` |
| Current lines | G1910 / L1910 (`stop_program=True` trước `def show_image`) |
| Suggested patch location | End of `go_run3`, sau nhánh `elif mychoose == 65536` cuối, trước `def show_image(self,image_path)` |

### Current Problem

`go_run3` có nhiều `if/elif` cho `select_model` đã biết nhưng không có `else` cuối. Model string không khớp → return im lặng, `wait_test` vẫn False → app trông treo.

### Before Improvement

Main loop set `wait_test=False` trước dispatch. Unknown model → không branch nào chạy → `wait_test` False → DUT tiếp không start; operator phải Stop/restart.

### Required Change

Chèn `else:` cuối `go_run3`:

```python
        else:
            logging.error(f"Unknown select_model: {self.select_model}")
            self.myuihand.textbox.emit(f"Unknown model: {self.select_model}")
            self.resultcolor("Fail")
            self.lineEdit_9.setText("Config Error")
            self.wait_test = True
```

### After Improvement

Unknown model → config error có kiểm soát → operator thấy message → log có model string → loop về ready state.

### Improvement Value

| Area | Value |
|---|---|
| Production stability | Chặn stall typo model/config |
| Operator experience | Lỗi rõ thay vì app đứng im |
| MES/SFIS integrity | N/A |
| Maintainability | An toàn khi thêm model mới |
| Debugging / troubleshooting | Log chứa unknown model value |

### Verification

| Test ID | Setup | Action | Expected result |
|---|---|---|---|
| T-RT-001 | Model JSON `model` = chuỗi giả không có trong `go_run3` | Start 1 chu kỳ | Log "Unknown select_model"; `wait_test=True`; DUT tiếp không cần Stop |

### Rollback

Xóa block `else` cuối `go_run3`. Rủi ro: unknown model stall lại.

### Suggested Implementation Window

| Window | Reason |
|---|---|
| Week 1 | P0 stall; fallback low-risk |

---

## Fix RT-003 — Button_check Flip reject stall

### Code Location

| Field | Detail |
|---|---|
| File | sky.py |
| Function / Block | `go_run3` → Button_check → `elif mychoose == 65536` sau Flip dialog |
| Current lines | G1450 / L1450 |
| Suggested patch location | Đầu block `elif mychoose == 65536:`, trước `QMessageBox.question` exit |

### Current Problem

Operator reject Flip (65536) → block không set `wait_test=True` → vòng test kẹt chờ DUT hiện tại.

### Before Improvement

Reject Flip → dialog exit → không reset `wait_test` → app đứng im; operator Stop mỗi lần reject.

### Required Change

Thêm `self.wait_test = True` đầu block reject:

```python
            elif mychoose == 65536:
                self.wait_test = True
                mychoose = QMessageBox.question(self, "Warning", "Yes for exit")
```

### After Improvement

Reject Flip → `wait_test=True` ngay → chu kỳ tiếp không cần Stop.

### Improvement Value

| Area | Value |
|---|---|
| Production stability | Chặn stall Button_check Flip reject |
| Operator experience | DUT tiếp sau reject |
| MES/SFIS integrity | N/A |
| Maintainability | 1 dòng; map PIPE-B02 |
| Debugging / troubleshooting | N/A |

### Verification

| Test ID | Setup | Action | Expected result |
|---|---|---|---|
| T-RT-003 | Button_check, tới dialog Flip | Reject Flip (65536) | `wait_test=True`; chu kỳ tiếp |

### Rollback

Xóa dòng `wait_test=True`. Rủi ro: reject Flip → stall lại.

### Suggested Implementation Window

| Window | Reason |
|---|---|
| Week 1 | 1 dòng; P0 stall Button_check |

---

## Fix SFIS-001 — SFIS upload exception skip `wait_test`

### Code Location

| Field | Detail |
|---|---|
| File | sky.py |
| Function / Block | `go_run3` fail upload blocks (16 sites không có try) |
| Current lines | Cisco step2 G1357/L1224; SKY L1016–1116; WP L1412–1513; Nanook L1641–1742 |
| Suggested patch location | Mỗi block `data_upload` + `wait_test=True` chưa có `try:` — bọc try; `wait_test` **luôn ngoài** except |

### Current Problem

SFIS `data_upload` throw → exception bỏ qua `wait_test=True` phía sau → line treo. Site đầu tiên trong playbook: Cisco step2 fail L1224.

### Before Improvement

Fail path gọi `data_upload` bare → network/SOAP lỗi → skip reset `wait_test` → operator Stop/restart; MES upload dở dang.

### Required Change

Bọc try/except theo diff mẫu Cisco L1224–1229; lặp 16 site "Không" trong `01_sfis_upload_helper.md`. Chi tiết site-by-site xem SFIS-001 bảng 16 dòng.

### After Improvement

SFIS throw → log + emit "cycle continues" → `wait_test=True` → DUT tiếp.

### Improvement Value

| Area | Value |
|---|---|
| Production stability | Line không treo khi SFIS flaky |
| Operator experience | Thông báo SFIS failed thay vì đứng im |
| MES/SFIS integrity | Giảm chu kỳ treo giữa upload |
| Maintainability | Pattern chung trước helper Month 2 |
| Debugging / troubleshooting | Log SFIS exception kèm step |

### Verification

| Test ID | Setup | Action | Expected result |
|---|---|---|---|
| T-SFIS-001 | Mock `data_upload` raise trên Cisco step2 fail | Chạy fail cycle | Log SFIS error; `wait_test=True`; loop tiếp |

### Rollback

Bỏ try/except từng site (16 chỗ). Rủi ro: line treo khi SFIS/network lỗi.

### Suggested Implementation Window

| Window | Reason |
|---|---|
| Week 1–2 | P0; nhiều site — chia 2–3 PR nhỏ |

---

## Fix RT-002A — HH4K exception stall (missing JSON)

### Code Location

| Field | Detail |
|---|---|
| File | sky.py |
| Function / Block | `go_run3` → HH4K → sau `if step1==True` block |
| Current lines | G994 / L1029–1030 (giữa cuối `if step1==True` và `elif mychoose==65536` STEP1) |
| Suggested patch location | Sau block `if self.step1==True:`, trước `elif mychoose==65536` STEP1 |

### Current Problem

HH4K chỉ xử lý `if step1==True`. Exception/thiếu JSON → `step1` không True cũng không False rõ → không fail path → `wait_test` không reset.

### Before Improvement

Đổi tên `point/step1.json` → exception hoặc step1 không set → không `elif step1==False` → stall.

### Required Change

Chèn `elif self.step1==False:` với Fail UI + `updatecount` + `wait_test=True` (copy Cisco L1369, bỏ SFIS).

### After Improvement

Missing JSON / vision fail → Fail UI + count → `wait_test=True` → recover không restart.

### Improvement Value

| Area | Value |
|---|---|
| Production stability | HH4K recover sau missing JSON |
| Operator experience | Fail rõ; DUT tiếp |
| MES/SFIS integrity | N/A (HH4K không SFIS) |
| Maintainability | Pattern elif fail cho HH4K |
| Debugging / troubleshooting | Log "step1 test fail or error" |

### Verification

| Test ID | Setup | Action | Expected result |
|---|---|---|---|
| T-RT-002A | HH4K, đổi tên `point/step1.json` | Start STEP 1 | Fail UI + count; `wait_test=True`; recover |

### Rollback

Xóa block `elif step1==False`. Rủi ro: HH4K exception → stall.

### Suggested Implementation Window

| Window | Reason |
|---|---|
| Week 1–2 | Cần test HH4K missing-JSON trên clone |

---

## Fix RT-002B — HH4K vision except im lặng (optional)

### Code Location

| Field | Detail |
|---|---|
| File | sky.py |
| Function / Block | `show_image_HH4K` — `except` cuối hàm |
| Current lines | G2525 (trước `def yolov5_inference`) |
| Suggested patch location | Trong `except` của `show_image_HH4K` — set `stepN=False` hoặc return Fail |

### Current Problem

Vision except trong `show_image_HH4K` chỉ log — không propagate fail state. RT-002A đủ cho missing JSON; fix này optional cho exception trong vision body.

### Before Improvement

Exception trong vision → log only → orchestration không biết fail → có thể stall nếu RT-002A chưa cover.

### Required Change

Optional: trong except set flag hoặc return để caller set `stepN=False`. **Short-term:** RT-002A đủ; ship RT-002B nếu audit thêm exception path.

### After Improvement

Vision except → step fail rõ → `wait_test` reset qua orchestration.

### Improvement Value

| Area | Value |
|---|---|
| Production stability | Bổ sung RT-002A cho vision except |
| Operator experience | Fail rõ hơn |
| MES/SFIS integrity | N/A |
| Maintainability | Optional — đánh giá sau RT-002A |
| Debugging / troubleshooting | Log + fail state |

### Verification

| Test ID | Setup | Action | Expected result |
|---|---|---|---|
| T-RT-002B | Ép exception trong `show_image_HH4K` body | STEP 1 | step1=False; recover (nếu implemented) |

### Rollback

Xóa except handling thêm. Rủi ro thấp nếu RT-002A vẫn còn.

### Suggested Implementation Window

| Window | Reason |
|---|---|
| Month 1 | Optional sau RT-002A + PIPE-H03 |

---

## Bảng tổng

| ID | Vấn đề | Đi tới | Anchor (đúng chỗ khi thấy…) | Thao tác | Test |
|----|--------|--------|-----------------------------|----------|------|
| **AI-001** | `cambrian_space` except → `None` | G2595 / F `def cambrian_space` | `except` cuối hàm, trước `def show_image_SKY` | **+1 dòng** `return "Fail"` | Cambrian off → Fail |
| **RT-001** | Unknown model, không `else` | G1910 / F `def show_image(self,image_path)` | L1910 `stop_program=True` → blank → `def show_image` · **Sai:** thấy `WP_check` | **Chèn** `else:` 8 sp giữa L1910–L1913 | Typo model → DUT tiếp |
| **RT-003** | Reject Flip → stall | G1450 / F `Please Flip the model` | `elif mychoose==65536` sau Flip dialog · **Sai:** block trong STEP test | **+1 dòng** `wait_test=True` đầu block | Reject Flip OK |
| **SFIS-001** | SFIS throw → skip `wait_test` | G1357 / F `data_upload(self.SN_8P` | step2 fail Cisco, trước `wait_test=True` | **Bọc** try/except; `wait_test` ngoài try | Mock throw → loop |
| **RT-002A** | HH4K except → stall | G994 / F `show_image_HH4K(self.shan1)` | Giữa cuối `if step1==True{…}` và `elif mychoose==65536` STEP1 (~L1030) | **Chèn** `elif step1==False` | Missing JSON → recover |
| **RT-002B** | HH4K vision except im lặng | G2525 / F `except` trong `show_image_HH4K` | Trước `def yolov5_inference` | Optional — RT-002A đủ | — |

**SFIS-001 sites** (mẫu: Button_check L1438):

| Site | G | Try? |
|------|---|------|
| Cisco step2 fail | 1357 | Không ← trước |
| WP step2–6 | 1546+ | Không |
| Nanook step2–6 | 1774+ | Không |
| step1 fail (Cisco/BC/Nanook) | 1382/1438/1894 | Có ✓ |

**Ship:** AI-001 → RT-001 → RT-003 → SFIS-001 → RT-002A

---

## Diff patches

### AI-001 · `cambrian_space` L2643

```python
# TRƯỚC
        except Exception as e:
            logging.error(str(e))
            self.myuihand.textbox.emit(str(e))

# SAU
        except Exception as e:
            logging.error(str(e))
            self.myuihand.textbox.emit(str(e))
            return "Fail"
```

Rollback: xóa `return "Fail"`.

---

### RT-001 · cuối `go_run3` L1910→L1913

```python
# TRƯỚC
            elif mychoose == 65536:
                ...
                    self.stop_program = True

    def show_image(self,image_path):

# SAU
            elif mychoose == 65536:
                ...
                    self.stop_program = True
        else:
            logging.error(f"Unknown select_model: {self.select_model}")
            self.myuihand.textbox.emit(f"Unknown model: {self.select_model}")
            self.resultcolor("Fail")
            self.lineEdit_9.setText("Config Error")
            self.wait_test = True

    def show_image(self,image_path):
```

Rollback: xóa block `else`.

---

### RT-003 · Button_check L1450

```python
# TRƯỚC
            elif mychoose == 65536:
                mychoose = QMessageBox.question(self, "Warning", "Yes for exit")

# SAU
            elif mychoose == 65536:
                self.wait_test = True
                mychoose = QMessageBox.question(self, "Warning", "Yes for exit")
```

---

### SFIS-001 · Cisco step2 L1357 (lặp cho site **Không**)

```python
# TRƯỚC
                            if self.sfis_choose==True:
                                self.mysfis.data_upload(self.SN_8P, self.data, error="BDFA01")
                            logging.error("fail upload OK")
                            ...
                            self.wait_test = True

# SAU
                            try:
                                if self.sfis_choose==True:
                                    self.mysfis.data_upload(self.SN_8P, self.data, error="BDFA01")
                                    logging.error("fail upload OK")
                                    self.myuihand.textbox.emit("fail upload OK")
                            except Exception as e:
                                logging.error(f"SFIS fail upload error: {e}")
                                self.myuihand.textbox.emit("SFIS upload failed — cycle continues")
                            self.wait_test = True
```

---

### RT-002A · HH4K L1029→L1030

```python
# TRƯỚC
                if self.step1==True:
                    ... STEP 2–4 ...
            elif mychoose==65536:

# SAU — copy Fail từ Cisco L1369, bỏ SFIS
                if self.step1==True:
                    ... GIỮ NGUYÊN ...
                elif self.step1==False:
                    logging.error("step1 test fail or error")
                    self.myuihand.textbox.emit("step1 test fail or error")
                    self.lineEdit_9.setText("Fail")
                    self.resultcolor("Fail")
                    self.updatecount(...)
                    self.wait_test = True
            elif mychoose==65536:
```

---

## Verification

| Test ID | Fix ID | Setup | Action | Expected result |
|---------|--------|-------|--------|-----------------|
| T-AI-001 | AI-001 | Ép exception trong `cambrian_space` (crop ROI invalid) | Chạy step Cambrian | Trả `"Fail"`; stepN=False; không None |
| T-RT-001 | RT-001 | Model JSON `model` = chuỗi giả không có trong `go_run3` | Start 1 chu kỳ | Log "Unknown select_model"; `wait_test=True`; DUT tiếp không cần Stop |
| T-RT-003 | RT-003 | Button_check, tới dialog Flip | Reject Flip (65536) | `wait_test=True`; chu kỳ tiếp |
| T-SFIS-001 | SFIS-001 | Mock `data_upload` raise trên Cisco step2 fail | Chạy fail cycle | Log SFIS error; `wait_test=True`; loop tiếp |
| T-RT-002A | RT-002A | HH4K, đổi tên `point/step1.json` | Start STEP 1 | Fail UI + count; `wait_test=True`; recover |

## Rollback

| Fix ID | Rollback | Behavior cũ quay lại | Rủi ro nếu rollback |
|--------|----------|----------------------|---------------------|
| AI-001 | Xóa `return "Fail"` | except → implicit None | Caller mơ hồ; có thể stall |
| RT-001 | Xóa block `else` cuối `go_run3` | Unknown model return im lặng | Stall khi typo model/config |
| RT-003 | Xóa dòng `wait_test=True` | Reject Flip → stall | Operator phải Stop mỗi lần reject |
| SFIS-001 | Bỏ try/except từng site (16 chỗ) | SFIS throw skip `wait_test` | Line treo khi SFIS/network lỗi |
| RT-002A | Xóa block `elif step1==False` | HH4K exception → stall | Treo sau missing JSON |

## Implementation Window

| Fix ID | Suggested window | Reason |
|--------|------------------|--------|
| AI-001 | Week 1 | 1 dòng, rủi ro thấp; chặn None ngay |
| RT-001 | Week 1 | P0 stall; fallback low-risk |
| RT-003 | Week 1 | 1 dòng; P0 stall Button_check |
| SFIS-001 | Week 1–2 | P0 nhưng nhiều site — chia 2–3 PR nhỏ, mock test từng nhóm |
| RT-002A | Week 1–2 | Cần test HH4K missing-JSON trên clone trước |

## Smoke

- [ ] RT-001 typo · RT-003 Flip · SFIS-001 mock throw · RT-002A missing JSON · AI-001 Cambrian off

## Ref

`00_playbook_sop.md` · `01_priority_roadmap.md` Phase B · `08_model_dispatch.md`
