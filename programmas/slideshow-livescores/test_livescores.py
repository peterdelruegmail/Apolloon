import unittest
from unittest.mock import patch
import livescores


def game(identifier, home='HBC Apolloon Spurs U14', away='Gent', date='2026-11-24', time='19:00'):
    return dict(id=identifier, home=home, away=away, date=date, time=time, score=None)


class ClubScoresTests(unittest.TestCase):
    def setUp(self):
        livescores._club_calendar = None
        self.items = [dict(name='Heren', source='men'), dict(name='Jeugd', source='youth')]

    def tearDown(self):
        livescores._club_calendar = None

    def test_home_away_youth_deduplication_order_and_cache_isolation(self):
        calendars = {'men': [game('2', home='Gent', away='Apolloon Spurs', time='20:00'),
                              game('9', home='Gent', away='Brugge')],
                     'youth': [game('1'), game('2', home='Gent', away='Apolloon Spurs', time='20:00'),
                               game('3', home='Apolloontest', away='Brugge')]}
        with patch.object(livescores, 'competitions', return_value=self.items) as menu, \
             patch.object(livescores, 'games', side_effect=lambda source: calendars[source]) as fetch:
            result = livescores.club_games()
            self.assertEqual([g['id'] for g in result], ['1', '2'])
            result[0]['score'] = 'OLD (niet bijgewerkt)'
            self.assertIsNone(livescores.club_games()[0]['score'])
            self.assertEqual(fetch.call_count, 2)
            self.assertEqual(menu.call_count, 1)

    def test_incomplete_scan_raises_and_is_not_cached(self):
        def fetch(source):
            if source == 'youth':
                raise ConnectionError('offline')
            return [game('1')]
        with patch.object(livescores, 'competitions', return_value=self.items), \
             patch.object(livescores, 'games', side_effect=fetch):
            with self.assertRaisesRegex(ConnectionError, 'Jeugd: offline'):
                livescores.club_games()
        self.assertIsNone(livescores._club_calendar)

    def test_expired_cache_is_rescanned(self):
        livescores._club_calendar = (0, [game('old')])
        with patch.object(livescores.time, 'monotonic', return_value=301), \
             patch.object(livescores, 'competitions', return_value=self.items), \
             patch.object(livescores, 'games', return_value=[game('new')]):
            self.assertEqual(livescores.club_games()[0]['id'], 'new')

    def test_date_boundaries_and_score_failure(self):
        calendar = [game('1', date='2026-11-23'), game('2'), game('3', date='2026-11-25')]
        with patch.object(livescores, 'club_games', return_value=calendar), \
             patch.object(livescores, 'live_game', side_effect=ConnectionError('offline')):
            selected, failures = livescores.load_scores(livescores.CLUB_SOURCE, '2026-11-23', '2026-11-24')
        self.assertEqual([g['id'] for g in selected], ['1', '2'])
        self.assertEqual(failures, 2)
        self.assertTrue(all('niet bijgewerkt' in g['score'] for g in selected))

    def test_specific_division_still_includes_opponents(self):
        other = game('9', home='Gent', away='Brugge')
        with patch.object(livescores, 'games', return_value=[other]), \
             patch.object(livescores, 'club_games') as club, \
             patch.object(livescores, 'live_game', side_effect=lambda g: dict(g, score='0 - 0')):
            selected, failures = livescores.load_scores('division', '2026-11-24', '2026-11-24')
        self.assertEqual(selected[0]['score'], '0 - 0')
        self.assertEqual(failures, 0)
        club.assert_not_called()

    def test_source_validation(self):
        self.assertTrue(livescores.valid_source(livescores.CLUB_SOURCE))
        self.assertFalse(livescores.valid_source(livescores.CLUB_SOURCE, allow_club=False))
        self.assertTrue(livescores.valid_source(livescores.ROOT + '/first-division-m--982001v4'))
        self.assertFalse(livescores.valid_source('https://example.org/testv4'))


class SettingsChoiceTests(unittest.TestCase):
    def test_choices_save_reload_and_old_division_settings(self):
        import tempfile
        from pathlib import Path
        import slideshow
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(slideshow, 'CONFIG', Path(folder) / 'settings.ini'), \
             patch.object(slideshow.Settings, 'load_divisions'), \
             patch.object(slideshow.messagebox, 'showerror') as error:
            settings = slideshow.Settings()
            settings.root.withdraw()
            try:
                self.assertIn(livescores.CLUB_LABEL, settings.divisions)
                settings.division_choice.set(livescores.CLUB_LABEL)
                settings.division_box.event_generate('<<ComboboxSelected>>')
                settings.root.update()
                self.assertTrue(settings.save())
                self.assertEqual(slideshow.read_config().get('LiveScores', 'Source'), livescores.CLUB_SOURCE)
                items = [dict(name='Testreeks', source=livescores.ROOT + '/testv4')]
                settings.apply_divisions(items)
                self.assertEqual(settings.division_choice.get(), livescores.CLUB_LABEL)
                settings.division_choice.set('Testreeks')
                settings.division_box.event_generate('<<ComboboxSelected>>')
                settings.root.update()
                self.assertTrue(settings.save())
                saved = slideshow.read_config()
                self.assertEqual(saved.get('LiveScores', 'Source'), items[0]['source'])
                self.assertEqual(saved.get('LiveScores', 'Division'), 'Testreeks')
                settings.apply_divisions(items)
                self.assertEqual(settings.division_choice.get(), 'Testreeks')
                error.assert_not_called()
            finally:
                settings.root.destroy()
            restored = slideshow.Settings()
            restored.root.withdraw()
            try:
                self.assertEqual(restored.values[('LiveScores', 'Source')].get(), items[0]['source'])
                self.assertEqual(restored.division_choice.get(), 'Testreeks')
                self.assertIn(livescores.CLUB_LABEL, restored.divisions)
            finally:
                restored.root.destroy()


if __name__ == '__main__':
    unittest.main()
