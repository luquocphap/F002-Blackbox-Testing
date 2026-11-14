# F002 – Testcases

28 TC: ECP 7 (001–007), BVA 7 (008–014), Decision Table 7 (015–021), Use-case 7 (022–028). Đây là hướng dẫn thực hiện và expected result, không phải kết quả PASS/FAIL đã chạy trong gói bàn giao.

## Quy ước và thao tác chung

- Chạy setup toàn suite theo README, đủ 28 READY. Mỗi TC có course riêng, chỉ Manual enrolments bật; không dùng course/user của TC khác. Không setup/reset/cleanup giữa các TC. Tài khoản fixture không có nguồn enrolment/role khác che lấp kết quả access.
- Trong đầu ra setup, chọn `tests[TC-ID].fixture`: `course` là nguyên tên course, `username_prefix` là tiền tố tài khoản, `S` là custom start UTC. U1/U2/U3 là `username_prefix` + `_u1`/`_u2`/`_u3`; email là username + `@example.invalid`. Mật khẩu tài khoản thử nghiệm local: `F002!Local2026x`. Không dùng token hoặc ID của lượt cũ.
- Gọi t0 là thời điểm setup (`prepared_at`, hoặc `prepared`); S là ngày setup +2 ngày lúc 12:00 UTC. Course start là ngày trước ngày setup lúc 00:00 UTC. S cũng bằng Course start +3 ngày +12 giờ. Dùng S còn tương lai; chạy bộ test trong ngày setup, không qua nửa đêm UTC. Admin và Student dùng UTC; giữ timezone gốc của Admin để khôi phục cuối lượt.
- Mở fixture: đăng nhập Admin → Home → tìm nguyên tên `course` → mở course → Participants. Nếu course không hiện ngay, dùng Search courses với nguyên tên. Ghi số participant ban đầu. Trong dòng user, xác định bằng email đầy đủ, không chỉ tên rút gọn.
- Form ghi danh: bấm **Enrol users** ngoài trang → chờ modal. Gõ username trong Select users, chờ suggestion có đúng email, click suggestion và kiểm tra selected item. Chỉ gõ search chưa phải chọn user. Assign role chọn đúng label. **Show more...** mở Starting from, Enrolment duration, Enrolment ends và Recover user's old grades if possible.
- Chọn **Choose...** trong Starting from để nhập custom start. Với ngày S/E, nhập đủ Day/Month/Year/Hour/Minute vào đúng nhóm; bật checkbox Enable của End bằng click để mở date controls. Khi End bật, Duration bị khóa; muốn chọn Duration trước hết tắt End. Với duration hữu hạn hoặc Unlimited, giữ End tắt trừ TC yêu cầu explicit End.
- Submit bằng **Enrol users** trong modal, chờ phản hồi và bảng cập nhật. Modal đóng không đủ chứng minh thành công. Đọc count, dòng email, role/status; mở **Edit enrolment** trong đúng dòng để đọc start/end và trạng thái checkbox, rồi **Cancel** nếu chỉ đọc. Không Save để chuẩn bị dữ liệu cho bước tiếp theo, trừ TC-025.
- Kiểm tra access thủ công: ghi nhớ course URL lấy từ link UI, đăng xuất Admin → đăng nhập đúng U1 → mở lại URL mới. Không dùng Admin hoặc trang course đã mở trước để kết luận quyền Student. Sau bước Student, đăng xuất U1, trở lại Admin trước TC tiếp theo. Bảng Participants có thể hiển thị **Not current** trong khi Status trong Edit enrolment vẫn **Active**; phân biệt trạng thái với hiệu lực thời gian.
- Khi FAIL, ghi bước/actual và bằng chứng; nếu thiếu precondition thì BLOCKED. Chỉ cleanup cuối suite theo README. TC-013 là oracle mở, ghi OBSERVED; các dòng “Cần xác minh” được giữ từ thiết kế để người chạy đối chiếu expected, không phải nhãn PASS có sẵn.

## TC-002-001 — Không chọn user

**Test ID:** TC-002-001  
**Kỹ thuật thiết kế:** ECP  
**Mục tiêu kiểm thử:** Không chọn user.

**Precondition:** Setup toàn suite thành công; Admin/UI UTC; course riêng, manual bật duy nhất; U1/U2/U3 chưa enrol; Participants có 0 participant trước thao tác.

**Test data:** Course/U1/U2/U3/S của chính TC-002-001 theo đầu ra setup. Selection rỗng; Student; Now; Unlimited; End tắt.

**Các bước thực hiện:**

1. Đăng nhập Admin; mở đúng course TC-002-001 theo quy ước trên → Participants; xác nhận baseline 0 participant, chưa có U1/U2/U3.
2. Bấm Enrol users phía trên; chờ Select users/Assign role tải xong.
3. Để No selection; giữ Student/Now/Unlimited; bấm Enrol users trong modal.
4. Chờ modal đóng, so count và tìm U1 trong Participants.

**Expected result:** Modal đóng; không thêm participant; không hiện lỗi required

