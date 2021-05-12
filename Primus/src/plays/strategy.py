from util.game_info import GameInfo
from rlutilities.simulation import Car

from plays.play import Play
from plays.actions.drive import Drive, Stop, AdvancedDrive, Arrive
from plays.kickoff.kickoff import SimpleKickoff, SpeedFlipDodgeKickoff
from plays.strikes.strike import Strike, DodgeStrike, BumpStrike, CloseStrike, SetupStrike, DribbleStrike
from plays.strikes.aerial import AerialStrike, DoubleAerialStrike
from plays.dribbles.dribble import Dribble
from plays.defense.defense import Defense
from plays.defense.clear import BumpClear, DodgeClear, AerialClear
from plays.actions.jump import Jump, AirDodge, SpeedFlip, HalfFlip, AimDodge
from plays.utility.recovery import Recovery
from plays.utility.refuel import Refuel

from util.intercept import Intercept
from util.math import align, ground_distance, ground, distance 

def choose_play(state, agent):
    # First check if there's a car coming towards us and double jump to avoid it
    collisions = state.detect_collisions_with_agent(agent, 0.2, 1 / 60)
    if(len(collisions) > 0):
        return AirDodge(agent, 0.2)
    
    # First priority is to recover if airborne
    if not agent.on_ground:
        return Recovery(agent)    

    ball = state.ball
    teammates = state.get_teammates(agent)
    team = teammates + [agent] # Team is composed of teammates plus agent
    
    # Kickoffs
    if ball.position[0] == 0 and ball.position[1] == 0: # If ball is at the center, then kickoff
        # If nearest to the ball amongst all teammates, kickoff
        nearest_to_kickoff = min(team, key=lambda car: distance(car, ball))
        if nearest_to_kickoff is agent:
            return pick_kickoff(state, agent)
    
    # If low on boost go refuel
    if agent.boost < 20:
        return Refuel(agent, state)

    # Update ball predictions
    state.predict_ball()

    # Compute all possible intercepts
    agent_intercept = Intercept(agent, state.ball_predictions)
    team_intercepts = [Intercept(teammate, state.ball_predictions) for teammate in teammates] + [agent_intercept]

    net = ground(state.net.center)
    enemy_net = ground(state.enemy_net.center)

    # Good intercepts are those that shoot the ball towards the enemy net
    good_intercepts = [intercept for intercept in team_intercepts if align(intercept.car.position, intercept.ball, enemy_net) > 0.0]
    if len(good_intercepts) > 0:
        best_intercept = min(good_intercepts, key=lambda intercept: intercept.time)
    else:
        best_intercept = min(team_intercepts, key=lambda intercept: intercept.time)
    
    # If the best intercept is ours
    if best_intercept is agent_intercept:
        # If not out of position, go for the goal
        if(
            align(agent_intercept.car.position, agent_intercept.ball, enemy_net) > 0
            or ground_distance(agent_intercept, net) > 6000
        ):
            return pick_strike(state, agent, enemy_net, agent_intercept)

        # If out of position, just clear
        else:
            return pick_clear(state, agent)
    
    # If nearest goal, stay back but face the target
    if min(team, key=lambda car: distance(car, net) is agent):
        return Defense(agent, state, agent_intercept.position, 7000)

    # Else, just move into position to prepare for the intercept
    return Defense(agent, state, agent_intercept.position, 1000)


def pick_kickoff(state, agent):
    if abs(agent.position[0]) > 1000:
        return SpeedFlipDodgeKickoff(agent, state)
    return SimpleKickoff(agent, state)


def is_opponent_close(state, dist):
    for opponent in state.get_opponents():
        if ground_distance(opponent.position + opponent.velocity * 0.5, state.ball) < dist:
            return True
    return False

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
    
    return direct_shot


def pick_clear(state, agent):
    clear = DodgeClear(agent, state)
    
    # Aerial Clear
    if agent.boost > 40:
        clear = min([clear, AerialClear(agent, state)], key=lambda clear: clear.intercept.time)

    return clear
