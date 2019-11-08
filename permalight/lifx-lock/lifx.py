from lifxlan import errors, LifxLAN
from retrying import retry
import requests
import json
import time

class Controller():
  def __init__(self, lock_server=None):
    self.lan = LifxLAN()
    self.lights = []
    self.lock_server = lock_server
  @retry(stop_max_attempt_number=5, wait_random_min=1000, wait_random_max=2000)
  def discover(self, names=None):
    lifxlights = []
    if names is None:
      lifxlights = self.lan.get_lights()
    else:
      lifxlights = self.lan.get_devices_by_name(names).get_device_list()
    for light in lifxlights:
        print("success:")
        print(light.get_label())
        print(light.get_color())
        self.lights.append(Light(light.get_label(), self.lock_server, light))
    return sorted(self.lights, key=lambda x: x.name)

# generic wrapper for lifx light class
class Light():
    def __init__(self, name, lock_server=None, context=None):
        self.lock_server = lock_server
        self.name = name
        self.light = context
    def __str__(self):
        return(self.name)
    def __repr__(self):
        return(self.name)
    def grab_lock(func):
        def wrapper_grab_lock(self, *args, **kwargs):
            if self.lock_server is None:
                print("lock server is none")
                return
            token = None
            while(1):
                data = {'timeout_seconds':5}
                url = self.lock_server + "locks/" + self.light.get_mac_addr()
                try:
                    r = requests.get(url+ "/request", json=data)
                except Exception as e:
                    print(e)
                    return
                data = r.json()
                if not data["success"]:
                    print(data)
                    #if "remaining_time_seconds" in data:
                    #    print("light lock already held, sleeping " + str(data["remaining_time_seconds"]))
                    #    time.sleep(data["remaining_time_seconds"]+0.2)
                    print("not success")
                    return
                else:
                    token = data["lock"]["token"]
                    break
            result = func(self, *args, **kwargs)
            data = {"token": token}
            try:
                r = requests.post(url + "/release", json=data)
            except Exception as e:
                print(e)
                return
            return result
        return wrapper_grab_lock

    def ignore_except(func):
        def wrapper_ignore(self, *args, **kwargs):
            result = None
            try:
                result = func(self, *args, **kwargs)
            except Exception as e:
                print(e)
            return result
        return wrapper_ignore

    #@ignore_except
    @retry(stop_max_attempt_number=5, wait_random_min=1000, wait_random_max=2000)
    @grab_lock
    def off(self):
        self.light.set_power(0)

    @retry(stop_max_attempt_number=5, wait_random_min=1000, wait_random_max=2000)
    @grab_lock
    def on(self):
        self.light.set_power(1)

    @retry(stop_max_attempt_number=5, wait_random_min=1000, wait_random_max=2000)
    @grab_lock
    def toggle(self):
        if self.light.get_power() > 0:
            self.light.set_power(0)
        else: self.light.set_power(1)

    @retry(stop_max_attempt_number=5, wait_random_min=1000, wait_random_max=2000)
    @grab_lock
    def get_state(self):
        return self.light.get_power() > 0

    @retry(stop_max_attempt_number=5, wait_random_min=1000, wait_random_max=2000)
    @grab_lock
    def get_level(self):
        color = self.light.get_color()
        return color[2]/65535.0

    @retry(stop_max_attempt_number=5, wait_random_min=1000, wait_random_max=2000)
    @grab_lock
    def set_level(self, level, transition_time=1000):
        if level > 1:
            level = 1
        elif level < 0:
            level = 0
        color = list(self.light.get_color())
        color[2] = int(level * 65535.0)
        self.light.set_color(color, transition_time)
