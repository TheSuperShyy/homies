# -*- coding: utf-8 -*-
"""Tests for oxs_mirror_list.py.   python scripts/oxs_mirror_list_test.py

Every number here is one of the synthetic test phones (9725099020xx), fake by construction.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oxs_mirror_list as L  # noqa: E402

OWNER = "+972509902001"
A, B, C = "+972509902011", "+972509902012", "+972509902013"
RESIDENTS = [
    {"unit": "2", "phone": OWNER, "source": "agent"},
    {"unit": "1", "phone": A, "source": "agent"},
    {"unit": "1", "phone": B, "source": "oxs"},
    {"unit": "3", "phone": C, "source": "oxs"},
    {"unit": "4", "phone": "", "source": "oxs"},
    {"unit": "5", "phone": None, "source": "oxs"},
]


class Entries(unittest.TestCase):
    def test_the_list_is_read_the_way_the_function_reads_it(self):
        self.assertEqual(L.entries(" %s , %s,, " % (OWNER, A)), [OWNER, A])
        self.assertEqual(L.entries(""), [])
        self.assertEqual(L.entries(None), [])


class Numbers(unittest.TestCase):
    def test_a_flat_gives_every_number_on_file_for_it(self):
        self.assertEqual(L.numbers_of(RESIDENTS, "1"), [A, B])
        self.assertEqual(L.numbers_of(RESIDENTS, "3"), [C])

    def test_a_flat_with_no_number_gives_none(self):
        self.assertEqual(L.numbers_of(RESIDENTS, "4"), [])
        self.assertEqual(L.numbers_of(RESIDENTS, "5"), [])
        self.assertEqual(L.numbers_of(RESIDENTS, "9"), [])

    def test_only_a_number_as_the_function_compares_it_counts(self):
        # The function compares the reporter as +E.164, exactly. Anything else on file could never match.
        odd = [{"unit": "7", "phone": "972509902017"}, {"unit": "7", "phone": "050-990-2017"}]
        self.assertEqual(L.numbers_of(odd, "7"), [])
        self.assertTrue(L.valid(A))
        for bad in ("972509902011", "+97250 9902011", "+abc", "", None, "+12"):
            self.assertFalse(L.valid(bad), bad)


class Change(unittest.TestCase):
    def test_adding_keeps_the_order_and_adds_each_once(self):
        self.assertEqual(L.with_added([OWNER], [A, B, A, OWNER, C]), [OWNER, A, B, C])

    def test_adding_what_is_there_changes_nothing(self):
        self.assertEqual(L.with_added([OWNER, A], [A]), [OWNER, A])

    def test_removing_takes_only_those(self):
        self.assertEqual(L.without([OWNER, A, B, C], [A, B]), [OWNER, C])
        self.assertEqual(L.without([OWNER], [A]), [OWNER])


class Who(unittest.TestCase):
    def test_the_list_is_shown_by_flat_never_by_number(self):
        shown = L.by_flat([OWNER, A, B, C, "+972509902099"], RESIDENTS)
        self.assertEqual(shown, [("flat 2", 1), ("flat 1", 2), ("flat 3", 1), ("not on file in the test building", 1)])
        self.assertNotIn("9725", repr(shown))


class EnvFile(unittest.TestCase):
    TEXT = "A=1\nOXS_MIRROR_PHONES=%s\n# a comment\nB=2\n" % OWNER

    def test_only_the_one_line_changes(self):
        out = L.env_with(self.TEXT, "OXS_MIRROR_PHONES", "%s,%s" % (OWNER, A))
        self.assertEqual(out, "A=1\nOXS_MIRROR_PHONES=%s,%s\n# a comment\nB=2\n" % (OWNER, A))

    def test_windows_line_endings_are_kept(self):
        out = L.env_with(self.TEXT.replace("\n", "\r\n"), "OXS_MIRROR_PHONES", OWNER + "," + A)
        self.assertEqual(out, ("A=1\nOXS_MIRROR_PHONES=%s,%s\n# a comment\nB=2\n" % (OWNER, A)).replace("\n", "\r\n"))

    def test_a_missing_line_is_added_at_the_end(self):
        self.assertEqual(L.env_with("A=1\n", "OXS_MIRROR_PHONES", OWNER), "A=1\nOXS_MIRROR_PHONES=%s\n" % OWNER)
        self.assertEqual(L.env_with("A=1", "OXS_MIRROR_PHONES", OWNER), "A=1\nOXS_MIRROR_PHONES=%s\n" % OWNER)

    def test_a_line_that_only_starts_the_same_is_left_alone(self):
        text = "OXS_MIRROR_PHONES_OLD=x\nOXS_MIRROR_PHONES=%s\n" % OWNER
        self.assertEqual(L.env_with(text, "OXS_MIRROR_PHONES", A), "OXS_MIRROR_PHONES_OLD=x\nOXS_MIRROR_PHONES=%s\n" % A)


if __name__ == "__main__":
    unittest.main(verbosity=1)
