"""Small terminal interaction helpers for CLI commands."""

from __future__ import annotations

import os
import sys
from typing import TextIO


def select_index(
    prompt: str,
    options: list[str],
    *,
    input_stream: TextIO | None = None,
    output_stream: TextIO | None = None,
) -> int:
    """Return the selected option index from a short interactive list."""
    if not options:
        raise ValueError("options must not be empty.")
    if len(options) == 1:
        return 0
    resolved_input = input_stream or sys.stdin
    resolved_output = output_stream or sys.stdout
    if _supports_tty_selection(resolved_input, resolved_output):
        return _select_index_tty(prompt, options, output_stream=resolved_output)
    return _select_index_numbered(prompt, options, output_stream=resolved_output)


def _supports_tty_selection(input_stream: TextIO, output_stream: TextIO) -> bool:
    if not hasattr(input_stream, "isatty") or not hasattr(output_stream, "isatty"):
        return False
    if not input_stream.isatty() or not output_stream.isatty():
        return False
    if os.name != "nt" and os.environ.get("TERM", "").lower() in {"", "dumb"}:
        return False
    return True


def _select_index_tty(prompt: str, options: list[str], *, output_stream: TextIO) -> int:
    selected_index = 0
    line_count = len(options) + 2
    first_render = True
    while True:
        if not first_render:
            output_stream.write(f"\x1b[{line_count}F\x1b[J")
        output_stream.write(f"{prompt}\n")
        output_stream.write("Use the arrow keys and press Enter.\n")
        for index, label in enumerate(options):
            prefix = "> " if index == selected_index else "  "
            output_stream.write(f"{prefix}{label}\n")
        output_stream.flush()
        first_render = False

        key = _read_tty_key()
        if key == "up":
            selected_index = (selected_index - 1) % len(options)
            continue
        if key == "down":
            selected_index = (selected_index + 1) % len(options)
            continue
        if key == "enter":
            output_stream.write("\n")
            output_stream.flush()
            return selected_index
        if key == "interrupt":
            raise KeyboardInterrupt


def _select_index_numbered(prompt: str, options: list[str], *, output_stream: TextIO) -> int:
    output_stream.write(f"{prompt}\n")
    for index, label in enumerate(options, start=1):
        output_stream.write(f"{index}. {label}\n")
    output_stream.flush()
    while True:
        raw = input("Select one option by number: ").strip()
        if not raw:
            continue
        if not raw.isdigit():
            output_stream.write("Please enter a number.\n")
            output_stream.flush()
            continue
        choice = int(raw)
        if 1 <= choice <= len(options):
            return choice - 1
        output_stream.write(f"Please enter a number between 1 and {len(options)}.\n")
        output_stream.flush()


def _read_tty_key() -> str:
    if os.name == "nt":
        return _read_tty_key_windows()
    return _read_tty_key_posix()


def _read_tty_key_windows() -> str:
    import msvcrt

    first = msvcrt.getwch()
    if first in {"\x00", "\xe0"}:
        second = msvcrt.getwch()
        return {
            "H": "up",
            "P": "down",
        }.get(second, "other")
    if first == "\r":
        return "enter"
    if first == "\x03":
        return "interrupt"
    return "other"


def _read_tty_key_posix() -> str:
    import termios
    import tty

    file_descriptor = sys.stdin.fileno()
    original = termios.tcgetattr(file_descriptor)
    try:
        tty.setraw(file_descriptor)
        first = sys.stdin.read(1)
        if first == "\x1b":
            second = sys.stdin.read(1)
            third = sys.stdin.read(1)
            if second == "[":
                return {
                    "A": "up",
                    "B": "down",
                }.get(third, "other")
            return "other"
        if first in {"\r", "\n"}:
            return "enter"
        if first == "\x03":
            return "interrupt"
        return "other"
    finally:
        termios.tcsetattr(file_descriptor, termios.TCSADRAIN, original)


__all__ = ["select_index"]
