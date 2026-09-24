import math
import os
import random
import sys
from dataclasses import dataclass

import pygame

# ============================================================
# NEON DRIFT
# A complete single-file arcade game made with Python + Pygame.
# No external images, sounds, or fonts are required.
# ============================================================

# Some environments (headless CI, container shells, remote sessions) do not
# have a real display. Set a safe dummy video driver so the game can start
# without crashing during initialization.
if os.environ.get("DISPLAY", "") == "" and os.environ.get("SDL_VIDEODRIVER") is None:
    os.environ["SDL_VIDEODRIVER"] = "dummy"

pygame.init()
pygame.mixer.quit()
