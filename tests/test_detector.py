import cv2
import numpy as np
from vision.detector import Detector

# TM_CCOEFF_NORMED always scores 0 for a flat/solid-color template (its normalized
# cross-correlation formula divides by zero variance), so the fixtures below use a
# checkerboard patch with actual contrast/texture, matching how real UI screenshot
# crops (text, icons) behave.
_PATCH = np.zeros((20, 20, 3), dtype=np.uint8)
_PATCH[0:10, 0:10] = (255, 255, 255)
_PATCH[10:20, 10:20] = (255, 255, 255)


def _make_template(tmp_path):
    path = str(tmp_path / "template.png")
    cv2.imwrite(path, _PATCH)
    return path


def _make_screen(tmp_path, positions, size=(200, 200)):
    screen = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    for x, y in positions:
        screen[y:y + 20, x:x + 20] = _PATCH
    path = str(tmp_path / "screen.png")
    cv2.imwrite(path, screen)
    return path


def test_find_all_returns_every_distinct_match(tmp_path):
    """Test find_all locates multiple separate occurrences of a template, sorted top-to-bottom."""
    template_path = _make_template(tmp_path)
    positions = [(150, 150), (10, 10), (10, 100)]
    screen_path = _make_screen(tmp_path, positions)

    matches = Detector.find_all(screen_path, template_path, threshold=0.9)

    assert matches == [(10, 10), (10, 100), (150, 150)]  # sorted by y


def test_find_all_deduplicates_overlapping_matches(tmp_path):
    """Test find_all collapses a cluster of near-identical high-score matches into one."""
    template_path = _make_template(tmp_path)
    # Two placements of the patch 1px apart produce overlapping high-score matches
    # that should collapse into a single reported location.
    screen_path = _make_screen(tmp_path, positions=[(30, 30), (31, 31)])

    matches = Detector.find_all(screen_path, template_path, threshold=0.9)

    assert len(matches) == 1


def test_find_all_returns_empty_list_when_no_match(tmp_path):
    """Test find_all returns an empty list when the template isn't present."""
    template_path = _make_template(tmp_path)
    screen_path = _make_screen(tmp_path, positions=[])

    matches = Detector.find_all(screen_path, template_path, threshold=0.9)

    assert matches == []


def test_find_all_missing_template_file_returns_empty_list(tmp_path):
    """Test find_all fails safe (empty list, no exception) when the template file is missing."""
    screen_path = _make_screen(tmp_path, positions=[])

    matches = Detector.find_all(screen_path, "does/not/exist.png", threshold=0.9)

    assert matches == []
