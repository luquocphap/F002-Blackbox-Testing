"""Regression coverage for fixture ownership and REST transport."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.fixture import key_for, load, parameters, remove


class FixtureTests(unittest.TestCase):
    def test_rest_parameters_preserve_batch_structure(self):
        self.assertEqual(
            list(parameters([{"userid": 37, "courseid": 42}], "enrolments")),
            [("enrolments[0][userid]", 37), ("enrolments[0][courseid]", 42)],
        )

    def test_manifest_cannot_be_used_for_another_site(self):
        state = {
            "schema": 1,
            "tc": "TC-002-001",
            "token": "a" * 32,
            "phase": "building",
            "site": "http://localhost:9501",
        }
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "TC-002-001.json"
            manifest.write_text(json.dumps(state), encoding="utf-8")
            self.assertEqual(load(manifest, state["tc"], state["site"]), state)
            with self.assertRaisesRegex(RuntimeError, "site mismatch"):
                load(manifest, state["tc"], "http://localhost:9502")

    def test_cleanup_checks_remote_identity_before_any_delete(self):
        site = Mock()
        state = {"tc": "TC-002-001", "token": "a" * 32, "courseid": 42}
        key = key_for(state)
        site.read.side_effect = [
            [{"id": 42, "shortname": key, "idnumber": key, "summary": key}],
            [{"value": "2"}],
            [],
            [],
            [],
        ]
        site.api.side_effect = [{"courses": [{"id": 43}]}, []]
        with self.assertRaisesRegex(RuntimeError, "identities differ"):
            remove(site, state)
        self.assertEqual(
            [call.args[0] for call in site.api.call_args_list],
            ["core_course_get_courses_by_field", "core_user_get_users_by_field"],
        )