## TC-002-002 — Tìm không có kết quả

**Test ID:** TC-002-002  
**Kỹ thuật thiết kế:** ECP  
**Mục tiêu kiểm thử:** Tìm không có kết quả.

**Precondition:** Setup toàn suite thành công; Admin/UI UTC; course riêng, manual bật duy nhất; U1/U2/U3 chưa enrol; Participants có 0 participant trước thao tác.

**Test data:** Course/U1/U2/U3/S của chính TC-002-002 theo đầu ra setup. Search `zz_f002_no_match_20261113`; không chọn user.

**Các bước thực hiện:**

1. Đăng nhập Admin; mở đúng course TC-002-002 theo quy ước trên → Participants; xác nhận baseline 0 participant, chưa có U1/U2/U3.
2. Bấm Enrol users phía trên; chờ Select users/Assign role tải xong.
3. Gõ zz_f002_no_match_20261113 vào Select users; chờ AJAX hoàn tất; đọc No suggestions và No selection.
4. Cancel; kiểm tra Participants.

**Expected result:** `No suggestions`; selection vẫn rỗng; không tạo user mới qua search

## TC-002-003 — Chỉ gõ tên, chưa chọn suggestion

**Test ID:** TC-002-003  
**Kỹ thuật thiết kế:** ECP  
**Mục tiêu kiểm thử:** Chỉ gõ tên, chưa chọn suggestion.

**Precondition:** Setup toàn suite thành công; Admin/UI UTC; course riêng, manual bật duy nhất; U1/U2/U3 chưa enrol; Participants có 0 participant trước thao tác.

**Test data:** Course/U1/U2/U3/S của chính TC-002-003 theo đầu ra setup. Search username U1, có suggestion nhưng không click.

**Các bước thực hiện:**

1. Đăng nhập Admin; mở đúng course TC-002-003 theo quy ước trên → Participants; xác nhận baseline 0 participant, chưa có U1/U2/U3.
2. Bấm Enrol users phía trên; chờ Select users/Assign role tải xong.
3. Gõ username U1, chờ suggestion có đúng email; KHÔNG chọn option.
4. Kiểm tra No selection; submit; tìm U1 trong Participants.

**Expected result:** Cần xác minh: search text không trở thành selection; không enrol U1

## TC-002-004 — Tìm người đã có manual enrolment

**Test ID:** TC-002-004  
**Kỹ thuật thiết kế:** ECP  
**Mục tiêu kiểm thử:** Tìm người đã có manual enrolment.

**Precondition:** Setup toàn suite thành công; Admin/UI UTC; U1 Student Active, start setup −2 ngày, end +7 ngày; U2/U3 chưa enrol; Participants có 1 participant trước thao tác.

**Test data:** Course/U1/U2/U3/S của chính TC-002-004 theo đầu ra setup. Search U1 đã có Student/Active trong chính course.

**Các bước thực hiện:**

1. Đăng nhập Admin; mở đúng course TC-002-004 theo quy ước trên → Participants; xác nhận baseline 1 participant là U1.
2. Bấm Enrol users phía trên; chờ Select users/Assign role tải xong.
3. Gõ username U1 đã enrol bởi setup, chờ AJAX; đọc No suggestions.
4. Cancel; kiểm tra U1 vẫn đúng một dòng Student/Active.

**Expected result:** Không có suggestion cho những user đã khảo sát; không suy ra kết quả gửi request ghi danh trùng

## TC-002-005 — Gán Teacher khi ghi danh mới

**Test ID:** TC-002-005  
**Kỹ thuật thiết kế:** ECP  
**Mục tiêu kiểm thử:** Gán Teacher khi ghi danh mới.

**Precondition:** Setup toàn suite thành công; Admin/UI UTC; course riêng, manual bật duy nhất; U1/U2/U3 chưa enrol; Participants có 0 participant trước thao tác.

**Test data:** Course/U1/U2/U3/S của chính TC-002-005 theo đầu ra setup. U1; Teacher; Now; Unlimited; End tắt.

**Các bước thực hiện:**

1. Đăng nhập Admin; mở đúng course TC-002-005 theo quy ước trên → Participants; xác nhận baseline 0 participant, chưa có U1/U2/U3.
2. Bấm Enrol users phía trên; chờ Select users/Assign role tải xong.
3. Gõ username U1; click suggestion đúng email; chọn Assign role Teacher; giữ Now/Unlimited, end tắt; submit.
4. Kiểm tra role Teacher trong dòng U1.

**Expected result:** Dòng U1 được tạo với role Teacher; không kết luận mọi capability của Teacher

## TC-002-006 — Gán Non-editing teacher

**Test ID:** TC-002-006  
**Kỹ thuật thiết kế:** ECP  
**Mục tiêu kiểm thử:** Gán Non-editing teacher.

**Precondition:** Setup toàn suite thành công; Admin/UI UTC; course riêng, manual bật duy nhất; U1/U2/U3 chưa enrol; Participants có 0 participant trước thao tác.

