# SOP Rollback — Nội Bộ

**Luồng công việc:** `07_testing_and_release`  
**Nguyên tắc:** Mỗi patch cải tiến phải **nhỏ và revert độc lập**. Chỉ rollback patch lỗi — không hoàn tác cả quý trừ khi bắt buộc.

---

## Improvement Purpose

Mục tiêu của cải tiến này là chuẩn hóa quy trình rollback khi regression P0 trên production — trigger rõ, backup requirement, restore steps, smoke verify sau revert. Mỗi fix phải revert độc lập.

## Before Improvement

Trước cải tiến, khi sự cố xảy ra engineer có thể mất thời gian tìm bản `sky.py` cũ, rollback cả bundle thay vì patch lỗi, hoặc trì hoãn revert để "thử thêm DUT" — làm trầm trọng MES sai SN hoặc line treo. Không có decision tree formal.

## After Improvement

Sau cải tiến, SOP rollback có trigger table (treo/crash/MES sai/guard chặn sai), decision flow, backup naming convention, restore commands, smoke 3–5 P0 sau revert, incident record template. Rollback nhanh, đúng patch, production tiếp tục an toàn.

## Improvement Value

| Area                        | Value |
| --------------------------- | ----- |
| Production stability        | Rollback nhanh giảm downtime khi regression |
| Operator experience         | Line resume sau revert + smoke — ít chờ ad-hoc fix |
| MES/SFIS integrity          | Rollback SN/upload patch ngay khi audit fail |
| Maintainability             | Independent revert per PR/fix ID |
| Debugging / troubleshooting | Incident record + pre-backup compare |

## Before / After Summary

| Aspect           | Before | After |
| ---------------- | ------ | ----- |
| Runtime behavior | Ad-hoc revert or full revert | Targeted patch rollback |
| Error handling   | Delay rollback during incident | Immediate rollback triggers defined |
| Operator impact  | Long downtime uncertain fix | Fast restore known-good |
| Production risk  | Extended exposure to bad patch | Minimize exposure window |

---

## Per-Fix Rollback Groups

Mỗi nhóm rollback map Fix ID → file/block revert → rủi ro mở lại.

## Fix RB-G1 — Runtime stall / orchestration

### Code Location

| Field | Detail |
|---|---|
| File | sky.py |
| Function / Block | `go_run3`, `cambrian_space`, Button_check Flip |
| Fix IDs | RT-001, RT-002A, RT-003, AI-001, SFIS-001 (stall aspect) |
| Revert blocks | `else` cuối go_run3; `elif step1==False` HH4K; `wait_test=True` Flip; `return "Fail"` cambrian_space; try/except SFIS fail sites |

### Rollback

Revert từng block theo Fix ID trong PR. Sau rollback: unknown model stall; Flip reject stall; Cambrian except → None; SFIS throw skip wait_test.

### Suggested Implementation Window

| Window | Reason |
|---|---|
| Week 1 deploy / any time revert | P0 group — revert ngay nếu line treo |

---

## Fix RB-G2 — MES / SN integrity

### Code Location

| Field | Detail |
|---|---|
| File | sky.py |
| Function / Block | `go_run3` upload vars, SN reset, `go_run1` scan |
| Fix IDs | SN-001–005, SFIS-001, SFIS-002/003, EC-002/003, PIPE-B01, PIPE-W01, PIPE-C01 |
| Revert blocks | L1308 `scaninfo`; SN reset lines; `"None"` → literal; empty scan validate; helper upload |

### Rollback

**Không khuyến nghị revert SN-001, PIPE-B01** — MES wrong SN quay lại. Nếu bắt buộc: revert PR SN/upload; audit MES 10 fail records.

### Suggested Implementation Window

| Window | Reason |
|---|---|
| Week 1–2 deploy | Revert ngay nếu audit MES SN sai |

---

## Fix RB-G3 — Sensor / Cambrian guards

### Code Location

| Field | Detail |
|---|---|
| File | sky.py |
| Function / Block | `startprogram`, `validate_sensor_mode`, `validate_cambrian_policy` |
| Fix IDs | SENSOR-001/002, AI-G01/G02, DEP-P02 |
| Revert blocks | Guard blocks đầu `startprogram`; validate methods |

### Rollback

Xóa guard → non-MR6500 + sensor chạy MR6500 pipeline lại; Cambrian off + SKY crash lại. Chỉ revert nếu guard chặn sai config hợp lệ.

### Suggested Implementation Window

| Window | Reason |
|---|---|
| Week 1 deploy | Revert nếu guard block mọi Start sai |

---

## Fix RB-G4 — Pipeline-specific

### Code Location

