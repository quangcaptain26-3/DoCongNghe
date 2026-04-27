# EIM — BỘ Q&A USE CASES ĐẦY ĐỦ
> Từ cơ bản → nâng cao → quái dị. Tổng hợp từ spec + các usecase đã triển khai + tự nghĩ thêm.
> Dùng để ôn tập, hội đồng hỏi gì cũng có đáp án.

---

# CẤP 1 — CƠ BẢN (hội đồng hỏi khởi động)

**Q1: Học viên mới đến đăng ký học thì luồng xử lý thế nào từ đầu đến cuối?**
> 1. Học vụ tạo hồ sơ học sinh (students) với thông tin cá nhân + phụ huynh
> 2. Học sinh làm test đầu vào → ghi kết quả vào `test_result`
> 3. Học vụ tạo enrollment với `status = 'trial'` vào lớp phù hợp → học thử tối đa 2 buổi
> 4. GV/Học vụ điểm danh 2 buổi thử → `trial_sessions` tăng
> 5. Phụ huynh quyết định:
>    - Đồng ý → Kế toán tạo phiếu thu → Học vụ activate enrollment (`status = 'active'`)
>    - Không đồng ý → Drop với lý do "Không đăng ký sau trial"
> 6. Học sinh học 24 buổi → điểm danh từng buổi → complete

**Q2: Học viên đóng học phí rồi, xử lý trong hệ thống thế nào?**
> Kế toán tạo phiếu thu (POST /receipts): ghi `payer_name`, `amount`, `payment_method`, `enrollment_id`. Sau khi tạo receipt, hệ thống tự check `SUM(receipts.amount) >= tuition_fee` — nếu đủ thì tự động `activate enrollment`. `amount_in_words` do BE tính (không nhận từ FE). Phiếu thu đã tạo không được xóa — sai thì tạo phiếu âm bù trừ.

**Q3: Giáo viên điểm danh thế nào?**
> GV vào trang "Lịch dạy của tôi" → thấy session hôm nay → click "Điểm danh". Trang hiện danh sách học sinh trong lớp, GV chọn 1 trong 4 trạng thái: P (có mặt), L (muộn), A (vắng có phép), U (vắng không phép). Sau khi điểm danh đủ tất cả học sinh và submit → session `status = 'completed'`. Toàn bộ ghi vào `audit_logs` với snapshot đầy đủ.

**Q4: Học vụ tạo lớp học mới thế nào?**
> Chọn Program → Room → Shift (Ca 1/Ca 2) → Schedule days (2 ngày tự do, gap ≥ 2) → GV. Hệ thống validate conflict: GV + Phòng không trùng shift+schedule_days với lớp active khác. Sau tạo lớp: dialog "Generate sessions ngay?" — chọn có thì sinh 24 buổi tự động, bỏ qua ngày lễ. Lớp chuyển `pending → active` sau khi generate xong.

**Q5: Công nợ học viên xem ở đâu, tính thế nào?**
> Công nợ = `enrollment.tuition_fee - SUM(receipts.amount WHERE enrollment_id = X)`. Không lưu sẵn trong DB, tính realtime qua function `enrollment_debt()`. Hiển thị ở: tab Tài chính trong student detail, trang Công nợ, KPI Dashboard. Kết quả âm = học viên đang dư tiền (nộp thừa).

---

# CẤP 2 — TRUNG BÌNH (hội đồng bắt đầu siết)

**Q6: Học viên muốn bảo lưu — xử lý thế nào? Có khác nhau giữa buổi 2 và buổi 5 không?**
> Có 2 giai đoạn hoàn toàn khác nhau:
>
> **Giai đoạn tự do (sessionsAttended < 3):** Bảo lưu ngay, không cần Admin duyệt. Học vụ bấm "Bảo lưu" → `enrollment.status = 'paused'` tức thì. Học phí bảo lưu 100%.
>
> **Giai đoạn kiểm soát (sessionsAttended ≥ 3):** Tạo `pause_request` → Admin xem xét → duyệt mới được bảo lưu. Admin có thể từ chối kèm lý do.
>
> **Quan trọng:** Chỉ được bảo lưu **1 lần duy nhất** trong toàn bộ 1 enrollment — field `pause_count` track, CHECK constraint enforce ở DB level.

