import math


class Rotor:
    """Mechanik der Motorwelle (Motor + angekoppelte Last).

    J * d omega/dt = M_motor - M_last - B*omega - M_bremse
    """

    def __init__(self, J=0.05, B=0.002):
        self.J = J            # Traegheitsmoment [kg m^2]
        self.B = B            # viskose Lagerreibung [Nm s/rad]
        self.reset()

    def reset(self):
        self.theta = 0.0      # mechanischer Winkel [rad]
        self.omega = 0.0      # Winkelgeschwindigkeit [rad/s]
        self.torque = 0.0     # resultierendes Moment [Nm]
        self.brake_torque = 0.0

    def update(self, motor_torque, load_torque, brake, dt):
        drive = motor_torque - load_torque - self.B * self.omega
        brake_torque = brake.compute(self.omega, drive, self.J, dt) if brake else 0.0
        self.brake_torque = brake_torque
        self.torque = drive - brake_torque
        self.omega += self.torque / self.J * dt
        self.theta = (self.theta + self.omega * dt) % (2.0 * math.pi)

    # ------------------------------------------------------------
    # Darstellung
    # ------------------------------------------------------------
    def draw(self, screen, center, radius, flux_angle, flux_level, scale=1.0):
        """Rotor mit Rotorfluss (N/S) im elektrischen Winkel und einer
        Markierung fuer den mechanischen Wellenwinkel."""
        import pygame

        cx, cy = int(center[0]), int(center[1])
        pygame.draw.circle(screen, (110, 110, 110), (cx, cy), radius)

        # Rotorfluss: Nordpol in Flussrichtung
        r = radius * 0.72
        level = max(0.15, min(1.0, flux_level))
        c, s = math.cos(flux_angle), math.sin(flux_angle)
        xN, yN = cx + r * c, cy - r * s
        xS, yS = cx - r * c, cy + r * s
        pygame.draw.line(screen, (230, 210, 60), (xS, yS), (xN, yN),
                         max(2, int(4 * scale)))
        pole_r = max(5, int(14 * scale))
        pygame.draw.circle(screen, (int(255 * level), 40, 40), (int(xN), int(yN)), pole_r)
        pygame.draw.circle(screen, (40, 40, int(255 * level)), (int(xS), int(yS)), pole_r)

        # Welle: mechanischer Winkel (weisser Punkt am Rotorrand)
        rm = radius * 0.92
        xm = cx + rm * math.cos(self.theta)
        ym = cy - rm * math.sin(self.theta)
        pygame.draw.circle(screen, (255, 255, 255), (int(xm), int(ym)), max(3, int(6 * scale)))
        pygame.draw.circle(screen, (30, 30, 30), (cx, cy), max(3, int(8 * scale)))
