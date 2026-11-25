import datetime as dt
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("calendar_check", Path(__file__).with_name("check_match_calendar.py"))
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class CalendarTests(unittest.TestCase):
    def event(self, start="DTSTART;TZID=Europe/Brussels:20270417T000000", extra=""):
        return "BEGIN:VCALENDAR\nBEGIN:VEVENT\nUID:a\n" + start + "\nSUMMARY:Schoten - D1\n" + extra + "\nEND:VEVENT\nEND:VCALENDAR"

    def game(self, **changes):
        result = dict(id="123", title="Schoten - Apolloon", date="2027-04-17", time="12:45",
                      team="D1", opponent="schoten", home=False, location="Sporthal Vordensteyn")
        result.update(changes)
        return result

    def test_timezone_conversion_twizzit_utc(self):
        event = check.parse_ical(self.event("DTSTART:20270417T104500Z"))[0]
        self.assertEqual(event["time"], "12:45")

    def test_unfolding_and_escaped_location(self):
        event = check.parse_ical(self.event(extra="LOCATION:Sporthal Vor\n densteyn\\, Schoten"))[0]
        self.assertEqual(event["location"], "Sporthal Vordensteyn, Schoten")

    def test_cancelled_twizzit_is_not_active(self):
        active = self.event().replace("END:VCALENDAR", "")
        cancelled = self.event(extra="STATUS:CANCELLED").replace("BEGIN:VCALENDAR\n", "").replace("UID:a", "UID:b")
        self.assertEqual(len(check.parse_ical(active + cancelled)), 1)

    def test_invalid_calendar_fails(self):
        with self.assertRaises(ValueError):
            check.parse_ical("An error occurred.")

    def test_changed_time_is_reported(self):
        other = check.parse_ical(self.event())[0]
        rows, extras, count = check.compare([self.game()], [other])
        self.assertEqual(rows[0][0], "Uur verschilt")
        self.assertFalse(extras)
        self.assertEqual(count, 1)

    def test_same_time_is_not_a_difference(self):
        other = check.parse_ical(self.event("DTSTART;TZID=Europe/Brussels:20270417T124500",
                                            extra="LOCATION:Sporthal Vordensteyn - straat"))[0]
        self.assertFalse(check.compare([self.game()], [other])[0])

    def test_rescheduled_match_is_linked(self):
        other = check.parse_ical(self.event("DTSTART;TZID=Europe/Brussels:20270418T124500"))[0]
        self.assertIn("Mogelijke datumwijziging", check.compare([self.game()], [other])[0][0][0])

    def test_ambiguous_opponent_is_not_guessed(self):
        other = check.parse_ical(self.event())[0]
        rows, extras, count = check.compare([self.game()], [other, dict(other, id="b")])
        self.assertEqual(rows[0][0], "Mogelijke koppeling onduidelijk")
        self.assertEqual(count, 0)

    def test_short_name_keeps_reserve_team_uncertain(self):
        other = check.parse_ical(self.event())[0]
        rows, extras, count = check.compare([self.game(opponent="schoten 2")], [other])
        self.assertIn("Ploegnummer controleren", rows[0][0])
        self.assertFalse(extras)

    def test_sponsor_aliases(self):
        self.assertEqual(check.opponent("Handbal Hestia Bilzen"), check.opponent("H. Bilzen D1 M VHV (Senior M)"))
        self.assertEqual(check.opponent("Elita Lebbeke"), check.opponent("Lebbeke D1 M (Senior M)"))
        self.assertEqual(check.opponent("DHC Waasmunster M14 Regionale Beker (U14 F)"), "waasmunster")

    def test_missing_game_is_reported(self):
        self.assertEqual(check.compare([self.game()], [])[0][0][0], "Niet gevonden in Twizzit")

    def test_api_wall_clock_matches_public_clubee(self):
        payload = '{"id":123,"start_date":"2027-04-17T12:45:00+00:00"}'
        with patch.object(check, "fetch", return_value=payload):
            self.assertEqual(check.hydrate(self.game())["time"], "12:45")

    def test_alias_and_team_mapping(self):
        self.assertEqual(check.opponent("HC Don Bosco Gent 2"), check.opponent("DB Gent U12 VHV R 2 (U12 M)"))
        self.assertEqual(check.team_code("Apolloon G14 VHV R (U14 F)"), "M14")
        self.assertEqual(check.team_code("Apolloon D1 M VHV (Senior M)"), "H2")

    def test_failed_sources_never_report_success(self):
        report = check.render([], [], ["Clubee niet bereikbaar"], dt.date(2026, 11, 25))
        self.assertIn("ONVOLLEDIGE CONTROLE", report)
        self.assertNotIn("Geen verschillen gevonden", report)

    def test_gmail_delivery_uses_tls_and_requested_recipient(self):
        with patch.dict(check.os.environ, {"SMTP_PASSWORD": "app password"}, clear=True):
            with patch.object(check.smtplib, "SMTP") as smtp:
                check.send_report("rapport", "peter.delrue@gmail.com")
                smtp.assert_called_once_with("smtp.gmail.com", 587, timeout=30)
                session = smtp.return_value.__enter__.return_value
                session.starttls.assert_called_once()
                session.login.assert_called_once_with("peter.delrue@gmail.com", "apppassword")
                message = session.send_message.call_args.args[0]
                self.assertEqual(message["To"], "peter.delrue@gmail.com")
                self.assertIn("rapport", message.get_content())

    def test_smtp_missing_secrets_fails_before_sending(self):
        with patch.dict(check.os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "SMTP_PASSWORD"):
                check.send_report("test", "recipient@example.com")


if __name__ == "__main__":
    unittest.main()