| Field | Detail |
|---|---|
| File | sky.py |
| Function / Block | `show_image_*`, pipeline orchestration |
| Fix IDs | PIPE-M01–M03, PIPE-S01–S03, PIPE-H01, PIPE-C01–C04, PIPE-W01–W03, PIPE-N01–N02, PIPE-B01–B06 |
| Revert blocks | Per playbook diff section |

### Rollback

Revert per-model PR. Rủi ro: SKY false pass STEP 6; Cisco OCR crash; WP route fail pass giả; MR6500 SFIS off crash.

### Suggested Implementation Window

| Window | Reason |
|---|---|
| Month 1 deploy | Spot revert by model PR |

---

## Fix RB-G5 — UI / OCR performance (Month 2)

### Code Location

| Field | Detail |
|---|---|
| File | sky.py |
| Function / Block | `go_run2` sleep, PaddleOCR init, `startprogram` finally |
| Fix IDs | E-01, E-03, E-06, E-07, E-08, AI-O01–O05 |
| Revert blocks | Sliced sleep; OCR singleton; finally enable Start |

### Rollback

E-01 và E-03 độc lập. Revert OCR cache → UI freeze trở lại. Revert sleep → Stop chậm 5s.

### Suggested Implementation Window

| Window | Reason |
|---|---|
| Month 2+ | Perf patches — revert nếu regression OCR accuracy |

---

## Khi nào rollback

| Kích hoạt | Hành động |
|---------|--------|
| Hồi quy P0 trên production (treo, crash, SN MES sai) | Rollback **ngay** nhóm patch mới nhất |
| Audit MES fail (SN sai, `"None"`, pass giả) | Rollback patch SN/upload; giữ line |
| Một model fail hồi quy; model khác OK | Rollback patch model đó hoặc revert nhánh riêng model |
| Operator không chạy được 1 ca không Stop vì treo | Rollback patch orchestration |
| Guard Cambrian/SFIS chặn mọi Start sai | Rollback guard; sửa config trên clone trước |
| Patch hiệu năng gây hồi quy OCR/thread | Chỉ rollback E-03 / thay đổi Runthread |

**Không trì hoãn rollback** để "thử thêm một DUT" khi toàn vẹn MES hoặc an toàn có rủi ro.

---

## Luồng quyết định rollback

```text
Phát hiện sự cố
  → Xác định triệu chứng (treo / crash / MES / sai model)
  → Ánh xạ nhóm patch (G1–G4) hoặc một PR
  → Dừng line hoặc trạm
  → Khôi phục sky.py từ backup
  → Tùy chọn: khôi phục config nếu release đổi JSON
  → Xác minh tập con smoke (3–5 dòng P0)
  → Tiếp tục production HOẶC leo thang
  → Lưu hồ sơ sự cố
```

---

## Yêu cầu backup (trước mỗi release)

### `sky.py`

```text
backup/
  sky_YYYYMMDD_HHMM_pre_REL-NNN.py    # bản copy đầy đủ trước deploy
  sky_YYYYMMDD_HHMM_post_REL-NNN.py  # tùy chọn sau ký duyệt thành công
```

**Lệnh (ví dụ):**

```powershell
$ts = Get-Date -Format "yyyyMMdd_HHmm"
Copy-Item "sky.py" "backup\sky_${ts}_pre_release.py"
```

Tag trong git nếu dùng version control:

```bash
git tag sky-pre-REL-YYYYMMDD-NN
```

### Config / recipe / bộ đếm

| File | Đường backup |
|------|-------------|
| `config.json` | `backup/config_YYYYMMDD.json` |
| Model JSON (`choose_model`) | `backup/model_YYYYMMDD.json` |
| `barcode_point` / `model_point` | `backup/points_YYYYMMDD/` |
| Count JSON | `backup/count_YYYYMMDD.json` |

**Quan trọng:** Rollback count JSON có thể **mất** Pass/Fail tích lũy trong release lỗi — ghi delta để đối soát MES.

---

## Cách rollback từng loại patch

### Hoàn tác `sky.py` một file (phổ biến nhất)

1. Stop ứng dụng (nút Stop → chờ → đóng nếu cần).
2. Copy `backup/sky_*_pre_release.py` đè lên `sky.py`.
3. Nếu release chỉ đụng `sky.py` — **không** khôi phục config trừ khi config đã đổi.
4. Restart app; chạy smoke:
   - Start/Stop
   - Một chu kỳ model bị ảnh hưởng
   - Một test offline SFIS nếu revert patch SFIS
5. Mở lại line khi smoke pass.

### Hoàn tác một phần (git)

Nếu patch là commit riêng trên một nhánh:

```bash
git revert <commit-hash>   # một patch
# KHÔNG git reset --hard trên nhánh dùng chung nếu chưa được duyệt
```

