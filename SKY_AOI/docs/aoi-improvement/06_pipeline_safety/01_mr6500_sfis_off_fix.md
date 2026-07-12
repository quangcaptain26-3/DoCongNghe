# MR6500 SFIS Off & Offline — Compact Playbook

**File:** `sky.py` · **Workstream:** `06_pipeline_safety`  
**Nguồn:** `13_mr6500_pipeline.md`, `07_camera_io_sfis.md` §4, `10_risks_and_bugs.md`  
**Luật:** `show_image_MR6500` không gọi `self.mysfis` khi `sfis_choose=False`; thiếu golden sample → Fail có cấu trúc, không crash.

> Repo: `show_image_MR6500` G1870; SFIS G1899–1905; `sample/{liaohao}.jpg` G1905; except G2008. Analysis: L2032–2038. **Ctrl+F** `def show_image_MR6500`.

---

## Improvement Purpose

Mục tiêu của cải tiến này là MR6500 pipeline fail an toàn khi SFIS off hoặc thiếu golden sample — guard `sfis_choose`, check `imread` null, except → Fail UI có cấu trúc. Rõ behavior offline thay vì crash opaque.

## Before Improvement

Trước cải tiến, `show_image_MR6500` gọi `self.mysfis.get_sfis_SN`/`get_sfis_90` không guard `sfis_choose` (G1899) → crash khi SFIS off; `cv2.imread` null không check trước crop → exception; except cuối chỉ log — không Fail UI/count. Sensor line crash hoặc stall khi test offline hoặc thiếu sample liaohao.

## After Improvement

Sau cải tiến: `if not self.sfis_choose` → offline path Fail + count + return; `os.path.isfile` + null check trước crop; except → Fail UI + updatecount. SFIS off: operator thấy "SFIS Offline"; thiếu sample: Fail có cấu trúc; line recover qua `wait_test`.

## Improvement Value

| Area                        | Value |
| --------------------------- | ----- |
| Production stability        | MR6500 không crash khi SFIS off — sensor line tiếp tục |
| Operator experience         | Message "SFIS offline" / Fail rõ thay vì crash |
| MES/SFIS integrity          | Không gọi SFIS khi off; không upload ambiguous |
| Maintainability             | Guard pattern tái dùng cho offline test |
| Debugging / troubleshooting | Log offline path vs missing sample |

## Before / After Summary

| Aspect           | Before | After |
| ---------------- | ------ | ----- |
| Runtime behavior | SFIS off → AttributeError; null imread crash | Guard sfis_choose; structured Fail |
| Error handling   | except chỉ log | Fail UI + count + return |
| Operator impact  | Crash/restart sensor line | Fail message; cycle continues |
| Production risk  | Downtime sensor khi SFIS maintenance | Offline test an toàn |

---

## Bảng tổng

| ID | Vấn đề | Đi tới | Anchor (đúng chỗ khi thấy…) | Thao tác | Test |
|----|--------|--------|-----------------------------|----------|------|
| **PIPE-M01** | `mysfis` không guard `sfis_choose` | G1899 / F `get_sfis_SN` trong `show_image_MR6500` | Sau `reader.getISN()[0]==True`, **trước** `get_sfis_SN` · **Sai:** `__init__` SFIS | **Bọc** `if self.sfis_choose:` + nhánh offline | M-02 không crash |
| **PIPE-M02** | `imread` null không check | G1905 / F `sample/"+liaohao` | Trước crop `[int(y1):int(y2)]` · **Sai:** except ngoài | **Chèn** `os.path.isfile` + null check | M-04 Fail + count |
| **PIPE-M03** | except chỉ log | G2008 / F `except Exception` cuối MR6500 | Cuối `show_image_MR6500` try · **Sai:** `go_run2` | **Chèn** Fail UI + `updatecount` | Exception → Fail |

**Ship:** PIPE-M01 → PIPE-M02 → PIPE-M03

---

## Diff patches

### PIPE-M01 · guard SFIS G1896–1905

**Đúng chỗ:** nhánh decode OK, trước `mbsn=((self.mysfis.get_sfis_SN` · **Sai:** wrap toàn hàm

