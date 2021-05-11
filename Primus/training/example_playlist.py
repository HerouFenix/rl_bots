import hello_world_training
import rlbottraining.common_exercises.silver_striker as silver_striker

def make_default_playlist():
    exercises = (
        #hello_world_training.make_default_playlist() +
        silver_striker.make_default_playlist()
    )
    for exercise in exercises:
        exercise.match_config = hello_world_training.make_match_config_with_my_bot()

    return exercises
