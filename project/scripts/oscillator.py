# oscillator.py — pystudio3d script
import math

class Oscillator:
    def start(self, obj):
        self.amplitude = 1.0
        self.frequency = 1.0
        self._origin_y = obj.transform.position[1]
        self._t = 0.0

    def update(self, obj, dt):
        self._t += dt
        obj.transform.position[1] = (
            self._origin_y + math.sin(self._t * self.frequency * math.pi * 2) * self.amplitude
        )

    def on_destroy(self, obj):
        pass
