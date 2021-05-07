from rlutilities.simulation import Car
from plays.play import Play
from util.game_info import GameInfo

class Kickoff(Play):
    """
    Base kickoff class.
    Kickoffs are based on phases (f.ex - drive -> flip -> drive)
    """
    def __init__(self, info: GameInfo, agent: Car):
        super().__init__(agent)

        self.info = info

        self.drive = Drive(car, target_speed = 2300)
        self.action = self.drive
        self.phase = 0

        self.name = "KickOff"


    def step(self, dt: float):        
        self.action.step(dt) # Next step of the current action
        self.controls = self.action.controls


class Kickoff(Play):
    """
    Simple kickoff
    Drive towards ball, dodge at the middle and end
    """