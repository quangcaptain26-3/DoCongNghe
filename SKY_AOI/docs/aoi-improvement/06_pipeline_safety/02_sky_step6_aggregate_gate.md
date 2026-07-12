# SKY STEP 6 — Cổng Tổng Hợp & MES Pass — Compact Playbook

**File:** `sky.py` · **Workstream:** `06_pipeline_safety`  
**Nguồn:** `14_sky_pipeline.md`, `10_risks_and_bugs.md` §SKY STEP6, `11_refactor_plan.md` A-06  
**Luật:** `data_upload` STEP 6 chỉ khi `yolo_step6=="Pass"` **và** `checksn and modelcheck and sncheck`; aggregate fail → Fail UI, không MES pass.

> Repo: STEP 6 block G2896–2969 trong `show_image_SKY`; upload bug G2950–2951. Cờ: `checksn` STEP1, `modelcheck`/`sncheck` STEP3. **Ctrl+F** `elif self.step5 == True and stepname == "STEP 6"`.

---

## Improvement Purpose

Mục tiêu của cải tiến này là tránh SKY STEP 6 upload MES pass khi aggregate fail (`checksn`/`modelcheck`/`sncheck` false) — Cambrian STEP 6 Pass nhưng barcode/model/SN check fail vẫn upload và set `step6=True`.

## Before Improvement

Trước cải tiến, khi `yolo_step6=="Pass"` nhưng aggregate `my_inference_result=="fail"`: UI fail branch bị comment (G2934); `data_upload` vẫn gọi không check aggregate (G2950); `step6=True` dù fail (G2963). MES nhận pass trong khi UI/flags fail — truy vết sai, yield report lệch.

## After Improvement

Sau cải tiến: upload chỉ khi `my_inference_result=="pass"`; uncomment/viết lại fail branch Fail UI + count; `step6=True` chỉ khi aggregate pass. Operator thấy Fail; MES không pass upload khi SN/model/barcode fail; data integrity SKY STEP 6 đúng.

## Improvement Value

| Area                        | Value |
| --------------------------- | ----- |
| Production stability        | N/A |
| Operator experience         | Fail UI hiển thị khi aggregate fail — không Pass mâu thuẫn |
| MES/SFIS integrity          | Đảm bảo MES pass chỉ khi đủ checksn+modelcheck+sncheck |
| Maintainability             | Gate rõ một chỗ STEP 6 |
| Debugging / troubleshooting | Dễ audit STEP 6 pass vs aggregate flags |

## Before / After Summary

| Aspect           | Before | After |
| ---------------- | ------ | ----- |
| Runtime behavior | Cambrian Pass + aggregate fail → vẫn upload MES | Upload gated on aggregate pass |
| Error handling   | Fail UI commented out | Fail branch active |
| Operator impact  | Có thể thấy Pass UI trong khi checks fail | Fail rõ khi aggregate fail |
| Production risk  | MES false pass — rủi ro traceability cao | Giảm rủi ro sai dữ liệu MES |

---

## Bảng tổng

| ID | Vấn đề | Đi tới | Anchor (đúng chỗ khi thấy…) | Thao tác | Test |
|----|--------|--------|-----------------------------|----------|------|
| **PIPE-S01** | MES upload khi aggregate fail | G2950 / F `data_upload(self.thissn` trong STEP 6 | Trong `if yolo_step6 == "Pass":`, sau set `my_inference_result` · **Sai:** ngoài block Cambrian Pass | **Bọc** upload trong `if my_inference_result=="pass"` | S-02 không upload |
| **PIPE-S02** | UI Fail aggregate bị comment | G2934 / F `# if my_inference_result == "fail"` | Sau `my_inference_result = "fail"` · **Sai:** STEP 1 | **Bỏ comment** / viết lại fail branch | S-02 Fail UI |
| **PIPE-S03** | `step6=True` khi aggregate fail | G2963 / F `self.step6 = True` STEP 6 | Cuối nhánh Cambrian Pass · **Sai:** `elif yolo_step6 == "Fail"` | **Đổi** chỉ set True khi aggregate pass | S-02 step6 False |

**Ship:** PIPE-S02 → PIPE-S01 → PIPE-S03 (một diff gộp được)

---

## Context — bug hiện tại G2922–2963

```python
if yolo_step6 == "Pass":
    ...
    if self.checksn and self.modelcheck and self.sncheck:
        my_inference_result = "pass"
    elif self.checksn == False or ...:
        my_inference_result = "fail"
    # UI fail COMMENTED G2934-2941
    if my_inference_result == "pass":
        self.resultcolor("Pass")
        self.updatecount(...pass...)
    if self.sfis_choose==True:                    # ← BUG: không check aggregate
        self.mysfis.data_upload(self.thissn, self.data)
    ...
    self.step6 = True                             # ← BUG: True dù aggregate fail
```

