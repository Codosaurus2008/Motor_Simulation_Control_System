import math

SQRT3 = math.sqrt(3.0)


class InductionMotor:
    """Dynamisches Modell einer Asynchronmaschine (Kaefiglaeufer).

    Zustandsgroessen im staenderfesten alpha/beta-Koordinatensystem
    (amplitudeninvariante Clarke-Transformation):
        Staenderstrom  i_s  = (i_a, i_b)
        Rotorfluss     psi_r = (psi_a, psi_b)

    Gleichungen (omega_e = p * omega_mech):
        d psi_r/dt = (Lm*i_s - psi_r)/Tr + omega_e * J*psi_r
        d i_s/dt   = (u_s - Rs*i_s - (Lm/Lr) * d psi_r/dt) / (sigma*Ls)
        M          = 3/2 * p * (Lm/Lr) * (psi_a*i_b - psi_b*i_a)
    mit J*psi = (-psi_b, psi_a), Tr = Lr/Rr, sigma = 1 - Lm^2/(Ls*Lr).

    Standardwerte: 4-kW-Motor, 400 V, 50 Hz, 4-polig (p = 2),
    Nenndrehzahl ca. 1430 U/min, Nennmoment ca. 26.7 Nm.
    """

    def __init__(self, Rs=1.405, Rr=1.395, Lls=0.005839, Llr=0.005839,
                 Lm=0.1722, p=2):
        self.Rs = Rs
        self.Rr = Rr
        self.Lls = Lls
        self.Llr = Llr
        self.Lm = Lm
        self.p = p
        self._update_constants()
        self.reset()

    def _update_constants(self):
        self.Ls = self.Lls + self.Lm
        self.Lr = self.Llr + self.Lm
        self.sigma = 1.0 - self.Lm ** 2 / (self.Ls * self.Lr)
        self.Tr = self.Lr / self.Rr
        self.kr = self.Lm / self.Lr
        self.sigma_Ls = self.sigma * self.Ls

    def reset(self):
        self.i_a = 0.0
        self.i_b = 0.0
        self.psi_a = 0.0
        self.psi_b = 0.0
        self.v_a = 0.0
        self.v_b = 0.0
        self.torque = 0.0

    # ------------------------------------------------------------
    @staticmethod
    def clarke(xA, xB, xC):
        a = (2.0 / 3.0) * (xA - 0.5 * xB - 0.5 * xC)
        b = (xB - xC) / SQRT3
        return a, b

    @property
    def phase_currents(self):
        iA = self.i_a
        iB = -0.5 * self.i_a + 0.5 * SQRT3 * self.i_b
        iC = -0.5 * self.i_a - 0.5 * SQRT3 * self.i_b
        return iA, iB, iC

    @property
    def current_amplitude(self):
        return math.hypot(self.i_a, self.i_b)

    @property
    def flux_amplitude(self):
        return math.hypot(self.psi_a, self.psi_b)

    @property
    def flux_angle(self):
        return math.atan2(self.psi_b, self.psi_a)

    @property
    def current_angle(self):
        return math.atan2(self.i_b, self.i_a)

    @property
    def electrical_power(self):
        # P = 3/2 * (u_a*i_a + u_b*i_b) bei amplitudeninvarianter Transformation
        return 1.5 * (self.v_a * self.i_a + self.v_b * self.i_b)

    # ------------------------------------------------------------
    def update(self, vA, vB, vC, omega_mech, dt):
        v_a, v_b = self.clarke(vA, vB, vC)
        self.v_a, self.v_b = v_a, v_b

        we = self.p * omega_mech
        i_a, i_b = self.i_a, self.i_b
        psi_a, psi_b = self.psi_a, self.psi_b

        dpsi_a = (self.Lm * i_a - psi_a) / self.Tr - we * psi_b
        dpsi_b = (self.Lm * i_b - psi_b) / self.Tr + we * psi_a

        di_a = (v_a - self.Rs * i_a - self.kr * dpsi_a) / self.sigma_Ls
        di_b = (v_b - self.Rs * i_b - self.kr * dpsi_b) / self.sigma_Ls

        self.i_a = i_a + di_a * dt
        self.i_b = i_b + di_b * dt
        self.psi_a = psi_a + dpsi_a * dt
        self.psi_b = psi_b + dpsi_b * dt

        self.torque = 1.5 * self.p * self.kr * (
            self.psi_a * self.i_b - self.psi_b * self.i_a)
        return self.torque
