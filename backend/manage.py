#!/usr/bin/env python
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ceo_desk_server.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Could not import Django. Did you run `uv sync`?") from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