```python
# TRƯỚC
            if reader.getISN()[0]==True:
                logging.info(f"Get isn OK")
                self.myuihand.textbox.emit("Get isn OK")
                mbsn=((self.mysfis.get_sfis_SN(reader.getISN()[1])).split("\x7f")[2]).split(":")[1]
                self.mbsn=str(mbsn)
                self.lineEdit_8.setText(str(mbsn))  
                liaohao=(self.mysfis.get_sfis_90(mbsn)).split("\x7f")[2]
                ...
                sample_image=(cv2.imread("sample/"+liaohao+".jpg"))[int(y1):int(y2), int(x1):int(x2)]

# SAU
            if reader.getISN()[0]==True:
                logging.info(f"Get isn OK")
                self.myuihand.textbox.emit("Get isn OK")
                if not self.sfis_choose:
                    logging.warning("MR6500 SFIS off — offline path")
                    self.myuihand.textbox.emit("SFIS offline — cannot resolve liaohao")
                    self.resultcolor("Fail")
                    self.lineEdit_9.setText("SFIS Offline")
                    self.updatecount(str(int(self.lineEdit_4.text()) + 1),
                                     self.lineEdit_5.text(),
                                     str(int(self.lineEdit_6.text()) + 1),
                                     "%.2f%%" % ((int(self.lineEdit_5.text())) / (int(self.lineEdit_4.text()) + 1) * 100))
                    return
                mbsn=((self.mysfis.get_sfis_SN(reader.getISN()[1])).split("\x7f")[2]).split(":")[1]
                self.mbsn=str(mbsn)
                self.lineEdit_8.setText(str(mbsn))
                liaohao=(self.mysfis.get_sfis_90(mbsn)).split("\x7f")[2]
                ...
```

Rollback: xóa `if not self.sfis_choose` block; yêu cầu SFIS on trên trạm MR6500.

---

### PIPE-M02 · validate golden sample G1905

**Đúng chỗ:** sau `liaohao=...`, trước crop sample · **Sai:** trong `except` only

```python
# TRƯỚC
                liaohao=(self.mysfis.get_sfis_90(mbsn)).split("\x7f")[2]
                logging.info(f"Get 90 OK")
                self.myuihand.textbox.emit("Get 90 OK")
                sample_image=(cv2.imread("sample/"+liaohao+".jpg"))[int(y1):int(y2), int(x1):int(x2)]

# SAU
                liaohao=(self.mysfis.get_sfis_90(mbsn)).split("\x7f")[2]
                logging.info(f"Get 90 OK")
                self.myuihand.textbox.emit("Get 90 OK")
                sample_path = "sample/" + liaohao + ".jpg"
                if not os.path.isfile(sample_path):
                    logging.error(f"Missing golden: {sample_path}")
                    self.myuihand.textbox.emit(f"Missing golden: {sample_path}")
                    self.resultcolor("Fail")
                    self.lineEdit_9.setText("Missing Sample")
                    self.updatecount(str(int(self.lineEdit_4.text()) + 1),
                                     self.lineEdit_5.text(),
                                     str(int(self.lineEdit_6.text()) + 1),
                                     "%.2f%%" % ((int(self.lineEdit_5.text())) / (int(self.lineEdit_4.text()) + 1) * 100))
                    return
                sample_image = cv2.imread(sample_path)
                if sample_image is None:
                    logging.error(f"Cannot read: {sample_path}")
                    self.resultcolor("Fail")
                    self.lineEdit_9.setText("Bad Sample")
                    return
                sample_image = sample_image[int(y1):int(y2), int(x1):int(x2)]
```

---

### PIPE-M03 · except → Fail G2008

```python
# TRƯỚC
        except Exception as e:
            logging.error(str(e))
            self.myuihand.textbox.emit(str(e))

    def show_image_HH4K(self,image_numpy):

# SAU
        except Exception as e:
            logging.error(str(e))
            self.myuihand.textbox.emit(str(e))
            self.resultcolor("Fail")
            self.lineEdit_9.setText("Error")
            self.updatecount(str(int(self.lineEdit_4.text()) + 1),
                             self.lineEdit_5.text(),
                             str(int(self.lineEdit_6.text()) + 1),
                             "%.2f%%" % ((int(self.lineEdit_5.text())) / (int(self.lineEdit_4.text()) + 1) * 100))
```

---

## Verification

| Test ID | Fix ID | Setup | Action | Expected result |
|---------|--------|-------|--------|-----------------|
| T-M01 | PIPE-M01 | `sfis_choose=False`, MR6500 decode OK | 1 cycle | Không AttributeError; Fail "SFIS Offline"; count cập nhật |
| T-M02 | PIPE-M02 | Đổi tên `sample/{liaohao}.jpg` | 1 cycle SFIS on | Fail "Missing Sample" + count; không crash crop |
| T-M03 | PIPE-M03 | Ép exception trong `show_image_MR6500` | 1 cycle | Fail UI + count — không chỉ log |
| T-M04 | Regression | SFIS on + sample OK | Pass + Fail cycle | Không regression baseline (M-01) |

Chi tiết matrix M-01…M-06 bên dưới.

## Test matrix

| # | Setup | Kỳ vọng |
|---|-------|---------|
| M-01 | SFIS on + sample OK | Pass/Fail bình thường |
| M-02 | `sfis_choose=False`, decode OK | Không crash; Fail "SFIS Offline" |
| M-03 | SFIS response `\x7f` lỗi | Fail có cấu trúc |
| M-04 | Thiếu `sample/{liaohao}.jpg` | Fail + count |
| M-06 | Decode fail G1988 | Không regression |

## Rollback

