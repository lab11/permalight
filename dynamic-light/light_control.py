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

class LightControl:
    class State(Enum):
        IDLE = 0
        DISCOVER = 1
        CONTROL = 2

    def __init__(self, mqtt_address):
        self.state = self.State.IDLE

        # list of lights
        self.lightNameToLights = {}
        # dict mapping of sensor id (string) to light id (string)
        self.lightSensorIdToLightName = {}
        self.occSensorIdToLightName = {}

        # keep track of discovered sensors
        self.sensorIdToSensor = {}

        self.lowerBoundLux = 300
        self.lightToPidControllers = {}

        self.motionTimeout = 10*60

        self.mqttClient = mqtt.Client()
        self.mqttClient.on_connect = self.on_connect
        self.mqttClient.on_message = self.on_message

        self.mqttClient.connect(mqtt_address)
        self.mqttClient.loop_start()

    def all_on(self):
        for name in self.lightNameToLights:
            self.lightNameToLights[name].on()

    def all_off(self):
        for name in self.lightNameToLights:
            self.lightNameToLights[name].off()

    def discover(self, light_list, sensor_light_map=None, occ_light_map=None):
        # discover lights, sensors, existing mapping
        # do we have a saved python dict from characterization?
        #have_char_light_file = os.path.isfile('sensor_light_mappings.pkl') and \
        #        os.path.getsize('sensor_light_mappings.pkl') > 0

        # if we already have a light list
        if light_list is not None:
            for light in controller.discover(light_list):
                self.lightNameToLights[light.name] = light
        else:
            try:
                for light in controller.discover():
                    self.lightNameToLights[light.name] = light
            except AttributeError as e:
                print("No lights provided in config and no method to discover!")
                print(e)
                exit(1)

        print('Discovered the following lights:')
        for light_id in self.lightNameToLights:
            print('\t' + light_id)

        # generate PID for each light
        for name in self.lightNameToLights:
            print(name)
            #TODO might need to alter these parameters
            pid = PID(0.1, 0, 0)
            pid.SetPoint = self.lowerBoundLux
            self.lightToPidControllers[name] = pid
            self.lightNameToLights[name].on()
            self.lightNameToLights[name].set_level(1)

        if sensor_light_map is not None:
            for sensor_id in sensor_light_map:
                self.sensorIdToSensor[sensor_id] = LightSensor(sensor_id)
        else:
            # start sensor discovery
            self.state = self.State.DISCOVER
            # toggle all lights on/off to generate output from sensor
            # the change in light will cause mqtt messages, and we can generate
            # list of relavent sensors
            self.all_off()
            time.sleep(5)
            self.all_on()
            self.state = self.State.IDLE

        print('Discovered the following sensors:')
        for sensor_id in self.sensorIdToSensor:
            print('\t' + sensor_id)

        # set up sensor-light mapping
        if sensor_light_map is not None:
            #TODO read in mapping
            for sensor_id in sensor_light_map:
                self.lightSensorIdToLightName[sensor_id] = sensor_light_map[sensor_id]
        else:
            # TODO characterization!
            print("missing mappings!");
            exit(1)

        if occ_light_map is not None:
            #TODO read in mapping
            for sensor_id in occ_light_map:
                self.occSensorIdToLightName[sensor_id] = occ_light_map[sensor_id]

        # TODO pick lights/sensors/mapping out of saved data

        print('Discovered the following light sensors:')
        for sensor_id in self.lightSensorIdToLightName:
            print('\t' + sensor_id)

        print('Discovered the following occ sensors:')
        for sensor_id in self.occSensorIdToLightName:
            print('\t' + sensor_id)

        print('Discovered the following light mappings:')
        for sensor_id in self.lightSensorIdToLightName:
            print('\t' + sensor_id + ' <--> ' + self.lightSensorIdToLightName[sensor_id])

        print('Discovered the following occ mappings:')
        for sensor_id in self.occSensorIdToLightName:
            print('\t' + sensor_id + ' <--> ' + self.occSensorIdToLightName[sensor_id])


    def _motion_watchdog(self):
        # TODO if haven't seen motion since last time, turn off associated light
        time_start = datetime.datetime.now()
        while(1):
            time.sleep(5)
            time_check = datetime.datetime.now()
            if (time_check - time_start).total_seconds() >= self.motionTimeout:
                time_start = datetime.datetime.now()
                for sensor_id in self.occSensorIdToLightName:
                    light_id = self.occSensorIdToLightName[sensor_id]
                    if self.sensorIdToSensor[sensor_id].motion == 0:
                        print("have not seen motion, turning off light %s" % light_id)
                        self.lightNameToLights[light_id].off()
                    self.sensorIdToSensor[sensor_id].motion = 0

    def _update_light(self, sensor_id):
        light_id = self.lightSensorIdToLightName[sensor_id]
        light_to_update = self.lightNameToLights[light_id]

        # if the light is on and haven't seen motion recently
        print(self.lightNameToLights[light_id].get_state())
        print(self.sensorIdToSensor[sensor_id].motion)
        if not self.lightNameToLights[light_id].get_state() and not self.sensorIdToSensor[sensor_id].motion:
            print("haven't seen motion, not updating light")
            return
        print('updating light: ' + light_id + ' and sensor: ' + sensor_id)
        pid = self.lightToPidControllers[light_id]
        pid.update(self.sensorIdToSensor[sensor_id].lux)
        brightness = self.lightNameToLights[light_id].get_level()
        print('brightness setting: %f' % brightness)
        print('lux sensed: %f' % self.sensorIdToSensor[sensor_id].lux)
        print('pid output: %f' % pid.output)
        brightness += pid.output/100.0
        try:
            light_to_update.on()
            light_to_update.set_level(brightness, 1000)
            print('brightness setting: %f' % brightness)
            print(light_id + ' brightness set to ' + str(brightness*100) + ' percent at ' + str(datetime.datetime.now()))
        except Exception as e:
            print(e)
            traceback.print_exc()

    def start_control_loop(self):
        self.state = self.state.CONTROL
        # toggle the lights just to get initial measurements
        self.all_off()
        time.sleep(2)
        self.all_on()
        # start motion watchdog
        self._motion_watchdog()

    # mqtt source for sensor data
    def on_connect(self, client, userdata, flags, rc):
        print("Connected to mqtt stream with result code "+str(rc))
        client.subscribe("device/Permamote/#")
        #client.subscribe("device/BLEES/#")

    def on_message(self, client, userdata, msg):
        #print(msg.topic+" "+str(msg.payload) + '\n')

        data = json.loads(msg.payload.decode('utf-8'))
        device_id = data['_meta']['device_id']

        if device_id not in self.sensorIdToSensor and self.state != self.State.DISCOVER:
            return

        if 'light_lux' in data:
            print(device_id)
            lux = data['light_lux']
            print(lux)
            # state machine for message handling
            if self.state == self.State.IDLE:
                return
            elif self.state == self.State.DISCOVER:
                if device_id not in self.sensorIdToSensor:
                    self.sensorIdToSensor[device_id] = LightSensor(device_id)

            elif self.state == self.State.CONTROL:
                self.sensorIdToSensor[device_id].lux = lux
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
            light_id = self.occSensorIdToLightName[device_id]
            try:
                light = self.lightNameToLights[light_id]
                light.on()
            except Exception as e:
                print(e)
                traceback.print_exc()
            self.sensorIdToSensor[device_id].motion = 1
            print()

sys.path.append(os.path.abspath('../lifx'))
from lifx import Controller
from lifx import Light

config_fname = 'config.yaml'
with open(config_fname, 'r') as f:
  config = yaml.safe_load(f)

controller = Controller()

lightcontrol = LightControl(config['mqtt_addr'])
#TODO add inputs for lights, mapping of sensors to lights
lightcontrol.discover(config['light_list'], config['sensor_map'], config['occ_map'])
#lightcontrol.discover(config['light_list'])
#print(lightcontrol.lights)
#print(sorted(lightcontrol.sensors.keys()))
lightcontrol.start_control_loop()

