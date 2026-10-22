# -*- coding: utf-8 -*-
"""Tests for check_name_flow.py.   python scripts/check_name_flow_test.py"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_name_flow as C  # noqa: E402

OPENED = {"ok": True, "reference": "255-1600-26", "reference_spoken": "אחת שש אפס אפס"}


def turn_tool(name, args, result, agent):
    return {"rounds": [[{"tool": name, "arguments": args, "result": result}]], "agent": agent}


class Rules(unittest.TestCase):
    def check(self, card, turns):
        return C.score(card, {"scenario": card["id"], "turns": turns})

    def test_ticket_with_name_asked_first_passes(self):
        card = {"id": "a", "call_has_number": True, "expect": {"ticket": True}}
        turns = [{"agent": "היי, מדבר מיכאל"}, {"caller": "נשרפה נורה בחדר מדרגות"},
                 {"agent": "אוי. על איזה שם לרשום את הקריאה?"}, {"caller": "דני כהן"},
                 {"agent": "באיזה בניין, ומה מספר הדירה?"}, {"caller": "בר כוכבא 23 דירה 4"},
                 turn_tool("open_request", {"description": "נורה", "reporter_name": "דני כהן",
                                            "building": "בר כוכבא 23"}, OPENED, "פתחתי פנייה")]
        self.assertEqual(self.check(card, turns), [])

    def test_ticket_without_name_fails(self):
        card = {"id": "b", "call_has_number": True, "expect": {"ticket": True}}
        turns = [{"agent": "היי"}, {"caller": "נורה שרופה, בר כוכבא 23"},
                 turn_tool("open_request", {"description": "נורה", "building": "בר כוכבא 23"},
                           OPENED, "פתחתי")]
        fails = self.check(card, turns)
        self.assertIn("named", fails)
        self.assertIn("asked_first", fails)

    def test_name_said_up_front_must_not_be_asked(self):
        card = {"id": "c", "call_has_number": True, "expect": {"ticket": True, "name_given": True}}
        turns = [{"agent": "היי"}, {"caller": "זאת דנה לוי מבר כוכבא 23 דירה 4, יש נזילה"},
                 {"agent": "מה השם שלך?"}, {"caller": "אמרתי, דנה"},
                 turn_tool("open_request", {"description": "נזילה", "reporter_name": "דנה לוי"},
                           OPENED, "פתחתי")]
        self.assertIn("asked_once", self.check(card, turns))

    def test_emergency_alert_must_come_before_the_name(self):
        card = {"id": "d", "call_has_number": True, "expect": {"ticket": True, "emergency": True}}
        turns = [{"agent": "היי"}, {"caller": "יש ריח של גז חזק"},
                 {"agent": "מה השם שלך?"}, {"caller": "רון"},
                 turn_tool("notify_team", {"reason": "emergency", "description": "גז"},
                           {"ok": True}, "הצוות יודע"),
                 turn_tool("open_request", {"description": "גז", "reporter_name": "רון",
                                            "urgency": "emergency"}, OPENED, "פתחתי")]
        self.assertIn("emergency_first", self.check(card, turns))

    def test_phone_must_not_be_asked_when_the_call_has_one(self):
        card = {"id": "e", "call_has_number": True, "expect": {"ticket": True}}
        turns = [{"agent": "היי"}, {"caller": "שער שבור"}, {"agent": "על איזה שם לרשום?"},
                 {"caller": "מיכל"}, {"agent": "ומה מספר הטלפון שלך?"}, {"caller": "050..."},
                 turn_tool("open_request", {"description": "שער", "reporter_name": "מיכל"},
                           OPENED, "פתחתי")]
        self.assertIn("phone", self.check(card, turns))

    def test_no_ticket_expected(self):
        card = {"id": "f", "call_has_number": True, "expect": {"ticket": False}}
        turns = [{"agent": "היי"}, {"caller": "הכיור שלי סתום"},
                 {"agent": "כיור בתוך הדירה הוא באחריותך"}]
        self.assertEqual(self.check(card, turns), [])

    def test_refusal_gets_a_ticket_and_no_third_ask(self):
        card = {"id": "g", "call_has_number": True, "expect": {"ticket": True, "refuses_name": True}}
        turns = [{"agent": "היי"}, {"caller": "המעלית תקועה"}, {"agent": "על איזה שם לרשום?"},
                 {"caller": "לא משנה"}, {"agent": "זה רק כדי שהצוות יידע עם מי לדבר. מה השם?"},
                 {"caller": "לא רוצה"},
                 turn_tool("open_request", {"description": "מעלית", "name_declined": True},
                           OPENED, "פתחתי")]
        self.assertEqual(self.check(card, turns), [])


class Questions(unittest.TestCase):
    def test_the_tenants_name_is_a_name_question(self):
        # 22 Oct, nm_staff_no_number: "ומה השם של הדייר?" was missed by the
        # lookahead meant only for the street.
        self.assertTrue(C.NAME_ASK.search("אין בעיה! ומה השם של הדייר?"))

    def test_the_streets_name_is_not(self):
        self.assertFalse(C.NAME_ASK.search("ומה השם של הרחוב?"))
        self.assertFalse(C.NAME_ASK.search("מה השם של הבניין?"))


class Files(unittest.TestCase):
    def test_run_reads_the_source_deck_for_expectations(self):
        with tempfile.TemporaryDirectory() as d:
            deck = {"defaults": {}, "scenarios": [
                {"id": "a", "call_has_number": True, "expect": {"ticket": False}}]}
            src = os.path.join(d, "deck_src.json")
            json.dump(deck, open(src, "w", encoding="utf-8"), ensure_ascii=False)
            json.dump({"_source": src, "defaults": {}, "scenarios": [{"id": "a"}]},
                      open(os.path.join(d, "deck.json"), "w", encoding="utf-8"))
            os.makedirs(os.path.join(d, "transcripts"))
            json.dump({"scenario": "a", "turns": [{"agent": "היי"}]},
                      open(os.path.join(d, "transcripts", "a.json"), "w", encoding="utf-8"))
            self.assertEqual(C.run(d), {"a": []})


if __name__ == "__main__":
    unittest.main()
