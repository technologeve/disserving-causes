import unittest
from unittest.mock import MagicMock, patch
from app import app
import os

class DissConnectTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test'
        self.client = app.test_client()
        
    def test_index_route(self):
        """Test the landing page loads."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Make Your Dissertation Matter', response.data)

    def test_login_page_loads(self):
        """Test login page renders."""
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome Back', response.data)

    def test_register_page_loads(self):
        """Test registration page renders."""
        response = self.client.get('/register')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Create an Account', response.data)

    @patch('app.supabase')
    def test_dashboard_redirect_if_not_logged_in(self, mock_supabase):
        """Test dashboard redirects to login if no session."""
        with self.client as c:
            response = c.get('/dashboard')
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.location.endswith('/login'))

    @patch('app.supabase')
    def test_charity_dashboard(self, mock_supabase):
        """Test charity dashboard renders projects."""
        with self.client as c:
            with c.session_transaction() as sess:
                sess['user'] = 'test-uuid'
                sess['role'] = 'charity'
            
            # Mock project response
            mock_response = MagicMock()
            mock_response.data = [{'title': 'Test Project', 'description': 'desc', 'status': 'open'}]
            mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response

            response = c.get('/dashboard')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Test Project', response.data)
            self.assertIn(b'Create New Project', response.data)

if __name__ == '__main__':
    unittest.main()
