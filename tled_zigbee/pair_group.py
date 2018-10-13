from light import Light
from controller import Controller

controller = Controller(config_file='settings.yaml')
controller.start()
# controller.permit_joining()

# controller.add_groups(light_address=0xb175, light_ep=0x40, group_address=0xaaab)
# controller.add_groups(light_address=0x4748, light_ep=0x40, group_address=0xaaab)

group = Light(0xaaab, 0x40, controller, is_group=True)
group.toggle()
