import math

from rlutilities.linear_algebra import vec3,vec2, norm, dot, normalize, sgn, look_at
from rlutilities.simulation import Car
from plays.play import Play
from util.game_info import GameInfo

from rlutilities.mechanics import Dodge, AerialTurn

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

class HalfFlip(Play):
    """
    https://www.youtube.com/watch?v=V_4ajUfCVq4 
    """
    
    def __init__(self, agent, use_boost = False):
        super().__init__(agent)

        self.dodge = Dodge(agent)
        self.dodge.duration = 0.12
        self.dodge.direction = vec2(agent.forward() * -1.0)

        self.s = 0.95 * sgn(dot(self.car.angular_velocity, self.car.up()) + 0.01)
        self.timer = 0.0

        self.use_boost = use_boost

        self.name = "HalfFlip"

    def step(self, dt):
        boost_delay = 0.4
        stall_start = 0.50
        stall_end = 0.70
        timeout = 2.0

        self.dodge.step(dt)
        self.controls = self.dodge.controls

        if stall_start < self.timer < stall_end:
            self.controls.roll = 0.0
            self.controls.pitch = -1.0
            self.controls.yaw = 0.0
        
        if self.timer > stall_end:
            self.controls.roll = self.s
            self.controls.pitch = -1.0
            self.controls.yaw = self.s

        if self.use_boost and self.timer > boost_delay:
            self.controls.boost = 1
        else:
            self.controls.boost = 0

        self.timer += dt

        self.finished = (self.timer > timeout) or (self.car.on_ground and self.timer > 0.5)

class AimDodge(AirDodge):
    """
    Dodge after turning the car towards the target.
    Useful for dodging into the ball.
    """

    def __init__(self, agent, duration, target):
        super().__init__(agent, duration, target)
        self.turn = AerialTurn(agent)

        self.name = "AimDodge"

    def step(self, dt):
        super().step(dt)

        if not self.jump.finished and not self.car.on_ground:
            target_direction = direction(self.car, self.target + vec3(0, 0, 200))
            up = target_direction * -1
            up[2] = 1
            up = normalize(up)
            self.turn.target = look_at(target_direction, up)
            self.turn.step(dt)

            self.controls.pitch = self.turn.controls.pitch
            self.controls.yaw = self.turn.controls.yaw
            self.controls.roll = self.turn.controls.roll