---

## Diff patch (gộp PIPE-S01/S02/S03) G2922–2963

**Đúng chỗ:** `show_image_SKY`, `elif self.step5 == True and stepname == "STEP 6"` · **Sai:** go_run3 fail handler

```python
# TRƯỚC
                if yolo_step6 == "Pass":
                    self.UI_show(...)
                    ...
                    if self.checksn and self.modelcheck and self.sncheck:
                        self.lineEdit_9.setText(...)
                        my_inference_result = "pass"
                    elif self.checksn == False or self.modelcheck == False or self.sncheck == False:
                        my_inference_result = "fail"
                    # if my_inference_result == "fail": ... COMMENTED
                    if my_inference_result == "pass":
                        self.resultcolor("Pass")
                        self.updatecount(...pass...)
                    if self.sfis_choose==True:
                        self.mysfis.data_upload(self.thissn, self.data)
                    ...
                    self.step6 = True

# SAU
                if yolo_step6 == "Pass":
                    self.UI_show(...)
                    ...
                    aggregate_ok = self.checksn and self.modelcheck and self.sncheck
                    if aggregate_ok:
                        self.lineEdit_9.setText(str(self.thismodel) + ";" + str(self.getmodel))
                        my_inference_result = "pass"
                    else:
                        my_inference_result = "fail"
                        logging.error(
                            f"STEP6 aggregate fail checksn={self.checksn} "
                            f"modelcheck={self.modelcheck} sncheck={self.sncheck}"
                        )

                    if my_inference_result == "pass":
                        self.resultcolor("Pass")
                        self.updatecount(...pass...)  # giữ nguyên công thức
                        if self.sfis_choose:
                            self.mysfis.data_upload(self.thissn, self.data)
                        cv2.imwrite(... ALL PASS ...)
                        self.step6 = True
                    else:
                        self.resultcolor("Fail")
                        self.lineEdit_9.setText("Fail")
                        self.updatecount(str(int(self.lineEdit_4.text()) + 1),
                                         self.lineEdit_5.text(),
                                         str(int(self.lineEdit_6.text()) + 1),
                                         "%.2f%%" % ((int(self.lineEdit_5.text())) / (int(self.lineEdit_4.text()) + 1) * 100))
                        self.step6 = False
```

Rollback: khôi phục upload không guard — **ghi rõ rủi ro MES pass giả**.

---

## Verification

| Test ID | Fix ID | Setup | Action | Expected result |
|---------|--------|-------|--------|-----------------|
| T-S01 | PIPE-S01 | Ép `sncheck=False`, Cambrian STEP 6 Pass | Chạy STEP 6 | **Không** `data_upload`; không "sfis upload OK" |
| T-S02 | PIPE-S02 | Cùng setup T-S01 | Xem UI | Fail UI + count fail — không im lặng |
| T-S03 | PIPE-S03 | Cùng setup | Check flag | `step6=False`; go_run3 vào fail path BDFA0 |
| T-S04 | Regression | Golden DUT đủ 6 bước, mọi cờ true | Full cycle | Pass + upload như baseline |

Chi tiết matrix S-01…S-07 bên dưới.

## Test matrix

| # | Scenario | Kỳ vọng |
|---|----------|---------|
| S-01 | Mọi cờ true + Cambrian Pass | Pass + upload |
| S-02 | `sncheck=False`, Cambrian Pass | Fail UI; **không** upload; step6 False |
| S-03 | `modelcheck=False` | Tương tự S-02 |
| S-05 | Cambrian Fail | step6 False; go_run3 fail BDFA0 |
| S-07 | Golden 6 step full | Không regression |

## Rollback

| Fix ID | Rollback | Behavior cũ quay lại | Rủi ro nếu rollback |
|--------|----------|----------------------|---------------------|
| PIPE-S01/S02/S03 (1 diff gộp) | Git restore block STEP 6 G2922–2963 | Upload không gate; fail UI comment; step6 luôn True | **MES false pass quay lại** — chỉ rollback nếu gate chặn nhầm golden DUT, và phải báo MES |

## Implementation Window

| Fix ID | Suggested window | Reason |
|--------|------------------|--------|
| PIPE-S01/S02/S03 | Week 1–2 | P0 MES integrity; 1 diff gộp; cần verify golden DUT + audit MES record trên clone trước deploy |

