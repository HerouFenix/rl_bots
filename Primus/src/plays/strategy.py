from util.game_info import GameInfo
from rlutilities.simulation import Car

from plays.kickoff.kickoff import SimpleKickoff

def choose_play(info: GameInfo, agent: Car):
    ball = info.ball
    teammates = info.get_teammates(agent)
    team = teammates + [agent] # Team is composed of teammates plus agent

    if ball.position[0] == 0 and ball.position[1] == 0: # If ball is at the center, then kickoff
        return pick_kickoff(info, agent)

    return  None


def pick_kickoff(info: GameInfo, agent: Car):
    return SimpleKickoff(info, car)