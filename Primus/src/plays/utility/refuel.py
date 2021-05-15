from plays.play import Play
from rlutilities.linear_algebra import vec3, norm
from rlutilities.mechanics import AerialTurn
from rlutilities.simulation import Car, Pad
from util.math import distance
from util.game_info import GameInfo
from util.intercept import estimate_time
from plays.actions.drive import AdvancedDrive, Arrive

import math

class Refuel(Play):
    """
    Choose a large boost pad and go pick it up.
    """

    def __init__(self, agent, state, forbidden_pads = set(), small_refuel = False):
        super().__init__(agent)
        self.state = state
        self.small = small_refuel

        if not small_refuel:
            pads = set(state.large_boost_pads) - forbidden_pads
        else:
            pads = set(state.small_boost_pads) - forbidden_pads

        available_pads = {pad for pad in pads if pad.is_active or estimate_time(agent, pad.position) * 0.8 > pad.timer}
        pos = (state.ball.position + agent.position * 2 + state.net.center) / 4

        self.pad = min(available_pads, key=lambda pad: distance(pad.position, pos)) if available_pads else None

        self.pad_was_active = self.pad and self.pad.is_active # Used cus we might start by going to a pad that's not available but about to spawn

        self.travel = AdvancedDrive(agent, self.pad.position if self.pad else state.net.center, use_boost=not small_refuel, target_speed=1000 if small_refuel else 2300)

        self.target = self.travel.target
        self.name = "Refueling"

    def interruptible(self):
        return self.travel.interruptible()

    def step(self, dt):
        if self.pad is None:
            self.finished = True
            return

        # Slow down when we're about to pick up the boost, so we can turn faster afterwards
        if distance(self.car, self.pad) < norm(self.car.velocity) * 0.2:
            self.travel.drive.target_speed = 1400

        self.travel.step(dt)
        self.controls = self.travel.controls

        # End when someone picks up pad (whether that be us or someone else)
        if not self.pad.is_active and self.pad_was_active:
            self.finished = True
        self.pad_was_active = self.pad.is_active

        # If we're on top of the pad and boost is full, end (just in case the last end condition wasnt met)
        if self.car.boost > 99 or distance(self.car, self.pad) < 100:
            self.finished = True


    @staticmethod
    def best_boostpad(car, pads, pos):
        best_pad = None
        best_dist = math.inf

        for pad in pads:
            dist = distance(pos, pad.position)
            time_estimate = estimate_time(car, pad.position) * 0.7

            if dist < best_dist and (pad.is_active or pad.timer < time_estimate):
                best_pad = pad
                best_dist = dist

        return best_pad

