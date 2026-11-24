"""AC-Antrieb: Frequenzumrichter + Asynchronmotor mit Kaskadenregelung.

Bedienung
---------
Maus     : Slider ziehen, Buttons Start / Stop / Reset / Einstellungen
Leertaste: Start / Stop
R        : Reset
B        : mechanische Bremse (gedrueckt halten)
S        : Einstellungen ein/aus
Esc      : Beenden

Die Physik steckt in simulation.py (laeuft auch ohne pygame).
"""

import math
import sys
import time

import pygame

from coil import Coil
from fonts import get_font
from pygmonitor import Monitor, DriveMonitor
from simulation import DriveSimulation
from slider import Slider

# ------------------------------------------------------------------
# Anzeige
# ------------------------------------------------------------------
SCALE = 0.5          # 0.5 fuer Laptop, 1.0 fuer grossen Bildschirm
FPS = 30

BASE_WIDTH, BASE_HEIGHT = 2500, 1400


def scaled(value):
    return int(value * SCALE)


WIDTH, HEIGHT = scaled(BASE_WIDTH), scaled(BASE_HEIGHT)
LEFT_WIDTH = scaled(2000)
RIGHT_WIDTH = WIDTH - LEFT_WIDTH
TOP_HEIGHT = scaled(1100)
RHEIGHT = scaled(720)

main_h = int(TOP_HEIGHT * 0.7)
drive_h = TOP_HEIGHT - main_h

rect_main = pygame.Rect(0, 0, LEFT_WIDTH, main_h)
rect_drive = pygame.Rect(0, main_h, LEFT_WIDTH, drive_h)
rect_controls = pygame.Rect(0, TOP_HEIGHT, LEFT_WIDTH, HEIGHT - TOP_HEIGHT)
rect_sim = pygame.Rect(LEFT_WIDTH, 0, RIGHT_WIDTH, RHEIGHT)
rect_values = pygame.Rect(LEFT_WIDTH, RHEIGHT, RIGHT_WIDTH, HEIGHT - RHEIGHT)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption(
    "AC Drive  |  Space: Start/Stop   R: Reset   B: Brake   S: Settings   Esc: Quit")
clock = pygame.time.Clock()

graph_surface_main = pygame.Surface(rect_main.size)
graph_surface_drive = pygame.Surface(rect_drive.size)
control_surface = pygame.Surface(rect_controls.size)
sim_surface = pygame.Surface(rect_sim.size)
value_surface = pygame.Surface(rect_values.size)

# ------------------------------------------------------------------
# Simulation und Monitore
# ------------------------------------------------------------------
sim = DriveSimulation()
params = sim.params

monitor = Monitor(scale=SCALE, time_window=params["time_window_main"])
monitor_drive = DriveMonitor(scale=SCALE, time_window=params["time_window_drive"])
sim.monitor = monitor
sim.drive_monitor = monitor_drive