**Q7: Sau khi bảo lưu, học viên quay lại học thế nào? Tiếp tục từ đâu?**
> Học vụ/Admin bấm "Tiếp tục học" (POST /enrollments/:id/resume). Enrollment `status → 'active'`. Hệ thống tìm session pending đầu tiên của lớp → đó là buổi học tiếp theo. Sessions đã completed trước khi bảo lưu giữ nguyên. Nếu muốn đổi lớp khi resume: truyền `targetClassId` trong request body, validate lớp mới cùng program + còn chỗ.

**Q8: GV bận, không dạy được — xử lý thế nào?**
> Học vụ/Admin vào session cần cover → "Gán Cover". Hệ thống hiện danh sách GV khả dụng: không trùng shift+date ở bất kỳ session/cover/makeup nào. GV unavailable hiện disabled + tooltip lý do (VD: "Đang dạy EIM-LS-02 Ca 1"). Chọn GV cover + nhập lý do → ghi vào `session_covers`. Khi tính lương: buổi đó tính cho GV cover, không tính cho GV chính (`effective_teacher_id()` function).

**Q9: Học viên muốn chuyển lớp — điều kiện là gì?**
> 2 điều kiện độc lập phải đều thỏa:
> - `sessionsAttended < 3` (chỉ trong 3 buổi đầu)
> - `classTransferCount < 1` (chỉ được chuyển 1 lần/enrollment)
> Vi phạm bất kỳ điều kiện nào → block, kể cả Admin. Lớp mới phải cùng program + còn chỗ + status pending/active. Ghi `enrollment_history` action `class_changed` + tăng `classTransferCount`.

**Q10: Tính lương giáo viên tháng này thế nào?**
> Kế toán/Admin vào Chốt lương → chọn GV + tháng/năm → Preview. Hệ thống đếm sessions completed trong tháng theo `effective_teacher_id()`: buổi chính (wasCover=false) + buổi đi cover (wasCover=true). Lương = `sessionsCount × salary_per_session + allowance` — snapshot tại thời điểm chốt, không bị ảnh hưởng nếu lương thay đổi sau. Không chốt 2 lần cùng tháng/GV (UNIQUE constraint).

**Q11: Phòng học 2 tầng có ảnh hưởng gì đến logic hệ thống không?**
> Thêm field `floor` (1/2), `room_type` (normal/large), `amenities` (JSONB) vào bảng rooms. Khi tạo lớp, room selector group theo tầng + hiện availability check realtime (gọi `/rooms/availability?shift=1&scheduleDays=[2,4]`). Conflict check vẫn dùng `room_id` — không thay đổi. Tầng chỉ là thông tin visual, không ảnh hưởng business logic.

**Q12: Học sinh đăng ký lớp sắp khai giảng thì flow thế nào?**
> Admin/Học vụ tạo lớp `status='pending'` với `expected_start_date`, `min_students`, rồi "Công bố" (`announced_at = now()`). Phụ huynh thấy lớp trên trang `/upcoming`. Đăng ký trước: tạo enrollment `status='pending'` hoặc `reserved` (đóng phí giữ chỗ). Khi đủ `min_students` và đến ngày: Admin/Học vụ bấm "Khai giảng" → generate 24 sessions → class `status='active'` → enrollments đã đóng tiền tự `activate`.

---

# CẤP 3 — NÂNG CAO (hội đồng muốn thấy hiểu sâu)

**Q13: Học viên học 12 buổi (nửa khóa) rồi muốn nghỉ — xử lý học phí thế nào?**
> Phụ thuộc lý do:
> - **Lý do chủ quan** (bản thân/gia đình): KHÔNG hoàn học phí. Học vụ chọn `reason_type` từ danh sách (subjective_no_interest, subjective_financial...) → drop enrollment → ghi `enrollment_history`. Không tạo refund.
> - **Lý do khách quan** (trung tâm lỗi): tạo `refund_request` với `reason_type = 'center_unable_to_open'` → hoàn 100%.
> - **Nâng chương trình**: tính credit phần còn lại chuyển sang khóa mới (xem Q17).

