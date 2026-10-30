"""Turn-taking state machine for the live listener. Pure Python so it is testable without numpy.

One frame is 512 samples at 16 kHz (32 ms). The caller supplies Silero's speech probability per frame,
a callable that runs Smart Turn on the current turn audio, and whether the wake word fired in this frame.
"""

START_FRAMES = 8     # 256 ms of sustained speech before a turn starts (ignores clicks and breaths)
CHECK_FRAMES = 6     # ~190 ms of silence before asking Smart Turn whether the thought is complete
HARD_FRAMES = 47     # ~1.5 s of silence ends the turn even if Smart Turn says "incomplete"
MAX_FRAMES = 780     # ~25 s: very long turns are cut so recognition stays bounded
SPEECH, SILENCE = .5, .35


class TurnDetector:
    def __init__(self, standby=False):
        self.standby = standby
        self.reset()

    def reset(self):
        self.voiced = 0          # consecutive speech frames before the turn starts
        self.speaking = False    # a turn is in progress
        self.silent = 0          # consecutive silence frames inside the turn
        self.frames = 0          # frames since the turn started
        self.checked = False     # Smart Turn already consulted for this pause
        self.woken = False       # wake word heard during this turn

    def frame(self, probability, complete, wake=False):
        """Returns events for this frame: 'speech' (turn started), 'turn' (send it) or 'discard'."""
        self.woken = self.woken or wake
        if not self.speaking:
            self.voiced = self.voiced + 1 if probability >= SPEECH else 0
            if self.voiced < START_FRAMES:
                return []
            self.speaking = True
            self.frames = self.voiced
            return ['speech']
        self.frames += 1
        if probability >= SILENCE:
            self.silent = 0
            self.checked = False
        else:
            self.silent += 1
        done = self.frames >= MAX_FRAMES or self.silent >= HARD_FRAMES
        if not done and self.silent >= CHECK_FRAMES and not self.checked:
            self.checked = True
            done = complete() >= .5
        if not done:
            return []
        event = 'discard' if self.standby and not self.woken else 'turn'
        self.reset()
        return [event]