# ------------------------------------------------------------------
# Motorbild: 2-poliges Ersatzbild (elektrische Winkel)
# ------------------------------------------------------------------
sim_center = (RIGHT_WIDTH // 2, scaled(330))
rotor_radius = scaled(130)
stator_radius = scaled(190)
I_SCALE = 15.0   # Strom fuer volle Farbintensitaet [A]

coils = []
for phase, axis in (("A", 0.0), ("B", 2 * math.pi / 3), ("C", 4 * math.pi / 3)):
    # Wicklungsachse 'axis': Hinleiter bei axis+90 Grad, Rueckleiter bei axis-90 Grad
    for sign, angle in ((+1, axis + math.pi / 2), (-1, axis - math.pi / 2)):
        x = sim_center[0] + stator_radius * math.cos(angle)
        y = sim_center[1] - stator_radius * math.sin(angle)
        coils.append(Coil((x, y), phase, sign=sign, scale=SCALE, i_scale=I_SCALE))

# ------------------------------------------------------------------
# Slider
# ------------------------------------------------------------------
col_x = [scaled(50), scaled(700), scaled(1350)]
row_y = [scaled(100), scaled(180), scaled(260)]
slider_w = scaled(500)
inp = sim.inputs

sliders = {
    "load_base": Slider(col_x[0], row_y[0], slider_w, 0.0, 30.0, inp["load_base"],
                        "Base load", SCALE, "Nm", 1),
    "load_dist": Slider(col_x[0], row_y[1], slider_w, 0.0, 20.0, inp["load_dist"],
                        "Load disturbance", SCALE, "Nm", 1),
    "dist_freq": Slider(col_x[0], row_y[2], slider_w, 0.0, 2.0, inp["dist_freq"],
                        "Disturbance freq.", SCALE, "Hz", 2),
    "omega_target": Slider(col_x[1], row_y[0], slider_w, 0.0, 150.0, params["omega_target"],
                           "Speed setpoint", SCALE, "rad/s", 1),
    "noise": Slider(col_x[1], row_y[1], slider_w, 0.0, 5.0, inp["noise"],
                    "Measurement noise", SCALE, "rad/s", 2),
    "Kp": Slider(col_x[2], row_y[0], slider_w, 0.0, 5.0, inp["Kp"], "Kp", SCALE, "Nm s/rad", 2),
    "Ki": Slider(col_x[2], row_y[1], slider_w, 0.0, 40.0, inp["Ki"], "Ki", SCALE, "Nm/rad", 1),
    "Kd": Slider(col_x[2], row_y[2], slider_w, 0.0, 0.05, inp["Kd"], "Kd", SCALE, "Nm s2/rad", 3),
}
column_titles = ["Load", "Setpoint / Measurement", "Speed controller (PID)"]


def sync_sliders():
    for key, s in sliders.items():
        if key == "omega_target":
            params["omega_target"] = s.value
        else:
            inp[key] = s.value
    monitor.omega_target = params["omega_target"]


# ------------------------------------------------------------------
# Einstellungen
# ------------------------------------------------------------------
setting_fields = [
    {"key": "time_window_main", "label": "Graph time window [s]", "min": 1.0, "max": 15.0, "step": 1.0},
    {"key": "time_window_drive", "label": "Scope time window [s]", "min": 0.02, "max": 1.0, "step": 0.02},
    {"key": "ramp", "label": "Acceleration ramp [rad/s2]", "min": 10.0, "max": 500.0, "step": 10.0},
    {"key": "J", "label": "Inertia J [kg m2]",
     "choices": [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0]},
    {"key": "K_vf", "label": "V/f ratio [V/Hz]", "min": 3.0, "max": 10.0, "step": 0.5},
    {"key": "V_boost", "label": "Voltage boost [V]", "min": 0.0, "max": 30.0, "step": 1.0},
    {"key": "pwm_freq", "label": "PWM frequency [Hz]", "min": 500.0, "max": 4000.0, "step": 500.0},
    {"key": "time_scale", "label": "Sim speed (1 = real time)",
     "choices": [0.02, 0.05, 0.1, 0.2, 0.5, 1.0]},
]
settings_rects = {}          # key -> (minus_rect, plus_rect), Koordinaten der Werte-Flaeche
settings_close_rect = None


def change_setting(field, direction):
    key = field["key"]
    val = params[key]
    if "choices" in field:
        choices = field["choices"]
        idx = min(range(len(choices)), key=lambda i: abs(choices[i] - val))
        idx = max(0, min(len(choices) - 1, idx + direction))
        val = choices[idx]
    else:
        val = round(val + direction * field["step"], 6)
        val = max(field["min"], min(field["max"], val))
    params[key] = val
    apply_settings()


def apply_settings():
    sim.apply_params()
    monitor.time_window = params["time_window_main"]
    monitor_drive.time_window = params["time_window_drive"]


def draw_settings_page(surface):
    global settings_close_rect
    surface.fill((40, 40, 50))
    title_font = get_font(max(22, int(36 * SCALE)))
    font = get_font(max(16, int(26 * SCALE)))
    surface.blit(title_font.render("Settings", True, (255, 255, 255)), (scaled(20), scaled(10)))

    y0 = scaled(60)
    row_h = scaled(60)
    bw, bh = scaled(40), scaled(40)
    for idx, field in enumerate(setting_fields):
        y = y0 + idx * row_h
        val = params[field["key"]]
        surface.blit(font.render(f"{field['label']}: {val:g}", True, (220, 220, 220)),
                     (scaled(20), y + scaled(8)))
        minus = pygame.Rect(surface.get_width() - scaled(110), y, bw, bh)
        plus = pygame.Rect(surface.get_width() - scaled(60), y, bw, bh)
        for r, txt in ((minus, "-"), (plus, "+")):
            pygame.draw.rect(surface, (100, 100, 100), r)
            lbl = font.render(txt, True, (255, 255, 255))
            surface.blit(lbl, lbl.get_rect(center=r.center))
        settings_rects[field["key"]] = (minus, plus)

    settings_close_rect = pygame.Rect(scaled(20), y0 + len(setting_fields) * row_h + scaled(5),
                                      scaled(260), scaled(46))
    draw_button(surface, settings_close_rect, "Close", True)


def handle_settings_click(pos):
    """pos in Koordinaten der Werte-Flaeche. Gibt True zurueck, wenn behandelt."""
    global show_settings
    if settings_close_rect and settings_close_rect.collidepoint(pos):
        show_settings = False
        return True
    for field in setting_fields:
        rects = settings_rects.get(field["key"])
        if not rects:
            continue
        if rects[0].collidepoint(pos):
            change_setting(field, -1)
            return True
        if rects[1].collidepoint(pos):
            change_setting(field, +1)
            return True
    return False


# ------------------------------------------------------------------
# Buttons
# ------------------------------------------------------------------
def draw_button(surface, rect, text, highlighted):
    color = (150, 150, 90) if highlighted else (90, 90, 90)
    pygame.draw.rect(surface, color, rect)
    pygame.draw.rect(surface, (255, 255, 0) if highlighted else (0, 0, 0), rect, 2)
    label = get_font(max(16, int(26 * SCALE))).render(text, True, (0, 0, 0))
    surface.blit(label, label.get_rect(center=rect.center))


button_margin = scaled(8)
button_w = scaled(105)
button_h = scaled(40)
buttons = {}
x = WIDTH - button_margin - button_w
for name in ("Settings", "Reset", "Start", "Stop"):
    buttons[name] = pygame.Rect(x, button_margin, button_w, button_h)
    x -= button_margin + button_w


def reset_simulation():
    sim.reset()
    monitor.clear()
    monitor_drive.clear()


# ------------------------------------------------------------------
# Zeichnen
# ------------------------------------------------------------------
def draw_motor_view(surface):
    surface.fill((30, 30, 30))
    motor = sim.motor
    iA, iB, iC = motor.phase_currents
    currents = {"A": iA, "B": iB, "C": iC}

    pygame.draw.circle(surface, (150, 150, 150), sim_center, stator_radius, 2)

    flux_level = motor.flux_amplitude / 1.0      # ca. 1 Vs = Nennfluss
    sim.rotor.draw(surface, sim_center, rotor_radius, motor.flux_angle, flux_level, SCALE)

    for coil in coils:
        coil.set_current(currents[coil.phase])
        coil.draw(surface)

    # Staenderstrom-Raumzeiger
    amp = min(1.0, motor.current_amplitude / (2 * I_SCALE))
    if amp > 0.01:
        ang = motor.current_angle
        length = stator_radius * 0.95 * amp
        end = (sim_center[0] + length * math.cos(ang), sim_center[1] - length * math.sin(ang))
        pygame.draw.line(surface, (0, 255, 120), sim_center, end, max(2, int(5 * SCALE)))
        pygame.draw.circle(surface, (0, 255, 120), (int(end[0]), int(end[1])), max(3, int(7 * SCALE)))

    font = get_font(max(14, int(24 * SCALE)))
    legend = [
        ("Space vectors, electrical angle (p = 2)", (220, 220, 220)),
        ("green: stator current   N/S: rotor flux", (180, 230, 180)),
        ("white dot: shaft (mech. angle)", (230, 230, 230)),
        ("red/blue: current out of/into page", (220, 160, 160)),
    ]
    y = surface.get_height() - len(legend) * font.get_linesize() - scaled(8)
    for text, color in legend:
        surface.blit(font.render(text, True, color), (scaled(12), y))
        y += font.get_linesize()


def draw_values(surface, sim_tempo):
    surface.fill((200, 200, 200))
    motor, drive, rotor = sim.motor, sim.drive, sim.rotor
    rpm = rotor.omega * 60 / (2 * math.pi)
    texts = [
        f"Status: {sim.status}",
        f"Speed: {rotor.omega:6.1f} rad/s ({rpm:5.0f} rpm)",
        f"Setpoint (ramp): {sim.omega_ref:6.1f} rad/s",
        f"Motor torque: {sim.torque_filt:6.1f} Nm",
        f"Load torque: {sim.load_torque:6.1f} Nm",
        f"Stator frequency: {sim.freq:6.2f} Hz",
        f"Slip: {100 * sim.slip:6.2f} %",
        f"Phase voltage: {sim.V_amp:5.0f} V peak (m = {drive.modulation:.2f})",
        f"U_DC: {drive.Vdc:5.0f} V",
        f"Motor current: {motor.current_amplitude / math.sqrt(2):5.2f} A rms",
        f"Rotor flux: {motor.flux_amplitude:5.3f} Vs",
        f"Electrical power: {sim.power_filt:6.0f} W",
        f"Sim speed: {sim_tempo:4.2f}x real time",
    ]
    font = get_font(max(16, int(28 * SCALE)))
    line_h = font.get_linesize()
    for i, text in enumerate(texts):
        surface.blit(font.render(text, True, (0, 0, 0)), (scaled(16), scaled(10) + i * line_h))


def draw_controls(surface):
    surface.fill((180, 180, 180))
    title_font = get_font(max(18, int(32 * SCALE)))
    for x, title in zip(col_x, column_titles):
        surface.blit(title_font.render(title, True, (20, 20, 60)), (x, scaled(10)))
    for s in sliders.values():
        s.draw(surface)


# ------------------------------------------------------------------
# Hauptschleife
# ------------------------------------------------------------------
sim_running = False
show_settings = False
sim_tempo = 0.0
last_wall = time.perf_counter()
last_sim_t = sim.t
running = True

while running:
    # ---------------- Ereignisse ----------------
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_b:
                sim.brake.active = True
            elif event.key == pygame.K_SPACE:
                sim_running = not sim_running
            elif event.key == pygame.K_r:
                reset_simulation()
            elif event.key == pygame.K_s:
                show_settings = not show_settings

        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_b:
                sim.brake.active = False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if buttons["Start"].collidepoint(pos):
                sim_running = True
            elif buttons["Stop"].collidepoint(pos):
                sim_running = False
            elif buttons["Reset"].collidepoint(pos):
                reset_simulation()
            elif buttons["Settings"].collidepoint(pos):
                show_settings = not show_settings
            elif show_settings and rect_values.collidepoint(pos):
                handle_settings_click((pos[0] - rect_values.x, pos[1] - rect_values.y))

        # Mausereignisse in Slider-Koordinaten weitergeben
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
            local = (event.pos[0] - rect_controls.x, event.pos[1] - rect_controls.y)
            attrs = {"pos": local}
            if hasattr(event, "button"):
                attrs["button"] = event.button
            local_event = pygame.event.Event(event.type, attrs)
            for s in sliders.values():
                s.handle_event(local_event)

    if not running:
        break

    # ---------------- Simulation ----------------
    sync_sliders()
    if sim_running:
        sim.advance(params["time_scale"] / FPS)

    now = time.perf_counter()
    wall_dt = now - last_wall
    if wall_dt > 0:
        tempo_now = (sim.t - last_sim_t) / wall_dt
        sim_tempo += 0.1 * (tempo_now - sim_tempo)
    last_wall, last_sim_t = now, sim.t

    # ---------------- Zeichnen ----------------
    monitor.draw_main_graphs(graph_surface_main)
    monitor_drive.draw_scope(graph_surface_drive)
    draw_controls(control_surface)
    draw_motor_view(sim_surface)
    if show_settings:
        draw_settings_page(value_surface)
    else:
        draw_values(value_surface, sim_tempo)

    screen.blit(graph_surface_main, rect_main)
    screen.blit(graph_surface_drive, rect_drive)
    screen.blit(control_surface, rect_controls)
    screen.blit(sim_surface, rect_sim)
    screen.blit(value_surface, rect_values)

    draw_button(screen, buttons["Start"], "Start", sim_running)
    draw_button(screen, buttons["Stop"], "Stop", not sim_running)
    draw_button(screen, buttons["Reset"], "Reset", False)
    draw_button(screen, buttons["Settings"], "Settings", show_settings)

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()
