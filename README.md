# Server Profiler & Terraform Generator

Profile remote servers and generate Terraform infrastructure-as-code.

[![Tests](https://github.com/your-org/server-profiler/actions/workflows/test.yml/badge.svg)](https://github.com/your-org/server-profiler/actions)

## Installation

```bash
pip install -e .
```

## Usage

### Profile a remote server

```bash
server-profiler profile --host example.com --user admin --key ~/.ssh/id_rsa
```

### Profile using Lightsail SSH config

```bash
server-profiler profile --lightsail-config ~/.ssh/lightsail-ssh-config --instance-name my-server
```

### Profile only (skip Terraform generation)

```bash
server-profiler profile --host example.com --key ~/.ssh/id_rsa --no-terraform
```

### Regenerate Terraform from existing profile

```bash
server-profiler terraform --input profile.json
```

### Show version

```bash
server-profiler --version
```

## Command Reference

### `server-profiler profile`

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | — | Remote server hostname or IP |
| `--user` | `admin` | SSH username |
| `--key` | — | Path to SSH private key |
| `--password` | — | SSH password |
| `--port` | `22` | SSH port |
| `--lightsail-config` | — | Path to Lightsail SSH config |
| `--instance-name` | — | Instance name in Lightsail config |
| `--terraform/--no-terraform` | `True` | Generate Terraform config |
| `--output` | `profile.json` | Profile output file |
| `--terraform-dir` | `terraform` | Terraform output directory |
| `-v, --verbose` | — | Show detailed progress |

### `server-profiler terraform`

| Option | Default | Description |
|--------|---------|-------------|
| `-i, --input` | `profile.json` | Input profile JSON |
| `--terraform-dir` | `terraform` | Terraform output directory |
| `-v, --verbose` | — | Show detailed progress |

## Outputs

- `profile.json` — Complete server profile
- `terraform/` — Generated Terraform configuration
  - `main.tf` — Lightsail instance and networking
  - `variables.tf` — Configurable parameters
  - `provisioner.tf` — Remote-exec provisioning
  - `outputs.tf` — Instance outputs
  - `startup.sh` — User data bootstrap script

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# Run tests with coverage
python -m pytest tests/ --cov=.
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design documentation.
