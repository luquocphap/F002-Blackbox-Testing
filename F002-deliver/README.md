# F002 – Enrol User

## 1. Môi trường

Docker có container `demo-webserver-1`; Moodle tại `http://127.0.0.1:9501`, cài ở `/var/www/site/moodle`; Chrome có Katalon Recorder. Moodle dùng English, có category ID 1, Manual enrolments bật, các role mặc định và grade history bật. Đặt timezone Admin là UTC qua Profile → Edit profile; ghi giá trị cũ để khôi phục sau run. Không chạy qua mốc đổi ngày UTC.

## 2. Setup toàn bộ fixtures

Mở terminal Ubuntu trong folder `F002-deliver/`, chạy:

```bash
docker exec demo-webserver-1 mkdir -p /tmp/f002-deliver
tar -C scripts -cf - fixture.php setup-all.php cleanup-all.php | docker exec -i demo-webserver-1 tar -xf - -C /tmp/f002-deliver
docker exec demo-webserver-1 ls -la /tmp/f002-deliver
docker exec demo-webserver-1 php -l /tmp/f002-deliver/fixture.php
docker exec demo-webserver-1 php -l /tmp/f002-deliver/setup-all.php
docker exec demo-webserver-1 php -l /tmp/f002-deliver/cleanup-all.php
```

Chỉ tiếp tục khi thấy đủ ba file PHP và cả ba lệnh lint báo `No syntax errors detected`. Nếu bất kỳ bước nào lỗi, dừng trước setup. `/tmp` trong container là vùng tạm; sau khi container khởi động lại, cần chuyển lại scripts và lint trước khi chạy.

```bash
docker exec demo-webserver-1 php /tmp/f002-deliver/setup-all.php
```

Chỉ chạy test khi exit code 0 và thấy `Setup completed: 28/28 test cases.` Setup tự kiểm tra precondition của cả 28 TC; mỗi dòng TC in `course`, `courseid`, `username_prefix`, `S` (UTC) và `prepared_at`. Trong [Testcases.md](Testcases.md), ký hiệu `tests[TC-ID].fixture` chỉ bộ dữ liệu tương ứng; bản rút gọn in trực tiếp các trường này, không xuất JSON kết quả. Nếu lỗi, terminal ghi TC/nguyên nhân và exit code khác 0.

Chỉ lưu manifest ownership tối thiểu trong `$CFG->dataroot/f002-fixtures` để nhận diện tài nguyên và dọn setup dở dang; không sinh log/report/history. Giữ manifest đến khi cleanup; cùng Moodle dataroot dùng chung fixtures. Setup chạy lại không tạo trùng hoặc reset dữ liệu đã đổi; nếu baseline sai, chạy cleanup rồi setup. Bản này đọc được manifest cũ; cleanup thành công xóa manifest, không giữ lịch sử.

## 3. Đăng nhập Admin

Đăng nhập Admin trước trong đúng tab Chrome playback, mở Dashboard. File Recorder được giữ nguyên theo bản bàn giao: các TC access dùng **Log in as** và khôi phục bằng tài khoản demo local `admin` / `admin`; chỉ chạy bản này trên môi trường local có đúng tài khoản đó. Tài khoản fixture dành cho kiểm thử có mật khẩu `F002!Local2026x`.

## 4. Import và chạy

Katalon Recorder → **Open Test Suites** → chọn `F002_Enrol_User.krecorder` → xác nhận đúng 28 TC (001–028) → chọn tab Moodle → **Play Test Suite / Play Suite**. Không chạy đồng thời suite hoặc setup/cleanup khác. Quy trình thủ công độc lập nằm trong [Testcases.md](Testcases.md).

## 5. Ghi kết quả

Ghi PASS/FAIL từng TC theo toàn bộ expected result, giữ lỗi verify dù lệnh cuối xanh. Khi lỗi, lưu TC ID, bước/command, actual so với expected, Log/Variables của Recorder và screenshot trang lỗi. Thiếu fixture/session là BLOCKED. **TC-013 chưa chốt oracle:** ghi OBSERVED và actual, không tự gán PASS nghiệp vụ chỉ vì Recorder xanh. Gói này chỉ được kiểm tra tĩnh, không có kết quả chạy mới được gán sẵn.

## 6. Cleanup

Sau khi lưu bằng chứng và đăng xuất tài khoản fixture, chạy:

```bash
docker exec demo-webserver-1 php /tmp/f002-deliver/cleanup-all.php
```

Cần exit code 0 và `Cleanup completed: 28/28 test cases.` Con số này là số TC xử lý thành công, gồm TC chưa có manifest (bỏ qua an toàn); không quét/xóa tài nguyên thiếu ownership. Nếu lỗi, giữ manifest để retry; không xóa manifest thủ công. Khôi phục timezone Admin ban đầu.

## 7. Reset để chạy lại từ đầu

Lưu kết quả, dừng suite, rồi chạy lần lượt; chỉ tiếp tục nếu lệnh trước thành công:

```bash
docker exec demo-webserver-1 php /tmp/f002-deliver/cleanup-all.php
# Kiểm tra cleanup thành công trước khi chạy tiếp.
docker exec demo-webserver-1 php /tmp/f002-deliver/setup-all.php
```

Chờ `Setup completed: 28/28 test cases.`, lấy dữ liệu/token mới và đăng nhập Admin trước lượt mới. Không reset giữa các TC của cùng một lượt.
