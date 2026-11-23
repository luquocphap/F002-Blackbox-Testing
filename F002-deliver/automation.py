"""Shared Selenium workflow and command line runner for Enrol User."""

import argparse
import csv
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter
from urllib.parse import urljoin
from urllib.request import urlopen

from selenium import webdriver
from selenium.common.exceptions import (
    StaleElementReferenceException,
    WebDriverException,
)
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select, WebDriverWait

UTC = timezone.utc
DATE_PARTS = ("year", "month", "day", "hour", "minute")
FIXTURE_ROW = re.compile(
    r"^(TC-002-\d{3}): course=(.+); courseid=(\d+); "
    r"username_prefix=([a-z0-9_]+); S=(.+) UTC; prepared_at=(\d+)$"
)
FUNCTIONAL_IDS = {f"TC-002-{n:03d}" for n in range(1, 29)}


class Blocked(Exception):
    """The run does not have the required environment or baseline."""


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def check(actual, expected, label):
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


@dataclass(frozen=True)
class Fixture:
    course: str
    courseid: str
    prefix: str
    start: datetime
    prepared: datetime

    def username(self, user):
        return f"{self.prefix}_{user}"

    def email(self, user):
        return self.username(user) + "@example.invalid"

    def date(self, expression):
        today = self.prepared.replace(hour=0, minute=0, second=0)
        if expression == "Today":
            return today
        if expression == "Course start":
            return today - timedelta(days=1)
        relative = re.fullmatch(r"(S|t0)(?:([+-]\d+)([mhd]))?", expression)
        if not relative:
            return datetime.fromisoformat(expression).replace(tzinfo=UTC)
        anchor, offset, unit = relative.groups()
        base = self.start if anchor == "S" else minute(self.prepared)
        seconds = int(offset or 0) * {"m": 60, "h": 3600, "d": 86400, None: 0}[unit]
        return base + timedelta(seconds=seconds)


def minute(value):
    return value.replace(second=0, microsecond=0)


def read_fixtures(path):
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    if "Setup completed: 28/28 test cases." not in lines:
        raise Blocked("Setup output is missing the successful 28/28 summary")
    fixtures = {}
    for line in lines:
        match = FIXTURE_ROW.fullmatch(line)
        if not match:
            continue
        case, course, number, prefix, start, prepared = match.groups()
        if case in fixtures:
            raise Blocked(f"Multiple setup entries for {case}")
        fixtures[case] = Fixture(
            course, number, prefix, datetime.fromisoformat(start).replace(tzinfo=UTC),
            datetime.fromtimestamp(int(prepared), UTC),
        )
    if set(fixtures) != FUNCTIONAL_IDS or len({f.courseid for f in fixtures.values()}) != 28:
        raise Blocked("Expected 28 distinct fixture courses in setup output")
    if any(f.prepared.date() != datetime.now(UTC).date() for f in fixtures.values()):
        raise Blocked("Run with fixtures prepared on the current UTC day")
    return fixtures


