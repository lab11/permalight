from light import Light
from controller import Controller
import signal
import sys


controller = Controller(config_file='settings.yaml')
#controller.start()
#controller.permit_joining(interval=0xf0)

controller.add_groups(light_address=0xbacb, light_ep=0x40, group_address=0xaaad)
controller.add_groups(light_address=0x1b97, light_ep=0x40, group_address=0xaaad)


# group = Light(0xaaad, 0x40, controller, is_group=True)
# group.toggle()
