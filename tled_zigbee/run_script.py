from light import Light
from controller import Controller
import yaml

with open('settings.yaml', 'r') as fp:
	config = yaml.safe_load(fp)

controller = Controller(config_file='settings.yaml')

light_objects = {}
for light in config['lights']:
	for name in light:
		obj = Light(address=light[name]['address'], endpoint=light[name]['endpoint'], controller=controller)
		light_objects[name] = obj

'''
	light_objects: {'light1': Light(address= 0xb175, endpoint= 0x40), 'light2': Light(address= 0x4748, endpoint= 0x40)}
'''

controller.start()
# light1 = light_objects['light1']
light2 = light_objects['light2']
# light1.set_level(0x0)
# light2.set_level(0xf0)
# light1.on()
light2.toggle()

# controller.synchronous_read()
# controller.synchronous_read()
# controller.synchronous_read()
