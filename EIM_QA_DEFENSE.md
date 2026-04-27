# EIM — BỘ Q&A CHỒNG VẶN HỘI ĐỒNG
> Tổng hợp từ: OVERVIEW v4, tất cả use cases, edge cases đã triển khai.
> Mục tiêu: không bị bất ngờ khi hội đồng hỏi bất kỳ câu nào.
> Format: Câu hỏi → Trả lời chuẩn + lý do thiết kế.

---

# PHẦN 1 — TỔNG QUAN & KIẾN TRÚC

**Q: Tại sao chọn kiến trúc Onion thay vì MVC truyền thống?**
> Onion Architecture tách biệt domain logic khỏi infrastructure. Domain (business rules) không phụ thuộc vào database hay framework — có thể test độc lập. Với hệ thống EIM có nhiều business rules phức tạp như bảo lưu, tính lương, học bù, tách lớp này ra giúp dễ maintain và mở rộng. MVC truyền thống dễ dẫn đến fat controller, business logic rải rác.

**Q: Tại sao dùng PostgreSQL mà không phải MySQL hay MongoDB?**
> EIM có nhiều ràng buộc dữ liệu phức tạp: UNIQUE DEFERRABLE (class_staff), triggers tự động cập nhật sessions_attended, array type (schedule_days SMALLINT[]), array overlap operator (&&) để check conflict lịch, JSONB cho amenities và audit diff. Đây là các tính năng PostgreSQL-specific. MongoDB không phù hợp vì dữ liệu có cấu trúc rõ ràng và cần ACID cho nhiều transaction như chuyển nhượng học phí.

**Q: Tại sao có 24 bảng? Có bị over-engineering không?**
> Mỗi bảng giải quyết 1 domain cụ thể. Không có bảng nào thừa:
> - `enrollment_history`: audit trail không thể gộp vào enrollments vì 1 enrollment có nhiều events
> - `session_covers`: tách riêng vì cover chỉ áp dụng từng buổi, không phải toàn lớp
> - `payroll_session_details`: snapshot từng buổi để đối soát — không thể tính lại sau
> - `audit_logs` tách `audit_logs_archive`: log > 90 ngày archive để giữ bảng chính nhỏ, query nhanh

**Q: UUID thay vì auto-increment ID — có làm chậm query không?**
> UUID v4 có index performance kém hơn integer do random, dẫn đến index fragmentation. Nhưng EIM chấp nhận trade-off này vì: (1) không lộ số lượng record qua sequential ID, (2) có thể merge data từ nhiều môi trường mà không conflict ID. Với quy mô trung tâm nhỏ (<10.000 records), hiệu năng không phải vấn đề. Đã có đủ index trên các cột query thường xuyên.

---

# PHẦN 2 — NGHIỆP VỤ CỐT LÕI

**Q: Tại sao `tuition_fee` trong enrollments là IMMUTABLE?**
> Đây là nguyên tắc kế toán. Khi học viên ghi danh, học phí được "chốt" theo giá tại thời điểm đó. Nếu trung tâm thay đổi `programs.default_fee` sau này, học viên đã ghi danh không bị ảnh hưởng — đúng với thực tế nghiệp vụ và tránh tranh chấp. Trigger `trg_guard_tuition_fee` enforce điều này ở tầng DB, không chỉ application logic.

**Q: Công nợ được tính thế nào? Có lưu trong DB không?**
> Công nợ = `enrollment.tuition_fee - SUM(receipts.amount WHERE enrollment_id = X)`. Không lưu trực tiếp — tính realtime qua function `enrollment_debt()`. Lý do: nếu lưu thì phải đồng bộ mỗi khi có phiếu thu mới, dễ lỗi. Tính on-the-fly từ receipts luôn chính xác. Với materialized view hoặc index phù hợp, hiệu năng không phải vấn đề.

