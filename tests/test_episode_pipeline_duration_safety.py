import math
import pytest

from core.episode_pipeline import _positive_duration


@pytest.mark.parametrize(
    "values, expected",
    [
        ((float("nan"), 8), 8),
        ((float("inf"), 7.5), 7.5),
        ((float("-inf"), 6), 6),
        (("bad", None, 4), 4),
        ((0, -2, 3), 3),
        ((float("nan"), float("inf")), 5),
        ((float("nan"),), 9),
    ],
)
def test_positive_duration_skips_invalid_values(values, expected):
    fallback = 9 if expected == 9 else 5
    actual = _positive_duration(*values, default=fallback)
    assert math.isfinite(actual)
    assert actual == expected


def test_positive_duration_rejects_invalid_fallback():
    assert _positive_duration(float("nan"), default=float("inf")) == 5
