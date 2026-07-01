import pygame

class Coil:
    def __init__(self, position, phase, scale=1.0):
        self.position = position
        self.phase = phase
        self.current = 0
        self.amplitude = 0
        self.scale = scale


    def draw(self, screen):
        x, y = int(self.position[0]), int(self.position[1])
        intensity = min(1.0, abs(self.current) / (self.amplitude + 1e-6))

        if self.current >=0:
            color= (int(255*intensity), 0, 0)   #current out: north

        else:
            color = (0, 0, int(255*intensity))  #current in: south

        radius = max(6, int(12 * self.scale))
        pygame.draw.circle(screen, color, (x,y), radius)
