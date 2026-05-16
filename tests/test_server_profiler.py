"""Tests for the ServerProfiler class."""
import json
import pytest
from unittest.mock import MagicMock, PropertyMock
from pathlib import Path

from server_profiler import ServerProfiler


class TestGetOsInfo:
    def test_os_info_full(self, mock_ssh):
        mock_ssh.execute_command.side_effect = [
            ('NAME="Debian GNU/Linux"\nVERSION_ID="11"\n', "", 0),
            ("5.10.0-28-cloud-amd64", "", 0),
            ("x86_64", "", 0),
        ]
        profiler = ServerProfiler(mock_ssh)
        info = profiler.get_os_info()
        assert info["name"] == "Debian GNU/Linux"
        assert info["version_id"] == "11"
        assert info["kernel"] == "5.10.0-28-cloud-amd64"
        assert info["architecture"] == "x86_64"

    def test_os_info_minimal(self, mock_ssh):
        mock_ssh.execute_command.side_effect = [
            ("", "", 0),
            ("6.8.0", "", 0),
            ("aarch64", "", 0),
        ]
        profiler = ServerProfiler(mock_ssh)
        info = profiler.get_os_info()
        assert info["kernel"] == "6.8.0"
        assert info["architecture"] == "aarch64"


class TestGetHardwareInfo:
    def test_hardware_info(self, mock_ssh):
        mock_ssh.execute_command.side_effect = [
            ("4", "", 0),
            ("model name : Intel(R) Xeon(R) CPU\n", "", 0),
            ("Mem:  16384  2048  12288\n", "", 0),
        ]
        profiler = ServerProfiler(mock_ssh)
        info = profiler.get_hardware_info()
        assert info["cpu_cores"] == 4
        assert "Xeon" in info["cpu_model"]
        assert info["memory_mb"] == 16384

    def test_hardware_no_cpu_model(self, mock_ssh):
        mock_ssh.execute_command.side_effect = [
            ("2", "", 0),
            ("", "", 0),
            ("Mem:  4096  1024  3072\n", "", 0),
        ]
        profiler = ServerProfiler(mock_ssh)
        info = profiler.get_hardware_info()
        assert info["cpu_cores"] == 2
        assert "cpu_model" not in info


class TestGetNetworkInfo:
    def test_network_info(self, mock_ssh):
        mock_ssh.execute_command.side_effect = [
            ("web-01", "", 0),
            ("52.56.145.153", "", 0),
            ('[{"ifname":"eth0","addr_info":[{"family":"inet","local":"10.0.0.5","prefixlen":24}]},{"ifname":"lo","addr_info":[]}]', "", 0),
            ("tcp   LISTEN 0      128    0.0.0.0:22        0.0.0.0:*\n"
             "tcp   LISTEN 0      128    0.0.0.0:80        0.0.0.0:*\n", "", 0),
        ]
        profiler = ServerProfiler(mock_ssh)
        info = profiler.get_network_info()
        assert info["hostname"] == "web-01"
        assert info["public_ip"] == "52.56.145.153"
        assert len(info["interfaces"]) == 1
        assert info["interfaces"][0]["name"] == "eth0"
        assert info["listening_ports"] == [22, 80]

    def test_network_no_public_ip(self, mock_ssh):
        mock_ssh.execute_command.side_effect = [
            ("server", "", 0),
            ("", "", 1),
            ("[]", "", 0),
            ("", "", 0),
        ]
        profiler = ServerProfiler(mock_ssh)
        info = profiler.get_network_info()
        assert info["hostname"] == "server"
        assert info["public_ip"] is None


class TestGetInstalledPackages:
    def test_apt_packages(self, mock_ssh):
        mock_ssh.execute_command.return_value = (
            "nginx\ncurl\ngit\npython3\n", "", 0
        )
        profiler = ServerProfiler(mock_ssh)
        packages = profiler.get_installed_packages()
        assert packages == ["nginx", "curl", "git", "python3"]

    def test_no_packages(self, mock_ssh):
        mock_ssh.execute_command.return_value = ("", "", 1)
        profiler = ServerProfiler(mock_ssh)
        assert profiler.get_installed_packages() == []


class TestGetServices:
    def test_running_services(self, mock_ssh):
        mock_ssh.execute_command.return_value = (
            "ssh.service      loaded active running   OpenBSD Secure Shell server\n"
            "nginx.service    loaded active running   Nginx web server\n",
            "", 0,
        )
        profiler = ServerProfiler(mock_ssh)
        services = profiler.get_services()
        assert len(services) == 2
        assert services[0]["name"] == "ssh"
        assert services[1]["name"] == "nginx"

    def test_no_services(self, mock_ssh):
        mock_ssh.execute_command.return_value = ("", "", 0)
        profiler = ServerProfiler(mock_ssh)
        assert profiler.get_services() == []


class TestGetFirewallRules:
    def test_ufw_active(self, mock_ssh):
        mock_ssh.execute_sudo_command.side_effect = [
            ("Status: active\n22/tcp ALLOW Anywhere\n80/tcp ALLOW Anywhere\n", "", 0),
            ("", "", 0),
        ]
        profiler = ServerProfiler(mock_ssh)
        firewall = profiler.get_firewall_rules()
        assert firewall["type"] == "ufw"
        assert len(firewall["rules"]) == 2

    def test_no_firewall(self, mock_ssh):
        mock_ssh.execute_sudo_command.side_effect = [
            ("Status: inactive\n", "", 0),
            ("", "", 0),
        ]
        profiler = ServerProfiler(mock_ssh)
        firewall = profiler.get_firewall_rules()
        assert firewall["type"] is None


