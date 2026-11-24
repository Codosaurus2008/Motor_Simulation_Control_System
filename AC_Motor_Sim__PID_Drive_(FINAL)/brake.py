import math


class BrakeSystem:
    """Mechanische Bremse an der Motorwelle.

    mode:
    - "hard"    : Reibungsbremse (Coulomb-Reibung) mit maximalem Moment
                  hard_torque. Mit Haftreibung: Steht die Welle, haelt die
                  Bremse sie fest, solange das antreibende Moment kleiner
                  als hard_torque ist. Die Bremse kann die Drehrichtung nie
                  umkehren (kein Schwingen um null).
    - "viscous" : geschwindigkeitsproportionale Bremse (Wirbelstrombremse),
                  M = viscous_gain * omega.
    """

    def __init__(self, mode="hard", hard_torque=50.0, viscous_gain=1.0):
        self.active = False
        self.mode = mode
        self.hard_torque = hard_torque
        self.viscous_gain = viscous_gain

    def compute(self, omega, drive_torque, J, dt):
        """Gibt das Bremsmoment zurueck (positiv = bremst positive Drehung).

        omega        : aktuelle Winkelgeschwindigkeit [rad/s]
        drive_torque : Summe aller anderen Momente auf die Welle [Nm]
        J, dt        : Traegheit und Zeitschritt (fuer das Haftmodell)
        """
        if not self.active:
            return 0.0

        if self.mode == "viscous":
            return self.viscous_gain * omega

        # Moment, das die Welle in diesem Schritt genau zum Stillstand bringt
        torque_to_stop = drive_torque + J * omega / dt
        if abs(torque_to_stop) <= self.hard_torque:
            return torque_to_stop          # Welle steht / bleibt stehen
        return math.copysign(self.hard_torque, torque_to_stop)
