#!/usr/bin/env python3
"""
Server Profiler & Terraform Generator

A CLI tool to profile remote servers and generate Terraform configuration.
"""
import json
import sys

import click
import rich_click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from ssh_connector import SSHConnector, parse_lightsail_config
from server_profiler import ServerProfiler
from terraform_generator import TerraformGenerator

VERSION = "0.2.0"

console = Console()

rich_click.USE_RICH_MARKUP = True
rich_click.STYLE_OPTIONS_PANEL_BORDER = "cyan"
rich_click.STYLE_COMMANDS_PANEL_BORDER = "green"
rich_click.STYLE_OPTION = "bold cyan"
rich_click.STYLE_OPTION_DEFAULT = "dim"
rich_click.STYLE_USAGE = "bold yellow"
rich_click.STYLE_HEADER = "bold cyan"
rich_click.STYLE_HELPTEXT_FIRST_LINE = "bold"
rich_click.WIDTH = 90
rich_click.SHOW_METAVARS_COLUMN = True
rich_click.APPEND_METAVARS_HELP = True
rich_click.GROUP_ARGUMENTS_OPTIONAL = True


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


EPILOG_ROOT = """
Examples:

    server-profiler profile --host 54.123.45.67 --user admin --key ~/.ssh/id_rsa
    server-profiler profile --lightsail-config ~/.ssh/lightsail --instance-name my-server --no-terraform
    server-profiler terraform -i profile.json
    server-profiler --version
"""

EPILOG_PROFILE = """
Examples:

    # Direct SSH connection
    server-profiler profile --host example.com --user admin --key ~/.ssh/id_rsa

    # Using AWS Lightsail SSH config
    server-profiler profile --lightsail-config ~/.ssh/lightsail-ssh-config --instance-name my-server

    # Profile only, skip Terraform generation
    server-profiler profile --host example.com --key ~/.ssh/id_rsa --no-terraform --output server.json

    # Custom port and verbose output
    server-profiler profile --host 10.0.1.100 --user ubuntu --key ~/.ssh/key.pem --port 2222 -v

Output files:

    profile.json               Complete server profile (JSON)
    terraform/main.tf          Lightsail instance and networking config
    terraform/variables.tf     Configurable Terraform variables
    terraform/provisioner.tf   Remote-exec provisioning
    terraform/outputs.tf       Instance output definitions
    terraform/startup.sh       User data bootstrap script
"""

EPILOG_TERRAFORM = """
Examples:

    server-profiler terraform                              (default profile.json)
    server-profiler terraform -i backups/prod-server.json  (custom input)
    server-profiler terraform -i profile.json --terraform-dir ./infra/terraform
"""


@click.group(cls=rich_click.RichGroup, context_settings={"help_option_names": ["-h", "--help"]}, epilog=EPILOG_ROOT)
@click.version_option(version=VERSION, prog_name="server-profiler", message="%(prog)s v%(version)s")
def cli():
    """Server Profiler & Terraform Generator

    Profile remote servers and generate Terraform infrastructure-as-code
    to recreate them on AWS Lightsail.
    """


@cli.command(epilog=EPILOG_PROFILE)
@click.option("--host", help="Remote server [cyan]hostname[/cyan] or [cyan]IP address[/cyan] to connect to")
@click.option("--user", default="admin", show_default=True,
              help="[cyan]SSH username[/cyan] for the remote connection")
@click.option("--key", help="Path to [cyan]SSH private key[/cyan] file (e.g. [i]~/.ssh/id_rsa[/i])")
@click.option("--password", help="[cyan]SSH password[/cyan] for authentication (alternative to --key)")
@click.option("--port", default=22, type=int, show_default=True,
              help="[cyan]SSH port number[/cyan]")
@click.option("--lightsail-config",
              help="Path to [cyan]AWS Lightsail SSH config[/cyan] file (alternative to --host)")
@click.option("--instance-name",
              help="[cyan]Instance name[/cyan] in Lightsail config file (used with --lightsail-config)")
@click.option("--terraform/--no-terraform", default=True,
              help="Enable or disable [cyan]Terraform[/cyan] configuration generation")
@click.option("--output", default="profile.json", show_default=True,
              help="Path to write the server [cyan]profile JSON[/cyan] output")
@click.option("--terraform-dir", default="terraform", show_default=True,
              help="Directory to write generated [cyan]Terraform[/cyan] files into")
@click.option("--verbose", "-v", is_flag=True,
              help="Show [cyan]detailed profiling progress[/cyan] for each step")
def profile(host, user, key, password, port, lightsail_config, instance_name,
            terraform, output, terraform_dir, verbose):
    """Profile a remote server over SSH.

    Connects to a remote server and collects system configuration:
    operating system, hardware specs, network configuration, installed
    packages, running services, firewall rules, storage, user accounts,
    cron jobs, and detected software.

    Optionally generates Terraform configuration to recreate the server
    as an AWS Lightsail instance.
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


@cli.command(epilog=EPILOG_TERRAFORM)
@click.option("--input", "-i", "input_file", default="profile.json", show_default=True,
              help="Path to an existing server [cyan]profile JSON[/cyan] file to load")
@click.option("--terraform-dir", default="terraform", show_default=True,
              help="Directory to write the generated [cyan]Terraform[/cyan] files into")
@click.option("--verbose", "-v", is_flag=True,
              help="Show [cyan]detailed progress[/cyan] during Terraform file generation")
def terraform(input_file, terraform_dir, verbose):
    """Generate Terraform from an existing profile.

    Takes a previously generated profile.json and recreates the
    Terraform configuration files (main.tf, variables.tf,
    provisioner.tf, outputs.tf, startup.sh) without needing to
    re-profile the server. Useful for iterating on IaC output.
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