**Q14: Tại sao phân biệt `sessions_attended` và `sessions_absent` — 2 con số này không thể suy ra từ nhau?**
> Đúng, 2 con số độc lập vì: học viên có thể vào giữa khóa (enrollment tạo sau khi lớp đã bắt đầu) → số sessions tổng của enrollment ≠ 24. Hơn nữa, session bị cancel không tính vào cả 2 con số. Trigger `trg_sync_attendance` cập nhật cả 2 sau mỗi INSERT/UPDATE/DELETE attendance. `total_absent = absent_excused + absent_unexcused` ở field riêng để check makeup_blocked nhanh hơn.

**Q15: Nếu học viên vắng 2 buổi có phép, được xếp học bù 2 buổi — nhưng vắng thêm 2 buổi không phép thì sao?**
> - `total_absent = 4 > 3` → `makeup_blocked = true` (trigger tự set)
> - 2 makeup sessions đã tạo trước đó: vẫn tồn tại, có thể hoàn thành
> - Các buổi vắng tiếp theo: không thể tạo makeup mới dù là `absent_excused`
> - UI hiện badge "🔒 Học bù bị khóa — Tổng vắng 4 buổi (giới hạn 3)"
> - Để mở lại: chỉ Admin mới có thể reset `makeup_blocked = false` (special case, ghi audit)

**Q16: Học sinh bận thứ 4, lớp lại học T2+T4 — hệ thống xử lý thế nào?**
> Hệ thống **không thể** tạo lịch riêng cho từng học sinh. 3 hướng xử lý:
> 1. **Chuyển lớp** (ưu tiên, trước buổi 3): `/classes/suggestions?programId=X&unavailableDays=[4]` → trả lớp không có T4
> 2. **Chấp nhận vắng**: điểm danh `absent_excused` buổi T4, học bù tối đa 3 buổi. Nếu bận T4 cố định = 12 buổi vắng → makeup_blocked sau buổi 3 vắng đầu tiên
> 3. **Bảo lưu**: chờ trung tâm mở lớp lịch phù hợp
> FE phòng tránh: khi ghi danh hiển thị lịch rõ, yêu cầu phụ huynh confirm, gọi `/schedule/conflict-check` nếu phụ huynh đã nhập ngày bận.

**Q17: Học sinh đang học Starters giữa chừng (16 buổi) muốn lên Movers — học phí tính thế nào?**
> Chỉ Admin thực hiện. Logic:
> - `tuitionUsed = 2.800.000 × 16/24 = 1.866.667đ` (làm tròn)
> - `creditAmount = 2.800.000 - 1.866.667 = 933.333đ` (phần chưa dùng)
> - `newTuitionFee = 3.000.000đ` (Movers)
> - `additionalFee = 3.000.000 - 933.333 = 2.066.667đ` (cần đóng thêm)
> Tạo phiếu âm `-933.333đ` cho enrollment Starters. Tạo enrollment Movers + phiếu dương `+2.066.667đ`. Ghi `enrollment_history` action `program_upgraded`. Cập nhật `students.current_level = 'MOVERS'`.

**Q18: Lương nhân viên hành chính nghỉ không phép tính thế nào?**
> Nhân viên hành chính (Academic, Accountant) có `monthly_salary` — không tính theo buổi như GV.
> - Mỗi tháng: 2 ngày phép (annual_leave/sick_leave không trừ lương)
> - Vượt 2 ngày: mỗi ngày thêm trừ `monthly_salary / 26`
> - Nghỉ không phép (`unpaid_leave`): trừ từ ngày đầu tiên, không được dùng phép
> View `v_leave_balance` tính realtime. Cuối tháng: `GET /payroll/staff-preview` trả `totalDeduction` để kế toán chốt.

---

# CẤP 4 — KHÓ (hội đồng muốn thấy tư duy hệ thống)

