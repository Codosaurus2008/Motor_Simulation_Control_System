"""Gesamtsystem: Umrichter + Asynchronmotor + Mechanik + Regelung.

Bewusst ohne pygame, damit die Physik auch ohne Grafik getestet werden kann.

Zeitebenen
----------
dt_fast  (20 us) : Netz, Gleichrichter, PWM, Motorgleichungen, Mechanik
dt_ctrl (0.5 ms) : Regelung (Drehzahl -> Moment -> Schlupf -> U/f)

Regelstruktur (skalare Regelung mit Schlupfvorgabe, Kaskade)
-----------------------------------------------------------
Drehzahlsollwert -> Rampe -> Drehzahl-PID -> Momentsollwert
-> Moment-PI (+ Vorsteuerung) -> Schlupffrequenz
-> Statorfrequenz = p*omega + omega_slip -> U/f-Kennlinie -> PWM
"""

import math
import random

from ac_drive import ACDrive
from motor import InductionMotor
from rotor import Rotor
from brake import BrakeSystem
from pid import PID

TWO_PI = 2.0 * math.pi

DEFAULT_PARAMS = {
    "omega_target": 100.0,   # Drehzahlsollwert [rad/s]  (100 rad/s = 955 U/min)
    "ramp": 150.0,           # Hochlauframpe [rad/s^2]
    "J": 0.05,               # Traegheit Motor + Last [kg m^2]
    "K_vf": 6.5,             # U/f-Verhaeltnis [V/Hz] (Spitzenwert): 325 V / 50 Hz
    "V_boost": 8.0,          # Spannungsanhebung bei kleiner Frequenz [V]
    "pwm_freq": 2000.0,      # Taktfrequenz des Wechselrichters [Hz]
    "time_scale": 1.0,       # Simulationszeit pro Echtzeit (1 = Echtzeit)
    "time_window_main": 10.0,
    "time_window_drive": 0.06,
}

DEFAULT_INPUTS = {
    "noise": 0.5,            # Messrauschen Drehzahlgeber [rad/s]
    "load_base": 5.0,        # Grundlastmoment [Nm]
    "load_dist": 3.0,        # Amplitude der Laststoerung [Nm]
    "dist_freq": 0.3,        # Frequenz der Laststoerung [Hz]
    "Kp": 1.0,               # Drehzahlregler [Nm/(rad/s)]
    "Ki": 8.0,               # [Nm/rad]
    "Kd": 0.0,               # [Nm s^2/rad]
}


