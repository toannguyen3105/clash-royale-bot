import cv2
import numpy as np
import os
from utils.logger import logger

class Detector:
    """Handles all image processing and template matching logic."""

    @staticmethod
    def find_all(screen_path, template_path, threshold=0.8):
        """Find every on-screen location where a template matches above threshold.
        Returns a list of (x, y) top-left coordinates, top-to-bottom, de-duplicated
        so overlapping matches of the same on-screen element only count once."""
        if not os.path.exists(template_path):
            logger.error(f"Template file not found at {template_path}")
            return []

        screen = cv2.imread(screen_path)
        template = cv2.imread(template_path)

        if screen is None or template is None:
            logger.error(f"Could not read images from {screen_path} or {template_path}")
            return []

        h, w = template.shape[:2]
        res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        ys, xs = np.where(res >= threshold)
        candidates = sorted(zip(xs.tolist(), ys.tolist()), key=lambda p: -res[p[1], p[0]])

        kept = []
        for x, y in candidates:
            if all(abs(x - kx) >= w // 2 or abs(y - ky) >= h // 2 for kx, ky in kept):
                kept.append((x, y))

        return sorted(kept, key=lambda p: p[1])

    @staticmethod
    def match_template(screen_path, template_path):
        """Find a template image in the screenshot and return max match value."""
        if not os.path.exists(template_path):
            logger.error(f"Template file not found at {template_path}")
            return 0.0

        screen = cv2.imread(screen_path)
        template = cv2.imread(template_path)

        if screen is None or template is None:
            logger.error(f"Could not read images from {screen_path} or {template_path}")
            return 0.0

        # Template Matching
        res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv2.minMaxLoc(res)
        
        logger.info(f"Matching {os.path.basename(template_path)}: Max match value: {max_val:.2f}")
        return max_val

    @staticmethod
    def is_present(screen_path, template_path, threshold=0.8):
        """Check if a template exists on the screen above the threshold."""
        return Detector.match_template(screen_path, template_path) >= threshold

    @staticmethod
    def is_gray_region(screen_path, center, half_size, max_channel_spread):
        """Check whether the area around `center` (half_size = (half_w, half_h)) is
        colorless: its mean B, G and R differ by at most `max_channel_spread`.
        Useful where a button's state is shown by color alone (e.g. grayed out)."""
        screen = cv2.imread(screen_path)
        if screen is None:
            logger.error(f"Could not read image from {screen_path}")
            return False

        (cx, cy), (hw, hh) = center, half_size
        region = screen[max(0, cy - hh):cy + hh, max(0, cx - hw):cx + hw]
        if region.size == 0:
            return False

        mean_bgr = region.reshape(-1, 3).mean(axis=0)
        return float(mean_bgr.max() - mean_bgr.min()) <= max_channel_spread