class TestGetStorageInfo:
    def test_storage_info(self, mock_ssh):
        mock_ssh.execute_command.side_effect = [
            (
                "Filesystem      Size  Used Avail Use% Mounted on\n"
                "/dev/xvda1       60G   12G   48G  20% /\n"
                "tmpfs           1.9G     0  1.9G   0% /dev/shm\n",
                "", 0,
            ),
            ('{"blockdevices": [{"name": "xvda"}]}', "", 0),
        ]
        profiler = ServerProfiler(mock_ssh)
        storage = profiler.get_storage_info()
        assert len(storage["mounts"]) == 1
        assert storage["mounts"][0]["mount_point"] == "/"
        assert storage["mounts"][0]["size"] == "60G"
        assert storage["disks"] == [{"name": "xvda"}]


class TestGetUsers:
    def test_user_list(self, mock_ssh):
        mock_ssh.execute_command.return_value = (
            "root:x:0:0:root:/root:/bin/bash\n"
            "admin:x:1000:1000:admin:/home/admin:/bin/bash\n"
            "deploy:x:1001:1001:deploy:/home/deploy:/bin/bash\n",
            "", 0,
        )
        profiler = ServerProfiler(mock_ssh)
        users = profiler.get_users()
        assert len(users) == 2
        assert users[0]["username"] == "admin"
        assert users[1]["username"] == "deploy"


class TestDetectInstalledSoftware:
    def test_web_servers(self, mock_ssh):
        mock_ssh.execute_command.side_effect = [
            ("/usr/sbin/nginx", "", 0),
            ("nginx version: nginx/1.18.0\n", "", 0),
            ("", "", 1),
            ("", "", 1),
            ("", "", 1),
            ("", "", 1),
            ("", "", 1),
            ("Python 3.9.2", "", 0),
            ("", "", 1),
            ("", "", 1),
            ("", "", 1),
            ("", "", 1),
            ("", "", 1),
            ("", "", 1),
        ]
        profiler = ServerProfiler(mock_ssh)
        sw = profiler.detect_installed_software()
        assert "nginx" in sw
        assert sw["nginx"]["installed"] is True
        assert "nginx" in sw["nginx"]["version"]
        assert "python" in sw
        assert sw["python"]["version"] == "Python 3.9.2"


class TestProfileAll:
    def test_profile_all_integration(self, mock_ssh):
        def execute_side_effect(cmd):
            if "os-release" in cmd:
                return ('NAME="Debian"\nVERSION_ID="11"\n', "", 0)
            elif "uname -r" == cmd:
                return ("5.10.0", "", 0)
            elif "uname -m" == cmd:
                return ("x86_64", "", 0)
            elif cmd == "nproc":
                return ("2", "", 0)
            elif "cpuinfo" in cmd:
                return ("model name : Intel CPU\n", "", 0)
            elif "free -m" in cmd:
                return ("Mem:  1984  512  1024\n", "", 0)
            elif cmd == "hostname":
                return ("server", "", 0)
            elif "ifconfig.me" in cmd:
                return ("1.2.3.4", "", 0)
            elif "ip -j addr" in cmd:
                return ("[]", "", 0)
            elif "ss -tuln" in cmd:
                return (":::22\n:::80\n", "", 0)
            elif "dpkg -l" in cmd:
                return ("nginx\ncurl\n", "", 0)
            elif "systemctl" in cmd:
                return ("nginx.service    loaded active running\n", "", 0)
            elif "ufw status" in cmd:
                return ("Status: active\n22 ALLOW\n", "", 0)
            elif "iptables" in cmd:
                return ("", "", 0)
            elif cmd == "df -h":
                return ("Filesystem Size Used Avail Use% Mounted on\n/dev/a 10G 1G 9G 10% /\n", "", 0)
            elif "lsblk" in cmd:
                return ("{}", "", 0)
            elif "/etc/passwd" in cmd:
                return ("admin:x:1000:1000::/home/admin:/bin/bash\n", "", 0)
            elif "cron" in cmd:
                return ("", "", 1)
            elif "which" in cmd or "--version" in cmd or "docker ps" in cmd:
                return ("", "", 1)
            return ("", "", 0)

        mock_ssh.execute_command.side_effect = execute_side_effect
        mock_ssh.execute_sudo_command.side_effect = lambda c, **kw: execute_side_effect(c)

        profiler = ServerProfiler(mock_ssh)
        profile = profiler.profile_all()

        assert profile["os_info"]["name"] == "Debian"
        assert profile["hardware"]["cpu_cores"] == 2
        assert profile["hardware"]["memory_mb"] == 1984
        assert profile["network"]["hostname"] == "server"
        assert profile["packages"] == ["nginx", "curl"]
        assert len(profile["services"]) == 1
        assert profile["firewall"]["type"] == "ufw"
        assert len(profile["users"]) == 1


class TestSaveProfile:
    def test_save_profile(self, mock_ssh, tmp_path, sample_profile):
        profiler = ServerProfiler(mock_ssh)
        profiler.profile = sample_profile

        output = tmp_path / "test_out.json"
        profiler.save_profile(str(output))

        with open(output) as f:
            data = json.load(f)
        assert data["os_info"]["name"] == "Debian GNU/Linux"
        assert data["hardware"]["cpu_cores"] == 2