class Moodle:
    def __init__(self, driver, config, fixture):
        self.driver = driver
        self.ui = config
        self.fixture = fixture
        self.wait = WebDriverWait(
            driver, 15, poll_frequency=0.15,
            ignored_exceptions=(StaleElementReferenceException,),
        )

    def url(self, name):
        template = self.ui[name][1]
        return urljoin(self.ui["base_url"][1].rstrip("/") + "/",
                       template.format(courseid=self.fixture.courseid).lstrip("/"))

    def locator(self, name, **values):
        kind, value = self.ui[name]
        return kind, value.format(**values)

    def elements(self, name, **values):
        return self.driver.find_elements(*self.locator(name, **values))

    def visible(self, name, **values):
        return next((el for el in self.elements(name, **values) if el.is_displayed()), None)

    def element(self, name, **values):
        return self.wait.until(lambda _: self.visible(name, **values), f"waiting for {name} {values}")

    def click(self, name, **values):
        def activate(_):
            el = self.visible(name, **values)
            if el is None or not el.is_enabled():
                return False
            el.click()
            return True

        self.wait.until(activate, f"waiting to click {name}")

    def go(self, page):
        self.driver.get(self.url(page))

    def login(self, username, password):
        self.go("login_url")
        self.element("login_user").send_keys(username)
        self.element("login_password").send_keys(password)
        self.click("login_button")
        self.element("logged_in")

    def prepare(self, credentials, baseline):
        # Moodle can replace the login DOM during redirect. Retry the read-only
        # setup once before any enrolment action has taken place.
        for attempt in range(2):
            try:
                self.driver.delete_all_cookies()
                self.login(credentials["admin_user"], credentials["admin_password"])
                self.go("participants_url")
                self.expect_text("course_heading", self.fixture.course)
                check(self.count(), int(baseline), "fixture participant baseline")
                return
            except StaleElementReferenceException:
                if attempt == 1:
                    raise
                print("  Retrying case setup after a stale page element", flush=True)

    def select(self, name, **values):
        return Select(self.element(name, **values))

    def checkbox(self, name, enabled):
        if self.element(name).is_selected() != enabled:
            self.click(name)
        self.wait.until(lambda _: self.element(name).is_selected() == enabled, f"setting {name}")

    def count(self):
        text = self.wait.until(lambda _: (el := self.visible("participant_count")) and el.text,
                               "reading participant count")
        return int(text.split()[0])

    def expect_count(self, count):
        self.wait.until(lambda _: self.count() == int(count), f"expected {count} participants")
        check(self.count(), int(count), "participant count")

    def row(self, user, role="", status=""):
        email = self.fixture.email(user)
        check(len(self.elements("participant_row", email=email)), 1, f"participant rows for {email}")
        for label in filter(None, (role, status)):
            self.element("participant_value", email=email, label=label)

    def open_form(self):
        self.click("enrol_button")
        self.element("assign_role")
        self.element("user_search")

    def close_form(self, action):
        self.click(action)
        self.wait.until(lambda _: not self.visible("modal"), f"modal after {action}")

    def search(self, text):
        search = self.element("user_search")
        search.clear()
        search.send_keys(text)

    def expect_text(self, name, expected, **values):
        def matching_text(_):
            el = self.visible(name, **values)
            if el is None:
                return False
            text = el.text
            return text if expected in text else False

        return self.wait.until(matching_text, f"{name} should contain {expected!r}")

    def write_date(self, name, value):
        for part in DATE_PARTS:
            self.select(name, part=part).select_by_value(str(getattr(value, part)))

    def read_date(self, name):
        parts = [int(self.select(name, part=part).first_selected_option.get_attribute("value"))
                 for part in DATE_PARTS]
        return datetime(*parts, tzinfo=UTC)

    def fill_form(self, data, users, end=None, recovery=None):
        for user in users:
            email = self.fixture.email(user)
            self.search(self.fixture.username(user))
            self.click("suggestion", email=email)
            self.expect_text("selection", email)
        self.select("assign_role").select_by_visible_text(data["role"])
        if data["start_choice"] or recovery is not None:
            self.click("show_more")
        if choice := data["start_choice"]:
            mode = self.select("start_mode")
            # Moodle appends the formatted date to Today and Course start.
            option = next((o.text for o in mode.options if o.text.startswith(choice)), None)
            if option is None:
                raise AssertionError(f"Starting from has no option for {choice!r}")
            mode.select_by_visible_text(option)
            if data["start_at"]:
                self.write_date("form_start_part", self.fixture.date(data["start_at"]))
            self.checkbox("end_enabled", False)
            seconds = str(int(data["duration_days"]) * 86400) if data["duration_days"] else ""
            self.select("duration").select_by_value(seconds)
            if end:
                self.checkbox("end_enabled", True)
                check(self.element("duration").is_enabled(), False, "duration with explicit end")
                self.write_date("end_part", self.fixture.date(end))
        if recovery is not None:
            self.checkbox("recover_grades", recovery)

    def open_edit(self, user):
        self.click("edit_enrolment", email=self.fixture.email(user))
        self.element("status")

    def edit_dates(self):
        start = self.read_date("edit_start_part") if self.element("start_enabled").is_selected() else None
        end = self.read_date("end_part") if self.element("end_enabled").is_selected() else None
        return start, end

    def verify_edit(self, data, user):
        self.open_edit(user)
        start, end = self.edit_dates()
        if label := data["expected_edit_status"]:
            check(self.select("status").first_selected_option.text, label, "edit status")
        if expected := data["expected_start"]:
            check(start, self.fixture.date(expected), "saved start")
        if expected := data["expected_end"]:
            check(end, None if expected == "disabled" else self.fixture.date(expected), "saved end")
        if days := data["expected_days"]:
            if start is None or end is None:
                raise AssertionError(f"Expected enabled dates, got start={start}, end={end}")
            check(end - start, timedelta(days=int(days)), "saved duration")
        self.close_form("cancel")

    def access(self, credentials, access, message):
        self.driver.delete_all_cookies()
        self.login(self.fixture.username("u1"), credentials["student_password"])
        self.go("course_url")
        check(self.driver.current_url, self.url("course_url" if access == "allowed" else "denied_url"),
              f"URL for student access {access}")
        self.expect_text("main", message)
        print(f"  Student {access}: {message} ({self.driver.current_url})", flush=True)
        self.driver.delete_all_cookies()
        self.login(credentials["admin_user"], credentials["admin_password"])
        self.go("participants_url")

    def grades(self, item, users, expected):
        self.go("grader_url")
        header = self.element("grade_header", item=item)
        table = header.find_element(*self.locator("grade_table"))
        column = int(header.get_property("cellIndex")) + 1
        actual_grades = []
        for user in users:
            row = table.find_element(*self.locator("grade_row", email=self.fixture.email(user)))
            actual = row.find_element(*self.locator("grade_cell", column=column)).text.strip()
            actual_grades.append(actual.replace("−", "-"))
        detail = ", ".join(f"{user}={grade}" for user, grade in zip(users, actual_grades, strict=True))
        check(actual_grades, expected, f"{item} grades for {', '.join(users)}")
        return f"{item}: {detail}"