| Fix ID | Rollback | Behavior cũ quay lại | Rủi ro nếu rollback |
|--------|----------|----------------------|---------------------|
| PIPE-M01 | Xóa block `if not self.sfis_choose` | SFIS off → crash `mysfis` | Trạm offline không test được |
| PIPE-M02 | Khôi phục imread inline không check | Null crop → exception | Crash khi liaohao mới chưa có golden |
| PIPE-M03 | Xóa Fail UI trong except | Exception chỉ log | Operator không thấy Fail; count lệch |

## Implementation Window

| Fix ID | Suggested window | Reason |
|--------|------------------|--------|
| PIPE-M01 | Week 2 (P3) | Guard offline; test M-02 trên clone |
| PIPE-M02 | Week 2 | Cùng PR M01; cần case liaohao thiếu golden |
| PIPE-M03 | Week 2 | Nhỏ; đi cùng 2 fix trên |

## Smoke

- [ ] M-02 SFIS off không AttributeError
- [ ] M-04 missing sample → Fail trên UI

## Per-Fix Detail

### PIPE-M01 — SFIS `sfis_choose` guard MR6500

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G1899 / `get_sfis_SN` trong `show_image_MR6500` |
| Lines | Sau `reader.getISN()[0]==True`, trước `get_sfis_SN` |
| Legacy alias | M-02 (test matrix) |

#### Current Problem

`show_image_MR6500` gọi `self.mysfis.get_sfis_SN`/`get_sfis_90` không guard `sfis_choose` → AttributeError khi SFIS off.

#### Before Improvement

Decode OK → gọi `mysfis` trực tiếp; offline test crash.

#### Required Change

Bọc: `if not self.sfis_choose:` → log offline, Fail UI "SFIS Offline", updatecount, `return`.

#### After Improvement

SFIS off + decode OK → Fail có cấu trúc; không crash; count cập nhật.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | MR6500 không crash khi SFIS maintenance |
| Operator experience | Message "SFIS offline" rõ |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-M01 | `sfis_choose=False`, decode OK | 1 cycle | Không AttributeError; Fail "SFIS Offline" |
| M-02 | SFIS off, decode OK | Cycle | Không crash; Fail message |

#### Rollback

Xóa block `if not self.sfis_choose`. **Rủi ro:** trạm offline không test được.

#### Suggested Implementation Window

Month 1 pipeline — Week 2 (P3); test M-02 trên clone.

---

### PIPE-M02 — Golden sample `imread` validation

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G1905 / `sample/"+liaohao` |
| Lines | Sau `liaohao=...`, trước crop `[int(y1):int(y2)]` |
| Legacy alias | M-04 (test matrix) |

#### Current Problem

`cv2.imread("sample/"+liaohao+".jpg")` null không check → exception khi crop; thiếu golden im lặng crash.

#### Before Improvement

Inline imread + slice — null hoặc missing file → exception opaque.

#### Required Change

`os.path.isfile(sample_path)` check; `imread` null check; Fail UI "Missing Sample"/"Bad Sample" + updatecount + `return`.

#### After Improvement

Thiếu/hỏng golden → Fail có cấu trúc; không crash crop.

#### Improvement Value

| Area | Value |
|------|-------|
| Production stability | Không crash liaohao mới chưa có golden |
| Operator experience | Fail "Missing Sample" trên UI |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-M02 | Đổi tên `sample/{liaohao}.jpg` | 1 cycle SFIS on | Fail "Missing Sample" + count |
| M-04 | Thiếu golden file | Cycle | Fail + count |

#### Rollback

Khôi phục imread inline không check. **Rủi ro:** crash khi liaohao mới.

#### Suggested Implementation Window

Month 1 pipeline — Week 2; cùng PR PIPE-M01.

---

### PIPE-M03 — MR6500 except → structured Fail

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G2008 / `except Exception` cuối `show_image_MR6500` |
| Lines | Cuối try `show_image_MR6500` |
| Legacy alias | — |

#### Current Problem

Except cuối chỉ log — không Fail UI/count; operator không thấy kết quả; count lệch.

#### Before Improvement

```python
        except Exception as e:
            logging.error(str(e))
            self.myuihand.textbox.emit(str(e))
```

#### Required Change

Thêm `resultcolor("Fail")`, `lineEdit_9` "Error", `updatecount` fail formula.

#### After Improvement

Exception → Fail UI + count; line recover qua orchestration.

#### Improvement Value

| Area | Value |
|------|-------|
| Operator experience | Fail rõ thay vì chỉ log |
| Production stability | Count đúng sau exception |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-M03 | Ép exception trong `show_image_MR6500` | 1 cycle | Fail UI + count — không chỉ log |

#### Rollback

Xóa Fail UI trong except. **Rủi ro:** operator không thấy Fail; count lệch.

#### Suggested Implementation Window

Month 1 pipeline — Week 2; đi cùng M01/M02.

---

## Ref

`13_mr6500_pipeline.md` · `02_sfis_mes_integrity/01_sfis_upload_helper.md` · `01_deployment_bundle_checklist.md` MR6500 golden
