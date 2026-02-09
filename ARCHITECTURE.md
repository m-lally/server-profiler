# Architecture Documentation

## System Overview

The Server Profiler is a modular Python tool that reverse-engineers infrastructure by:
1. Connecting to a remote server via SSH
2. Gathering comprehensive system information
3. Generating Terraform IaC to recreate the server

## Component Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         profiler.py                          │
│                      (CLI Interface)                         │
└───────────┬─────────────────────────────────────────────────┘
            │
            ├─────────────────────┬──────────────────────────┐
            ▼                     ▼                          ▼
┌──────────────────┐   ┌─────────────────┐   ┌─────────────────────┐
│ ssh_connector.py │   │ server_profiler │   │ terraform_generator │
│                  │   │      .py        │   │        .py          │
└──────────────────┘   └─────────────────┘   └─────────────────────┘
```

## Module Breakdown

### 1. ssh_connector.py

**Purpose**: Handle SSH connections to remote servers

**Key Classes**:
- `SSHConnector`: Main SSH connection handler
  - Supports key-based and password authentication
  - Context manager support (`with` statement)
  - Command execution with sudo support
  - File reading capabilities

**Functions**:
- `parse_lightsail_config()`: Parse AWS Lightsail SSH config files

**Features**:
- Automatic host key acceptance
- Connection timeout handling
- Error handling and logging
- File operations over SSH

### 2. server_profiler.py

**Purpose**: Gather comprehensive server information

**Key Classes**:
- `ServerProfiler`: Main profiling engine

**Profiling Methods**:

1. **OS Information** (`get_os_info()`)
   - Distribution and version
   - Kernel version
   - System architecture
   - Sources: `/etc/os-release`, `uname`

2. **Hardware Information** (`get_hardware_info()`)
   - CPU cores and model
   - Memory capacity
   - Sources: `/proc/cpuinfo`, `free`

3. **Network Configuration** (`get_network_info()`)
   - Network interfaces and IPs
   - Public IP address
   - Listening ports
   - Hostname
   - Sources: `ip`, `ss`, `curl ifconfig.me`

4. **Package Management** (`get_installed_packages()`)
   - Lists all installed packages
   - Supports APT (Debian/Ubuntu)
   - Sources: `dpkg`

5. **Services** (`get_services()`)
   - Running systemd services
   - Service states
   - Sources: `systemctl`

6. **Firewall Rules** (`get_firewall_rules()`)
   - UFW rules
   - iptables rules
   - Sources: `ufw status`, `iptables -L`

7. **Storage** (`get_storage_info()`)
   - Disk usage and capacity
   - Mount points
   - Block devices
   - Sources: `df`, `lsblk`

8. **Users** (`get_users()`)
   - User accounts (UID > 100)
   - Home directories
   - Default shells
   - Sources: `/etc/passwd`

9. **Cron Jobs** (`get_cron_jobs()`)
   - System cron jobs
   - User crontabs
   - Sources: `/etc/cron.*`

10. **Software Detection** (`detect_installed_software()`)
    - Web servers (nginx, apache)
    - Databases (mysql, postgresql, redis, mongodb)
    - Programming languages (python, node, ruby, php, go, rust)
    - Container platforms (docker)
    - Version information

### 3. terraform_generator.py

**Purpose**: Generate Terraform configuration from server profile

**Key Classes**:
- `TerraformGenerator`: Terraform code generator

**Generation Methods**:

1. **main.tf** (`generate_main_tf()`)
   - Lightsail instance resource
   - Network port configuration
   - Static IP allocation
   - Tags and metadata

2. **variables.tf** (`generate_variables_tf()`)
   - AWS region
   - Instance configuration
   - Blueprint and bundle IDs
   - Customizable parameters

3. **provisioner.tf** (`generate_provisioner_tf()`)
   - Null resource for provisioning
   - File upload configuration
   - Remote execution setup

4. **outputs.tf** (`generate_outputs_tf()`)
   - Instance ID and name
   - Public and private IPs
   - SSH connection string

5. **startup.sh** (`generate_startup_script()`)
   - System update commands
   - Package installation
   - Service configuration
   - User creation
   - Firewall setup

**Mapping Logic**:
- Memory to Lightsail bundle (`_get_lightsail_bundle()`)
- OS to blueprint ID
- Services to systemd units
- Firewall rules to UFW commands

### 4. profiler.py (CLI)

**Purpose**: Command-line interface and orchestration

**Features**:
- Click-based CLI with rich formatting
- Multiple connection methods
- Progress indicators
- Profile summary display
- Error handling and user feedback

**Command Options**:
- Direct SSH parameters
- Lightsail config parsing
- Terraform generation toggle
- Custom output paths

## Data Flow

```
1. User Input (SSH credentials)
        ▼
