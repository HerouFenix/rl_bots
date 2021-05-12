from pathlib import Path
from dataclasses import dataclass, field
from math import pi
import random

from rlbot.utils.game_state_util import GameState, BoostState, BallState, CarState, Physics, Vector3, Rotator
from rlbot.matchconfig.match_config import MatchConfig, PlayerConfig, Team
from rlbottraining.common_exercises.common_base_exercises import StrikerExercise
from rlbottraining.common_graders.goal_grader import StrikerGrader
from rlbottraining.rng import SeededRandomNumberGenerator
from rlbottraining.match_configs import make_empty_match_config
from rlbottraining.grading.grader import Grader
from rlbottraining.training_exercise import TrainingExercise, Playlist

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
class AerialExercise(StrikerExercise):
    """
    Spawns the ball in the air
    """
    grader: Grader = StrikerGrader(timeout_seconds = 7.0)

    def make_game_state(self, rng: SeededRandomNumberGenerator) -> GameState:
        random_start_pos = [
            (Vector3(-2048, -2560, 18), Rotator(0, 0.25*pi, 0)),
            (Vector3(0, -4608, 18), Rotator(0, 0.5*pi, 0)),
            (Vector3(256.0, -3840, 18), Rotator(0, 0.5*pi, 0)),
            (Vector3(-256, -3840, 18), Rotator(0, 0.5*pi, 0)),
            (Vector3(2048, -2560, 18), Rotator(0, 0.75*pi, 0))
        ]

        start_pos = random.choice(random_start_pos)

        ball_y = random.randint(-1250,3000)
        ball_x = random.randint(-1250, 1250)

        random_ball = [
            (Vector3(ball_x, ball_y, 5000), Vector3(0, 0, -50)),
            (Vector3(ball_x, ball_y, 0), Vector3(0, 0, 2000)),
        ]

        ball_pos = random.choice(random_ball)

        return GameState(
            ball=BallState(physics=Physics(
                location=ball_pos[0],
                velocity=ball_pos[1],
                angular_velocity=Vector3(0, 0, 0))),
            cars={
                0: CarState(
                    physics=Physics(
                        location=start_pos[0],
                        rotation=start_pos[1],
                        velocity=Vector3(0, 0, 0),
                        angular_velocity=Vector3(0, 0, 0)),
                    jumped=False,
                    double_jumped=False,
                    boost_amount=100)
            },
            boosts={i: BoostState(0) for i in range(34)},
        )


def make_default_playlist() -> Playlist:
    exercises = [
        AerialExercise('Fly and hit ball'),
    ]
    return add_my_bot_to_playlist(exercises)