**Q: Tại sao không cho DELETE receipts?**
> Phiếu thu là chứng từ kế toán. Xóa vật lý vi phạm nguyên tắc immutability của dữ liệu tài chính. Thay vào đó dùng "phiếu âm" (void receipt): tạo receipt mới với `amount = -original.amount` và `voided_by_receipt_id` trỏ về phiếu gốc. Trigger `trg_prevent_receipt_delete` enforce điều này. Phương pháp này giúp audit trail luôn đầy đủ.

**Q: Tại sao bảo lưu chỉ được 1 lần trong 1 enrollment?**
> Thực tế nghiệp vụ: trung tâm cần đảm bảo học viên cam kết. Cho phép bảo lưu nhiều lần dễ bị lợi dụng (giữ chỗ vô thời hạn, ảnh hưởng sĩ số). 1 lần là cân bằng giữa linh hoạt cho học viên và quyền lợi trung tâm. Field `pause_count` enforce ở cả DB (CHECK constraint) và application logic — double protection.

**Q: Tại sao bảo lưu từ buổi 4 mới cần Admin duyệt?**
> 3 buổi đầu là "giai đoạn thử" — trung tâm chưa "chốt danh sách". Sau buổi 3, trung tâm đã lên kế hoạch GV, phòng học, in tài liệu — bảo lưu ảnh hưởng đến vận hành. Admin duyệt để xem xét từng trường hợp cụ thể (lý do hợp lý không, có thể xếp lớp khác không...). Số `3` này có thể config trong `system_config.max_free_period_sessions`.

**Q: `effective_teacher_id` là gì? Tại sao cần function riêng?**
> Khi có GV cover, session có 2 GV: GV chính (`sessions.teacher_id`) và GV cover (`session_covers.cover_teacher_id`). Khi tính lương, phải dùng GV thực tế dạy buổi đó. `effective_teacher_id(session_id)` trả về `cover_teacher_id` nếu có cover completed, ngược lại trả `teacher_id`. Nếu không có function này, mỗi chỗ tính lương phải viết lại logic này — dễ bug.

**Q: Tại sao `class_staff` cần UNIQUE constraint DEFERRABLE?**
> Khi thay GV giữa khóa cần 2 thao tác trong 1 transaction: UPDATE record cũ (set `effective_to_session`) và INSERT record mới (`effective_to_session = NULL`). Cả 2 cùng có `class_id` và `effective_to_session = NULL` trong cùng 1 thời điểm. Nếu không DEFERRABLE, INSERT sẽ fail ngay vì unique violation. DEFERRABLE cho phép check constraint ở cuối transaction thay vì sau mỗi statement.

---

# PHẦN 3 — ĐIỂM DANH & HỌC BÙ

**Q: Học bù bị block khi nào? Logic có phức tạp không?**
> 2 điều kiện độc lập, thỏa 1 trong 2 thì block:
> (1) `total_absent > 3` — tổng vắng (có phép + không phép) quá 3 buổi
> (2) `absent_unexcused >= 3` — vắng không phép đủ 3 lần
> Trigger `trg_check_makeup_blocked` cập nhật `enrollment.makeup_blocked` sau mỗi INSERT/UPDATE attendance. Không có học bù cho buổi vắng không phép dù makeup_blocked = false.

**Q: Học sinh vắng không phép 3 lần thì sao? Có ảnh hưởng gì nữa không?**
> Ngoài block học bù, hệ thống: (1) hiện badge cảnh báo đỏ trên enrollment card, (2) ghi vào `total_absent` field, (3) hiện trong dashboard "Học viên cần chú ý". GV thấy cảnh báo khi điểm danh lần thứ 3. Không tự động drop enrollment — quyết định đó thuộc về Admin/Academic sau khi liên hệ phụ huynh.

**Q: Tại sao UPSERT cho attendance thay vì INSERT?**
> Học vụ có thể nhập sai và cần sửa trong ngày. Nếu chỉ INSERT thì phải xóa record cũ trước, phức tạp hơn và dễ lỗi. UPSERT (`INSERT ON CONFLICT DO UPDATE`) xử lý cả 2 trường hợp trong 1 query. Trigger `trg_sync_attendance` chạy sau mỗi UPSERT để cập nhật `sessions_attended` và `sessions_absent` — luôn đồng bộ.