def items(value):
    return value.split("|") if value else []


def verify_rows(page, data):
    page.expect_count(data["expected_count"])
    expected = items(data["expected_users"])
    for user in expected:
        page.row(user, data["expected_role"], data["expected_status"])
    for user in {"u1", "u2", "u3"} - set(expected):
        check(len(page.elements("participant_row", email=page.fixture.email(user))),
              0, f"unexpected rows for {user}")


def rejected(page, message, count, users):
    page.click("save")
    actual = page.expect_text("alert", message, message=message)
    print(f"  Validation: {actual}", flush=True)
    if not page.visible("modal"):
        # Confirm the baseline after the request, even if the table was left unchanged.
        page.go("participants_url")
    page.expect_count(count)
    for user in users:
        check(len(page.elements("participant_row", email=page.fixture.email(user))),
              0, f"rows after rejected submit for {user}")


def search_case(page, data):
    page.open_form()
    if term := data["search"]:
        page.search(page.fixture.username(term) if term in ("u1", "u2", "u3") else term)
    if suggestion := data["expected_suggestions"]:
        if suggestion in ("u1", "u2", "u3"):
            page.element("suggestion", email=page.fixture.email(suggestion))
        else:
            page.expect_text("suggestions", suggestion)
    check(page.element("selection").text, data["expected_selection"], "search selection")
    page.close_form(data["action"])
    if confirmation := data["expected_submit"]:
        page.expect_text("submit_confirmation", confirmation)
    if error := data["forbidden_error"]:
        check(page.visible("alert", message=error), None, "unexpected validation")


