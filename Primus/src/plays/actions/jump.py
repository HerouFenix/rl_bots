import math

from rlutilities.linear_algebra import vec3, norm, dot, normalize, sgn
from rlutilities.simulation import Car
from plays.play import Play
from util.game_info import GameInfo

from util.math import ground, local, ground_distance, distance, direction, abs_clamp, clamp11


class Jump(Play):
    """
    Jump :)
    """
    
    def __init__(self, agent, duration):
        super().__init__(agent)

        self.duration = duration
        self.timer = 0
        self.counter = 0

        self.name = "Jumping"

    def step(self, dt):
        self.controls.jump = 1 if self.timer < self.duration else 0

        if self.controls.jump == 0:
            self.counter += 1
        
        self.timer += dt

        if self.counter >= 2: # Double jump
            self.finished = True
    
class AirDodge(Play):
    """
    Dodge towards a target or do a double jump if no target
    """

    def __init__(self, car, duration = 0.0, target = None):
        super().__init__(car)
        self.target = target
        self.jump = Jump(car, duration)

        self.jump_finished = True if duration <= 0 else False
        
        self.state_timer = 0.0
        self.total_timer = 0.0
        self.phase = 0

        self.name = "AirDodge"

    def step(self, dt):
        recovery_time = 0.0 if self.target is None else 0.4

        if not self.jump.finished:
            self.jump.step(dt)
            self.controls = self.jump.controls
        else:
            if self.phase == 0:
                # Double jump
                if self.target is None:
                    self.controls.roll = 0
                    self.controls.pitch = 0
                    self.controls.yaw = 0
                
                # Air Dodge
                else:
                    target_pos = dot(self.target - self.car.position, self.car.orientation)
                    target_pos[2] = 0
                    
                    target_direction = normalize(target_pos)

                    self.controls.roll = 0
                    self.controls.pitch = -target_direction[0]
                    self.controls.yaw = clamp11(sgn(self.car.orientation[2,2]) * target_direction[1])

                    if target_pos[0] > 0 and dot(self.car.velocity, self.car.forward()) > 500:
                        self.controls.pitch = self.controls.pitch * 0.8
                        self.controls.yaw = clamp11(self.controls.yaw * 5)

            elif self.phase == 2:
                self.controls.jump = 1
           
            elif self.phase >= 4:
                self.controls.roll = 0
                self.controls.pitch = 0
                self.controls.yaw = 0
                self.controls.jump = 0
            
            self.phase += 1
            self.state_timer += dt
        
        self.finished = self.jump.finished and self.state_timer > recovery_time and self.phase >= 6

class SpeedFlip(Play):
    """
    https://www.google.com/search?client=firefox-b-d&q=rocket+league+speed+flip#kpvalbx=__lWVYMfTHY64UqTuvsgN22
    """

    def __init__(self, car, right = True, boost = True):
        super().__init__(car)
        
        self.direction = 1 if right else -1
        self.use_boost = boost

        self.timer = 0.0

        self.FIRST_JUMP_DURATION = 0.1
        self.TIME_BETWEEN_JUMPS = 0.1
        self.SECOND_JUMP_DURATION = 0.05
        self.TIMEOUT = 2.0
        
        self.name = "SpeedFlip"

    def step(self, dt):
        self.controls.throttle = 1.0

        # Use boost after first jump (unless already at max velocity)
        speed = norm(self.car.velocity)
        self.controls.boost = (
            self.use_boost and speed < 2290
        )

        if self.timer < self.FIRST_JUMP_DURATION:
            self.controls.jump = True
            self.controls.pitch = 1.0

        elif self.timer < self.FIRST_JUMP_DURATION + self.TIME_BETWEEN_JUMPS:
            self.controls.jump = False
            self.controls.pitch = 1.0

        elif self.timer < self.FIRST_JUMP_DURATION + self.TIME_BETWEEN_JUMPS + self.SECOND_JUMP_DURATION:
            self.controls.jump = True
            self.controls.pitch = -1.0
            self.controls.roll = -0.3 * self.direction

        else:
            self.controls.jump = False
            self.controls.pitch = 1.0
            self.controls.roll = -1.0 * self.direction
            self.controls.yaw = -1.0 * self.direction
        
        self.timer += dt

        self.finished = (self.timer > self.TIMEOUT) or (self.car.on_ground and self.timer > 0.5)