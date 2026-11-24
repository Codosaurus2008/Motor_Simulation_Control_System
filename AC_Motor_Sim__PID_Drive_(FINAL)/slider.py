import pygame
from fonts import get_font


class Slider:
    def __init__(self, x, y, width, min_val, max_val, start_val, label,
                 scale=1.0, unit="", decimals=2):
        self.x = x
        self.y = y
        self.width = width

        self.min = min_val
        self.max = max_val
        self.value = min(max_val, max(min_val, start_val))

        self.label = label
        self.unit = unit
        self.decimals = decimals
        self.dragging = False
        self.scale = scale
        self.line_width = max(2, int(4 * scale))
        self.knob_radius = max(6, int(13 * scale))
        self.font_size = max(16, int(28 * scale))
        self.label_offset = max(20, int(30 * scale))

    def _set_from_x(self, mx):
        ratio = (mx - self.x) / self.width
        ratio = max(0.0, min(1.0, ratio))
        self.value = self.min + ratio * (self.max - self.min)

    def handle_event(self, event):
        """event.pos muss bereits in Koordinaten der Slider-Flaeche sein."""
        if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, "button", 1) == 1:
            if self.is_hover(event.pos):
                self.dragging = True
                self._set_from_x(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and getattr(event, "button", 1) == 1:
            self.dragging = False
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_from_x(event.pos[0])

    def is_hover(self, pos):
        x, y = pos
        r = self.knob_radius
        return (self.x - r <= x <= self.x + self.width + r
                and self.y - r <= y <= self.y + r)

    def draw(self, surface):
        pygame.draw.line(surface, (250, 250, 250),
                         (self.x, self.y), (self.x + self.width, self.y),
                         self.line_width)

        span = self.max - self.min
        ratio = (self.value - self.min) / span if span else 0.0
        hx = int(self.x + ratio * self.width)
        pygame.draw.circle(surface, (255, 100, 100), (hx, self.y), self.knob_radius)

        text = f"{self.label}: {self.value:.{self.decimals}f} {self.unit}".rstrip()
        surface.blit(get_font(self.font_size).render(text, True, (0, 0, 0)),
                     (self.x, self.y - self.label_offset))
