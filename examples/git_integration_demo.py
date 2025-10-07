"""
Demo script showing Git auto-commit functionality

This script demonstrates how AutoDevOps automatically commits
each generated infrastructure file to Git with descriptive messages.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from audit.version_control import GitVersionControl
from generators.terraform import TerraformGenerator
from generators.kubernetes import KubernetesGenerator
from parsers.intent_parser import IntentParser
from parsers.parameter_extractor import ParameterExtractor


def demo_git_integration():
    """Demonstrate Git integration with auto-commit"""
    
    print("=" * 60)
    print("AutoDevOps Git Integration Demo")
    print("=" * 60)
    print()
    
    # Initialize Git version control
    print("1. Initializing Git repository...")
    git = GitVersionControl(
        repo_path="./infrastructure",
        auto_commit=True,
        user_name="AutoDevOps Bot",
        user_email="bot@autodevops.io"
    )
    print(f"   ✓ Git repository initialized at ./infrastructure")
    print()
    
    # Example 1: Generate Terraform code
    print("2. Generating Terraform infrastructure...")
    
    # Parse user intent
    user_request = "Create an EC2 instance with t3.micro on AWS"
    intent_parser = IntentParser()
    param_extractor = ParameterExtractor()
    
    intent = intent_parser.parse(user_request)
    parameters = param_extractor.extract(user_request, intent)
    
    # Generate Terraform code with Git integration
    terraform_gen = TerraformGenerator(
        output_dir="./infrastructure/terraform",
        git_integration=git,
        auto_commit=True
    )
    
    code = terraform_gen.generate(intent, parameters)
    
    # Save and auto-commit
    metadata = {
        "user_request": user_request,
        "iac_type": "terraform",
        "provider": intent.get("provider"),
        "action": intent.get("action")
    }
    
    file_path = terraform_gen.save_to_file(
        code=code,
        filename="main.tf",
        commit_metadata=metadata
    )
    
    print(f"   ✓ Generated and committed: {file_path}")
    print()
    
    # Example 2: Generate Kubernetes manifests
    print("3. Generating Kubernetes manifests...")
    
    user_request_k8s = "Deploy a web app with 3 replicas on Kubernetes"
    intent_k8s = intent_parser.parse(user_request_k8s)
    parameters_k8s = param_extractor.extract(user_request_k8s, intent_k8s)
    
    k8s_gen = KubernetesGenerator(
        output_dir="./infrastructure/kubernetes",
        git_integration=git,
        auto_commit=True
    )
    
    k8s_code = k8s_gen.generate(intent_k8s, parameters_k8s)
    
    metadata_k8s = {
        "user_request": user_request_k8s,
        "iac_type": "kubernetes",
        "action": intent_k8s.get("action")
    }
    
    k8s_file_path = k8s_gen.save_to_file(
        code=k8s_code,
        filename="deployment.yaml",
        commit_metadata=metadata_k8s
    )
    
    print(f"   ✓ Generated and committed: {k8s_file_path}")
    print()
    
    # Show Git history
    print("4. Git commit history:")
    print("-" * 60)
    
    latest_commit = git.get_latest_commit()
    if latest_commit:
        print(f"   Latest commit: {latest_commit['short_sha']}")
        print(f"   Author: {latest_commit['author']}")
        print(f"   Date: {latest_commit['date']}")
        print(f"   Message: {latest_commit['message'][:100]}...")
    
    print()
    
    # Show file history
    print("5. File commit history for main.tf:")
    print("-" * 60)
    
    history = git.get_file_history("terraform/main.tf", max_count=5)
    for i, commit in enumerate(history, 1):
        print(f"   {i}. {commit['short_sha']} - {commit['date']}")
        print(f"      {commit['message'].split(chr(10))[0]}")
    
    print()
    
    # Show uncommitted changes
    print("6. Checking for uncommitted changes...")
    has_changes = git.has_uncommitted_changes()
    if has_changes:
        print("   ⚠ There are uncommitted changes")
        print(f"   Diff:\n{git.get_diff()}")
    else:
        print("   ✓ All changes are committed")
    
    print()
    print("=" * 60)
    print("Demo completed!")
    print("=" * 60)
    print()
    print("Key Features Demonstrated:")
    print("  • Automatic Git initialization")
    print("  • Auto-commit on file generation")
    print("  • Descriptive commit messages with metadata")
    print("  • Commit history tracking")
    print("  • File-specific history")
    print()
    print("Check the ./infrastructure directory for generated files")
    print("Use 'git log' in that directory to see all commits")


if __name__ == "__main__":
    try:
        demo_git_integration()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
