#!/usr/bin/env python3
"""
Server Profiler & Terraform Generator

A CLI tool to profile remote servers and generate Terraform configuration.
"""
import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.columns import Columns
from rich import box
from rich.syntax import Syntax

from ssh_connector import SSHConnector, parse_lightsail_config
from server_profiler import ServerProfiler
from terraform_generator import TerraformGenerator

VERSION = "0.2.0"

console = Console()


def show_splash():
    console.print()
    console.print(Panel.fit(
        "[bold cyan]╔══════════════════════════════════════╗\n"
        "║       Server Profiler & Terraform       ║\n"
        "║         Infrastructure-as-Code           ║\n"
        "╚══════════════════════════════════════╝[/bold cyan]\n\n"
        "[dim]Profile remote servers and generate Terraform configuration.[/dim]",
        border_style="cyan",
        padding=(1, 2)
    ))


def show_profile_summary(profile):
    os_info = profile.get('os_info', {})
    hardware = profile.get('hardware', {})
    network = profile.get('network', {})
    services = profile.get('services', [])
    packages = profile.get('packages', [])
    storage = profile.get('storage', {})
    users = profile.get('users', [])
    firewall = profile.get('firewall', {})
    software = profile.get('software', {})

    table = Table(title="Profile Summary", box=box.ROUNDED, title_style="bold cyan")
    table.add_column("Category", style="yellow", no_wrap=True)
    table.add_column("Detail", style="white")

    table.add_row("OS", f"{os_info.get('name', 'Unknown')} {os_info.get('version_id', '')}")
    table.add_row("Kernel", os_info.get('kernel', 'Unknown'))
    table.add_row("Architecture", os_info.get('architecture', 'Unknown'))
    table.add_row("Hostname", network.get('hostname', 'Unknown'))
    table.add_row("Public IP", network.get('public_ip', 'Unknown') or 'N/A')
    table.add_row("CPU", f"{hardware.get('cpu_cores', 0)} cores")
    table.add_row("Memory", f"{hardware.get('memory_mb', 0)} MB")

    listening = network.get('listening_ports', [])
    if listening:
        table.add_row("Open Ports", ", ".join(str(p) for p in listening[:10]))

    mounts = storage.get('mounts', [])
    if mounts:
        root = next((m for m in mounts if m['mount_point'] == '/'), mounts[0])
        table.add_row("Disk", f"{root.get('used', '?')} / {root.get('size', '?')} ({root.get('use_percent', '?')})")

    table.add_row("Running Services", str(len(services)))
    table.add_row("Installed Packages", str(len(packages)))
    table.add_row("User Accounts", str(len(users)))
    table.add_row("Firewall", str(firewall.get('type', 'None')).capitalize())
    table.add_row("Detected Software", str(len(software)))

    console.print()
    console.print(table)

    if software:
        sw_table = Table(title="Detected Software", box=box.SIMPLE, title_style="bold green")
        sw_table.add_column("Name", style="green")
        sw_table.add_column("Version", style="white")
        for name, info in sorted(software.items()):
            version = info.get('version', 'installed')
            sw_table.add_row(name, version)
        console.print()
        console.print(sw_table)


def build_profile_dict(output_file: str) -> dict:
    try:
        with open(output_file) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        console.print(f"[red]✗[/red] Failed to load profile: {e}")
        sys.exit(1)


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(version=VERSION, prog_name="server-profiler", message="%(prog)s v%(version)s")
def cli():
    """Server Profiler & Terraform Generator

    Profile remote servers and generate Terraform infrastructure-as-code.
    """


