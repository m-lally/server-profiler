"""Tests for the TerraformGenerator class."""
import pytest
from pathlib import Path

from terraform_generator import TerraformGenerator


class TestTerraformGenerator:
    def test_generate_all_files(self, sample_profile, tmp_path):
        output_dir = str(tmp_path / "tf")
        gen = TerraformGenerator(sample_profile, output_dir=output_dir)
        gen.generate_all()

        expected_files = ["main.tf", "variables.tf", "provisioner.tf",
                          "outputs.tf", "startup.sh"]
        for fname in expected_files:
            assert (Path(output_dir) / fname).exists()

    def test_main_tf_content(self, sample_profile, tmp_path):
        output_dir = str(tmp_path / "tf")
        gen = TerraformGenerator(sample_profile, output_dir=output_dir)
        gen.generate_all()

        content = (Path(output_dir) / "main.tf").read_text()
        assert 'required_providers' in content
        assert 'aws_lightsail_instance' in content
        assert 'aws_lightsail_instance_public_ports' in content
        assert 'aws_lightsail_static_ip' in content
        assert '1984MB RAM' in content  # memory in comment
        assert 'Debian' in content

    def test_main_tf_listening_ports(self, sample_profile, tmp_path):
        output_dir = str(tmp_path / "tf")
        gen = TerraformGenerator(sample_profile, output_dir=output_dir)
        gen.generate_all()

        content = (Path(output_dir) / "main.tf").read_text()
        assert "from_port = 22" in content
        assert "from_port = 80" in content
        assert "from_port = 443" in content

    def test_variables_tf_content(self, sample_profile, tmp_path):
        output_dir = str(tmp_path / "tf")
        gen = TerraformGenerator(sample_profile, output_dir=output_dir)
        gen.generate_all()

        content = (Path(output_dir) / "variables.tf").read_text()
        assert 'variable "aws_region"' in content
        assert 'variable "instance_name"' in content
        assert 'variable "blueprint_id"' in content
        assert 'variable "bundle_id"' in content
        assert 'variable "use_static_ip"' in content
        assert 'variable "environment"' in content
        assert 'variable "ssh_key_name"' in content
        assert 'debian_11' in content

    def test_variables_tf_hostname(self, sample_profile, tmp_path):
        output_dir = str(tmp_path / "tf")
        gen = TerraformGenerator(sample_profile, output_dir=output_dir)
        gen.generate_all()

        content = (Path(output_dir) / "variables.tf").read_text()
        assert "web-01" in content

    def test_outputs_tf_content(self, sample_profile, tmp_path):
        output_dir = str(tmp_path / "tf")
        gen = TerraformGenerator(sample_profile, output_dir=output_dir)
        gen.generate_all()

        content = (Path(output_dir) / "outputs.tf").read_text()
        assert 'output "instance_id"' in content
        assert 'output "public_ip"' in content
        assert 'output "private_ip"' in content
        assert 'output "static_ip"' in content
        assert 'output "ssh_connection"' in content

    def test_startup_script_content(self, sample_profile, tmp_path):
        output_dir = str(tmp_path / "tf")
        gen = TerraformGenerator(sample_profile, output_dir=output_dir)
        gen.generate_all()

        content = (Path(output_dir) / "startup.sh").read_text()
        assert "#!/bin/bash" in content
        assert "apt-get update" in content
        assert "ufw --force enable" in content
        assert "useradd -m -s /bin/bash -u 1000 admin" in content
        assert "useradd -m -s /bin/bash -u 1001 deploy" in content

    def test_startup_script_executable(self, sample_profile, tmp_path):
        output_dir = str(tmp_path / "tf")
        gen = TerraformGenerator(sample_profile, output_dir=output_dir)
        gen.generate_all()

        script = Path(output_dir) / "startup.sh"
        assert script.stat().st_mode & 0o111

    def test_provisioner_tf_content(self, sample_profile, tmp_path):
        output_dir = str(tmp_path / "tf")
        gen = TerraformGenerator(sample_profile, output_dir=output_dir)
        gen.generate_all()

        content = (Path(output_dir) / "provisioner.tf").read_text()
        assert 'null_resource' in content
        assert 'aws_lightsail_instance.server' in content
        assert 'remote-exec' in content

    def test_bundle_mapping_nano(self, sample_profile, tmp_path):
        sample_profile["hardware"]["memory_mb"] = 512
        gen = TerraformGenerator(sample_profile, output_dir=str(tmp_path / "tf-nano"))
        gen.generate_all()

        content = (Path(tmp_path / "tf-nano") / "variables.tf").read_text()
        assert "nano_3_0" in content

    def test_bundle_mapping_large(self, sample_profile, tmp_path):
        sample_profile["hardware"]["memory_mb"] = 8192
        gen = TerraformGenerator(sample_profile, output_dir=str(tmp_path / "tf-large"))
        gen.generate_all()

        content = (Path(tmp_path / "tf-large") / "variables.tf").read_text()
        assert "large_3_0" in content

    def test_bundle_mapping_xlarge(self, sample_profile, tmp_path):
        sample_profile["hardware"]["memory_mb"] = 16384
        gen = TerraformGenerator(sample_profile, output_dir=str(tmp_path / "tf-xl"))
        gen.generate_all()

        content = (Path(tmp_path / "tf-xl") / "variables.tf").read_text()
        assert "xlarge_3_0" in content

    def test_ubuntu_blueprint(self, sample_profile, tmp_path):
        sample_profile["os_info"]["name"] = "Ubuntu"
        sample_profile["os_info"]["version_id"] = "22.04"
        gen = TerraformGenerator(sample_profile, output_dir=str(tmp_path / "tf-ubuntu"))
        gen.generate_all()

        content = (Path(tmp_path / "tf-ubuntu") / "variables.tf").read_text()
        assert "ubuntu_22_04" in content

    def test_no_packages(self, sample_profile, tmp_path):
        sample_profile["packages"] = []
        gen = TerraformGenerator(sample_profile, output_dir=str(tmp_path / "tf-nopkg"))
        gen.generate_all()

        content = (Path(tmp_path / "tf-nopkg") / "startup.sh").read_text()
        assert "apt-get install" not in content

    def test_with_docker_containers(self, sample_profile, tmp_path):
        sample_profile["software"]["docker"]["installed"] = True
        sample_profile["software"]["docker"]["running_containers"] = ["web", "db"]
        gen = TerraformGenerator(sample_profile, output_dir=str(tmp_path / "tf-docker"))
        gen.generate_all()

        content = (Path(tmp_path / "tf-docker") / "startup.sh").read_text()
        assert "systemctl enable docker" in content

    def test_startup_script_firewall(self, sample_profile, tmp_path):
        gen = TerraformGenerator(sample_profile, output_dir=str(tmp_path / "tf-fw"))
        gen.generate_all()

        content = (Path(tmp_path / "tf-fw") / "startup.sh").read_text()
        assert "ufw --force enable" in content
        assert "ufw 22/tcp ALLOW Anywhere" in content
        assert "ufw 80/tcp ALLOW Anywhere" in content
