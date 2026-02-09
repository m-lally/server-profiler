"""Server profiling module to gather system configuration."""
import json
import re
from typing import Dict, List, Optional, Any
from ssh_connector import SSHConnector


class ServerProfiler:
    """Profiles a remote server's configuration."""
    
    def __init__(self, ssh_connector: SSHConnector):
        """
        Initialize server profiler.
        
        Args:
            ssh_connector: Connected SSH connector instance
        """
        self.ssh = ssh_connector
        self.profile: Dict[str, Any] = {}
    
    def profile_all(self) -> Dict[str, Any]:
        """
        Run all profiling methods and return complete profile.
        
        Returns:
            Dictionary containing complete server profile
        """
        print("🔍 Profiling server...")
        
        self.profile['os_info'] = self.get_os_info()
        print("  ✓ OS information")
        
        self.profile['hardware'] = self.get_hardware_info()
        print("  ✓ Hardware information")
        
        self.profile['network'] = self.get_network_info()
        print("  ✓ Network configuration")
        
        self.profile['packages'] = self.get_installed_packages()
        print("  ✓ Installed packages")
        
        self.profile['services'] = self.get_services()
        print("  ✓ Running services")
        
        self.profile['firewall'] = self.get_firewall_rules()
        print("  ✓ Firewall rules")
        
        self.profile['storage'] = self.get_storage_info()
        print("  ✓ Storage configuration")
        
        self.profile['users'] = self.get_users()
        print("  ✓ User accounts")
        
        self.profile['cron_jobs'] = self.get_cron_jobs()
        print("  ✓ Cron jobs")
        
        self.profile['software'] = self.detect_installed_software()
        print("  ✓ Software detection")
        
        return self.profile
    
    def get_os_info(self) -> Dict[str, str]:
        """Get operating system information."""
        info = {}
        
        # OS release info
        stdout, _, _ = self.ssh.execute_command("cat /etc/os-release")
        for line in stdout.split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                info[key.lower()] = value.strip('"')
        
        # Kernel version
        stdout, _, _ = self.ssh.execute_command("uname -r")
        info['kernel'] = stdout.strip()
        
        # Architecture
        stdout, _, _ = self.ssh.execute_command("uname -m")
        info['architecture'] = stdout.strip()
        
        return info
    
    def get_hardware_info(self) -> Dict[str, Any]:
        """Get hardware information."""
        info = {}
        
        # CPU info
        stdout, _, _ = self.ssh.execute_command("nproc")
        info['cpu_cores'] = int(stdout.strip())
        
        stdout, _, _ = self.ssh.execute_command("cat /proc/cpuinfo | grep 'model name' | head -1")
        if stdout:
            info['cpu_model'] = stdout.split(':', 1)[1].strip()
        
        # Memory info
        stdout, _, _ = self.ssh.execute_command("free -m | grep Mem")
        if stdout:
            mem_info = stdout.split()
            info['memory_mb'] = int(mem_info[1])
        
        return info
    
    def get_network_info(self) -> Dict[str, Any]:
        """Get network configuration."""
        info = {
            'interfaces': [],
            'public_ip': None,
            'hostname': None
        }
        
        # Hostname
        stdout, _, _ = self.ssh.execute_command("hostname")
        info['hostname'] = stdout.strip()
        
        # Public IP
        stdout, _, exit_code = self.ssh.execute_command("curl -s ifconfig.me")
        if exit_code == 0:
            info['public_ip'] = stdout.strip()
        
        # Network interfaces
        stdout, _, _ = self.ssh.execute_command("ip -j addr show")
        try:
            import json
            interfaces = json.loads(stdout)
            for iface in interfaces:
                if iface['ifname'] != 'lo':
                    iface_info = {
                        'name': iface['ifname'],
                        'addresses': []
                    }
                    for addr in iface.get('addr_info', []):
                        iface_info['addresses'].append({
                            'family': addr.get('family'),
                            'address': addr.get('local'),
                            'prefix': addr.get('prefixlen')
                        })
                    info['interfaces'].append(iface_info)
        except:
            # Fallback if ip -j not available
            pass
        
        # Open ports
        stdout, _, _ = self.ssh.execute_command("ss -tuln | grep LISTEN")
        ports = set()
        for line in stdout.split('\n'):
            match = re.search(r':(\d+)\s', line)
            if match:
                ports.add(int(match.group(1)))
        info['listening_ports'] = sorted(list(ports))
        
        return info
    
    def get_installed_packages(self) -> List[str]:
        """Get list of installed packages."""
        packages = []
        
        # Try apt (Debian/Ubuntu)
        stdout, _, exit_code = self.ssh.execute_command("dpkg -l | grep '^ii' | awk '{print $2}'")
        if exit_code == 0 and stdout:
            packages = [pkg.strip() for pkg in stdout.split('\n') if pkg.strip()]
        
        return packages
    
    def get_services(self) -> List[Dict[str, str]]:
        """Get running services."""
        services = []
        
        stdout, _, exit_code = self.ssh.execute_command("systemctl list-units --type=service --state=running --no-pager --no-legend")
        if exit_code == 0:
            for line in stdout.split('\n'):
                if line.strip():
                    parts = line.split()
                    if parts:
                        services.append({
                            'name': parts[0].replace('.service', ''),
                            'status': 'running'
                        })
        
        return services
    
    def get_firewall_rules(self) -> Dict[str, Any]:
        """Get firewall configuration."""
        firewall = {
            'type': None,
            'rules': []
        }
        
        # Check for ufw
        stdout, _, exit_code = self.ssh.execute_sudo_command("ufw status")
        if exit_code == 0 and 'Status: active' in stdout:
            firewall['type'] = 'ufw'
            for line in stdout.split('\n'):
                if 'ALLOW' in line or 'DENY' in line:
                    firewall['rules'].append(line.strip())
        
        # Check for iptables
        stdout, _, exit_code = self.ssh.execute_sudo_command("iptables -L -n")
        if exit_code == 0 and stdout:
            if not firewall['type']:
                firewall['type'] = 'iptables'
            # Simplified iptables parsing
            firewall['iptables_rules'] = stdout
        
        return firewall
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get storage and filesystem information."""
        storage = {
            'disks': [],
            'mounts': []
        }
        
        # Disk usage
        stdout, _, _ = self.ssh.execute_command("df -h")
        for line in stdout.split('\n')[1:]:  # Skip header
            if line.strip() and not line.startswith('tmpfs'):
                parts = line.split()
                if len(parts) >= 6:
                    storage['mounts'].append({
                        'filesystem': parts[0],
                        'size': parts[1],
                        'used': parts[2],
                        'available': parts[3],
                        'use_percent': parts[4],
                        'mount_point': parts[5]
                    })
        
        # Block devices
        stdout, _, _ = self.ssh.execute_command("lsblk -J")
        try:
            import json
            block_devices = json.loads(stdout)
            storage['disks'] = block_devices.get('blockdevices', [])
        except:
            pass
        
        return storage
    
    def get_users(self) -> List[Dict[str, str]]:
        """Get user accounts."""
        users = []
        
        stdout, _, _ = self.ssh.execute_command("cat /etc/passwd")
        for line in stdout.split('\n'):
            if line.strip():
                parts = line.split(':')
                if len(parts) >= 7:
                    uid = int(parts[2])
                    # Only include regular users and system users > 100
                    if uid >= 1000 or (uid >= 100 and uid < 1000):
                        users.append({
                            'username': parts[0],
                            'uid': uid,
                            'gid': int(parts[3]),
                            'home': parts[5],
                            'shell': parts[6]
                        })
        
        return users
    
    def get_cron_jobs(self) -> Dict[str, List[str]]:
        """Get cron jobs."""
        cron_jobs = {
            'system': [],
            'users': {}
        }
        
        # System crontabs
        for cron_dir in ['/etc/cron.d', '/etc/cron.daily', '/etc/cron.hourly', '/etc/cron.weekly', '/etc/cron.monthly']:
            stdout, _, exit_code = self.ssh.execute_command(f"ls -1 {cron_dir} 2>/dev/null")
            if exit_code == 0 and stdout:
                cron_jobs['system'].extend([f"{cron_dir}/{f.strip()}" for f in stdout.split('\n') if f.strip()])
        
        return cron_jobs
    
    def detect_installed_software(self) -> Dict[str, Any]:
        """Detect commonly installed software and their configurations."""
        software = {}
        
        # Web servers
        for server in ['nginx', 'apache2']:
            stdout, _, exit_code = self.ssh.execute_command(f"which {server}")
            if exit_code == 0:
                software[server] = {'installed': True}
                # Get version
                version_cmd = f"{server} -v" if server == 'nginx' else f"{server} -V"
                stdout, _, _ = self.ssh.execute_command(version_cmd)
                software[server]['version'] = stdout.split('\n')[0] if stdout else 'unknown'
        
        # Databases
        for db in ['mysql', 'postgresql', 'redis-server', 'mongodb']:
            stdout, _, exit_code = self.ssh.execute_command(f"which {db}")
            if exit_code == 0:
                software[db] = {'installed': True}
        
        # Programming languages
        for lang, cmd in [('python', 'python3 --version'), ('node', 'node --version'), 
                          ('ruby', 'ruby --version'), ('php', 'php --version'),
                          ('go', 'go version'), ('rust', 'rustc --version')]:
            stdout, _, exit_code = self.ssh.execute_command(cmd)
            if exit_code == 0:
                software[lang] = {'version': stdout.strip()}
        
        # Docker
        stdout, _, exit_code = self.ssh.execute_command("docker --version")
        if exit_code == 0:
            software['docker'] = {'version': stdout.strip()}
            # Get running containers
            stdout, _, _ = self.ssh.execute_command("docker ps --format '{{.Names}}'")
            if stdout:
                software['docker']['running_containers'] = [c.strip() for c in stdout.split('\n') if c.strip()]
        
        return software
    
    def save_profile(self, output_file: str = 'profile.json'):
        """Save profile to JSON file."""
        with open(output_file, 'w') as f:
            json.dump(self.profile, f, indent=2)
        print(f"\n💾 Profile saved to {output_file}")
