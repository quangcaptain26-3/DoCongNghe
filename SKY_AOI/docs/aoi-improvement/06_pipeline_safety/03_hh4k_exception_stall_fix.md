# HH4K Exception Stall — Compact Playbook

**File:** `sky.py` · **Workstream:** `06_pipeline_safety`  
**Nguồn:** `15_hh4k_pipeline.md`, `10_risks_and_bugs.md`, `01_runtime_stability/01_wait_test_stall_fix.md`  
**Luật:** Exception / `stepN==False` sau `show_image_HH4K` → `wait_test=True` — không treo line.

> Repo: HH4K orchestration G838–900; `show_image_HH4K` G2012; point G2016–2019. **Trùng RT-002A** trong `01_wait_test_stall_fix.md`. **Ctrl+F** `elif self.select_model=="HH4K"`.

**Ghi chú:** HH4K fail vision vẫn nối STEP 2–4 khi `stepN==True` (ngữ nghĩa "đã chạy") — **ngoài scope** patch này; chỉ sửa **stall**.

---

## Improvement Purpose

Mục tiêu của cải tiến này là HH4K pipeline fail an toàn khi exception hoặc thiếu point/sample JSON — thêm `elif stepN==False` + `wait_test=True` sau mỗi `show_image_HH4K`. Chỉ sửa stall, không đổi ngữ nghĩa multi-step HH4K.

## Before Improvement

Trước cải tiến, HH4K orchestration chỉ có `if step1==True` (và tương tự step2–4) — không có `elif stepN==False`. Thiếu `point/step1.json` hoặc vision except → `stepN` không set False rõ → không `wait_test=True` → line treo. Operator phải Stop/restart sau missing JSON hoặc exception STEP 1.

## After Improvement

Sau cải tiến, mỗi step có `elif stepN==False`: log, Fail UI, updatecount, `wait_test=True`. Exception trong vision (optional PIPE-H03) set step False. Line recover; DUT tiếp sau fail STEP; không stall dù HH4K vẫn nối step khi stepN True (known behavior).

## Improvement Value

| Area                        | Value |
| --------------------------- | ----- |
| Production stability        | Giảm khả năng treo HH4K sau missing JSON/exception |
| Operator experience         | Fail message + cycle tiếp thay vì app đứng im |
| MES/SFIS integrity          | N/A (HH4K không SFIS) |
| Maintainability             | Pattern copy từ Cisco fail handler |
| Debugging / troubleshooting | Log "HH4K stepN fail" kèm step number |

## Before / After Summary

| Aspect           | Before | After |
| ---------------- | ------ | ----- |
| Runtime behavior | stepN fail → no elif → stall | elif stepN==False → wait_test |
| Error handling   | Exception im lặng optional | Fail UI + count + wait_test |
| Operator impact  | Stop/restart sau missing point | Fail rõ; Start DUT tiếp |
| Production risk  | HH4K line down time | Cải thiện khả năng vận hành HH4K |

---

## Bảng tổng

| ID | Vấn đề | Đi tới | Anchor (đúng chỗ khi thấy…) | Thao tác | Test |
|----|--------|--------|-----------------------------|----------|------|
| **PIPE-H01** | Không `elif step1==False` | G860 / F `show_image_HH4K(self.shan1)` | Sau `show_image_HH4K(shan1)`, trước `if self.step1==True` STEP2 · **Sai:** SKY branch | **Chèn** `elif step1==False` + `wait_test` | H-01 missing JSON recover |
| **PIPE-H02** | step2–4 tương tự (optional) | G867, G875, G882 | Sau mỗi `show_image_HH4K(shanN)` | Lặp pattern H01 | H-06 exception step2 |
| **PIPE-H03** | except vision im lặng | G2392 / F `except` trong `show_image_HH4K` | Trước `def yolov5_inference` · **Sai:** go_run3 | Optional `stepN=False` | — |

**Ship:** PIPE-H01 (bắt buộc) → PIPE-H02 (khuyến nghị) → PIPE-H03 (optional)

