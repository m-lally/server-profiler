"""Tests for the SSH connector module."""
import pytest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path

from ssh_connector import SSHConnector, parse_lightsail_config


class TestParseLightsailConfig:
    def test_parse_valid_config(self, lightsail_config_path):
        result = parse_lightsail_config(lightsail_config_path, "my-server")
        assert result["host"] == "54.123.45.67"
        assert result["username"] == "admin"
        assert result["key_file"] == "~/.ssh/key.pem"
        assert result["port"] == 22

    def test_parse_nonexistent_config(self):
        with pytest.raises(FileNotFoundError):
            parse_lightsail_config("/nonexistent/config", "my-server")

    def test_parse_unknown_host(self, lightsail_config_path):
        result = parse_lightsail_config(lightsail_config_path, "unknown")
        assert result["host"] == "unknown"
        assert result["username"] == "admin"
        assert result["key_file"] == ""
        assert result["port"] == 22

    def test_parse_missing_file(self):
        with pytest.raises(FileNotFoundError):
            parse_lightsail_config("~/nonexistent_file", "any-host")

    def test_parse_multiple_hosts(self, tmp_path):
        content = (
            "Host web\n"
            "    HostName 10.0.0.1\n"
            "    User ubuntu\n"
            "    IdentityFile ~/.ssh/web.pem\n"
            "    Port 2222\n"
            "\n"
            "Host db\n"
            "    HostName 10.0.0.2\n"
            "    User admin\n"
            "    IdentityFile ~/.ssh/db.pem\n"
            "    Port 22\n"
        )
        path = tmp_path / "multi_config"
        with open(path, "w") as f:
            f.write(content)

        web = parse_lightsail_config(str(path), "web")
        db = parse_lightsail_config(str(path), "db")

        assert web["host"] == "10.0.0.1"
        assert web["username"] == "ubuntu"
        assert web["port"] == 2222
        assert db["host"] == "10.0.0.2"


