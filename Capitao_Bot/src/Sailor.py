from rlbot.utils.logging_utils import get_logger

from rlbot.utils.structures.bot_input_struct import PlayerInput


class Sailor:
    """
        Every car in the Captn Bot Team will be a Sailor. A sailor holds its index and current plan.
        The current plan is often gonna be used to fetch input.
    """
    def __init__(self, index: int):
        self.index = index
        self.logger = get_logger(f'Ay ay! Sailor{index}')
        self.controls = PlayerInput()
        self.plan = None

    def get_input(self) -> PlayerInput:
        player_input = PlayerInput()
        player_input.throttle = self.controls.throttle
        player_input.steer = self.controls.steer
        player_input.pitch = self.controls.pitch
        player_input.yaw = self.controls.yaw
        player_input.roll = self.controls.roll
        player_input.jump = self.controls.jump
        player_input.boost = self.controls.boost
        player_input.handbrake = self.controls.handbrake
        return player_input