import deffense_training
import rlbottraining.common_exercises.bronze_goalie as bronze_goalie
import rlbottraining.common_exercises.silver_goalie as silver_goalie

def make_default_playlist():
    exercises = (
        #hello_world_training.make_default_playlist() +
        silver_goalie.make_default_playlist() + bronze_goalie.make_default_playlist()
    )
    for exercise in exercises:
        exercise.match_config = deffense_training.make_match_config_with_my_bot()

    return exercises
