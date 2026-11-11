# -*- coding: utf-8 -*-
"""Tests for chatwoot_teams.py.   python scripts/chatwoot_teams_test.py"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chatwoot_teams as T  # noqa: E402
import n8n_handover as H  # noqa: E402

ADMIN = {"id": 2, "name": "Owner", "role": "administrator", "confirmed": True}
SEAT_IN = {"id": 7, "name": "Seat in the inbox", "role": "agent", "confirmed": True}
SEAT_OUT = {"id": 9, "name": "Seat outside the inbox", "role": "agent", "confirmed": True}


class Reach(unittest.TestCase):
    def test_an_administrator_is_reached_without_inbox_membership(self):
        self.assertEqual(T.reach([ADMIN], inbox_ids=set()), [ADMIN])

    def test_an_agent_in_the_inbox_is_reached(self):
        self.assertEqual(T.reach([SEAT_IN], inbox_ids={7}), [SEAT_IN])

    def test_an_agent_outside_the_inbox_is_dropped_in_silence(self):
        # 3 Sep: administrators always worked and the first real seat got nothing.
        self.assertEqual(T.reach([SEAT_OUT], inbox_ids={7}), [])

    def test_an_empty_team_reaches_nobody(self):
        self.assertEqual(T.reach([], inbox_ids={7}), [])


class Summary(unittest.TestCase):
    def rows(self, members):
        return {r["department"]: r for r in T.summary(members, inbox_ids={7})}

    def test_every_department_has_a_row_even_when_chatwoot_returned_none(self):
        rows = self.rows({})
        self.assertEqual(sorted(rows), sorted(T.DEPARTMENTS))
        self.assertTrue(all(r["silent"] for r in rows.values()))

    def test_a_department_with_only_an_outside_seat_is_silent(self):
        rows = self.rows({"management": [SEAT_OUT], "service": [ADMIN]})
        self.assertTrue(rows["management"]["silent"])
        self.assertFalse(rows["service"]["silent"])
        self.assertEqual(rows["management"]["members"], [SEAT_OUT])
        self.assertEqual(rows["management"]["reached"], [])

    def test_silent_lists_the_departments_nobody_hears(self):
        got = T.silent(T.summary({"service": [ADMIN], "collections": [SEAT_IN]}, inbox_ids={7}))
        self.assertEqual(got, ["operations", "management"])


class Plan(unittest.TestCase):
    def test_adding_someone_already_seated_is_nothing_to_do(self):
        self.assertEqual(T.plan("add", member_ids=[2, 7], agent_ids=[2]), [])

    def test_adding_keeps_only_the_new_ones_once_each(self):
        self.assertEqual(T.plan("add", member_ids=[2], agent_ids=[7, 2, 7]), [7])

    def test_removing_someone_not_seated_is_nothing_to_do(self):
        self.assertEqual(T.plan("remove", member_ids=[2], agent_ids=[9]), [])

    def test_removing_takes_only_who_is_there(self):
        self.assertEqual(T.plan("remove", member_ids=[2, 7], agent_ids=[7, 9]), [7])


class SameTableAsTheWorkflow(unittest.TestCase):
    def test_department_ids_equal_the_ones_hand_to_a_person_mentions(self):
        # "Decide the routing" builds the mention from its own TEAMS table. If the two
        # drift, this script reports on one team while the note mentions another.
        m = re.search(r"const TEAMS = \{([^}]*)\}", H.DECIDE)
        self.assertIsNotNone(m, "TEAMS not found in n8n_handover.DECIDE")
        in_workflow = {k: int(v) for k, v in re.findall(r"(\w+):\s*(\d+)", m.group(1))}
        self.assertEqual(in_workflow, T.DEPARTMENTS)


if __name__ == "__main__":
    unittest.main(verbosity=1)
