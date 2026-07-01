from collections import deque
import numpy as np
import pygame


# -------------------------
# RMS
# -------------------------
def compute_rms(data, window=1000):
    data_list = list(data)
    samples = np.array(data_list[-window:])
    if len(samples) == 0:
        return 0
    return np.sqrt(np.mean(samples**2))


# =========================================================
# MAIN MONITOR
# =========================================================
class Monitor:
    def __init__(self, scale=1, max_len=30000):
        self.time_window = None   
        self.max_len=max_len 
        self.t = deque(maxlen=self.max_len)
        self.scale = scale
        self.omega_target= 0
        self.omega = deque(maxlen=self.max_len)
        self.torque = deque(maxlen=self.max_len)

        self.iA = deque(maxlen=self.max_len)
        self.vA = deque(maxlen=self.max_len)

        self._time_axis_last = None
        self._time_axis_text = None


    def log(self, t, omega, torque,
            iA, iB, iC,
            vA, vB, vC,
            Vdc):

        self.t.append(t)
        self.omega.append(omega)
        self.torque.append(torque)

        self.iA.append(iA)
        self.vA.append(vA)

        
    # -------------------------
    # DRAW MAIN GRAPHS indices
    # -------------------------
    def draw_main_graphs(self, surface):

        surface.fill((50, 50, 50))

        WIDTH, HEIGHT = surface.get_size()
        gap = 12

        heights = [3.0, 1.2, 3, 1.2]
        total = sum(heights)

        usable_height = HEIGHT - gap * (len(heights)+1)
        row_heights = [int(usable_height * h / total) for h in heights]

        scales = {
            "Speed": (-5, 15),
            "Torque": (-50, 50),
            "Current": (-150, 150),
            "Voltage": (-200, 200),
        }

    

        signals = [
            (self.omega, (255,255,0), "Speed"),
            (self.torque, (255,100,100), "Torque"),
            (self.iA, (0,255,100), "Current"),
            (self.vA, (0,180,255), "Voltage"),
        ]

        title_font = pygame.font.SysFont(None, int(40*self.scale))
        axis_font = pygame.font.SysFont(None, int(40*self.scale))
        time_font = pygame.font.SysFont(None, int(40*self.scale))

        def draw_signal(data, rect_full, color, name):

            if len(self.t) < 2:
                return

            title_h = 24
            rect = pygame.Rect(rect_full.x, rect_full.y + title_h,
                            rect_full.width, rect_full.height - title_h)

            # ---------- TITLE (OUTSIDE GRAPH) ----------
            label = title_font.render(name, True, (220,220,220))
            surface.blit(label, label.get_rect(center=(rect_full.centerx, rect_full.y + title_h//2)))

            # ---------- DATA ----------
            data = list(data)

            t_max = self.t[-1]
            t_min = t_max - self.time_window
            t_vals_full = self.t

            start = 0
            for i in range(len(t_vals_full)-1, -1, -1):
                if t_vals_full[i] < t_min:
                    start = i + 1
                    break

            data = data[start:]
            t_vals = list(t_vals_full)[start:]

            step = max(1, len(data)//rect.width)
            data = data[::step]
            t_vals = t_vals[::step]

            y_min, y_max = scales[name]

            def scale_y(v):
                return (v - y_min)/(y_max - y_min)

            # ---------- TIME GRID + LABELS ----------
    
            grid_dt = self.time_window / 10

            t_line = t_min - (t_min % grid_dt)

            while t_line < t_max:
                x = rect.x + (t_line - t_min)/(t_max - t_min + 1e-6) * rect.width

                # grid line
                pygame.draw.line(surface, (50,50,50),
                                (x, rect.y),
                                (x, rect.y + rect.height))

                t_line += grid_dt

                if name == "Speed":

                    omega_ref = self.omega_target

                    # only draw if within visible range
                    if y_min <= omega_ref <= y_max:

                        # convert value to Y position
                        y_ref = rect.y + rect.height * (1 - (omega_ref - y_min)/(y_max - y_min))

                        # draw dashed-like line
                        for x in range(rect.x, rect.x + rect.width, 10):
                            pygame.draw.line(surface, (255, 180, 0),
                                            (x, y_ref),
                                            (x + 5, y_ref), 1)

                        label = axis_font.render(f"ω_target = {omega_ref}", True, (200, 200, 0))
                        surface.blit(label, (rect.x + rect.width - 120, y_ref - 18))
                        
            # ---------- SIGNAL ----------
            pts = []
            for i in range(len(data)):
                t_norm = (t_vals[i]-t_min)/(t_max - t_min + 1e-6)
                x = rect.x + t_norm * rect.width

                y_norm = scale_y(data[i])
                y = rect.y + rect.height * (1 - y_norm)

                pts.append((x,y))

            if len(pts) > 1:
                pygame.draw.lines(surface, color, False, pts, 1)

            # ---------- TIME LABEL ----------
            if self._time_axis_last is None or t_max - self._time_axis_last >= 0.5:
                self._time_axis_last = t_max
                self._time_axis_text = time_font.render(f"t = {t_max:.1f}s", True, (200,200,200))
            if self._time_axis_text:
                surface.blit(self._time_axis_text, (
                    rect_full.x + 4,
                    rect_full.y + 7
                ))

            # ---------- ZERO LINE ----------
            if y_min < 0 < y_max:
                y0 = rect.y + rect.height * (1 - scale_y(0))
                pygame.draw.line(surface, (90,90,90),
                                (rect.x, y0),
                                (rect.x + rect.width, y0))

        # ---------- LAYOUT ----------
        y_offset = gap

        for i, (data, color, name) in enumerate(signals):

            rect_full = pygame.Rect(gap, y_offset, WIDTH-2*gap, row_heights[i])

            pygame.draw.rect(surface, (200,200,200), rect_full, 1)

            draw_signal(data, rect_full, color, name)

            y_offset += row_heights[i] + gap












# =========================================================
# DRIVE MONITOR
# =========================================================



class DriveMonitor:
    def __init__(self, scale=1,  max_len=20000):
        self.scale=scale
        self.time_window = None
        self.max_len = max_len   
        self.t = deque(maxlen=self.max_len)

        self.vA_grid = deque(maxlen=self.max_len)
        self.Vrect = deque(maxlen=self.max_len)
        self.Vdc = deque(maxlen=self.max_len)

        self.vA = deque(maxlen=self.max_len)
        self.iA = deque(maxlen=self.max_len)

        self._time_axis_last = None
        self._time_axis_text = None

    def log(self, t, iA, vA, Vdc,
            vA_grid, vB_grid, vC_grid,
            Vrect):

        self.t.append(t)
        self.iA.append(iA)
        self.vA.append(vA)
        self.Vdc.append(Vdc)
        self.vA_grid.append(vA_grid)
        self.Vrect.append(Vrect)

    def draw_scope(self, surface):

        surface.fill((20,20,20))

        WIDTH, HEIGHT = surface.get_size()

        cols = 4
        rows = 2
        margin = 10

        cell_w = (WIDTH - margin*(cols+1)) // cols
        cell_h = (HEIGHT - margin*(rows+1)) // rows

        title_h = 18

        axis_font = pygame.font.SysFont(None, int(self.scale* 30))
        time_font = pygame.font.SysFont(None, int(self.scale * 30))

        voltage_range = (-800, 800)
        current_range = (-250, 250)

        def extract(data):
            if len(self.t) < 2:
                return [], []

            t_max = self.t[-1]
            t_min = t_max - self.time_window

            indices = [i for i, tt in enumerate(self.t) if tt >= t_min]

            d = [data[i] for i in indices]
            t_vals = [self.t[i] for i in indices]

            step = max(1, len(d)//cell_w)
            return d[::step], t_vals[::step]

        def draw_signal(data, rect_full, color, y_min, y_max, title):

            # split title + graph
            rect = pygame.Rect(rect_full.x, rect_full.y + title_h,
                            rect_full.width, rect_full.height - title_h)

            # TITLE (outside)
            title_font = pygame.font.SysFont(None, 20)
            surface.blit(title_font.render(title, True, (220,220,220)),
                        (rect_full.centerx - 30, rect_full.y))

            d, t_vals = extract(data)
            if len(d) < 2:
                return
            t_max = self.t[-1]
            t_min = t_max - self.time_window


            # time grid
            grid_dt = self.time_window / 10
            t_line = t_min - (t_min % grid_dt)

            while t_line < t_max:
                x = rect.x + (t_line - t_min)/(t_max - t_min) * rect.width

                pygame.draw.line(surface, (50,50,50),
                                (x, rect.y),
                                (x, rect.y + rect.height))

                t_line += grid_dt


            surface.blit(axis_font.render(f"{y_max:.1f}", True, (200,200,200)),
             (rect.x+5, rect.y+5))

            surface.blit(axis_font.render(f"{y_min:.1f}", True, (200,200,200)),
                        (rect.x+5, rect.y + rect.height - 30))

            pts = []
            for i in range(len(d)):
                t_norm = (t_vals[i]-t_min)/(t_max-t_min)
                x = rect.x + t_norm * rect.width

                y = rect.y + rect.height * (1 - (d[i]-y_min)/(y_max-y_min))

                pts.append((x,y))

            pygame.draw.lines(surface, color, False, pts, 1)
            
            # time label
            if self._time_axis_last is None or t_max - self._time_axis_last >= 0.5:
                self._time_axis_last = t_max
                self._time_axis_text = time_font.render(f" {t_max:.1f}", True, (200,200,200))
            if self._time_axis_text:
                surface.blit(self._time_axis_text, (
                    rect_full.x + 4,
                    rect_full.y + rect_full.height - self._time_axis_text.get_height() - 4
                ))

        voltage = [self.vA_grid, self.Vrect, self.Vdc, self.vA]
        current = [self.iA]*4
        labels = ["GRID", "RECT", "DC", "INV"]

        for col in range(cols):

            x = margin + col*(cell_w + margin)

            rect_v = pygame.Rect(x, margin, cell_w, cell_h)
            rect_i = pygame.Rect(x, margin*2 + cell_h, cell_w, cell_h)

            pygame.draw.rect(surface, (120,120,120), rect_v, 2)
            pygame.draw.rect(surface, (120,120,120), rect_i, 2)

            draw_signal(voltage[col], rect_v, (0,200,255), *voltage_range, labels[col]+" V")
            draw_signal(current[col], rect_i, (0,255,120), *current_range, labels[col]+" I")