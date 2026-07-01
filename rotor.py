import pygame
import numpy as np

class Rotor:
    def __init__(self, center, radius, scale=1.0):
        self.center = np.array(center, dtype=float)
        self.radius = radius
        self.scale = scale

        self.theta = 0.0
        self.omega = 0.0

        self.J = 10
        self.torque = 0.0

    def update(self,dt):
        self.omega += (self.torque / self.J) * dt
        self.theta += self.omega * dt
        self.theta = self.theta % (2 * np.pi)

    def draw(self, screen):
        cx, cy = int(self.center[0]), int(self.center[1])

        # rotor core
        pygame.draw.circle(screen, (120, 120, 120), (cx, cy), self.radius)

        self.draw_axis(screen)
        self.draw_poles(screen)

    def draw_axis(self, screen):
        cx, cy = self.center

        length = self.radius*0.8
        x = cx + length * np.cos(self.theta)
        y = cy - length * np.sin(self.theta)   

        pygame.draw.line(
            screen,
            (255,255,0),
            (int(cx- length * np.cos(self.theta)), int(cy +length * np.sin(self.theta))),
            (int(x), int(y)),
            max(2, int(3 * self.scale))
        )

    def draw_poles(self, screen):
        cx, cy = self.center
        r = self.radius*0.8

        # North
        xN = cx + r * np.cos(self.theta)
        yN = cy - r * np.sin(self.theta)

        # South
        xS = cx - r * np.cos(self.theta)
        yS = cy + r * np.sin(self.theta)

        pole_radius = max(6, int(13 * self.scale))
        pygame.draw.circle(screen, (255,0,0), (int(xN), int(yN)), pole_radius)
        pygame.draw.circle(screen, (0,0,255), (int(xS), int(yS)), pole_radius)


