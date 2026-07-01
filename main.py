import pygame
import random
from rotor import Rotor
import numpy as np
from coil import Coil
from pygmonitor import Monitor
from pygmonitor import DriveMonitor
from slider import Slider
from pygmonitor import compute_rms
from brake import BrakeSystem
from pid import PID
from ac_drive import ACDrive
import time 


#--------------------- user and physical parameters ::::: -------------
time_window_main= 10
time_window_drive=0.5 
omega_target=7
V_amp = 20
SCALE=0.5    #0.5 for laptop, 1 for screen

k=0.3
J = 0.2
L= 0.1

power_elec=0
K_slip=0.1
K_vf=50
dt = 0.0005
modulation=0.5
#-------------------display-------------------------- 
w= 2* np.pi * 1
pygame.init()
info = pygame.display.Info()
BASE_WIDTH, BASE_HEIGHT = 2500, 1400


def scaled(value):
    return int(value * SCALE)

WIDTH, HEIGHT = scaled(BASE_WIDTH), scaled(BASE_HEIGHT)
LEFT_WIDTH = scaled(2000)
RIGHT_WIDTH = WIDTH - LEFT_WIDTH
TOP_HEIGHT = scaled(1100)
BOTTOM_HEIGHT = HEIGHT
RHEIGHT = scaled(720)
RHEIGHT = scaled(720)
main_h = int(TOP_HEIGHT * 0.7)
drive_h = int(TOP_HEIGHT * 0.3)

rect_main = pygame.Rect(0, 0, LEFT_WIDTH, main_h)
rect_drive = pygame.Rect(0, main_h, LEFT_WIDTH, drive_h)

graph_surface_main = pygame.Surface((LEFT_WIDTH, main_h))
graph_surface_drive = pygame.Surface((LEFT_WIDTH, drive_h))

rect_controls = pygame.Rect(0, TOP_HEIGHT, LEFT_WIDTH, HEIGHT - TOP_HEIGHT)
rect_sim = pygame.Rect(LEFT_WIDTH, 0, RIGHT_WIDTH, RHEIGHT)
rect_values = pygame.Rect(LEFT_WIDTH, RHEIGHT, RIGHT_WIDTH, BOTTOM_HEIGHT)
control_surface = pygame.Surface((LEFT_WIDTH, HEIGHT - TOP_HEIGHT))
sim_surface = pygame.Surface((RIGHT_WIDTH, HEIGHT))
value_surface = pygame.Surface((RIGHT_WIDTH, BOTTOM_HEIGHT))


