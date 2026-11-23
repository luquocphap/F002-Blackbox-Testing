# F002 – Enrol User

## 1. Môi trường

Moodle local chạy trong Docker tại `http://127.0.0.1:9501`. Dùng Chrome với Katalon Recorder cho bản playback hoặc Selenium theo [README Project 3](README-project3.md). Moodle dùng English, có category ID 1, Manual enrolments bật, các role mặc định và grade history bật. Đặt timezone Admin là UTC qua Profile → Edit profile; ghi giá trị cũ để khôi phục sau run. Không chạy qua mốc đổi ngày UTC.

## 2. Setup toàn bộ fixtures

Chạy từ `F002-deliver/` trên Ubuntu hoặc WSL. Cài Python 3.10+, Chrome/Chromium và `python -m pip install -r requirements.txt`. Script Python dùng REST và trang quản trị Moodle để ghi dữ liệu, cùng các truy vấn PostgreSQL chỉ đọc để xác minh fixture. Môi trường Docker cần có `psql` trong container PostgreSQL.

Trên **Moodle local**, bật Web services và giao thức REST. Trong *Site administration → Server → Web services → External services*, tạo một service dành cho fixture và thêm các hàm sau:

- `core_course_create_courses`, `core_course_get_courses_by_field`, `core_course_delete_courses`
- `core_user_create_users`, `core_user_get_users_by_field`, `core_user_delete_users`
- `enrol_manual_enrol_users`, `enrol_manual_unenrol_users`

Ở *Manage tokens*, cấp token cho tài khoản quản trị local và service vừa tạo. Giới hạn token vào tài khoản/service trên môi trường thử nghiệm.

```bash
export F002_ADMIN_USER=admin
read -rsp 'Moodle REST token: ' F002_MOODLE_WS_TOKEN
export F002_MOODLE_WS_TOKEN
printf '\n'
read -rsp 'Moodle Admin password: ' F002_ADMIN_PASSWORD
export F002_ADMIN_PASSWORD
printf '\n'
read -rsp 'Mật khẩu các user fixture: ' F002_STUDENT_PASSWORD
export F002_STUDENT_PASSWORD
printf '\n'
mkdir -p .project3-local
python scripts/setup-all.py > .project3-local/setup.txt &&
tail -1 .project3-local/setup.txt
```

Script mặc định dùng `F002_MOODLE_URL=http://127.0.0.1:9501`, `F002_DB_CONTAINER=demo-db-1`, `F002_DB_NAME=moodle`, `F002_DB_USER=moodle` và `F002_DB_PREFIX=mdl_`. Đặt các biến tương ứng nếu máy bạn dùng tên khác. PostgreSQL trong container cần cho phép user cấu hình truy cập bằng lệnh `psql`. Có thể đặt `F002_CHROME_BINARY` và `F002_CHROMEDRIVER` nếu dùng Chrome ở đường dẫn riêng.

Chỉ chạy test khi setup trả exit code 0 và báo `Setup completed: 28/28 test cases.`. Mỗi dòng TC in `course`, `courseid`, `username_prefix`, `S` (UTC) và `prepared_at`. Setup kiểm tra các điều kiện đầu vào của [Testcases.md](Testcases.md), gồm enrolment theo thời gian và lịch sử điểm của TC-002-026. Setup lần hai kiểm tra lại dữ liệu hiện có. Để reset, chạy cleanup trước.

Giữ manifest trong `.project3-local/fixtures/` đến khi cleanup hoàn tất. Nếu dùng `--state-dir`, dùng cùng thư mục cho cả setup và cleanup. Khi chuyển từ phiên bản PHP, dùng cleanup của phiên bản cũ trên các fixture cũ trước khi dùng bộ Python. Manifest cũ nằm trong Moodle dataroot, còn bộ Python lưu manifest riêng ở máy chạy lệnh.

## 3. Đăng nhập Admin

Đăng nhập Admin trước trong đúng tab Chrome playback, mở Dashboard. File Recorder được giữ nguyên theo bản bàn giao: các TC access dùng **Log in as** và khôi phục bằng tài khoản demo local `admin` / `admin`; chỉ chạy bản này trên môi trường local có đúng tài khoản đó. Tài khoản fixture dành cho kiểm thử có mật khẩu `F002!Local2026x`.

## 4. Import và chạy

Katalon Recorder → **Open Test Suites** → chọn `F002_Enrol_User.krecorder` → xác nhận đúng 28 TC (001–028) → chọn tab Moodle → **Play Test Suite / Play Suite**. Không chạy đồng thời suite hoặc setup/cleanup khác. Quy trình thủ công độc lập nằm trong [Testcases.md](Testcases.md).

## 5. Ghi kết quả

Ghi PASS/FAIL từng TC theo toàn bộ expected result, giữ lỗi verify dù lệnh cuối xanh. Khi lỗi, lưu TC ID, bước/command, actual so với expected, Log/Variables của Recorder và screenshot trang lỗi. Thiếu fixture/session là BLOCKED. **TC-013 chưa chốt oracle:** ghi OBSERVED và actual, không tự gán PASS nghiệp vụ chỉ vì Recorder xanh. Gói này chỉ được kiểm tra tĩnh, không có kết quả chạy mới được gán sẵn.

## 6. Cleanup

Sau khi lưu bằng chứng và đăng xuất tài khoản fixture, chạy:

```bash
python scripts/cleanup-all.py
```

Cần exit code 0 và `Cleanup completed: 28/28 test cases.` Con số này là số TC xử lý thành công, gồm TC chưa có manifest (bỏ qua an toàn); không quét/xóa tài nguyên thiếu ownership. Nếu lỗi, giữ manifest để retry; không xóa manifest thủ công. Khôi phục timezone Admin ban đầu.

## 7. Reset để chạy lại từ đầu

Lưu kết quả, dừng suite, rồi chạy lần lượt; chỉ tiếp tục nếu lệnh trước thành công:

```bash
python scripts/cleanup-all.py
# Kiểm tra cleanup thành công trước khi chạy tiếp.
python scripts/setup-all.py
```

Chờ `Setup completed: 28/28 test cases.`, lấy dữ liệu/token mới và đăng nhập Admin trước lượt mới. Không reset giữa các TC của cùng một lượt.
