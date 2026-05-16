"""Shared fixtures and test data for server-profiler tests."""
import json
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

SAMPLE_PROFILE = {
    "os_info": {
        "name": "Debian GNU/Linux",
        "version_id": "11",
        "kernel": "5.10.0-28-cloud-amd64",
        "architecture": "x86_64",
    },
    "hardware": {
        "cpu_cores": 2,
        "cpu_model": "Intel(R) Xeon(R) CPU E5-2686 v4 @ 2.30GHz",
        "memory_mb": 1984,
    },
    "network": {
        "hostname": "web-01",
        "public_ip": "52.56.145.153",
        "interfaces": [
            {
                "name": "eth0",
                "addresses": [
                    {"family": "inet", "address": "172.26.0.5", "prefix": 20}
                ],
            }
        ],
        "listening_ports": [22, 80, 443],
    },
    "packages": ["nginx", "curl", "git"],
    "services": [
        {"name": "ssh", "status": "running"},
        {"name": "nginx", "status": "running"},
    ],
    "firewall": {
        "type": "ufw",
        "rules": ["22/tcp ALLOW Anywhere", "80/tcp ALLOW Anywhere"],
    },
    "storage": {
        "disks": [],
        "mounts": [
            {
                "filesystem": "/dev/xvda1",
                "size": "60G",
                "used": "12G",
                "available": "48G",
                "use_percent": "20%",
                "mount_point": "/",
            }
        ],
    },
    "users": [
        {"username": "admin", "uid": 1000, "gid": 1000, "home": "/home/admin", "shell": "/bin/bash"},
        {"username": "deploy", "uid": 1001, "gid": 1001, "home": "/home/deploy", "shell": "/bin/bash"},
    ],
    "cron_jobs": {"system": ["/etc/cron.daily/apt-compat"], "users": {}},
    "software": {
        "nginx": {"installed": True, "version": "nginx version: nginx/1.18.0"},
        "python": {"version": "Python 3.9.2"},
        "docker": {"version": "Docker version 20.10.5"},
    },
}


@pytest.fixture
def sample_profile():
    return SAMPLE_PROFILE.copy()


@pytest.fixture
def sample_profile_path(tmp_path, sample_profile):
    path = tmp_path / "profile.json"
    with open(path, "w") as f:
        json.dump(sample_profile, f)
    return str(path)


@pytest.fixture
def mock_ssh():
    ssh = MagicMock()
    ssh.execute_command.return_value = ("output", "", 0)
    ssh.execute_sudo_command.return_value = ("output", "", 0)
    ssh.connect.return_value = True
    return ssh


@pytest.fixture
def mock_ssh_connector():
    with patch("ssh_connector.SSHConnector") as mock:
        instance = mock.return_value
        instance.connect.return_value = True
        instance.execute_command.return_value = ("mock_output", "", 0)
        instance.execute_sudo_command.return_value = ("mock_output", "", 0)
        instance.close.return_value = None
        yield instance


@pytest.fixture
def lightsail_config_content():
    return (
        "Host my-server\n"
        "    HostName 54.123.45.67\n"
        "    User admin\n"
        "    IdentityFile ~/.ssh/key.pem\n"
        "    Port 22\n"
    )


@pytest.fixture
def lightsail_config_path(tmp_path, lightsail_config_content):
    path = tmp_path / "lightsail-ssh-config"
    with open(path, "w") as f:
        f.write(lightsail_config_content)
    return str(path)
