"""Shared control colors for stylesheet states, icons and animated fills."""
from typing import NamedTuple


class PauseColors(NamedTuple):
    fill: str
    hover: str
    pressed: str
    ink: str


def pause_colors(dark):
    if dark:
        return PauseColors('#2c2c2c', '#3a3a3a', '#242424', '#f0f0f0')
    return PauseColors('#e9d7b4', '#dfc9a1', '#d3b98f', '#594422')
