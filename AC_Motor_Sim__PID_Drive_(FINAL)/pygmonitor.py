from bisect import bisect_left
from collections import deque
from itertools import islice

import numpy as np
import pygame

from fonts import get_font


# -------------------------
# RMS
# -------------------------
def compute_rms(data, window=1000):
    samples = np.array(list(data)[-window:], dtype=float)
    if len(samples) == 0:
        return 0.0
    return float(np.sqrt(np.mean(samples ** 2)))


# -------------------------
# Hilfsfunktionen zum Zeichnen
# -------------------------
def _window(t_deque, series, t_min):
    """Schneidet alle Datenreihen auf das sichtbare Zeitfenster zu."""
    n = len(t_deque)
    lo = bisect_left(t_deque, t_min)
    ts = list(islice(t_deque, lo, n))
    return ts, [list(islice(s, lo, n)) for s in series]


def _draw_trace(surface, rect, ts, vals, t_min, t_max, y_min, y_max, color, minmax=False):
    if len(ts) < 2 or t_max <= t_min:
        return
    width = max(1, rect.width)
    y_span = (y_max - y_min) or 1.0
    t_span = t_max - t_min
    top, bottom = rect.y, rect.y + rect.height - 1

    def ypix(v):
        y = rect.y + rect.height * (1.0 - (v - y_min) / y_span)
        return min(bottom, max(top, y))

    pts = []
    if minmax and len(ts) > 2 * width:
        # Min/Max je Pixelspalte (wie ein Oszilloskop, zeigt PWM korrekt)
        col_min = {}
        col_max = {}
        for t, v in zip(ts, vals):
            col = int((t - t_min) / t_span * (width - 1))
            if col in col_min:
                if v < col_min[col]:
                    col_min[col] = v
                if v > col_max[col]:
                    col_max[col] = v
            else:
                col_min[col] = v
                col_max[col] = v
        for col in sorted(col_min):
            x = rect.x + col
            pts.append((x, ypix(col_min[col])))
            pts.append((x, ypix(col_max[col])))
    else:
        step = max(1, len(ts) // (2 * width))
        for i in range(0, len(ts), step):
            x = rect.x + (ts[i] - t_min) / t_span * rect.width
            pts.append((x, ypix(vals[i])))

    if len(pts) > 1:
        pygame.draw.lines(surface, color, False, pts, 1)


def _draw_frame(surface, rect, t_min, t_max, time_window, y_min, y_max, font):
    # Zeitgitter (10 Teilungen)
    grid_dt = time_window / 10.0
    if grid_dt > 0:
        t_line = t_min - (t_min % grid_dt) + grid_dt
        while t_line < t_max:
            x = rect.x + (t_line - t_min) / (t_max - t_min) * rect.width
            pygame.draw.line(surface, (70, 70, 80), (x, rect.y), (x, rect.y + rect.height))
            t_line += grid_dt
    # Nulllinie
    if y_min < 0 < y_max:
        y0 = rect.y + rect.height * (1 - (0 - y_min) / (y_max - y_min))
        pygame.draw.line(surface, (100, 100, 110), (rect.x, y0), (rect.x + rect.width, y0))
    # Skala
    surface.blit(font.render(f"{y_max:g}", True, (190, 190, 190)), (rect.x + 4, rect.y + 2))
    lbl = font.render(f"{y_min:g}", True, (190, 190, 190))
    surface.blit(lbl, (rect.x + 4, rect.y + rect.height - lbl.get_height() - 2))


# =========================================================
# HAUPTGRAFEN
# =========================================================
class Monitor:
    PLOTS = [
        # Titel, (y_min, y_max), [(Schluessel, Farbe, Legende)], relative Hoehe
        ("Speed [rad/s]", (-20, 170),
         [("omega", (255, 255, 0), "Actual"), ("omega_ref", (255, 150, 0), "Setpoint (ramp)")], 3.0),
        ("Torque [Nm]", (-50, 50),
         [("torque", (255, 100, 100), "Motor"), ("load", (170, 170, 170), "Load")], 1.8),
        ("Current i_A [A]", (-40, 40),
         [("iA", (0, 255, 100), "Phase A")], 1.6),
        ("Voltage u_A [V] (fundamental)", (-400, 400),
         [("vA", (0, 180, 255), "Phase A")], 1.6),
    ]

    def __init__(self, scale=1.0, max_len=4000, time_window=10.0):
        self.scale = scale
        self.time_window = time_window
        self.omega_target = 0.0
        self.max_len = max_len
        self.clear()

    def clear(self):
        self.t = deque(maxlen=self.max_len)
        self.data = {key: deque(maxlen=self.max_len)
                     for _, _, traces, _ in self.PLOTS for key, _, _ in traces}

    def log(self, t, omega, omega_ref, torque, load, iA, vA):
        self.t.append(t)
        d = self.data
        d["omega"].append(omega)
        d["omega_ref"].append(omega_ref)
        d["torque"].append(torque)
        d["load"].append(load)
        d["iA"].append(iA)
        d["vA"].append(vA)

    def draw_main_graphs(self, surface):
        surface.fill((50, 50, 60))
        W, H = surface.get_size()
        gap = max(4, int(12 * self.scale))
        title_h = max(14, int(30 * self.scale))
        title_font = get_font(max(16, int(32 * self.scale)))
        axis_font = get_font(max(14, int(26 * self.scale)))

        total = sum(p[3] for p in self.PLOTS)
        usable = H - gap * (len(self.PLOTS) + 1)

        if self.t:
            t_max = max(self.t[-1], self.time_window)
        else:
            t_max = self.time_window
        t_min = t_max - self.time_window

        keys = [k for _, _, traces, _ in self.PLOTS for k, _, _ in traces]
        ts, cols = _window(self.t, [self.data[k] for k in keys], t_min)
        visible = dict(zip(keys, cols))

        y = gap
        for title, (y_min, y_max), traces, h in self.PLOTS:
            h_px = int(usable * h / total)
            full = pygame.Rect(gap, y, W - 2 * gap, h_px)
            rect = pygame.Rect(full.x, full.y + title_h, full.width, full.height - title_h)
            pygame.draw.rect(surface, (200, 200, 200), full, 1)

            surface.blit(title_font.render(title, True, (225, 225, 225)),
                         (full.x + 6, full.y + 3))

            # Legende
            lx = full.right - 6
            for _, color, name in reversed(traces):
                lbl = axis_font.render(name, True, color)
                lx -= lbl.get_width()
                surface.blit(lbl, (lx, full.y + 4))
                lx -= 14

            _draw_frame(surface, rect, t_min, t_max, self.time_window, y_min, y_max, axis_font)

            if title.startswith("Speed") and y_min <= self.omega_target <= y_max:
                y_ref = rect.y + rect.height * (1 - (self.omega_target - y_min) / (y_max - y_min))
                for x in range(rect.x, rect.right, 10):
                    pygame.draw.line(surface, (255, 180, 0), (x, y_ref), (x + 5, y_ref), 1)
                lbl = axis_font.render(f"Target = {self.omega_target:g} rad/s", True, (220, 200, 0))
                surface.blit(lbl, (rect.right - lbl.get_width() - 6, y_ref - lbl.get_height() - 2))

            for key, color, _ in traces:
                _draw_trace(surface, rect, ts, visible[key], t_min, t_max, y_min, y_max, color)

            y += h_px + gap

        lbl = axis_font.render(f"t = {t_max:.1f} s   (window {self.time_window:g} s)",
                               True, (200, 200, 200))
        surface.blit(lbl, (W - lbl.get_width() - gap, H - lbl.get_height() - 2))


# =========================================================
# SCOPE: NETZ -> GLEICHRICHTER -> ZWISCHENKREIS -> WECHSELRICHTER
# =========================================================
class DriveMonitor:
    COLUMNS = [
        # Titel, Spannung (Schluessel, Bereich), Strom (Schluessel, Bereich)
        ("GRID", ("v_grid", (-400, 400), "u_A"), ("i_grid", (-40, 40), "i_A")),
        ("RECTIFIER", ("v_rect", (0, 800), "u"), ("i_rect", (0, 40), "i")),
        ("DC LINK", ("v_dc", (0, 800), "U_DC"), ("i_dc", (-40, 40), "I_DC")),
        ("INVERTER", ("v_inv", (-600, 600), "u_A"), ("i_inv", (-40, 40), "i_A")),
    ]

    def __init__(self, scale=1.0, max_len=26000, time_window=0.06):
        self.scale = scale
        self.time_window = time_window
        self.max_len = max_len
        self.clear()

    def clear(self):
        self.t = deque(maxlen=self.max_len)
        self.data = {}
        for _, (kv, _, _), (ki, _, _) in self.COLUMNS:
            self.data[kv] = deque(maxlen=self.max_len)
            self.data[ki] = deque(maxlen=self.max_len)

    def log(self, t, v_grid, i_grid, v_rect, i_rect, v_dc, i_dc, v_inv, i_inv):
        self.t.append(t)
        d = self.data
        d["v_grid"].append(v_grid)
        d["i_grid"].append(i_grid)
        d["v_rect"].append(v_rect)
        d["i_rect"].append(i_rect)
        d["v_dc"].append(v_dc)
        d["i_dc"].append(i_dc)
        d["v_inv"].append(v_inv)
        d["i_inv"].append(i_inv)

    def draw_scope(self, surface):
        surface.fill((20, 20, 20))
        W, H = surface.get_size()
        cols, rows = len(self.COLUMNS), 2
        margin = max(4, int(10 * self.scale))
        title_h = max(12, int(26 * self.scale))
        cell_w = (W - margin * (cols + 1)) // cols
        cell_h = (H - margin * (rows + 1)) // rows
        font = get_font(max(13, int(24 * self.scale)))

        if self.t:
            t_max = max(self.t[-1], self.time_window)
        else:
            t_max = self.time_window
        t_min = t_max - self.time_window

        keys = list(self.data.keys())
        ts, series = _window(self.t, [self.data[k] for k in keys], t_min)
        visible = dict(zip(keys, series))

        for c, (title, volt, curr) in enumerate(self.COLUMNS):
            x = margin + c * (cell_w + margin)
            for r, ((key, (y_min, y_max), name), color, unit) in enumerate(
                    [(volt, (0, 200, 255), "V"), (curr, (0, 255, 120), "A")]):
                full = pygame.Rect(x, margin + r * (cell_h + margin), cell_w, cell_h)
                rect = pygame.Rect(full.x, full.y + title_h, full.width, full.height - title_h)
                pygame.draw.rect(surface, (120, 120, 120), full, 1)
                surface.blit(font.render(f"{title}  {name} [{unit}]", True, (220, 220, 220)),
                             (full.x + 4, full.y + 2))
                _draw_frame(surface, rect, t_min, t_max, self.time_window, y_min, y_max, font)
                _draw_trace(surface, rect, ts, visible[key], t_min, t_max,
                            y_min, y_max, color, minmax=True)

        lbl = font.render(f"Window {self.time_window * 1000:g} ms", True, (200, 200, 200))
        surface.blit(lbl, (W - lbl.get_width() - margin, H - lbl.get_height() - 1))
