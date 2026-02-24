"""Entry point for PontySpeech."""

import sys


def main():
    """Main entry point."""
    from .app import PontySpeechApp

    app = PontySpeechApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