**Q: Ai được phép điểm danh?**
> ADMIN: tất cả sessions. ACADEMIC: tất cả sessions. TEACHER: chỉ sessions mà mình là `effective_teacher_id` (GV chính HOẶC GV cover). Việc TEACHER check được qua middleware `requireOwnSession`. Phân quyền này đảm bảo GV không điểm danh lớp người khác.

---

# PHẦN 4 — HỌC THỬ & PHÍ GIỮ CHỖ

**Q: Học thử 2 buổi rồi không đăng ký thì học phí xử lý thế nào?**
> Không có học phí phát sinh trong giai đoạn trial. Enrollment `status = 'trial'`, `tuition_fee` được set nhưng `paid_at = NULL` và không có receipt nào. Khi drop sau trial: enrollment `status = 'dropped'`, không hoàn gì cả vì chưa thu gì. GV vẫn được tính lương cho 2 buổi dạy trial (tính theo `effective_teacher_id` như bình thường).

**Q: Phí giữ chỗ có được hoàn lại không?**
> Phụ thuộc lý do: Nếu trung tâm lỗi (không khai giảng được sau 60 ngày): hoàn toàn bộ kể cả phí giữ chỗ. Nếu phụ huynh tự không đăng ký: mất phí giữ chỗ (lý do chủ quan). Điều này được config trong `reason_type` của refund_requests. Thực tế: phí giữ chỗ là cam kết 2 chiều — trung tâm giữ chỗ, phụ huynh cam kết sẽ đăng ký.

**Q: Enrollment `reserved` khác gì `pending`?**
> `pending`: học viên đã được tạo hồ sơ, chưa đóng tiền, chưa có cam kết tài chính. `reserved`: phụ huynh đã đóng phí giữ chỗ (thường 500k), có receipt trong DB. `reserved` có thời hạn 30 ngày, sau đó tự chuyển `dropped`. Khi activate từ `reserved`: `remaining_fee = tuition_fee - reservation_fee` — trừ phần đã đặt cọc.

---

# PHẦN 5 — TÀI CHÍNH & LƯƠNG

**Q: Cash basis và accrual basis khác nhau thế nào trong hệ thống?**
> **Cash basis**: `SUM(receipts.amount WHERE payment_date IN period)` — tiền thực tế đã thu vào tài khoản. **Accrual basis**: `SUM(enrollments.tuition_fee WHERE enrolled_at IN period)` — học phí phát sinh theo nghĩa vụ. Ví dụ: học sinh ghi danh tháng 3 nhưng đóng tiền tháng 4 → accrual tháng 3 tăng, cash tháng 4 tăng. Hiển thị cả 2 giúp Admin ra quyết định tốt hơn.

**Q: Lương GV được tính như thế nào khi có GV cover?**
> Cuối tháng, với mỗi session `status = completed`:
> - Nếu có `session_covers.status = completed` → tính cho `cover_teacher_id`
> - Ngược lại → tính cho `sessions.teacher_id`
> GV chính bị cover: không được tính buổi đó (`sessionsCovered`). GV cover: được tính thêm buổi đó (`sessionsAsCover`). Lương = `sessionsCount × salary_per_session + allowance`. `salary_per_session` được snapshot tại thời điểm chốt — thay đổi sau không ảnh hưởng.

**Q: Tại sao không cho sửa bảng lương sau khi đã chốt?**
> Bảng lương đã chốt là chứng từ kế toán, có thể đã được ký và thanh toán. Sửa sau tạo inconsistency với sổ sách. Nếu có sai sót: tạo bảng lương bổ sung (thêm/bớt) cho tháng sau, ghi rõ lý do. Constraint `UNIQUE(teacher_id, period_month, period_year)` block chốt 2 lần cùng tháng/GV.

