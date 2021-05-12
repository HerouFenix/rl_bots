import aerial_training
import rlbottraining.common_exercises.silver_striker as silver_striker

def make_default_playlist():
    exercises = (
        aerial_training.make_default_playlist() 
        #silver_striker.make_default_playlist()
    )
    for exercise in exercises:
        exercise.match_config = aerial_training.make_match_config_with_my_bot()

    return exercises
