import unittest
from unittest.mock import patch, MagicMock
from app import app

class SettingsTest(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    @patch('app.routes.get_db_connection')
    def test_update_thresholds(self, mock_db):
        # Fake DB connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.is_connected.return_value = True
        mock_db.return_value = mock_conn

        # Fake form data to update thresholds
        form_data = {
            'temperature_min': '18',
            'temperature_max': '30'
        }

        # Send POST request
        response = self.client.post('/settings', data=form_data)

        # Check if SQL was called correctly
        self.assertIn(
            unittest.mock.call("UPDATE optimal_ranges SET min_value = %s WHERE parameter = %s", ('18', 'temperature')),
            mock_cursor.execute.call_args_list
        )

        self.assertIn(
            unittest.mock.call("UPDATE optimal_ranges SET max_value = %s WHERE parameter = %s", ('30', 'temperature')),
            mock_cursor.execute.call_args_list
        )

        # Check redirect and commit
        mock_conn.commit.assert_called_once()
        self.assertEqual(response.status_code, 302)

if __name__ == '__main__':
    unittest.main()