**Q: Chuyển nhượng học phí hoạt động thế nào? Tại sao cần transaction?**
> Học viên A chuyển nhượng phần học phí còn lại cho học viên B. Cần atomic vì 5 thao tác phải xảy ra cùng nhau hoặc không gì cả: (1) tính `sessionsRemaining`, (2) tạo phiếu âm cho A, (3) tạo enrollment mới cho B, (4) tạo phiếu dương cho B, (5) update enrollment A → transferred. Nếu bất kỳ bước nào fail (VD: lớp B vừa đầy) → rollback toàn bộ, không có inconsistent state.

---

# PHẦN 6 — LỚP HỌC & CONFLICT CHECK

**Q: Hệ thống check conflict lịch thế nào khi tạo lớp?**
> `ConflictCheckerService` query DB: với GV/phòng đã chọn, có sessions nào có cùng `shift` VÀ `schedule_days` overlap (dùng PostgreSQL array overlap operator `&&`) với lớp active khác không. Check này áp dụng khi: tạo lớp mới, assign cover, reschedule session, thay GV giữa khóa. Error message nếu conflict sẽ chứa tên lớp/ca đang trùng để staff xử lý.

**Q: `schedule_days` là mảng số thay vì string — tại sao?**
> `SMALLINT[]` cho phép dùng PostgreSQL array operators trực tiếp. Ví dụ: `{2,4} && {3,4}` = `true` (trùng thứ 4). Nếu lưu string ("T2,T4") thì phải parse ra mới compare được — chậm hơn và phức tạp hơn. Array cũng dễ index với GIN index nếu cần. Frontend nhận `[2,4]` và map sang "Thứ 2, Thứ 4" qua `fmt.scheduleDays()`.

**Q: Tại sao cho phép chọn lịch tự do thay vì fix 5 combo?**
> Spec ban đầu fix 5 combo nhưng thực tế trung tâm có thể muốn T2+T6, T3+T7... Chỉ cần đảm bảo 2 điều kiện: đúng 2 ngày và cách nhau ít nhất 1 ngày (gap >= 2). Validation bằng Zod ở cả FE và BE. Thay fix 5 combo = 10 combo hợp lệ, linh hoạt hơn cho trung tâm.

**Q: Có bao nhiêu phòng học? Tại sao chia theo tầng?**
> 6 phòng trên 2 tầng: P.101-103 (tầng 1, 15 chỗ), P.201-202 (tầng 2, 12 chỗ), P.203 (tầng 2, 20 chỗ — phòng lớn). Chia tầng lưu trong DB (`floor` field) để: (1) UI group phòng theo tầng cho dễ chọn, (2) Admin có thể filter phòng theo tầng khi cần, (3) phòng lớn P.203 có thể dùng cho sự kiện trung tâm. `amenities` JSONB lưu tiện ích (projector, AC...) linh hoạt không cần thêm cột.

---

# PHẦN 7 — BẢO MẬT & PHÂN QUYỀN

**Q: RBAC được implement như thế nào?**
> 4 roles: ADMIN (permissions=["*"]), ACADEMIC, ACCOUNTANT, TEACHER. Permissions lưu JSONB trong bảng `roles`. Mỗi API route gắn `authorize('permission:action')` middleware. Middleware đọc `req.user.permissions`, check có chứa action không — ADMIN với "*" luôn pass. TEACHER có thêm IDOR check: chỉ xem session/payroll của mình.

**Q: IDOR protection làm thế nào?**
> IDOR (Insecure Direct Object Reference) được xử lý ở middleware `teacher-idor.middleware`. TEACHER gọi `GET /sessions/:id` → middleware check `effective_teacher_id(sessionId) === req.user.id`. Nếu không phải → 403. Tương tự với payroll: check `payroll_records.teacher_id === req.user.id`. ADMIN/ACADEMIC/ACCOUNTANT bypass tất cả IDOR checks.

**Q: Token refresh hoạt động thế nào khi nhiều request cùng 401?**
> Race condition pattern: biến `isRefreshing` + `waitQueue`. Request đầu tiên nhận 401 → set `isRefreshing = true`, gọi refresh. Các request sau cũng nhận 401 → thấy `isRefreshing = true` → push resolve vào `waitQueue`, chờ. Khi refresh xong → drain queue, retry tất cả với token mới. Refresh fail → clear auth, redirect login. Giải pháp này đảm bảo refresh chỉ gọi 1 lần duy nhất.

