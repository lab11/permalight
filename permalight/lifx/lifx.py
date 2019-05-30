from lifxlan import LifxLAN
from retrying import retry

class Controller():
  def __init__(self):
    self.lan = LifxLAN()
    self.lights = []
  @retry(stop_max_attempt_number=5, wait_random_min=1000, wait_random_max=2000)
  def discover(self, names=None):
    lifxlights = []
    if names is None:
      lifxlights = self.lan.get_lights()
    else:
      lifxlights = self.lan.get_devices_by_name(names).get_device_list()
    for light in lifxlights:
      for light in lifxlights:
          self.lights.append(Light(light.get_label(), light))
      return sorted(self.lights, key=lambda x: x.name)

# generic wrapper for lifx light class
class Light():
    def __init__(self, name, context=None):
        self.name = name
        self.light = context
    def __str__(self):
        return(self.name)
    @retry(stop_max_attempt_number=5, wait_random_min=1000, wait_random_max=2000)
    def off(self):
        self.light.set_power(0)
        self.light.set_power(0)
    @retry(stop_max_attempt_number=5, wait_random_min=1000, wait_random_max=2000)
    def on(self):
        self.light.set_power(1)
    @retry(stop_max_attempt_number=5, wait_random_min=1000, wait_random_max=2000)
    def toggle(self):
        if self.light.get_power() > 0:
            self.light.set_power(0)
        else: self.light.set_power(1)
    @retry(stop_max_attempt_number=5, wait_random_min=1000, wait_random_max=2000)
    def get_state(self):
        return self.light.get_power() > 0
    @retry(stop_max_attempt_number=5, wait_random_min=1000, wait_random_max=2000)
    def get_level(self):
        color = self.light.get_color()
        return color[2]/65535.0
    @retry(stop_max_attempt_number=5, wait_random_min=1000, wait_random_max=2000)
    def set_level(self, level, transition_time=1000):
        if level > 1:
            level = 1
        elif level < 0:
            level = 0
        color = list(self.light.get_color())
        color[2] = int(level * 65535.0)
        self.light.set_color(color, transition_time)

