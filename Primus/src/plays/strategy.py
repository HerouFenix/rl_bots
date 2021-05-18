from util.game_info import GameInfo
from rlutilities.simulation import Car
from rlutilities.linear_algebra import vec3

from plays.play import Play
from plays.actions.drive import Drive, Stop, AdvancedDrive, Arrive
from plays.kickoff.kickoff import SimpleKickoff, SpeedFlipDodgeKickoff
from plays.strikes.strike import Strike, DodgeStrike, BumpStrike, CloseStrike, SetupStrike, DribbleStrike
from plays.strikes.aerial import AerialStrike, DoubleAerialStrike
from plays.dribbles.dribble import Dribble
from plays.defense.defense import Defense, GoToNet
from plays.defense.clear import BumpClear, DodgeClear, AerialClear
from plays.actions.jump import Jump, AirDodge, SpeedFlip, HalfFlip, AimDodge
from plays.utility.recovery import Recovery
from plays.utility.refuel import Refuel

from util.intercept import Intercept
from util.math import align, ground_distance, ground, distance 

def choose_play(state, agent):
    # First priority is to recover if airborne
    if not agent.on_ground:
        return (Recovery(agent), "Landing")   

    ball = state.ball
    teammates = state.get_teammates(agent)
    team = teammates + [agent] # Team is composed of teammates plus agent

    # Arrays should be sorted by agent id, this way it'll be the same for all team agents
    team.sort(key=lambda car: car.id)
    
    # Kickoffs
    if ball.position[0] == 0 and ball.position[1] == 0: # If ball is at the center, then kickoff
        # If nearest to the ball amongst all teammates, kickoff

        #nearest_to_kickoff = min(team, key=lambda car: distance(car, ball)) # Causes problems when 2 are equally close
        furthest_car = team[0] 
        closest_car = team[0] 
        furthest_car_2 = None
        closest_car_2 = None

        furthest_dist = distance(team[0], ball.position)
        closest_dist = distance(team[0], ball.position) 
        furthest_dist_2 = None
        closest_dist_2 = None 

        for car in team[1:]:   
            cur_dist = distance(car, ball.position)  
            
            if cur_dist < closest_dist:
                closest_car = car
                closest_dist = cur_dist
            elif cur_dist == closest_dist:
                if car.id < closest_car.id:
                    closest_car_2 = closest_car
                    closest_car = car

                    closest_dist_2 = cur_dist
                else:
                    closest_car_2 = car
                    closest_dist_2 = cur_dist

            if cur_dist > furthest_dist:
                furthest_car = car
                furthest_dist = cur_dist
            elif cur_dist == furthest_dist:
                if car.id < furthest_car.id:
                    furthest_car_2 = furthest_car
                    furthest_car = car

                    furthest_dist_2 = cur_dist
                else:
                    furthest_car_2 = car
                    furthest_dist_2 = cur_dist

        if closest_dist != closest_dist_2:
            closest_car_2 == None
        
        if furthest_dist != furthest_dist_2:
            furthest_car_2 == None

        if distance(furthest_car.position,vec3(-256.000000, -3840.000000, 17.049999)) < 100:
            temp = furthest_car
            furthest_car = furthest_car_2
            furthest_car_2 = temp

        if closest_car is agent:
            return (pick_kickoff(state, agent), "Going for Kickoff")
        elif closest_car_2 is agent:
            return (Refuel(agent, state), "Refueling at Kickoff") # If 2 cars are tied for kickoff, one should go get boost
        else:
            if(agent is not furthest_car_2 and agent.boost <= 35): # To avoid when 2 cars are equally far apart and try to go for the same boost
                return (Refuel(agent, state, small_refuel=True), "Small Refueling at Kickoff")

    #return (Stop(agent), "Doing nothing")
    
    # If low on boost go refuel
    if agent.boost < 20:
        return (Refuel(agent, state), "Refueling")

    # Update ball predictions
    state.predict_ball()

    # Compute all possible intercepts

    team_intercepts = []
    agent_intercept = None
    for car in team:
        intercept = Intercept(car, state.ball_predictions)
        team_intercepts.append(intercept)

        if(car is agent):
            agent_intercept = intercept

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
            return (pick_strike(state, agent, enemy_net, agent_intercept), "Striking")

        # If out of position, just clear
        else:
            return (pick_clear(state, agent), "Clearing")
    

    ###### DEFENSE AND SETUP ######

    # Check how many enemies are in our side of the field
    enemies_in_side = 0
    for opponent in state.get_opponents():
        if state.team == 0:
            if opponent.position[1] < 0:
                enemies_in_side += 1
        else:
            if opponent.position[1] > 0:
                enemies_in_side += 1
                
            
    # Check how many teammates are in our side of the field
    teammates_in_side = 0
    min_dist_to_net = distance(teammates[0], net)
    for teammate in teammates:
        cur_dist = distance(teammate, net)
        if cur_dist < min_dist_to_net:
            min_dist_to_net = cur_dist
        if state.team == 0:
            if teammate.position[1] < 0:
                teammates_in_side += 1
        else:
            if teammate.position[1] > 0:
                teammates_in_side += 1
    
    # If nearest goal
    if min(team, key=lambda car: distance(car, net) is agent):
        # If there's danger, CLEAR!
        danger = False
        for prediction in state.ball_predictions:
            if state.net.check_inside(prediction.position):
                danger = True
                break
        
        # if (danger or ground_distance(state.ball, net) < 800): # If ball is close to net, and no one else is close to the net, do your best to clear it
        #     return (pick_clear(state, agent), "Danger Clearing")

        
        # Go to net and prepare if too many enemies are on our side of the field or no teammates are in our side or if no other teammate is near then et
        if enemies_in_side >= 2 or teammates_in_side < 1 or ((enemies_in_side > 0 or state.ball.position[1] < 0 if agent.team == 0 else state.ball.position[1] > 0) and min_dist_to_net > 800):
            return (GoToNet(agent, state, state.ball.position), "Waiting at Net")
        

        # Stay back and face ball
        return (Defense(agent, state, agent_intercept.position, 7000), "Waiting for opportunity (Defensive)")

    # Else, just move into position to prepare for the intercept
    return (Defense(agent, state, agent_intercept.position, 1000), "Waiting for opportunity")
    """
    """

    


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
    
    # Check if a teammate's intercept would be better, if so, pass it to them

    return direct_shot


def pick_clear(state, agent):
    clear = DodgeClear(agent, state)
    
    # Aerial Clear
    if agent.boost > 40:
        clear = min([clear, AerialClear(agent, state)], key=lambda clear: clear.intercept.time)

    return clear
