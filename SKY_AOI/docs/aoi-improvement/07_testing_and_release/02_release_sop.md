# SOP Release — Nội Bộ

**Luồng công việc:** `07_testing_and_release`  
**Đối tượng:** Engineering, QA, hỗ trợ line  
**Nguyên tắc:** Patch nhỏ, clone trước, chấp nhận đo được, sẵn sàng rollback

---

## Improvement Purpose

Mục tiêu của cải tiến này là chuẩn hóa quy trình release nội bộ — từ lập kế hoạch, clone test, backup, deploy production đến sign-off. Đảm bảo mỗi patch có cách triển khai và nghiệm thu rõ, giảm rủi ro deploy lên line.

## Before Improvement

Trước cải tiến, release thường copy `sky.py` trực tiếp lên production với test tay không đầy đủ; thiếu checklist T-7→T-0; backup không nhất quán; không phân loại hotfix vs monthly; MES không được notify khi đổi SN upload. Rollback khó vì không tag pre-release.

## After Improvement

Sau cải tiến, SOP release có checklist planning/build/clone/backup/deploy/monitor; loại release (hotfix/monthly/infra/config); liên kết playbook fix ID; smoke 19 P0 trên clone bắt buộc; backup `sky.py` + config + count baseline; sign-off QA/MES/operator. Deploy có gate; audit trail rõ.

## Improvement Value

| Area                        | Value |
| --------------------------- | ----- |
| Production stability        | Clone-first + smoke gate giảm bad deploy |
| Operator experience         | Notify trước deploy; monitor 1 ca post-release |
| MES/SFIS integrity          | MES notify khi đổi SN/error code; audit sample |
| Maintainability             | Release notes link fix ID; repeatable process |
| Debugging / troubleshooting | Pre/post backup giúp compare khi sự cố |

## Before / After Summary

| Aspect           | Before | After |
| ---------------- | ------ | ----- |
| Runtime behavior | N/A (process doc) | Verified on clone before prod |
| Error handling   | Deploy then hope | Smoke P0 fail = block |
| Operator impact  | Surprise behavior change | Briefed; monitored post-release |
| Production risk  | High uncontrolled deploy risk | Structured gate + rollback ready |

---

## Phạm vi

SOP này bao phủ triển khai cải tiến `sky.py` và thay đổi config/recipe trong `docs/aoi-improvement/`. **Không** thay quy trình change-control khách hàng nếu site có quy trình IT riêng — căn chỉnh cả hai.

---

## Loại release

| Loại | Phạm vi | Hồi quy |
|------|-------|------------|
| **Hotfix** | Một sửa P0 (logic 1–3 file) | Smoke P0 khu vực liên quan |
| **Hàng tháng** | Bundle phase (A–C điển hình) | Ma trận full |
| **Hạ tầng** | Chỉ cache OCR, preflight, guard | Smoke + dòng hiệu năng |
| **Chỉ config** | Model JSON / `is_sensor` / cờ Cambrian | Spot model + dòng sensor/Cambrian |

---

## Checklist trước release

### Lập kế hoạch (T-7 đến T-3 ngày)

- [ ] Phạm vi patch đã ghi — liên kết ID playbook (ví dụ A-03, B-01)
- [ ] **Một thay đổi logic mỗi PR** nếu có thể — rollback độc lập
- [ ] Đánh giá rủi ro: model/trạm nào bị ảnh hưởng
- [ ] Thông báo đội MES/SFIS nếu đổi upload SN hoặc mã lỗi
- [ ] Danh sách trạm đích (clone trước, rồi production)

### Nhánh & build (T-2 ngày)

- [ ] Nhánh từ tag known-good (ví dụ `sky_YYYYMMDD_pre_phaseA`)
- [ ] Code review xong — tập trung orchestration, SFIS, không diff lạ
- [ ] Import xác minh trên máy dev (`IoCard`, `ipex` nếu có)
- [ ] Nhãn version: comment header `sky.py` hoặc mục `RELEASE_NOTES.md` bên ngoài

### Chuẩn bị trạm clone (T-1 ngày)

- [ ] Clone mirror phần cứng production (camera, IO, endpoint SFIS/Cambrian)
- [ ] Backup trạng thái clone (xem mục Backup)
- [ ] Deploy `sky.py` candidate chỉ lên clone
- [ ] Chạy thủ công mục `03_startup_preflight_check` nếu chưa có trong code
- [ ] Chạy **ma trận smoke** (`01_regression_test_matrix.md` — tối thiểu 19 P0)
- [ ] Chạy **ma trận full** nếu release hàng tháng
- [ ] Ghi lỗi — sửa hoặc hoãn có ký chấp nhận rủi ro

### Backup production (T-0, trước deploy)

- [ ] Copy production `sky.py` → `backup/sky_YYYYMMDD_HHMM_pre_release.py`
- [ ] Copy `config.json`
- [ ] Copy model JSON đang dùng + `barcode_point` / `model_point` / count JSON
- [ ] Xuất Pass/Fail/Total hiện tại từ UI hoặc count JSON (baseline)
- [ ] Ghi version endpoint SFIS/Cambrian
- [ ] Xác nhận người phụ trách rollback on-call (`03_rollback_sop.md`)

