
from engine.enums import Flag, Pulse, MovementType, Facing

class Animator:  # contains different animation functions
    def __init__(self, pet):
        self.frames = []
        self.index = 0
        self.timer = 0
        self.loop = True
        self.ticks_left = 0
        self.done = False

        self.pet = pet

    def set(self, frames, fps, loop, times_to_loop, holds=None): #sets the animatios. receives a list of PixMap (frames), int (fps) and a bool(loop)
        self.frames = frames
        self.fps = fps if fps > 0 else 0.001
        self.loop = loop
        self.times_to_loop = times_to_loop
        self.index = 0
        self.timer = 0
        self.holds = holds or {}
        self.ticks_left = self.hold_for(0)
        self.done = False
        
    def update(self, dt): #iterates over the list of frames with the speed of fps, loops if loop==True
        if self.done or not self.frames:
            return False

        self.timer += dt
        frame_time = 1 / self.fps

        if self.timer >= frame_time:
            self.timer -= frame_time
            self.ticks_left -= 1

            if self.ticks_left <= 0:
                self.index += 1

                # print(self.index)

                if self.index >= len(self.frames):
                    print("Animator: Pulse.ANIMATION_END ")
                    self.pet.state_machine.pulse(Pulse.ANIMATION_END)  # if the index of the frame is more than we have frames, the animation is considered finished(for ease of connecting animations together), else - not

                    if self.loop or self.times_to_loop >= 2 :
                        self.index = 0
                        self.times_to_loop -= 1
                    else:
                        self.index = len(self.frames) - 1
                        print("Animator: Flag.ANIMATION_FINISHED ")
                        self.pet.state_machine.raise_flag(Flag.ANIMATION_FINISHED)
                        self.done = True


                self.ticks_left = self.hold_for(self.index)


    def hold_for(self, index):
        return self.holds.get(index + 1, 1)

    def frame(self): #returns a single frame which should be displayed at the moment
        return self.frames[self.index]