**Test data:** Course/U1/U2/U3/S của chính TC-002-006 theo đầu ra setup. U1; Non-editing teacher; Now; Unlimited; End tắt.

**Các bước thực hiện:**

1. Đăng nhập Admin; mở đúng course TC-002-006 theo quy ước trên → Participants; xác nhận baseline 0 participant, chưa có U1/U2/U3.
2. Bấm Enrol users phía trên; chờ Select users/Assign role tải xong.
3. Gõ username U1; chọn suggestion đúng email; chọn Assign role Non-editing teacher; giữ Now/Unlimited, end tắt; submit.
4. Đọc role dòng U1.

**Expected result:** Cần xác minh: ghi danh thành công, role đọc lại đúng Non-editing teacher

## TC-002-007 — Gán Manager

**Test ID:** TC-002-007  
**Kỹ thuật thiết kế:** ECP  
**Mục tiêu kiểm thử:** Gán Manager.

**Precondition:** Setup toàn suite thành công; Admin/UI UTC; course riêng, manual bật duy nhất; U1/U2/U3 chưa enrol; Participants có 0 participant trước thao tác.

**Test data:** Course/U1/U2/U3/S của chính TC-002-007 theo đầu ra setup. U1; Manager; Now; Unlimited; End tắt.

**Các bước thực hiện:**

1. Đăng nhập Admin; mở đúng course TC-002-007 theo quy ước trên → Participants; xác nhận baseline 0 participant, chưa có U1/U2/U3.
2. Bấm Enrol users phía trên; chờ Select users/Assign role tải xong.
3. Gõ username U1; chọn suggestion đúng email; chọn Assign role Manager; giữ Now/Unlimited, end tắt; submit.
4. Đọc role dòng U1.

**Expected result:** Cần xác minh: ghi danh thành công, role đọc lại đúng Manager

## TC-002-008 — Thời hạn dương nhỏ nhất

**Test ID:** TC-002-008  
**Kỹ thuật thiết kế:** BVA  
**Mục tiêu kiểm thử:** Thời hạn dương nhỏ nhất.

**Precondition:** Setup toàn suite thành công; Admin/UI UTC; course riêng, manual bật duy nhất; U1/U2/U3 chưa enrol; Participants có 0 participant trước thao tác.

**Test data:** Course/U1/U2/U3/S của chính TC-002-008 theo đầu ra setup. U1; Student; Now; Duration 1 day; End tắt.

**Các bước thực hiện:**

1. Đăng nhập Admin; mở đúng course TC-002-008 theo quy ước trên → Participants; xác nhận baseline 0 participant, chưa có U1/U2/U3.
2. Bấm Enrol users phía trên; chờ Select users/Assign role tải xong.
3. Chọn suggestion U1; Student; Show more; Now; duration 1 days; end Enable tắt; submit.
4. Mở Edit enrolment dòng U1; đọc start/end, so chênh lệch 1 ngày UTC; Cancel.

**Expected result:** Enrol thành công; đọc lại end cách start một ngày

## TC-002-009 — Sát biên dưới duration

**Test ID:** TC-002-009  
**Kỹ thuật thiết kế:** BVA  
**Mục tiêu kiểm thử:** Sát biên dưới duration.

**Precondition:** Setup toàn suite thành công; Admin/UI UTC; course riêng, manual bật duy nhất; U1/U2/U3 chưa enrol; Participants có 0 participant trước thao tác.

**Test data:** Course/U1/U2/U3/S của chính TC-002-009 theo đầu ra setup. U1; Student; Now; Duration 2 days; End tắt.

**Các bước thực hiện:**

1. Đăng nhập Admin; mở đúng course TC-002-009 theo quy ước trên → Participants; xác nhận baseline 0 participant, chưa có U1/U2/U3.
2. Bấm Enrol users phía trên; chờ Select users/Assign role tải xong.
3. Chọn suggestion U1; Student; Show more; Now; duration 2 days; end tắt; submit.
4. Mở Edit enrolment dòng U1, đọc start/end; so 2 ngày UTC; Cancel.

**Expected result:** Cần xác minh: end = start + 2 ngày theo múi giờ course/user đã cố định

## TC-002-010 — Sát biên trên duration

**Test ID:** TC-002-010  
**Kỹ thuật thiết kế:** BVA  
**Mục tiêu kiểm thử:** Sát biên trên duration.

**Precondition:** Setup toàn suite thành công; Admin/UI UTC; course riêng, manual bật duy nhất; U1/U2/U3 chưa enrol; Participants có 0 participant trước thao tác.

**Test data:** Course/U1/U2/U3/S của chính TC-002-010 theo đầu ra setup. U1; Student; Now; Duration 364 days; End tắt.

**Các bước thực hiện:**

1. Đăng nhập Admin; mở đúng course TC-002-010 theo quy ước trên → Participants; xác nhận baseline 0 participant, chưa có U1/U2/U3.
2. Bấm Enrol users phía trên; chờ Select users/Assign role tải xong.
3. Chọn suggestion U1; Student; Show more; Now; duration 364 days; end tắt; submit.
4. Mở Edit enrolment dòng U1, đọc start/end; so 364 ngày UTC; Cancel.

