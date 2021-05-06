import math

from rlutilities.linear_algebra import *

class physics_object:
    def __init__(self):
        self.location = Vector([0, 0, 0])
        self.velocity = Vector([0, 0, 0])
        self.rotation = Vector([0, 0, 0])
        self.avelocity = Vector([0, 0, 0])
        self.local_location = Vector([0, 0, 0])
        self.boostLevel = 0
        self.team = -1
        self.matrix = []

class Vector:
    def __init__(self, content): #accepts list of float/int values
        self.data = content

    def __str__(self):
        return str(self.data)

    def __repr__(self):
        return str(self)

    def __len__(self):
        return len(self.data)

    def __getitem__(self, item):
        return self.data[item]

    def vec3Convert(self):
        return vec3(self.data[0],self.data[1].self.data[2])

    def raiseLengthError(self,other, operation):
        raise ValueError(f"Tried to perform {operation} on 2 vectors of differing lengths")

    def raiseCrossError(self):
        raise ValueError("Both vectors need 3 terms for cross product")

    def __mul__(self, other):
        if len(self.data) == len(other.data):
            return Vector([self.data[i] * other[i] for i in range(len(other))])
        else:
            self.raiseLengthError(other,"multiplication")

    def __add__(self, other):
        if len(self.data) == len(other.data):
            return Vector([self.data[i] + other[i] for i in range(len(other))])
        else:
            self.raiseLengthError(other, "addition")

    def __sub__(self, other):
        if len(self.data) == len(other.data):
            return Vector([self.data[i] - other[i] for i in range(len(other))])
        else:
            self.raiseLengthError(other, "subtraction")

    def alignTo(self, rot):
        v = Vector([self.data[0], self.data[1], self.data[2]])
        v = Vector([v[0],math.cos(rot[0]) * v[1] + math.sin(rot[0]) * v[2],math.cos(rot[0]) * v[2] - math.sin(rot[0]) * v[1]])
        v = Vector([math.cos(-rot[1]) * v[0] + math.sin(-rot[1]) * v[2], v[1], math.cos(-rot[1]) * v[2] - math.sin(-rot[1]) * v[0]])
        v = Vector([math.cos(-rot[2]) * v[0] + math.sin(-rot[2]) * v[1], math.cos(-rot[2]) * v[1] - math.sin(-rot[2]) * v[0], v[2]])

        return v

    def crossProduct(self,other):
        if len(self.data) == 3 and len(other.data) == 3:
            newVec = [0,0,0]
            newVec[0] = self[1]*other[2] - self[2]*other[1]
            newVec[1] = self[2]*other[0] - self[0]*other[2]
            newVec[2] = self[0] * other[1] - self[1] * other[0]

            return Vector(newVec)


        else:
            self.raiseCrossError()

    def flatten(self):
        return Vector(self.data[:2]+[0])


    def magnitude(self):
        return math.sqrt(sum([x*x for x in self]))

    def normalize(self):
        mag = self.magnitude()
        if mag != 0:
            return Vector([x/mag for x in self])
        else:
            return Vector([0 for _ in range(len(self.data))])

    def dotProduct(self,other):
        product = 0
        for i,j in zip(self,other):
            product += i*j
        return product

    def scale(self,scalar):
        return Vector([x*scalar for x in self.data])


    def correction_to(self, ideal):
        current_in_radians = math.atan2(self[1], -self[0])
        ideal_in_radians = math.atan2(ideal[1], -ideal[0])

        correction = ideal_in_radians - current_in_radians
        if abs(correction) > math.pi:
            if correction < 0:
                correction += 2 * math.pi
            else:
                correction -= 2 * math.pi

        return correction


    def toList(self):
        return self.data

    def lerp(self,otherVector,percent): #percentage indicated 0 - 1
        percent = clamp(1,0,percent)
        originPercent = 1-percent

        scaledOriginal = self.scale(originPercent)
        other = otherVector.scale(percent)
        return scaledOriginal+other

def clamp(_max,_min,value):
    if value > _max:
        return _max
    if value < _min:
        return _min
    return value