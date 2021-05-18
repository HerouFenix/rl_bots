from plays.actions.drive import Drive, Stop, AdvancedDrive
from plays.play import Play

from rlutilities.linear_algebra import vec3, dot
from rlutilities.simulation import Car

from util.game_info import GameInfo
from util.math import nearest_point, farthest_point, ground_distance, ground_direction, ground, angle_to,distance, angle_between, abs_clamp

class Defense(Play):
    """
    General defense play.
    Get into a defense position (pick up boost along the way), turn to face the ball and stop and wait for the ball
    """

    # TODO: TRY WITHOUT A TIMEOUT AND INSTEAD SET AS FINISHED IF WE'VE STOPPED

    DURATION = 0.5 # How long we wait for before terminating the play (and maybe restarting it)
    BOOST_LOOK_RADIUS = 1200 # How far away a boostpad can be before being discarded
    BOOST_LOOK_ANGLE = 2.0 # How far away (in terms of angle difference) the boost pad can be before its discaded

    def __init__(self, agent, state, face_target, distance_from_target, force_nearest=False):
        super().__init__(agent)

        self.state = state
        self.face_target = face_target

        dist = min(distance_from_target, ground_distance(face_target, self.state.net.center) - 50)
        target_pos = ground(face_target) + ground_direction(face_target, self.state.net.center) * dist

        near_net = abs(self.car.position[1] - self.state.net.center[1]) < 3000 # Check if we're near our net
        side_shift = 400 if near_net else 1800

        points = target_pos + vec3(side_shift, 0, 0), target_pos - vec3(side_shift, 0, 0)
        target_pos = nearest_point(face_target, points) if near_net or force_nearest else farthest_point(face_target, points)

        if abs(face_target[0]) < 1000 or ground_distance(self.car, face_target) < 1000:
            target_pos = nearest_point(self.car.position, points)
        target_pos = vec3(
            abs_clamp(target_pos[0], 4096 - 500),
            abs_clamp(target_pos[1], 5120 - 500),
            target_pos[2]
        )

        self.travel = AdvancedDrive(agent, target_pos)
        self.travel.finish_distance = 800 if near_net else 1500 # Use fancy driving if far aways

        self.drive = Drive(agent)
        self.stop = Stop(agent)

        self.start_time = agent.time

        self.boost_pad = None

        self.name = "SettingUp"

        self.stopped = False

    def interruptible(self):
        return self.travel.interruptible() or self.stopped

    def step(self, dt):
        self.travel.step(dt)

        if self.travel.finished:
            # If we're done traveling, turn around to face the target
            if angle_to(self.car, self.face_target) > 0.3:
                self.drive.target_pos = self.face_target
                self.drive.target_speed = 1000
                self.drive.step(dt)
                self.controls = self.drive.controls
                self.controls.handbrake = False
                self.stopped = False

            else:
                self.stop.step(dt)
                self.controls = self.stop.controls
                self.stopped = True

        else:
            self.stopped = False
            
            self.boost_pad = None

            # Collect boost pads during travel
            if self.car.boost < 90 and self.travel.interruptible():
                to_target = ground_direction(self.car, self.travel.target)

                for pad in self.state.large_boost_pads + self.state.small_boost_pads:
                    to_pad = ground_direction(self.car, pad)

                    if(
                        pad.is_active and distance(self.car, pad) < self.BOOST_LOOK_RADIUS
                        and angle_between(to_target, to_pad) < self.BOOST_LOOK_ANGLE
                    ):
                        self.boost_pad = pad
                        self.drive.target_pos = pad.position
                        self.drive.target_speed = 2200
                        self.drive.step(dt)
                        self.controls = self.drive.controls

                        self.name = "SettingUp (Refueling)"
                        break
                
                if self.boost_pad is None: # If we're not chasing a boost pad, go to position
                    self.name = "SettingUp"
                    self.controls = self.travel.controls

        # Avoid boosting unless really far away
        if self.car.boost < 100 and ground_distance(self.car, self.travel.target) < 4000: self.controls.boost = False

        self.finished = self.travel.driving and self.car.time > self.start_time + self.DURATION


class GoToNet(Play):
    DURATION = 0.2 # How long we wait for before terminating the play (and maybe restarting it)
    BOOST_LOOK_RADIUS = 1200 # How far away a boostpad can be before being discarded
    BOOST_LOOK_ANGLE = 2.0 # How far away (in terms of angle difference) the boost pad can be before its discaded

    def __init__(self, agent, state, face_target):
        super().__init__(agent)

        self.state = state
        self.face_target = face_target

        dist = 0
        target_pos = ground(self.state.net.center) + ground_direction(self.state.net.center, self.state.net.center) * dist

        near_net = abs(self.car.position[1] - self.state.net.center[1]) < 3000 # Check if we're near our net
        side_shift = 400 if near_net else 1800

        points = target_pos + vec3(side_shift, 0, 0), target_pos - vec3(side_shift, 0, 0)
        target_pos = nearest_point(self.state.net.center, points)

        if abs(self.state.net.center[0]) < 1000 or ground_distance(self.car, self.state.net.center) < 1000:
            target_pos = nearest_point(self.car.position, points)
        target_pos = vec3(
            abs_clamp(target_pos[0], 4096 - 500),
            abs_clamp(target_pos[1], 5120 - 500),
            target_pos[2]
        )

        self.travel = AdvancedDrive(agent, target_pos)
        self.travel.finish_distance = 500
        if near_net:
            self.travel.drive.target_speed = 1100  # Prevent going too fast if near net

        self.drive = Drive(agent)
        self.stop = Stop(agent)

        self.start_time = agent.time

        self.name = "GoToNet"

        self.stopped = False

    def interruptible(self):
        return self.travel.interruptible() or self.stopped

    def step(self, dt):
        if self.travel.finished:
            # If we're done traveling, turn around to face the target
            if angle_to(self.car, self.face_target) > 0.5:
                self.drive.target_pos = self.face_target
                self.drive.target_speed = 1000
                self.drive.step(dt)
                self.controls = self.drive.controls
                #self.controls.handbrake = False
                self.stopped = False

            else:
                self.stop.step(dt)
                self.controls = self.stop.controls
                self.stopped = True

        else:
            self.travel.step(dt)

            self.stopped = False
            
            self.controls = self.travel.controls

        # Avoid boosting unless really far away
        if self.car.boost < 100 and ground_distance(self.car, self.travel.target) < 4000: self.controls.boost = False

        self.finished = (self.travel.driving or self.travel.finished) and self.car.time > self.start_time + self.DURATION