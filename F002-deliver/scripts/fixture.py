"""Create and verify F002 fixtures through Moodle's REST and admin interfaces."""

import argparse
import csv
import fcntl
import json
import os
import re
import secrets
import subprocess
import sys
from contextlib import ExitStack, contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from selenium.common.exceptions import WebDriverException

UTC = timezone.utc
CASES = tuple(f"TC-002-{number:03d}" for number in range(1, 29))
USERS = ("u1", "u2", "u3")
PRE_ENROLLED = {4, 16, 17, 19, 25}
DAY = 86400
GRADE_ITEM = "F002 Recovery 73"
ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def parameters(value, key):
    """Encode nested Moodle REST arguments as bracketed form keys."""
    if isinstance(value, dict):
        for field, item in value.items():
            yield from parameters(item, f"{key}[{field}]")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            yield from parameters(item, f"{key}[{index}]")
    else:
        yield key, value


class Site:
    def __init__(self, stack):
        self.stack = stack
        self.url = os.environ.get("F002_MOODLE_URL", "http://127.0.0.1:9501").rstrip(
            "/"
        )
        origin = urlsplit(self.url)
        require(
            origin.scheme in {"http", "https"} and origin.hostname,
            "Invalid F002_MOODLE_URL",
        )
        require(
            origin.scheme == "https"
            or origin.hostname in {"127.0.0.1", "localhost", "::1"},
            "Moodle REST credentials require HTTPS outside loopback",
        )
        self.token = os.environ.get("F002_MOODLE_WS_TOKEN")
        require(self.token, "Set F002_MOODLE_WS_TOKEN for the fixture service")
        self.prefix = os.environ.get("F002_DB_PREFIX", "mdl_")
        require(
            re.fullmatch(r"[a-z_][a-z0-9_]*", self.prefix),
            "Invalid PostgreSQL table prefix",
        )
        self.psql = [
            "docker",
            "exec",
            os.environ.get("F002_DB_CONTAINER", "demo-db-1"),
            "psql",
            "-XqAt",
            "-v",
            "ON_ERROR_STOP=1",
            "-U",
            os.environ.get("F002_DB_USER", "moodle"),
            "-d",
            os.environ.get("F002_DB_NAME", "moodle"),
        ]
        self.browser = None

    def api(self, method, **kwargs):
        fields = [
            (key, value)
            for name, value in kwargs.items()
            for key, value in parameters(value, name)
        ]
        fields += [
            ("wstoken", self.token),
            ("wsfunction", method),
            ("moodlewsrestformat", "json"),
        ]
        request = Request(
            f"{self.url}/webservice/rest/server.php", data=urlencode(fields).encode()
        )
        with urlopen(request, timeout=60) as response:
            result = json.load(response)
        if isinstance(result, dict) and (
            "exception" in result or result.get("warnings")
        ):
            error = result.get("errorcode") or "Moodle returned warnings"
            raise RuntimeError(f"{method}: {error}")
        return result

    def read(self, sql, **values):
        # Only these local, generated marker strings and integer IDs enter SQL.
        require(
            all(
                type(value) is int or re.fullmatch(r"[a-z0-9_]+", value)
                for value in values.values()
            ),
            "Unexpected value in fixture lookup",
        )
        query = sql.format(p=self.prefix, **values)
        output = subprocess.run(
            [
                *self.psql,
                "-c",
                f"BEGIN READ ONLY; SELECT coalesce(json_agg(q),'[]') FROM ({query}) q; COMMIT",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return json.loads(output.stdout)

    def admin(self):
        if self.browser is None:
            sys.path.insert(0, str(ROOT))
            from automation import BrowserOptions, Moodle, create_browser

            with (ROOT / "level2/ui_config.csv").open(
                encoding="utf-8-sig", newline=""
            ) as stream:
                config = {
                    row["name"]: (row["type"], row["value"])
                    for row in csv.DictReader(stream)
                }
            config["base_url"] = ("url", self.url)
            username = os.environ.get("F002_ADMIN_USER")
            password = os.environ.get("F002_ADMIN_PASSWORD")
            require(
                username and password,
                "Set F002_ADMIN_USER and F002_ADMIN_PASSWORD for setup",
            )
            driver = self.stack.enter_context(create_browser(BrowserOptions.from_env()))
            browser = Moodle(driver, config, SimpleNamespace(courseid=""))
            browser.login(username, password)
            self.browser = browser
        return self.browser

    def remove_extra_methods(self, courseid, methods):
        extras = [method for method in methods if method["enrol"] != "manual"]
        if not extras:
            return
        page = self.admin()
        sesskey = page.wait.until(
            lambda driver: driver.execute_script("return window.M?.cfg?.sesskey")
        )
        cookie = "; ".join(
            f"{entry['name']}={entry['value']}" for entry in page.driver.get_cookies()
        )
        # The native Moodle confirmation endpoint handles the actual deletion.
        for method in extras:
            args = urlencode(
                {
                    "id": courseid,
                    "action": "delete",
                    "instance": method["id"],
                    "confirm": 1,
                    "sesskey": sesskey,
                }
            )
            request = Request(
                f"{self.url}/enrol/instances.php",
                data=args.encode(),
                headers={"Cookie": cookie},
            )
            with urlopen(request, timeout=30):
                pass

    def seed_grade(self, courseid, users, key):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as ec

        page = self.admin()
        driver = page.driver

        def submit(path, fields):
            driver.get(f"{self.url}{path}")
            for name, value in fields.items():
                element = page.wait.until(ec.element_to_be_clickable((By.NAME, name)))
                element.clear()
                element.send_keys(value)
            before = driver.current_url
            button = page.wait.until(ec.presence_of_element_located((By.ID, "id_submitbutton")))
            # Fixture setup can submit the native form directly, with HTML validation.
            driver.execute_script("arguments[0].form.requestSubmit(arguments[0])", button)
            page.wait.until(
                ec.url_changes(before), "Moodle did not accept the grade form"
            )

        submit(
            f"/grade/edit/tree/item.php?courseid={courseid}",
            {"itemname": GRADE_ITEM, "idnumber": f"{key}_grade"},
        )
        item = self.grade_item(courseid, key)
        for user in users:
            submit(
                f"/grade/edit/tree/grade.php?courseid={courseid}&userid={user}&itemid={item['id']}",
                {"finalgrade": "73"},
            )
        return item["id"]

    def methods(self, courseid):
        return self.read(
            "SELECT id,enrol,status,roleid,enrolperiod FROM {p}enrol WHERE courseid={id}",
            id=courseid,
        )

    def grade_item(self, courseid, key):
        items = self.read(
            "SELECT id,itemname,itemtype,gradetype,grademin,grademax FROM {p}grade_items "
            "WHERE courseid={id} AND idnumber='{key}_grade'",
            id=courseid,
            key=key,
        )
        require(len(items) == 1, "Missing or duplicate recovery grade item")
        return items[0]


def key_for(state):
    return f"f002_{state['tc'][-3:]}_{state['token']}"


def day_start(prepared):
    return datetime.fromtimestamp(prepared, UTC).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


def enrol_dates(number, prepared):
    return prepared - 2 * DAY, prepared + (-3600 if number == 19 else 7 * DAY)


def load(path, tc, url):
    state = json.loads(path.read_text(encoding="utf-8"))
    require(
        isinstance(state, dict)
        and state.get("tc") == tc
        and state.get("site") == url
        and state.get("schema") == 1
        and re.fullmatch(r"[a-f0-9]{32}", state.get("token", ""))
        and state.get("phase") in {"building", "ready"},
        "Invalid fixture manifest or Moodle site mismatch",
    )
    users = state.get("users", {})
    require(
        isinstance(users, dict) and set(users) <= set(USERS), "Invalid manifest users"
    )
    ids = [users[suffix] for suffix in users]
    require(
        all(type(value) is int and value > 0 for value in ids)
        and len(set(ids)) == len(ids),
        "Invalid or duplicate manifest user IDs",
    )
    for field in ("courseid", "prepared_at", "instanceid", "roleid", "gradeitemid"):
        if field in state:
            require(
                type(state[field]) is int and state[field] > 0,
                f"Invalid manifest {field}",
            )
    return state


def save(path, state):
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(state, stream)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def owned(site, state):
    key = key_for(state)
    courseid = state.get("courseid", 0)
    courses = site.read(
        "SELECT id,shortname,idnumber,summary,fullname,visible,startdate FROM {p}course "
        "WHERE idnumber='{key}' OR id={id}",
        key=key,
        id=courseid,
    )
    require(len(courses) <= 1, "Ambiguous fixture course ownership")
    course = next(iter(courses), None)
    if course:
        require(
            course["id"] > 1
            and all(
                course[field] == key for field in ("shortname", "idnumber", "summary")
            )
            and (not courseid or courseid == course["id"]),
            "Course ownership mismatch",
        )
    admins = site.read("SELECT value FROM {p}config WHERE name='siteadmins'")
    require(len(admins) == 1, "Cannot determine Moodle site admins")
    admin_ids = {int(value) for value in admins[0]["value"].split(",")}
    users = {}
    for suffix in USERS:
        username = f"{key}_{suffix}"
        userid = state.get("users", {}).get(suffix, 0)
        records = site.read(
            "SELECT id,username,idnumber,description,auth,confirmed,suspended,timezone,lang,email FROM {p}user "
            "WHERE deleted=0 AND (username='{username}' OR id={id})",
            username=username,
            id=userid,
        )
        require(len(records) <= 1, "Ambiguous fixture user ownership")
        if records:
            user = records[0]
            require(
                user["username"] == user["idnumber"] == username
                and user["description"] == key
                and user["id"] not in admin_ids
                and (not userid or userid == user["id"]),
                "User ownership mismatch",
            )
            users[suffix] = user
    return course, users


def create(site, path, state, student, password):
    key = key_for(state)
    prepared = int(datetime.now(UTC).timestamp())
    course = {
        "fullname": f"F002 {state['tc']} {state['token']}",
        "shortname": key,
        "idnumber": key,
        "summary": key,
        "summaryformat": 2,
        "categoryid": 1,
        "visible": 1,
        "format": "topics",
        "startdate": int((day_start(prepared) - timedelta(days=1)).timestamp()),
        "enddate": 0,
    }
    state["courseid"] = courseid = site.api(
        "core_course_create_courses", courses=[course]
    )[0]["id"]
    save(path, state)
    requests = [
        {
            "username": f"{key}_{suffix}",
            "idnumber": f"{key}_{suffix}",
            "email": f"{key}_{suffix}@example.invalid",
            "firstname": "F002",
            "lastname": f"{state['tc']} {suffix} {state['token']}",
            "password": password,
            "auth": "manual",
            "lang": "en",
            "timezone": "UTC",
            "description": key,
        }
        for suffix in USERS
    ]
    created = site.api("core_user_create_users", users=requests)
    by_username = {user["username"]: user["id"] for user in created}
    state["users"] = users = {
        suffix: by_username[f"{key}_{suffix}"] for suffix in USERS
    }
    save(path, state)
    owned_course, owned_users = owned(site, state)
    require(
        owned_course and len(owned_users) == 3,
        "REST course/users are missing from the configured database",
    )
    methods = site.methods(courseid)
    site.remove_extra_methods(courseid, methods)
    methods = site.methods(courseid)
    require(
        len(methods) == 1 and methods[0]["enrol"] == "manual",
        "Course must have exactly one Manual enrolment method",
    )
    number = int(state["tc"][-3:])
    if number in PRE_ENROLLED:
        start, end = enrol_dates(number, prepared)
        site.api(
            "enrol_manual_enrol_users",
            enrolments=[
                {
                    "roleid": student,
                    "userid": users["u1"],
                    "courseid": courseid,
                    "timestart": start,
                    "timeend": end,
                    "suspend": int(number == 17),
                },
            ],
        )
    if number == 26:
        require(
            not site.read(
                "SELECT value FROM {p}config WHERE name='disablegradehistory' AND value='1'"
            ),
            "Grade history is disabled",
        )
        enrolments = [
            {"roleid": student, "userid": users[suffix], "courseid": courseid}
            for suffix in ("u1", "u2")
        ]
        site.api("enrol_manual_enrol_users", enrolments=enrolments)
        state["gradeitemid"] = site.seed_grade(
            courseid, [users["u1"], users["u2"]], key
        )
        site.api(
            "enrol_manual_unenrol_users",
            enrolments=[
                {"userid": entry["userid"], "courseid": courseid}
                for entry in enrolments
            ],
        )
    state.update(
        prepared_at=prepared, instanceid=methods[0]["id"], roleid=student, phase="ready"
    )
    save(path, state)


def verify(site, state, student):
    require(state["phase"] == "ready", "Incomplete fixture. Run cleanup before setup")
    key = key_for(state)
    course, users = owned(site, state)
    prepared = state["prepared_at"]
    today = day_start(prepared)
    require(
        today.date() == datetime.now(UTC).date(),
        "Fixture date is stale. Run cleanup before setup",
    )
    require(
        course
        and set(users) == set(USERS)
        and course["id"] == state["courseid"]
        and course["visible"] == 1
        and course["fullname"] == f"F002 {state['tc']} {state['token']}"
        and course["startdate"] == int((today - timedelta(days=1)).timestamp()),
        "Course/user baseline changed",
    )
    courseid = course["id"]
    require(
        state["roleid"] == student
        and site.methods(courseid)
        == [
            {
                "id": state["instanceid"],
                "enrol": "manual",
                "status": 0,
                "roleid": student,
                "enrolperiod": 0,
            }
        ],
        "Manual enrolment baseline changed",
    )
    number = int(state["tc"][-3:])
    start, end = enrol_dates(number, prepared)
    expected = int(number in PRE_ENROLLED)
    instance = state["instanceid"]
    context = site.read(
        "SELECT id FROM {p}context WHERE contextlevel=50 AND instanceid={id}",
        id=courseid,
    )[0]["id"]
    require(
        len(
            site.read(
                "SELECT id FROM {p}user_enrolments WHERE enrolid={id}", id=instance
            )
        )
        == expected
        and len(
            site.read(
                "SELECT id FROM {p}role_assignments WHERE contextid={id}", id=context
            )
        )
        == expected,
        "Participant or role baseline changed. Run cleanup before setup",
    )
    for suffix, user in users.items():
        userid = user["id"]
        require(
            state["users"][suffix] == userid
            and user["auth"] == "manual"
            and user["confirmed"] == 1
            and user["suspended"] == 0
            and user["timezone"] == "UTC"
            and user["lang"] == "en"
            and user["email"] == f"{key}_{suffix}@example.invalid",
            f"User baseline changed: {suffix}",
        )
        active = expected and suffix == "u1"
        enrolments = site.read(
            "SELECT enrolid,status,timestart,timeend FROM {p}user_enrolments WHERE userid={id}",
            id=userid,
        )
        assignments = site.read(
            "SELECT roleid,contextid,component,itemid FROM {p}role_assignments WHERE userid={id}",
            id=userid,
        )
        require(
            enrolments
            == (
                [
                    {
                        "enrolid": instance,
                        "status": int(number == 17),
                        "timestart": start,
                        "timeend": end,
                    }
                ]
                if active
                else []
            )
            and assignments
            == (
                [
                    {
                        "roleid": student,
                        "contextid": context,
                        "component": "",
                        "itemid": 0,
                    }
                ]
                if active
                else []
            ),
            f"Unexpected enrolment or role for {suffix}",
        )
    if number == 26:
        item = site.grade_item(courseid, key)
        require(
            item
            == {
                "id": state["gradeitemid"],
                "itemname": GRADE_ITEM,
                "itemtype": "manual",
                "gradetype": 1,
                "grademin": 0,
                "grademax": 100,
            },
            "Recovery grade item baseline changed",
        )
        for suffix, user in users.items():
            identifiers = {"item": item["id"], "user": user["id"]}
            current = site.read(
                "SELECT id FROM {p}grade_grades WHERE itemid={item} AND userid={user}",
                **identifiers,
            )
            history = site.read(
                "SELECT finalgrade FROM {p}grade_grades_history WHERE itemid={item} AND userid={user}",
                **identifiers,
            )
            require(
                not current
                and (
                    not history
                    if suffix == "u3"
                    else any(row["finalgrade"] == 73 for row in history)
                ),
                f"Recovery grade/history baseline changed: {suffix}",
            )
    start = today + timedelta(days=2, hours=12)
    return (
        f"{state['tc']}: course={course['fullname']}; courseid={courseid}; username_prefix={key}; "
        f"S={start:%Y-%m-%d %H:%M} UTC; prepared_at={prepared}"
    )


def remove(site, state):
    course, users = owned(site, state)
    key = key_for(state)
    remote = site.api("core_course_get_courses_by_field", field="idnumber", value=key)[
        "courses"
    ]
    remote_users = site.api(
        "core_user_get_users_by_field",
        field="username",
        values=[f"{key}_{suffix}" for suffix in USERS],
    )
    require(
        {row["id"] for row in remote} == ({course["id"]} if course else set())
        and {row["id"] for row in remote_users}
        == {row["id"] for row in users.values()},
        "REST and database fixture identities differ. Refusing deletion",
    )
    if course:
        site.api("core_course_delete_courses", courseids=[course["id"]])
    if users:
        site.api(
            "core_user_delete_users", userids=[row["id"] for row in users.values()]
        )
    require(
        owned(site, state) == (None, {}), "Owned resources remain. Manifest preserved"
    )


@contextmanager
def locked(directory):
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (directory / ".lock").open("a", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def main(action):
    parser = argparse.ArgumentParser(
        description=f"{action.capitalize()} Moodle F002 fixtures"
    )
    parser.add_argument(
        "--state-dir", type=Path, default=ROOT / ".project3-local/fixtures"
    )
    args = parser.parse_args()
    done = 0
    try:
        with ExitStack() as stack:
            stack.enter_context(locked(args.state_dir))
            site = Site(stack)
            if action == "setup":
                student = site.read("SELECT id FROM {p}role WHERE shortname='student'")[
                    0
                ]["id"]
                password = os.environ.get("F002_STUDENT_PASSWORD")
                require(password, "Set F002_STUDENT_PASSWORD before setup")
                if any(not (args.state_dir / f"{tc}.json").exists() for tc in CASES):
                    site.api("core_course_get_courses_by_field", field="id", value=1)
                    site.admin()
            for tc in CASES:
                path = args.state_dir / f"{tc}.json"
                try:
                    state = load(path, tc, site.url) if path.exists() else None
                    if action == "setup":
                        if state is None:
                            state = {
                                "schema": 1,
                                "tc": tc,
                                "site": site.url,
                                "token": secrets.token_hex(16),
                                "phase": "building",
                            }
                            save(path, state)
                            create(site, path, state, student, password)
                        print(verify(site, state, student), flush=True)
                    elif state is not None:
                        remove(site, state)
                        path.unlink()
                    done += 1
                except (
                    OSError,
                    RuntimeError,
                    ValueError,
                    KeyError,
                    IndexError,
                    TypeError,
                    subprocess.SubprocessError,
                    WebDriverException,
                ) as error:
                    print(
                        f"{tc}: {next(iter(str(error).splitlines()), type(error).__name__)}",
                        file=sys.stderr,
                    )
    except (
        OSError,
        RuntimeError,
        ValueError,
        KeyError,
        IndexError,
        TypeError,
        subprocess.SubprocessError,
        WebDriverException,
    ) as error:
        print(f"{action.capitalize()} unavailable: {error}", file=sys.stderr)
    print(f"{action.capitalize()} completed: {done}/{len(CASES)} test cases.")
    return int(done != len(CASES))
