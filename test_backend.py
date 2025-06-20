
import unittest
import json
from app import app 

class BackendTest(unittest.TestCase):

    def setUp(self):
        """Set up a test client for each test."""
        self.app = app.test_client()
        self.app.testing = True

    def test_01_login_and_get_token(self):
        """Test the login endpoint and token generation."""
        response = self.app.post('/login',
                                 data=json.dumps({'username': 'testuser', 'password': 'test'}),
                                 content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('access_token', data)

    def test_02_alert_endpoint_with_valid_token(self):
        """Test the /alert endpoint with a valid JWT."""
        # First, log in to get a token
        login_response = self.app.post('/login',
                                       data=json.dumps({'username': 'testuser', 'password': 'test'}),
                                       content_type='application/json')
        token = json.loads(login_response.data)['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        
        alert_response = self.app.post('/alert',
                                       data=json.dumps({
                                           'user_id': 1,
                                           'emergency_type': 'Medical',
                                           'location': 'Library'
                                       }),
                                       content_type='application/json',
                                       headers=headers)
        self.assertEqual(alert_response.status_code, 200)
        response_data = json.loads(alert_response.data)
        self.assertIn('Alert received', response_data['status'])
        
    def test_03_alert_endpoint_without_token(self):
        """Test that the /alert endpoint is protected."""
        response = self.app.post('/alert',
                                 data=json.dumps({
                                     'user_id': 1, 'emergency_type': 'Medical', 'location': 'Library'
                                 }),
                                 content_type='application/json')
        # Expecting 401 Unauthorized
        self.assertEqual(response.status_code, 401)

if __name__ == '__main__':
    unittest.main(verbosity=2)
