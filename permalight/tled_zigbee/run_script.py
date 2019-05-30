from light import Light
from controller import Controller
import yaml

with open('settings.yaml', 'r') as fp:
	config = yaml.safe_load(fp)

controller = Controller(config_file='settings.yaml')

objects = {}
'''
for light in config['lights']:
	for name in light:
		obj = Light(address=light[name]['address'], endpoint=light[name]['endpoint'], controller=controller, is_group=False)
		objects[name] = obj
'''
for light in config['groups']:
	for name in light:
		obj = Light(address=light[name]['address'], endpoint=light[name]['endpoint'], controller=controller, is_group=True)
		objects[name] = obj

'''
	light_objects: {'light1': Light(address= 0xb175, endpoint= 0x40), 'light2': Light(address= 0x4748, endpoint= 0x40)}
'''

# controller.start()
# light1 = light_objects['light1']
group1 = objects['group1']
group2 = objects['group2']
# light2 = light_objects['light2']
# light1.set_level(0x0)
# light2.set_level(0xf0)
# light1.on()
#group1.toggle()
group2.set_level(20, print_return=True)
print("done")
group1.set_level(100, print_return=True)
#group2.toggle(print_return=False)

# controller.synchronous_read()
# controller.synchronous_read()
# controller.synchronous_read()
