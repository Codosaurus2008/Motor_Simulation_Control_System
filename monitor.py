




### !!! NOT USED !!!





import matplotlib.pyplot as plt
from collections import deque 
import numpy as np
plt.switch_backend('Agg')



def compute_rms(data, window=1000):
    data_list = list(data)           
    samples = np.array(data_list[-window:]) 

    if len(samples) == 0:
        return 0

    return np.sqrt(np.mean(samples**2))




class Monitor:
    def __init__(self, scale=1.0):
        plt.ion()
        self.WINDOW = 4
        self.scale = scale
        self.max_len = 10000   # recommended range: 1000–3000

        self.t = deque(maxlen=self.max_len)
        self.omega = deque(maxlen=self.max_len)
        self.torque = deque(maxlen=self.max_len)

        self.iA = deque(maxlen=self.max_len)
        self.iB = deque(maxlen=self.max_len)
        self.iC = deque(maxlen=self.max_len)

        self.vA = deque(maxlen=self.max_len)
        self.vB = deque(maxlen=self.max_len)
        self.vC = deque(maxlen=self.max_len)

        self.Vdc = deque(maxlen=self.max_len)

        # Create figure
        self.fig, self.axs = plt.subplots(5, 1, figsize=(max(8, 15 * scale), max(6, 10 * scale)))
        self.fig.subplots_adjust(hspace=max(0.3, 0.5 * scale))
        # Lines
        lw=0.3
        self.line_speed, = self.axs[0].plot([], [])
        self.line_torque, = self.axs[1].plot([], [])
        self.line_iA, = self.axs[2].plot([], [], label="iA")
        self.line_iB, = self.axs[2].plot([], [], label="iB")
        self.line_iC, = self.axs[2].plot([], [], label="iC")
        self.line_vA, = self.axs[3].plot([], [], label="vA")
        self.line_vB, = self.axs[3].plot([], [], label="vB")
        self.line_vC, = self.axs[3].plot([], [], label="vC")
        self.axs[3].set_title("Phase Voltages")
        self.axs[3].legend()

        self.axs[0].set_title("Speed")
        self.axs[1].set_title("Torque")
        self.axs[2].set_title("Phase Currents")
        self.axs[2].legend()

    



    # -------------------------
    # LOG DATA
    # -------------------------
    def log(self, t, omega, torque, iA, iB, iC, vA, vB, vC, Vdc):


        self.t.append(t)
        self.omega.append(omega)
        self.torque.append(torque)

        self.iA.append(iA)
        self.iB.append(iB)
        self.iC.append(iC)
        
        self.vA.append(vA)
        self.vB.append(vB)
        self.vC.append(vC)

        self.Vdc.append(Vdc)



    # -------------------------
    # UPDATE PLOT (SCROLLING)
    # -------------------------
    def update_plot(self):
        if len(self.t) < 2:
            return

        # update lines
        lw=0.3
        self.line_speed.set_data(list(self.t), self.omega)
        self.line_torque.set_data(list(self.t), self.torque)
        self.line_iA.set_data(list(self.t), self.iA)
        self.line_iB.set_data(list(self.t), self.iB)
        self.line_iC.set_data(list(self.t), self.iC)
        self.line_vA.set_data(list(self.t), self.vA)
        self.line_vB.set_data(list(self.t), self.vB)
        self.line_vC.set_data(list(self.t), self.vC)





        t_min = self.t[-1] - self.WINDOW

        # filter indices for visible data
        indices = [i for i, t_val in enumerate(self.t) if t_val >= t_min]

        # extract only visible values
        torque_visible = [self.torque[i] for i in indices]


        # ✅ SCROLLING WINDOW
        t_min = self.t[-1] - self.WINDOW
        t_max = self.t[-1]

        for ax in self.axs:
            ax.set_xlim(t_min, t_max)
        # -------- SPEED --------
        if len(self.omega) > 0:
            o_min = min(self.omega)
            o_max = max(self.omega)

            if abs(o_max - o_min) < 1e-6:
                o_max += 0.1
                o_min -= 0.1

            margin = 0.1 * (o_max - o_min)
            self.axs[0].set_ylim(o_min - margin, o_max + margin)


        # -------- TORQUE --------
        t_min = self.t[-1] - self.WINDOW

        # filter indices for visible data
        indices = [i for i, t_val in enumerate(self.t) if t_val >= t_min]

        # extract only visible values
        torque_visible = [self.torque[i] for i in indices]

        if len(torque_visible) > 0:
            t_min_val = min(torque_visible)*3
            t_max_val = max(torque_visible)*3

            margin = 0.1 * (t_max_val - t_min_val + 1e-6)

            self.axs[1].set_ylim(t_min_val - margin, t_max_val + margin)


        # -------- CURRENTS --------
        if len(self.iA) > 0:
            i_all = self.iA + self.iB + self.iC
            i_min = min(i_all)
            i_max = max(i_all)

            if abs(i_max - i_min) < 1e-6:
                i_max += 0.1
                i_min -= 0.1

            margin = 0.1 * (i_max - i_min)
            self.axs[2].set_ylim(i_min - margin, i_max + margin)


        # -------- VOLTAGES --------
        if len(self.vA) > 0:
            v_all = self.vA + self.vB + self.vC
            v_min = min(v_all)
            v_max = max(v_all)

            if abs(v_max - v_min) < 1e-6:
                v_max += 0.1
                v_min -= 0.1

            margin = 0.1 * (v_max - v_min)
            self.axs[3].set_ylim(v_min - margin, v_max + margin)
            # draw
            self.fig.canvas.draw()
            self.fig.canvas.flush_events()



    def get_image(self):
        # draw the matplotlib figure
        self.fig.canvas.draw()

        # get raw pixel data
        raw_data = self.fig.canvas.buffer_rgba()
        size = self.fig.canvas.get_width_height()

        # convert to pygame surface
        import pygame
        return pygame.image.frombuffer(raw_data, size, "RGBA")
    

