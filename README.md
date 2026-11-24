# AC Drive: Frequency Converter + Induction Motor with PID Control

Simulation of a frequency converter drive (ABB internship).

Run: `python main.py` (requires `pygame` and `numpy`).

## Controls

| Input | Effect |
|---|---|
| Start / Stop / Space | Run / pause the simulation |
| Reset / R | Reset everything |
| Settings / S | Settings (time windows, ramp, J, V/f, PWM frequency, sim speed) |
| B (hold) | Mechanical brake |
| Sliders | Load, speed setpoint, measurement noise, Kp / Ki / Kd |
| Esc | Quit |

For large screens, set `SCALE = 1.0` in `main.py`. While the motor is
running, the rotor animation strobes. In that case, set the sim speed in
the settings to e.g. 0.05 (slow motion).

## Files

| File | Contents |
|---|---|
| `main.py` | Window, controls, drawing |
| `simulation.py` | Complete system and control (runs without pygame) |
| `ac_drive.py` | Grid, diode rectifier, precharge, DC link, PWM inverter, brake chopper |
| `motor.py` | Induction machine (dynamic model in the alpha/beta frame) |
| `rotor.py` | Shaft mechanics + rotor drawing |
| `brake.py` | Friction brake with stiction model |
| `pid.py` | PID controller (anti-windup, filtered D term on the measurement) |
| `pygmonitor.py` | Graphs and scope |
| `slider.py`, `coil.py`, `fonts.py` | Controls / drawing |

## Physics

**Converter:** 400 V grid → B6 diode rectifier → DC link
(C = 1 mF, approx. 563 V) → 2-level inverter with sine-triangle PWM
(2 kHz) and zero-sequence injection (like space vector modulation). At
switch-on, a precharge resistor charges the capacitor. If the motor feeds
energy back while braking, a brake resistor is switched in above 750 V.

**Motor:** 4 kW induction motor, 4-pole (p = 2). States: stator current
and rotor flux. Check on a stiff 50 Hz grid: 1436 rpm at rated torque
26.7 Nm, 7.6 A, 4.4 kW, as with a real 4 kW motor.

**Control (every 0.5 ms), cascade:**
Setpoint → ramp → speed PID → torque setpoint (max. 40 Nm)
→ torque PI with feedforward → slip frequency (max. 30 rad/s)
→ stator frequency = p·ω + ω_slip → V/f characteristic (6.5 V/Hz + boost) → PWM.

**Time step:** 20 µs for electrics and mechanics.