**Expected result:** Cần xác minh: end = start + 364 ngày, không bị cắt về giá trị khác

## TC-002-011 — Biên trên duration UI

**Test ID:** TC-002-011  
**Kỹ thuật thiết kế:** BVA  
**Mục tiêu kiểm thử:** Biên trên duration UI.

**Precondition:** Setup toàn suite thành công; Admin/UI UTC; course riêng, manual bật duy nhất; U1/U2/U3 chưa enrol; Participants có 0 participant trước thao tác.

**Test data:** Course/U1/U2/U3/S của chính TC-002-011 theo đầu ra setup. U1; Student; Now; Duration 365 days; End tắt.

**Các bước thực hiện:**

1. Đăng nhập Admin; mở đúng course TC-002-011 theo quy ước trên → Participants; xác nhận baseline 0 participant, chưa có U1/U2/U3.
2. Bấm Enrol users phía trên; chờ Select users/Assign role tải xong.
3. Chọn suggestion U1; Student; Show more; Now; duration 365 days; end tắt; submit.
4. Mở Edit enrolment dòng U1, đọc start/end; so 365 ngày UTC; Cancel.

**Expected result:** Cần xác minh: end = start + 365 ngày; đây là biên UI, chưa chứng minh giới hạn server

## TC-002-012 — End ngay trước start

**Test ID:** TC-002-012  
**Kỹ thuật thiết kế:** BVA  
**Mục tiêu kiểm thử:** End ngay trước start.

**Precondition:** Setup toàn suite thành công; Admin/UI UTC; course riêng, manual bật duy nhất; U1/U2/U3 chưa enrol; Participants có 0 participant trước thao tác.

**Test data:** Course/U1/U2/U3/S của chính TC-002-012 theo đầu ra setup. U1; Student; custom start S; Unlimited trước khi bật End; E=S−1 phút.

**Các bước thực hiện:**

1. Đăng nhập Admin; mở đúng course TC-002-012 theo quy ước trên → Participants; xác nhận baseline 0 participant, chưa có U1/U2/U3.
2. Bấm Enrol users phía trên; chờ Select users/Assign role tải xong.
3. Chọn U1; Student; Show more; Choose; nhập S bằng Day/Month/Year/Hour/Minute; Unlimited; bật end Enable; nhập E = S − 1 phút.
4. Submit; đọc lỗi; kiểm tra không có U1 trong Participants.

**Expected result:** Cần xác minh tại đúng biên: `Invalid enrolment duration`, không thêm U1

## TC-002-013 — End bằng start

**Test ID:** TC-002-013  
**Kỹ thuật thiết kế:** BVA  
**Mục tiêu kiểm thử:** End bằng start.

**Precondition:** Setup toàn suite thành công; Admin/UI UTC; course riêng, manual bật duy nhất; U1/U2/U3 chưa enrol; Participants có 0 participant trước thao tác.

**Test data:** Course/U1/U2/U3/S của chính TC-002-013 theo đầu ra setup. U1; Student; custom start S; Unlimited trước khi bật End; E=S.

**Các bước thực hiện:**

1. Đăng nhập Admin; mở đúng course TC-002-013 theo quy ước trên → Participants; xác nhận baseline 0 participant, chưa có U1/U2/U3.
2. Bấm Enrol users phía trên; chờ Select users/Assign role tải xong.
3. Chọn U1; Student; Show more; Choose S; Unlimited; bật end; nhập E bằng S.
4. Submit; ghi thông báo và việc có tạo U1 không; nếu tạo, mở Edit enrolment đọc S/E.
5. Khảo sát oracle, chưa tự chấm PASS.

**Expected result:** Cần xác minh Moodle chấp nhận hay từ chối E = S; ghi nhận thông báo và participant, nếu tạo thì đọc lại start/end; chưa chốt oracle pass/fail

**Đánh giá:** Oracle E=S chưa chốt; ghi thông báo, count và ngày đã lưu nếu có. Giữ OBSERVED/chưa kết luận PASS nghiệp vụ, kể cả các lệnh Recorder đều xanh.

## TC-002-014 — End ngay sau start

**Test ID:** TC-002-014  
**Kỹ thuật thiết kế:** BVA  
**Mục tiêu kiểm thử:** End ngay sau start.

**Precondition:** Setup toàn suite thành công; Admin/UI UTC; course riêng, manual bật duy nhất; U1/U2/U3 chưa enrol; Participants có 0 participant trước thao tác.

**Test data:** Course/U1/U2/U3/S của chính TC-002-014 theo đầu ra setup. U1; Student; custom start S; Unlimited trước khi bật End; E=S+1 phút.

**Các bước thực hiện:**

