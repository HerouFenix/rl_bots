import sys
import json
import numpy as np
from numpy.core.defchararray import array

# Format expected by rlgym: 
#   Ticks
#   Blue Score
#   Orange Score
#   Boost Pads x34 (Boolean)
#   BallState(18 values)
#       Position(x,y,z)
#       LinearVelocity(x,y,z)
#       AngularVelocity(x,y,z)
#   PlayerInfo(38 values)
#       CarId
#       TeamNum
#       Position(x,y,z)
#       Quaternion(x, y, z, w)
#       LinearVelocity(x,y,z)
#       AngularVelocity(x,y,z)
#       Goals
#       Saves
#       Shots
#       Demolishes
#       Boost Pickups
#       IsDemoed
#       OnGround
#       Ball Touched
#       HasFlip
#       BoostAmount(Float)


class Struct:
    def __init__(self, d):
        self.__dict__.update(parse_dicts(d))

    def keys(self):
        return self.__dict__.keys()

    def items(self):
        return self.__dict__.items()

    def values(self):
        return self.__dict__.values()

    def __repr__(self) -> str:
        return repr(self.__dict__)
    
def parse_dicts(d):
    for k, v in d.items():
        if isinstance(v, dict):
            d[k] = Struct(v)
        elif isinstance(v, list):
            for idx, lv in enumerate(v):
                if isinstance(lv, dict):
                    v[idx] = Struct(lv)

    return d

fname = sys.argv[1]

with open(fname) as f:
    data = Struct(json.load(f))

gamestates = [{"score": (0,0)}]

firstFrame = data.network_frames.frames[0]
actors = {}

def removeDeletedActors(frame, actors):
    for actor in frame.deleted_actors:
        actors.pop(actor)

def updateActors(frame, actors):
    for actor in frame.updated_actors:
        id = actor.actor_id
        for k, v in actor.attribute.items():
            actors[id][k] = v

def getNewActors(frame, actors):
    for actor in frame.new_actors:
        id = actor.actor_id
        actors[id] = {"actor_id": id, "name": data.names[actor.name_id], "object": data.objects[actor.object_id]}

def updateState(frame, actors, gamestate):
    if not isinstance(frame, list):
        frame = [frame]
    for f in frame:
        getNewActors(f, actors)
        updateActors(f, actors)
        removeDeletedActors(f, actors)
    #for actor in frame.updated_actors:
    #    print("Actor: %d --- Object: %s" % (actor.actor_id, data.objects[actor.object_id]))

for i in range(500):
    updateState(data.network_frames.frames[i], actors, gamestates)

for a in actors.values():
    print(a["actor_id"], a["object"])

print(actors[0])