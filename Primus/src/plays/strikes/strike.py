import math

from plays.actions.drive import Arrive, Drive
from plays.actions.jump import AimDodge
from plays.dribbles.dribble import Dribble

from plays.play import Play

from rlutilities.mechanics import Dodge
from rlutilities.linear_algebra import vec3, dot, norm, normalize, xy
from rlutilities.simulation import Car, Ball, Field, sphere

from util.game_info import GameInfo
from util.intercept import Intercept
from util.math import distance, ground_distance, clamp, ground_direction, abs_clamp

class Strike(Play):
    """
    Baseline Strike class. Encompasses everything that involves the agent moving towards the ball and hitting it
    """
    ALLOW_BACKWARDS = False
    UPDATE_INTERVAL = 0.2
    STOP_UPDATING = 0.1
    MAX_ADDITIONAL_TIME = 0.4

    def __init__(self, agent, state, target):
        super().__init__(agent)

        self.state = state
        self.target = target # Corresponds to where we want the ball the go to

        self.arrive = Arrive(agent)
        self.intercept = None

        # Control variables
        self.last_update_time = agent.time
        self.should_strike_backwards = False
        self.initial_time = math.inf

        self.update_intercept()

        self.initial_time = self.intercept.time

        self.name = "Strike"

    def interruptible(self):
        return self.arrive.interruptible()

    def configure(self, intercept):
        # Configure the movement settings for the strike such as the Arrive settings and the Target
        self.arrive.target = intercept.ground_pos
        self.arrive.arrival_time = intercept.time
        self.arrive.backwards = self.should_strike_backwards

    def intercept_predicate(self, car, ball):
        # This basically returns whether Primus should move to intercept or stay put
        return True

    def update_intercept(self):
        # Update Intercept class based on the updated ball predictions
        self.intercept = Intercept(self.car, self.state.ball_predictions, self.intercept_predicate)

        if self.ALLOW_BACKWARDS:
            backwards_intercept = Intercept(self.car, self.state.ball_predictions, self.intercept_predicate,
                                            backwards=True)
            if backwards_intercept.time + 0.1 < self.intercept.time:
                self.intercept = backwards_intercept
                self.should_strike_backwards = True
            else:
                self.should_strike_backwards = False

        self.configure(self.intercept)
        self.last_update_time = self.car.time
        if not self.intercept.is_viable or self.intercept.time > self.initial_time + self.MAX_ADDITIONAL_TIME:
            self.finished = True

    def pick_easiest_target(self, car, ball, targets):
        # Pick the easiest target (i.e where which target is easiest to throw the ball to)
        
        to_goal = ground_direction(ball, self.state.enemy_net.center)
        return max(targets, key=lambda target: dot(ground_direction(car, ball) + to_goal * 0.5, ground_direction(ball, target)))

    def step(self, dt):
        # Update controls/what to do

        if (
            self.last_update_time + self.UPDATE_INTERVAL < self.car.time < self.intercept.time - self.STOP_UPDATING
            and self.car.on_ground and not self.controls.jump
        ):
            self.state.predict_ball(foresight=self.intercept.time - self.car.time + 1)
            self.update_intercept()

        if self.intercept.time - self.car.time > 1.0 and self.interruptible() and not self.car.on_ground:
            self.finished = True

        self.arrive.step(dt)
        self.controls = self.arrive.controls

        if self.arrive.drive.target_speed < 300:
            self.controls.throttle = 0

        if self.arrive.finished:
            self.finished = True

class DodgeStrike(Strike):
    """
    Strike by dodging (front flipping) into the ball

    TODO: Commented lines use RLUtilities dodge, rather than our own aimdodge...check which is better
    """

    ALLOW_BACKWARDS = False
    JUMP_TIME_MULTIPLIER = 1.0

    def __init__(self, agent, state, target=None):
        self.dodge = AimDodge(agent, 0.1, state.ball.position)
        #self.dodge = Dodge(agent)
        self.dodge.duration = 0.15
        self.dodge.target = target
        
        self.dodging = False

        super().__init__(agent, state, target)

        self.name = "DodgeStrike"

    def interruptible(self):
        if self.state.ball.position[2] > 150 and self.dodging:
            return True
        return not self.dodging and super().interruptible()

    def intercept_predicate(self, car, ball):
        if (ball.time - car.time) < self.get_jump_duration(ball.position[2]):
            return False
        return ball.position[2] < 300

    def get_jump_duration(self, ball_height):
        return 0.05 + clamp((ball_height - 92) / 500, 0, 1.5) * self.JUMP_TIME_MULTIPLIER

    def configure(self, intercept):
        super().configure(intercept)

        ball = intercept.ball
        target_direction = ground_direction(ball, self.target)
        hit_dir = ground_direction(ball.velocity, target_direction * (norm(ball.velocity) * 3 + 500))

        self.arrive.target = intercept.ground_pos - hit_dir * 165
        self.arrive.target_direction = hit_dir

        self.dodge.jump.duration = self.get_jump_duration(ball.position[2])
        #self.dodge.duration = self.get_jump_duration(ball.position[2])

        self.dodge.target = intercept.ball.position
        self.arrive.additional_shift = self.get_jump_duration(ball.position[2]) * 1000

    def step(self, dt):
        if self.dodging:
            self.dodge.step(dt)
            self.controls = self.dodge.controls
        else:
            super().step(dt)
            if (
                self.arrive.arrival_time - self.car.time < self.dodge.jump.duration + 0.13
                #self.arrive.arrival_time - self.car.time < self.dodge.duration + 0.13
                and abs(self.arrive.drive.target_speed - norm(self.car.velocity)) < 1000
                and (
                    dot(normalize(self.car.velocity), ground_direction(self.car, self.arrive.target)) > 0.95
                    or norm(self.car.velocity) < 500
                )
            ):
                self.dodging = True

        if self.dodge.finished:
            self.finished = True