---

## Diff patches

### PIPE-H01 · `elif step1==False` G860 (copy từ Cisco G1236)

**Đúng chỗ:** HH4K STEP 1, ngay sau `self.show_image_HH4K(self.shan1)` · **Sai:** block SKY/Cisco

```python
# TRƯỚC
                self.show_image_HH4K(self.shan1)
                if self.step1==True:
                    mychoose=QMessageBox.question(self,"STEP 2","Please enter for test STEP 2")

# SAU
                self.show_image_HH4K(self.shan1)
                if self.step1==True:
                    mychoose=QMessageBox.question(self,"STEP 2","Please enter for test STEP 2")
                elif self.step1==False:
                    logging.error("HH4K step1 fail or error")
                    self.myuihand.textbox.emit("HH4K step1 fail or error")
                    self.lineEdit_9.setText("Fail")
                    self.resultcolor("Fail")
                    self.updatecount(str(int(self.lineEdit_4.text()) + 1),
                                     self.lineEdit_5.text(),
                                     str(int(self.lineEdit_6.text()) + 1),
                                     "%.2f%%" % ((int(self.lineEdit_5.text())) / (int(self.lineEdit_4.text()) + 1) * 100))
                    self.wait_test = True
```

Rollback: xóa `elif` block.

---

### PIPE-H02 · mẫu step2 G867 (lặp step3/4)

```python
# SAU — sau show_image_HH4K(self.shan2)
                        if self.step2==True:
                            mychoose=QMessageBox.question(self,"STEP 3",...)
                        elif self.step2==False:
                            logging.error("HH4K step2 fail or error")
                            ...
                            self.wait_test = True
```

---

### PIPE-H03 · except `show_image_HH4K` G2392 (optional)

```python
# TRƯỚC
        except Exception as e:
            logging.error(str(e))
            self.myuihand.textbox.emit(str(e))

# SAU
        except Exception as e:
            logging.error(str(e))
            self.myuihand.textbox.emit(str(e))
            # step index: rely on which step*==False in caller; optional set all False
```

---

## Verification

| Test ID | Fix ID | Setup | Action | Expected result |
|---------|--------|-------|--------|-----------------|
| T-H01 | PIPE-H01 | Đổi tên `point/step1.json`, HH4K | Start STEP 1 | Fail UI + count; `wait_test=True`; Start DUT tiếp |
| T-H02 | PIPE-H02 | Ép exception STEP 2 (thiếu `sample/step2.jpg`) | Chạy tới STEP 2 | Tương tự — fail path step2 |
| T-H03 | PIPE-H03 | Exception trong `show_image_HH4K` | 1 cycle | stepN=False rõ (nếu áp dụng optional) |
| T-H04 | Regression | Bundle đủ, DUT tốt | Pass 4 bước | Không regression baseline |

Chi tiết matrix H-01…H-04 bên dưới.

## Test matrix

| # | Scenario | Kỳ vọng |
|---|----------|---------|
| H-01 | Đổi tên `point/step1.json` | Fail; `wait_test=True`; Start lại được |
| H-02 | Thiếu `sample/step1.jpg` | Tương tự |
| H-04 | Pass 4 bước | Không regression |

## Rollback

| Fix ID | Rollback | Behavior cũ quay lại | Rủi ro nếu rollback |
|--------|----------|----------------------|---------------------|
| PIPE-H01 | Xóa block `elif step1==False` | Exception/missing JSON → stall | Treo HH4K quay lại — P0 |
| PIPE-H02 | Xóa các block step2–4 | Stall ở step sau | Tương tự H01 |
| PIPE-H03 | Xóa ghi chú except | Vision except im lặng | Thấp — H01/H02 đã cover |

## Implementation Window

| Fix ID | Suggested window | Reason |
|--------|------------------|--------|
| PIPE-H01 | Week 1 | P0 stall (trùng RT-002A); copy pattern Cisco |
| PIPE-H02 | Week 1–2 | Lặp pattern; test từng step trên clone |
| PIPE-H03 | Week 2 (optional) | Defense thêm, không blocker |

