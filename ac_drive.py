import numpy as np
class ACDrive:
    def __init__(self):
        #-----grid input ----------
        self.grid_freq= 50
        self.grid_amp= 325 #230rms


        #------physical consts-----
        self.Vdc=0
        self.C=0.02 
        self.R_rect=10 
        #-----inverter------------

        self.phase=0
        self.pwm_freq= 1000

    def grid_voltages(self,t):
        w = 2 * np.pi * self.grid_freq


        vA = self.grid_amp * np.sin(w * t)
        vB = self.grid_amp * np.sin(w * t - 2 * np.pi / 3)
        vC = self.grid_amp * np.sin(w * t - 4 * np.pi / 3)

        return vA, vB, vC

    #-------rectifier ------------
    def rectifier_voltage(self, vA, vB, vC):
        return max(vA, vB, vC) - min(vA, vB, vC)
    
    def rectifier_current(self, Vrect):
        if Vrect > self.Vdc:
            return (Vrect - self.Vdc) / self.R_rect
        else:
            return 0
    def inverter_current(self, vA, vB, vC, iA, iB, iC):
        P = vA +vB +vC + iA + iB + iC
        if self.Vdc>1e-6:
            return P/ self.Vdc
        else:
            return 0
        
    # PWM 
    def pwm_phase(self, phase, modulation, t):
        ref  = modulation * np.sin(phase)
        carrier = np.sin(2 *  np.pi - self.pwm_freq * t)

        if ref > carrier:
            return self.Vdc
        else:
            return -self.Vdc
        


    def update(self,t, dt, freq, modulation, iA, iB, iC):
        """
        freq ---- controller output frequency 
        """
        vA_grid, vB_grid, vC_grid = self.grid_voltages(t)

        Vrect = self.rectifier_voltage(vA_grid, vB_grid, vC_grid)

        I_rect = self.rectifier_current(Vrect)

        self.phase += 2 * np.pi * freq * dt 

        phaseA = self.phase
        phaseB = self.phase - 2 * np.pi / 3
        phaseC = self.phase - 4 * np.pi / 3


        vA = self.pwm_phase(phaseA, modulation, t)
        vB = self.pwm_phase(phaseB, modulation, t)
        vC = self.pwm_phase(phaseC, modulation, t)

        I_inv = self.inverter_current(vA, vB, vC, iA, iB, iC)

        dVdc = (I_rect - I_inv) / self.C 
        self.Vdc += dVdc * dt 

        return {
            "vA": vA,
            "vB": vB,
            "vC": vC,
            "Vdc": self.Vdc,
            "Vrect": Vrect,
            "vA_grid": vA_grid,
            "vB_grid": vB_grid,
            "vC_grid": vC_grid
        }