1. Đăng nhập Admin; mở đúng course TC-002-014 theo quy ước trên → Participants; xác nhận baseline 0 participant, chưa có U1/U2/U3.
2. Bấm Enrol users phía trên; chờ Select users/Assign role tải xong.
3. Chọn U1; Student; Show more; Choose S; Unlimited; bật end; nhập E = S + 1 phút.
4. Submit; tìm U1; mở Edit enrolment đọc lại S/E và chênh lệch một phút; Cancel.

**Expected result:** Cần xác minh: tạo enrolment và lưu đúng khoảng một phút; không dùng access hiện tại để kết luận vì S ở tương lai

## TC-002-015 — Chặn khoảng thời gian đảo ngược

**Test ID:** TC-002-015  
**Kỹ thuật thiết kế:** Decision Table  
**Mục tiêu kiểm thử:** Chặn khoảng thời gian đảo ngược.

**Precondition:** Setup toàn suite thành công; Admin/UI UTC; course riêng, manual bật duy nhất; U1/U2/U3 chưa enrol; Participants có 0 participant trước thao tác.

**Test data:** Course/U1/U2/U3/S của chính TC-002-015 theo đầu ra setup. U1; Student; start 15/11/2027 12:00 UTC; end 15/11/2026 12:00 UTC; Unlimited trước khi bật End.

**Các bước thực hiện:**

1. Đăng nhập Admin; mở đúng course TC-002-015 theo quy ước trên → Participants; xác nhận baseline 0 participant, chưa có U1/U2/U3.
2. Bấm Enrol users phía trên; chờ Select users/Assign role tải xong.
3. Chọn U1; Student; Show more; Choose start 15/11/2027 12:00 UTC; Unlimited; bật end 15/11/2026 12:00 UTC.
4. Submit; đọc Invalid enrolment duration; kiểm tra không có U1 trong Participants.

**Expected result:** `Invalid enrolment duration`; U1 không được thêm vào Participants

## TC-002-016 — Active đang có hiệu lực

**Test ID:** TC-002-016  
**Kỹ thuật thiết kế:** Decision Table  
**Mục tiêu kiểm thử:** Active đang có hiệu lực.

**Precondition:** Setup toàn suite thành công; Admin/UI UTC; U1 Student Active, start setup −2 ngày, end +7 ngày; U2/U3 chưa enrol; Participants có 1 participant trước thao tác.

**Test data:** Course/U1/U2/U3/S của chính TC-002-016 theo đầu ra setup. U1 Student/Active; start=t0−2 ngày; end=t0+7 ngày; kiểm tra khi start < hiện tại < end.

**Các bước thực hiện:**

1. Đăng nhập Admin; mở đúng course TC-002-016 theo quy ước trên → Participants; xác nhận baseline 1 participant là U1.
2. Không mở Enrol users.
3. Đọc dòng U1 Student/Active và thời hạn trong Edit enrolment; Cancel.
4. Đăng xuất admin, đăng nhập U1; mở course URL từ setup; kiểm tra nội dung course xuất hiện, không bị đưa sang Enrolment options.
5. Đăng xuất U1, đăng nhập lại Admin; giữ fixture để tiếp tục các TC khác, không cleanup riêng TC.

**Expected result:** Student truy cập được course

## TC-002-017 — Suspended đang trong thời hạn

**Test ID:** TC-002-017  
**Kỹ thuật thiết kế:** Decision Table  
**Mục tiêu kiểm thử:** Suspended đang trong thời hạn.

**Precondition:** Setup toàn suite thành công; Admin/UI UTC; U1 Student Suspended, start setup −2 ngày, end +7 ngày; Participants có 1 participant trước thao tác.

**Test data:** Course/U1/U2/U3/S của chính TC-002-017 theo đầu ra setup. U1 Student/Suspended; start=t0−2 ngày; end=t0+7 ngày, chưa hết hạn.

**Các bước thực hiện:**

1. Đăng nhập Admin; mở đúng course TC-002-017 theo quy ước trên → Participants; xác nhận baseline 1 participant là U1.
2. Không mở Enrol users.
3. Đọc dòng U1 Student/Suspended và thời hạn chưa hết; Cancel Edit enrolment.
4. Đăng xuất admin, đăng nhập U1; mở course; đọc Enrolment options và thông báo chặn.
5. Đăng xuất U1, đăng nhập lại Admin; giữ fixture để tiếp tục các TC khác, không cleanup riêng TC.

**Expected result:** Student bị chặn, đến Enrolment options với `You cannot enrol yourself in this course.`; ghi danh/role vẫn còn

## TC-002-018 — Active nhưng chưa bắt đầu

**Test ID:** TC-002-018  
**Kỹ thuật thiết kế:** Decision Table  
**Mục tiêu kiểm thử:** Active nhưng chưa bắt đầu.

**Precondition:** Setup toàn suite thành công; Admin/UI UTC; course riêng, manual bật duy nhất; U1/U2/U3 chưa enrol; Participants có 0 participant trước thao tác.

**Test data:** Course/U1/U2/U3/S của chính TC-002-018 theo đầu ra setup. U1; Student; start=S còn tương lai; end=S+1 ngày; Unlimited trước khi bật End.

