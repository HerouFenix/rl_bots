from action.general_defense import GeneralDefense
from action.recovery import Recovery
from action.refuel import Refuel
from action.strikes.strike import Strike
from rlutilities.linear_algebra import dot
from rlutilities.simulation import Car
from policy import offense, defense, kickoffs
from tools.game_info import GameInfo
from tools.intercept import Intercept
from tools.math import sign
from tools.vector_math import align, ground, ground_distance, ground_direction, distance

from policy.macros import ACK, KICKOFF, GEN_DEFEND, CLUTCH_DEFEND, BALL, RECOVERY, ATTACK, DEFENSE, BOOST, CLEAR


def choose_stance(info: GameInfo, my_car: Car, team):
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
    teammates_intercepts = [Intercept(mate, info.ball_predictions) for mate in teammates]
    our_intercepts = {index: Intercept(info.cars[index], info.ball_predictions) for index in team}

    good_intercepts = [our_intercepts[i] for i in our_intercepts if align(our_intercepts[i].car.position, our_intercepts[i].ball, their_goal) > 0.0]
    if good_intercepts:
        best_intercept = min(good_intercepts, key=lambda intercept: intercept.time)
    else:
        best_intercept = min(our_intercepts.values(), key=lambda i: distance(i.car, my_goal))
        if ground_distance(my_car, my_goal) < 2000:
            best_intercept = my_intercept

    for inter in our_intercepts:
        if best_intercept == our_intercepts[inter]:
            # if not completely out of position, go for a shot
            if (
                align(best_intercept.car.position, best_intercept.ball, their_goal) > 0
                or ground_distance(best_intercept, my_goal) > 6000
            ):
                assigned_actions[inter] = ATTACK
                #return offense.any_shot(info, my_intercept.car, their_goal, my_intercept)

            # otherwise try to clear
            else:
                assigned_actions[inter] = CLEAR
                #return defense.any_clear(info, my_intercept.car)

    # Otherwise just assign them to defense / boost depending on whether the ball is
    for index in team:
        if assigned_actions[index] == None:
            if info.cars[index].boost < 30:
                assigned_actions[index] = BOOST

    for index in team:
        if assigned_actions[index] == None:
            assigned_actions[index] = DEFENSE

    return assigned_actions

    ##
    info.predict_ball()

    my_intercept = Intercept(my_car, info.ball_predictions)
    teammates_intercepts = [Intercept(mate, info.ball_predictions) for mate in teammates]
    our_intercepts = teammates_intercepts + [my_intercept]
    their_intercepts = [Intercept(opponent, info.ball_predictions) for opponent in opponents]
    their_intercept = min(their_intercepts, key=lambda i: i.time)
    opponent = their_intercept.car


    # if ball is in a dangerous position, clear it
    # TODO: if the ball is or is going to be in a dangerous position
    if (
        ground_distance(my_intercept, my_goal) < 3000
        and (abs(my_intercept.position[0]) < 2000 or abs(my_intercept.position[1]) < 4500)
        and my_car.position[2] < 300
    ):
        if align(my_car.position, my_intercept.ball, their_goal) > 0.5:
            return offense.any_shot(info, my_intercept.car, their_goal, my_intercept, allow_dribble=True)
        return defense.any_clear(info, my_intercept.car)

    # intercepting ball
    good_intercepts = [i for i in our_intercepts if align(i.car.position, i.ball, their_goal) > 0.0]
    if good_intercepts:
        best_intercept = min(good_intercepts, key=lambda intercept: intercept.time)
    else:
        best_intercept = min(our_intercepts, key=lambda i: distance(i.car, my_goal))
        if ground_distance(my_car, my_goal) < 2000:
            best_intercept = my_intercept

    if best_intercept is my_intercept:
        # if not completely out of position, go for a shot
        if (
            align(my_intercept.car.position, my_intercept.ball, their_goal) > 0
            or ground_distance(my_intercept, my_goal) > 6000
        ):
            return offense.any_shot(info, my_intercept.car, their_goal, my_intercept)

        # otherwise try to clear
        else:
            return defense.any_clear(info, my_intercept.car)
    # else: tell the guy to intercept it


    # defense
    # if I'm nearest to goal, stay far back
    if min(my_team, key=lambda car: distance(car, my_goal)) is my_car:
        return GeneralDefense(my_car, info, my_intercept.position, 7000)


    # collecting boosts
    banned_boostpads = {pad for pad in info.large_boost_pads if
                        abs(pad.position[1] - their_goal[1]) < abs(my_intercept.position[1] - their_goal[1])
                        or abs(pad.position[0] - my_car.position[0]) > 6000}

    # if I'm low on boost and the ball is not near my goal, go for boost
    # TODO: if i'm near a boost, the ball is not near my goal and i'm low
    if my_car.boost < 10 and ground_distance(my_intercept, their_goal) > 3000:
        refuel = Refuel(my_car, info, forbidden_pads=banned_boostpads)
        if refuel.pad: return refuel

    ball_in_their_half = abs(my_intercept.position[1] - their_goal[1]) < 3000
    shadow_distance = 4000 if ball_in_their_half else 6000
    # if they can hit the ball sooner than me and they aren't out of position, wait in defense
    if (
        their_intercept.time < my_intercept.time
        and align(opponent.position, their_intercept.ball, my_goal) > -0.1 + opponent.boost / 100
        and ground_distance(opponent, their_intercept) > 300
        and dot(opponent.velocity, ground_direction(their_intercept, my_goal)) > 0
    ):
        return GeneralDefense(my_car, info, my_intercept.position, shadow_distance, force_nearest=ball_in_their_half)


    # shooting the ball
    # if not completely out of position, go for a shot
    if (
        align(my_car.position, my_intercept.ball, their_goal) > -0.5
        or ground_distance(my_intercept, their_goal) < 2000
        or ground_distance(opponent, their_intercept) < 300
    ):
        if my_car.position[2] < 300:
            shot = offense.any_shot(info, my_intercept.car, their_goal, my_intercept, allow_dribble=True)
            if (
                not isinstance(shot, Strike)
                or shot.intercept.time < their_intercept.time
                or abs(shot.intercept.position[0]) < 3500
            ):
                return shot


    # fallback strategies: collect boost and generic defense
    if my_car.boost < 30:
        refuel = Refuel(my_car, info, forbidden_pads=banned_boostpads)
        if refuel.pad: return refuel

    return GeneralDefense(my_car, info, my_intercept.position, shadow_distance, force_nearest=ball_in_their_half)

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
