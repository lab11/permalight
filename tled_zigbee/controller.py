import serial
import yaml
import utils
from utils import PARITY_CONSTANTS, BYTE_SIZE_CONSTANTS, STOP_BITS_CONSTANTS
from threading import Thread

class Controller(Thread):
	def __init__(self, config_file='settings.yaml'):
		super(Controller, self).__init__()
		with open(config_file, 'r') as fp:
			config = yaml.safe_load(fp)

		serial_config = config['serial']
		self.serial_port = serial_config['serial_port']
		self.baud_rate = serial_config['baud_rate']
		self.parity = PARITY_CONSTANTS[serial_config['parity']]
		self.stop_bits = STOP_BITS_CONSTANTS[serial_config['stop_bits']]
		self.byte_size = BYTE_SIZE_CONSTANTS[serial_config['byte_size']]
		self.xonxoff = serial_config['flow_control']
		self.timeout = serial_config['baud_rate']

		self.device = serial.Serial(
			port=self.serial_port,
			baudrate=self.baud_rate,
			parity=self.parity,
			stopbits=self.stop_bits,
			timeout=self.timeout,
			bytesize=self.byte_size,
			xonxoff=self.xonxoff 
		)
	def get_device(self):
		return self.device

	def permit_joining(self):
		msg_type = 0x0049
		msg_type_list = utils.convert_int16_msb_lsb_list(msg_type)
		msg_type_msb = msg_type_list['msb']
		msg_type_lsb = msg_type_list['lsb']

		target_short_address = 0x0
		target_short_address_list = utils.convert_int16_msb_lsb_list(target_short_address)
		target_short_address_msb = target_short_address_list['msb']
		target_short_address_lsb = target_short_address_list['lsb']

		interval = 0xff
		tcsignificance = 0x0

		content = [target_short_address_msb, target_short_address_lsb, interval, tcsignificance]

		length = utils.convert_int16_msb_lsb_list(len(content))
		length_msb = length['msb']
		length_lsb = length['lsb']

		checksum = utils.get_checksum(msg_type_msb=msg_type_msb, msg_type_lsb=msg_type_lsb, length_msb=length_msb, length_lsb=length_lsb, data=content)

		data = [msg_type_msb, msg_type_lsb, length_msb, length_lsb, checksum] + content

		bytes_to_send = utils.create_byte_stream_to_send(data_bytes=data)
		self.device.write(bytes_to_send)
		print(bytes_to_send)

	def synchronous_read(self):
		read_bytes = []
		# while line != b'\x03':
		while True:
			line = self.device.read()
			read_bytes.append(line)

			if line == b'\x03':
				final_bytes = []
				i = 1
				while i < len(read_bytes)-1:
					b = int.from_bytes(read_bytes[i], byteorder='big')
					if b != 2:
						final_bytes.append(hex(b))
					else:
						i+=1
						b = int.from_bytes(read_bytes[i], byteorder='big') ^ 0x10
						final_bytes.append(hex(b))
					i+=1

				print(final_bytes)

				if final_bytes[0] == 0 and final_bytes[1] == 0x4d and final_bytes[2] == 0x0 and final_bytes[3] == 0x0b:
					print("short address = ", final_bytes[5], final_bytes[6])
				read_bytes = []

	def add_groups(self, light_address, light_ep, group_address):
		msg_type = 0x0060
		msg_type_list = utils.convert_int16_msb_lsb_list(msg_type)
		msg_type_msb = msg_type_list['msb']
		msg_type_lsb = msg_type_list['lsb']

		address_mode = 0x02
		destn_list = utils.convert_int16_msb_lsb_list(light_address)
		destn_msb = destn_list['msb']
		destn_lsb = destn_list['lsb']

		source_ep = 0x01

		group_address_list = utils.convert_int16_msb_lsb_list(group_address)
		group_address_msb = group_address_list['msb']
		group_address_lsb = group_address_list['lsb']

		content = [address_mode, destn_msb, destn_lsb, source_ep, light_ep, group_address_msb, group_address_lsb]
		length = utils.convert_int16_msb_lsb_list(len(content))
		length_msb = length['msb']
		length_lsb = length['lsb']

		checksum = utils.get_checksum(msg_type_msb=msg_type_msb, msg_type_lsb=msg_type_lsb, length_msb=length_msb, length_lsb=length_lsb, data=content)

		data = [msg_type_msb, msg_type_lsb, length_msb, length_lsb, checksum] + content
		bytes_to_send = utils.create_byte_stream_to_send(data_bytes=data)
		self.device.write(bytes_to_send)
		print(bytes_to_send)


	def run(self):
		self.synchronous_read()