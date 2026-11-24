import math

TWO_PI = 2.0 * math.pi
SQRT3 = math.sqrt(3.0)


class ACDrive:
    """Frequenzumrichter (Spannungszwischenkreis-Umrichter).

    Signalfluss:
        3~ Netz -> B6-Diodengleichrichter -> DC-Zwischenkreis (Kondensator C)
        -> 2-Level-PWM-Wechselrichter -> Motor

    Modelliert werden:
    - Netz: 3 Sinusspannungen (Strangspannung, Spitzenwert grid_amp)
    - Gleichrichter: ideale Dioden. Ausgangsspannung = max - min der
      Strangspannungen (= Huellkurve der Aussenleiterspannungen). Der
      Ladestrom fliesst nur, wenn diese ueber U_DC liegt.
    - Vorladung: beim Einschalten laedt ein Vorladewiderstand den
      Kondensator langsam auf (sonst riesiger Einschaltstrom). Erst danach
      ist der Umrichter "bereit".
    - Wechselrichter: Sinus-Dreieck-PWM mit Nullsystem-Einspeisung
      (entspricht der Raumzeigermodulation, max. Strangspannung U_DC/sqrt(3)).
    - Brems-Chopper: wenn der Motor generatorisch Energie zurueckspeist,
      steigt U_DC. Ueber 750 V wird ein Bremswiderstand zugeschaltet.
    """

    def __init__(self, grid_amp=325.0, grid_freq=50.0, C=1.0e-3,
                 R_line=0.5, R_precharge=47.0, pwm_freq=2000.0,
                 V_chop_on=750.0, V_chop_off=720.0, R_chop=40.0):
        # Netz (230 V eff Strangspannung -> 325 V Spitze, 400 V verkettet)
        self.grid_amp = grid_amp
        self.grid_freq = grid_freq

        # Zwischenkreis
        self.C = C
        self.R_line = R_line            # Netz- und Diodenwiderstand
        self.R_precharge = R_precharge  # Vorladewiderstand

        # Wechselrichter
        self.pwm_freq = pwm_freq

        # Brems-Chopper
        self.V_chop_on = V_chop_on
        self.V_chop_off = V_chop_off
        self.R_chop = R_chop

        self.reset()

    def reset(self):
        self.Vdc = 0.0
        self.precharged = False
        self.chopper_on = False
        self.phase = 0.0
        self.modulation = 0.0

        self.vA_grid = self.vB_grid = self.vC_grid = 0.0
        self.iA_grid = 0.0
        self.Vrect = 0.0
        self.I_rect = 0.0
        self.I_inv = 0.0
        self.I_chop = 0.0
        self.sA = self.sB = self.sC = 0
        self.vA = self.vB = self.vC = 0.0

    @property
    def ready(self):
        return self.precharged

    # ------------------------------------------------------------
    # Netz und Gleichrichter
    # ------------------------------------------------------------
    def grid_voltages(self, t):
        wt = TWO_PI * self.grid_freq * t
        vA = self.grid_amp * math.sin(wt)
        vB = self.grid_amp * math.sin(wt - TWO_PI / 3.0)
        vC = self.grid_amp * math.sin(wt + TWO_PI / 3.0)
        return vA, vB, vC

    @staticmethod
    def rectifier_voltage(vA, vB, vC):
        return max(vA, vB, vC) - min(vA, vB, vC)

    # ------------------------------------------------------------
    # PWM
    # ------------------------------------------------------------
    def carrier(self, t):
        """Symmetrisches Dreieck zwischen -1 und +1 mit pwm_freq."""
        x = (t * self.pwm_freq) % 1.0
        return 4.0 * abs(x - 0.5) - 1.0

    # ------------------------------------------------------------
    # Ein Simulationsschritt
    # ------------------------------------------------------------
    def update(self, t, dt, freq, V_amp, iA, iB, iC, enable=True):
        """freq  : Ausgangsfrequenz in Hz (Vorzeichen = Drehrichtung)
        V_amp : gewuenschte Strangspannung (Spitzenwert) in V
        iA..iC: Motorstroeme (aus dem letzten Schritt)
        Gibt die Strangspannungen am Motor (gegen Sternpunkt) zurueck."""

        # --- Netz + Gleichrichter ---
        vA_g, vB_g, vC_g = self.grid_voltages(t)
        self.vA_grid, self.vB_grid, self.vC_grid = vA_g, vB_g, vC_g
        Vrect = self.rectifier_voltage(vA_g, vB_g, vC_g)
        self.Vrect = Vrect

        R = self.R_line if self.precharged else self.R_precharge
        I_rect = (Vrect - self.Vdc) / R if Vrect > self.Vdc else 0.0
        self.I_rect = I_rect

        # Netzstrom Phase A: die Phase mit der hoechsten Spannung fuehrt
        # +I_rect, die mit der tiefsten -I_rect, die dritte keinen Strom.
        if vA_g >= vB_g and vA_g >= vC_g:
            self.iA_grid = I_rect
        elif vA_g <= vB_g and vA_g <= vC_g:
            self.iA_grid = -I_rect
        else:
            self.iA_grid = 0.0

        if not self.precharged and self.Vdc > 0.9 * SQRT3 * self.grid_amp:
            self.precharged = True

        # --- Wechselrichter ---
        self.phase = (self.phase + TWO_PI * freq * dt) % TWO_PI
        Vdc = self.Vdc

        if enable and self.precharged and Vdc > 1.0:
            half = 0.5 * Vdc
            m = V_amp / half
            self.modulation = m
            ph = self.phase
            uA = m * math.sin(ph)
            uB = m * math.sin(ph - TWO_PI / 3.0)
            uC = m * math.sin(ph + TWO_PI / 3.0)
            # Nullsystem-Einspeisung (wie Raumzeigermodulation)
            u0 = -0.5 * (max(uA, uB, uC) + min(uA, uB, uC))
            uA = min(1.0, max(-1.0, uA + u0))
            uB = min(1.0, max(-1.0, uB + u0))
            uC = min(1.0, max(-1.0, uC + u0))

            c = self.carrier(t)
            sA = 1 if uA > c else 0
            sB = 1 if uB > c else 0
            sC = 1 if uC > c else 0
        else:
            # Pulssperre: alle unteren Schalter -> Nullspannungszeiger
            self.modulation = 0.0
            sA = sB = sC = 0

        self.sA, self.sB, self.sC = sA, sB, sC

        # Brueckenzweig-Spannungen gegen DC-Mitte, dann gegen Motorsternpunkt
        vAo = (sA - 0.5) * Vdc
        vBo = (sB - 0.5) * Vdc
        vCo = (sC - 0.5) * Vdc
        vN = (vAo + vBo + vCo) / 3.0
        vA = vAo - vN
        vB = vBo - vN
        vC = vCo - vN
        self.vA, self.vB, self.vC = vA, vB, vC

        # DC-Strom in den Wechselrichter (exakt fuer die Schalterstellung)
        I_inv = sA * iA + sB * iB + sC * iC
        self.I_inv = I_inv

        # --- Brems-Chopper (Hysterese) ---
        if self.Vdc > self.V_chop_on:
            self.chopper_on = True
        elif self.Vdc < self.V_chop_off:
            self.chopper_on = False
        I_chop = self.Vdc / self.R_chop if self.chopper_on else 0.0
        self.I_chop = I_chop

        # --- Zwischenkreis: C dU/dt = I_rect - I_inv - I_chop ---
        self.Vdc += (I_rect - I_inv - I_chop) / self.C * dt
        if self.Vdc < 0.0:
            self.Vdc = 0.0

        return vA, vB, vC
