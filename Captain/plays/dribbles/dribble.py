import math

from plays.actions.drive import Drive

from plays.play import Play

from rlutilities.linear_algebra import vec3, norm, normalize
from rlutilities.simulation import Car, Ball

from util.game_info import GameInfo
from util.intercept import Intercept
from util.math import clamp, sign, distance, ground_distance, direction, local, ground, world

class Dribble(Play):
    """
    Carry the ball on roof towards a target.
    Finishes if the ball hits the floor.
    """

    def __init__(self, agent, ball, target):
        super().__init__(agent)

        self.ball = ball
        self.target = ground(target)
        self.drive = Drive(self.car)
        self.shift_direction = vec3(0, 0, 0)

        self.name = "Dribble"

    def step(self, dt):
        ball = Ball(self.ball)

        # Simulate ball until it gets near the floor
        while (ball.position[2] > 120 or ball.velocity[2] > 0) and ball.time < self.car.time + 10:
            ball.step(1/60)

        ball_local = local(self.car, ground(ball.position))
        target = local(self.car, self.target)

        shift = ground(direction(ball_local, target))
        shift[1] *= 1.8
        shift = normalize(shift)
        
        max_turn = clamp(norm(self.car.velocity) / 800, 0, 1)
        max_shift = normalize(vec3(1 - max_turn, max_turn * sign(shift[1]), 0))

        if abs(shift[1]) > abs(max_shift[1]) or shift[0] < 0:
            shift = max_shift
        shift *= clamp(self.car.boost, 40, 60)

        shift[1] *= clamp(norm(self.car.velocity)/1000, 1, 2)

        self.shift_direction = normalize(world(self.car, shift) - self.car.position)

        target = world(self.car, ball_local - shift)
        speed = distance(self.car.position, target) / max(0.001, ball.time - self.car.time)

        self.drive.target_speed = speed
        self.drive.target_pos = target

        self.drive.step(dt)
        self.controls = self.drive.controls
        self.finished = self.ball.position[2] < 100 or ground_distance(self.ball, self.car) > 2000
