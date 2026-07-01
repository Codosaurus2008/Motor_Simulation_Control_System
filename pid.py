class PID:
    def __init__(self, Kp, Ki, Kd, limit_min=None, limit_max=None):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd

        self.integral = 0
        self.prev_error = 0

        self.limit_min = limit_min
        self.limit_max = limit_max

    def update(self, error, dt):
        # integral
        self.integral += error * dt

        # derivative
        derivative = (error - self.prev_error) / dt
        self.prev_error = error

        # raw output
        output = (
            self.Kp * error +
            self.Ki * self.integral +
            self.Kd * derivative
        )

        # clamp + anti-windup
        if self.limit_min is not None and output < self.limit_min:
            output = self.limit_min
            self.integral -= error * dt   # anti-windup

        if self.limit_max is not None and output > self.limit_max:
            output = self.limit_max
            self.integral -= error * dt

        return output