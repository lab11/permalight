#!/usr/bin/env python3

import sys
import traceback
import paho.mqtt.client as mqtt
from PID import PID
from enum import Enum
import numpy as np
import time
import pickle
import json
import os.path
import datetime
import yaml
from light_sensor import LightSensor
sys.path.append('../tled_zigbee/')
from controller import Controller
from light import Light

class LightControl:
    class State(Enum):
        IDLE = 0
        DISCOVER = 1
        CHAR_LIGHT = 2
        #CHAR_SHADE = 3
        CONTROL = 3

    def __init__(self, mqtt_address):
        self.state = self.State.IDLE

        # dict mapping of sensor id (string) to sensor object
        self.sensors = {}
        # dict mapping of light id to light object
        self.lights = {}
        # dict mapping of sensor id (string) to light object
        self.sensors_to_lights = {}
        # keep track of sensors seen during
        # characterization steps
        self.seen_sensors = set()
        self.current_light = None
        #self.current_shade = None
        self.current_brightness = None

        self.lower_bound_lux = 100
        self.pid_controllers = {}

        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message

        self.mqtt_client.connect(mqtt_address)
        self.mqtt_client.loop_start()

    def discover(self, light_list, sensor_list, sensor_light_map):
        # discover lights, sensors, existing mapping
        # do we have a saved python dict from characterization?
        #have_char_light_file = os.path.isfile('sensor_light_mappings.pkl') and \
        #        os.path.getsize('sensor_light_mappings.pkl') > 0

        # if we already have a light list
        if light_list is not None:
            for light in light_list:
              for name in light:
                self.lights[hex(light[name]['address']).replace('0x','')] = Light(address=light[name]['address'], endpoint=light[name]['endpoint'], controller=controller, is_group=True)
        else:
            #TODO some way to discover lights?
            print("no lights supplied!")
            exit(1)

        print('Discovered the following lights:')
        for light_id in self.lights:
            print('\t' + light_id)

        # generate PID for each light
        for light_id in self.lights:
            #TODO might need to alter these parameters
            pid = PID(0.1, 0, 0)
            pid.SetPoint = self.lower_bound_lux
            self.pid_controllers[light_id] = pid

        if sensor_list is not None:
            for sensor_id in sensor_list:
                self.sensors[sensor_id] = LightSensor(sensor_id)
        else:
            # start sensor discovery
            self.state = self.State.DISCOVER
            # toggle all lights on/off to generate output from sensor
            # the change in light will cause mqtt messages, and we can generate
            # list of relavent sensors
            #TODO turn all lights high
            time.sleep(5)
            #TODO turn all lights low
            time.sleep(5)
            self.state = self.State.IDLE

        # TODO pick lights/sensors/mapping out of saved data
        print('Discovered the following sensors:')
        for sensor_id in self.sensors:
            print('\t' + sensor_id)

        # set up sensor-light mapping
        if sensor_light_map is not None:
            #TODO read in mapping
            for sensor_id in sensor_light_map:
                if sensor_id not in self.sensors:
                    print('mapped sensor (%s) not one of sensors!' % sensor_id);
                    continue
                self.sensors_to_lights[sensor_id] = self.lights[sensor_light_map[sensor_id]]
        else:
            # TODO characterization!
            print("missing mappings!");
            exit(1)

        print('Discovered the following mappings:')
        for sensor_id in self.sensors_to_lights:
            print('\t' + sensor_id + ' <--> ' + hex(self.sensors_to_lights[sensor_id].address))

    def _characterize_lights(self):
        # characterize lights
        # reuse old characterization if it exists
        if len(self.sensors_to_lights) != 0:
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

    def characterize(self):
        # turn all lights off
        for light in self.lights:
            #TODO turn light off
            pass
        self._characterize_lights()

    def _update_light(self, sensor_id):
        light_to_update = self.sensors_to_lights[sensor_id]
        print('updating light: ' + hex(light_to_update.address) + ' and sensor: ' + sensor_id)
        # if light is off
        if light_to_update.state != 1:
            light_to_update.on()
            light_to_update.set_level(100)
        pid = self.pid_controllers[hex(light_to_update.address).replace('0x', '')]
        pid.update(self.sensors[sensor_id].lux)
        brightness = light_to_update.level
        print('brightness setting: %f' % brightness)
        print('lux sensed: %f' % self.sensors[sensor_id].lux)
        print('pid output: %f' % pid.output)
        brightness += pid.output
        if brightness > 100:
            brightness = 100
        elif brightness < 0:
            brightness = 0
        try:
            light_to_update.set_level(brightness)
            print(hex(light_to_update.address) + ' brightness set to ' + str(brightness) + ' percent at ' + str(datetime.datetime.now()))
        except Exception as e:
            print(e)
            traceback.print_exc()

    def start_control_loop(self):
        self.state = self.state.CONTROL
        time.sleep(2)

    # mqtt source for sensor data
    def on_connect(self, client, userdata, flags, rc):
        print("Connected to mqtt stream with result code "+str(rc))
        client.subscribe("device/Permamote/#")
        #client.subscribe("device/BLEES/#")

    def on_message(self, client, userdata, msg):
        #print(msg.topic+" "+str(msg.payload) + '\n')

        data = json.loads(msg.payload.decode('utf-8'))
        # only interested in light_lux messages
        if 'light_lux' not in data:
            return
        device_id = data['_meta']['device_id']
        lux = float(data['light_lux'])

        if device_id not in self.sensors and self.state != self.State.DISCOVER:
            return

        print(device_id)
        print(lux)
        print()

        # state machine for message handling
        if self.state == self.State.IDLE:
            return
        elif self.state == self.State.DISCOVER:
            if device_id not in self.sensors:
                self.sensors[device_id] = LightSensor(device_id)
            self.sensors[device_id].baseline = lux
            self.sensors[device_id].update_seq_no(seq_no)

        elif self.state == self.State.CHAR_LIGHT:
            # only consider devices we've done baseline measurements for
            #print('Saw ' + str(device_id))
            if self.current_light is None:
                # if the current light is not set yet, ignore this
                print('characterize current light not set?')
                return
            if device_id not in self.sensors:
                print("Saw sensor not in discovered devices: " + str(device_id))
                return
            # if device_id not in self.seen_sensors:
            # get measurement for current light
            self.sensors[device_id].light_char_measurements[self.current_light] = lux
        elif self.state == self.State.CONTROL:
            self.sensors[device_id].lux = lux
            self._update_light(device_id)

CONFIG_FILE = '../config.yaml'
with open(CONFIG_FILE, 'r') as fp:
  config = yaml.safe_load(fp)
sensor_list = config['sensors']
light_list = config['groups']
sensor_light_map = config['map']

controller = Controller(config_file='../config.yaml')

lightcontrol = LightControl("34.218.46.181")
#TODO add inputs for lights, mapping of sensors to lights
lightcontrol.discover(light_list, sensor_list, sensor_light_map)
#print(lightcontrol.lights)
#print(sorted(lightcontrol.sensors.keys()))
lightcontrol.start_control_loop()

while(1):
    pass
