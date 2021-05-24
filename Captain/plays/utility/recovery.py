from plays.play import Play
from rlutilities.linear_algebra import vec3, dot, norm, angle_between, normalize, cross, mat3, look_at, xy
from rlutilities.mechanics import AerialTurn
from rlutilities.simulation import Car, Input, sphere, Field
from util.math import forward, three_vec3_to_mat3


class Recovery(Play):
    """
    Land smoothly and recover from an aerial
    """

    def __init__(self, agent, jump_when_upside_down=True):
        super().__init__(agent)

        self.jump_when_upside_down = jump_when_upside_down
        self.landing = False
        self.aerial_turn = AerialTurn(self.car)

        self.trajectory = []
        self.landing_pos = None

        self.name = "Recovering"

    def simulate_landing(self):
        pos = vec3(self.car.position)
        vel = vec3(self.car.velocity)
        grav = vec3(0, 0, -650)
        self.trajectory = [vec3(pos)]
        self.landing = False
        collision_normal = None

        dt = 1/60
        simulation_duration = 0.8
        for i in range(int(simulation_duration / dt)):
            pos += vel * dt
            vel += grav * dt
            if norm(vel) > 2300: vel = normalize(vel) * 2300
            self.trajectory.append(vec3(pos))

            collision_sphere = sphere(pos, 50)
            collision_ray = Field.collide(collision_sphere)
            collision_normal = collision_ray.direction

            if (norm(collision_normal) > 0.0 or pos[2] < 0) and i > 20:
                self.landing = True
                self.landing_pos = pos
                break

        if self.landing:
            u = collision_normal
            f = normalize(vel - dot(vel, u) * u)
            l = normalize(cross(u, f))
            self.aerial_turn.target = three_vec3_to_mat3(f, l, u)
        else:
            target_direction = normalize(normalize(self.car.velocity) - vec3(0, 0, 3))
            self.aerial_turn.target = look_at(target_direction, vec3(0, 0, 1))

    def step(self, dt):
        self.simulate_landing()

        self.aerial_turn.step(dt)
        self.controls = self.aerial_turn.controls

        self.controls.boost = angle_between(self.car.forward(), vec3(0, 0, -1)) < 1.5 and not self.landing
        self.controls.throttle = 1  # If we're upsidedown and on the floor accelerate to fix

        # Jump if car is upside down and all wheels touching floor (cool for when we're on the ceiling)
        if (
            self.jump_when_upside_down
            and self.car.on_ground
            and dot(self.car.up(), vec3(0, 0, 1)) < -0.95
        ):
            self.controls.jump = True
            self.landing = False
            
        else:
            self.finished = self.car.on_ground