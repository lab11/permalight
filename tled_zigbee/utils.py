import serial
import time

AND_WITH_FF = lambda x: x & 0xFF
SHIFT_RIGHT_8 = lambda x: x >> 8

PARITY_CONSTANTS = {
	'even': serial.PARITY_EVEN,
	'none': serial.PARITY_NONE,
	'odd': serial.PARITY_ODD,
	'mark': serial.PARITY_MARK,
	'space': serial.PARITY_SPACE,
}

BYTE_SIZE_CONSTANTS = {
	5: serial.FIVEBITS,
	6: serial.SIXBITS,
	7: serial.SEVENBITS,
	8: serial.EIGHTBITS
}

STOP_BITS_CONSTANTS = {
	1: serial.STOPBITS_ONE,
	1.5: serial.STOPBITS_ONE_POINT_FIVE,
	2: serial.STOPBITS_TWO
}

def create_byte_stream_to_send(data_bytes):
	bytes_to_send = []
	bytes_to_send.append(0x01)

	for i in range(len(data_bytes)):
		if data_bytes[i] < 0x10:
			bytes_to_send.append(0x02)
			bytes_to_send.append(data_bytes[i]^0x10)
		else:
			bytes_to_send.append(data_bytes[i])
	bytes_to_send.append(0x03)
	return bytearray(bytes_to_send)

def convert_int16_msb_lsb_list(n):
	lsb = AND_WITH_FF(n)
	msb = AND_WITH_FF(SHIFT_RIGHT_8(n))
	return {'msb': msb, 'lsb': lsb}

def get_checksum(msg_type_msb, msg_type_lsb, length_msb, length_lsb, data):
	checksum = msg_type_msb ^ msg_type_lsb ^ length_msb ^ length_lsb
	for b in data:
		checksum = checksum ^ b
	return checksum

def wait_for_prev(start_time, wait_timeout):
	if start_time == None or wait_timeout == None:
		return

	while(time.time() - start_time < wait_timeout):
		continue