2. SSH Connection (ssh_connector)
        ▼
3. Server Profiling (server_profiler)
   - Execute remote commands
   - Parse command outputs
   - Build profile dictionary
        ▼
4. Save Profile (JSON)
        ▼
5. Generate Terraform (terraform_generator)
   - Parse profile data
   - Map to AWS resources
   - Render Jinja2 templates
   - Write .tf files
        ▼
6. Output (Terraform files + profile)
```

## Profile Data Structure

```json
{
  "os_info": {
    "name": "Debian GNU/Linux",
    "version": "11",
    "kernel": "5.10.0-18-amd64",
    "architecture": "x86_64"
  },
  "hardware": {
    "cpu_cores": 1,
    "cpu_model": "Intel Xeon",
    "memory_mb": 512
  },
  "network": {
    "hostname": "my-server",
    "public_ip": "54.123.45.67",
    "interfaces": [...],
    "listening_ports": [22, 80, 443]
  },
  "packages": ["nginx", "python3", ...],
  "services": [
    {"name": "nginx", "status": "running"},
    ...
  ],
  "firewall": {
    "type": "ufw",
    "rules": [...]
  },
  "storage": {
    "disks": [...],
    "mounts": [...]
  },
  "users": [...],
  "cron_jobs": {...},
  "software": {
    "nginx": {"installed": true, "version": "1.18.0"},
    ...
  }
}
```

## Terraform Resource Mapping

| Profile Data | Terraform Resource |
|--------------|-------------------|
| OS + Memory | `aws_lightsail_instance` (blueprint_id, bundle_id) |
| Listening Ports | `aws_lightsail_instance_public_ports` |
| Public IP | `aws_lightsail_static_ip` |
| Packages | `startup.sh` (apt-get install) |
| Services | `startup.sh` (systemctl enable/start) |
| Firewall | `startup.sh` (ufw rules) |
| Users | `startup.sh` (useradd) |

## Extension Points

### Adding New Profilers

To add a new profiling method:

```python
def get_custom_info(self) -> Dict[str, Any]:
    """Get custom information."""
    info = {}
    stdout, _, _ = self.ssh.execute_command("your-command")
    # Parse stdout
    return info
```

Add to `profile_all()`:
```python
self.profile['custom'] = self.get_custom_info()
```

### Adding New Terraform Resources

1. Create template in `terraform_generator.py`
2. Add to appropriate generation method
3. Map profile data to resource attributes

### Supporting Other Cloud Providers

Create new generator classes:
- `AWSGenerator`
- `AzureGenerator`
- `GCPGenerator`

Inherit from base `TerraformGenerator` and override resource generation methods.

## Security Considerations

1. **SSH Key Handling**
   - Keys never logged or stored
   - Read-only access to key files
   - Proper permission checks (600)

2. **Credential Storage**
   - No plaintext password storage
   - Config files in `.gitignore`
   - Environment variable support

3. **Remote Execution**
   - Limited sudo usage
   - Command validation
   - Timeout enforcement

4. **Generated Code**
   - Review before applying
   - No hardcoded secrets
   - Variable-based configuration

## Performance Optimization

1. **Parallel Profiling**
   - Could execute independent commands concurrently
   - Use `concurrent.futures.ThreadPoolExecutor`

2. **Caching**
   - Cache command results
   - Avoid redundant SSH calls

3. **Selective Profiling**
   - Skip sections via config
   - Configurable package limits

## Testing Strategy

1. **Unit Tests**
   - Mock SSH connections
   - Test parsing logic
   - Validate Terraform output

2. **Integration Tests**
   - Test against Docker containers
   - Verify SSH connectivity
   - End-to-end profiling

3. **Terraform Validation**
   - `terraform validate` on generated code
   - `terraform plan` dry runs

## Future Enhancements

1. **Multi-server support**
   - Batch profiling
   - Fleet analysis
   - Comparison reports

2. **Change detection**
   - Compare profiles over time
   - Drift detection
   - Compliance checking

3. **Advanced software detection**
   - Docker container analysis
   - Application configuration
   - Database schemas

4. **Interactive mode**
   - Select what to profile
   - Choose Terraform resources
   - Customize generation

5. **Cloud provider abstraction**
   - Pulumi support
   - CloudFormation templates
   - Ansible playbooks
