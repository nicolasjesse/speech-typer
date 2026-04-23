"""Entry point for Holler."""

import sys


def main():
    """Main entry point."""
    from .app import HollerApp

    app = HollerApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
