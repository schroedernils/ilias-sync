"""Readable ink for every pause state, independent of UI rendering."""
import pytest

from ilias_sync.control_colors import pause_colors


def luminance(color):
    channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


@pytest.mark.parametrize('dark', [True, False])
def test_pause_ink_stays_readable_in_every_interaction_state(dark):
    colors = pause_colors(dark)
    for surface in (colors.fill, colors.hover, colors.pressed):
        lower, upper = sorted([luminance(surface), luminance(colors.ink)])
        assert (upper + 0.05) / (lower + 0.05) >= 4.5
