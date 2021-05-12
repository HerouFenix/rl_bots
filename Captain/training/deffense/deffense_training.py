from pathlib import Path
from dataclasses import dataclass, field
from math import pi

from rlbot.utils.game_state_util import GameState, BoostState, BallState, CarState, Physics, Vector3, Rotator
from rlbot.matchconfig.match_config import MatchConfig, PlayerConfig, Team
from rlbottraining.common_exercises.common_base_exercises import StrikerExercise, GoalieExercise
from rlbottraining.rng import SeededRandomNumberGenerator
from rlbottraining.match_configs import make_empty_match_config
from rlbottraining.grading.grader import Grader
from rlbottraining.training_exercise import TrainingExercise, Playlist

from rlbottraining.common_graders.goal_grader import StrikerGrader

import training_util


def make_match_config_with_my_bot() -> MatchConfig:
    # Makes a config which only has our bot in it for now.
    # For more details: https://youtu.be/uGFmOZCpel8?t=375
    match_config = make_empty_match_config()
    match_config.player_configs = [
        PlayerConfig.bot_config(
            Path(__file__).absolute().parent.parent.parent  / 'src' / 'bot.cfg',
            Team.BLUE
        ),
    ]
    return match_config


def add_my_bot_to_playlist(exercises: Playlist) -> Playlist:
    """
    Updates the match config for each excercise to include
    the bot from this project
    """
    for exercise in exercises:
        exercise.match_config = make_match_config_with_my_bot()
    return exercises


@dataclass
class AerialDefense(TrainingExercise):
    grader: Grader = StrikerGrader(timeout_seconds = 10.0)

    def make_game_state(self, rng: SeededRandomNumberGenerator) -> GameState:
        return GameState(
            ball=BallState(physics=Physics(
                location=Vector3(0, 1000, 3000),
                velocity=Vector3(0, -500, 0),
                angular_velocity=Vector3(0, 0, 0))),
            cars={
                0: CarState(
                    physics=Physics(
                        location=Vector3(0, -4608, 18),
                        rotation=Rotator(0, 0.5*pi, 0),
                        velocity=Vector3(0, 0, 0),
                        angular_velocity=Vector3(0, 0, 0)),
                    boost_amount=100)
            },
            boosts={i: BoostState(0) for i in range(34)},
        )


def make_default_playlist() -> Playlist:
    exercises = [
        AerialDefense("Aerial Defense")
    ]
    return add_my_bot_to_playlist(exercises)
