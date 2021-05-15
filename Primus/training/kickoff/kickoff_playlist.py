import kickoff_training
import rlbottraining.common_exercises.kickoff_exercise as kickoff_exercise

def make_default_playlist():
    exercises = (
        kickoff_exercise.make_default_playlist()
    )
    for exercise in exercises:
        exercise.match_config = kickoff_training.make_match_config_with_my_bot()

    return exercises