## Smoke

- [ ] H-01 corrupt `point/step1.json` → không treo sau STEP 1

## Per-Fix Detail

### PIPE-H01 — HH4K `elif step1==False` fail handler

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G860 / sau `show_image_HH4K(self.shan1)` |
| Lines | Sau STEP 1 vision, trước `if self.step1==True` STEP2 |
| Legacy alias | **RT-002A**; H-01 (test matrix) |

#### Current Problem

HH4K orchestration chỉ `if step1==True` — không `elif step1==False`. Missing JSON/exception → không `wait_test=True` → line treo.

#### Before Improvement

```python
                self.show_image_HH4K(self.shan1)
                if self.step1==True:
                    mychoose=QMessageBox.question(self,"STEP 2",...)
```

#### Required Change

Chèn `elif self.step1==False:` — log, Fail UI, updatecount, `wait_test=True` (copy Cisco G1236 pattern).

#### After Improvement

STEP 1 fail → Fail message; `wait_test=True`; Start DUT tiếp không Stop.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | P0 stall fix HH4K |
| Operator experience | Cycle tiếp sau missing JSON |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-H01 | Đổi tên `point/step1.json`, HH4K | Start STEP 1 | Fail UI + `wait_test=True` |
| H-01 | Corrupt step1.json | STEP 1 | Fail; recover |

#### Rollback

Xóa `elif step1==False` block. **Rủi ro:** treo HH4K quay lại — P0.

#### Suggested Implementation Window

Week 1 (P0) — copy pattern Cisco.

---

### PIPE-H02 — HH4K step2–4 fail handlers (optional)

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G867, G875, G882 |
| Lines | Sau mỗi `show_image_HH4K(shanN)` |
| Legacy alias | H-06 (test matrix) |

#### Current Problem

Step 2–4 thiếu `elif stepN==False` — stall tương tự H01 ở step sau.

#### Before Improvement

Chỉ `if step2==True` (và step3/4) — no fail elif.

#### Required Change

Lặp pattern PIPE-H01 sau `show_image_HH4K(shan2/3/4)`.

#### After Improvement

Exception/missing sample step 2–4 → fail path + `wait_test`.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Full HH4K multi-step stall coverage |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-H02 | Ép exception STEP 2 (thiếu `sample/step2.jpg`) | Chạy tới STEP 2 | Fail path step2 + wait_test |
| H-02 | Thiếu sample/step1.jpg | STEP 1 | Tương tự |

#### Rollback

Xóa các block step2–4. **Rủi ro:** stall ở step sau.

#### Suggested Implementation Window

Week 1–2 — lặp pattern; test từng step.

---

### PIPE-H03 — `show_image_HH4K` except handling (optional)

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G2392 / `except` trong `show_image_HH4K` |
| Lines | Cuối try `show_image_HH4K` |
| Legacy alias | — |

#### Current Problem

Vision except chỉ log — không set stepN=False rõ trong vision function.

#### Before Improvement

```python
        except Exception as e:
            logging.error(str(e))
            self.myuihand.textbox.emit(str(e))
```

#### Required Change

Optional: set step flags False hoặc rely on caller `elif stepN==False` (PIPE-H01/H02 đã cover).

#### After Improvement

Exception → stepN=False rõ (nếu áp dụng); defense thêm.

#### Improvement Value

| Area | Value |
|------|-------|
| Debugging | Exception path rõ hơn |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-H03 | Exception trong `show_image_HH4K` | 1 cycle | stepN=False rõ (nếu optional patch) |

#### Rollback

Xóa ghi chú/optional set. **Rủi ro:** thấp — H01/H02 đã cover.

#### Suggested Implementation Window

Week 2 (optional) — defense thêm, không blocker.

---

## Ref

`15_hh4k_pipeline.md` · `01_wait_test_stall_fix.md` RT-002A · `04_dependency_deployment/03_startup_preflight_check.md` P-06