def observe(page, users):
    def alerts():
        return [el.text for el in page.elements("alert", message="") if el.is_displayed() and el.text]

    previous = set(alerts())
    page.click("save")
    user = users[0]
    email = page.fixture.email(user)
    page.wait.until(lambda _: page.elements("participant_row", email=email)
                    or set(alerts()) - previous, "participant or validation for equal dates")
    count = page.count()
    rows = len(page.elements("participant_row", email=email))
    if rows:
        page.expect_count(rows)
        count = page.count()
    detail = f"alerts={sorted(set(alerts()) - previous)!r}, participants={count}, rows for {user}={rows}"
    if rows:
        page.open_edit(user)
        start, end = page.edit_dates()
        page.close_form("cancel")
        detail += f", saved start={start}, saved end={end}"
    return detail


def run_functional(page, data, credentials):
    users = items(data["users"])
    flow = data["flow"]
    if flow == "search":
        search_case(page, data)
    elif flow == "grades":
        for index, (user, recovery) in enumerate(zip(users, items(data["recovery"]), strict=True), 1):
            page.open_form()
            page.fill_form(data, [user], recovery=recovery == "on")
            page.close_form("save")
            page.expect_count(index)
    elif flow not in ("existing", "toggle"):
        page.open_form()
        page.fill_form(data, users, data["end_at"])
        if flow == "observe":
            return "OBSERVED", observe(page, users)
        if flow in ("reject", "retry"):
            rejected(page, data["expected_error"], data["baseline"], users)
            if flow == "retry":
                if page.visible("modal"):
                    page.write_date("end_part", page.fixture.date(data["retry_end_at"]))
                else:
                    page.open_form()
                    page.fill_form(data, users, data["retry_end_at"])
                page.close_form("save")
        else:
            page.close_form("cancel" if flow == "cancel" else "save")

    verify_rows(page, data)
    expected_users = items(data["expected_users"])
    if any(data[key] for key in ("expected_edit_status", "expected_start", "expected_end", "expected_days")):
        for user in expected_users:
            page.verify_edit(data, user)

    if flow == "cancel":
        page.open_form()
        check(page.element("selection").text, data["expected_selection"], "selection after reopen")
        check(page.select("assign_role").first_selected_option.text, data["expected_reset_role"], "role after reopen")
        page.click("show_more")
        check(page.select("duration").first_selected_option.text, data["expected_reset_duration"],
              "duration after reopen")
        page.close_form("cancel")

    if flow == "toggle":
        steps = ((data["expected_access"], data["expected_access_text"]),
                 (data["second_access"], data["second_access_text"]))
        for status, (access, message) in zip(items(data["change_status"]), steps, strict=True):
            page.open_edit(expected_users[0])
            page.select("status").select_by_visible_text(status)
            page.close_form("save")
            page.row(expected_users[0], data["expected_role"], status)
            page.access(credentials, access, message)
        verify_rows(page, data)
    elif data["expected_access"]:
        page.access(credentials, data["expected_access"], data["expected_access_text"])
        verify_rows(page, data)

    if flow == "grades":
        return "PASS", page.grades(data["grade_item"], expected_users, items(data["expected_grades"]))
    return "PASS", ""


def run_nonfunctional(page, data):
    page.open_form()
    user = data["users"]
    email = page.fixture.email(user)
    started = perf_counter()
    page.search(page.fixture.username(user))
    page.element("suggestion", email=email)
    if data["flow"] == "latency":
        elapsed = (perf_counter() - started) * 1000
        limit = float(data["max_ms"])
        detail = f"suggestion={elapsed:.0f} ms, limit={limit:.0f} ms"
        if elapsed > limit:
            raise AssertionError(detail)
    else:
        page.element("user_search").send_keys(Keys.ARROW_DOWN, Keys.ENTER)
        page.expect_text("selection", email)
        detail = "Arrow Down + Enter selected the expected user"
    page.close_form("cancel")
    verify_rows(page, data)
    return "PASS", detail


