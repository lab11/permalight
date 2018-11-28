from light import Light
import yaml

with open("config.yaml", "r") as f:
	config = yaml.safe_load(f)

hostname = config['webapp_host']
port = config['webapp_port']
light_config = config['lights']

lights = {}
for light_idx in light_config:
	light = Light(channel = light_config[light_idx]['channel'], webapp_host=hostname, webapp_port=port)
	lights[light_idx] = light

print(lights['light0'].get_state())
lights['light0'].off()
# lights['light0'].on()
