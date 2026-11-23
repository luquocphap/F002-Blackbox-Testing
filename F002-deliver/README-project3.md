# Project 3 — Enrol User với Selenium

Cả hai level dùng cùng workflow trong `automation.py` và chạy đủ TC-002-001 đến TC-002-028 trong [Testcases.md](Testcases.md). Mỗi level có `test_data.csv` chứa input và các cột `expected_*`. Ví dụ, dòng TC-002-005 yêu cầu chọn U1, gán Teacher và kiểm tra tổng cộng một participant, đúng email U1, role Teacher và trạng thái Active.

- **Level 1** đọc dữ liệu từ [level1/test_data.csv](level1/test_data.csv). URL và locator nằm trong [level1/ui.py](level1/ui.py).
- **Level 2** đọc dữ liệu từ [level2/test_data.csv](level2/test_data.csv) và URL, locator từ [level2/ui_config.csv](level2/ui_config.csv). Cột `name` là tên mà workflow dùng, `type` là kiểu Selenium như `css selector`, `id` hoặc `xpath`, và `value` là URL hoặc selector. Nếu chuyển Moodle sang cổng 9502, sửa `base_url`. Nếu thay đổi selector nút mở form, sửa cặp `type`–`value` tương ứng với `enrol_button`. Các locator kiểm tra count, email, role, trạng thái và điểm cũng nằm trong file này.

## Chuẩn bị

Cần Python 3.10+, Chrome/Chromium và Moodle có tùy chọn **Choose...** trong **Starting from**. Dùng Moodle local English ở `http://127.0.0.1:9501` với Admin UTC, Manual enrolments và grade history theo [README fixture](README.md). Đặt timezone Admin về giá trị ban đầu khi xong. Chạy từ thư mục `F002-deliver/`.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
mkdir -p .project3-local
export F002_ADMIN_USER=admin
read -rsp 'Mật khẩu Admin Moodle local: ' F002_ADMIN_PASSWORD
export F002_ADMIN_PASSWORD
printf '\n'
read -rsp 'Mật khẩu Student fixture (xem README.md): ' F002_STUDENT_PASSWORD
export F002_STUDENT_PASSWORD
printf '\n'
```

Mặc định Selenium chạy Chrome headless. Dùng `--headed` để theo dõi trên cửa sổ Chrome. Nếu Chrome hoặc ChromeDriver ở đường dẫn riêng, truyền `--chrome-binary` và `--driver` hoặc đặt `F002_CHROME_BINARY` và `F002_CHROMEDRIVER`.

## Chạy trên fixture sạch

Copy và lint ba script PHP theo [README fixture](README.md#2-setup-toàn-bộ-fixtures). Lưu nguyên stdout của setup. Runner đọc `course`, `courseid`, `username_prefix`, `S` và `prepared_at` cho từng TC. Chỉ chạy khi setup báo đủ 28/28 và trong cùng ngày UTC với setup.

```bash
docker exec demo-webserver-1 php /tmp/f002-deliver/setup-all.php > .project3-local/setup-level1.txt &&
tail -1 .project3-local/setup-level1.txt

python level1/test_enrol_user.py --fixtures .project3-local/setup-level1.txt \
  --results .project3-local/level1.json
```

Reset sau Level 1 rồi lưu stdout mới cho Level 2.

```bash
docker exec demo-webserver-1 php /tmp/f002-deliver/cleanup-all.php &&
docker exec demo-webserver-1 php /tmp/f002-deliver/setup-all.php > .project3-local/setup-level2.txt &&
tail -1 .project3-local/setup-level2.txt

python level2/test_enrol_user.py --fixtures .project3-local/setup-level2.txt \
  --results .project3-local/level2.json
