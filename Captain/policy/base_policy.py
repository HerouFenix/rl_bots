import math
from typing import Callable

from action.collect_boost.collect_boost import CollectBoost
from action.kickoff.kickoff import Kickoff

from util.generator_utils import initialize_generator

class BasePolicy:
    """ This is where the agent will pick his actions and decide the strategy to follow.
        This is the highest level of abstraction in the project:
            Should return an action, an action returns a mechanic, and mechanics return controls.
        The policy always refers to a Capitao, since it is also an action to assign other actions.
    """
    def __init__(self, agent, rendering_enabled=False):
        self.agent = agent
        self.kickoff_action = Kickoff(agent, rendering_enabled)
        self.action_loop = self.create_action_loop()

    def get_controls(self, game_data):
        return self.get_action(game_data).get_controls(game_data)

    def get_action(self, game_data):
        ball_loc = game_data.ball.location
        kickoff = math.sqrt(ball_loc[0] ** 2 + ball_loc[1] ** 2) < 1

        if kickoff:
            # reset the action loop
            self.action_loop = self.create_action_loop()
            return self.kickoff_action
        else:
            return self.action_loop.send(game_data)

    @initialize_generator
    def create_action_loop(self):
        game_data = yield

        while True:
            # choose action to do
            action = CollectBoost(self.agent)

            # use action until it is finished
            while not action.finished and not action.failed:
                game_data = yield action