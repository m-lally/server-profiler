"""Terraform configuration generator from server profile."""
import os
import json
from pathlib import Path
from typing import Dict, Any, List
from jinja2 import Template


class TerraformGenerator:
    """Generates Terraform configuration from server profile."""
    
    def __init__(self, profile: Dict[str, Any], output_dir: str = 'terraform'):
        """
        Initialize Terraform generator.
        
        Args:
            profile: Server profile dictionary
            output_dir: Directory to write Terraform files
        """
        self.profile = profile
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_all(self):
        """Generate all Terraform configuration files."""
        print("\n🏗️  Generating Terraform configuration...")
        
        self.generate_main_tf()
        print("  ✓ main.tf")
        
        self.generate_variables_tf()
        print("  ✓ variables.tf")
        
        self.generate_provisioner_tf()
        print("  ✓ provisioner.tf")
        
        self.generate_outputs_tf()
        print("  ✓ outputs.tf")
        
        self.generate_startup_script()
        print("  ✓ startup.sh")
        
        print(f"\n✅ Terraform configuration generated in {self.output_dir}/")
    
    def generate_main_tf(self):
        """Generate main.tf with Lightsail instance configuration."""
        os_info = self.profile.get('os_info', {})
        hardware = self.profile.get('hardware', {})
        
        # Map memory to Lightsail bundle
        memory_mb = hardware.get('memory_mb', 512)
        bundle_id = self._get_lightsail_bundle(memory_mb)
        
        # Get availability zone from network info
        region = 'us-east-1'  # Default
        
        template = Template('''# Terraform configuration for AWS Lightsail instance
# Auto-generated from server profile

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

resource "aws_lightsail_instance" "server" {
  name              = var.instance_name
  availability_zone = "${var.aws_region}a"
  blueprint_id      = var.blueprint_id  # {{ os_name }}
  bundle_id         = var.bundle_id     # {{ memory_mb }}MB RAM, {{ cpu_cores }} vCPU
  
  # User data script for initial setup
  user_data = file("${path.module}/startup.sh")
  
  tags = {
    Name        = var.instance_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    SourceProfile = "{{ hostname }}"
  }
}

# Networking
resource "aws_lightsail_instance_public_ports" "server" {
  instance_name = aws_lightsail_instance.server.name

  {% for port in listening_ports %}
  port_info {
    protocol  = "tcp"
    from_port = {{ port }}
    to_port   = {{ port }}
    cidrs     = ["0.0.0.0/0"]
  }
  {% endfor %}
}

# Static IP (optional)
resource "aws_lightsail_static_ip" "server" {
  count = var.use_static_ip ? 1 : 0
  name  = "${var.instance_name}-static-ip"
}

resource "aws_lightsail_static_ip_attachment" "server" {
  count          = var.use_static_ip ? 1 : 0
  static_ip_name = aws_lightsail_static_ip.server[0].name
  instance_name  = aws_lightsail_instance.server.name
}
''')
        
        content = template.render(
            os_name=os_info.get('name', 'Debian'),
            memory_mb=memory_mb,
            cpu_cores=hardware.get('cpu_cores', 1),
            hostname=self.profile.get('network', {}).get('hostname', 'server'),
            listening_ports=self.profile.get('network', {}).get('listening_ports', [22, 80, 443])
        )
        
        with open(self.output_dir / 'main.tf', 'w') as f:
            f.write(content)
    
    def generate_variables_tf(self):
        """Generate variables.tf with configurable parameters."""
        os_info = self.profile.get('os_info', {})
        hardware = self.profile.get('memory_mb', 512)
        
        template = Template('''# Terraform variables

variable "aws_region" {
  description = "AWS region for Lightsail instance"
  type        = string
  default     = "us-east-1"
}

variable "instance_name" {
  description = "Name of the Lightsail instance"
  type        = string
  default     = "{{ hostname }}"
}

variable "blueprint_id" {
  description = "Lightsail blueprint ID (OS image)"
  type        = string
  default     = "{{ blueprint_id }}"
}

variable "bundle_id" {
  description = "Lightsail bundle ID (instance size)"
  type        = string
  default     = "{{ bundle_id }}"
}

variable "use_static_ip" {
  description = "Whether to allocate and attach a static IP"
  type        = bool
  default     = true
}

variable "environment" {
  description = "Environment tag"
  type        = string
  default     = "production"
}

variable "ssh_key_name" {
  description = "Name of SSH key pair for instance access"
  type        = string
  default     = "lightsail-key"
}
''')
        
        # Determine blueprint ID
        os_name = os_info.get('name', '').lower()
        os_version = os_info.get('version_id', '')
        
        if 'debian' in os_name:
            if '11' in os_version:
                blueprint_id = 'debian_11'
            elif '12' in os_version:
                blueprint_id = 'debian_12'
            else:
                blueprint_id = 'debian_11'
        elif 'ubuntu' in os_name:
            blueprint_id = 'ubuntu_22_04'
        else:
            blueprint_id = 'debian_11'
        
        content = template.render(
            hostname=self.profile.get('network', {}).get('hostname', 'server'),
            blueprint_id=blueprint_id,
            bundle_id=self._get_lightsail_bundle(self.profile.get('hardware', {}).get('memory_mb', 512))
        )
        
        with open(self.output_dir / 'variables.tf', 'w') as f:
            f.write(content)
    
    def generate_provisioner_tf(self):
        """Generate provisioner configuration for software installation."""
        services = self.profile.get('services', [])
        software = self.profile.get('software', {})
        
        template = Template('''# Provisioner configuration using remote-exec
# This runs after the instance is created

resource "null_resource" "provisioner" {
  depends_on = [aws_lightsail_instance.server]

  connection {
    type        = "ssh"
    user        = "admin"  # Default for Debian on Lightsail
    host        = aws_lightsail_instance.server.public_ip_address
    private_key = file("~/.ssh/${var.ssh_key_name}.pem")
  }

  # Upload configuration files
  {% for config_file in config_files %}
  provisioner "file" {
    source      = "configs/{{ config_file.name }}"
    destination = "/tmp/{{ config_file.name }}"
  }
  {% endfor %}

  # Execute setup script
  provisioner "remote-exec" {
    inline = [
      "chmod +x /tmp/setup.sh",
      "sudo /tmp/setup.sh"
    ]
  }
}
''')
        
        config_files = []
        # Collect important config files to replicate
        # This would be expanded based on detected services
        
        content = template.render(
            config_files=config_files
        )
        
        with open(self.output_dir / 'provisioner.tf', 'w') as f:
            f.write(content)
    
    def generate_outputs_tf(self):
        """Generate outputs.tf for instance information."""
        content = '''# Terraform outputs

output "instance_id" {
  description = "Lightsail instance ID"
  value       = aws_lightsail_instance.server.id
}

output "instance_name" {
  description = "Lightsail instance name"
  value       = aws_lightsail_instance.server.name
}

output "public_ip" {
  description = "Public IP address"
  value       = aws_lightsail_instance.server.public_ip_address
}

output "private_ip" {
  description = "Private IP address"
  value       = aws_lightsail_instance.server.private_ip_address
}

output "static_ip" {
  description = "Static IP address (if enabled)"
  value       = var.use_static_ip ? aws_lightsail_static_ip.server[0].ip_address : null
}

output "ssh_connection" {
  description = "SSH connection command"
  value       = "ssh admin@${aws_lightsail_instance.server.public_ip_address}"
}
'''
        
        with open(self.output_dir / 'outputs.tf', 'w') as f:
            f.write(content)
    
    def generate_startup_script(self):
        """Generate startup.sh user data script."""
        packages = self.profile.get('packages', [])
        software = self.profile.get('software', {})
        services = self.profile.get('services', [])
        
        # Filter to essential packages only (avoid system packages)
        essential_packages = []
        common_packages = ['nginx', 'apache2', 'mysql-server', 'postgresql', 
                          'redis-server', 'docker.io', 'git', 'curl', 'wget',
                          'python3', 'python3-pip', 'nodejs', 'npm']
        
        for pkg in packages:
            if pkg in common_packages:
                essential_packages.append(pkg)
        
        template = Template('''#!/bin/bash
# Startup script for Lightsail instance
# Auto-generated from server profile

set -e

# Update system
apt-get update
apt-get upgrade -y

# Install essential packages
{% if essential_packages %}
apt-get install -y \\
{% for pkg in essential_packages %}
  {{ pkg }}{% if not loop.last %} \\{% endif %}
{% endfor %}
{% endif %}

# Configure software
{% for name, config in software.items() %}
{% if config.installed %}
# Configure {{ name }}
systemctl enable {{ name }}
systemctl start {{ name }}
{% endif %}
{% endfor %}

# Set up firewall (if UFW was used)
{% if firewall_type == 'ufw' %}
ufw --force enable
{% for rule in firewall_rules %}
ufw {{ rule }}
{% endfor %}
{% endif %}

# Create users
{% for user in users %}
{% if user.uid >= 1000 %}
useradd -m -s {{ user.shell }} -u {{ user.uid }} {{ user.username }} || true
{% endif %}
{% endfor %}

echo "Server setup complete!"
''')
        
        firewall = self.profile.get('firewall', {})
        
        content = template.render(
            essential_packages=essential_packages[:20],  # Limit to avoid huge script
            software=software,
            firewall_type=firewall.get('type'),
            firewall_rules=firewall.get('rules', []),
            users=self.profile.get('users', [])
        )
        
        with open(self.output_dir / 'startup.sh', 'w') as f:
            f.write(content)
        
        # Make executable
        os.chmod(self.output_dir / 'startup.sh', 0o755)
    
    def _get_lightsail_bundle(self, memory_mb: int) -> str:
        """
        Map memory size to Lightsail bundle ID.
        
        Args:
            memory_mb: Memory in megabytes
            
        Returns:
            Lightsail bundle ID
        """
        if memory_mb <= 512:
            return "nano_3_0"  # 512 MB, 1 vCPU
        elif memory_mb <= 1024:
            return "micro_3_0"  # 1 GB, 1 vCPU
        elif memory_mb <= 2048:
            return "small_3_0"  # 2 GB, 1 vCPU
        elif memory_mb <= 4096:
            return "medium_3_0"  # 4 GB, 2 vCPU
        elif memory_mb <= 8192:
            return "large_3_0"  # 8 GB, 2 vCPU
        else:
            return "xlarge_3_0"  # 16 GB, 4 vCPU
