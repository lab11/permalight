#!/usr/bin/env python3

lights = {}
sensors = {}
sensors_to_lights = {}

def characterize_lights():
    # characterize lights
    # reuse old characterization if it exists
    if len(sensors_to_lights) != 0:
        return

    print("starting light characterizing measurements!")
    for light in self.lights:
        label = light.address
        if label is None:
            print('this light is wack!')
            print(light)
            continue
        self.current_light = label
        print(label)
        self.state = self.State.CHAR_LIGHT
        # TODO turn on the light
        time.sleep(5)
        # TODO turn off the light
        time.sleep(5)
        self.state = self.State.CHAR_IDLE

        # sweep through brightness
        #for brightness in range(0, 101, 10):
        #    print(brightness)
        #    # clear seen devices
        #    self.seen_sensors.clear()
        #    #print(brightness)
        #    self.current_brightness = brightness
        #    while(1):
        #        try:
        #            light.set_brightness(brightness/100*65535)
        #            break
        #        except lifxlan.errors.WorkflowException:
        #            print('Failed to set brightness ' + label)
        #    while(1):
        #        if self.seen_sensors == set([x for x in self.sensors.keys()]):
        #            break
        #        time.sleep(5)
        for sensor_id in self.sensors:
            baseline_lux = self.sensors[sensor_id].baseline
            measurement = self.sensors[sensor_id].light_char_measurements[light]

            # save because why not?
            with open(sensor_id + '_characterization.pkl', 'wb') as output:
                pickle.dump(self.sensors[sensor_id].light_char_measurements, output, pickle.HIGHEST_PROTOCOL)

    # generate primary light associations
    # eventually we can do smarter things than 1-to-1 mappings
    # for each sensor, see which light affected it the most
    for sensor_id in self.sensors:
        max_affect_light = (None, 50)
        for light in self.sensors[sensor_id].light_char_measurements:
            max_effect = self.sensors[sensor_id].light_char_measurements[light]
            if max_effect > max_affect_light[1]:
                max_affect_light = (light, max_effect)
        self.sensors_to_lights[sensor_id] = max_affect_light[0]
    print(self.sensors_to_lights)
    with open('sensor_light_mappings.pkl', 'wb') as output:
        pickle.dump(self.sensors_to_lights, output, pickle.HIGHEST_PROTOCOL)

    self.current_light = None
    self.current_brightness = None

CONFIG_FILE = '/home/pi/permalight/config.yaml'
with open(CONFIG_FILE, 'r') as fp:
  config = yaml.safe_load(fp)
sensor_list = config['sensors']
light_list = config['groups']
#sensor_light_map = config['map']