**Q19: 60 ngày trung tâm không khai giảng được lớp — xử lý thế nào với tiền phụ huynh đã đóng?**
> Cơ chế tự động: function `fn_check_class_open_deadline()` tìm lớp pending > 60 ngày. Dashboard admin hiện cảnh báo "⚠ X lớp quá hạn". Admin xử lý:
> 1. Tạo `refund_request` với `reason_type = 'center_unable_within_60days'` cho từng enrollment có phiếu thu
> 2. `refund_amount = tuition_fee` (hoàn 100%)
> 3. Kế toán tạo phiếu âm cho từng phụ huynh
> 4. Enrollment → `status = 'dropped'`, history `action = 'refunded_full'`
> Phí giữ chỗ (reservation_fee): **cũng hoàn** trong trường hợp này (trung tâm lỗi).

**Q20: Chuyển nhượng học phí từ học sinh A sang học sinh B — atomic thế nào?**
> Toàn bộ trong 1 DB transaction, rollback nếu bất kỳ bước nào fail:
> 1. Check enrollment A còn `active`, enrollment B chưa tồn tại
> 2. `sessionsRemaining = 24 - A.sessionsAttended`
> 3. `amountTransferred = A.tuitionFee × sessionsRemaining / 24`
> 4. INSERT receipt âm cho A (hoàn credit)
> 5. INSERT enrollment mới cho B với `tuitionFee = amountTransferred`, `status = 'active'`
> 6. INSERT receipt dương cho B (đóng tiền nhận chuyển nhượng)
> 7. UPDATE A.status = 'transferred'
> 8. INSERT transfer_requests để track `transfer_group_id`
> Nếu lớp B vừa đầy (step 5) → rollback, không tạo phiếu nào.

**Q21: GV đang dạy lớp A (T2+T4, Ca 1) được assign cover lớp B (T2+T5, Ca 1) — có conflict không?**
> Check: GV có session nào có `shift = 1` VÀ `schedule_days && {2}` (T2 overlap) không?
> - Lớp A: T2+T4, Ca 1 → T2 Ca 1 bị chiếm
> - Lớp B cover cần T2+T5, Ca 1 → T2 Ca 1 cũng bị chiếm
> → **Conflict!** Block gán cover. `ConflictCheckerService.checkTeacherConflictByDate()` check cả `sessions`, `session_covers`, và `makeup_sessions` — không bỏ sót case nào.

**Q22: Khi chốt lương, salary_per_session được lấy ở thời điểm nào?**
> **Tại thời điểm chốt**, không phải preview. `finalize-payroll.usecase` query `users.salary_per_session` ngay khi chạy và snapshot vào `payroll_records.salary_per_session_snapshot`. Dù Admin thay đổi lương GV sau đó, bảng lương cũ vẫn giữ nguyên. Preview (`GET /payroll/preview`) dùng giá trị hiện tại để ước tính — có note "Lương/buổi hiện tại: X, sẽ snapshot khi chốt".

**Q23: Học viên đã hoàn thành Starters, muốn học Flyers bỏ qua Movers — hệ thống có cho không?**
> Hệ thống **cho phép**. Không có constraint bắt phải học theo thứ tự level_order. Học vụ chọn Program = FLYERS khi tạo enrollment mới. `students.current_level` được cập nhật theo enrollment mới. Thực tế: một số học sinh có thể đã học ở trường, trình độ cao hơn → test đầu vào quyết định level phù hợp, không phải lộ trình cứng.

---

# CẤP 5 — QUÁI DỊ (hội đồng sáng tạo)

**Q24: Phụ huynh đóng học phí nhầm cho 2 enrollment cùng lúc (thực ra chỉ muốn đóng 1)**
> 2 phiếu thu tồn tại, 1 enrollment bị "dư" tiền (`debt < 0`). Hệ thống hiển thị "Dư: X₫" thay vì "Còn nợ". Kế toán tạo phiếu âm hoàn lại khoản dư cho enrollment không muốn đóng, với `voided_by_receipt_id` trỏ về phiếu gốc. Không xóa phiếu nào — audit trail đầy đủ.

