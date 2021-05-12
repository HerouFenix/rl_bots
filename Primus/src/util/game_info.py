from rlbot.utils.structures.game_data_struct import GameTickPacket, FieldInfoPacket
from rlutilities.simulation import Game, Car, Ball, Pad, Input
from rlutilities.linear_algebra import vec3, vec2, norm, normalize, cross, rotation, dot, xy
from util.math import distance

class Net:
    def __init__(self, team):
        self.sign = 1 - 2 * team
        self.l_post = vec3(self.sign * 1784.0 / 2, -self.sign * 5120.0, 0)
        self.r_post = vec3(-self.sign * 1784.0 / 2, - self.sign * 5120.0, 0)

        self.team = team

        self.center = vec3(0, -self.sign * 5120.0, 640.0 / 2.0)

    def check_inside(self, pos): # Check whether or not inside net
        return pos[1] < -5120.0 if self.team == 0 else pos[1] > 5120.0


class GameInfo(Game):
    def __init__(self, team):
        super().__init__()

        self.team = team
        self.net = Net(team)
        self.enemy_net = Net(1-team)

        # Ball predictions
        self.ball_predictions = []
        self.scoring = False
        self.getting_scored = False
        self.time_of_goal = -1

        # Boost Pads - contains Pad objects which store position and the time until boost is available
        self.large_boost_pads = []
        self.small_boost_pads = []


    def read_packet(self, packet: GameTickPacket, field_info: FieldInfoPacket):
        # Get updated information about the game
        self.read_game_information(packet, field_info)
        
        self.large_boost_pads = [self.pads[i] for i in range(field_info.num_boosts) if field_info.boost_pads[i].is_full_boost]
        self.small_boost_pads = [self.pads[i] for i in range(field_info.num_boosts) if not field_info.boost_pads[i].is_full_boost]

        # Update boost pad timers
        for pad in self.large_boost_pads:
            pad.timer = 10.0 - pad.timer
        for pad in self.small_boost_pads:
            pad.timer = 4.0 - pad.timer


    def get_teammates(self, car):
        # Get all teammate's cars (i.e cars in the same team and with different id than our own)
        return [self.cars[i] for i in range(self.num_cars) if self.cars[i].team == self.team and self.cars[i].id != car.id]

    def get_opponents(self):
        return [self.cars[i] for i in range(self.num_cars) if self.cars[i].team != self.team]

    def predict_ball(self, foresight=5.0, dt=1/120):
        # Predict where the ball will be in the specified duration with intervals of dt (1/120) s
        self.ball_predictions = []
        prediction = Ball(self.ball)

        while(prediction.time < self.time + foresight):
            prediction.step(dt)
            self.ball_predictions.append(Ball(prediction))

            if self.time_of_goal == -1:
                if self.net.check_inside(prediction.position): #If the ball is predicted to go inside our net
                    self.getting_scored = True
                    self.time_of_goal = prediction.time
                elif self.enemy_net.check_inside(prediction.position): #If the ball is predicted to go inside enemy net
                    self.scoring = True
                    self.time_of_goal = prediction.time
    
    def predict_car(self, index, foresight=2.0, dt=1/60):
        # Predict where a given car will be in the specified duration with interval of dt (1/60) s
        # Assumes car is moving with constant acceleration
        car = self.cars[index]
        time_steps = int(foresight/dt)
        speed = norm(car.velocity)
        ang_vel_z = car.angular_velocity[2]

        # Circular Path
        if ang_vel_z != 0 and car.on_ground:
            radius = speed / ang_vel_z
            center = car.position - cross(normalize(xy(car.velocity)), vec3(0,0,1)) * radius
            center_to_car = vec2(car.position - center)

            return [vec3(dot(rotation(ang_vel_z * dt * i), center_to_car)) + center for i in range(time_steps)]

        # Straight path
        return [car.position + car.velocity * dt * i for i in range(time_steps)]

    def detect_collisions(self, foresight=0.5, dt=1/60):
        # Detect collisions that are happening - List of tuples where first 2 elements are the indices of colliding cars and the last is the time until collision

        time_steps = int(foresight / dt)
        predictions = [self.predict_car(i, foresight, dt) for i in range(self.num_cars)]

        collisions = []
        # Check collision between each 2 cars
        for i in range(self.num_cars):
            for j in range(self.num_cars):
                if i >= j: #Ignore duplicat collisions
                    continue
                
                for step in range(time_steps):
                    # Get the predicted position of the 2 cars and check if their distance is smaller than a collision threshold
                    pos1 = predictions[i][step]
                    pos2 = predictions[j][step]

                    if distance(pos1, pos2) < 150: #150 - Collision Threshold
                        collisions.append((i, j, step * dt))
                        break
        
        return collisions

    def detect_collisions_with_agent(self, agent, foresight=0.5, dt=1/60):
        # Detect collisions with given agent - List with time until collision

        time_steps = int(foresight / dt)
        predictions = [self.predict_car(i, foresight, dt) for i in range(self.num_cars)]

        collisions = []


        # Check collision between each 2 cars
        for i in range(self.num_cars):
            if i == agent.id: #Ignore collision with self
                continue
            
            for step in range(time_steps):
                # Get the predicted position of the 2 cars and check if their distance is smaller than a collision threshold
                pos1 = predictions[agent.id][step]
                pos2 = predictions[i][step]

                if distance(pos1, pos2) < 150: #150 - Collision Threshold
                    collisions.append(step * dt)
                    break
        
        return collisions

