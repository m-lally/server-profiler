"""Tests for the profiler CLI."""
import json
import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from pathlib import Path

from profiler import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestCli:
    def test_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Server Profiler" in result.output
        assert "profile" in result.output
        assert "terraform" in result.output

    def test_version(self, runner):
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "server-profiler" in result.output
        assert "0.2.0" in result.output

    def test_profile_help(self, runner):
        result = runner.invoke(cli, ["profile", "--help"])
        assert result.exit_code == 0
        assert "--host" in result.output
        assert "--key" in result.output
        assert "--lightsail-config" in result.output
        assert "--terraform" in result.output

    def test_terraform_help(self, runner):
        result = runner.invoke(cli, ["terraform", "--help"])
        assert result.exit_code == 0
        assert "--input" in result.output
        assert "--input-file" in result.output or "-i" in result.output

    def test_profile_no_args(self, runner):
        result = runner.invoke(cli, ["profile"])
        assert result.exit_code != 0
        assert "required" in result.output.lower()

    def test_profile_no_auth(self, runner):
        result = runner.invoke(cli, ["profile", "--host", "example.com"])
        assert result.exit_code != 0
        assert "key" in result.output.lower() or "password" in result.output.lower()


class TestProfileCommand:
    @patch("profiler.SSHConnector")
    @patch("profiler.ServerProfiler")
    @patch("profiler.TerraformGenerator")
    def test_full_profile_flow(self, mock_tf, mock_sp, mock_ssh, runner, sample_profile):
        mock_ssh_instance = MagicMock()
        mock_ssh_instance.connect.return_value = True
        mock_ssh.return_value = mock_ssh_instance

        mock_sp_instance = MagicMock()
        mock_sp_instance.profile_all.return_value = sample_profile
        mock_sp.return_value = mock_sp_instance

        mock_tf_instance = MagicMock()
        mock_tf.return_value = mock_tf_instance

        with runner.isolated_filesystem():
            result = runner.invoke(cli, [
                "profile",
                "--host", "example.com",
                "--key", "~/.ssh/id_rsa",
                "--terraform",
                "--output", "test_profile.json",
            ])

        assert result.exit_code == 0
        assert "Profile" in result.output
        mock_ssh_instance.connect.assert_called_once()
        mock_sp_instance.profile_all.assert_called_once()
        mock_tf_instance.generate_all.assert_called_once()
        mock_ssh_instance.close.assert_called_once()

    @patch("profiler.SSHConnector")
    @patch("profiler.ServerProfiler")
    def test_profile_no_terraform(self, mock_sp, mock_ssh, runner, sample_profile):
        mock_ssh_instance = MagicMock()
        mock_ssh_instance.connect.return_value = True
        mock_ssh.return_value = mock_ssh_instance

        mock_sp_instance = MagicMock()
        mock_sp_instance.profile_all.return_value = sample_profile
        mock_sp.return_value = mock_sp_instance

        with runner.isolated_filesystem():
            result = runner.invoke(cli, [
                "profile",
                "--host", "example.com",
                "--key", "~/.ssh/id_rsa",
                "--no-terraform",
            ])

        assert result.exit_code == 0
        # TerraformGenerator should not be called
        from profiler import TerraformGenerator

    @patch("profiler.SSHConnector")
    def test_connection_failure(self, mock_ssh, runner):
        mock_ssh_instance = MagicMock()
        mock_ssh_instance.connect.return_value = False
        mock_ssh.return_value = mock_ssh_instance

        result = runner.invoke(cli, [
            "profile",
            "--host", "example.com",
            "--key", "~/.ssh/id_rsa",
        ])

        assert result.exit_code != 0


class TestTerraformCommand:
    def test_terraform_from_profile(self, runner, sample_profile, tmp_path):
        profile_file = tmp_path / "profile.json"
        with open(profile_file, "w") as f:
            json.dump(sample_profile, f)

        result = runner.invoke(cli, [
            "terraform",
            "--input", str(profile_file),
            "--terraform-dir", str(tmp_path / "tf-output"),
        ])

        assert result.exit_code == 0
        assert "Loaded profile" in result.output

        tf_dir = tmp_path / "tf-output"
        assert (tf_dir / "main.tf").exists()
        assert (tf_dir / "variables.tf").exists()
        assert (tf_dir / "outputs.tf").exists()

    def test_terraform_missing_profile(self, runner):
        result = runner.invoke(cli, [
            "terraform",
            "--input", "/nonexistent/profile.json",
        ])

        assert result.exit_code != 0
        assert "Failed to load profile" in result.output

    def test_terraform_invalid_profile(self, runner, tmp_path):
        profile_file = tmp_path / "bad.json"
        with open(profile_file, "w") as f:
            f.write("not valid json")

        result = runner.invoke(cli, [
            "terraform",
            "--input", str(profile_file),
        ])

        assert result.exit_code != 0
