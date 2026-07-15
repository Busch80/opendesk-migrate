"""CLI to generate a Fernet key (run once during bootstrap)."""

from __future__ import annotations

import sys

import click

from app.services.encryption.cipher import generate_fernet_key


@click.command()
@click.option(
    "--length",
    default=48,
    help="Number of random bytes (more = more entropy). 32 is minimum, 44 is default.",
)
def main(length: int) -> None:
    """Generate a base64-url encoded Fernet key for FERNET_KEY."""
    if length < 32:
        click.echo("Length must be >= 32 bytes for sufficient entropy.", err=True)
        sys.exit(1)
    key = generate_fernet_key()
    click.echo(key)
    click.echo("# Example:", err=True)
    click.echo(f"# FERNET_KEY={key}", err=True)


if __name__ == "__main__":
    main()
