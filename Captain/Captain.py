from typing import List

from rlbot.agents.base_agent import BaseAgent, GameTickPacket, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

from tmcp import TMCPHandler, TMCPMessage, ActionType

from util.drive import steer_toward_target
from util.vec import Vec3
from util.utilities import physics_object, Vector

from action.kickoffs.kickoff import Kickoff
from action.maneuver import Maneuver
from policy import solo_strategy, teamplay_strategy, base_policy, marujo_strategy
from tools.drawing import DrawingTool
from tools.game_info import GameInfo

from policy.base_policy import ACK, KICKOFF, GEN_DEFEND, CLUTCH_DEFEND, BALL, RECOVERY
from policy import offense, defense, kickoffs

from action.recovery import Recovery

try:
    from rlutilities.linear_algebra import *
    from rlutilities.mechanics import Aerial, AerialTurn, Dodge, Wavedash, Boostdash
    from rlutilities.simulation import Game, Ball, Car, Input
except:
    print("==========================================")
    print("\nrlutilities import failed.")
    print("\n==========================================")
    quit()

RENDERING = True
ATTACK = 0
DEFENSE = 1
BOOST = 2

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

        # Team actions {index: Action Macro}
        self.team_actions = {}
        self.last_sent = {}
        self.stance = None


    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        # Handle the packet
        self.parse_packet(packet)

        # Check if our action needs to change
        self.check_resets(packet)

        # Choosing the action: only the captain decides
        if self.captain:
            my_team = [i for i in range(self.info.num_cars) if self.info.cars[i].team == self.team]
            self.team_actions = base_policy.choose_action(self.info, self.info.cars[self.index], my_team)
        
        # Execute action
        if self.action is not None:
            self.action.step(self.info.time_delta)
            self.controls = self.action.controls

            if RENDERING:
                self.draw.group("maneuver")
                self.draw.color(self.draw.yellow)
                self.draw.string(self.info.cars[self.index].position + vec3(0, 0, 50), type(self.action).__name__)
                self.action.render(self.draw)

            # When you're finished with the action or if it has been cancelled, reconsider team strategy
            if self.action.finished or self.action == None:
                if self.captain:
                    self.team_actions = base_policy.choose_action(self.info, self.info.cars[self.index], my_team)

                # Pick action according to previous orders
                self.action = marujo_strategy.choose_action(self.info, self.info.cars[self.index], self.stance)
                
        if RENDERING:
            self.draw.execute()

        # Send / Receive TMCP messages
        self.handle_comms()

        return self.controls

    def parse_packet(self, packet):
        """ Updates information about the cars in the game from a given packet. Location, velocity, rotation and boost level. 
            Also useful to keep everyone in check with who the captain is.
        """
        self.info.read_packet(packet, self.get_field_info())
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
            Also, the original implementation of TMCP does not support targeted messages, only broadcasts. So we are going to instance the message and replace
            the index of the sender with the index of the receiver.
        """

        # Receive and parse all new matchcomms messages into TMCPMessage objects.
        new_messages: List[TMCPMessage] = self.tmcp_handler.recv()

        # Decide what to do with your mateys
        if self.captain:
            for index in self.team_actions:
                success = False
                message = None

                # If the last message was Kick-off we need to repeat it a couple of times due to Captain roles still being negotiated
                if index in self.last_sent and self.last_sent[index] == self.team_actions[index] and self.last_sent[index] != KICKOFF:
                    continue

                if self.team_actions[index] == KICKOFF:
                    message = TMCPMessage.demo_action(self.team, index, -1)

                elif self.team_actions[index] == GEN_DEFEND:
                    message = TMCPMessage.boost_action(self.team, index, GEN_DEFEND)

                elif self.team_actions[index] == CLUTCH_DEFEND:
                    message = TMCPMessage.boost_action(self.team, index, CLUTCH_DEFEND)

                elif self.team_actions[index] == BALL:
                    message = TMCPMessage.ball_action(self.team, index)

                elif self.team_actions[index] == RECOVERY:
                    message = TMCPMessage.defend_action(self.team, index)


                if index == self.index:
                    self.parse_message(message)

                success = self.tmcp_handler.send(message)

                if success:
                    self.last_sent[index] = self.team_actions[index]

        # Check if there are new orders
        else:
            # Handle TMCPMessages.
            for message in new_messages:
                if message.index == self.index:
                    self.parse_message(message)

    def parse_message(self, message):
        """ Converts a message into actions
            Only update action if the current one is interruptible
        """
        if self.action != None and not self.action.interruptible():
            return

        if message.action_type == ActionType.DEMO:
            self.logger.info("Got it, car " + str(self.index) + " is supposed to kick off!")
            self.action = kickoffs.choose_kickoff(self.info, self.info.cars[self.index])

        elif message.action_type == ActionType.BOOST:
            self.action = base_policy.general_defense(self.info, self.info.cars[self.index], clutch=(message.target == CLUTCH_DEFEND))

        elif message.action_type == ActionType.DEFEND:
            self.action = Recovery(self.info.cars[self.index])


    def check_resets(self, packet):
        # cancel action if a kickoff is happening and current action isn't a kickoff action
        if packet.game_info.is_kickoff_pause:
            for index in self.team_actions:
                if not isinstance(self.team_actions[index], Kickoff):
                    self.team_actions[index] = None

        # reset action when another car hits the ball
        touch = packet.game_ball.latest_touch
        if (touch.time_seconds > self.last_latest_touch_time and touch.player_name != packet.game_cars[self.index].name):
            self.last_latest_touch_time = touch.time_seconds

            # don't reset when we're dodging, wavedashing or recovering
            if self.action and self.action.interruptible():
                self.action = None
