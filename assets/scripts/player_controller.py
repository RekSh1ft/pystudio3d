# player_controller.py — pystudio3d script

class PlayerController:
    def start(self, obj):
        self.speed = 5.0
        self.jump_force = 8.0
        self.velocity_y = 0.0
        self.grounded = True
        print(f"PlayerController started on {obj.name}")

    def update(self, obj, dt):
        # simple gravity
        if not self.grounded:
            self.velocity_y -= 9.8 * dt
            obj.transform.position[1] += self.velocity_y * dt
            if obj.transform.position[1] <= 0.5:
                obj.transform.position[1] = 0.5
                self.velocity_y = 0.0
                self.grounded = True

    def jump(self, obj):
        if self.grounded:
            self.velocity_y = self.jump_force
            self.grounded = False

    def on_destroy(self, obj):
        print(f"PlayerController destroyed on {obj.name}")
