from typing import List

from rlbot.agents.base_agent import BaseAgent, GameTickPacket, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

from tmcp import TMCPHandler, TMCPMessage

from util.vec import Vec3
from util.utilities import physics_object, Vector

from policy import base_policy, marujo_strategy
from tools.drawing import DrawingTool
from util.game_info import GameInfo

from policy.macros import ACK, KICKOFF, CLEAR, DEFENSE, UNDEFINED

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


class Captain(BaseAgent):
    def __init__(self, name, team, index):
        super().__init__(name, team, index)

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

        # Team actions {index: Stance}
        self.team_actions = {}
        self.last_sent = {}
        self.stance = UNDEFINED
        self.negotiated = False


    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        # Handle the packet
        self.parse_packet(packet)

        # Check if our action needs to change
        self.check_resets(packet)

        # Choosing the action: only the captain decides
        if self.captain:
            my_team = [i for i in range(self.info.num_cars) if self.info.cars[i].team == self.team]
            self.team_actions = base_policy.choose_stance(self.info, self.info.cars[self.index], my_team)
        
        # Send / Receive TMCP messages
        self.handle_comms(packet)

        # When you're finished with the action or if it has been cancelled or the game has just reset, reconsider team strategy
        if self.action == None or self.action.finished:
            if self.captain:
                self.team_actions = base_policy.choose_stance(self.info, self.info.cars[self.index], my_team)

            # Pick action according to previous orders
            self.action = marujo_strategy.choose_action(self.info, self.info.cars[self.index], self.stance)

        # Execute action
        if self.action is not None:
            self.action.step(self.info.time_delta)
            self.controls = self.action.controls

            if RENDERING:
                self.renderer.draw_string_3d(self.info.cars[self.index].position + vec3(0,0,10), 2, 2, self.action.name, self.renderer.white())

                self.renderer.draw_line_3d(self.info.cars[self.index].position, self.info.ball.position, self.renderer.white())
                self.renderer.draw_string_3d(self.info.cars[self.index].position + vec3(0,0,-5), 1, 1, f'Speed: {norm(self.info.cars[self.index].velocity):.1f}', self.renderer.white())
                self.renderer.draw_rect_3d(self.info.ball.position , 8, 8, True, self.renderer.cyan(), centered=True)
                
        if RENDERING:
            self.draw.execute()

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

    def handle_comms(self, packet):
        """ Responsible for handling the TMCP packets sent in the previous iteration.
            Marujos read messages, captains send them. (general rule)
            TMCP only supports a pre-defined set of messages, so we will be adding a few by changing certain parameters.
            Also, the original implementation of TMCP does not support targeted messages, only broadcasts. So we are going to instance the message and replace
            the index of the sender with the index of the desired receiver.
        """

        # Decide what to do with your mateys
        if self.captain:
            for index in self.team_actions:
                if index in self.last_sent and self.last_sent[index] == self.team_actions[index] and self.last_sent[index] != KICKOFF:
                    continue
                
                message = TMCPMessage.boost_action(self.team, index, self.team_actions[index]) # Send the stance to maroojo

                if index == self.index:
                    self.stance = message.target

                else:
                    succ = self.tmcp_handler.send(message)
                    if not succ:
                        self.logger.warn("Failed to send message to" + str(index))

                self.last_sent[index] = self.team_actions[index]


        # Check if there are new orders
        else:
            # Receive and parse all new matchcomms messages into TMCPMessage objects.
            while True:
                new_messages: List[TMCPMessage] = self.tmcp_handler.recv()

                # Handle TMCPMessages, which for marujos is pretty much just updating stance.
                for message in new_messages:
                    if message.index == self.index and message.team == self.team:
                        if not (packet.game_info.is_kickoff_pause and message.target not in [KICKOFF, DEFENSE]):
                            self.stance = message.target

                if self.stance != UNDEFINED:
                    self.negotiated = True
                    break

    def check_resets(self, packet):

        # cancel maneuver if a kickoff is happening and current maneuver isn't a kickoff maneuver
        if packet.game_info.is_kickoff_pause and not self.negotiated:
            self.action = None
            self.stance = UNDEFINED

        if self.negotiated and not packet.game_info.is_kickoff_pause:
            self.negotiated = False

        # reset action when another car hits the ball
        touch = packet.game_ball.latest_touch
        if (touch.time_seconds > self.last_latest_touch_time and touch.player_name != packet.game_cars[self.index].name):
            self.last_latest_touch_time = touch.time_seconds

            # don't reset when we're dodging, wavedashing or recovering
            if self.action and self.action.interruptible():
                self.action = None
                return True

        # reset action if we are not clearing, if its interruptible and the ball is entering the danger zone
        # if ball is in a dangerous position, clear it, be it with a clear or with a well-alligned strike   
        dangerous = marujo_strategy.danger(self.info, self.info.cars[self.index])
        if (dangerous and self.stance != CLEAR and self.action and self.action.interruptible()):
            self.stance = CLEAR
            self.action = None
            return True

        return False

