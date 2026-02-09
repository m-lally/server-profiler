"""
Example usage of the Server Profiler tool.
"""

# Example 1: Direct SSH connection
example_1 = """
python profiler.py \\
  --host 54.123.45.67 \\
  --user admin \\
  --key ~/.ssh/lightsail-key.pem \\
  --terraform
"""

# Example 2: Using Lightsail SSH config
example_2 = """
# First, ensure your Lightsail SSH config is in place
# Typically at: ~/.ssh/lightsail-ssh-config

# Then run:
python profiler.py \\
  --lightsail-config ~/.ssh/lightsail-ssh-config \\
  --instance-name my-debian-server \\
  --terraform
"""

# Example 3: Profile only, no Terraform generation
example_3 = """
python profiler.py \\
  --host example.com \\
  --user root \\
  --key ~/.ssh/id_rsa \\
  --no-terraform \\
  --output server-inventory.json
"""

# Example 4: Custom output directory
example_4 = """
python profiler.py \\
  --host 10.0.1.100 \\
  --user admin \\
  --key ~/.ssh/key.pem \\
  --terraform-dir ./my-terraform \\
  --output ./profiles/server1.json
"""

# Example AWS Lightsail SSH config format:
lightsail_config_example = """
# ~/.ssh/lightsail-ssh-config

Host my-debian-server
    HostName 54.123.45.67
    User admin
    IdentityFile ~/.ssh/LightsailDefaultKey-us-east-1.pem
    Port 22

Host my-ubuntu-server
    HostName 18.234.56.78
    User ubuntu
    IdentityFile ~/.ssh/LightsailDefaultKey-us-east-1.pem
    Port 22
"""

if __name__ == '__main__':
    print("Server Profiler - Usage Examples")
    print("=" * 50)
    
    print("\n1. Direct SSH Connection:")
    print(example_1)
    
    print("\n2. Using Lightsail SSH Config:")
    print(example_2)
    
    print("\n3. Profile Only (No Terraform):")
    print(example_3)
    
    print("\n4. Custom Output Directory:")
    print(example_4)
    
    print("\n\nLightsail SSH Config Format:")
    print(lightsail_config_example)
    
    print("\n\nWorkflow:")
    print("1. Run the profiler to analyze your server")
    print("2. Review the generated profile.json")
    print("3. Review and customize Terraform files in terraform/")
    print("4. Initialize Terraform: cd terraform && terraform init")
    print("5. Plan deployment: terraform plan")
    print("6. Apply configuration: terraform apply")