**Q25: GV dạy buổi 8, xong điểm danh xong. Học vụ nhớ ra là GV này lẽ ra bị cover bởi GV khác — xử lý thế nào?**
> Session đã `completed`, attendance đã ghi. Về mặt nghiệp vụ:
> - Attendance đã điểm danh: Admin sửa được (ghi audit với old/new values)
> - `session_covers`: cancel cover cũ (nếu có), hoặc thêm cover mới cho historical record
> - **Lương bị ảnh hưởng**: nếu đã chốt lương tháng này → không sửa, điều chỉnh tháng sau. Nếu chưa chốt → `effective_teacher_id()` sẽ trả đúng GV khi preview/finalize.
> - Ghi `enrollment_history` nếu cần.

**Q26: Học sinh A đang học, muốn chuyển nhượng phần còn lại cho... chính mình (enroll lại lớp khác cùng chương trình)?**
> Không thể chuyển nhượng cho chính mình — `transfer_requests` validate `from_student_id ≠ to_student_id`. Nếu muốn đổi lớp: dùng `transfer-class` nếu còn trong 3 buổi đầu. Nếu qua buổi 3: bảo lưu → resume ở lớp khác. Đây là 2 nghiệp vụ khác nhau, không thể lẫn lộn.

**Q27: Phụ huynh đã đóng học phí tháng 1, đến tháng 3 trung tâm tăng học phí lên — học viên đang học có bị truy thu không?**
> **Không**. `enrollment.tuition_fee` là IMMUTABLE — giá trị tại thời điểm ghi danh, không bao giờ thay đổi. `programs.default_fee` tăng chỉ ảnh hưởng enrollment MỚI tạo sau thời điểm đó. DB trigger `trg_guard_tuition_fee` block mọi attempt UPDATE nếu `paid_at IS NOT NULL`.

**Q28: Admin xóa GV đang có lịch dạy trong tháng này — hệ thống làm gì?**
> Soft delete (`deleted_at = now()`) — GV không login được nhưng tất cả data còn nguyên. Sessions của tháng này vẫn thuộc GV đó (`sessions.teacher_id` giữ nguyên). GV vẫn được tính lương cho buổi đã dạy. Tuy nhiên các sessions **chưa dạy** (pending) giờ có GV bị xóa → hệ thống hiện cảnh báo "GV {tên} đã bị xóa, cần phân công lại". Học vụ cần: thay GV cho các sessions pending còn lại.

**Q29: Kế toán chốt lương nhầm tháng (chốt tháng 3 thay vì tháng 4) — xử lý thế nào?**
> Bảng lương đã finalized là **immutable**. Không sửa, không xóa. Cách xử lý:
> 1. Tạo payroll tháng 4 đúng như bình thường
> 2. Với bảng lương tháng 3 nhầm: ghi chú vào `payroll_records.notes` (nếu có field này) hoặc ghi vào audit_logs
> 3. Thực tế thanh toán: trả cho GV theo tháng 4, tháng 3 nhầm = 0 buổi thực tế → kế toán tự xử lý ngoài hệ thống
> Không thể rollback vì đã ghi `payroll_session_details` — dữ liệu phải nhất quán.

**Q30: Học viên học xong 24 buổi nhưng GV chưa hoàn thành điểm danh hết — session cuối vẫn pending — hệ thống xử lý thế nào?**
> Session thứ 24 vẫn `pending` → `enrollment.status` vẫn `active` (chưa complete). Hệ thống không tự complete enrollment — cần GV/Học vụ điểm danh buổi cuối. Sau khi submit attendance buổi 24 → `sessions.status = 'completed'` → trigger cập nhật `sessions_attended = 24`. Hệ thống gợi ý: "Lớp đã đủ 24 buổi — Xác nhận hoàn thành?" → Admin/Học vụ confirm → `enrollment.status = 'completed'` + `students.current_level` cập nhật.

**Q31: 2 học vụ cùng ghi danh cùng học sinh vào cùng 1 lớp đang có 11/12 chỗ — ai thành công?**
> DB trigger `trg_guard_capacity` check `COUNT(trial+active) < max_capacity` BEFORE INSERT. PostgreSQL row-level locking đảm bảo chỉ 1 INSERT thành công. Request thứ 2 nhận error `CLASS_CAPACITY_EXCEEDED`. Không có race condition vì trigger chạy trong transaction của INSERT — atomic. FE hiện toast error "Lớp vừa đủ học viên khi bạn đang thao tác".