class DriveSimulation:
    dt_fast = 20e-6
    ctrl_div = 25                 # Regler alle 25 schnellen Schritte (0.5 ms)
    drive_log_div = 2             # Scope-Daten alle 40 us
    main_log_div = 10             # Hauptgrafen alle 5 ms

    T_max = 40.0                  # Momentgrenze (ca. 1.5 x Nennmoment) [Nm]
    slip_max = 30.0               # max. Schlupfkreisfrequenz (elektr.) [rad/s]
    K_T = 1.8                     # Momentkonstante im linearen Bereich [Nm/(rad/s)]

    def __init__(self, params=None, inputs=None, seed=None):
        self.params = dict(DEFAULT_PARAMS)
        if params:
            self.params.update(params)
        self.inputs = dict(DEFAULT_INPUTS)
        if inputs:
            self.inputs.update(inputs)

        self.rng = random.Random(seed)

        self.drive = ACDrive(pwm_freq=self.params["pwm_freq"])
        self.motor = InductionMotor()
        self.rotor = Rotor(J=self.params["J"])
        self.brake = BrakeSystem()

        self.pid_speed = PID(self.inputs["Kp"], self.inputs["Ki"], self.inputs["Kd"],
                             limit_min=-self.T_max, limit_max=self.T_max, d_tau=0.01)
        self.pid_torque = PID(0.3, 40.0, 0.0,
                              limit_min=-self.slip_max, limit_max=self.slip_max)

        self.monitor = None          # optional: Hauptgrafen
        self.drive_monitor = None    # optional: Scope
        self.reset()

    # ------------------------------------------------------------
    def reset(self):
        self.t = 0.0
        self.step_count = 0
        self.ctrl_count = 0

        self.drive.reset()
        self.motor.reset()
        self.rotor.reset()
        self.pid_speed.reset()
        self.pid_torque.reset()

        self.omega_ref = 0.0
        self.omega_meas = 0.0
        self.omega_filt = 0.0
        self.torque_ref = 0.0
        self.torque_filt = 0.0
        self.omega_slip = 0.0
        self.freq = 0.0
        self.V_amp = 0.0
        self.load_torque = 0.0
        self.power_filt = 0.0

        # gefilterte Groessen fuer die Anzeige
        self.vA_filt = 0.0
        self.iA_filt = 0.0

    # ------------------------------------------------------------
    def apply_params(self):
        """Nach Aenderung in den Einstellungen aufrufen."""
        self.rotor.J = self.params["J"]
        self.drive.pwm_freq = self.params["pwm_freq"]

    # ------------------------------------------------------------
    def compute_load(self, t, omega):
        """Passive Last (wirkt immer gegen die Drehung, z.B. Reibung/Luefter).
        Grundlast + Sinusstoerung + Laststoss (1 s lang, alle 5 s)."""
        inp = self.inputs
        step = 1.0 if (t % 5.0) >= 4.0 else 0.0
        magnitude = (inp["load_base"]
                     + inp["load_dist"] * (step + math.sin(TWO_PI * inp["dist_freq"] * t)))
        magnitude = max(0.0, magnitude)
        # tanh: glatter Uebergang im Stillstand (Last kann nicht antreiben)
        return magnitude * math.tanh(omega / 0.5)

    # ------------------------------------------------------------
    def control_step(self, dt):
        p = self.params
        inp = self.inputs
        motor = self.motor

        # Reglerparameter live aus den Slidern
        self.pid_speed.Kp = inp["Kp"]
        self.pid_speed.Ki = inp["Ki"]
        self.pid_speed.Kd = inp["Kd"]

        # Messung: Drehzahlgeber mit Rauschen, Tiefpass 5 ms
        self.omega_meas = self.rotor.omega + self.rng.gauss(0.0, inp["noise"])
        a_w = dt / (0.005 + dt)
        self.omega_filt += a_w * (self.omega_meas - self.omega_filt)

        # Moment-Istwert (im realen Umrichter: Schaetzung aus Strom und Spannung),
        # gefiltert gegen den PWM-Rippel
        a_T = dt / (0.002 + dt)
        self.torque_filt += a_T * (motor.torque - self.torque_filt)

        if not self.drive.ready:
            # Vorladung laeuft: Wechselrichter gesperrt, Regler zuruecksetzen
            self.pid_speed.reset()
            self.pid_torque.reset()
            self.omega_ref = self.omega_filt
            self.torque_ref = 0.0
            self.omega_slip = 0.0
            self.freq = 0.0
            self.V_amp = 0.0
            return

        # Sollwert-Rampe
        step = p["ramp"] * dt
        diff = p["omega_target"] - self.omega_ref
        self.omega_ref += max(-step, min(step, diff))

        # Drehzahlregler -> Momentsollwert
        self.torque_ref = self.pid_speed.update(self.omega_ref, self.omega_filt, dt)

        # Momentregler -> Schlupffrequenz (mit Vorsteuerung M/K_T)
        self.omega_slip = self.pid_torque.update(
            self.torque_ref, self.torque_filt, dt,
            feedforward=self.torque_ref / self.K_T)

        # Statorfrequenz
        omega_s = motor.p * self.omega_filt + self.omega_slip
        self.freq = omega_s / TWO_PI

        # U/f-Kennlinie (Spitzenwert der Strangspannung)
        self.V_amp = p["V_boost"] + p["K_vf"] * abs(self.freq)

    # ------------------------------------------------------------
    def fast_step(self):
        dt = self.dt_fast

        if self.ctrl_count == 0:
            self.control_step(dt * self.ctrl_div)
        self.ctrl_count = (self.ctrl_count + 1) % self.ctrl_div

        motor = self.motor
        iA, iB, iC = motor.phase_currents
        vA, vB, vC = self.drive.update(self.t, dt, self.freq, self.V_amp, iA, iB, iC)
        T_motor = motor.update(vA, vB, vC, self.rotor.omega, dt)

        self.load_torque = self.compute_load(self.t, self.rotor.omega)
        self.rotor.update(T_motor, self.load_torque, self.brake, dt)

        # Anzeige-Filter (Grundschwingung sichtbar machen)
        self.vA_filt += (dt / (0.0008 + dt)) * (vA - self.vA_filt)
        self.iA_filt += (dt / (0.0002 + dt)) * (motor.phase_currents[0] - self.iA_filt)
        self.power_filt += (dt / (0.02 + dt)) * (motor.electrical_power - self.power_filt)

        self.t += dt
        self.step_count += 1

        if self.drive_monitor is not None and self.step_count % self.drive_log_div == 0:
            d = self.drive
            self.drive_monitor.log(self.t, d.vA_grid, d.iA_grid, d.Vrect, d.I_rect,
                                   d.Vdc, d.I_inv, vA, motor.phase_currents[0])

        if self.monitor is not None and self.step_count % (self.ctrl_div * self.main_log_div) == 0:
            self.monitor.log(self.t, self.rotor.omega, self.omega_ref,
                             self.torque_filt, self.load_torque,
                             self.iA_filt, self.vA_filt)

    # ------------------------------------------------------------
    def advance(self, sim_time):
        n = int(round(sim_time / self.dt_fast))
        for _ in range(n):
            self.fast_step()

    # ------------------------------------------------------------
    @property
    def slip(self):
        """Schlupf s = (n_s - n)/n_s."""
        omega_s = TWO_PI * self.freq
        if abs(omega_s) < 1e-3:
            return 0.0
        return (omega_s - self.motor.p * self.rotor.omega) / omega_s

    @property
    def status(self):
        if not self.drive.ready:
            return "Precharging"
        if self.brake.active:
            return "Brake active"
        if self.drive.chopper_on:
            return "Brake chopper"
        if abs(self.pid_speed.output) >= self.T_max - 1e-9:
            return "Torque limit"
        return "Running"
