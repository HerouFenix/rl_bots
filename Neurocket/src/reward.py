from rlgym.utils.gamestates import GameState
from rlgym.utils.gamestates import PlayerData
from rlgym.utils.reward_functions import RewardFunction
from rlgym.utils import common_values
import numpy as np

class CustomReward(RewardFunction):
    def __init__(self):
        self.players = {}

    def reset(self, initial_state: GameState):
        self.players = { p.car_id: (initial_state, p) for p in initial_state.players }

    def get_reward(self, player: PlayerData, state: GameState, previous_action: np.ndarray) -> float:
        (last_state, last_player) = self.players[player.car_id]

        reward = 0
        if last_state is not None:
            prev_score_diff = last_state.blue_score - last_state.orange_score if player.team_num == common_values.BLUE_TEAM else last_state.orange_score - last_state.blue_score
            curr_score_diff = state.blue_score - state.orange_score if player.team_num == common_values.BLUE_TEAM else state.orange_score - state.blue_score
            # if team has scored
            if curr_score_diff > prev_score_diff:
                reward = 1000
            elif curr_score_diff < prev_score_diff:
                reward = -1000
            # if scored
            elif player.match_goals > last_player.match_goals:
                reward = 200
            # if saved
            elif player.match_saves > last_player.match_saves:
                reward = 100
            # if shot
            elif player.match_shots > last_player.match_shots:
                reward = 50

        self.players[player.car_id] = (state, player)
        return reward
    
    def get_final_reward(self, player: PlayerData, state: GameState, previous_action: np.ndarray) -> float:
        return 0
