from light import Light
from controller import Controller
import signal
import sys

def signal_handler(sig, frame):
	sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

controller = Controller(config_file='settings.yaml')
# controller.start()
# controller.permit_joining(interval=0xf0)

# controller.add_groups(light_address=0xdfc3, light_ep=0x40, group_address=0xaaab)
# controller.add_groups(light_address=0xc170, light_ep=0x40, group_address=0xaaab)

group = Light(0xaaab, 0x40, controller, is_group=True)
group.toggle()