```

Nếu Moodle cài ở thư mục khác, thêm `-e F002_MOODLE_ROOT=/đường/dẫn` ngay sau `docker exec` ở cả lệnh setup và cleanup. Với Moodle 5.1 có thư mục `public/`, giá trị biến trỏ vào thư mục Moodle chứa `config.php`. Cleanup lần cuối theo README.

Dùng `--list` để xem mã testcase. Để chạy nhóm đầu, thêm `--case TC-002-005 --case TC-002-006 --case TC-002-007 --case TC-002-012` vào lệnh của từng level. Mỗi case tự đăng nhập Admin và mở trang Participants của course đã được setup. Runner trả mã thoát 1 nếu có FAIL hoặc BLOCKED. TC-002-013 trả OBSERVED khi đã thu được phản hồi và trạng thái lưu. TC-002-026 đọc điểm trong Grader report.

### Chạy bằng unittest discovery

Mỗi dòng CSV là một `unittest.TestCase` mang mã gốc. Discovery thu thập 30 ca mỗi level, gồm 28 ca chức năng và 2 ca phi chức năng. Cả hai cách chạy kiểm tra đủ bộ ID, kể cả khi dùng bộ lọc. CSV có ID thiếu, trùng hoặc ngoài bộ ca sẽ làm lệnh trả mã thoát khác 0.

```bash
F002_FIXTURES=.project3-local/setup-level1.txt python -m unittest discover -s level1 -v
# Cleanup rồi setup và lưu stdout mới trước Level 2.
F002_FIXTURES=.project3-local/setup-level2.txt python -m unittest discover -s level2 -v
```

Dùng `-k TC-002-024` để chọn ca. Nếu thiếu fixture hoặc thông tin đăng nhập, unittest hiển thị ca là `skipped` với lý do `BLOCKED`. TC-002-013 hiển thị `skipped` với lý do `OBSERVED` và ghi nhận thực tế. Dùng lệnh Python trực tiếp ở trên nếu cần báo cáo JSON và mã thoát 1 khi có BLOCKED.

Các ca TC-002-012, 015 và lần submit đầu của 024 kiểm tra Participants trong tab mới sau khi xác nhận lỗi. Tab ban đầu giữ phiên bản form hiện tại để TC-002-024 có thể sửa ngày.

Chạy kiểm tra hồi quy cho discovery, CSV và luồng đọc Participants mà không cần Moodle bằng `python -m unittest discover -s checks -v`.

`.project3-local/` dùng cho setup output, kết quả JSON và log của mỗi lượt. Mật khẩu chỉ cung cấp qua biến môi trường.

## Kiểm thử phi chức năng

Hai ca sau dùng course rỗng của TC-002-002. Cả hai hủy form rồi kiểm tra Participants vẫn rỗng.

| ID | Kiểm tra | Kỳ vọng |
| --- | --- | --- |
| NFR-002-001 | Thời gian từ khi nhập username đến khi Selenium thấy đúng gợi ý theo email | Tối đa 3.000 ms trên Moodle local, lấy từ cột `max_ms` |
| NFR-002-002 | Chọn đúng gợi ý từ ô Select users bằng phím Mũi tên xuống và Enter | Email của user đã chọn xuất hiện trong vùng selection |

## Kết quả thực tế ngày 2026-11-23

Moodle 5.1.9+ (Build 20261117), Chrome headless 158.0.8127.36 và Selenium 4.53.0. Nhóm chạy đầu gồm TC-002-005, 006, 007, 012 và PASS 4/4 ở mỗi level. Mỗi lượt đầy đủ dùng fixture sạch và setup báo 28/28. Lượt Level 2 đầu có TC-002-011 BLOCKED do Selenium gặp phần tử cũ ở bước chuẩn bị. Bảng ghi kết quả lượt chạy lại sau khi bổ sung một lần thử lại bước chuẩn bị và reset fixture.

| Kiểm tra | Level 1 | Level 2 |
| --- | --- | --- |
| 28 ca chức năng | 27 PASS, 1 OBSERVED | 27 PASS, 1 OBSERVED |
| TC-002-013, end bằng start | OBSERVED, `Invalid enrolment duration`, 0 participant | OBSERVED, `Invalid enrolment duration`, 0 participant |
| TC-002-026, cột F002 Recovery 73 trong Grader report | PASS, U1 = 73.00, U2 và U3 để trống | PASS, U1 = 73.00, U2 và U3 để trống |
| NFR-002-001, thời gian hiện gợi ý | PASS, 1055 ms | PASS, 1030 ms |
| NFR-002-002, chọn bằng bàn phím | PASS, đúng email | PASS, đúng email |

Hai lượt đều có 0 FAIL và 0 BLOCKED. Số đo của NFR-002-001 là một lần đo trên mỗi lượt local. Cleanup cuối lượt báo đủ 28/28.

Sau khi chuyển sang unittest, discovery thu thập 30 ca mỗi level. Nhóm xác minh TC-002-012, 013, 015 và 024 chạy lại trên fixture riêng cho mỗi level. Level 1 chạy bằng discovery, Level 2 chạy bằng CLI với `--case` và xuất JSON. Mỗi lượt ghi nhận 3 PASS và 1 OBSERVED ở TC-002-013.