**Các bước thực hiện:**

1. Đăng nhập Admin; mở đúng course TC-002-018 theo quy ước trên → Participants; xác nhận baseline 0 participant, chưa có U1/U2/U3.
2. Bấm Enrol users phía trên; chờ Select users/Assign role tải xong.
3. Chọn U1; Student; Show more; Choose S; Unlimited; bật end E = S + 1 ngày.
4. Submit; đọc lại S/E.
5. Đăng xuất admin, đăng nhập U1; mở course và ghi quyền truy cập/message thực tế.
6. Đăng xuất U1, đăng nhập lại Admin; giữ fixture để tiếp tục các TC khác, không cleanup riêng TC.

**Expected result:** Cần xác minh: enrolment được lưu nhưng Student chưa truy cập được; ghi nhận status/message thật

## TC-002-019 — Active nhưng đã hết hạn

**Test ID:** TC-002-019  
**Kỹ thuật thiết kế:** Decision Table  
**Mục tiêu kiểm thử:** Active nhưng đã hết hạn.

**Precondition:** Setup toàn suite thành công; Admin/UI UTC; U1 Student Active, start setup −2 ngày, end −1 giờ; Participants có 1 participant trước thao tác.

**Test data:** Course/U1/U2/U3/S của chính TC-002-019 theo đầu ra setup. U1 Status Active; start=t0−2 ngày; end=t0−1 giờ, đã hết hạn.

**Các bước thực hiện:**

1. Đăng nhập Admin; mở đúng course TC-002-019 theo quy ước trên → Participants; xác nhận baseline 1 participant là U1.
2. Không mở Enrol users.
3. Mở Edit enrolment U1; đọc Status Active, end = setup − 1 giờ; Cancel.
4. Ghi status trong Participants.
5. Đăng xuất admin, đăng nhập U1; mở course; ghi kết quả access thực tế.
6. Đăng xuất U1, đăng nhập lại Admin; giữ fixture để tiếp tục các TC khác, không cleanup riêng TC.

**Expected result:** Cần xác minh Student bị chặn; đọc status, không tự động đổi kỳ vọng thành Suspended

## TC-002-020 — Không giới hạn thời hạn

**Test ID:** TC-002-020  
**Kỹ thuật thiết kế:** Decision Table  
**Mục tiêu kiểm thử:** Không giới hạn thời hạn.

**Precondition:** Setup toàn suite thành công; Admin/UI UTC; course riêng, manual bật duy nhất; U1/U2/U3 chưa enrol; Participants có 0 participant trước thao tác.

**Test data:** Course/U1/U2/U3/S của chính TC-002-020 theo đầu ra setup. U1; Student; Now; Unlimited; End tắt.

**Các bước thực hiện:**

1. Đăng nhập Admin; mở đúng course TC-002-020 theo quy ước trên → Participants; xác nhận baseline 0 participant, chưa có U1/U2/U3.
2. Bấm Enrol users phía trên; chờ Select users/Assign role tải xong.
3. Chọn U1; Student; Show more; Now; Unlimited; end Enable tắt; submit.
4. Mở Edit enrolment U1, đọc end Enable tắt; Cancel.
5. Đăng nhập U1; mở course; kiểm tra access.
6. Đăng xuất U1, đăng nhập lại Admin; giữ fixture để tiếp tục các TC khác, không cleanup riêng TC.

**Expected result:** Cần xác minh: ghi danh Student và Edit enrolment không có end hiệu lực; Student vào được course

## TC-002-021 — Duration và explicit end cùng được đặt

**Test ID:** TC-002-021  
**Kỹ thuật thiết kế:** Decision Table  
**Mục tiêu kiểm thử:** Duration và explicit end cùng được đặt.

**Precondition:** Setup toàn suite thành công; Admin/UI UTC; course riêng, manual bật duy nhất; U1/U2/U3 chưa enrol; Participants có 0 participant trước thao tác.

**Test data:** Course/U1/U2/U3/S của chính TC-002-021 theo đầu ra setup. U1; Student; start=S; chọn Duration 1 day lúc End tắt, sau đó bật End=S+3 ngày.

**Các bước thực hiện:**

1. Đăng nhập Admin; mở đúng course TC-002-021 theo quy ước trên → Participants; xác nhận baseline 0 participant, chưa có U1/U2/U3.
2. Bấm Enrol users; tìm và chọn suggestion đúng email U1; giữ Student.
3. Show more; tắt End Enable nếu đang bật; Starting from Choose..., nhập đủ S.
4. Chọn Duration 1 day khi End còn tắt.
5. Click bật End Enable; kiểm tra Duration bị disabled và các select ngày End được mở; nhập E=S+3 ngày.
6. Submit; kiểm tra đúng một dòng U1.
7. Mở Edit enrolment dòng U1; đọc lại start=S và end=S+3 ngày, không phải S+1 ngày; Cancel.

**Expected result:** End bật khóa Duration; enrol thành công, đọc lại start=S và end=S+3 ngày (explicit end ưu tiên)

