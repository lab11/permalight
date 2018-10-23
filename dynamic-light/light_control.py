#!/usr/bin/env python3

import paho.mqtt.client as mqtt
from PID import PID
from enum import Enum
import numpy as np
import time
import pickle
import json
import os.path
import datetime
from light_sensor import LightSensor
import importlib.util
spec = importlib.util.spec_from_file_location("Light", "../tled_zigbee/light.py")
Light = importlib.util.module_from_spec(spec)
spec.loader.exec_module(Light)

class LightControl:
    class State(Enum):
        IDLE = 0
        DISCOVER = 1
        CHAR_LIGHT = 2
        #CHAR_SHADE = 3
        CONTROL = 3

    def __init__(self, mqtt_address):
        self.state = self.State.IDLE

        self.lights = []
        # dict mapping of sensor id (string) to sensor object
        self.sensors = {}
        self.sensor_whitelist = []
        # dict mapping of sensor id (string) to light object
        self.sensors_to_lights = {}
        # keep track of sensors seen during
        # characterization steps
        self.seen_sensors = set()
        self.current_light = None
        #self.current_shade = None
        self.current_brightness = None

        #self.upper_bound_lux = 800
        self.hyster = 100
        self.lower_bound_lux = 100
        self.pid_controllers = {}

        #TODO set up lights here
        #self.lan = LifxLAN()
        #self.shade_client = ShadeClient(shade_config)

        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message

        self.mqtt_client.connect(mqtt_address)
        self.mqtt_client.loop_start()

    def discover(self, light_list, sensor_list):
        # discover lights, shades, sensors
        #TODO light list may exist as yaml config instead
        have_light_file = os.path.isfile('sensor_light_mappings.pkl') and \
                os.path.getsize('sensor_light_mappings.pkl') > 0

        # if we don't already have a set of lights we're interested in,
        # discover all lights
        if light_list is None and not have_light_file:
            #TODO some mechanism to discover TLED lights
            #We can just use predefined lists instead
            print("no lights supplied")
            exit(1)
        # otherwise, generate from saved mappings or use light file
        else:
            known_lights = []
            # if we already have a generated mapping to lights (created during characterization):
            if have_light_file:
                with open('sensor_light_mappings.pkl', 'rb') as f:
                    self.sensors_to_lights = pickle.load(f)
                for sensor_id in self.sensors_to_lights:
                    if self.sensors_to_lights[sensor_id] is not None:
                        known_lights.append(self.sensors_to_lights[sensor_id])
            # otherwise we just use lights in supplied light list
            else:
                known_lights = light_list
            # get handles to known lights
            for label in known_lights:
                #TODO some mechanism to discover/create light, if needed
                pass
        # generate PID for each light
        for light in self.lights:
            #TODO might need to alter these parameters
            pid = PID(200, 0, 5)
            pid.SetPoint = self.lower_bound_lux
            self.pid_controllers[light.label] = pid

        # set up sensor whitelist
        if sensor_list is not None:
            self.sensor_whitelist = sensor_list

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

        # TODO pick sensors out of saved data
        print('Discovered the following sensors:')
        for sensor_id in self.sensors:
            print('\t' + sensor_id)

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

        data = json.loads(msg.payload)
        # only interested in light_lux messages
        if 'light_lux' not in data:
            return
        device_id = data['_meta']['device_id']
        lux = float(data['light_lux'])

        if len(self.sensor_whitelist) != 0 and device_id not in self.sensor_whitelist:
            return

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

    def _update_light(self, sensor):
        light_to_update = self.sensors_to_lights[sensor]
        print('updating light: ' + light.address + ' and sensor: ' + sensor)
        if light_to_update is None:
            print('this light is wonky')
            return
        #TODO if light is off
        if light_to_update.state == 0:
            #TODO turn light on
            pass
        pid = self.pid_controllers[light_to_update.address]
        pid.update(self.sensors[sensor].lux)
        brightness = light_to_update.level
        print(brightness)
        print(self.sensors[sensor].lux)
        print(pid.output)
        brightness += pid.output
        #TODO what is the correct range of light levels for tleds?
        if brightness > 65535:
            brightness = 65535
        elif brightness < 0:
            brightness = 0
        #TODO set brightness
        print(label + ' brightness set to ' + str(brightness/65535*100) + ' percent at ' + str(datetime.datetime.now()))

sensor_list = [
        'c098e5110015',
        #'c098e5110008',
        #'c098e5110006',
        #'c098e5110007',
        ]
#shade_list = [
#        "F4:21:20:D9:FA:CD",
#        "DF:93:08:12:38:CF",
#        #"FD:97:B5:16:08:4F",
#        #"FE:AF:38:31:AC:C7",
#        #"F0:8A:FB:BC:E9:82",
#        ]

lightcontrol = LightControl("34.218.46.181")
#TODO add inputs for lights, mapping of sensors to lights
lightcontrol.discover(None, sensor_list)
#print(lightcontrol.lights)
#print(sorted(lightcontrol.sensors.keys()))
#lightcontrol.characterize()
lightcontrol.start_control_loop()
