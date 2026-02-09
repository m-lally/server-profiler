"""SSH connection handler for remote server access."""
import paramiko
import os
from typing import Optional, Tuple
from pathlib import Path


class SSHConnector:
    """Handles SSH connections to remote servers."""
    
    def __init__(self, host: str, username: str, key_file: Optional[str] = None, 
                 password: Optional[str] = None, port: int = 22):
        """
        Initialize SSH connector.
        
        Args:
            host: Remote server hostname or IP
            username: SSH username
            key_file: Path to private key file
            password: SSH password (if not using key)
            port: SSH port (default: 22)
        """
        self.host = host
        self.username = username
        self.key_file = key_file
        self.password = password
        self.port = port
        self.client: Optional[paramiko.SSHClient] = None
        
    def connect(self) -> bool:
        """
        Establish SSH connection.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            connect_kwargs = {
                'hostname': self.host,
                'username': self.username,
                'port': self.port,
                'timeout': 10
            }
            
            if self.key_file:
                key_path = Path(self.key_file).expanduser()
                if not key_path.exists():
                    raise FileNotFoundError(f"Key file not found: {key_path}")
                connect_kwargs['key_filename'] = str(key_path)
            elif self.password:
                connect_kwargs['password'] = self.password
            else:
                raise ValueError("Either key_file or password must be provided")
            
            self.client.connect(**connect_kwargs)
            return True
            
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def execute_command(self, command: str) -> Tuple[str, str, int]:
        """
        Execute a command on the remote server.
        
        Args:
            command: Command to execute
            
        Returns:
            Tuple of (stdout, stderr, exit_code)
        """
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")
        
        stdin, stdout, stderr = self.client.exec_command(command)
        exit_code = stdout.channel.recv_exit_status()
        
        return (
            stdout.read().decode('utf-8'),
            stderr.read().decode('utf-8'),
            exit_code
        )
    
    def execute_sudo_command(self, command: str, sudo_password: Optional[str] = None) -> Tuple[str, str, int]:
        """
        Execute a command with sudo privileges.
        
        Args:
            command: Command to execute
            sudo_password: Sudo password (if required)
            
        Returns:
            Tuple of (stdout, stderr, exit_code)
        """
        if sudo_password:
            full_command = f"echo '{sudo_password}' | sudo -S {command}"
        else:
            full_command = f"sudo {command}"
        
        return self.execute_command(full_command)
    
    def read_file(self, remote_path: str) -> Optional[str]:
        """
        Read a file from the remote server.
        
        Args:
            remote_path: Path to file on remote server
            
        Returns:
            File contents or None if error
        """
        stdout, stderr, exit_code = self.execute_command(f"cat {remote_path}")
        if exit_code == 0:
            return stdout
        return None
    
    def close(self):
        """Close SSH connection."""
        if self.client:
            self.client.close()
            self.client = None
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def parse_lightsail_config(config_path: str, instance_name: str) -> dict:
    """
    Parse AWS Lightsail SSH config file.
    
    Args:
        config_path: Path to SSH config file
        instance_name: Name of the Lightsail instance
        
    Returns:
        Dictionary with connection parameters
    """
    config_path = Path(config_path).expanduser()
    
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        content = f.read()
    
    # Parse SSH config format
    config = {}
    current_host = None
    
    for line in content.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        if line.lower().startswith('host '):
            current_host = line.split(None, 1)[1]
        elif current_host == instance_name:
            if ' ' in line:
                key, value = line.split(None, 1)
                config[key.lower()] = value
    
    return {
        'host': config.get('hostname', instance_name),
        'username': config.get('user', 'admin'),
        'key_file': config.get('identityfile', '').strip('"'),
        'port': int(config.get('port', 22))
    }