## TC-002-022 — Luồng enrol nhiều người

**Test ID:** TC-002-022  
**Kỹ thuật thiết kế:** Use-case  
**Mục tiêu kiểm thử:** Luồng enrol nhiều người.

**Precondition:** Setup toàn suite thành công; Admin/UI UTC; course riêng, manual bật duy nhất; U1/U2/U3 chưa enrol; Participants có 0 participant trước thao tác.

**Test data:** Course/U1/U2/U3/S của chính TC-002-022 theo đầu ra setup. U1 và U2; Student; Now; Duration 1 day; End tắt; một lần submit.

**Các bước thực hiện:**

1. Đăng nhập Admin; mở đúng course TC-002-022 theo quy ước trên → Participants; xác nhận baseline 0 participant, chưa có U1/U2/U3.
2. Bấm Enrol users phía trên; chờ Select users/Assign role tải xong.
3. Chọn suggestion U1, gõ rồi chọn suggestion U2; kiểm tra hai selected items; Student; Show more; Now; 1 days; end tắt; submit một lần.
4. Kiểm tra từng U1/U2 đúng một dòng Student; mở Edit enrolment từng người đọc thời hạn một ngày.

**Expected result:** Cần xác minh cả hai có đúng role/thời hạn, không bỏ sót hoặc tạo trùng

## TC-002-023 — Hủy sau khi chọn user

**Test ID:** TC-002-023  
**Kỹ thuật thiết kế:** Use-case  
**Mục tiêu kiểm thử:** Hủy sau khi chọn user.

**Precondition:** Setup toàn suite thành công; Admin/UI UTC; course riêng, manual bật duy nhất; U1/U2/U3 chưa enrol; Participants có 0 participant trước thao tác.

**Test data:** Course/U1/U2/U3/S của chính TC-002-023 theo đầu ra setup. U1; Teacher; Duration 2 days; hủy; mở lại để đối chiếu No selection/Student/Unlimited.

**Các bước thực hiện:**

1. Đăng nhập Admin; mở đúng course TC-002-023 theo quy ước trên → Participants; xác nhận baseline 0 participant, chưa có U1/U2/U3.
2. Bấm Enrol users phía trên; chờ Select users/Assign role tải xong.
3. Chọn U1; Assign role Teacher; Show more; duration 2 days; Cancel.
4. Kiểm tra không có U1; mở Enrol users lại; ghi selected items, role và duration có reset về No selection/Student/Unlimited không; Cancel.

**Expected result:** Cần xác minh không tạo U1, không lưu cấu hình nháp của lần hủy

## TC-002-024 — Sửa dữ liệu sau lỗi thời gian

**Test ID:** TC-002-024  
**Kỹ thuật thiết kế:** Use-case  
**Mục tiêu kiểm thử:** Sửa dữ liệu sau lỗi thời gian.

**Precondition:** Setup toàn suite thành công; Admin/UI UTC; course riêng, manual bật duy nhất; U1/U2/U3 chưa enrol; Participants có 0 participant trước thao tác.

**Test data:** Course/U1/U2/U3/S của chính TC-002-024 theo đầu ra setup. U1; Student; start=S; lần đầu E=S−1 phút; lần sửa E=S+1 ngày; Unlimited trước khi bật End.

**Các bước thực hiện:**

1. Đăng nhập Admin; mở đúng course TC-002-024 theo quy ước trên → Participants; xác nhận baseline 0 participant, chưa có U1/U2/U3.
2. Bấm Enrol users phía trên; chờ Select users/Assign role tải xong.
3. Chọn U1; Choose S; Unlimited; end Enable bật, E = S − 1 phút; submit.
4. Ghi lỗi, kiểm tra không có U1.
5. Nếu modal đóng, mở lại và chọn U1; nhập S và E = S + 1 ngày; submit.
6. Kiểm tra đúng một U1 và đọc lại S/E.

**Expected result:** Cần xác minh cách UI phục hồi sau lỗi và ghi danh đúng một lần với thời gian mới; kiểm tra không có bản ghi từ lần lỗi

## TC-002-025 — Tạm ngưng rồi khôi phục

**Test ID:** TC-002-025  
**Kỹ thuật thiết kế:** Use-case  
**Mục tiêu kiểm thử:** Tạm ngưng rồi khôi phục.

**Precondition:** Setup toàn suite thành công; Admin/UI UTC; U1 Student Active, start setup −2 ngày, end +7 ngày; U2/U3 chưa enrol; Participants có 1 participant trước thao tác.

**Test data:** Course/U1/U2/U3/S của chính TC-002-025 theo đầu ra setup. U1 Student/Active đang hiệu lực; chuỗi Suspended → kiểm tra Student → Active → kiểm tra Student.

**Các bước thực hiện:**

