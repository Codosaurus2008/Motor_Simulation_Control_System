import pygame

class Slider:
    def __init__(self, x, y, width, min_val, max_val, start_val, label, scale=1.0):
        self.x = x
        self.y = y
        self.width = width

        self.min = min_val
        self.max = max_val
        self.value = start_val

        self.label = label
        self.dragging = False
        self.scale = scale
        self.line_width = max(2, int(4 * scale))
        self.knob_radius = max(6, int(13 * scale))
        self.font_size = max(16, int(28 * scale))
        self.label_offset = max(20, int(30 * scale))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.is_hover(event.pos):
                self.dragging = True

        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging = False

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging:
                mx = event.pos[0]
                ratio = (mx - self.x) / self.width
                ratio = max(0, min(1, ratio))
                self.value = self.min + ratio * (self.max - self.min)

    def is_hover(self, pos):
        x, y = pos
        return self.x <= x <= self.x + self.width and self.y - self.knob_radius <= y <= self.y + self.knob_radius

    def draw(self, surface):
        # line
        pygame.draw.line(surface, (250,250,250),
                         (self.x, self.y),
                         (self.x + self.width, self.y), self.line_width)

        # handle
        ratio = (self.value - self.min) / (self.max - self.min)
        hx = int(self.x + ratio * self.width)
        pygame.draw.circle(surface, (255,100,100), (hx, self.y), self.knob_radius)

        # label
        font = pygame.font.SysFont(None, self.font_size)
        text = f"{self.label}: {self.value:.2f}"
        surface.blit(font.render(text, True, (255,255,255)),
                     (self.x, self.y - self.label_offset))
