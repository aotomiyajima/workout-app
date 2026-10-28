import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

import app as workout_app


class WorkoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.original_database = workout_app.DATABASE
        workout_app.DATABASE = Path(self.temp.name) / "workouts.db"
        # 変更前と同じ構造・データから移行を検証する。
        with closing(sqlite3.connect(workout_app.DATABASE)) as conn:
            conn.execute("CREATE TABLE workouts (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                         "workout_name TEXT NOT NULL, weight REAL NOT NULL, "
                         "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
            conn.execute("INSERT INTO workouts (workout_name, weight) VALUES ('過去の投稿', 20)")
            conn.commit()
        workout_app.init_db()
        self.client = workout_app.app.test_client()

    def tearDown(self):
        workout_app.DATABASE = self.original_database
        self.temp.cleanup()

    def rows(self):
        conn = workout_app.get_db_connection()
        try:
            return [dict(row) for row in conn.execute("SELECT * FROM workouts ORDER BY id")]
        finally:
            conn.close()

    def test_migration_and_legacy_edit(self):
        workout_app.init_db()  # 再起動相当の初期化でも既存データは残る。
        self.assertEqual(len(self.rows()), 1)
        self.assertIsNone(self.rows()[0]['reps'])
        self.assertIn('回数：未設定', self.client.get('/').get_data(as_text=True))
        self.assertIn('value="" required', self.client.get('/edit/1').get_data(as_text=True))
        response = self.client.post('/edit/1', data={'workout_name': '過去の投稿', 'weight': '20'})
        self.assertEqual(response.status_code, 400)
        self.assertIsNone(self.rows()[0]['sets'])
        response = self.client.post('/edit/1', data={'workout_name': '更新', 'weight': '25', 'reps': '8', 'sets': '2'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual((self.rows()[0]['reps'], self.rows()[0]['sets']), (8, 2))

    def test_create_edit_delete_and_persistence(self):
        data = {'workout_name': 'ベンチプレス', 'weight': '40', 'reps': '10', 'sets': '3'}
        self.assertEqual(self.client.post('/', data=data).status_code, 302)
        workout_app.init_db()
        client = workout_app.app.test_client()
        self.assertIn('ベンチプレス 40kg × 10回 × 3セット', client.get('/').get_data(as_text=True))
        html = client.get('/edit/2').get_data(as_text=True)
        self.assertIn('value="10" required', html)
        data.update(reps='12', sets='4')
        self.assertEqual(client.post('/edit/2', data=data).status_code, 302)
        self.assertEqual((self.rows()[1]['reps'], self.rows()[1]['sets']), (12, 4))
        self.assertEqual(client.post('/delete/2').status_code, 302)
        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(client.get('/edit/999').status_code, 404)

    def test_invalid_values_do_not_change_database(self):
        before = self.rows()
        for url in ('/', '/edit/1'):
            for field in ('reps', 'sets'):
                for invalid in ('', '0', '-1', '1.5', 'abc', '9223372036854775808'):
                    with self.subTest(url=url, field=field, invalid=invalid):
                        data = {'workout_name': '保持する種目', 'weight': '40', 'reps': '10', 'sets': '3'}
                        data[field] = invalid
                        response = self.client.post(url, data=data)
                        self.assertEqual(response.status_code, 400)
                        html = response.get_data(as_text=True)
                        self.assertIn('1以上の整数', html)
                        self.assertIn('value="保持する種目"', html)
                        self.assertIn(f'value="{invalid}"', html)
                        self.assertEqual(self.rows(), before)


if __name__ == '__main__':
    unittest.main()
