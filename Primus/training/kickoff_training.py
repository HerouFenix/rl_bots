from pathlib import Path

import rlbottraining.common_exercises.bronze_goalie as bronze_goalie
from rlbot.matchconfig.match_config import PlayerConfig, Team


def make_default_playlist():
    exercises = (
        bronze_goalie.make_default_playlist()
    )
    for exercise in exercises:
        exercise.match_config.player_configs = [
            PlayerConfig.bot_config(Path(__file__).absolute().parent.parent / 'src' / 'bot.cfg',
            Team.BLUE
            )
        ]
    return exercises
