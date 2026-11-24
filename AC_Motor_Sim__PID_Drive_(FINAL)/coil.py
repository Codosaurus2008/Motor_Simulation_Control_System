import pygame
from fonts import get_font


class Coil:
    """Eine Spulenseite der Staenderwicklung.

    sign = +1: Hinleiter (z.B. A), sign = -1: Rueckleiter (A').
    Farbe: rot = Strom aus der Bildebene heraus, blau = hinein.
    Die Helligkeit zeigt die Stromstaerke relativ zu i_scale.
    """

    def __init__(self, position, phase, sign=1, scale=1.0, i_scale=15.0):
        self.position = position
        self.phase = phase
        self.sign = sign
        self.scale = scale
        self.i_scale = i_scale
        self.current = 0.0

    def set_current(self, phase_current):
        self.current = self.sign * phase_current

    def draw(self, screen):
        x, y = int(self.position[0]), int(self.position[1])
        intensity = min(1.0, abs(self.current) / max(self.i_scale, 1e-6))
        level = int(60 + 195 * intensity)
        if self.current >= 0:
            color = (level, 30, 30)
        else:
            color = (30, 30, level)

        radius = max(6, int(14 * self.scale))
        pygame.draw.circle(screen, color, (x, y), radius)
        pygame.draw.circle(screen, (200, 200, 200), (x, y), radius, 1)

        name = self.phase + ("" if self.sign > 0 else "'")
        label = get_font(max(14, int(24 * self.scale))).render(name, True, (230, 230, 230))
        screen.blit(label, label.get_rect(center=(x, y)))