class BumpStrike(Strike):
    """
    Strike by bumping (driving into) the ball
    Simplest kind of strike. Similar to a clear, but the car only moves in to strike the ball if its not too far away and in the car's direction
    """

    MAX_DISTANCE_FROM_WALL = 120

    def __init__(self, agent, state, target=None):
        super().__init__(agent, state, target)

        self.name = "BumpStrike"

    def intercept_predicate(self, car, ball):
        # If ball is too in the air or too far forward return false
        if ball.position[2] > 200 or abs(ball.position[1]) > 5120 - 100:
            return False
        contact_ray = Field.collide(sphere(ball.position, self.MAX_DISTANCE_FROM_WALL))

        # Only go for the ball if its infront of us and not too far away
        return norm(contact_ray.start) > 0 and abs(dot(ball.velocity, contact_ray.direction)) < 300

    def configure(self, intercept):
        target_direction = ground_direction(intercept, self.target)
        strike_direction = ground_direction(intercept.ball.velocity, target_direction * 4000)

        self.arrive.target = intercept.position - strike_direction * 105
        self.arrive.target_direction = strike_direction
        self.arrive.arrival_time = intercept.time

class CloseStrike(DodgeStrike):
    """
    Variant of the DodgeStrike used to shoot at the goal when the intercept is near the enemy net
    Changes where Primus aims. Rather than aiming at the center of the net, it aims at the position within the net that is closest to the ball
    """

    JUMP_TIME_MULTIPLIER = 1.1

    def __init__(self, agent, state, target=None):
        super().__init__(agent, state, target)

        self.name = "CloseStrike"

    def intercept_predicate(self, car, ball):
        return ball.position[2] < 250

    def configure(self, intercept):
        self.target[0] = abs_clamp(self.intercept.ground_pos[0], 300)

        super().configure(intercept)

class SetupStrike(DodgeStrike):
    """
    Variant of the DodgeStrike used to make the ball bounce off a wall towards the target position
    Good for setups (duh)
    """

    JUMP_TIME_MULTIPLIER = 1.1

    def __init__(self, agent, state, target=None):
        #self.real_target = target
        self.state = state

        # Pick which wall we should bounce off of
        mirrors = [self.mirror_position(target, 1), self.mirror_position(target, -1)]
        target = self.pick_easiest_target(agent, self.state.ball, mirrors)
        
        super().__init__(agent, state, target)

        self.name = "SetupStrike"

    @staticmethod
    def mirror_position(pos, wall_sgn):
        mirrored_x = 2 * 4096 * wall_sgn - pos[0]
        return vec3(mirrored_x, pos[1], pos[2])

class DribbleStrike(Play):
    """
    TODO: IMPROVE THIS
    Dribble the ball and then shoot it towards the goal when facing the target and fast enough, or when an opponent is close
    """
    def __init__(self, agent, state, target):
        super().__init__(agent)

        self.target = target
        self.state = state

        self.dribble = Dribble(agent, state.ball, target)
        
        self.shoot = Dodge(agent)
        self.shoot.duration = 0.15
        self.shoot.target = target

        self.shooting = False

        self.name = "DribbleStrike"

    def interruptible(self):
        return not self.shooting

    def step(self, dt):
        if not self.shooting:
            self.name = "DribbleStrike (Dribble)"

            # If not shooting, dribble
            self.dribble.step(dt)
            self.controls = self.dribble.controls
            
            self.finished = self.dribble.finished

            car = self.car
            ball = self.state.ball

            # Check if we should shoot
            dir_to_target = ground_direction(car, self.target)
            if(
                distance(car,ball) < 150
                and ground_distance(car, ball) < 100
                and dot(car.forward(), dir_to_target) > 0.7
                and norm(car.velocity) > clamp(distance(car, self.target) / 3, 1000, 1700)
                and dot(dir_to_target, ground_direction(car, ball)) > 0.9
            ):
                self.shooting = True

            # Check if we should shoot cus an enemy is close
            for opponent in self.state.get_opponents():
                if(
                   distance(opponent.position + opponent.velocity, car) < max(300.0, norm(opponent.velocity) * 0.5)
                   and dot(opponent.velocity, direction(opponent, self.state.ball)) > 0.5   
                ):
                    if distance(car.position, self.state.ball.position) < 200:
                        self.shooting = True
                    else:
                        self.shooting = True
        
        else:
            self.name = "DribbleStrike (Shoot)"
            self.shoot.step(dt)
            self.controls = self.shoot.controls
            self.finished = self.shoot.finished