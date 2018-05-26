from lifxlan import LifxLAN
import paho.mqtt.client as mqtt
from PID import PID
from enum import Enum
import numpy as np
import time
import dill as pickle
import json
from lightsensor import LightSensor
import os.path
import datetime

class LightControl:
    class State(Enum):
        IDLE = 0
        DISCOVER = 1
        CHARACTERIZE = 2
        CONTROL = 3

    def __init__(self, mqtt_address):
        self.state = self.State.IDLE

        self.lights = []
        self.sensors = {}
        self.sensors_to_lights = {}
        self.shades = []
        # keep track of sensors seen during
        # characterization steps
        self.seen_sensors = set()
        self.current_light = None
        self.current_brightness = None

        self.pid_controllers = {}

        self.lan = LifxLAN()

        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message

        self.mqtt_client.connect(mqtt_address)
        self.mqtt_client.loop_start()

    def discover(self, light_list, sensor_list, shade_list):
        # discover lights, shades, sensors
        if light_list is None:
            self.lights = self.lan.get_lights()
        else:
            for label in light_list:
                self.lights.append(self.lan.get_device_by_name(label))
                if self.lights[-1] is None:
                    print('failed to get light ' + label)
        for light in self.lights:
            pid = PID(300, 0, 50)
            pid.SetPoint = 100
            self.pid_controllers[light.label] = pid

            # turn all lights off
            init_color = [0, 0, 65535, 4000]
            light.set_color(init_color)
            light.set_power(0)

        # shade discover is kind of dumb right now
        self.shades = shade_list
        # start sensor discovery
        self.state = self.State.DISCOVER
        # sleep for some time to allow discovery
        # BLE sucks sometimes, eh?
        time.sleep(10)

    def characterize(self):
        if os.path.isfile('sensor_light_characterization.pkl'):
            with open('sensor_light_characterization.pkl', 'rb') as output:
                self.sensor = pickle.load(output)
        else:
            self.state = self.State.CHARACTERIZE
            print("starting characterizing measurements!")
            for light in self.lights:
                while(1):
                    try:
                        label = light.get_label()
                        break
                    except:
                        print('Failed to get light label for:')
                        print(light)
                        continue
                if label is None:
                    print('this light is wack!')
                    print(light)
                    continue
                self.current_light = label
                # turn on the light
                while(1):
                    try:
                        light.set_power(1)
                        break
                    except:
                        print('Failed to turn on light ' + label)
                # sweep through brightness
                for brightness in range(0, 101, 10):
                    print(brightness)
                    for device in self.sensors:
                        print(self.sensors[device])
                    # clear seen devices
                    self.seen_sensors.clear()
                    #print(brightness)
                    self.current_brightness = brightness
                    while(1):
                        try:
                            light.set_brightness(brightness/100*65535)
                            break
                        except:
                            print('Failed to set brightness ' + label)
                    while(1):
                        print(sorted(self.seen_sensors))
                        print(sorted([x for x in self.sensors.keys()]))
                        print()
                        if self.seen_sensors == set([x for x in self.sensors.keys()]):
                            break
                        time.sleep(5)
                try:
                    light.set_power(0)
                except:
                    print('Failed to turn off light' + label)
            for device in self.sensors:
                baseline_lux = self.sensors[device].baseline
                for light in self.sensors[device].light_char_measurements:
                    measurements = np.array(self.sensors[device].light_char_measurements[light])
                    measurements[:, 1] -= baseline_lux
                    ind = measurements[:, 1] < 0
                    measurements[:, 1][ind] = 0
                    self.sensors[device].light_char_measurements[light] = measurements

        # generate primary light associations
        # eventually we can do smarter things than 1-to-1 mappings
        for device in self.sensors:
            print(self.sensors[device])
            max_affect_light = ('none', 0)
            for light in self.sensors[device].light_char_measurements:
                 max_effect = self.sensors[device].light_char_measurements[light][-1][1]
                 if max_effect > max_affect_light[1]:
                     max_affect_light = (light, max_effect)
            self.sensors_to_lights[device] = max_affect_light[0]
        print(self.sensors_to_lights)

        # save because why not?
        with open('sensor_light_characterization.pkl', 'wb') as output:
            pickle.dump(self.sensors, output, pickle.HIGHEST_PROTOCOL)

        self.current_light = None
        self.current_brightness = None


    # mqtt source for sensor data
    def on_connect(self, client, userdata, flags, rc):
        print("Connected to mqtt stream with result code "+str(rc))
        client.subscribe("device/Permamote/#")

    def on_message(self, client, userdata, msg):
        #print(msg.topic+" "+str(msg.payload) + '\n')

        data = json.loads(msg.payload)
        seq_no = int(data['sequence_number'])
        device_id = data['_meta']['device_id']
        lux = float(data['light_lux'])

        # state machine for message handling
        if self.state == self.State.IDLE:
            return
        elif self.state == self.State.DISCOVER:
            if device_id not in self.sensors:
                self.sensors[device_id] = LightSensor(device_id)
            self.sensors[device_id].baseline = lux
            self.sensors[device_id].update_seq_no(seq_no)

        elif self.state == self.State.CHARACTERIZE:
            # only consider devices we've done baseline measurements for
            #print('Saw ' + str(device_id))
            if self.current_light is None:
                # if the current light is not set yet, ignore this
                print('huh?')
                return
            if device_id not in self.sensors:
                print("Saw sensor not in devices with baseline measurement: " + str(device_id))
                return
            #if device_id not in self.seen_sensors:
            self.seen_sensors.add(device_id)
            #print(self.seen_sensors)
            if self.current_light not in self.sensors[device_id].light_char_measurements:
                self.sensors[device_id].light_char_measurements[self.current_light] = []
            measurements = [x[0] for x in self.sensors[device_id].light_char_measurements[self.current_light]]
            if self.current_brightness not in measurements:
                self.sensors[device_id].light_char_measurements[self.current_light].append([self.current_brightness, lux])
        elif self.state == self.State.CONTROL:
            self.sensors[device_id].lux = lux

    def update_lights(self):
        for sensor in self.sensors_to_lights:
            light_label = self.sensors_to_lights[sensor]
            light_to_update = None
            for light in self.lights:
                print(light.label)
                if light.label == light_label:
                    light_to_update = light

            pid = self.pid_controllers[light_to_update.label]
            try:
                brightness = light.get_color()[2]
            except:
                pass
            pid.update(sensor.lux)
            print(pid.output)
            brightness += pid.output
            if brightness > 65535:
                brightness = 65535
            elif brightness < 0:
                brightness = 0
            try:
                light_to_update.set_brightness(brightness, 5)
                print('light brightness set to ' + str(brightness/65535*100) + ' percent at ' + str(datetime.datetime.now()))
            except:
                print('failed to set light brightness')


    def control_loop(self):
        time.sleep(5)


shade_list = [
                "F4:21:20:D9:FA:CD",
                "DF:93:08:12:38:CF",
                "FD:97:B5:16:08:4F",
                "FD:97:B5:16:08:4F",
                "F0:8A:FB:BC:E9:82",
             ]
selected_labels = sorted([s + "'s light" for s in ['Neal', 'Pat', 'Josh', 'Will']])

lightcontrol = LightControl("128.32.171.51")
lightcontrol.discover(selected_labels, None, shade_list)
#print(lightcontrol.lights)
#print(sorted(lightcontrol.sensors.keys()))
lightcontrol.characterize()
update_lights()