Revert **commit lỗi mới nhất trước**. Chạy lại smoke giữa các lần revert.

### Hoàn tác chỉ config

Nếu release đổi `is_sensor`, Cambrian, hoặc đường model:

1. Khôi phục `config.json` và model JSON từ backup.
2. Giữ `sky.py` đã rollback nếu code không phải nguyên nhân.
3. Restart; xác minh sensor guard và cờ Cambrian khớp ý định trạm.

### Không rollback từng phần được

Nếu patch bị squash thành một diff khối:

- Khôi phục toàn bộ `sky.py` pre-release
- Áp lại patch từng cái một trên clone trước lần thử tiếp

**Phòng ngừa:** Theo nhóm patch `02_release_sop.md` — tránh deploy khối.

---

## Xác minh sau rollback

| Bước | Kiểm tra |
|------|-------|
| 1 | App launch; camera phát hiện |
| 2 | Model load; UI hiện `select_model` kỳ vọng |
| 3 | SFIS/Cambrian theo config — login hoặc tắt sạch |
| 4 | Sensor MR6500: một chu kỳ trigger nếu trạm sensor |
| 5 | Model manual: một chu kỳ Pass hoặc Fail |
| 6 | `wait_test` reset — không treo khi fail chủ ý |
| 7 | MES: upload test tùy chọn trên endpoint clone |
| 8 | Operator xác nhận UI quen (không kẹt guard) |

Smoke tối thiểu sau rollback: **Unknown model N/A** — dùng 5 dòng ma trận khớp họ model trạm.

---

## Mẫu hồ sơ sự cố

Lưu tại `backup/incidents/INC-YYYYMMDD-NN.md`:

```markdown
# Incident INC-YYYYMMDD-NN

## Tóm tắt
Mô tả một dòng (ví dụ Button_check MES wrong SN after REL-20260712-01)

## Phát hiện
- Ai / khi nào / trạm nào
- Triệu chứng

## Ngữ cảnh release
- ID release:
- Patch đã triển khai:
- Bản backup `sky.py` dùng để hoàn tác:

## Nguyên nhân gốc (ban đầu)
- Mục playbook:
- Bằng chứng (đoạn log, ID bản ghi MES)

## Hành động hoàn tác
- Thời điểm bắt đầu / hoàn tất hoàn tác
- File đã khôi phục: sky.py [Y], config [Y/N], count [Y/N]
- Kết quả smoke sau hoàn tác:

## Tác động sản xuất
- Số DUT bị ảnh hưởng (ước tính):
- Bản ghi MES cần sửa:

## Theo dõi sau sự cố
- Kế hoạch sửa tiến (fix forward):
- Kiểm thử lại trên clone trước khi release lại:
- Người phụ trách / hạn xử lý:
```

---

## Truyền thông

| Đối tượng | Thông điệp |
|----------|---------|
| Operators | "Đã rollback về bản trước; vận hành như trước NGÀY; báo nếu lặp lại" |
| MES | Liệt kê SN/cửa sổ thời gian cần sửa thủ công nếu có upload lỗi |
| Engineering | ID sự cố + ticket nguyên nhân gốc |

---

## Quy tắc patch độc lập (bắt buộc)

| Quy tắc | Lý do |
|------|-----------|
| Một mục playbook ≈ một PR ≈ một revert | Cô lập lỗi |
| Không bundle G1+G3 lần đẩy production đầu | Khó chẩn đoán |
| Giữ `sky.py` pre-release cho **mỗi** deploy | Luôn có bản known-good |
| Ghi ID patch trong log release | Ánh xạ sự cố → revert |
| Clone chứng minh patch trước prod | Tỷ lệ rollback giảm |

Nếu patch không revert độc lập được, **tách trước khi release**.

---

## Verification / Timeline (compliance note)

- **Verification:** Sau mỗi rollback chạy smoke 3–5 dòng P0 khớp họ model trạm (bảng "Xác minh sau rollback" trên) + hồ sơ sự cố INC.
- **Implementation Window:** SOP này phải sẵn sàng **trước** release đầu tiên (Week 1) — backup convention + quy tắc patch độc lập là điều kiện tiên quyết cho mọi deploy.

---

## Release lại sau rollback

1. Sửa nguyên nhân gốc trên clone.
2. Smoke đầy đủ (hoặc ma trận full nếu đụng MES) pass.
3. Backup mới trước deploy lần hai.
4. Không bỏ audit MES ở lần thử thứ hai.

---

## Tham chiếu

`02_release_sop.md`, `01_regression_test_matrix.md`, `01_priority_roadmap.md`, `11_refactor_plan.md` §10 acceptance
