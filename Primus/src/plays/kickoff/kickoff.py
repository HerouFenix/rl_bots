from rlutilities.simulation import Car

from plays.play import Play
from plays.actions.drive import Drive
from plays.actions.jump import AirDodge, SpeedFlip

from rlutilities.linear_algebra import vec3, norm, sgn

from util.game_info import GameInfo
from util.math import distance, local, ground_distance

class Kickoff(Play):
    """
    Base kickoff class.
    Kickoffs are based on phases (f.ex - drive -> flip -> drive)
    """
    def __init__(self, agent, state):
        super().__init__(agent)

        self.state = state

        self.drive = Drive(agent, target_speed = 2300)
        self.action = self.drive
        self.phase = 0

        self.name = "KickOff"


    def step(self, dt: float):        
        self.action.step(dt) # Next step of the current action
        self.controls = self.action.controls


class SimpleKickoff(Kickoff):
    """
    Simple kickoff
    Drive towards ball, dodge at the middle and end
    """

    def __init__(self, agent, state):
        super().__init__(agent, state)
        self.drive.target_pos = vec3(0, sgn(state.net.center[1]) * 100, 0)

        self.interruptible = True #Will be true if action is drive, so phase 0 and phase 2

    def step(self, dt):
        # Drive
        if self.phase == 0:
            speed_threshold = 1550 if abs(self.car.position[0]) < 100 else 1400
            if norm(self.car.velocity) > speed_threshold:
                self.action = AirDodge(self.car, 0.1, self.car.position + self.car.velocity)
                self.phase = 1
            
        # Air Dodge
        if self.phase == 1:
            self.action.controls.boost = self.action.state_timer < 0.1
            
            if self.car.on_ground and self.action.finished:
                self.action = self.drive
                self.interruptible = True
                self.phase = 2
            
        # Drive
        if self.phase == 2:
            if distance(self.car, vec3(0,0,93)) < norm(self.car.velocity) * 0.3:
                self.phase = 3
                self.action = AirDodge(self.car, 0.1, self.state.ball.position)

        # Air Dodge
        if self.phase == 3:
            if self.action.finished:
                self.finished = True

        self.name = "Simple Kickoff (" + str(self.phase) + ")"
        super().step(dt)

            
class SpeedFlipDodgeKickoff(Kickoff):
    """
    Used for corner kickoffs
    Drive until min speed achieved then Speed flip then dodge into the ball
    """

    def __init__(self, agent, state):
        super().__init__(agent, state)
        self.drive.target_pos = self.state.net.center * 0.05
        self.speed_flip_start_time = 0.0


    def step(self, dt):
        # Drive
        if self.phase == 0:
            if norm(self.car.velocity) > 800:
                self.action = SpeedFlip(self.car, right = local(self.car, self.state.ball.position)[1] < 0.0)
                self.phase = 1
                self.speed_flip_start_time = self.car.time

        # Speed Flip
        if self.phase == 1:
            if self.action.finished and self.car.on_ground:
                self.action = self.drive
                self.drive.target_pos = vec3(0.0,0.0,0.0)
                self.phase = 2

        # Drive
        if self.phase == 2:
            if ground_distance(self.car, vec3(0.0,0.0,0.0)) < 500:
                self.action = AirDodge(self.car, 0.1, vec3(0.0,0.0,0.0))
                self.phase = 3

        # Air Dodge
        if self.phase == 3:
            if self.action.finished:
                self.finished = True
        
        self.name = "SpeedFlipDodge Kickoff (" + str(self.phase) + ")"
        super().step(dt)