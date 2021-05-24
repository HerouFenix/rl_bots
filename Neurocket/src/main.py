import rlgym
from obs import CustomObsBuilder
from reward import CustomReward
from agent import Agent

PLAY = False

REPEAT_ACTIONS = 5
EPISODES = 100
TEAM_SIZE = 2
LR = 0.0005
GAMMA = 0.99

# Options: Duel, Doubles, Standard
GAME_MODE = "Duel"

env = rlgym.make(GAME_MODE + "Self", obs_builder=CustomObsBuilder(), reward_fn=CustomReward())

agent = Agent(alpha=LR, gamma=GAMMA, n_actions=2**env.action_space.shape[0],
              epsilon = 0.01, batch_size=64, input_dims=env.observation_space.shape[0], fname="./save/" + GAME_MODE + "_model.h5")

try:
    agent.load_model()
except Exception as e:
    print("There may not exist a model for this game mode")
    if PLAY:
        raise e

if PLAY:
    observation = env.reset()
    done = False
    while not done:
        outActions = []
        for obs in observation:
            o, _ = agent.choose_action(obs)
            outActions.append(o)
        
        for i in range(REPEAT_ACTIONS): # Repeat same actions for REPEAT_ACTIONS steps to limit stutter
            observation_, reward, done, gameinfo = env.step(outActions)
            observation = observation_
else:
    for i in range(EPISODES):
        observation = env.reset()
        done = False
        cnt = 1
        while not done:
            outActions = []
            actions = []
            for obs in observation:
                o, a = agent.choose_action(obs)
                outActions.append(o)
                actions.append(a)
            observation_, reward, done, gameinfo = env.step(outActions)
            for j, obs in enumerate(observation_):
                agent.remember(observation[j], actions[j], reward[j], observation_[j], int(done))
                agent.learn()
            observation = observation_
            if cnt % 10_000 == 0:
                print("Saving...")
                agent.save_model()
        print("Saving...")
        agent.save_model()
        print("Episode %d/%d" % (i, EPISODES))
    agent.save_model()