**Q: Audit log có thể bị sửa hoặc xóa không?**
> Không. Thiết kế append-only: (1) application không có endpoint UPDATE/DELETE audit_logs, (2) lý tưởng: DB role chỉ có INSERT permission trên bảng này. `AuditWriter` bọc trong try-catch — lỗi audit không làm fail request chính. `AuditWriter` redact các field nhạy cảm (password_hash, token) trước khi ghi.

---

# PHẦN 8 — EDGE CASES TRICKY

**Q: Học viên đang học Starters muốn lên Movers giữa khóa thì học phí thế nào?**
> Tính credit: `credit = tuition_fee × (24 - sessionsAttended) / 24`. Ví dụ học 16/24 buổi Starters (3tr): `credit = 3.000.000 × 8/24 = 1.000.000đ`. Học phí Movers = 3.000.000đ → cần đóng thêm 2.000.000đ. Hệ thống tạo phiếu âm (-1tr) cho enrollment cũ và phiếu dương (+2tr) cho enrollment mới. Nếu credit > học phí mới: tạo phiếu hoàn chênh lệch.

**Q: Học sinh nghỉ phép không học được thứ 4 trong lớp T2+T4 thì sao?**
> 3 giải pháp theo thứ tự ưu tiên: (1) Chuyển lớp có lịch phù hợp hơn (trong 3 buổi đầu), (2) Điểm danh vắng có phép, xếp học bù (tối đa 3 buổi vắng), (3) Bảo lưu đợi lớp mới mở lịch phù hợp. Không có cơ chế "học riêng ngày khác" — lịch là của cả lớp. Endpoint `/classes/suggestions?programId=X&unavailableDays=[4]` trả về lớp không có thứ 4.

**Q: 2 kế toán cùng tạo phiếu thu cho 1 enrollment trong cùng 1 lúc?**
> Hệ thống ALLOW điều này — phiếu thu không có unique constraint per enrollment. Kết quả: enrollment bị thu thừa, debt < 0 (dư). Hệ thống hiển thị "Dư: X₫" thay vì "Còn nợ". Kế toán xử lý bằng cách tạo phiếu âm hoàn lại phần thừa. Phương án block bằng lock transaction phức tạp hơn lợi ích — trường hợp này rất hiếm và dễ nhận biết.

**Q: GV bị xóa giữa tháng thì tính lương thế nào?**
> Soft delete (`deleted_at IS NOT NULL`) — GV không login được nhưng data vẫn còn. Sessions đã dạy trước `deleted_at` vẫn valid, `effective_teacher_id` vẫn trả đúng. Khi chốt lương: query không filter `deleted_at` → vẫn tính đủ cho tháng đó. Chỉ các tháng sau mới không có sessions nữa (vì không được phân công lớp mới).

**Q: Admin xóa chính mình thì sao?**
> Block ở application layer: `if (actorId === targetId) throw SELF_DELETE_NOT_ALLOWED`. Thêm nữa: nếu là Admin cuối cùng trong hệ thống, block đổi role sang bất kỳ role nào khác. Query: `SELECT COUNT(*) FROM users JOIN roles ON... WHERE roles.code='ADMIN' AND deleted_at IS NULL`.

**Q: Học viên đã drop có thể ghi danh lại không?**
> Có — tạo enrollment mới. Enrollment cũ vẫn còn với `status = 'dropped'` để giữ lịch sử. Enrollment mới bắt đầu từ đầu: `sessions_attended = 0`, `pause_count = 0`. Không có giới hạn số lần ghi danh lại — nhưng mỗi lần phải đóng học phí đầy đủ.

**Q: Session bị reschedule nhiều lần thì lưu ngày gốc nào?**
> `sessions.original_date` chỉ lưu ngày đầu tiên trước khi reschedule lần đầu — lần đầu check `IF original_date IS NULL THEN original_date = session_date`. Reschedule lần 2 không ghi đè `original_date`. Như vậy luôn biết buổi học này ban đầu dự kiến ngày nào, dù đã dời bao nhiêu lần.

