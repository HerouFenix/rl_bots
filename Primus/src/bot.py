from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection
from rlbot.utils.structures.game_data_struct import GameTickPacket

from rlutilities.linear_algebra import vec3, norm
from util.game_info import GameInfo

from plays import strategy

# USED JUST FOR TESTING PURPOSES - COMMENT AFTER
from plays.play import Play
from plays.actions.drive import Drive, Stop, AdvancedDrive, Arrive
from plays.kickoff.kickoff import SimpleKickoff, SpeedFlipDodgeKickoff
from plays.strikes.strike import Strike, DodgeStrike, BumpStrike, CloseStrike, SetupStrike, DribbleStrike
from plays.strikes.aerial import AerialStrike, DoubleAerialStrike
from plays.dribbles.dribble import Dribble
from plays.actions.jump import Jump, AirDodge, SpeedFlip, HalfFlip, AimDodge
from rlutilities.simulation import Input

TRAINING = False # Set to True if using a training scenario
DRAW_BALL_PREDICTIONS = False # Set to True if you want to show the ball prediction lines
DRAW_FLIGHT_PATH = True # Set to True if you want to show the ball flight path when aerialing

class Primus(BaseAgent):

    def __init__(self, name, team, index):
        super().__init__(name, team, index)

        self.state = None
        self.tick_counter = 0 # Used for RLBotTraining
        
        self.play = None # The play the bot is trying to execute
        self.controls: SimpleControllerState = SimpleControllerState()

        self.primus = None #The agent

    def initialize_agent(self):
        # Set up information about the boost pads now that the game is active and the info is available
        #self.boost_pad_tracker.initialize_boosts(self.get_field_info())

        # Set up information about the game (abstracted into the GameInfo class)
        self.state = GameInfo(self.team)
        self.state.set_mode("soccar")
        
        self.primus = self.state.cars[self.index]

    def get_output(self, packet: GameTickPacket):
        if TRAINING and self.tick_counter < 20:
            self.tick_counter += 1
            return Input()


        # Start by updating the game's state
        self.state.read_packet(packet, self.get_field_info())

        # If the bot is not attempting to do anything
        if self.play is None:
            # Get a play to execute
            #self.play = strategy.choose_play(self.state, self.primus)

            """Test individual moves"""
            # Jumps
            #self.play = Jump(self.primus, 1.0)
            #self.play = AirDodge(self.primus, 0.1,self.state.ball.position)
            #self.play = SpeedFlip(self.primus)
            #self.play = HalfFlip(self.primus)
            #self.play = AimDodge(self.primus, 0.8, self.state.ball.position)

            # Drive
            #self.play = Drive(self.primus,target_speed=5000)
            #self.play = AdvancedDrive(self.primus, self.state.ball.position)
            #self.play = Arrive(self.primus, arrival_time = 20.0)
            #self.play = Stop(self.primus)

            # Kickoffs
            #self.play = SimpleKickoff(self.primus, self.state)
            #self.play =  SpeedFlipDodgeKickoff(self.primus, self.state)

            # Strikes
            self.state.predict_ball()
            
            #self.play = Strike(self.primus, self.state, self.state.enemy_net.center)
            self.play = DodgeStrike(self.primus, self.state, self.state.enemy_net.center)
            #self.play = BumpStrike(self.primus, self.state, self.state.enemy_net.center)
            #self.play = CloseStrike(self.primus, self.state, self.state.enemy_net.center)
            #self.play = SetupStrike(self.primus, self.state, self.state.enemy_net.center)
            #self.play = DribbleStrike(self.primus, self.state, self.state.enemy_net.center) 

            #self.play = AerialStrike(self.primus, self.state, self.state.enemy_net.center)
            #aerial = AerialStrike(self.primus, self.state, self.state.enemy_net.center)
            #self.play = DoubleAerialStrike(aerial)
            
            # Dribble
            #self.play = Dribble(self.primus, self.state.ball, self.state.enemy_net.center)
                
            # Defense

        # If bot has picked a play, execute it
        if self.play is not None:
            self.play.step(self.state.time_delta)
            self.controls = self.play.controls

            if(self.play.finished): # If the bot finished its play
                # Get a play to execute
                #self.play = strategy.choose_play(self.state, self.primus) #Pick new play
                
                """Test individual moves"""
                # Jumps
                #self.play = Jump(self.primus, 1.0)
                #self.play = AirDodge(self.primus, 0.1,self.state.ball.position)
                #self.play = SpeedFlip(self.primus)
                #self.play = HalfFlip(self.primus)
                #self.play = AimDodge(self.primus, 0.8, self.state.ball.position)

                # Drive
                #self.play = Drive(self.primus,target_speed=5000)
                #self.play = AdvancedDrive(self.primus, self.state.ball.position)
                #self.play = Arrive(self.primus, arrival_time = 20.0)
                #self.play = Stop(self.primus)

                # Kickoffs
                #self.play = SimpleKickoff(self.primus, self.state)
                #self.play =  SpeedFlipDodgeKickoff(self.primus, self.state)

                # Strikes
                self.state.predict_ball()
                
                #self.play = Strike(self.primus, self.state, self.state.enemy_net.center)
                self.play = DodgeStrike(self.primus, self.state, self.state.enemy_net.center)
                #self.play = BumpStrike(self.primus, self.state, self.state.enemy_net.center)
                #self.play = CloseStrike(self.primus, self.state, self.state.enemy_net.center)
                #self.play = SetupStrike(self.primus, self.state, self.state.enemy_net.center)
                
                #self.play = DribbleStrike(self.primus, self.state, self.state.enemy_net.center) 
                
                #self.play = AerialStrike(self.primus, self.state, self.state.enemy_net.center)
                #aerial = AerialStrike(self.primus, self.state, self.state.enemy_net.center)
                #self.play = DoubleAerialStrike(aerial)


                # Dribble
                #self.play = Dribble(self.primus, self.state.ball, self.state.enemy_net.center)
                
                # Defense
        
        # Draw play name
        self.renderer.draw_string_3d(self.primus.position + vec3(0,0,10), 2, 2, self.play.name, self.renderer.white())

        self.renderer.draw_line_3d(self.primus.position, self.state.ball.position, self.renderer.white())
        self.renderer.draw_string_3d(self.primus.position + vec3(0,0,-5), 1, 1, f'Speed: {norm(self.primus.velocity):.1f}', self.renderer.white())
        self.renderer.draw_rect_3d(self.state.ball.position , 8, 8, True, self.renderer.cyan(), centered=True)

        # Draw Ball predictions 
        if DRAW_BALL_PREDICTIONS and len(self.state.ball_predictions) > 0:
            points = [ball.position for ball in self.state.ball_predictions]
            if len(points) > 1:
                self.renderer.draw_polyline_3d([vec3(p[0], p[1], 10) if p[2] < 10 else p for p in points], self.renderer.lime())

        # Draw Flight path
        if DRAW_FLIGHT_PATH:
            if isinstance(self.play,AerialStrike) and len(self.play.flight_path) > 0:  
                self.renderer.draw_polyline_3d([vec3(p[0], p[1], 10) if p[2] < 10 else p for p in self.play.flight_path], self.renderer.orange())
            elif isinstance(self.play,DoubleAerialStrike) and len(self.play.aerial_strike.flight_path) > 0:  
                self.renderer.draw_polyline_3d([vec3(p[0], p[1], 10) if p[2] < 10 else p for p in self.play.aerial_strike.flight_path], self.renderer.orange())

        return self.controls