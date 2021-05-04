from typing import Dict

from rlbot.utils.structures.bot_input_struct import PlayerInput
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.agents.hivemind.python_hivemind import PythonHivemind
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection

from util.ball_prediction_analysis import find_slice_at_time
from util.boost_pad_tracker import BoostPadTracker
from util.drive import steer_toward_target
from util.sequence import Sequence, ControlStep
from util.vec import Vec3

# Link to Hivemind wiki: https://github.com/ViliamVadocz/Hivemind/wiki/

class CapitaoBotHivemind(PythonHivemind):
    def initialize_hive(self, packet: GameTickPacket) -> None:
        self.logger.info("Initialised!")

        # Find out team by looking at packet.
        # drone_indices is a set, so you cannot just pick first element.
        self.index = next(iter(self.drone_indices))
        self.team = packet.game_cars[self.index].team
        #self.crew = [Sailor(index) for index in self.drone_indices]

        # Identifying the captain
        self.im_captain = self.index == min(self.drone_indices)

        # Initialise objects and attributes here!
        # I suggest making a Car or Drone object for each of your drones
        # that will store info about them.
        self.active_sequence: Sequence = None
        self.boost_pad_tracker = BoostPadTracker()

    def get_outputs(self, packet: GameTickPacket) -> Dict[int, PlayerInput]:

        # 3 States: Kickoff, Attack, Defense

        ## Kickoff - rush to the ball if you're the closest to it

        ## Attack - if the ball is on the enemy field, allocate two "Sailors" to get there

        ## Defense - if the ball is on our field, allocate two "Sailors" to get here

        # Return a dictionary where the keys are indices of your drones and
        # the values are PlayerInput objects (the controller inputs).

        # Keep our boost pad info updated with which pads are currently active
        #self.boost_pad_tracker.update_boost_status(packet)

        # This is good to keep at the beginning of get_output. It will allow you to continue
        # any sequences that you may have started during a previous call to get_output.
        if self.active_sequence is not None and not self.active_sequence.done:
            controls = self.active_sequence.tick(packet)
            if controls is not None:
                return controls

        # Gather some information about our car and the ball
        my_car = packet.game_cars[self.index]
        car_location = Vec3(my_car.physics.location)
        car_locations = {index: Vec3(packet.game_cars[index].physics.location) for index in self.drone_indices}
        car_velocity = Vec3(my_car.physics.velocity)
        ball_location = Vec3(packet.game_ball.physics.location)

        # By default we will chase the ball, but target_location can be changed later
        target_location = ball_location

        if car_location.dist(ball_location) > 1500:
            # We're far away from the ball, let's try to lead it a little bit
            ball_prediction = self.get_ball_prediction_struct()  # This can predict bounces, etc
            ball_in_future = find_slice_at_time(ball_prediction, packet.game_info.seconds_elapsed + 2)

            # ball_in_future might be None if we don't have an adequate ball prediction right now, like during
            # replays, so check it to avoid errors.
            if ball_in_future is not None:
                target_location = Vec3(ball_in_future.physics.location)
                #self.renderer.draw_line_3d(ball_location, target_location, self.renderer.cyan())

        # Draw some things to help understand what the bot is thinking
        # Make sure it's only one bot rendering this, to avoid race conditions
        if(self.im_captain):
            self.renderer.begin_rendering()

            for index in self.drone_indices:
                self.renderer.draw_line_3d(car_locations[index], target_location, self.renderer.white())

            self.renderer.draw_string_3d(car_location, 1, 1, f'Speed: {car_velocity.length():.1f}', self.renderer.white())
            self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.cyan(), centered=True)
            
            self.renderer.end_rendering()

        #if 750 < car_velocity.length() < 800:
            # We'll do a front flip if the car is moving at a certain speed.
            #self.logger.info("Front flip!")

            #return self.begin_front_flip(packet)

        controls = PlayerInput(throttle=1.0, steer=steer_toward_target(my_car, target_location))

        #return {index: PlayerInput(throttle=1.0) for index in self.drone_indices}
        return {index: controls for index in self.drone_indices}
