from plays.strikes.aerial import AerialStrike
from plays.strikes.strike import Strike, DodgeStrike, BumpStrike, CloseStrike

from rlutilities.linear_algebra import vec3, normalize
from rlutilities.simulation import Ball

from util.math import ground_direction,ground_distance

"""
Clears are basically just a variant of a normal strike in which Primus simply trys to bump the ball towards 
the direction between it and the ball (it doesn't care where the ball goes to, it just wants to make it go away fast)
"""

CLEAR_DISTANCE = 1000.0 # How far away we want to shoot the ball

# Several points in the center horizontal line of the arena (y = 0) and sides (x = 4096 or x = -4096)
points = [vec3(0+i,0,0) for i in range(-4000, 4000, 500)] + [vec3(4096,0+i,0) for i in range(-5000, 5000, 500)] + [vec3(-4096,0+i,0) for i in range(-5000, 5000, 500)]

class DodgeClear(DodgeStrike):
    def configure(self, intercept):
        self.name = "DodgeClear"

        #self.target = ground_direction(self.car.position, intercept.ball.position)
        #self.target = self.target + normalize(self.target) * CLEAR_DISTANCE

        self.target = self.pick_easiest_target(self.car, intercept.ball, points)

        super().configure(intercept)

class BumpClear(BumpStrike):
    def configure(self, intercept):
        self.name = "BumpClear"

        #self.target = ground_direction(self.car.position, intercept.ball.position)
        #self.target = self.target + normalize(self.target) * CLEAR_DISTANCE
        
        self.target = self.pick_easiest_target(self.car, intercept.ball, points)
        
        super().configure(intercept)

class AerialClear(AerialStrike):
    def configure(self, intercept):
        self.name = "AerialClear"
        
        #self.target = ground_direction(self.car.position, intercept.ball.position)
        #self.target = self.target + normalize(self.target) * CLEAR_DISTANCE
        
        self.target = self.pick_easiest_target(self.car, intercept.ball, points)
        
        super().configure(intercept)