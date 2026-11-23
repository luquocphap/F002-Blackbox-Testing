"""Runner regression tests that need neither credentials nor Moodle."""

import csv
import importlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import Mock, call, patch

from selenium.common.exceptions import ElementClickInterceptedException
from selenium.webdriver.support.ui import WebDriverWait

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automation import Moodle, main, read_test_data, rejected, run_functional


class RunnerTests(unittest.TestCase):
    def test_click_refinds_element_after_interception(self):
        page = Moodle(Mock(), {}, Mock())
        page.wait = WebDriverWait(page.driver, 0.2, poll_frequency=0.01)
        before_refresh = Mock()
        before_refresh.click.side_effect = ElementClickInterceptedException("main intercepted click")
        after_refresh = Mock()
        page.visible = Mock(side_effect=[before_refresh, after_refresh])

        page.click("edit_enrolment", email="u1@example.invalid")

        locator_call = call("edit_enrolment", email="u1@example.invalid")
        self.assertEqual(page.visible.call_args_list, [locator_call, locator_call])
        before_refresh.click.assert_called_once_with()
        after_refresh.click.assert_called_once_with()

    def test_click_fails_if_target_remains_obstructed(self):
        page = Moodle(Mock(), {}, Mock())
        page.wait = WebDriverWait(page.driver, 0.03, poll_frequency=0.01)
        link = Mock()
        link.click.side_effect = ElementClickInterceptedException("main intercepted click")
        page.visible = Mock(return_value=link)

        with self.assertRaisesRegex(ElementClickInterceptedException, "main intercepted click"):
            page.click("edit_enrolment", email="u1@example.invalid")
        self.assertGreater(link.click.call_count, 1)

    def test_login_waits_for_the_password_control_moodle_replaces(self):
        for toggles_password in (True, False):
            with self.subTest(toggles_password=toggles_password):
                page = Moodle(Mock(), {}, Mock())
                page.go = Mock()
                page.elements = Mock(return_value=[Mock()] if toggles_password else [])
                fields = {name: Mock() for name in ("login_user", "login_password", "login_password_ready", "logged_in")}
                page.element = Mock(side_effect=fields.__getitem__)
                page.click = Mock()
                page.login("user", "test-only")
                password = "login_password_ready" if toggles_password else "login_password"
                self.assertEqual(page.element.call_args_list, [
                    call(password), call("login_user"), call("logged_in"),
                ])
                fields[password].send_keys.assert_called_once_with("test-only")

    def test_discovery_collects_all_original_ids(self):
        expected = {f"TC-002-{n:03d}" for n in range(1, 29)} | {"NFR-002-001", "NFR-002-002"}
        loader = unittest.TestLoader()
        for level in ("level1", "level2"):
            with self.subTest(level=level):
                module = importlib.import_module(f"{level}.test_enrol_user")
                cases = list(loader.loadTestsFromModule(module))
                self.assertEqual(len(cases), len(expected))
                self.assertEqual({case.id().rsplit(".", 1)[-1] for case in cases}, expected)

    def test_csv_errors_fail_before_case_filter(self):
        with (ROOT / "level1/test_data.csv").open(newline="", encoding="utf-8") as source:
            rows = list(csv.reader(source))
        variants = {
            "missing": rows[:-1],
            "duplicate": [*rows, rows[1]],
            "invalid": [*rows, ["TC-002-999", *rows[1][1:]]],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test_data.csv"
            for problem, invalid_rows in variants.items():
                with self.subTest(problem=problem):
                    with path.open("w", newline="", encoding="utf-8") as stream:
                        csv.writer(stream).writerows(invalid_rows)
                    stderr = io.StringIO()
                    with (
                        patch.object(sys, "argv", ["runner", "--list", "--case", "TC-002-005"]),
                        redirect_stderr(stderr),
                        self.assertRaises(SystemExit) as raised,
                    ):
                        main(__name__, path, Mock())
                    self.assertEqual(raised.exception.code, 2)
                    self.assertIn(f"{problem} IDs", stderr.getvalue())
                    module = importlib.import_module("level1.test_enrol_user")
                    loader = unittest.TestLoader()
                    loader.testNamePatterns = ["*TC-002-005*"]
                    with patch.object(module, "DATA", path):
                        suite = loader.loadTestsFromModule(module)
                    result = suite.run(unittest.TestResult())
                    self.assertFalse(result.wasSuccessful())
                    self.assertIn(f"{problem} IDs", result.errors[0][1])

    def test_open_modal_cannot_hide_an_enrolment(self):
        page = Mock()
        page.visible.return_value = True
        page.driver.current_window_handle = "original"
        page.fixture.email.return_value = "u1@example.invalid"
        # Only the fresh page shows the erroneous enrolment.
        page.count.side_effect = lambda: int(page.go.called)
        page.elements.side_effect = lambda *args, **kwargs: [object()] if page.go.called else []

        with redirect_stdout(io.StringIO()), self.assertRaisesRegex(AssertionError, "got 1"):
            rejected(page, "Invalid enrolment duration", "0", ["u1"])

        page.driver.switch_to.new_window.assert_called_once_with("tab")
        page.go.assert_called_once_with("participants_url")
        page.driver.close.assert_called_once()
        page.driver.switch_to.window.assert_called_once_with("original")

    def test_discovery_is_unsuccessful_when_blocked(self):
        for level in ("level1", "level2"):
            with self.subTest(level=level), patch.dict("os.environ", clear=True):
                module = importlib.import_module(f"{level}.test_enrol_user")
                suite = unittest.TestLoader().loadTestsFromModule(module)
                result = suite.run(unittest.TestResult())
                self.assertEqual(result.testsRun, 30)
                self.assertFalse(result.wasSuccessful())
                self.assertEqual(len(result.skipped), 0)
                self.assertIn("F002_FIXTURES", result.errors[0][1])

    def test_empty_selection_submit_checks_fresh_participants(self):
        rows = read_test_data(ROOT / "level1/test_data.csv")
        for data in (row for row in rows if row["id"] in {"TC-002-001", "TC-002-003"}):
            with self.subTest(case=data["id"]):
                page = Mock()
                page.element.return_value.text = data["expected_selection"]
                page.visible.return_value = None
                page.elements.side_effect = lambda _name, *, email, page=page: (
                    [object()] if page.go.called and email == "u1@example.invalid" else []
                )
                page.fixture.email.side_effect = lambda user: f"{user}@example.invalid"
                with self.assertRaisesRegex(AssertionError, "unexpected rows for u1"):
                    run_functional(page, data, {})
                self.assertLess(
                    page.mock_calls.index(call.expect_text("submit_confirmation", "0 enrolled users")),
                    page.mock_calls.index(call.visible("alert", message="required")),
                )
                self.assertLess(
                    page.mock_calls.index(call.visible("alert", message="required")),
                    page.mock_calls.index(call.go("participants_url")),
                )

    def test_cli_writes_json_and_continues_after_empty_exception(self):
        ids = ("TC-002-001", "TC-002-003")
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "results.json"
            args = ["runner", "--fixtures", "fixture.txt", "--case", ids[0], "--case", ids[1],
                    "--results", str(report)]
            with (
                patch.object(sys, "argv", args),
                patch.dict("os.environ", F002_ADMIN_USER="admin", F002_ADMIN_PASSWORD="test-only"),
                patch("automation.read_fixtures", return_value=dict.fromkeys(ids)),
                patch("automation.urlopen"),
                patch("automation.create_browser"),
                patch("automation.Moodle"),
                patch("automation.run_functional", side_effect=[AssertionError(), ("PASS", "")]),
                redirect_stdout(io.StringIO()),
            ):
                exit_code = main(__name__, ROOT / "level1/test_data.csv",
                                 lambda: {"base_url": ("url", "http://localhost")})
            self.assertEqual(exit_code, 1)
            self.assertEqual(json.loads(report.read_text(encoding="utf-8")), [
                {"id": ids[0], "status": "FAIL", "detail": "AssertionError"},
                {"id": ids[1], "status": "PASS", "detail": ""},
            ])
