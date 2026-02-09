# Quick Start Guide

Get started with Server Profiler in 5 minutes!

## Prerequisites

- Python 3.8 or higher
- SSH access to your AWS Lightsail server
- SSH key file for authentication

## Installation

### Option 1: Automated Setup

```bash
cd /Users/scarecro/Projects/server-profiler
chmod +x setup.sh
./setup.sh
```

### Option 2: Manual Setup

```bash
cd /Users/scarecro/Projects/server-profiler

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Make profiler executable
chmod +x profiler.py
```

## Usage

### Method 1: Using Lightsail SSH Config (Recommended)

If you have your Lightsail SSH config file, this is the easiest method:

```bash
# Profile your server and generate Terraform
python profiler.py \
  --lightsail-config ~/.ssh/lightsail-ssh-config \
  --instance-name my-debian-server
```

Your Lightsail SSH config should look like:

```
Host my-debian-server
    HostName 54.123.45.67
    User admin
    IdentityFile ~/.ssh/LightsailDefaultKey-us-east-1.pem
    Port 22
```

### Method 2: Direct Connection

If you don't have a config file:

```bash
python profiler.py \
  --host 54.123.45.67 \
  --user admin \
  --key ~/.ssh/LightsailDefaultKey-us-east-1.pem
```

### Method 3: Using Makefile

```bash
# With Lightsail config
make profile-lightsail INSTANCE=my-debian-server

# Direct connection
make profile HOST=54.123.45.67 KEY=~/.ssh/key.pem USER=admin
```

## What Gets Generated

After running the profiler, you'll get:

1. **profile.json** - Complete server profile with:
   - OS and kernel information
   - Hardware specs (CPU, RAM)
   - Network configuration
   - Installed packages and services
   - Firewall rules
   - Storage configuration
   - User accounts
   - Running software

2. **terraform/** directory with:
   - `main.tf` - Lightsail instance configuration
   - `variables.tf` - Customizable variables
   - `provisioner.tf` - Software installation scripts
   - `outputs.tf` - Instance information outputs
   - `startup.sh` - User data script

## Using the Generated Terraform

```bash
# Navigate to Terraform directory
cd terraform/

# Review and edit variables
vim variables.tf

# Initialize Terraform
terraform init

# Preview changes
terraform plan

# Create the infrastructure
terraform apply
```

## Common Options

```bash
# Profile only (no Terraform generation)
python profiler.py --host SERVER --key KEY --no-terraform

# Custom output files
python profiler.py --host SERVER --key KEY \
  --output my-profile.json \
  --terraform-dir my-terraform/

# View help
python profiler.py --help
```

## Troubleshooting

### Connection Issues

If you can't connect:

1. Check your SSH key permissions:
   ```bash
   chmod 600 ~/.ssh/your-key.pem
   ```

2. Test SSH connection manually:
   ```bash
   ssh -i ~/.ssh/your-key.pem admin@your-server
   ```

3. Verify the server's firewall allows SSH (port 22)

### Missing Sudo Privileges

Some profiling features require sudo. If you get permission errors, ensure your user has sudo access on the server.

### Large Package Lists

For servers with many packages, profiling may take a few minutes. You can skip package listing by editing `config.yaml`:

```yaml
profiling:
  skip:
    - packages: true
```

## Next Steps

1. Review the generated `profile.json` to understand your server
2. Customize the Terraform variables in `terraform/variables.tf`
3. Review `terraform/startup.sh` and adjust package installations
4. Test the Terraform configuration with `terraform plan`
5. Deploy with `terraform apply`

## Advanced Usage

### Docker Support

```bash
# Build Docker image
make docker-build

# Run in container
docker run -it --rm \
  -v ~/.ssh:/root/.ssh:ro \
  -v $(pwd)/output:/app/output \
  server-profiler --host SERVER --key /root/.ssh/key.pem
```

### Custom Configuration

Edit `config.yaml` to customize:
- Software detection list
- Terraform defaults
- Output settings
- Profiling behavior

## Getting Help

- Run `python profiler.py --help` for all options
- Check `examples.py` for usage examples
- Review `config.yaml` for configuration options
