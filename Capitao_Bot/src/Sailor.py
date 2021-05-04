from util.boost_pad_tracker import BoostPadTracker
from util.sequence import Sequence, ControlStep
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.logging_utils import get_logger

from rlbot.utils.structures.game_interface import GameInterface

class Sailor(BaseAgent):
    def __init__(self, index: int):
        super().__init__()
        self.index = index
        self.logger = get_logger(f'Ay ay! Sailor{index}')
        self.active_sequence: Sequence = None
        self.boost_pad_tracker = BoostPadTracker()

    def render_target(self, car_location, target_location):
        self.renderer.begin_rendering()

        self.renderer.draw_line_3d(car_locations, target_location, self.renderer.white())
        self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.cyan(), centered=True)
        
        self.renderer.end_rendering()
