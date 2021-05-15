import math

from rlutilities.linear_algebra import vec3, vec2, norm, dot, normalize
from rlutilities.simulation import Car
from plays.play import Play

from plays.actions.jump import HalfFlip

from util.game_info import GameInfo

from rlutilities.mechanics import Wavedash, Dodge

from util.math import clamp, nonzero, ground, local, ground_distance, distance, direction, abs_clamp, clamp11, angle_to

from util.intercept import estimate_time

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

    def interruptible(self):
        return True
    

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

    @staticmethod
    def turn_radius(speed: float) -> float:
        spd = clamp(speed, 0, 2300)
        return 156 + 0.1 * spd + 0.000069 * spd ** 2 + 0.000000164 * spd ** 3 + -5.62E-11 * spd ** 4

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
    Gets to a location ASAP
    """

    DODGE_DURATION = 1.5
    HALFFLIP_DURATION = 2
    WAVEDASH_DURATION = 1.45

    def __init__(self, car, target = vec3(0,0,0), use_boost = False, target_speed = 2300):
        super().__init__(car)

        target = ground(target)

        self.target = vec3(
            abs_clamp(target[0], 4096 - 100),
            abs_clamp(target[1], 5120 - 100),
            target[2]
        )

        self.use_boost = use_boost

        self.finish_distance = 500

        self.time_on_ground = 0
        self.driving = True


        # Choose if we want to start driving backwards and then halfflip to correct
        forward_estimate = estimate_time(car, self.target)
        backwards_estimate = estimate_time(car, self.target, -1) + 0.5

        backwards = (
            dot(car.velocity, car.forward()) < 500
            and backwards_estimate < forward_estimate
            and (distance(self.car, self.target) > 3000 or distance(self.car, self.target) < 300)
            and car.position[2] < 200
        )

        self.drive = Drive(car, self.target, target_speed, backwards)
        self.action = self.drive

        self.name = "AdvancedDriving"

    def interruptible(self):
        return self.driving and self.car.on_ground

    def step(self, dt):
        target = ground(self.target)
        car_speed = norm(self.car.velocity)

        time_left = (ground_distance(self.car, target) - self.finish_distance) / max(car_speed+500, 1400)
        forward_speed = dot(self.car.forward(), self.car.velocity)

        if self.driving and self.car.on_ground:
            self.action.target_pos = target
            self.time_on_ground += dt

            # Decide whether to dodge, wavedash or halfflip

            if(
                self.time_on_ground > 0.2
                and self.car.position[2] < 200
                and car_speed < 2000
                and angle_to(self.car, target, backwards = forward_speed < 0) < 0.1
                and self.car.gravity[2] < -500
            ):
                # If going forward
                if forward_speed > 0:
                    can_use_boost = self.use_boost and self.car.boost > 20 # Use boost rather than doing a flip to gain speed

                    if car_speed > 1200 and not can_use_boost:

                        if car_speed > self.DODGE_DURATION: # Do a dodge
                            dodge = Dodge(self.car)
                            dodge.duration = 0.07
                            dodge.direction = vec2(direction(self.car, target))
                            self.action = dodge
                            self.driving = False
                            self.name = "AdvancedDriving (Dodge)"
                        
                        elif time_left > self.WAVEDASH_DURATION: # Do a wave dash
                            wavedash = Wavedash(self.car)
                            wavedash.direction = vec2(direction(self.car, target))
                            self.action = wavedash
                            self.driving = False
                            self.name = "AdvancedDriving (WaveDash)"

                elif time_left > self.HALFFLIP_DURATION and car_speed > 800: # If going backwards decide whether to halfflip
                    self.action = HalfFlip(self.car, self.use_boost and time_left > 3)
                    self.driving = False
                    self.name = "AdvancedDriving (HalfFlip)"
                
        self.action.step(dt)
        self.controls = self.action.controls

        # Prevent boosting when in air
        if self.driving and not self.car.on_ground:
            self.controls.boost = False

        # Make sure we don't stay stuck upside down
        if not self.car.on_ground:
            self.controls.throttle = 1

        # Check if a dodge, wavedash or halfflip has finished
        if self.action.finished and not self.driving:
            self.driving = True
            self.time_on_ground = 0
            self.action = self.drive
            self.name = "AdvancedDriving (Drive)"
            self.drive.backwards = False

        if ground_distance(self.car, target) < self.finish_distance and self.driving:
            self.finished = True


class Arrive(Play):
    """
    Arrive at a target location at a certain time and angle
    """

    def __init__(self, agent):
        super().__init__(agent)
        self.drive = Drive(self.car)
        self.travel = AdvancedDrive(self.car)

        self.travel.drive.backwards = False
        self.action = self.drive

        self.target_direction = None
        self.target = None
        self.arrival_time = 0
        self.backwards = False

        self.lerp_time = 0.56
        self.allow_fancy_moves = True # Whether to allow dodges and wavedashes
        self.additional_shift = 0.0

        self.name = "Arrive"

    def interruptible(self):
        return self.action.interruptible()

    def step(self, dt):
        if self.target_direction is not None:
            car_speed = norm(self.car.velocity)
            target_direction = normalize(self.target_direction)

            # in order to arrive in a direction, we need to shift the target in the opposite direction
            # the magnitude of the shift is based on how far are we from the target
            shift = clamp(ground_distance(self.car.position, self.target) * self.lerp_time, 0, clamp(car_speed, 1500, 2300) * 1.6)

            # if we're too close to the target, aim for the actual target so we don't miss it
            if shift - self.additional_shift * 0.4 < Drive.turn_radius(clamp(car_speed, 500, 2300)) * 1.1:
                shift = 0
            else:
                shift += self.additional_shift

            shifted_target = self.target - target_direction * shift

            time_shift = ground_distance(shifted_target, self.target) / clamp(car_speed, 500, 2300) * 1.2
            shifted_arrival_time = self.arrival_time - time_shift

        else:
            shifted_target = self.target
            shifted_arrival_time = self.arrival_time

        self.drive.target_pos = shifted_target
        self.travel.target = shifted_target

        # Define what our drive target speed is
        dist_to_target = ground_distance(self.car.position, shifted_target)
        time_left = nonzero(shifted_arrival_time - self.car.time)
        target_speed = clamp(dist_to_target / time_left, 0, 2300)

        # If we're close to the target and correctly aligned start stopping
        if target_speed < 800 and dist_to_target > 500 and angle_to(self.car, shifted_target) < 0.1:
            target_speed = 0

        self.drive.target_speed = target_speed
        self.drive.backwards = self.backwards

        # dodges and wavedashes can mess up correctly arriving, so we use them only if we really need them
        if (
            (
                self.allow_fancy_moves
                and norm(self.car.velocity) < target_speed - 600
                and self.car.boost < 20
                and not self.backwards
            )
            or not self.travel.driving  # a dodge/wavedash is in progress
        ):
            self.action = self.travel
        else:
            self.action = self.drive

        self.action.step(dt)
        self.controls = self.action.controls

        self.finished = self.car.time >= self.arrival_time
