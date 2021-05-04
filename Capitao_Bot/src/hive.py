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

from Sailor import Sailor
from captain_strat import CaptainStrategy

class CapitaoBotHivemind(PythonHivemind):
    def initialize_hive(self, packet: GameTickPacket) -> None:
        self.logger.info("Initialising Crew..")

        # Find out team by looking at packet.
        # drone_indices is a set, so you cannot just pick first element.
        self.index = next(iter(self.drone_indices))
        self.team = packet.game_cars[self.index].team

        # Identifying the captain
        self.im_captain = self.index == min(self.drone_indices)
        self.strategy = CaptainStrategy()

        # Initialise objects and attributes
        # Its better to use a dict, since indexes matter
        self.crew = {index: Sailor(index) for index in self.drone_indices}

    def get_outputs(self, packet: GameTickPacket) -> Dict[int, PlayerInput]:
        outputs = {}

        # This is good to keep at the beginning of get_output. It will allow you to continue
        # any sequences that you may have started during a previous call to get_output.
        for sailor_index in self.crew:
            sailor = self.crew[sailor_index]
            if sailor.active_sequence is not None and not sailor.active_sequence.done:
                controls = self.convert_scp_input(sailor.active_sequence.tick(packet))
                if controls is not None:
                    outputs[sailor_index] = controls

        # If everyone knows what to do, return
        if len([1 for sailor in self.crew if self.crew[sailor].active_sequence is None]) == 0: return outputs

        # Gather some information about our crew's positions and the ball
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

        # Draw some things to help understand what the bot is thinking
        # Make sure it's only one bot rendering this, to avoid race conditions
        if(self.im_captain):
            self.renderer.begin_rendering()

            for index in self.drone_indices:
                self.renderer.draw_line_3d(car_locations[index], target_location, self.renderer.white())

            self.renderer.draw_string_3d(car_location, 1, 1, f'Speed: {car_velocity.length():.1f}', self.renderer.white())
            self.renderer.draw_rect_3d(target_location, 8, 8, True, self.renderer.cyan(), centered=True)
            
            self.renderer.end_rendering()

        # Execute 1 step of each Sailor's plan
        for index in self.crew:
            sailor = self.crew[index]
            if sailor.plan is None:
                continue

            sailor.plan.step(self.info.time_delta)
            sailor.controls = sailor.plan.controls

            if sailor.plan.finished:
                sailor.plan = None

        # Return a dictionary where the keys are indices of your drones and
        # the values are PlayerInput objects (the controller inputs).
        return {index: self.crew[index].get_input() for index in self.crew}

    def begin_front_flip(self, packet, sailor):
        # Do a front flip. We will be committed to this for a few seconds and the bot will ignore other
        # logic during that time because we are setting the active_sequence.
        sailor.active_sequence = Sequence([
            ControlStep(duration=0.05, controls=SimpleControllerState(jump=True)),
            ControlStep(duration=0.05, controls=SimpleControllerState(jump=False)),
            ControlStep(duration=0.2, controls=SimpleControllerState(jump=True, pitch=-1)),
            ControlStep(duration=0.8, controls=SimpleControllerState()),
        ])

        # Return the controls associated with the beginning of the sequence so we can start right away.
        return self.convert_scp_input(sailor.active_sequence.tick(packet))

    def convert_scp_input(self, scp) -> PlayerInput:
        return PlayerInput(
            throttle=scp.throttle,
            steer=scp.steer,
            pitch=scp.steer,
            yaw=scp.yaw,
            roll=scp.roll,
            jump=scp.jump,
            boost=scp.boost,
            handbrake=scp.handbrake,
            use_item=scp.use_item
        )


