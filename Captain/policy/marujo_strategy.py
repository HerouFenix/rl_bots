from util.game_info import GameInfo
from rlutilities.simulation import Car
from rlutilities.linear_algebra import vec3

from policy.macros import KICKOFF, ATTACK, DEFENSE, BOOST, CLEAR, PREEMPTIVE_DEF
from policy.picker import pick_kickoff, pick_clear, pick_strike

from plays.kickoff.kickoff import SimpleKickoff, SpeedFlipDodgeKickoff
from plays.strikes.strike import DodgeStrike, BumpStrike, CloseStrike, SetupStrike, DribbleStrike
from plays.strikes.aerial import AerialStrike, DoubleAerialStrike
from plays.defense.defense import Defense, GoToNet
from plays.defense.clear import DodgeClear, AerialClear
from plays.utility.recovery import Recovery
from plays.utility.refuel import Refuel

from util.intercept import Intercept
from util.math import align, ground_distance, ground, distance


def choose_action(info: GameInfo, my_car: Car, stance):
    ball = info.ball
    their_goal = ground(info.enemy_net.center)
    my_goal = ground(info.net.center)

    # recovery
    if not my_car.on_ground:
        return Recovery(my_car)

    # kickoff
    if stance == KICKOFF:
        return pick_kickoff(info, my_car)

    info.predict_ball()

    my_intercept = Intercept(my_car, info.ball_predictions)

    banned_boostpads = {pad for pad in info.large_boost_pads if
                        abs(pad.position[1] - their_goal[1]) < abs(my_intercept.position[1] - their_goal[1])
                        or abs(pad.position[0] - my_car.position[0]) > 6000}


    ball_in_their_half = abs(my_intercept.position[1] - their_goal[1]) < 3000
    shadow_distance = 4000 if ball_in_their_half else 6000

    if stance == BOOST:
        return Refuel(my_car, info, forbidden_pads=banned_boostpads)

    if stance == ATTACK:
        return pick_strike(info, my_intercept.car, their_goal, my_intercept)

    if stance == CLEAR:
        return pick_clear(info, my_intercept.car)

    if stance == PREEMPTIVE_DEF:
        return Defense(my_car, info, my_intercept.position, shadow_distance, force_nearest=ball_in_their_half)

    if stance == DEFENSE:
        if ground_distance(ball, my_goal) < 1000:
            return pick_strike(info, my_intercept.car, their_goal, my_intercept)

        return Defense(my_car, info, my_intercept.position, 7000)

    return Defense(my_car, info, my_intercept.position, 4000)

def danger(info, my_car):

    info.predict_ball()
    my_intercept = Intercept(my_car, info.ball_predictions)
    their_goal = ground(info.enemy_net.center)
    my_goal = ground(info.net.center)

    if (
        ground_distance(my_intercept, my_goal) < 3000
        and (abs(my_intercept.position[0]) < 2000 or abs(my_intercept.position[1]) < 4500)
        and my_car.position[2] < 300
    ):
        if align(my_car.position, my_intercept.ball, their_goal) > 0.5:
            return [ATTACK]

        return [CLEAR]

    return []
