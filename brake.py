import numpy as np

class BrakeSystem:
    def __init__(self, mode="viscous"):
        """
        mode:
        - "viscous" → proportional to speed (realistic electrical braking)
        - "hard" → strong constant braking (mechanical brake)
        """
        self.active = False
        self.mode = mode

        # tuning parameters
        self.viscous_gain = 5
        self.hard_torque = 20

        # stop threshold
        self.stop_threshold = 0.1

    def compute(self, omega):
        """
        Returns braking torque based on current speed
        """
        if not self.active:
            return 0.0

        if self.mode == "viscous":
            # Smooth braking (T ∝ ω)
            return self.viscous_gain * omega

        elif self.mode == "hard":
            # Strong constant braking
            return self.hard_torque * np.sign(omega)

        return 0.0

    def enforce_stop(self, rotor):
        """
        Prevents oscillation around zero speed
        """
        if self.active and abs(rotor.omega) < self.stop_threshold:
            rotor.omega = 0
