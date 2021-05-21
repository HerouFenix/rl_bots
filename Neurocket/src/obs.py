from rlgym.utils.obs_builders import ObsBuilder
from rlgym.utils.gamestates import GameState
from rlgym.utils.gamestates import PlayerData
from rlgym.utils import common_values
import numpy as np

class CustomObsBuilder(ObsBuilder):
    def reset(self, initial_state: GameState):
        pass

    def build_obs(self, player: PlayerData, state: GameState, previous_action: np.ndarray):
        obs = []
        tm8s = []
        opponents = []

        for player_other in state.players:
            if player.car_id != player_other.car_id:
                if player_other.team_num == player.team_num:
                    tm8s.append(player_other)
                else:
                    opponents.append(player_other)

        # Mirror states in relation to team
        if player.team_num == common_values.BLUE_TEAM:
            obs += state.ball.serialize()
            obs += player.car_data.serialize()
            for pl in tm8s:
                obs += pl.car_data.serialize()
            for pl in opponents:
                obs += pl.car_data.serialize()
        else:
            obs += state.inverted_ball.serialize()
            obs += player.inverted_car_data.serialize()
            for pl in tm8s:
                obs += pl.inverted_car_data.serialize()
            for pl in opponents:
                obs += pl.inverted_car_data.serialize()

        return np.asarray(obs, dtype=np.float32)
