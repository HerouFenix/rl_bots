import math

from plays.actions.drive import Arrive, Drive
from plays.actions.jump import AimDodge

from plays.play import Play

from rlutilities.linear_algebra import vec3, dot, norm, normalize, xy
from rlutilities.simulation import Car, Ball, Field, sphere

from util.game_info import GameInfo
from util.intercept import Intercept
from util.math import ground_distance, clamp, ground_direction

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
        self.target = target

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
        self.arrive.target = intercept.ground_pos
        self.arrive.arrival_time = intercept.time
        self.arrive.backwards = self.should_strike_backwards

    def intercept_predicate(self, car, ball):
        # This basically returns whether Primus should move to intercept or stay put
        return True

    def update_intercept(self):
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
        to_goal = ground_direction(ball, self.state.enemy_net.center)
        return max(targets, key=lambda target: dot(ground_direction(car, ball) + to_goal * 0.5, ground_direction(ball, target)))

    def step(self, dt):
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
    """

    ALLOW_BACKWARDS = False
    JUMP_TIME_MULTIPLIER = 1.0

    def __init__(self, agent, state, target=None):
        self.dodge = AimDodge(agent, 0.1, state.ball.position)
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