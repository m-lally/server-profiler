# Server Profiler & Terraform Generator

A service that connects to a remote server, profiles its configuration, and generates Terraform scripts to recreate it.

## Features

- SSH connection to remote servers
- Comprehensive server profiling:
  - OS and distribution details
  - Installed packages
  - Running services
  - Network configuration
  - Firewall rules
  - Storage and volumes
  - User accounts
  - Cron jobs
  - Key configuration files
- Terraform code generation

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic profiling

```bash
python profiler.py --host <hostname> --user <username> --key <path-to-key>
```

### Generate Terraform

```bash
python profiler.py --host <hostname> --user <username> --key <path-to-key> --terraform
```

### Example Using Lightsail SSH config

```bash
python profiler.py --lightsail-config ~/.ssh/lightsail-config --instance-name <instance-name>
```

## Output

- `profile.json` - Complete server profile
- `terraform/` - Generated Terraform configuration
  - `main.tf` - Instance configuration
  - `provisioner.tf` - Software and configuration provisioning
  - `variables.tf` - Terraform variables
  - `outputs.tf` - Terraform outputs
