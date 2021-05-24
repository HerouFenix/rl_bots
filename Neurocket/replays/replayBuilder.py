import sys
import json
import numpy as np

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

class Ball:
    def __init__(self, position, linear_velocity, angular_velocity):
        self.position = position
        self.linear_velocity = linear_velocity
        self.angular_velocity = angular_velocity

class Player:
    def __init__(self, team, position, linear_velocity, angular_velocity):
        self.team = team
        self.position = position
        self.linear_velocity = linear_velocity
        self.angular_velocity = angular_velocity

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

def parse_file(fname):
    with open(fname) as f:
        data = Struct(json.load(f))
    return data

gamestates = []
actors = {}

def removeDeletedActors(frame, actors):
    for actor in frame.deleted_actors:
        #print("Deleted object of type %s" % actors[actor]["object"])
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
        if data.objects[actor.object_id] == "Archetypes.Car.Car_Default":
            print("New car:", data.names[actor.name_id], data.objects[actor.object_id])

def updateState(frame, actors, gamestate):
    if not isinstance(frame, list):
        frame = [frame]
    for tick, f in enumerate(frame):
        getNewActors(f, actors)
        updateActors(f, actors)
        removeDeletedActors(f, actors)

        new_game_state = {"tick": tick}
        for v in actors.values():
            if v["object"] == "Archetypes.Teams.Team0":
                new_game_state["blue_score"] = v["Int"] if "Int" in v else 0
            elif v["object"] == "Archetypes.Teams.Team1":
                new_game_state["orange_score"] = v["Int"] if "Int" in v else 0
            elif v["object"] == "Archetypes.Ball.Ball_Default":
                if "RigidBody" in v:
                    body = v["RigidBody"]
                    if not body.sleeping:
                        new_game_state["ball"] = (body.location.x, body.location.y, body.location.z,
                                                body.linear_velocity.x, body.linear_velocity.y, body.linear_velocity.z,
                                                body.angular_velocity.x, body.angular_velocity.y, body.angular_velocity.z)
            elif "VehiclePickup_Boost" in v["object"]:
                if "boosts" in new_game_state:
                    new_game_state["boosts"].append(v)
                else:
                    new_game_state["boosts"] = [v]
            
        if "ball" in new_game_state:
            gamestate.append(new_game_state)

if __name__ == "__main__":
    fname = sys.argv[1]

    data = parse_file(fname)

    updateState(data.network_frames.frames, actors, gamestates)

    #for a in actors.values():
    #    print(a["actor_id"], a["object"])

    #for g in gamestates:
    #    for b in g["boosts"]:
    #        if "Enum" in b:
    #            print(b["PickupNew"], b["Enum"])
    #        else:
    #            print(b["PickupNew"], "Insigator: %s" % actors[b["PickupNew"].instigator]["object"])