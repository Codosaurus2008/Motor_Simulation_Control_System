import numpy as np
import pygame

class PhaseSource:
    def __init__(
        self,
        center,
        y_offset=0,
        R=1.0,
        L=2,
        amplitude=5.0,
        frequency=1.0,
        phase_shift=0.0,
        scale=1.0
    ):
        # position for drawing
        self.center = (center[0], center[1] + y_offset)

        # electrical parameters
        self.R = R
        self.L = L
        self.amplitude = amplitude
        self.frequency = frequency
        self.phase_shift = phase_shift
        self.phase=self.phase_shift
        self.scale = scale
        self.line_width = max(2, int(12 * scale))
        self.circle_radius = max(4, int(6 * scale))

        # dynamic variables
        self.current = 0.0
        self.charge = 0.0

    # -------------------------
    # voltage input
    # -------------------------
    def voltage(self):
        return self.amplitude * np.sin(self.phase)



    # -------------------------
    # update system
    # -------------------------
    def update(self, dt):
        # integrate phase
        self.phase += 2 * np.pi * self.frequency * dt

        # compute voltage from phase
        V = self.amplitude * np.sin(self.phase)

        L_safe = max(self.L, 1e-6)
        dI_dt = (V - self.R * self.current) / L_safe

        self.current += dI_dt * dt
        self.charge += self.current * dt

        return self.current

    # -------------------------
    # draw cable
    # -------------------------
    def draw(self, screen):
        cx, cy = self.center

        start = (int(cx), int(cy))
        end = (screen.get_width(), int(cy))

        # color based on current
        intensity =0*  min(1.0, abs(self.current) / self.amplitude)

        if self.current >= 0:
            color = (int(255 * intensity), 0,0)
        else:
            color = (0,0, int(255 * intensity))

        pygame.draw.line(screen, (30, 30, 30), start, end, self.line_width)
        pygame.draw.line(screen, color, start, end, max(2, int(8 * self.scale)))
        pygame.draw.circle(screen, (200, 200, 200), end, self.circle_radius)