"""End-to-end checks use temporary data, never the normal data directory."""
import contextlib
import io
import json
import os
import secrets
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as system


class LocalSystemTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config_values = {}
        for key, value in {
            "DATA_DIR": Path(self.temp.name),
            "USER_FILE": Path(self.temp.name) / "users.json",
            "ADMIN_CONFIG": Path(self.temp.name) / "admin.json",
            "BLOCKCHAIN_FILE": Path(self.temp.name) / "blockchain.json",
            "BLOCKCHAIN_BACKUP": Path(self.temp.name) / "blockchain_backup.json",
        }.items():
            self.config_values[key] = getattr(system.Config, key)
            setattr(system.Config, key, value)
        self.addCleanup(self.restore_config)
        self.admin_password = secrets.token_urlsafe(14)
        self.environment = patch.dict(os.environ, {
            "STOCK_ADMIN_USERNAME": "admin",
            "STOCK_ADMIN_PASSWORD": self.admin_password,
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)
        self.application = system.create_app()
        self.application.testing = True
        self.client = self.application.test_client()
        self.username = "release_user"
        self.password = "Local-Demo-12345"

    def restore_config(self):
        for key, value in self.config_values.items():
            setattr(system.Config, key, value)

    def register_and_login(self, client=None, password=None):
        client = client or self.client
        password = password or self.password
        result = client.post("/register", json={
            "username": self.username, "password": password, "confirm_pwd": password,
        }).get_json()
        self.assertEqual(result["status"], "success", result)
        self.login(client, password)

    def login(self, client, password):
        captcha = client.get("/get_captcha").get_json()["captcha"]
        result = client.post("/login", json={
            "username": self.username, "password": password, "captcha": captcha,
        }).get_json()
        self.assertEqual(result["status"], "success", result)

    def test_fresh_install_and_local_pages(self):
        self.assertTrue(system.Config.USER_FILE.exists())
        self.assertTrue(system.Config.ADMIN_CONFIG.exists())
        self.assertTrue(system.Config.BLOCKCHAIN_FILE.exists())
        self.assertEqual(system.DataManager.load_users(), {})
        self.assertNotIn(self.admin_password, system.Config.ADMIN_CONFIG.read_text(encoding="utf-8"))
        for url in ("/login", "/register", "/admin/login", "/static/bootstrap.min.css", "/static/bootstrap.bundle.min.js"):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                response.close()
        self.assertNotIn("cdn.jsdelivr.net", self.client.get("/login").get_data(as_text=True))
        result = self.client.post("/admin/login", json={
            "username": "admin", "password": self.admin_password,
        }).get_json()
        self.assertEqual(result["status"], "success", result)
        for url in ("/admin/dashboard", "/admin/users", "/admin/blockchain"):
            self.assertEqual(self.client.get(url).status_code, 200, url)
        before = system.Config.ADMIN_CONFIG.read_bytes()
        system.create_app()
        self.assertEqual(before, system.Config.ADMIN_CONFIG.read_bytes())

    def test_user_trade_persistence_and_password_flow(self):
        self.assertEqual(self.client.get("/").status_code, 302)
        self.register_and_login()
        for url in ("/", "/profile"):
            self.assertEqual(self.client.get(url).status_code, 200, url)
        for trade_type, quantity in (("buy", 3), ("sell", 1)):
            result = self.client.post("/trade", json={
                "code": "600036", "type": trade_type, "quantity": quantity,
            }).get_json()
            self.assertEqual(result["status"], "success", result)
            self.assertIn("block_index", result)
        user = system.DataManager.load_users()[self.username]
        self.assertEqual(user["holdings"][0]["quantity"], 2)
        self.assertEqual(user["balance"], 49934.88)
        self.assertEqual(len(user["trade_records"]), 2)
        self.assertNotIn(self.password, system.Config.USER_FILE.read_text(encoding="utf-8"))
        chain = self.client.get("/blockchain_info").get_json()
        self.assertTrue(chain["is_valid"])
        self.assertEqual(chain["chain_length"], 3)
        self.assertEqual(chain["user_trade_count"], 2)
        new_app = system.create_app()
        new_app.testing = True
        new_client = new_app.test_client()
        self.login(new_client, self.password)
        self.assertEqual(new_client.get("/blockchain_info").get_json()["chain_length"], 3)
        result = new_client.post("/change_pwd", json={
            "old_pwd": self.password, "new_pwd": "Changed-Demo-12345", "confirm_pwd": "Changed-Demo-12345",
        }).get_json()
        self.assertEqual(result["status"], "success", result)
        new_client.get("/logout")
        self.login(new_client, "Changed-Demo-12345")
        admin = new_app.test_client()
        result = admin.post("/admin/login", json={"username": "admin", "password": self.admin_password}).get_json()
        self.assertEqual(result["status"], "success", result)
        for url in ("/admin/dashboard", "/admin/users?user=release_user", "/admin/blockchain"):
            self.assertEqual(admin.get(url).status_code, 200, url)
        self.assertEqual(admin.get("/admin/backup_blockchain").get_json()["status"], "success")
        self.assertTrue(system.Config.BLOCKCHAIN_BACKUP.exists())

    def test_invalid_requests_do_not_change_balances_or_chain(self):
        self.assertEqual(self.client.post("/trade", json={}).get_json()["status"], "error")
        self.assertEqual(self.client.post("/register", json={"username": "", "password": "", "confirm_pwd": ""}).get_json()["status"], "error")
        self.register_and_login()
        for order in (
            {"code": "600036", "type": "buy", "quantity": -1},
            {"code": "600036", "type": "sell", "quantity": 1},
            {"code": "600036", "type": "buy", "quantity": 10001},
            {"code": "no-stock", "type": "buy", "quantity": 1},
        ):
            self.assertEqual(self.client.post("/trade", json=order).get_json()["status"], "error", order)
        self.assertEqual(system.DataManager.load_users()[self.username]["balance"], 50000.0)
        self.assertEqual(self.client.get("/blockchain_info").get_json()["chain_length"], 1)
        result = self.client.post("/trade", json={"code": "600036", "type": "buy", "quantity": 1}).get_json()
        self.assertEqual(result["status"], "success", result)
        chain = system.Blockchain(persist_file=system.Config.BLOCKCHAIN_FILE)
        chain.chain[-1].transactions[0]["quantity"] += 1
        self.assertFalse(chain.is_chain_valid())


if __name__ == "__main__":
    unittest.main(verbosity=2)
