import os

from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.structures.game_data_struct import GameTickPacket

from tmcp import TMCPHandler, TMCPMessage, ActionType

from util.drive import steer_toward_target
from util.vec import Vec3
from util.utilities import physics_object, Vector

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
        # Try to figure out if you really are the captain or a marujo
        # Assume you're the captain, if anyone tells you their index is lower than yours, adjust
        self.captain = True

    def initialize_agent(self):
        self.tmcp_handler = TMCPHandler(self)
        self.allies = []
        self.enemies = []

    def parse_packet(self, packet):
        """
        Updates information about my team from a given packet. Location, velocity, rotation and boost level. Also useful to keep everyone in check with who the captain is.
        """
        for i in range(packet.num_cars):
            if i != self.index:
                car = packet.game_cars[i]

                # Checking who the captain is
                if self.captain and i < self.index and car.team == self.team:
                    self.captain = False
                    self.logger.info("Just got demoted.. captain now is " + str(i))
                    self.tmcp_handler.send_boost_action(-420)



                # Fetching relevant information about my team
                _obj = physics_object()
                _obj.index = i
                _obj.team = car.team
                _obj.location = Vector([car.physics.location.x, car.physics.location.y, car.physics.location.z])
                _obj.velocity = Vector([car.physics.velocity.x, car.physics.velocity.y, car.physics.velocity.z])
                _obj.rotation = Vector([car.physics.rotation.pitch, car.physics.rotation.yaw, car.physics.rotation.roll])
                _obj.avelocity = Vector([car.physics.angular_velocity.x, car.physics.angular_velocity.y, car.physics.angular_velocity.z])
                _obj.boostLevel = car.boost
                #_obj.local_location = localizeVector(_obj,self.me)

                if car.team == self.team:
                    self.allies.append(_obj)
                else:
                    self.enemies.append(_obj)

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:

        self.parse_packet(packet)

        # Marujos read messages, captains send them
        if self.captain:
            # Decide what to do with your mateys
            pass
        else:
            # Check if there are new orders
            pass

        # Receive and parse all new matchcomms messages into TMCPMessage objects.
        new_messages: List[TMCPMessage] = self.tmcp_handler.recv()

        # Handle TMCPMessages.
        for message in new_messages:
            if message.action_type == ActionType.BOOST:
                print(message)




        # Gather some information about our car and the ball
        my_car = packet.game_cars[self.index]
        car_location = Vec3(my_car.physics.location)
        car_velocity = Vec3(my_car.physics.velocity)
        ball_location = Vec3(packet.game_ball.physics.location)

        # By default we will chase the ball, but target_location can be changed later
        target_location = ball_location

        # Draw some things to help understand what the bot is thinking
        self.renderer.draw_line_3d(car_location, target_location, self.renderer.white())
        self.renderer.draw_string_3d(car_location, 1, 1, f"Speed: {car_velocity.length():.1f}", self.renderer.white(),)
        self.renderer.draw_rect_3d(
            target_location, 8, 8, True, self.renderer.cyan(), centered=True
        )

        controls = SimpleControllerState()
        controls.steer = steer_toward_target(my_car, target_location)
        controls.throttle = 1.0

        return controls

    def receive_coms(self):
        # Process up to 50 messages per tick.
        for _ in range(50):
            try:
                # Grab a message from the queue.
                msg = self.matchcomms.incoming_broadcast.get_nowait()
            except:
                break

            # This message either isn't following the standard protocol
            # or is intended for the other team.
            # DO NOT spy on the other team for information!
            if "tmcp_version" not in msg or msg["team"] != self.team:
                continue

            # Will's handler checks to make sure the message is valid.
            # Here we are keeping it as simple as possible.

            # If we made it here we know it's information relevant to our team.
            # Let's save it in a dictionary for reference later.
            # self.ally_actions[msg["index"]] = msg

    def send_coms(self):
        # Let's assume that our bot is attacking the ball and aiming for prediction slice 100.
        outgoing_msg = {
            "tmcp_version": [1, 0],
            "team": self.team,
            "index": self.index,
            "action": {
                "type": "ROLE_CALL",
                # You'll likely have the ball predictions cached locally.
                # This implementation is for demonstration purposes only.
                "payload": self.index,
            },
        }
        self.matchcomms.outgoing_broadcast.put_nowait(outgoing_msg)