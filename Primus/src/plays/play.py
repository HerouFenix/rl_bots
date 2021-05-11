from rlutilities.simulation import Input, Car

class Play:
    def __init__(self, car):
        self.car = car

        self.controls = Input()

        self.finished = False

        self.name = "NULL" 

    def step(self, dt: float):
        # Current step in the play's execution - To be implemented in each implementation of Play
        pass

    def interruptible(self):
        return False # Whether or not the play can be interrupted