**Q32: Phụ huynh đặt giữ chỗ (500k) cho con vào lớp sắp khai giảng, nhưng sau 30 ngày lớp vẫn chưa khai giảng — phí giữ chỗ có được hoàn không?**
> 2 trường hợp:
> - **Lớp chưa đủ sĩ số** (lỗi trung tâm không đủ học sinh): HOÀN 100% phí giữ chỗ + học phí nếu có → `refund_request` với `reason_type = 'center_unable_within_60days'`
> - **Phụ huynh tự hủy** sau 30 ngày: MẤT phí giữ chỗ. `enrollment → dropped`, phí giữ chỗ là cam kết 2 chiều.
> Cơ chế: cron job chạy hàng ngày check `enrolled_at < now() - 30 days AND status = 'reserved'` → auto expire nếu không có action.

**Q33: Học sinh đang trial (buổi 1), xin bảo lưu — được không?**
> **Không được**. Bảo lưu chỉ áp dụng cho `status = 'active'`. Trial là giai đoạn chưa đóng tiền, chưa cam kết. Nếu không muốn tiếp tục sau trial: drop enrollment (không mất gì vì chưa đóng tiền). FE hiện tooltip "Không thể bảo lưu — học viên đang trong giai đoạn học thử".

**Q34: Học sinh đã bảo lưu 1 lần (pause_count = 1), sau khi resume lại học vài buổi rồi muốn bảo lưu lần 2 — Admin có override được không?**
> **Không**. `pause_count <= 1` là CHECK constraint ở DB level — không có exception nào. Admin cũng không thể bypass. Nếu thực sự cần: Admin phải drop enrollment cũ, tạo enrollment mới (học viên mất lịch sử). Đây là quyết định thiết kế intentional — 1 lần bảo lưu là đủ linh hoạt trong 1 khóa 24 buổi.

**Q35: Học viên học hết Kindy, Starters, Movers, Flyers — hệ thống ghi nhận thế nào?**
> Sau mỗi khóa complete: `students.current_level` cập nhật lên level tiếp theo. Sau khi complete Flyers (level_order = 4, cao nhất):
> - `students.current_level = 'FLYERS'`
> - `students.graduated_at = now()` (field thêm mới)
> - Dashboard hiện badge "🎓 Tốt nghiệp"
> - Không có constraint nào block ghi danh khóa mới (trung tâm có thể mở khóa nâng cao sau này)

---

# CẤP 6 — SIÊU QUÁI (hội đồng chứng minh edge case)

**Q36: GV A đang cover buổi 8 lớp EIM-LS-01. Học vụ đồng thời assign GV A làm GV chính lớp EIM-LS-03 có cùng shift và T2 trong lịch. Hệ thống xử lý thế nào?**
> `ConflictCheckerService.checkTeacherConflict()` check tất cả 3 nguồn: sessions, session_covers, makeup_sessions. Lớp EIM-LS-03 có T2 → overlap với cover T2 của EIM-LS-01 → conflict. Block tạo lớp với error `CLASS_TEACHER_CONFLICT: GV A đang có lịch Ca 1 Thứ 2 (cover EIM-LS-01)`. Học vụ phải chọn GV khác hoặc đổi lịch lớp mới.

**Q37: Audit log có entry "Admin A xóa GV B". Sau đó Admin A cũng bị xóa. Audit log hiện tên ai?**
> Audit log là **append-only snapshot**. Entry gốc có `actor_id = AdminA.id`, `actor_code = 'EIM-ADM-xxxxx'`, `actor_role = 'ADMIN'` — tất cả là snapshot tại thời điểm ghi. Dù Admin A sau đó bị soft delete, audit entry vẫn hiện đúng thông tin. Field `actor_code` là string, không FK lookup → không bị NULL khi user bị xóa.

