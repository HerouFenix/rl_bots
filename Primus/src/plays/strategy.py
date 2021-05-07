from util.game_info import GameInfo
from rlutilities.simulation import Car

from plays.play import Play
from plays.actions.drive import Drive, Stop
from plays.kickoff.kickoff import SimpleKickoff, SpeedFlipDodgeKickoff
from plays.actions.jump import Jump, AirDodge

def choose_play(state: GameInfo, agent: Car):
    ball = state.ball
    teammates = state.get_teammates(agent)
    team = teammates + [agent] # Team is composed of teammates plus agent

    if ball.position[0] == 0 and ball.position[1] == 0: # If ball is at the center, then kickoff
        return pick_kickoff(state, agent)

    return  Stop(agent)


def pick_kickoff(state: GameInfo, agent: Car):
    if abs(agent.position[0]) > 1000:
        return SpeedFlipDodgeKickoff(agent, state)
    return SimpleKickoff(agent, state)