## Smoke

- [ ] S-02 ép `sncheck=False` → không thấy "sfis upload OK" trên textbox
- [ ] S-01 golden DUT → upload vẫn chạy

## Per-Fix Detail

### PIPE-S01 — STEP 6 MES upload aggregate gate

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G2950 / `data_upload(self.thissn` trong STEP 6 |
| Lines | Trong `if yolo_step6 == "Pass":`, sau set `my_inference_result` |
| Legacy alias | S-02 (test matrix) |

#### Current Problem

`data_upload` gọi khi `yolo_step6=="Pass"` **không** check `checksn`/`modelcheck`/`sncheck` — MES pass khi aggregate fail.

#### Before Improvement

```python
                    if self.sfis_choose==True:                    # ← BUG
                        self.mysfis.data_upload(self.thissn, self.data)
```

#### Required Change

Bọc upload trong `if my_inference_result == "pass":` (sau aggregate check). Chỉ upload khi `aggregate_ok`.

#### After Improvement

Cambrian Pass + aggregate fail → **không** `data_upload`; không "sfis upload OK".

#### Improvement Value

| Area | Value |
|------|-------|
| MES/SFIS integrity | P0 — MES pass chỉ khi đủ checks |
| Debugging | Dễ audit STEP 6 pass vs flags |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-S01 | Ép `sncheck=False`, Cambrian STEP 6 Pass | Chạy STEP 6 | **Không** `data_upload` |
| S-02 | `sncheck=False`, Cambrian Pass | STEP 6 | Fail UI; không upload |

#### Rollback

Khôi phục upload không guard. **Rủi ro:** **MES false pass quay lại**.

#### Suggested Implementation Window

Week 1 (P0) — 1 diff gộp với S02/S03.

---

### PIPE-S02 — STEP 6 aggregate fail UI branch

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G2934 / `# if my_inference_result == "fail"` |
| Lines | Sau `my_inference_result = "fail"` trong STEP 6 |
| Legacy alias | — |

#### Current Problem

UI fail branch khi aggregate fail bị comment (G2934) — operator không thấy Fail khi checks fail.

#### Before Improvement

Fail UI commented; chỉ pass branch active khi `my_inference_result=="pass"`.

#### Required Change

Uncomment/viết lại `else` branch: `resultcolor("Fail")`, updatecount fail, log aggregate flags.

#### After Improvement

Aggregate fail → Fail UI + count; operator thấy Fail rõ.

#### Improvement Value

| Area | Value |
|------|-------|
| Operator experience | Không Pass UI mâu thuẫn với checks fail |
| MES/SFIS integrity | UI khớp MES decision |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-S02 | Cùng setup T-S01 | Xem UI | Fail UI + count fail |
| S-03 | `modelcheck=False` | STEP 6 | Tương tự S-02 |

#### Rollback

Comment lại fail branch. **Rủi ro:** im lặng khi aggregate fail.

#### Suggested Implementation Window

Week 1 (P0) — cùng diff PIPE-S01/S03.

---

### PIPE-S03 — `step6=True` only on aggregate pass

#### Code Location

| Field | Value |
|-------|-------|
| File | `sky.py` |
| Function / anchor | G2963 / `self.step6 = True` STEP 6 |
| Lines | Cuối nhánh Cambrian Pass |
| Legacy alias | — |

#### Current Problem

`self.step6 = True` set dù aggregate fail — go_run3 không vào fail path BDFA0.

#### Before Improvement

`step6=True` unconditional sau Cambrian Pass block.

#### Required Change

`step6=True` chỉ trong `if my_inference_result == "pass":`; else `step6=False`.

#### After Improvement

Aggregate fail → `step6=False`; go_run3 fail handler đúng.

#### Improvement Value

| Area | Value |
|------|-------|
| MES/SFIS integrity | Fail path BDFA0 khi checks fail |
| Production stability | State machine STEP 6 đúng |

#### Verification

| Test ID | Setup | Action | Expected result |
|---------|-------|--------|-----------------|
| T-S03 | Cùng setup T-S01 | Check flag | `step6=False`; go_run3 fail BDFA0 |
| S-07 | Golden 6 step full | Full cycle | Không regression |

#### Rollback

Khôi phục `step6=True` unconditional. **Rủi ro:** false pass state.

#### Suggested Implementation Window

Week 1 (P0) — verify golden DUT + audit MES trên clone.

---

## Ref

`14_sky_pipeline.md` · `02_sfis_mes_integrity/01_sfis_upload_helper.md` · `05_ai_ocr_runtime/03_cambrian_space_fail_policy.md`
