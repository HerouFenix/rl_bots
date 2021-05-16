from plays.kickoff.kickoff import SimpleKickoff, SpeedFlipDodgeKickoff
from plays.strikes.strike import DodgeStrike, BumpStrike, CloseStrike, SetupStrike, DribbleStrike
from plays.strikes.aerial import AerialStrike, DoubleAerialStrike
from plays.defense.clear import DodgeClear, AerialClear

from util.math import align, ground_distance, ground, distance 

def pick_kickoff(state, agent):
    if abs(agent.position[0]) > 1000:
        return SpeedFlipDodgeKickoff(agent, state)
    return SimpleKickoff(agent, state)

def pick_strike(state, agent, target, intercept):
    ball = intercept.ball

    # Dribble and Flick
    if(
        (ball.position[2] > 100 or abs(ball.velocity[2]) > 250 or distance(agent, state.ball) < 300)
        and abs(ball.velocity[2]) < 700
        and ground_distance(agent, ball) < 1500
        and ground_distance(ball, state.net.center) > 1000
        and ground_distance(ball, state.enemy_net.center) > 1000
        and not is_opponent_close(state, state.ball.position[2] * 2 + 1000)
    ):
        return DribbleStrike(agent, state, target)

    direct_shot = None

    # Dodge Shot
    dodge_strike = DodgeStrike(agent, state, target)

    # Bump Shot
    bump_strike = BumpStrike(agent, state, target)

    # Aerial
    if agent.boost > 40:
        aerial_strike = AerialStrike(agent, state, target)

        if(
            aerial_strike.intercept.time < dodge_strike.intercept.time
            and abs(aerial_strike.intercept.position[1] - state.enemy_net.center[1]) > 500
        ):
            # Double Aerial Strike
            if ground_distance(aerial_strike.intercept, state.enemy_net.center) < 8000:
                direct_shot = DoubleAerialStrike(aerial_strike)
            else:
                direct_shot = aerial_strike

    if direct_shot is None:
        if(
            dodge_strike.intercept.time < bump_strike.intercept.time - 0.1
            or ground_distance(dodge_strike.intercept, target)< 2000
            or distance(bump_strike.intercept.ball.velocity, agent.velocity) < 500
            or is_opponent_close(state, 300)
        ):
            # Close Strike
            if(
                distance(dodge_strike.intercept.ground_pos, target) < 4000
                and abs(dodge_strike.intercept.ground_pos[0]) < 2000
            ):
                direct_shot = CloseStrike(agent, state, target)
            else:
                direct_shot = dodge_strike
        else:
            direct_shot = bump_strike

    # Check whether we should do a setup strike instead (if alignment is too far off, distance is too far and intercept will take too long)
    if not isinstance(direct_shot, BumpStrike) and intercept.time < agent.time + 4.0:
        alignment = align(agent.position, ball, target)
        if alignment < -0.3 and abs(ball.position[1] - target[1]) > 3000:
            return SetupStrike(agent, state, target)
    
    # Check if a teammate's intercept would be better, if so, pass it to them

    return direct_shot

def pick_clear(state, agent):
    clear = DodgeClear(agent, state)
    
    # Aerial Clear
    if agent.boost > 40:
        clear = min([clear, AerialClear(agent, state)], key=lambda clear: clear.intercept.time)

    return clear

def is_opponent_close(state, dist):
    for opponent in state.get_opponents():
        if ground_distance(opponent.position + opponent.velocity * 0.5, state.ball) < dist:
            return True
    return False