class TestSSHConnector:
    def test_init(self):
        conn = SSHConnector(host="test.host", username="admin",
                            key_file="~/.ssh/key.pem", port=2222)
        assert conn.host == "test.host"
        assert conn.username == "admin"
        assert conn.key_file == "~/.ssh/key.pem"
        assert conn.port == 2222

    def test_init_default_port(self):
        conn = SSHConnector(host="test.host", username="admin",
                            key_file="~/.ssh/key.pem")
        assert conn.port == 22

    def test_init_password(self):
        conn = SSHConnector(host="test.host", username="admin",
                            password="secret")
        assert conn.password == "secret"

    @patch("ssh_connector.paramiko.SSHClient")
    def test_connect_with_key(self, mock_ssh_client):
        mock_client = MagicMock()
        mock_ssh_client.return_value = mock_client

        conn = SSHConnector(host="test.host", username="admin",
                            key_file="/tmp/test_key.pem")

        with patch("pathlib.Path.exists", return_value=True):
            conn.connect()

        mock_client.set_missing_host_key_policy.assert_called_once()
        mock_client.connect.assert_called_once_with(
            hostname="test.host",
            username="admin",
            port=22,
            timeout=10,
            key_filename="/tmp/test_key.pem"
        )

    @patch("ssh_connector.paramiko.SSHClient")
    def test_connect_with_password(self, mock_ssh_client):
        mock_client = MagicMock()
        mock_ssh_client.return_value = mock_client

        conn = SSHConnector(host="test.host", username="admin",
                            password="secret")
        result = conn.connect()

        assert result is True
        mock_client.connect.assert_called_once_with(
            hostname="test.host",
            username="admin",
            port=22,
            timeout=10,
            password="secret"
        )

    @patch("ssh_connector.paramiko.SSHClient")
    def test_connect_no_auth(self, mock_ssh_client):
        conn = SSHConnector(host="test.host", username="admin")
        result = conn.connect()
        assert result is False

    @patch("ssh_connector.paramiko.SSHClient")
    def test_connect_key_not_found(self, mock_ssh_client):
        conn = SSHConnector(host="test.host", username="admin",
                            key_file="/nonexistent/key.pem")

        with patch("pathlib.Path.exists", return_value=False):
            result = conn.connect()

        assert result is False

    @patch("ssh_connector.paramiko.SSHClient")
    def test_execute_command(self, mock_ssh_client):
        mock_client = MagicMock()
        mock_ssh_client.return_value = mock_client

        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b"output_text"
        mock_stderr = MagicMock()
        mock_stderr.read.return_value = b""
        mock_channel = MagicMock()
        mock_channel.recv_exit_status.return_value = 0
        mock_stdout.channel = mock_channel

        mock_client.exec_command.return_value = (None, mock_stdout, mock_stderr)

        conn = SSHConnector(host="test.host", username="admin", password="pwd")
        conn.client = mock_client

        stdout, stderr, exit_code = conn.execute_command("ls -la")

        assert stdout == "output_text"
        assert exit_code == 0
        mock_client.exec_command.assert_called_once_with("ls -la")

    def test_execute_command_not_connected(self):
        conn = SSHConnector(host="test.host", username="admin", password="pwd")
        with pytest.raises(RuntimeError, match="Not connected"):
            conn.execute_command("ls")

    @patch("ssh_connector.paramiko.SSHClient")
    def test_execute_sudo_command(self, mock_ssh_client):
        conn = SSHConnector(host="test.host", username="admin", password="pwd")
        conn.client = MagicMock()
        conn.execute_command = MagicMock(return_value=("", "", 0))

        conn.execute_sudo_command("apt update", sudo_password="s3cret")

        conn.execute_command.assert_called_once_with(
            "echo 's3cret' | sudo -S apt update"
        )

    @patch("ssh_connector.paramiko.SSHClient")
    def test_execute_sudo_command_no_password(self, mock_ssh_client):
        conn = SSHConnector(host="test.host", username="admin", password="pwd")
        conn.client = MagicMock()
        conn.execute_command = MagicMock(return_value=("", "", 0))

        conn.execute_sudo_command("apt update")

        conn.execute_command.assert_called_once_with("sudo apt update")

    @patch("ssh_connector.paramiko.SSHClient")
    def test_read_file(self, mock_ssh_client):
        conn = SSHConnector(host="test.host", username="admin", password="pwd")
        conn.client = MagicMock()
        conn.execute_command = MagicMock(
            return_value=("file contents\nline 2", "", 0)
        )

        content = conn.read_file("/etc/hostname")

        assert content == "file contents\nline 2"
        conn.execute_command.assert_called_once_with("cat /etc/hostname")

    @patch("ssh_connector.paramiko.SSHClient")
    def test_read_file_failure(self, mock_ssh_client):
        conn = SSHConnector(host="test.host", username="admin", password="pwd")
        conn.client = MagicMock()
        conn.execute_command = MagicMock(return_value=("", "not found", 1))

        content = conn.read_file("/nonexistent")

        assert content is None

    @patch("ssh_connector.paramiko.SSHClient")
    def test_close(self, mock_ssh_client):
        conn = SSHConnector(host="test.host", username="admin", password="pwd")
        mock_client = MagicMock()
        conn.client = mock_client

        conn.close()

        mock_client.close.assert_called_once()
        assert conn.client is None

    @patch("ssh_connector.paramiko.SSHClient")
    def test_context_manager(self, mock_ssh_client):
        mock_client = MagicMock()
        mock_ssh_client.return_value = mock_client

        conn = SSHConnector(host="test.host", username="admin", password="pwd")

        with patch("pathlib.Path.exists", return_value=True):
            with conn as c:
                assert c is conn

        mock_client.connect.assert_called_once()
        mock_client.close.assert_called_once()