sim_center = (RIGHT_WIDTH // 2, RHEIGHT // 2)
center = sim_center
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
clock = pygame.time.Clock()
monitor = Monitor(scale=SCALE)
monitor_drive = DriveMonitor(scale=SCALE)
t = 0
angles = [0, 2*np.pi/3, 4*np.pi/3 ]
gap = 12

# relative heights 
heights = [2.0, 1.0, 1.0, 1.0]

total = sum(heights)

usable_height = HEIGHT - gap * (len(heights)+1)
row_heights = [int(usable_height * h / total) for h in heights]

monitor.time_window= time_window_main
monitor_drive.time_window = time_window_drive


freq=20

# ----------------------rotor -------------------
rotor = Rotor(center, scaled(80), scale=SCALE)
rotor.omega = 0
rotor.J = J
stator_radius = rotor.radius * 1.2
rotor.torque = 20


#--------------------------coils--------------------
coils=[]
for i, angle in enumerate(angles):
    x = center[0] + stator_radius* np.cos(angle)
    y = center[1] - stator_radius * np.sin(angle)

    phase = ["A","B","C"][i]
    coils.append(Coil((x,y), phase, scale=SCALE))






#---------------------braking--------------------

brake = BrakeSystem()
rotor.center=sim_center
pid_speed= PID(
    Kp=5, 
    Ki=4,
    Kd=2, 
    limit_min=-50, 
    limit_max=50
)

pid_torque=PID(
    Kp=0.5, 
    Ki=1, 
    Kd=0, 
    limit_min=-50, 
    limit_max=50
)

#------------------- functions-------------------------
def abc_to_alpha_beta(iA, iB, iC):
    alpha = (2/3) * (iA - 0.5*iB - 0.5*iC)
    beta  = (2/3) * (np.sqrt(3)/2) * (iB - iC)
    return alpha, beta
def draw_values(surface, rotor, field_strength, V_rms=0, I_rms=0):
    surface.fill((200, 200, 200))

    font = pygame.font.SysFont(None, max(18, int(30 * SCALE)))

    texts = [
        f"Speed ω: {rotor.omega:.2f}",
        f"Torque: {rotor.torque:.4f}",
        f"Torque Max: {torque_max:.4f}",
        f"Flux: {field_strength:.3f}",
        f"Power: {power_elec:.2f}" ,
        
        
    
        #V_rms = np.sqrt((V_rms_A**2 + V_rms_B**2 + V_rms_C**2)/3)
        #I_rms = np.sqrt((I_rms_A**2 + I_rms_B**2 + I_rms_C**2)/3) 
        f"Frequency: {freq:.2f}",
        f" V/f ratio: {vf_ratio:.3f}"
    ]

    for i, text in enumerate(texts):
        rendered = font.render(text, True, (0,0,0))
        surface.blit(rendered, (scaled(20), scaled(10) + i * scaled(50)))


# simple button renderer
def draw_button(surface, rect, text, active=True):
    color = (100, 100, 100) if active else (100, 100, 100)
    pygame.draw.rect(surface, color, rect)
    pygame.draw.rect(surface, (0,0,0), rect, 2)
    font = pygame.font.SysFont(None, max(18, int(24 * SCALE)))
    label = font.render(text, True, (0,0,0))
    surface.blit(label, label.get_rect(center=rect.center))


# settings metadata for interactive editor
setting_fields = [
    {"key": "time_window_main", "label": "Main Time Window", "min": 0.5, "max": 15.0, "step": 0.5},
    {"key": "time_window_drive", "label": "Drive Time Window", "min": 0.1, "max": 5.0, "step": 0.02},
    {"key": "omega_target", "label": "Target Speed ω", "min": 0.5, "max": 50.0, "step": 0.5},
    {"key": "k", "label": "Motor Constant k", "min": 0.0, "max": 5.0, "step": 0.01},
    {"key": "J", "label": "Inertia J", "min": 0.01 , "max": 100.0, "step": 0.5},
    {"key": "K_vf", "label": "V/f Gain", "min": 5, "max": 130.0, "step": 5},
]


def draw_settings_page(surface, settings_values):
    surface.fill((40, 40, 50))
    title_font = pygame.font.SysFont(None, max(28, int(36 * SCALE)))
    font = pygame.font.SysFont(None, max(18, int(22 * SCALE)))
    title = title_font.render("Settings", True, (255,255,255))
    surface.blit(title, (scaled(20), scaled(10)))

    y0 = scaled(60)
    button_w = scaled(36)
    for idx, field in enumerate(setting_fields):
        y = y0 + idx * scaled(44)
        key = field["key"]
        val = settings_values.get(key, globals().get(key))
        label = font.render(f"{field['label']}: {val:.6g}", True, (220,220,220))
        surface.blit(label, (scaled(20), y))
        minus = pygame.Rect(surface.get_width() - scaled(140), y, button_w, scaled(30))
        plus = pygame.Rect(surface.get_width() - scaled(92), y, button_w, scaled(30))
        pygame.draw.rect(surface, (100,100,100), minus)
        pygame.draw.rect(surface, (100,100,100), plus)
        surface.blit(font.render("-", True, (255,255,255)), minus.move(scaled(8), scaled(4)))
        surface.blit(font.render("+", True, (255,255,255)), plus.move(scaled(8), scaled(4)))
        field["minus_rect"] = minus
        field["plus_rect"] = plus

    close_rect = pygame.Rect(scaled(20), y0 + len(setting_fields) * scaled(44) + scaled(20), scaled(220), scaled(44))
    draw_button(surface, close_rect, "Close Settings", active=True)
    return close_rect


sliders = [
    # -------- LEFT COLUMN (Environment) --------
    Slider(scaled(50),  scaled(50),  scaled(400), 0.0, 0.2, 0.05, "Noise Level", scale=SCALE),
    Slider(scaled(50),  scaled(150), scaled(400), 0.005, 0.2, 0.1, "Load Disturbance", scale=SCALE),
    Slider(scaled(50),  scaled(250), scaled(400), 0.1, 3.0, 0.5, "Disturbance Freq", scale=SCALE),

    # -------- RIGHT COLUMN (PID) --------
    Slider(scaled(550), scaled(50),  scaled(400), 0.0, 35.0, 5.0, "Kp", scale=SCALE),
    Slider(scaled(550), scaled(150), scaled(400), 0.0, 10.0, 4.0, "Ki", scale=SCALE),
    Slider(scaled(550), scaled(250), scaled(400), 0.0, 8.0, 0.2, "Kd", scale=SCALE),
]
#-----------------AC drive-------------------------
drive = ACDrive()

counter=0 
t=0

fps=20
torque_measured= rotor.torque 
motor_torque= rotor.torque
steps=int(1/dt /fps  ) 
R_phase=1

iA = 0.0
iB = 0.0
iC = 0.0
iA_s, iB_s, iC_s = iA, iB, iC
vA_smooth, vB_smooth , vC_smooth = 0,0,0

substeps=2
dt_fast = dt / substeps

# UI / simulation state
sim_running = False
show_settings = True
settings_close_button = None

# button geometry 
button_margin = scaled(10)
button_w = scaled(110)
button_h = scaled(38)
settings_button_rect = pygame.Rect(LEFT_WIDTH + RIGHT_WIDTH - button_margin - button_w, button_margin, button_w, button_h)
start_button_rect = pygame.Rect(settings_button_rect.x - button_margin - button_w, button_margin, button_w, button_h)
stop_button_rect = pygame.Rect(start_button_rect.x - button_margin - button_w, button_margin, button_w, button_h)




while True:

    if sim_running:



        start=time.time()
        sim_surface.fill((30,30,30))
        clock.tick( fps - 10 * time_window_main )
        noise_level = sliders[0].value
        load_amp    = sliders[1].value
        dist_freq   = sliders[2].value

        Kp = sliders[3].value
        Ki = sliders[4].value
        Kd = sliders[5].value
        pid_speed.Kp = Kp
        pid_speed.Ki = Ki
        pid_speed.Kd = Kd
        # --- modulation (from controller) ---


        #---------------------fast loop ::: dt ------------------------
        for i in range(int(steps)):

            # ----------fastest loop ::: dt_fast --------
            for _ in range(substeps):


                modulation = V_amp / max(0.5 * drive.Vdc, 1e-6)
                modulation = min(modulation, 1.0)
                modulation = max(modulation, 0.05)

                # --- AC DRIVE ---
                drive_out = drive.update(t, dt_fast, freq, modulation, iA, iB, iC)

                vA = drive_out["vA"]
                vB = drive_out["vB"]
                vC = drive_out["vC"]

                Vdc   = drive_out["Vdc"]
                Vrect = drive_out["Vrect"]

                vA_grid = drive_out["vA_grid"]
                vB_grid = drive_out["vB_grid"]
                vC_grid = drive_out["vC_grid"]

                # --- CURRENT UPDATE ---
                dIA = (vA - R_phase * iA) / max(L, 1e-6)
                dIB = (vB - R_phase * iB) / max(L, 1e-6)
                dIC = (vC - R_phase * iC) / max(L, 1e-6)

                iA += dIA * dt_fast
                iB += dIB * dt_fast
                iC += dIC * dt_fast

                t+=dt_fast 


            #-------------filters -------------

            vA_smooth += 0.005 * (vA - vA_smooth)
            vB_smooth += 0.005 * (vB - vB_smooth)
            vC_smooth += 0.005 * (vC - vC_smooth)

            iA_s += 0.01 * (iA - iA_s)
            iB_s += 0.01 * (iB - iB_s)
            iC_s += 0.01 * (iC - iC_s)





            psi_alpha, psi_beta = abc_to_alpha_beta(iA, iB, iC)
            field_angle= np.arctan2(psi_beta, psi_alpha)
            field_strength= np.sqrt(psi_alpha**2 + psi_beta**2)
            pA = vA * iA
            pB = vB * iB
            pC = vC * iC
            power_elec = pA + pB + pC
            torque_max = k * field_strength
            rotor.draw(sim_surface)
            pygame.draw.circle(sim_surface, (150,150,150), center, stator_radius, 3)
            for coil in coils:
                coil.draw(sim_surface)




            #------------------speed controller closed-loop  speed -> torque -------------------------- 

            omega_measured=rotor.omega + random.uniform(-0.2, 0.2)
            error_speed = omega_target - omega_measured
            torque_ref=pid_speed.update(error_speed, dt)
            #---------------torque controller closed loop   torque -> slip -------------------------

            error_torque=torque_ref - torque_measured
            slip_ref = pid_torque.update(error_torque, dt)
            torque_measured= motor_torque 
            #---------------- frequency from flux and speed from slip  -----------------------------------------------
            omega_field = rotor.omega + slip_ref

            # target frequency
            freq_target = omega_field / (2 * np.pi)

            # smooth it
            freq += 0.05 * (freq_target - freq)

            #-------------------- V/f controller ------------------------------------------------
            V_target=K_vf * freq
            V_amp += (V_target - V_amp) * 0.05
            vf_ratio = V_amp / max(freq , 1e-6)
        
            #----------------------- Motor ------------------------------------------------------------

            #Load torque 

            if int(t) % 5 == 0:
                step_dist = load_amp
            else:
                step_dist = 0

            load_torque = step_dist + load_amp * np.sin(dist_freq * t)

            noise = random.uniform(-noise_level, noise_level)

            slip = omega_field - rotor.omega
            motor_torque= k * field_strength * np.tanh(slip)
            rotor.torque = motor_torque - load_torque + noise



            #braking
            brake_torque = brake.compute(rotor.omega)
            rotor.torque-= brake_torque 
    



            rotor.update(dt)

    
            monitor.log(
                    t,
                    rotor.omega,
                    rotor.torque,
                    iA_s, iB_s, iC_s, 
                    vA_smooth, vB_smooth, vC_smooth, 
                    Vdc
                )
            monitor_drive.log(
                t, 
                iA, 
                vA,  
                Vdc, 
                vA_grid, vB_grid, vC_grid, 
                Vrect 
            )




        #-------------slow loop------------------------------
        if counter % 10 == 0:
            draw_values(
                value_surface,
                rotor,
                field_strength
            )
        font = pygame.font.SysFont(None, 36)

        control_surface.blit(font.render("Environment", True, (0,0,0)), (50, 10))
        control_surface.blit(font.render("PID Control", True, (0,0,0)), (550, 10))



        V_amp += (V_target - V_amp) * 0.05




    if not sim_running:
        clock.tick(10)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_b:
                brake.active=True
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
        if event.type == pygame.KEYUP:
            if event.key == pygame.K_b:
                brake.active = False


    # mouse interactions: buttons and settings page (robust coordinates)
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        px, py = event.pos
        # check screen-space button rects
        if settings_button_rect.collidepoint((px, py)):
            print("DEBUG: settings button clicked")
            show_settings = True
        elif start_button_rect.collidepoint((px, py)):
            print("DEBUG: start button clicked")
            sim_running = True
        elif stop_button_rect.collidepoint((px, py)):
            print("DEBUG: stop button clicked")
            sim_running = False
        else:
            # if settings page open, translate to value_surface coords
            if show_settings:
                rx = px - rect_values.x
                ry = py - rect_values.y
                if settings_close_button and settings_close_button.collidepoint((rx, ry)):
                    show_settings = False
                else:
                    for field in setting_fields:
                        if field.get("minus_rect") and field["minus_rect"].collidepoint((rx, ry)):
                            key = field["key"]
                            val = globals().get(key, 0)
                            val = max(field["min"], min(field["max"], val - field["step"]))
                            globals()[key] = val
                            if key == "time_window_main":
                                monitor.time_window = val
                            if key == "time_window_drive":
                                monitor_drive.time_window = val
                            if key == "dt":
                                dt = val
                                steps = max(1, int(1 / max(dt, 1e-12) / fps))
                                dt_fast = dt / max(substeps, 1)
                            if key == "J":
                                rotor.J = val
                            if key == "omega_target":
                                monitor.omega_target = val
                                omega_target = val
                        if field.get("plus_rect") and field["plus_rect"].collidepoint((rx, ry)):
                            key = field["key"]
                            val = globals().get(key, 0)
                            val = max(field["min"], min(field["max"], val + field["step"]))
                            globals()[key] = val
                            if key == "time_window_main":
                                monitor.time_window = val
                            if key == "time_window_drive":
                                monitor_drive.time_window = val
                            if key == "dt":
                                dt = val
                                steps = max(1, int(1 / max(dt, 1e-12) / fps))
                                dt_fast = dt / max(substeps, 1)
                            if key == "J":
                                rotor.J = val
                            if key == "omega_target":
                                monitor.omega_target = val
                                omega_target = val

    monitor.omega_target = globals().get('omega_target', monitor.omega_target)
    omega_target = monitor.omega_target

    if event.type in [pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION]:
        mx, my = event.pos

        # shift into control area coordinates
        mx -= rect_controls.x
        my -= rect_controls.y

        new_event = pygame.event.Event(event.type, pos=(mx, my))

        for s in sliders:
            s.handle_event(new_event)

    monitor.draw_main_graphs(graph_surface_main)
    monitor_drive.draw_scope(graph_surface_drive)

    screen.blit(graph_surface_main, rect_main)
    screen.blit(graph_surface_drive, rect_drive)



    # ---------------- DRAW UI / SLIDERS ----------------
    control_surface.fill((180, 180, 180))  # light background

    for s in sliders:
        s.draw(control_surface)

    screen.blit(control_surface, rect_controls)



        

    #V_amp = sliders[0].value
    #freq  = sliders[1].value
    omega_init =0
    L = sliders[1].value



    rotor.J = J

    # only set omega once (important!)
    if t < 0.1:
        rotor.omega = omega_init




    counter+=1




    screen.blit(sim_surface, rect_sim)
    # draw control buttons on top of simulation (screen coords)
    draw_button(screen, settings_button_rect, "settings", active=not show_settings)
    pygame.draw.rect(screen, (255,255,0), settings_button_rect, 2)
    draw_button(screen, start_button_rect, "Start", active=not sim_running)
    pygame.draw.rect(screen, (255,255,0), start_button_rect, 2)
    draw_button(screen, stop_button_rect, "Stop", active=sim_running)
    pygame.draw.rect(screen, (255,255,0), stop_button_rect, 2)

    # render settings page into the value panel when requested
    if show_settings:
        settings_values = {f["key"]: globals().get(f["key"]) for f in setting_fields}
        settings_close_button = draw_settings_page(value_surface, settings_values)
    else:
        if counter % 10 == 0:
            draw_values(value_surface, rotor, field_strength)

    screen.blit(value_surface, rect_values)


    pygame.display.flip()




    end=time.time()
    #if counter%20==0:
    #    print(end-start)
