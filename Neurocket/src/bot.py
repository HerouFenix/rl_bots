from numpy.core.defchararray import array
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import BallInfo, GameTickPacket, PlayerInfo
import numpy as np

from physics_object import PhysicsObject
from playing_agent import PlayingAgent

class MyBot(BaseAgent):
    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.agent = None

    def initialize_agent(self):
        team_size = self.get_match_settings().PlayerConfigurationsLength() // 2
    
        if team_size == 1:
            game_mode = "Duel"
        elif team_size == 2:
            game_mode = "Doubles"
        elif team_size == 3:
            game_mode = "Standard"
        else:
            raise Exception("Unknown team size {}.".format(team_size))

        self.agent = PlayingAgent(fname="./save/" + game_mode + "_model.h5")

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        """
        This function will be called by the framework many times per second. This is where you can
        see the motion of the ball, etc. and return controls to drive your car.
        """
        state = self.build_state(packet)

        _, action = self.agent.choose_action(state)

        controls = SimpleControllerState()

        map_action_to_controls(action, controls)
        
        return controls

    def build_state(self, packet: GameTickPacket):

        my_car = packet.game_cars[self.index]
        own_team = my_car.team

        observation = []
        tm8s = []
        opponents = []

        for i in range(packet.num_cars):
            player_other = packet.game_cars[i]
            if self.index != i:
                if player_other.team == own_team:
                    tm8s.append(player_other)
                else:
                    opponents.append(player_other)

        # Mirror states in relation to team
        inverted = own_team != 0
        
        observation += serialize_ball(packet.game_ball, inverted)
        observation += serialize_player(my_car, inverted)
        for pl in tm8s:
            observation += serialize_player(pl, inverted)
        for pl in opponents:
            observation += serialize_player(pl, inverted)

        return np.asarray(observation, dtype=np.float32)


def map_action_to_controls(action: int, controls: SimpleControllerState):
    """
    Imagining the agent as a Keyboard player, its inputs can only be booleans
    1st bit: Throttle
    2nd bit: Steering
    3rd bit: Pitch
    4th bit: Yaw
    5th bit: Roll
    6th bit: Jump
    7th bit: Boost
    8th bit: Handbrake
    """
    controls.throttle = 1 if action & 1 else -1
    controls.steer = 1 if action & 2 else -1
    controls.pitch = 1 if action & 4 else -1
    controls.yaw = 1 if action & 8 else -1
    controls.roll = 1 if action & 16 else -1
    controls.jump = 1 if action & 32 else -1
    controls.boost = 1 if action & 64 else -1
    controls.handbrake = 1 if action & 128 else -1

def serialize_ball(ball: BallInfo, inverted=False):
    ball_physics = ball.physics

    if inverted:
        phys = PhysicsObject(position=np.array([ball_physics.location.x, -ball_physics.location.y, ball_physics.location.z]), \
                             linear_velocity=np.array([ball_physics.velocity.x, -ball_physics.velocity.y, ball_physics.velocity.z]), \
                             angular_velocity=np.array([ball_physics.angular_velocity.x, -ball_physics.angular_velocity.y, ball_physics.angular_velocity.z]))
    else:
        phys = PhysicsObject(position=np.array([ball_physics.location.x, ball_physics.location.y, ball_physics.location.z]), \
                             linear_velocity=np.array([ball_physics.velocity.x, ball_physics.velocity.y, ball_physics.velocity.z]), \
                             angular_velocity=np.array([ball_physics.angular_velocity.x, ball_physics.angular_velocity.y, ball_physics.angular_velocity.z]))
    
    phys.euler_angles()
    phys.rotation_mtx()

    return phys.serialize()

def serialize_player(player: PlayerInfo, inverted=False):
    player_physics = player.physics

    if inverted:
        phys = PhysicsObject(position=np.array([player_physics.location.x, -player_physics.location.y, player_physics.location.z]), \
                             linear_velocity=np.array([player_physics.velocity.x, -player_physics.velocity.y, player_physics.velocity.z]), \
                             angular_velocity=np.array([player_physics.angular_velocity.x, -player_physics.angular_velocity.y, player_physics.angular_velocity.z]))    
    else:
        phys = PhysicsObject(position=np.array([player_physics.location.x, player_physics.location.y, player_physics.location.z]), \
                             linear_velocity=np.array([player_physics.velocity.x, player_physics.velocity.y, player_physics.velocity.z]), \
                             angular_velocity=np.array([player_physics.angular_velocity.x, player_physics.angular_velocity.y, player_physics.angular_velocity.z]))

    #phys._euler_angles = np.array([player_physics.rotation.pitch, player_physics.rotation.yaw, player_physics.rotation.roll])
    phys.euler_angles()
    phys.rotation_mtx()

    return phys.serialize()