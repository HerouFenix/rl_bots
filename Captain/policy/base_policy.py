from typing import List, Optional, Dict

from action.general_defense import GeneralDefense
from action.recovery import Recovery
from action.refuel import Refuel
from action.strikes.strike import Strike
from rlutilities.linear_algebra import dot, norm
from rlutilities.simulation import Car
from policy import offense, defense, kickoffs
from tools.game_info import GameInfo
from tools.intercept import Intercept
from tools.math import sign
from tools.vector_math import align, ground, ground_distance, ground_direction, distance

from policy.macros import ACK, KICKOFF, GEN_DEFEND, CLUTCH_DEFEND, BALL, RECOVERY, ATTACK, DEFENSE, BOOST, CLEAR, PREEMPTIVE_DEF


def choose_stance(info: GameInfo, my_car: Car, team, last_sent):
    """ High level assignment of "stances"
        Upon entering a stance, each Marujo is able to decide a few things to do
    """
    ball = info.ball
    teammates = info.get_teammates(my_car)
    my_team = [my_car] + teammates
    their_goal = ground(info.their_goal.center)
    my_goal = ground(info.my_goal.center)
    opponents = info.get_opponents()

    assigned_actions = {index: None for index in team}

    # Kickoff
    if ball.position[0] == 0 and ball.position[1] == 0:
        closest = min(distance(car, ball) for car in my_team)

        # Find nearest element to go for kickoff, every other one is assigned to general defense
        for index in team:
            if distance(info.cars[index], ball) == closest:
                assigned_actions[index] = KICKOFF
            else:
                assigned_actions[index] = DEFENSE

        return assigned_actions

    # Interceptions
    my_intercept = Intercept(my_car, info.ball_predictions)
    our_intercepts = {index: Intercept(info.cars[index], info.ball_predictions) for index in team}

    their_intercepts = [Intercept(opponent, info.ball_predictions) for opponent in opponents]
    their_intercept = min(their_intercepts, key=lambda i: i.time)
    opponent = their_intercept.car

    good_intercepts = [our_intercepts[i] for i in our_intercepts if align(our_intercepts[i].car.position, our_intercepts[i].ball, their_goal) > 0.0]
    if good_intercepts:
        best_intercept = min(good_intercepts, key=lambda intercept: intercept.time)
    else:
        best_intercept = min(our_intercepts.values(), key=lambda i: distance(i.car, my_goal))
        if ground_distance(my_car, my_goal) < 2000:
            best_intercept = my_intercept

    # if they can hit the ball sooner than me and they aren't out of position, wait in defense
    for inter in our_intercepts:
        if (
            their_intercept.time < our_intercepts[inter].time
            and align(opponent.position, their_intercept.ball, my_goal) > -0.1 + opponent.boost / 100
            and ground_distance(opponent, their_intercept) > 300
            and dot(opponent.velocity, ground_direction(their_intercept, my_goal)) > 0
        ):
            assigned_actions[inter] = PREEMPTIVE_DEF

    for inter in our_intercepts:
        if best_intercept == our_intercepts[inter]:
            # if not completely out of position, go for a shot
            if (
                align(best_intercept.car.position, best_intercept.ball, their_goal) > 0.1
                or ground_distance(best_intercept, my_goal) < 6000
                and ATTACK not in last_sent.values()
            ):
                assigned_actions[inter] = ATTACK

            # otherwise try to clear
            elif CLEAR not in last_sent.values():
                assigned_actions[inter] = CLEAR

    # Otherwise just assign them to defense / boost depending on whether the ball is
    for index in team:
        if assigned_actions[index] == None:
            if info.cars[index].boost < 20 and ground_distance(our_intercepts[inter], their_goal) < 3000:
                assigned_actions[index] = BOOST

    for index in team:
        if assigned_actions[index] == None:
            assigned_actions[index] = DEFENSE

    #avoid_demos_and_team_bumps(info, info.cars, assigned_actions)

    return assigned_actions

def general_defense(info, my_car, clutch=False):
    my_goal = ground(info.my_goal.center)
    their_goal = ground(info.their_goal.center)

    info.predict_ball()

    my_intercept = Intercept(my_car, info.ball_predictions)

    ball_in_their_half = abs(my_intercept.position[1] - their_goal[1]) < 3000
    shadow_distance = 4000 if ball_in_their_half else 6000

    if not clutch:
        return GeneralDefense(my_car, info, my_intercept.position, shadow_distance, force_nearest=ball_in_their_half)

    if (
        ground_distance(my_intercept, my_goal) < 3000
        and (abs(my_intercept.position[0]) < 2000 or abs(my_intercept.position[1]) < 4500)
        and my_car.position[2] < 300
    ):
        if align(my_car.position, my_intercept.ball, their_goal) > 0.5:
            return offense.any_shot(info, my_intercept.car, their_goal, my_intercept, allow_dribble=True)
        return defense.any_clear(info, my_intercept.car)

    return GeneralDefense(my_car, info, my_intercept.position, shadow_distance, force_nearest=ball_in_their_half)


## Not used yet
def avoid_demos_and_team_bumps(info, cars_by_index, assigned_actions):
    collisions = info.detect_collisions(time_limit=0.2, dt=1 / 60)

    for collision in collisions:
        index1, index2, time = collision

        # avoid team bumps
        if index1 in cars_by_index and index2 in cars_by_index:
            if assigned_actions[index1] in [CLEAR, ATTACK]:
                cars_by_index[index2].controls.jump = cars_by_index[index2].car.on_ground
            else:
                cars_by_index[index1].controls.jump = cars_by_index[index1].car.on_ground
            # TODO: if both drones aren't going for ball, decide which one is the better choice for jumping

        # dodge demolitions
        # TODO: Refactor so there's no duplicate code
        elif index1 in cars_by_index:
            opponent = info.cars[index2]
            if norm(opponent.velocity) > 2000:
                cars_by_index[index1].controls.jump = cars_by_index[index1].car.on_ground

        elif index2 in cars_by_index:
            opponent = info.cars[index1]
            if norm(opponent.velocity) > 2000:
                cars_by_index[index2].controls.jump = cars_by_index[index2].car.on_ground   
