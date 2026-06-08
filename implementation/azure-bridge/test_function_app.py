import json
import os
import unittest
from unittest.mock import MagicMock, patch

# Ensure function_app imports work
os.environ.setdefault("KEY_VAULT_URL", "https://test-vault.vault.azure.net/")

import function_app


class TestStorePassword(unittest.TestCase):
    def setUp(self):
        self._patch_credential = patch("function_app.DefaultAzureCredential")
        self.mock_credential_cls = self._patch_credential.start()
        self.mock_credential = MagicMock()
        self.mock_credential_cls.return_value = self.mock_credential

        self._patch_client = patch("function_app.SecretClient")
        self.mock_client_cls = self._patch_client.start()
        self.mock_client = MagicMock()
        self.mock_client_cls.return_value = self.mock_client

        # Simulate AKV set_secret response
        mock_secret = MagicMock()
        mock_secret.properties.version = "abc123"
        self.mock_client.set_secret.return_value = mock_secret

    def tearDown(self):
        self._patch_credential.stop()
        self._patch_client.stop()

    def _build_request(self, body: dict, headers: dict = None):
        from azure.functions import HttpRequest
        req_body = json.dumps(body).encode("utf-8")
        return HttpRequest(
            method="POST",
            url="/api/StoreTestOperatorPassword",
            headers=headers or {},
            body=req_body,
        )

    def test_success(self):
        req = self._build_request({
            "operatorId": "test_user_01",
            "newPassword": "MyNewPass123!",
            "timestamp": "2025-06-08T14:30:00Z",
            "environment": "test",
        })
        resp = function_app.main(req)
        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.get_body())
        self.assertEqual(data["status"], "stored")
        self.assertEqual(data["secretName"], "pega-test-op-test_user_01")
        self.mock_client.set_secret.assert_called_once()
        call_args = self.mock_client.set_secret.call_args
        self.assertEqual(call_args[0][0], "pega-test-op-test_user_01")
        self.assertEqual(call_args[0][1], "MyNewPass123!")
        self.assertEqual(call_args[1]["tags"]["operator-id"], "test_user_01")

    def test_missing_operator_id(self):
        req = self._build_request({"newPassword": "pass"})
        resp = function_app.main(req)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("operatorId", resp.get_body().decode())

    def test_missing_password(self):
        req = self._build_request({"operatorId": "user1"})
        resp = function_app.main(req)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("newPassword", resp.get_body().decode())

    def test_invalid_operator_id(self):
        req = self._build_request({"operatorId": "user@bad!", "newPassword": "pass"})
        resp = function_app.main(req)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Invalid operatorId", resp.get_body().decode())

    def test_password_never_logged(self):
        # The function should not leak password into logs even on error paths
        with patch("function_app.logger") as mock_logger:
            req = self._build_request({
                "operatorId": "user1",
                "newPassword": "Secret456!",
            })
            # Force AKV error
            self.mock_client.set_secret.side_effect = Exception("AKV down")
            resp = function_app.main(req)
            self.assertEqual(resp.status_code, 500)
            # Ensure no log call contains the password
            for call in mock_logger.method_calls:
                for arg in call.args:
                    self.assertNotIn("Secret456!", str(arg))
                for kwarg in call.kwargs.values():
                    self.assertNotIn("Secret456!", str(kwarg))


if __name__ == "__main__":
    unittest.main()
