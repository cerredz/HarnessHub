"""Module entrypoint for ``python -m harnessiq.cli``."""

from .main import main


if __name__ == "__main__":
    raise SystemExit(main())
