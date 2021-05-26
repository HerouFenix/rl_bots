import numpy as np
from tensorflow.keras.models import load_model
from agent import mapAction

class PlayingAgent:
    def __init__(self, fname='./save/dqn_model.h5'):
        self.model_file = fname
        self.load_model()
        
    def choose_action(self, state):
        state = state[np.newaxis, :]
        
        actions = self.q_eval.predict(state)
        action = np.argmax(actions)

        return mapAction(action), action

    def load_model(self):
        self.q_eval = load_model(self.model_file)