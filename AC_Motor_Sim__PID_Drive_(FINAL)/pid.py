class PID:
    """PID-Regler fuer die Kaskadenregelung.

    Eigenschaften:
    - D-Anteil wirkt auf den Messwert (nicht auf den Fehler) -> kein
      "Derivative Kick" bei Sollwertspruengen.
    - D-Anteil ist tiefpassgefiltert (Zeitkonstante d_tau), damit
      Messrauschen nicht verstaerkt wird.
    - Integrator mit Clamping-Anti-Windup: Er wird nur weitergefuehrt,
      wenn das die Saettigung nicht noch vertieft.
    - Der Integrator speichert Ki*sum(e*dt). Dadurch springt der Ausgang
      nicht, wenn Ki im Betrieb (Slider) veraendert wird.
    - Optionale Vorsteuerung (feedforward) wird vor der Begrenzung addiert.
    """

    def __init__(self, Kp, Ki, Kd, limit_min=None, limit_max=None, d_tau=0.005):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.limit_min = limit_min
        self.limit_max = limit_max
        self.d_tau = d_tau
        self.reset()

    def reset(self):
        self.integral = 0.0
        self.prev_measurement = None
        self.d_state = 0.0
        self.output = 0.0

    def _clamp(self, value):
        if self.limit_max is not None and value > self.limit_max:
            return self.limit_max
        if self.limit_min is not None and value < self.limit_min:
            return self.limit_min
        return value

    def update(self, setpoint, measurement, dt, feedforward=0.0):
        error = setpoint - measurement

        # P-Anteil
        p_term = self.Kp * error

        # D-Anteil auf Messwert, gefiltert
        if self.prev_measurement is None or dt <= 0:
            d_raw = 0.0
        else:
            d_raw = -(measurement - self.prev_measurement) / dt
        self.prev_measurement = measurement
        if dt > 0:
            alpha = dt / (self.d_tau + dt)
            self.d_state += alpha * (d_raw - self.d_state)
        d_term = self.Kd * self.d_state

        # I-Anteil mit Anti-Windup (Clamping)
        integral_new = self.integral + self.Ki * error * dt
        u_unsat = feedforward + p_term + integral_new + d_term
        u_sat = self._clamp(u_unsat)
        if (u_sat == u_unsat
                or (u_unsat > u_sat and error < 0)
                or (u_unsat < u_sat and error > 0)):
            self.integral = self._clamp(integral_new)

        self.output = self._clamp(feedforward + p_term + self.integral + d_term)
        return self.output