def create_browser(args):
    options = webdriver.ChromeOptions()
    if not args.headed:
        options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,1000")
    if args.chrome_binary:
        options.binary_location = args.chrome_binary
    driver = webdriver.Chrome(service=Service(executable_path=args.driver), options=options)
    driver.set_page_load_timeout(40)
    return driver


def main(directory, config_from_file=None, config=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, help="Captured stdout from setup-all.php")
    parser.add_argument("--case", action="append", metavar="ID", help="Limit to these IDs (repeatable)")
    parser.add_argument("--list", action="store_true", help="List IDs without opening Moodle")
    parser.add_argument("--headed", action="store_true")
    parser.add_argument("--chrome-binary", default=os.environ.get("F002_CHROME_BINARY"))
    parser.add_argument("--driver", default=os.environ.get("F002_CHROMEDRIVER"))
    parser.add_argument("--results", type=Path, help="Write per-case JSON results")
    args = parser.parse_args()
    data = read_csv(directory / "test_data.csv")
    if args.case:
        unknown = set(args.case) - {row["id"] for row in data}
        if unknown:
            parser.error(f"unknown case IDs: {', '.join(sorted(unknown))}")
        data = [row for row in data if row["id"] in args.case]
    if args.list:
        print("\n".join(row["id"] for row in data))
        return 0
    if args.fixtures is None:
        parser.error("--fixtures is required for a run")

    results = []

    def record(row, status, detail=""):
        print(f"{row['id']} {status}" + (f" | {detail}" if detail else ""), flush=True)
        results.append({"id": row["id"], "status": status, "detail": detail})

    driver = None
    try:
        if config_from_file:
            config = {row["name"]: (row["type"], row["value"]) for row in read_csv(config_from_file)}
        fixtures = read_fixtures(args.fixtures)
        credentials = {name: os.environ.get(f"F002_{name.upper()}") for name in
                       ("admin_user", "admin_password", "student_password")}
        needed = ["admin_user", "admin_password"]
        if any(row["expected_access"] for row in data):
            needed.append("student_password")
        for name in needed:
            if not credentials[name]:
                raise Blocked(f"Set F002_{name.upper()} before running")
        with urlopen(config["base_url"][1], timeout=5):
            pass
        driver = create_browser(args)
    except (Blocked, OSError, ValueError, KeyError, csv.Error, WebDriverException) as error:
        for row in data:
            record(row, "BLOCKED", str(error).splitlines()[0] or type(error).__name__)

    if driver is not None:
        try:
            for row in data:
                print(f"Running {row['id']}", flush=True)
                try:
                    fixture = fixtures[row.get("fixture_id") or row["id"]]
                    page = Moodle(driver, config, fixture)
                    page.prepare(credentials, row["baseline"])
                except (AssertionError, ValueError, KeyError, WebDriverException) as error:
                    record(row, "BLOCKED", str(error).splitlines()[0] or type(error).__name__)
                    continue
                try:
                    if row["id"] in FUNCTIONAL_IDS:
                        status, detail = run_functional(page, row, credentials)
                    else:
                        status, detail = run_nonfunctional(page, row)
                    record(row, status, detail)
                except (AssertionError, ValueError, KeyError, WebDriverException) as error:
                    record(row, "FAIL", str(error).splitlines()[0] or type(error).__name__)
        finally:
            driver.quit()
    if args.results:
        args.results.parent.mkdir(parents=True, exist_ok=True)
        args.results.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    statuses = [row["status"] for row in results]
    print(", ".join(f"{status}={statuses.count(status)}" for status in ("PASS", "FAIL", "OBSERVED", "BLOCKED")))
    return 1 if {"FAIL", "BLOCKED"} & set(statuses) else 0
