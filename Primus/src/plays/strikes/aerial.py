from plays.strikes.strike import Strike
from plays.play import Play

from rlutilities.linear_algebra import vec3, norm, normalize, look_at, axis_to_rotation, dot, xy
from rlutilities.mechanics import Aerial
from rlutilities.simulation import Car, Ball

from util.game_info import GameInfo
from util.intercept import Intercept
from util.math import angle_to, distance, ground_distance, clamp, ground_direction, abs_clamp, range_map, direction

class AerialStrike(Strike):
    """
    A strike but in the air..hence aerial..wow
    """

    MAX_DISTANCE_ERROR = 50
    DELAY_TAKEOFF = False
    MINIMAL_HEIGHT = 800
    MAXIMAL_HEIGHT = 1800
    MINIMAL_HEIGHT_TIME = 1.3
    MAXIMAL_HEIGHT_TIME = 2.5
    DOUBLE_JUMP = True

    def __init__(self, agent, state, target = None):
        self.aerial = Aerial(agent)
        self.aerial.angle_threshold = 0.8
        self.aerial.single_jump = not self.DOUBLE_JUMP

        super().__init__(agent, state, target)
        self.arrive.allow_fancy_moves = False  # Try enabling this (might mess up cus fancy moves may mess up the approach)

        self.flying = False
        self.flight_path = []

        self.name = "AerialStrike"

    def interruptible(self):
        return self.flying or super().interruptible()

    def intercept_predicate(self, car, ball):
        return True
        required_time = range_map(ball.position[2],
                                  self.MINIMAL_HEIGHT,
                                  self.MAXIMAL_HEIGHT,
                                  self.MINIMAL_HEIGHT_TIME,
                                  self.MAXIMAL_HEIGHT_TIME)
        return self.MINIMAL_HEIGHT < ball.position[2] < self.MAXIMAL_HEIGHT and ball.time - car.time > required_time

    def configure(self, intercept):
        super().configure(intercept)
        self.aerial.target = intercept.position - direction(intercept, self.target) * 100
        self.aerial.up = normalize(ground_direction(intercept, self.car) + vec3(0, 0, 0.5))
        self.aerial.arrival_time = intercept.time

    @staticmethod
    def simulate_flight(car, aerial, flight_path = None):
        test_car = Car(car)
        
        test_aerial = Aerial(test_car)

        test_aerial.target = aerial.target

        test_aerial.arrival_time =  aerial.arrival_time
        test_aerial.angle_threshold =  aerial.angle_threshold
        test_aerial.up =  aerial.up
        test_aerial.single_jump =  aerial.single_jump

        if flight_path is not None: flight_path.clear()

        while not test_aerial.finished:
            test_aerial.step(1 / 120)
            test_car.boost = 100 
            test_car.step(test_aerial.controls, 1 / 120)

            if flight_path is not None:
                flight_path.append(vec3(test_car.position))

        return test_car
    
    def step(self, dt):
        time_left = self.aerial.arrival_time - self.car.time

        if self.flying:
            dir_to_ball = direction(self.car, self.state.ball)

            # Up in the air
            if self.car.position[2] > 200:
                self.aerial.up = vec3(0, 0, -1) + xy(dir_to_ball)

            self.aerial.target_orientation = look_at(dir_to_ball, vec3(0,0,-3) + dir_to_ball)
            self.aerial.step(dt)

            self.controls = self.aerial.controls
            self.finished = self.aerial.finished and time_left < -0.3

        else:
            super().step(dt)

            # Simulate aerial
            simulated = self.simulate_flight(self.car, self.aerial, self.flight_path)
            #simulated = self.simulate_flight()

            speed_towards_target = dot(self.car.velocity, ground_direction(self.car, self.aerial.target))
            speed_needed = ground_distance(self.car, self.aerial.target) / time_left

            # If too fast, slow down
            if speed_towards_target > speed_needed and angle_to(self.car, self.aerial.target) < 0.1:
                self.controls.throttle = -1

            # If we're near the target, start flying
            elif distance(simulated, self.aerial.target) < self.MAX_DISTANCE_ERROR:
                if angle_to(self.car, self.aerial.target) < 0.1 or norm(self.car.velocity) < 1000:
                    """
                    if self.DELAY_TAKEOFF and ground_distance(self.car, self.aerial.target) > 1000:
                        future_car = Car(self.car)
                        time = 0.5
                        future_car.time += time
                        displacement = future_car.velocity * time if norm(future_car.velocity) > 500\
                            else normalize(future_car.velocity) * 500 * time
                        future_car.position += displacement

                        # Simulate aerial for future car
                        future_simulated = self.simulate_flight(future_car, self.aerial)

                        # If aerial was succesful, continue driving to make sure we go for the latest possible areals
                        if distance(future_simulated, self.aerial.target) > self.MAX_DISTANCE_ERROR:
                            self.flying = True
                    else:
                    """
                    self.flying = True

            else:
                self.controls.throttle = 1 
            
class DoubleAerialStrike(Play):
    """
    AerialStrike followed that checks if Primus can continue aerialing to hit the ball a second time
    """  

    def __init__(self, aerial_strike):
        super().__init__(aerial_strike.car)

        self.aerial_strike = aerial_strike
        self.state = aerial_strike.state
        
        self.aerial = Aerial(self.car)
        self.aerial.up = vec3(0,0,-1)
        
        self.flight_path = []
    	
        self.name = "DoubleAerialStrike"

    def interruptible(self):
        return self.aerial_strike.interruptible()

    def check_second_touch(self):
        # Check whether there's a second hit to be done, or if we should stop

        self.state.predict_ball(foresight=4.0)

        for i in range(0, len(self.state.ball_predictions), 5):
            ball = self.state.ball_predictions[i]
            if ball.position[2] < 500: break

            self.aerial.target = ball.position - direction(ball, self.aerial_strike.target) * 80
            self.aerial.arrival_time = ball.time

            final_car = AerialStrike.simulate_flight(self.car, self.aerial, self.flight_path)

            if distance(final_car, self.aerial.target) < 50:
                # Second touch found lets go!
                return 

        # No second touch found
        self.finished = True

    def step(self, dt):
        if self.aerial_strike.finished:
            # Second hit was found, perform it
            self.name = "DoubleAerialStrike (2nd)"
            
            self.aerial.step(dt)
            
            self.controls = self.aerial.controls
            self.finished = self.aerial.finished

            if self.car.on_ground: self.finished = True

        else:
            self.name = "DoubleAerialStrike"
            
            self.aerial_strike.step(dt)
            self.controls = self.aerial_strike.controls

            if self.aerial_strike.finished:
                if not self.car.on_ground:
                    # If we finished the aerial strike and we're still not on the ground, check for second hit
                    self.check_second_touch()
                else:
                    self.finished = True

