#!/usr/bin/env python3

import sys
import traceback
import multiprocessing
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
sys.path.append(os.path.abspath('/home/pi/permalight/tled_zigbee/'))
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
        self.manager = multiprocessing.Manager()

        # dict mapping of sensor id (string) to sensor object
        self.light_sensors = {}
        self.lights_to_motion = self.manager.dict()
        # dict mapping of light id to light object
        self.lights = {}
        self.lights_to_brightness = self.manager.dict()
        self.lights_to_off = self.manager.dict()
        # dict mapping of sensor id (string) to light id (string)
        self.light_sensors_to_lights = {}
        self.occ_sensors_to_lights = {}
        # keep track of sensors seen during
        # characterization steps
        self.seen_sensors = set()
        self.current_light = None
        #self.current_shade = None
        self.current_brightness = None

        self.lower_bound_lux = 500
        self.pid_controllers = {}

        self.motion_timeout = 10*60

        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message

        self.mqtt_client.connect(mqtt_address)

    def discover(self, light_list, sensor_light_map, occ_light_map):
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
            self.lights[light_id].on()
            self.lights[light_id].set_level(50)
            self.lights_to_brightness[light_id] = 50
            self.lights_to_motion[light_id] = 1
            self.lights_to_off[light_id] = 0;

        if sensor_light_map is not None:
            for sensor_id in sensor_light_map:
                self.light_sensors[sensor_id] = LightSensor(sensor_id)
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
        for sensor_id in self.light_sensors:
            print('\t' + sensor_id)

        # set up sensor-light mapping
        if sensor_light_map is not None:
            #TODO read in mapping
            for sensor_id in sensor_light_map:
                self.light_sensors_to_lights[sensor_id] = sensor_light_map[sensor_id]
        else:
            # TODO characterization!
            print("missing mappings!");
            exit(1)

        if occ_light_map is not None:
            #TODO read in mapping
            for sensor_id in occ_light_map:
                self.occ_sensors_to_lights[sensor_id] = occ_light_map[sensor_id]

        #if sensor_light_map is not None:
        #    for sensor_id in sensor_light_map:
        #        self.light_sensors[sensor_id] = LightSensor(sensor_id)
        #        self.light_sensors_to_motion[sensor_id] = 0
        #else:
        #    # start sensor discovery
        #    self.state = self.State.DISCOVER
        #    # toggle all lights on/off to generate output from sensor
        #    # the change in light will cause mqtt messages, and we can generate
        #    # list of relavent sensors
        #    #TODO turn all lights high
        #    time.sleep(5)
        #    #TODO turn all lights low
        #    time.sleep(5)
        #    self.state = self.State.IDLE

        # TODO pick lights/sensors/mapping out of saved data
        print('Discovered the following light sensors:')
        for sensor_id in self.light_sensors_to_lights:
            print('\t' + sensor_id)

        print('Discovered the following occ sensors:')
        for sensor_id in self.occ_sensors_to_lights:
            print('\t' + sensor_id)

        print('Discovered the following light mappings:')
        for sensor_id in self.light_sensors_to_lights:
            print('\t' + sensor_id + ' <--> ' + self.light_sensors_to_lights[sensor_id])

        print('Discovered the following occ mappings:')
        for sensor_id in self.occ_sensors_to_lights:
            print('\t' + sensor_id + ' <--> ' + self.occ_sensors_to_lights[sensor_id])


    #def _characterize_lights(self):
    #    # characterize lights
    #    # reuse old characterization if it exists
    #    if len(self.light_sensors_to_lights) != 0:
    #        return

    #    print("starting light characterizing measurements!")
    #    for light in self.lights:
    #        label = light.address
    #        if label is None:
    #            print('this light is wack!')
    #            print(light)
    #            continue
    #        self.current_light = label
    #        print(label)
    #        self.state = self.State.CHAR_LIGHT
    #        # TODO turn on the light
    #        time.sleep(5)
    #        # TODO turn off the light
    #        time.sleep(5)
    #        self.state = self.State.CHAR_IDLE

    #        # sweep through brightness
    #        #for brightness in range(0, 101, 10):
    #        #    print(brightness)
    #        #    # clear seen devices
    #        #    self.seen_sensors.clear()
    #        #    #print(brightness)
    #        #    self.current_brightness = brightness
    #        #    while(1):
    #        #        try:
    #        #            light.set_brightness(brightness/100*65535)
    #        #            break
    #        #        except lifxlan.errors.WorkflowException:
    #        #            print('Failed to set brightness ' + label)
    #        #    while(1):
    #        #        if self.seen_sensors == set([x for x in self.light_sensors.keys()]):
    #        #            break
    #        #        time.sleep(5)
    #        for sensor_id in self.light_sensors:
    #            baseline_lux = self.light_sensors[sensor_id].baseline
    #            measurement = self.light_sensors[sensor_id].light_char_measurements[light]

    #            # save because why not?
    #            with open(sensor_id + '_characterization.pkl', 'wb') as output:
    #                pickle.dump(self.light_sensors[sensor_id].light_char_measurements, output, pickle.HIGHEST_PROTOCOL)

    #    # generate primary light associations
    #    # eventually we can do smarter things than 1-to-1 mappings
    #    # for each sensor, see which light affected it the most
    #    for sensor_id in self.light_sensors:
    #        max_affect_light = (None, 50)
    #        for light in self.light_sensors[sensor_id].light_char_measurements:
    #            max_effect = self.light_sensors[sensor_id].light_char_measurements[light]
    #            if max_effect > max_affect_light[1]:
    #                max_affect_light = (light, max_effect)
    #        self.light_sensors_to_lights[sensor_id] = max_affect_light[0]
    #    print(self.light_sensors_to_lights)
    #    with open('sensor_light_mappings.pkl', 'wb') as output:
    #        pickle.dump(self.light_sensors_to_lights, output, pickle.HIGHEST_PROTOCOL)

    #    self.current_light = None
    #    self.current_brightness = None

    #def characterize(self):
    #    # turn all lights off
    #    for light in self.lights:
    #        #TODO turn light off
    #        pass
    #    self._characterize_lights()

    def _motion_watchdog(self):
        # TODO if haven't seen motion since last time, turn off associated light
        time_start = datetime.datetime.now()
        while(1):
            time.sleep(5)
            time_check = datetime.datetime.now()
            if (time_check - time_start).total_seconds() >= self.motion_timeout:
                time_start = datetime.datetime.now()
                for sensor_id in self.occ_sensors_to_lights:
                    light_id = self.occ_sensors_to_lights[sensor_id]
                    if self.lights_to_motion[light_id] == 0:
                        print("have not seen motion, turning off light %s" % self.lights[light_id])
                        self.lights[light_id].off()
                        self.lights_to_off[light_id] = 1;
                    self.light_sensors_to_motion[sensor_id] = 0

    def _update_light(self, sensor_id):
        light_id = self.light_sensors_to_lights[sensor_id]
        light_to_update = self.lights[light_id]
        # if light is off
        print(self.lights_to_brightness[light_id])
        if self.lights_to_off[light_id] and not self.lights_to_motion[light_id]:
            print("haven't seen motion, not updating light")
            return
        print('updating light: ' + hex(light_to_update.address) + ' and sensor: ' + sensor_id)
        pid = self.pid_controllers[hex(light_to_update.address).replace('0x', '')]
        pid.update(self.light_sensors[sensor_id].lux)
        brightness = self.lights_to_brightness[light_id]
        print('brightness setting: %f' % brightness)
        print('lux sensed: %f' % self.light_sensors[sensor_id].lux)
        print('pid output: %f' % pid.output)
        brightness += pid.output
        if brightness > 100:
            brightness = 100
        elif brightness < 0:
            brightness = 0
        try:
            light_to_update.set_level(brightness)
            print('brightness setting: %f' % brightness)
            print(hex(light_to_update.address) + ' brightness set to ' + str(brightness) + ' percent at ' + str(datetime.datetime.now()))
            self.lights_to_brightness[light_id] = brightness
        except Exception as e:
            print(e)
            traceback.print_exc()

    def start_control_loop(self):
        self.state = self.state.CONTROL
        # toggle the lights just to get initial measurements
        for light_id in self.lights:
            self.lights[light_id].off();
        time.sleep(2)
        for light_id in self.lights:
            self.lights[light_id].on();
        time.sleep(2)
        # start motion watchdog
        p = multiprocessing.Process(target=self._motion_watchdog)
        p.start()

        self.mqtt_client.loop_forever()

    # mqtt source for sensor data
    def on_connect(self, client, userdata, flags, rc):
        print("Connected to mqtt stream with result code "+str(rc))
        client.subscribe("device/Permamote/#")
        #client.subscribe("device/BLEES/#")

    def on_message(self, client, userdata, msg):
        #print(msg.topic+" "+str(msg.payload) + '\n')

        data = json.loads(msg.payload.decode('utf-8'))
        device_id = data['_meta']['device_id']

        if device_id not in self.light_sensors and self.state != self.State.DISCOVER:
            return

        if 'light_lux' in data:
            print(device_id)
            lux = data['light_lux']
            print(lux)
            # state machine for message handling
            if self.state == self.State.IDLE:
                return
            elif self.state == self.State.DISCOVER:
                if device_id not in self.light_sensors:
                    self.light_sensors[device_id] = LightSensor(device_id)
                self.light_sensors[device_id].baseline = lux

            elif self.state == self.State.CHAR_LIGHT:
                # only consider devices we've done baseline measurements for
                #print('Saw ' + str(device_id))
                if self.current_light is None:
                    # if the current light is not set yet, ignore this
                    print('characterize current light not set?')
                    return
                if device_id not in self.light_sensors:
                    print("Saw sensor not in discovered devices: " + str(device_id))
                    return
                # if device_id not in self.seen_sensors:
                # get measurement for current light
                self.light_sensors[device_id].light_char_measurements[self.current_light] = lux
            elif self.state == self.State.CONTROL:
                self.light_sensors[device_id].lux = lux
                try:
                    #self._update_light(device_id)
                    p = multiprocessing.Process(target=self._update_light, args=(device_id,))
                    p.start()
                    p.join(5)
                    if p.is_alive():
                        p.terminate()
                        p.join()
                except Exception as e:
                    print(e)
                    traceback.print_exc()
            print()
        elif 'motion' in data:
            print(device_id)
            print('Saw motion!')
            light_id = occ_sensors_to_lights[device_id]
            try:
                light = self.lights[light_id]
                #light.on()
                light.set_level(self.lights_to_brightness[light_id])
                self.lights_to_off[light_id] = 0
            except Exception as e:
                print(e)
                traceback.print_exc()
            self.lights_to_motion[light_id] = 1
            print()

CONFIG_FILE = '/home/pi/permalight/config.yaml'
with open(CONFIG_FILE, 'r') as fp:
  config = yaml.safe_load(fp)
light_list = config['groups']
sensor_light_map = config['sensor_map']
occ_light_map = config['occ_map']

controller = Controller(config_file=CONFIG_FILE)

lightcontrol = LightControl("34.218.46.181")
#TODO add inputs for lights, mapping of sensors to lights
lightcontrol.discover(light_list, sensor_light_map, occ_light_map)
#print(lightcontrol.lights)
#print(sorted(lightcontrol.sensors.keys()))
lightcontrol.start_control_loop()

