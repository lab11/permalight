from light import Light
from controller import Controller
import signal
import sys


controller = Controller(config_file='settings.yaml')
controller.start()
controller.permit_joining(interval=0xf0)
