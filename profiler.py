#!/usr/bin/env python3
"""
Server Profiler & Terraform Generator

A CLI tool to profile remote servers and generate Terraform configuration.
"""
import click
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from ssh_connector import SSHConnector, parse_lightsail_config
from server_profiler import ServerProfiler
from terraform_generator import TerraformGenerator

console = Console()


@click.command()
@click.option('--host', help='Remote server hostname or IP')
@click.option('--user', default='admin', help='SSH username')
@click.option('--key', help='Path to SSH private key file')
@click.option('--password', help='SSH password (if not using key)')
@click.option('--port', default=22, help='SSH port')
@click.option('--lightsail-config', help='Path to Lightsail SSH config file')
@click.option('--instance-name', help='Instance name in Lightsail config')
@click.option('--terraform/--no-terraform', default=True, help='Generate Terraform configuration')
@click.option('--output', default='profile.json', help='Output file for profile')
@click.option('--terraform-dir', default='terraform', help='Directory for Terraform files')
def main(host, user, key, password, port, lightsail_config, instance_name, 
         terraform, output, terraform_dir):
    """
    Profile a remote server and optionally generate Terraform configuration.
    
    Examples:
    
        # Using direct connection
        python profiler.py --host example.com --user admin --key ~/.ssh/id_rsa
        
        # Using Lightsail SSH config
        python profiler.py --lightsail-config ~/.ssh/lightsail --instance-name my-server
    """
    
    console.print(Panel.fit(
        "[bold cyan]Server Profiler & Terraform Generator[/bold cyan]\n"
        "Profile your server and generate infrastructure-as-code",
        border_style="cyan"
    ))
    
    # Parse connection parameters
    if lightsail_config and instance_name:
        try:
            config = parse_lightsail_config(lightsail_config, instance_name)
            host = config['host']
            user = config['username']
            key = config['key_file']
            port = config['port']
            console.print(f"[green]✓[/green] Loaded Lightsail config for: {instance_name}")
        except Exception as e:
            console.print(f"[red]✗[/red] Error parsing Lightsail config: {e}")
            sys.exit(1)
    elif not host:
        console.print("[red]✗[/red] Either --host or --lightsail-config + --instance-name required")
        sys.exit(1)
    
    if not key and not password:
        console.print("[red]✗[/red] Either --key or --password required")
        sys.exit(1)
    
    # Connect to server
    console.print(f"\n[yellow]→[/yellow] Connecting to {host}...")
    
    try:
        ssh = SSHConnector(host=host, username=user, key_file=key, 
                          password=password, port=port)
        
        if not ssh.connect():
            console.print("[red]✗[/red] Failed to connect to server")
            sys.exit(1)
        
        console.print(f"[green]✓[/green] Connected to {host}\n")
        
        # Profile server
        profiler = ServerProfiler(ssh)
        profile = profiler.profile_all()
        
        # Save profile
        profiler.save_profile(output)
        
        # Display summary
        display_profile_summary(profile)
        
        # Generate Terraform
        if terraform:
            console.print()
            generator = TerraformGenerator(profile, output_dir=terraform_dir)
            generator.generate_all()
            
            console.print(f"\n[bold green]🎉 Complete![/bold green]")
            console.print(f"\nNext steps:")
            console.print(f"  1. Review the generated Terraform files in [cyan]{terraform_dir}/[/cyan]")
            console.print(f"  2. Update variables in [cyan]{terraform_dir}/variables.tf[/cyan]")
            console.print(f"  3. Run: [yellow]cd {terraform_dir} && terraform init[/yellow]")
            console.print(f"  4. Run: [yellow]terraform plan[/yellow]")
            console.print(f"  5. Run: [yellow]terraform apply[/yellow]")
        
        ssh.close()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠[/yellow] Interrupted by user")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def display_profile_summary(profile):
    """Display a summary of the profiled server."""
    console.print("\n[bold]Profile Summary:[/bold]")
    
    # OS Info
    os_info = profile.get('os_info', {})
    console.print(f"  OS: {os_info.get('name', 'Unknown')} {os_info.get('version', '')}")
    console.print(f"  Kernel: {os_info.get('kernel', 'Unknown')}")
    console.print(f"  Architecture: {os_info.get('architecture', 'Unknown')}")
    
    # Hardware
    hardware = profile.get('hardware', {})
    console.print(f"  CPU: {hardware.get('cpu_cores', 0)} cores")
    console.print(f"  Memory: {hardware.get('memory_mb', 0)} MB")
    
    # Network
    network = profile.get('network', {})
    console.print(f"  Hostname: {network.get('hostname', 'Unknown')}")
    console.print(f"  Public IP: {network.get('public_ip', 'Unknown')}")
    
    # Software
    services = profile.get('services', [])
    console.print(f"  Services: {len(services)} running")
    
    software = profile.get('software', {})
    if software:
        console.print("  Installed software:")
        for name in list(software.keys())[:5]:
            console.print(f"    - {name}")
    
    packages = profile.get('packages', [])
    console.print(f"  Packages: {len(packages)} installed")


if __name__ == '__main__':
    main()