@cli.command()
@click.option("--host", help="Remote server hostname or IP")
@click.option("--user", default="admin", show_default=True, help="SSH username")
@click.option("--key", help="Path to SSH private key file")
@click.option("--password", help="SSH password (if not using key)")
@click.option("--port", default=22, type=int, show_default=True, help="SSH port")
@click.option("--lightsail-config", help="Path to Lightsail SSH config file")
@click.option("--instance-name", help="Instance name in Lightsail config")
@click.option("--terraform/--no-terraform", default=True, help="Generate Terraform configuration")
@click.option("--output", default="profile.json", show_default=True, help="Output file for profile")
@click.option("--terraform-dir", default="terraform", show_default=True, help="Directory for Terraform files")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed progress")
def profile(host, user, key, password, port, lightsail_config, instance_name,
            terraform, output, terraform_dir, verbose):
    """Profile a remote server over SSH.

    Connects to a remote server, profiles its system configuration (OS,
    hardware, network, packages, services, firewall, storage, users,
    cron jobs, and installed software), then optionally generates
    Terraform configuration to recreate it on AWS Lightsail.
    """
    show_splash()

    if lightsail_config and instance_name:
        try:
            config = parse_lightsail_config(lightsail_config, instance_name)
            host = config["host"]
            user = config["username"]
            key = config["key_file"]
            port = config["port"]
            console.print(f"[green]✓[/green] Loaded Lightsail config for: [bold]{instance_name}[/bold]")
        except Exception as e:
            console.print(f"[red]✗[/red] Error parsing Lightsail config: {e}")
            sys.exit(1)
    elif not host:
        console.print("[red]✗[/red] Either --host or --lightsail-config + --instance-name required")
        console.print()
        ctx = click.get_current_context()
        click.echo(ctx.get_help())
        sys.exit(1)

    if not key and not password:
        console.print("[red]✗[/red] Either --key or --password required")
        sys.exit(1)

    console.print(f"\n[bold yellow]⟐[/bold yellow] Connecting to [bold]{host}[/bold] on port [bold]{port}[/bold]...")

    try:
        ssh = SSHConnector(host=host, username=user, key_file=key,
                           password=password, port=port)

        if not ssh.connect():
            console.print("[red]✗[/red] Failed to connect to server")
            sys.exit(1)

        console.print(f"[green]✓[/green] Connected to {host}\n")

        profiler = ServerProfiler(ssh, console=console, verbose=verbose)
        profile_data = profiler.profile_all()

        profiler.save_profile(output)

        show_profile_summary(profile_data)

        if terraform:
            console.print()
            generator = TerraformGenerator(profile_data, output_dir=terraform_dir, console=console)
            generator.generate_all()

            console.print()
            console.print(Panel.fit(
                "[bold green]Infrastructure as Code generated successfully![/bold green]\n\n"
                f"Next steps:\n"
                f"  1. Review the Terraform files in [cyan]{terraform_dir}/[/cyan]\n"
                f"  2. Update variables in [cyan]{terraform_dir}/variables.tf[/cyan]\n"
                f"  3. [yellow]cd {terraform_dir}[/yellow]\n"
                f"  4. [yellow]terraform init[/yellow]\n"
                f"  5. [yellow]terraform plan[/yellow]\n"
                f"  6. [yellow]terraform apply[/yellow]",
                border_style="green",
                padding=(1, 2)
            ))

        ssh.close()

        console.print()
        console.print("[dim]Profile complete.[/dim]")

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠[/yellow] Interrupted by user")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.option("--input", "-i", "input_file", default="profile.json", show_default=True,
              help="Input profile JSON file")
@click.option("--terraform-dir", default="terraform", show_default=True,
              help="Directory for Terraform files")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed progress")
def terraform(input_file, terraform_dir, verbose):
    """Generate Terraform from an existing profile.

    Takes a previously generated profile.json and recreates
    the Terraform configuration files without re-profiling.
    """
    profile_data = build_profile_dict(input_file)

    os_info = profile_data.get("os_info", {})
    hardware = profile_data.get("hardware", {})
    network = profile_data.get("network", {})
    console.print(f"[green]✓[/green] Loaded profile for [bold]{network.get('hostname', '?')}[/bold] "
                  f"({os_info.get('name', '?')} / {hardware.get('cpu_cores', '?')} vCPU / "
                  f"{hardware.get('memory_mb', '?')} MB)")

    generator = TerraformGenerator(profile_data, output_dir=terraform_dir, console=console)
    generator.generate_all()

    console.print()
    console.print(Panel.fit(
        "[bold green]Terraform configuration regenerated![/bold green]",
        border_style="green"
    ))


if __name__ == "__main__":
    cli()
