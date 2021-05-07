from rlbot.utils.structures.game_data_struct import GameTickPacket, FieldInfoPacket
from rlutilities.simulation import Game, Car, Ball, Pad, Input
from rlutilities.linear_algebra import vec3, vec2, norm, normalize, cross, rotation, dot, xy

class GameInfo(Game):
    def __init__(self, team):
        super().__init__()

        self.team = team

        # Boost Pads - contains Pad objects which store position and the time until boost is available
        self.large_boost_pads = []
        self.small_boost_pads = []

        # Ball Predictions
        self.ball_predictions = []

    def read_packet(self, packet: GameTickPacket, field_info: FieldInfoPacket):
        # The Game class contains

        # Get updated information about the game
        self.read_game_information(packet, field_info)
        
        # Update boost pad timers
        for pad in self.large_boost_pads:
            pad.timer = 10.0 - pad.timer
        for pad in self.small_boost_pads:
            pad.time = 4.0 - pad.timer

    def _get_large_boost_pads(self, field_info: FieldInfoPacket):
        # Get the large boost pads infos
        return [self.pads[i] for i in range(field_info.num_boosts) if field_info.boost_pads[i].is_full_boost]

    def _get_small_boost_pads(self, field_info: FieldInfoPacket):
        # Get the small boost pads infos
        return [self.pads[i] for i in range(field_info.num_boosts) if not field_info.boost_pads[i].is_full_boost]

    def get_teammates(self, car: Car):
        # Get all teammate's cars (i.e cars in the same team and with different id than our own)
        return [self.cars[i] for i in range(self.num_cars) if self.cars[i].team == self.team and self.cars[i].id != car.id]

    def get_opponents(self):
        return [self.cars[i] for i in range(self.num_cars) if self.cars[i].team != self.team]