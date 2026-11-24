import pygame

_cache = {}


def get_font(size):
    """Schriften nur einmal erzeugen (SysFont ist langsam)."""
    size = max(8, int(size))
    font = _cache.get(size)
    if font is None:
        font = pygame.font.SysFont(None, size)
        _cache[size] = font
    return font
