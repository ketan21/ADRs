"""
Example: Test automation retrieving Pega test operator passwords from Azure Key Vault.

Usage:
    export AZURE_KEY_VAULT_URL=https://my-vault.vault.azure.net/
    python test_automation_example.py --operator test_user_01
"""
import argparse
import os

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


def get_operator_password(vault_url: str, operator_id: str) -> str:
    """Retrieve current password for a Pega test operator from AKV."""
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=vault_url, credential=credential)

    secret_name = f"pega-test-op-{operator_id}"
    secret = client.get_secret(secret_name)

    # Validate tags for freshness
    tags = secret.properties.tags or {}
    rotated = tags.get("last-rotated", "unknown")
    env = tags.get("environment", "unknown")

    print(f"Retrieved secret: {secret_name}")
    print(f"  Environment: {env}")
    print(f"  Last rotated: {rotated}")
    print(f"  Version: {secret.properties.version}")

    return secret.value


def main():
    parser = argparse.ArgumentParser(description="Fetch Pega test operator password from AKV")
    parser.add_argument("--vault", default=os.environ.get("AZURE_KEY_VAULT_URL"), help="AKV URL")
    parser.add_argument("--operator", required=True, help="Pega operator ID")
    args = parser.parse_args()

    if not args.vault:
        raise SystemExit("Error: --vault or AZURE_KEY_VAULT_URL required")

    password = get_operator_password(args.vault, args.operator)
    # Use password in your test automation (e.g., Selenium, Playwright, API calls)
    print(f"Password length: {len(password)} chars")


if __name__ == "__main__":
    main()
