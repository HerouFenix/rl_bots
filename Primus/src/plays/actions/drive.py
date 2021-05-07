import math

from rlutilities.linear_algebra import vec3, norm, dot, normalize
from rlutilities.simulation import Car
from plays.play import Play
from util.game_info import GameInfo

from util.math import ground, local, ground_distance, distance, direction, abs_clamp, clamp11

class Drive(Play):
    """
    Drive towards specified target position at a maximum target speed
    """
    
    def __init__(self, agent, target_pos = vec3(0,0,0), target_speed = 0, backwards = False):
        super().__init__(agent)

        self.target_pos = target_pos
        self.target_speed = target_speed
        self.backwards = backwards

        self.drive_on_walls = False

        self.name = "Driving"
    

    def step(self, dt):
        target = self.target_pos

        # Make sure the set target isn't outside the arena (can happen due to ball predictions)
        target = vec3(
            abs_clamp(target[0], 4096 - 100),
            abs_clamp(target[1], 5120 - 100),
            target[2]
        )

        if not self.drive_on_walls: # If we're driving on the floor
            seam_radius = 100 if abs(self.car.position[1]) > 5120 - 100 else 200
            if self.car.position[2] > seam_radius: # Check if car is in the air (if so, ground it)
                target = ground(self.car)

        local_target = local(self.car, target)

        if self.backwards: # If we're driving backwards
            local_target[0] *= -1
            local_target[1] *= -1

        # Steering
        angle = math.atan2(local_target[1], local_target[0])
        self.controls.steer = clamp11(2.22 * angle) # 2.22 corresponds to the car's (cyclone) turning radius

        # Powersliding
        if(
            abs(angle) > 1.5
            and self.car.position[2] < 300
            and (ground_distance(self.car, target) < 3500 or abs(self.car.position[0]) > 3500)
            and dot(normalize(self.car.velocity), self.car.forward()) > 0.85
        ):
            self.controls.handbrake = 1
        else:
            self.controls.handbrake = 0

        # Forward
        speed = dot(self.car.velocity, self.car.forward())
        if self.backwards:
            speed *= -1

        # Speed Controller
        if speed < self.target_speed: # If our speed is smaller than our target speed, accelerate
            self.controls.throttle = 1.0

            if self.target_speed > 1400 and speed < 2250 and self.target_speed - speed > 50: # If target speed is higher than minimum speed when boosting and car is moving at lower speed than max when boosting
                self.controls.boost = 1
            else:
                self.controls.boost = 0

        else:
            if(speed - self.target_speed) > 400:
                self.controls.throttle = -1.0
            elif(speed - self.target_speed) > 100:
                if self.car.up()[2] > 0.85:
                    self.controls.throttle = 0.0
                else:
                    self.controls.throttle = 0.01

            self.controls.boost = 0

        # Backwards Driving
        if self.backwards:
            self.controls.throttle *= -1
            self.controls.steer *= -1
            self.controls.boost = 0
            self.controls.handbrake = 0

        # Prevent boosting unless facing target (unpotimal)
        if abs(angle) > 0.3:
            self.controls.boost = 0

        # If close enough, finish
        if distance(self.car, self.target_pos) < 100:
            self.finished = True

class Stop(Play):
    """
    Stop moving
    """

    def __init__(self, agent):
        super().__init__(agent)

        self.name = "Stopping"

    def step(self, dt):
        speed = dot(self.car.forward(), self.car.velocity)

        if speed > 100: #If moving forward decelerate
            self.controls.throttle = -1.0
        elif speed < -100: #If moving backwards accelerate
            self.controls.throttle = 1.0
        else: #Else, stop
            self.controls.throttle = 0
            self.finished = True

class AdvancedDrive(Play):
    """
    Fancier Drive which incorporates techniques like wavedashes, halfflips and dodges
    """