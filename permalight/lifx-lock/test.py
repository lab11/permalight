from lifx import Controller
from lifx import Light

lock_server = "http://165.22.170.110:4000/"

controller = Controller(lock_server)
light = controller.discover(["Neal's light"])[0]

light.on()
light.set_level(1, 5000)
