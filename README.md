# Motor_Simulation_Control_System



This is a simulation of a controlled system operating on a motor. The inputs of the system are grid voltage and motor-specific values.  The system uses two PID controllers and an open-loop V/f controller to adjust power fed to the motor. 
The voltage and required frequencies based on feedback from the controllers are changed by an AC drive, which is assumed to be able to communicate with the controllers. 

The values are tracked and visualized. All implementation, including graphs, is made in pygame since matplotlib is really slow when combined with pygame. 

In settings, one can adjust most of the constants relevant for analysis, though one can also directly change them in main.py if they should be constant over the simulation. For optimal performance, one might have to adjust the fps of the simulation.

Due to the use of pygame, this project runs only on python versions strictly older than 3.14. 



To rescale for window fit, adjust SCALE. Set SCALE=1 for monitors, SCALE=0.5 for laptop. 
To be run from main.py


Please comment possible improvements (besides translating it into cpp XD )