---

# PHẦN 9 — DATABASE DESIGN DECISIONS

**Q: Tại sao materialized view cho search thay vì full-text index trực tiếp?**
> `mv_search_students` kết hợp nhiều fields (fullName + parentName + schoolName) thành 1 `tsvector` với GIN index. Nếu index trực tiếp trên bảng gốc: mỗi UPDATE row phải reindex — chậm hơn. Materialized view: batch refresh sau khi thêm data mới (`REFRESH MATERIALIZED VIEW CONCURRENTLY` — không lock read). Trade-off: search không realtime, nhưng refresh sau mỗi INSERT/UPDATE đủ nhanh cho use case này.

**Q: `REFRESH MATERIALIZED VIEW CONCURRENTLY` là gì? Tại sao cần UNIQUE index?**
> `CONCURRENTLY` cho phép refresh không block read queries — view vẫn trả kết quả cũ trong khi đang refresh. Yêu cầu có ít nhất 1 UNIQUE index để PostgreSQL track rows đã thay đổi. Đã tạo `UNIQUE INDEX idx_mv_stu_id ON mv_search_students(id)` và tương tự cho users. Không có UNIQUE index → phải dùng `REFRESH` thường (lock table).

**Q: Tại sao không dùng ORM (TypeORM, Prisma) mà dùng raw SQL với `pg`?**
> ORM sinh SQL không tối ưu cho các query phức tạp như: array overlap `&&`, window functions, CTE, trigger-based computed fields. EIM có nhiều query kiểu này. Raw SQL với `pg` cho full control, dễ explain/analyze. Nhược điểm: phải viết nhiều hơn, nhưng codebase dễ debug hơn khi có vấn đề performance.

**Q: `payroll_session_details` lưu `class_code` dưới dạng snapshot — tại sao?**
> Nếu sau này `class_code` thay đổi (hiếm nhưng có thể), bảng lương phải giữ nguyên class_code tại thời điểm chốt để đối soát. Tương tự `salary_per_session_snapshot` và `allowance_snapshot` trong `payroll_records`. Nguyên tắc: mọi thứ liên quan đến tài chính đã chốt đều là snapshot, không reference về giá trị hiện tại.

---

# PHẦN 10 — FRONTEND & INTEGRATION

**Q: Tại sao dùng TanStack Query thay vì Redux cho API state?**
> Redux phù hợp cho global UI state (auth, theme). API state (lists, details) phù hợp hơn với TanStack Query vì: built-in caching (staleTime), background refetch, optimistic updates, deduplication (cùng query gọi 2 lần = 1 request). Nếu dùng Redux cho API state phải tự implement tất cả những điều này — phức tạp hơn nhiều.

**Q: Token refresh race condition ở FE được xử lý thế nào?**
> Axios interceptor dùng pattern `isRefreshing + waitQueue`: request đầu nhận 401 → refresh → drain queue. Nếu dùng simple retry thì 10 request cùng 401 = 10 refresh calls — sai. Waitqueue đảm bảo chỉ 1 refresh và tất cả request pending đều được retry với token mới sau khi refresh xong.

**Q: Tại sao `amount_in_words` phải từ BE, không tính ở FE?**
> FE có `amountToWordsVi()` để preview realtime (UX). Nhưng giá trị lưu DB phải từ BE vì: (1) là chứng từ pháp lý, cần đảm bảo tính chính xác của phía hệ thống, (2) nếu FE có bug trong hàm convert → chứng từ sai, (3) BE là source of truth. FE không gửi `amount_in_words` trong request body — BE tự tính và trả về trong response.

**Q: `scheduleDay = [2,4]` từ BE — FE hiện thế nào?**
> `fmt.scheduleDays([2,4])` map: `{2:'Thứ 2', 3:'Thứ 3', 4:'Thứ 4', 5:'Thứ 5', 6:'Thứ 6', 7:'Thứ 7'}` → "Thứ 2, Thứ 4". Hàm này trong `src/shared/lib/date.ts` dùng xuyên suốt: class card, class detail, session timeline, my-sessions. 1 điểm thay đổi nếu cần.

