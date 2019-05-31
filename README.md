# Permalight
A lighting control system built on top of a deployment of
[Permamote](https://github.com/lab11/permamote) sensors and Lifx wifi connected
bulbs.

Permalight consists of two components, the lighting control system
([permalight](https://github.com/lab11/permalight/tree/lifx/permalight)) and a
control server
([permalight-server](https://github.com/lab11/permalight/tree/lifx/server)).
The control server receives JSON requests from external applications, and
forwards their contents to a local MQTT bus. The lighting control system
receives these MQTT messages and alters its control scheme accordingly.

## JSON Format
Permalight currently supports the following commands:
- enable
- set_point
- bright
- dim

### enable
The enable command enables or disables the system's control of the light, and
accepts a boolean value of 0 or 1. The command server expects JSON like the
following:
```
{
  "light_name": "Branden's light",
  "action": "enable",
  "value": {0,1}
}
```
### set_point
The set_point command changes the set point for a light, and accepts a float/integer value
in lux.
```
{
  "light_name": "Branden's light",
  "action": "set_point",
  "value": 250
}
```
### bright
The bright command increases the set_point of a light by 25 lux
```
{
  "light_name": "Branden's light",
  "action": "bright"
}
```
### dim
Similarly, the dim command decreases the set_point of a light by 25 lux
```
{
  "light_name": "Branden's light",
  "action": "bright"
}
```




