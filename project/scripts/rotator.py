# rotator.py — pystudio3d script

class Rotator:
    def start(self, obj):
        self.speed = 90.0  # degrees per second

    def update(self, obj, dt):
        obj.transform.rotation[1] += self.speed * dt
        if obj.transform.rotation[1] > 360:
            obj.transform.rotation[1] -= 360

    def on_destroy(self, obj):
        pass