---

# PHẦN 11 — CÂU HỎI ĐỂ DỌN

**Q: Hệ thống hỗ trợ bao nhiêu concurrent users? Load testing thế nào?**
> Với quy mô 1 trung tâm (<50 nhân viên, <500 học sinh), PostgreSQL + Node.js connection pool (20 connections) xử lý tốt. Load test cơ bản: 10 concurrent requests đến `/classes` < 3s tổng. Bottleneck dự kiến ở search GIN index — nhưng với `mv_search_*` đã được optimize, search query < 100ms. Scale lên: thêm read replica, tăng pool size.

**Q: Có backup/restore strategy không?**
> File `EIM_FULL_SETUP.sql` là cả schema + seed — chạy 1 lần là có full DB. Production cần: (1) `pg_dump` daily backup, (2) WAL archiving cho point-in-time recovery. `npm run db:fresh` = reset + migrate + seed — dùng cho development.

**Q: Soft delete mọi thứ — DB có bị đầy không?**
> Với quy mô trung tâm tiếng Anh (vài trăm học sinh/năm), soft delete không phải vấn đề storage. `audit_logs_archive` chứa log > 90 ngày để giữ `audit_logs` nhỏ. Nếu scale: thêm partitioning hoặc cron job archive data cũ. `deleted_at IS NULL` filter đã có index nên query không chậm dù có nhiều soft-deleted rows.

**Q: Import/Export hỗ trợ format nào?**
> Import: `.xlsx`, `.xls`, `.csv`. Export: `.xlsx` (mặc định), `.csv` (audit log), `.pdf` (roster, lịch học — dùng để in). File lớn (>=1000 rows): background job + polling. Template Excel có dropdown validation, sample row, sheet hướng dẫn — giảm lỗi nhập liệu.

**Q: Đã test chưa? Coverage bao nhiêu?**
> Unit tests cho domain usecases (business rules quan trọng: bảo lưu, tính lương, conflict check). Integration tests cho API endpoints chính. Smoke test script `tests/api-smoke.sh` chạy curl sau mỗi deploy. Regression test `tests/regression.sh` chạy < 30s sau mỗi commit quan trọng. DB invariant tests bằng SQL assertions.

---

# PHẦN 12 — CÂU HỎI TỰ DỌN (giám khảo hay hỏi cuối)

**Q: Nếu làm lại từ đầu, bạn sẽ thay đổi gì?**
> Gợi ý trả lời thành thật: (1) Nghiên cứu kỹ hơn về conflict check ngay từ đầu — `ConflictCheckerService` phải được implement đúng từ đầu thay vì stub luôn return false. (2) Thiết kế API response shape thống nhất hơn — một số endpoint trả 2 shape khác nhau (VD: pause) khiến FE phải handle phức tạp. (3) Viết integration test song song với code thay vì để cuối.

**Q: Hệ thống chưa làm được gì? Hạn chế là gì?**
> Trả lời thành thật: (1) Notification system thực sự (in-app, email, SMS) — hiện chỉ có audit logs. (2) Calendar sync cho GV (.ics export có nhưng sync 2 chiều với Google Calendar chưa có). (3) Mobile app — chỉ có web responsive. (4) Multi-branch — hệ thống thiết kế cho 1 trung tâm, mở rộng multi-branch cần refactor schema. (5) Thanh toán online — chỉ hỗ trợ ghi nhận thủ công.

**Q: Điểm mạnh nhất của hệ thống là gì?**
> Audit trail đầy đủ và bất biến — mọi thao tác đều được ghi với old/new values, actor, timestamp. Tài chính immutable — không thể sửa/xóa phiếu thu, học phí không thay đổi sau khi ghi danh. Business rules double-enforced (DB + application) — không thể bypass qua API hay trực tiếp vào DB. Đây là những điểm quan trọng nhất với hệ thống quản lý tài chính giáo dục.