---

## Thực thi release

### Thời điểm

- Deploy **ngoài giờ cao điểm production** (đổi ca, cửa sổ downtime có kế hoạch).
- Tránh deploy thứ Sáu nếu không có hỗ trợ cuối tuần trừ hotfix.

### Các bước deploy (tuần tự)

```text
1. Thông báo cửa sổ bảo trì cho operator (thông báo downtime ~5 phút)
2. Stop app AOI trên trạm đích — Stop graceful, xác minh camera được giải phóng
3. Thay sky.py (và module local nếu release có)
4. Giữ/khôi phục config.json — chỉ đổi nếu release kèm config
5. Xác minh point/sample/source còn nguyên; mkdir source/ nếu D-01 trong release
6. Launch app — theo dõi startup: danh sách camera, load model, version Cambrian, login SFIS
7. Smoke thủ công nhanh: một Start → cancel hoặc một chu kỳ test ngắn
8. Bàn giao operator giám sát production 1 ca
```

### Nhóm patch (thứ tự khuyến nghị)

Triển khai từng nhóm; smoke giữa các nhóm trên clone trước production:

| Nhóm | Nội dung | Ví dụ ID |
|-------|----------|-------------|
| G1 Safety | Treo, SN, guard SFIS | B-01, A-03, A-04, B-02 |
| G2 Guards | Sensor, Cambrian, preflight | sensor guard, cambrian guard, preflight |
| G3 Pipeline | Sửa theo model | SKY STEP6, Cisco OCR, Button_check |
| G4 Performance | Cache OCR, ngắt sleep | E-01, E-03 |

**Không gộp nhóm không liên quan vào một deploy production mà không chạy hồi quy kết hợp.**

### Unit / mock test (khi có)

- [ ] Nếu đã thêm `tests/` (Q4): chạy tập con tự động trước ma trận
- [ ] Mock SFIS: upload throw, route fail
- [ ] Hôm nay chưa có test tự động: ma trận là cổng chấp nhận

---

## Checklist sau release

### Ngay (0–2 giờ)

- [ ] App start; không ImportError / exit Cambrian
- [ ] Start/Stop phản hồi thử operator đầu
- [ ] Không MessageBox chặn bất ngờ (sensor/Cambrian/preflight)
- [ ] 5 DUT đầu: Pass/Fail trực quan hợp lý; SN `lineEdit_8` khớp nhãn
- [ ] File log tạo dưới `log/{date}/`

### Giám sát một ca (1 ca)

- [ ] Không Stop+Restart ngoài kế hoạch vì treo (mục tiêu)
- [ ] Operator ghi bất thường trên phiếu chạy
- [ ] So sánh tỷ lệ Pass/Fail baseline — báo nếu lệch > % đã thỏa

### Audit MES (trong 24–48 giờ)

- [ ] Mẫu **10 pass + 10 fail** từ SFIS
- [ ] SN khớp đơn vị vật lý / log quét
- [ ] Không bản ghi SN `"None"` (WP/Nanook/Button_check)
- [ ] Mã lỗi `BDFA0` / `BDFA01` đúng theo model

### Ký duyệt (trong 72 giờ)

| Vai trò | Ký |
|------|----------|
| Engineering | Kèm kết quả smoke/full matrix |
| QA | Audit MES pass |
| Operator lead | 1 ca ổn định |
| MES (nếu đổi logic SN) | Mẫu đã duyệt |

- [ ] Cập nhật log release nội bộ: version, ngày, trạm, ID patch
- [ ] Lưu đường backup và phiếu chạy test

---

## Mẫu log release

```text
Release ID: REL-YYYYMMDD-NN
sky.py: backup/sky_YYYYMMDD_pre.py → deployed hash/tag
Stations: LINE1-clone OK; LINE1-prod OK
Patches: A-03, B-01, B-04, ...
Matrix: Smoke 19/19 PASS (clone); Full 42/45 PASS (3 P2 deferred)
MES audit: 10+10 PASS
Xác nhận người vận hành: Name / date
Rollback plan: backup/sky_YYYYMMDD_pre.py
```

---

## Verification / Rollback / Timeline (compliance note)

- **Verification:** Cổng chấp nhận = smoke 19 P0 (`01_regression_test_matrix.md`) trên clone + audit MES 10+10 + giám sát 1 ca — đã nêu trong checklist sau release.
- **Rollback:** Backup T-0 bắt buộc trước mỗi deploy; quy trình revert tại `03_rollback_sop.md`; tiêu chí dừng release ở section dưới.
- **Implementation Window:** Áp dụng SOP này từ release đầu tiên (Week 1–2, nhóm G1 Safety); timeline T-7→T-0 lặp lại mỗi release.

---

## Khi dừng release

Dừng deploy và gọi rollback nếu:

- Bất kỳ dòng P0 ma trận fail trên clone sau khi thử sửa
- Crash startup trên clone
- Audit MES thấy SN sai trên mẫu production đầu
- Operator báo treo trong giờ đầu

Xem `03_rollback_sop.md`.

---

## Tham chiếu

`01_regression_test_matrix.md`, `03_rollback_sop.md`, `11_refactor_plan.md` §10, `01_priority_roadmap.md`