**Q38: Trung tâm có 2 kế toán, cả 2 cùng preview payroll của GV C tháng 4, rồi cả 2 cùng bấm "Chốt lương" trong 1 giây**
> `payroll_records` có `UNIQUE(teacher_id, period_month, period_year)`. Request thứ 2 nhận PostgreSQL unique violation error (code `23505`). Global error handler map sang `PAYROLL_ALREADY_FINALIZED` với HTTP 409. FE hiện toast "Đã có người chốt lương trước bạn" + link xem bảng lương.

**Q39: Học sinh A chuyển nhượng học phí cho học sinh B. Sau đó phát hiện enrollment của A thực ra đã bị bug tính sai sessionsAttended (thực tế học 10 buổi nhưng ghi 8) — credit đã chuyển sai số**
> Đây là data integrity issue. Xử lý:
> 1. Admin sửa `sessions_attended` về đúng (10) qua query trực tiếp + ghi audit
> 2. `amountTransferred` đã chốt trong `transfer_requests` — **không thể sửa**
> 3. Chênh lệch credit: Admin/Kế toán tạo phiếu thu bổ sung hoặc phiếu hoàn tùy chiều chênh lệch
> 4. Ghi note vào audit_logs về việc điều chỉnh
> Nguyên tắc: phiếu thu đã tạo không thể sửa, chỉ bù trừ bằng phiếu mới.

**Q40: Học sinh đang học lớp A (EIM-LS-01, T2+T4). Học vụ reschedule buổi 15 của lớp sang ngày T4 tuần sau — nhưng tuần sau đó lớp A cũng có buổi 16 vào đúng ngày T4 đó**
> `reschedule-session.usecase` validate: ngày mới không được trùng với session khác của **cùng lớp** trong cùng ngày. Query: `SELECT COUNT(*) FROM sessions WHERE class_id = X AND session_date = newDate AND id != currentSessionId`. Nếu > 0 → error `SESSION_DATE_CONFLICT: Lớp đã có buổi học vào ngày này`. Học vụ phải chọn ngày khác.

**Q41: Export bảng điểm danh dạng pivot (học sinh × buổi) cho lớp 12 người × 24 buổi. File Excel có 288 cells dữ liệu — có xử lý được không?**
> 288 cells là rất nhỏ, xử lý tức thì. Background job chỉ kích hoạt khi > 1000 rows (tổng). Pivot table được build bằng `exceljs`: header row = session dates, data rows = từng học sinh, cells = P/L/A/U với màu tương ứng (xanh/vàng/xanh dương/đỏ). Column width auto-fit. Freeze pane ở row 1 và column 1. File tên: `DiemDanh_EIM-LS-01_S1-24.xlsx`.

**Q42: Học sinh bảo lưu sau buổi 20 (pause_count = 0 nên hợp lệ), sau đó trung tâm đóng cửa vĩnh viễn. Học phí còn lại xử lý thế nào?**
> Đây là edge case ngoài spec, nhưng xử lý được:
> - Enrollment `status = 'paused'`, `sessionsAttended = 20`, còn 4 buổi
> - `creditRemaining = tuitionFee × 4/24`
> - Admin tạo `refund_request` với `reason_type = 'special_case'`, `refund_amount = creditRemaining`
> - Kế toán tạo phiếu âm hoàn lại phần còn lại
> - Ghi note đầy đủ vào `review_note`
> Hệ thống không có concept "đóng cửa trung tâm" — xử lý thủ công từng enrollment.

**Q43: Giám khảo hỏi: "Import 10.000 học sinh 1 lúc thì hệ thống có chịu không?"**
> Import chạy server-side: parse file Excel → validate từng row → INSERT trong 1 transaction. 10.000 rows:
> - Parse + validate: ~2-3 giây (CPU bound)
> - INSERT trong transaction: ~5-10 giây (IO bound, batch insert)
> - Tổng < 15 giây — chấp nhận được
> Nếu lo lắng: chia batch 500 rows/transaction, trả progress%. Background job + polling nếu cần. Sau import: `REFRESH MATERIALIZED VIEW CONCURRENTLY` để search thấy data mới. Constraint violations (trùng SĐT) ghi vào errors list — không rollback cả file.

