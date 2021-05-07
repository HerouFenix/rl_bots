from rlbot.agents.base_agent import BaseAgent, GameTickPacket, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

from tmcp import TMCPHandler, TMCPMessage, ActionType

from util.drive import steer_toward_target
from util.vec import Vec3
from util.utilities import physics_object, Vector

#from policy.base_policy import BasePolicy

from action.kickoffs.kickoff import Kickoff
from action.maneuver import Maneuver
from policy import solo_strategy, teamplay_strategy
from tools.drawing import DrawingTool
from tools.game_info import GameInfo

try:
    from rlutilities.linear_algebra import *
    from rlutilities.mechanics import Aerial, AerialTurn, Dodge, Wavedash, Boostdash
    from rlutilities.simulation import Game, Ball, Car, Input
except:
    print("==========================================")
    print("\nrlutilities import failed.")
    print("\n==========================================")
    quit()


ACK = -1
RENDERING = True

class Captain(BaseAgent):
    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        # Initializing general stuff here

    def initialize_agent(self):

        self.tmcp_handler = TMCPHandler(self)
        self.info = GameInfo(self.team)
        self.info.set_mode("soccar")
        self.draw = DrawingTool(self.renderer, self.team)
        self.tick_counter = 0
        self.last_latest_touch_time = 0
        self.me = physics_object()
        self.car = None

        # Assume you're the captain, if you find an index lower than yours, adjust
        self.captain = True
        self.allies = []
        self.enemies = []
        self.policy = None
        self.action = None
        self.controls = SimpleControllerState()


    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        self.parse_packet(packet)

        self.handle_comms()
        
        self.info.read_packet(packet, self.get_field_info())

        # cancel maneuver if a kickoff is happening and current maneuver isn't a kickoff maneuver
        if packet.game_info.is_kickoff_pause and not isinstance(self.action, Kickoff):
            self.action = None

        # reset maneuver when another car hits the ball
        touch = packet.game_ball.latest_touch
        if (
            touch.time_seconds > self.last_latest_touch_time
            and touch.player_name != packet.game_cars[self.index].name
        ):
            self.last_latest_touch_time = touch.time_seconds

            # don't reset when we're dodging, wavedashing or recovering
            if self.action and self.action.interruptible():
                self.action = None

        # choose action
        if self.action is None:

            if RENDERING:
                self.draw.clear()
            
            if self.info.get_teammates(self.info.cars[self.index]):
                self.action = teamplay_strategy.choose_action(self.info, self.info.cars[self.index])
            else:
                self.action = solo_strategy.choose_action(self.info, self.info.cars[self.index])
        
        # execute action
        if self.action is not None:
            self.action.step(self.info.time_delta)
            self.controls = self.action.controls

            if RENDERING:
                self.draw.group("maneuver")
                self.draw.color(self.draw.yellow)
                self.draw.string(self.info.cars[self.index].position + vec3(0, 0, 50), type(self.action).__name__)
                self.action.render(self.draw)

            # cancel maneuver when finished
            if self.action.finished:
                self.action = None
                
        if RENDERING:
            self.draw.execute()

        return self.controls

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
                self.tmcp_handler.send_boost_action(ACK)

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

    def handle_comms(self):
        """ Responsible for handling the TMCP packets sent in the previous iteration.
            Marujos read messages, captains send them. (general rule)
            TMCP only supports a pre-defined set of messages, so we will be adding a few by changing certain parameters.
        """

        # Receive and parse all new matchcomms messages into TMCPMessage objects.
        new_messages: List[TMCPMessage] = self.tmcp_handler.recv()

        # Decide what to do with your mateys
        if self.captain:
            # Handle TMCPMessages.
            for message in new_messages:
                if message.action_type == ActionType.BOOST:
                    print(message)
        # Check if there are new orders
        else:
            # Handle TMCPMessages.
            for message in new_messages:
                if message.action_type == ActionType.BOOST:
                    print(message)