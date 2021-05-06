from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

from tmcp import TMCPHandler, TMCPMessage, ActionType

from util.drive import steer_toward_target
from util.vec import Vec3
from util.utilities import physics_object, Vector

from policy.base_policy import BasePolicy

from skeleton.util.structure.game_data import GameData
from skeleton.skeleton_agent import SkeletonAgent

try:
    from rlutilities.linear_algebra import *
    from rlutilities.mechanics import Aerial, AerialTurn, Dodge, Wavedash, Boostdash
    from rlutilities.simulation import Game, Ball, Car
except:
    print("==========================================")
    print("\nrlutilities import failed.")
    print("\n==========================================")
    quit()



class Captain(BaseAgent):
    def __init__(self, name, team, index):
        super().__init__(name, team, index)

    def initialize_agent(self):
        self.tmcp_handler = TMCPHandler(self)
        # Assume you're the captain, if you find an index lower than yours, adjust
        self.captain = True
        self.allies = []
        self.enemies = []
        self.me = physics_object()
        self.car = None
        self.ball_location = None
        self.policy = BasePolicy(self)
        self.game_data = GameData(self.name, self.team, self.index)
        self.game_data.read_field_info(self.get_field_info())

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        self.parse_packet(packet)

        self.handle_comms()
        
        action = self.policy.get_action(self.game_data)
        
        controls = action.get_controls(self.game_data)





        # By default we will chase the ball, but target_location can be changed later
        target_location = self.ball_location

        # Draw some things to help understand what the bot is thinking
        self.renderer.draw_line_3d(self.me.location, target_location, self.renderer.white())
        self.renderer.draw_string_3d(self.me.location, 1, 1, f"Speed: {self.me.velocity.magnitude():.1f}\nThrottle: {controls.throttle:.1f}", self.renderer.white(),)
        self.renderer.draw_rect_3d(
            target_location, 8, 8, True, self.renderer.cyan(), centered=True
        )

        #controls = SimpleControllerState()
        #controls.steer = steer_toward_target(self.car, target_location)
        controls.boost = 1.0

        return controls

    def parse_packet(self, packet):
        """ Updates information about the cars in the game from a given packet. Location, velocity, rotation and boost level. 
            Also useful to keep everyone in check with who the captain is.
        """
        self.ball_location = Vec3(packet.game_ball.physics.location)

        for i in range(packet.num_cars):
            car = packet.game_cars[i]

            # Checking who the captain is
            if self.captain and i < self.index and car.team == self.team:
                self.captain = False
                self.logger.info("Just got demoted.. captain now is " + str(i))
                self.tmcp_handler.send_boost_action(-420)

            # Fetching relevant information about every car
            _obj = physics_object()
            _obj.index = i
            _obj.team = car.team
            _obj.location = Vector([car.physics.location.x, car.physics.location.y, car.physics.location.z])
            _obj.velocity = Vector([car.physics.velocity.x, car.physics.velocity.y, car.physics.velocity.z])
            _obj.rotation = Vector([car.physics.rotation.pitch, car.physics.rotation.yaw, car.physics.rotation.roll])
            _obj.avelocity = Vector([car.physics.angular_velocity.x, car.physics.angular_velocity.y, car.physics.angular_velocity.z])
            _obj.boostLevel = car.boost
            #_obj.local_location = localizeVector(_obj,self.me)

            if i != self.index:
                if car.team == self.team:
                    self.allies.append(_obj)
                else:
                    self.enemies.append(_obj)
            else:
                self.me = _obj
                self.car = packet.game_cars[i]

        self.game_data.read_game_tick_packet(packet)
        self.game_data.read_ball_prediction_struct(self.get_ball_prediction_struct())
        self.game_data.update_extra_game_data()


    def handle_comms(self):
        """ Responsible for handling the TMCP packets sent in the previous iteration.
            Marujos read messages, captains send them.
        """
        # Decide what to do with your mateys
        if self.captain:
            pass
        # Check if there are new orders
        else:
            # Receive and parse all new matchcomms messages into TMCPMessage objects.
            new_messages: List[TMCPMessage] = self.tmcp_handler.recv()

            # Handle TMCPMessages.
            for message in new_messages:
                if message.action_type == ActionType.BOOST:
                    print(message)