**Q44: Học sinh nhờ anh/chị đóng học phí giúp — người nộp tiền khác với tên học sinh — hệ thống có hỗ trợ không?**
> Có. Phiếu thu có 2 trường riêng: `student_id` (học sinh) và `payer_name`/`payer_address` (người thực tế nộp tiền). Ví dụ: `student_id → Nguyễn Văn An`, `payer_name = 'Nguyễn Văn Tâm'` (bố). Đây là thiết kế intentional từ spec — phiếu thu cần `payer_name` riêng cho đúng chứng từ pháp lý.

**Q45: Hệ thống có tracking được "học viên này đã học qua mấy trung tâm tiếng Anh trước đây" không?**
> Không, và đây là **ngoài phạm vi**. Hệ thống EIM chỉ quản lý dữ liệu nội bộ trung tâm. `test_result` field trong students có thể ghi kết quả test đầu vào (VD: "Starters placement - 72/100") nhưng không có field lịch sử học tập bên ngoài. Nếu cần mở rộng: thêm bảng `student_education_history` — nằm ngoài scope đồ án.

---

# PHẦN CUỐI — CÂU HỎI META

**Q46: Hệ thống này có thể mở rộng cho chuỗi trung tâm (multi-branch) không?**
> Hiện tại thiết kế cho **1 trung tâm**. Để multi-branch cần: thêm `branch_id` vào hầu hết bảng (users, classes, rooms, students...), RBAC thêm cấp branch manager, báo cáo consolidate across branches. Không phức tạp về concept nhưng tốn công sức vì phải sửa nhiều bảng và mọi query. Thiết kế hiện tại không block việc mở rộng này.

**Q47: Nếu trung tâm muốn thêm môn học (Piano, Toán...) bên cạnh tiếng Anh thì cần đổi gì?**
> Ít hơn bạn nghĩ. Programs là generic — thêm `code = 'PIANO'`, `name = 'Piano'`, `default_fee`, `level_order`. Classes/Sessions/Enrollments không cần đổi gì. Phần cần xem lại: mã lớp (hiện EIM-LK/LS/LM/LF — cần thêm prefix mới), generate_eim_code prefix. Phần học bù, bảo lưu, điểm danh dùng được ngay.

**Q48: Điểm yếu lớn nhất của thiết kế hiện tại là gì?**
> Trả lời thành thật, có chuẩn bị:
> 1. **Không có real-time notification**: audit log ghi đầy đủ nhưng không có push notification (WebSocket/FCM) → GV không biết ngay khi được assign cover
> 2. **Search chưa real-time**: `REFRESH MATERIALIZED VIEW` cần gọi thủ công sau insert — search không thấy data mới ngay
> 3. **Không có offline support**: điểm danh phải online — GV ở vùng mạng kém không dùng được
> 4. **Báo cáo PDF** chưa có template đẹp — dùng browser print CSS thay vì PDF generation thực sự

**Q49: So sánh approach của bạn với việc dùng 1 SaaS có sẵn (School Management System)?**
> SaaS có sẵn: triển khai nhanh, bảo trì thấp, nhưng generic — không fit nghiệp vụ đặc thù của trung tâm tiếng Anh (cover GV, tính lương theo buổi, học thử 2 buổi, bảo lưu 1 lần). Tự xây: tốn công hơn nhưng phản ánh đúng 100% nghiệp vụ, dữ liệu hoàn toàn kiểm soát, không bị phụ thuộc vendor. Với quy mô 1 trung tâm nhỏ và đây là đồ án tốt nghiệp — tự xây là hợp lý.

**Q50: Học được gì từ project này?**
> Gợi ý trả lời:
> - Onion Architecture giúp tách biệt concern rõ ràng — business logic không bị pollute bởi DB hay framework
> - Business rules phức tạp (bảo lưu, tính lương) cần enforce ở **nhiều tầng**: DB constraint, trigger, application logic — không chỉ 1 tầng
> - Audit trail và immutability là foundation của hệ thống tài chính, không thể bỏ qua
> - Edge cases không phải exception mà là **phần thiết yếu** của thiết kế — cần nghĩ từ đầu, không phải patch sau
> - Token refresh race condition, materialized view refresh, DEFERRABLE constraint — những chi tiết nhỏ này là thứ phân biệt senior và junior developer