1. Đăng nhập Admin; mở đúng course TC-002-025 theo quy ước trên → Participants; xác nhận baseline 1 participant là U1.
2. Không mở Enrol users.
3. Edit enrolment U1 → Status Suspended → Save changes; kiểm tra còn dòng U1/Student.
4. Đăng nhập U1, mở course, ghi bị chặn.
5. Đăng nhập admin; Edit enrolment U1 → Active → Save changes.
6. Đăng nhập lại U1, mở course mới, kiểm tra access phục hồi.
7. Đăng xuất U1, đăng nhập lại Admin; giữ fixture để tiếp tục các TC khác, không cleanup riêng TC.

**Expected result:** Còn participant/role; bị chặn khi Suspended; truy cập lại sau Active

## TC-002-026 — Khôi phục điểm cũ khi re-enrol

**Test ID:** TC-002-026  
**Kỹ thuật thiết kế:** Use-case  
**Mục tiêu kiểm thử:** Khôi phục điểm cũ khi re-enrol.

**Precondition:** Setup toàn suite thành công; Admin/UI UTC; U1/U2 có lịch sử điểm 73, chưa enrol và không grade hiện hành; U3 không lịch sử; grade history bật; Participants có 0 participant trước thao tác.

**Test data:** Course/U1/U2/U3/S của chính TC-002-026 theo đầu ra setup. Grade item `F002 Recovery 73`, thang 0–100; U1/U2 có lịch sử 73, U3 không lịch sử. Recovery: U1 ON, U2 OFF, U3 ON; Student/Now/Unlimited, End tắt.

**Các bước thực hiện:**

1. Đăng nhập Admin; mở đúng course TC-002-026 theo quy ước trên → Participants; xác nhận baseline 0 participant, chưa có U1/U2/U3.
2. Bấm Enrol users phía trên; chờ Select users/Assign role tải xong.
3. Chọn U1; Student/Now/Unlimited; Show more; bật Recover user's old grades if possible; submit.
4. Mở lại form, enrol U2 có lịch sử với recovery TẮT.
5. Enrol U3 không lịch sử với recovery BẬT.
6. Mở Grades → Grader report, tìm cột F002 Recovery 73; ghi điểm U1/U2/U3, so với 73/không khôi phục/không có điểm.
7. Không coi checkbox là kết quả.

**Expected result:** Cần xác minh điểm cũ được khôi phục khi có thể; so với điểm đã biết và đối chứng bỏ checkbox; không chỉ assert checkbox. Đối chiếu cột F002 Recovery 73: U1=73.00; U2 và U3 không có điểm (−).

## TC-002-027 — Ghi danh từ Course start

**Test ID:** TC-002-027  
**Kỹ thuật thiết kế:** Use-case  
**Mục tiêu kiểm thử:** Ghi danh từ Course start.

**Precondition:** Setup toàn suite thành công; Admin/UI UTC; course riêng, manual bật duy nhất; U1/U2/U3 chưa enrol; Participants có 0 participant trước thao tác.

**Test data:** Course/U1/U2/U3/S của chính TC-002-027 theo đầu ra setup. U1; Student; Starting from=Course start (hôm qua 00:00 UTC); Duration 1 day; End tắt.

**Các bước thực hiện:**

1. Đăng nhập Admin; mở đúng course TC-002-027 theo quy ước trên → Participants; xác nhận baseline 0 participant, chưa có U1/U2/U3.
2. Bấm Enrol users phía trên; chờ Select users/Assign role tải xong.
3. Chọn U1; Student; Show more; Course start; 1 days; end tắt.
4. Ghi ngày Course start trên option; submit; mở Edit enrolment đọc start/end.
5. So start = hôm qua 00:00 UTC, end +1 ngày; không dùng access để kết luận tạo thất bại.

**Expected result:** Cần xác minh start lưu theo ngày bắt đầu course và end tương ứng; nếu quá hạn phải phân biệt tạo thành công với access

## TC-002-028 — Ghi danh từ Today

**Test ID:** TC-002-028  
**Kỹ thuật thiết kế:** Use-case  
**Mục tiêu kiểm thử:** Ghi danh từ Today.

**Precondition:** Setup toàn suite thành công; Admin/UI UTC; course riêng, manual bật duy nhất; U1/U2/U3 chưa enrol; Participants có 0 participant trước thao tác.

**Test data:** Course/U1/U2/U3/S của chính TC-002-028 theo đầu ra setup. U1; Student; Starting from=Today (00:00 UTC ngày kiểm tra); Duration 1 day; End tắt.

**Các bước thực hiện:**

1. Đăng nhập Admin; mở đúng course TC-002-028 theo quy ước trên → Participants; xác nhận baseline 0 participant, chưa có U1/U2/U3.
2. Bấm Enrol users phía trên; chờ Select users/Assign role tải xong.
3. Chọn U1; Student; Show more; Today; 1 days; end tắt; ghi ngày giờ UTC thao tác.
4. Submit; mở Edit enrolment đọc start/end; so start 00:00 Today UTC và end ngày tiếp theo, phân biệt với Now; Cancel.

**Expected result:** Cần xác minh start là đầu ngày hiển thị và end sau một ngày; đối chiếu Now để tránh lấy thời điểm submit làm oracle

