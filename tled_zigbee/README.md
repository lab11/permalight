## Pairing

1. Reset the TLEDs that have to be paired and grouped: Press the identify button and then reset button on the IR remote
2. Once the TLED(s) have been reset, in permalight/tled_zigbee folder, run `python pair.py`. Wait for some time and see the output. 
3. Each pairing will output 2 lines; Look at the first line: the 7th and 8th byte is the short address of the TLED. Note these 2 bytes.
4. Ctrl+C to terminate the script

Example:

`python pair.py` 

It returns: 

01 00 4D 00 0B 00 **B1 75** 00 17 88 01 01 90 1C 1F 8E 03 <br/>
01 87 01 00 02 84 00 00 03 <br/>
01 00 4D 00 0B 1F **47 48** 00 17 88 01 01 90 1B CC 8E 03 <br/>
01 87 01 00 02 84 00 00 03

In this example, 2 TLEDs were paired and the address are 0xb175 and 0x4748

## Grouping

1. Open `permalight/tled_zigbee/group.py` in an editor 
2. In lines 11 and 12, replace the existing light address with the address of the lights (found after pairing) you want to group
3. In lines 11 and 12, set a group address
4. And run `python group.py`
