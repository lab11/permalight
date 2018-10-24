from utils import PARITY_CONSTANTS, BYTE_SIZE_CONSTANTS, STOP_BITS_CONSTANTS
import utils

class Light():
  def __init__(self, address, endpoint, controller, is_group=False):
    self.address = address
    self.endpoint = endpoint

    if is_group:
      self.address_mode = 0x01
    else:
      self.address_mode = 0x02
    self.state = -1
    self.level = -1

    self.controller = controller
    self.device = self.controller.get_device()

  def get_on_off_toggle_data(self, command):

    msg_type = 0x0092
    msg_type_list = utils.convert_int16_msb_lsb_list(msg_type)
    msg_type_msb = msg_type_list['msb']
    msg_type_lsb = msg_type_list['lsb']

    address_mode = self.address_mode
    destn_list = utils.convert_int16_msb_lsb_list(self.address)
    destn_msb = destn_list['msb']
    destn_lsb = destn_list['lsb']

    source_ep = 0x01

    content = [address_mode, destn_msb, destn_lsb, source_ep, self.endpoint, command]

    length = utils.convert_int16_msb_lsb_list(len(content))
    length_msb = length['msb']
    length_lsb = length['lsb']

    checksum = utils.get_checksum(msg_type_msb=msg_type_msb, msg_type_lsb=msg_type_lsb, length_msb=length_msb, length_lsb=length_lsb, data=content)

    data = [msg_type_msb, msg_type_lsb, length_msb, length_lsb, checksum] + content
    return data

  def off(self, print_return=False):
    self.state = 0
    data = self.get_on_off_toggle_data(command=0x0)
    bytes_to_send = utils.create_byte_stream_to_send(data_bytes=data)
    self.device.write(bytes_to_send)
    if print_return:
      rsp = [self.synchronous_read(), self.synchronous_read()]
      print (rsp)

  def on(self, print_return=False):
    self.state = 1
    data = self.get_on_off_toggle_data(command=0x01)
    bytes_to_send = utils.create_byte_stream_to_send(data_bytes=data)
    self.device.write(bytes_to_send)
    if print_return:
      rsp = [self.synchronous_read(), self.synchronous_read()]
      print (rsp)

  def toggle(self, print_return=False):
    self.state = not self.state
    data = self.get_on_off_toggle_data(command=0x02)
    bytes_to_send = utils.create_byte_stream_to_send(data_bytes=data)
    self.device.write(bytes_to_send)
    if print_return:
      rsp = [self.synchronous_read(), self.synchronous_read()]
      print (rsp)

  def set_level(self, level, transition_time=1, with_on_off=True, print_return=False):

    self.level = level
    msg_type = 0x0081
    msg_type_list = utils.convert_int16_msb_lsb_list(msg_type)
    msg_type_msb = msg_type_list['msb']
    msg_type_lsb = msg_type_list['lsb']

    address_mode = self.address_mode
    destn_list = utils.convert_int16_msb_lsb_list(self.address)
    destn_msb = destn_list['msb']
    destn_lsb = destn_list['lsb']

    source_ep = 0x01

    on_off = int(with_on_off)
    if int(level/100*0xFF) > 0xFF or level < 0x0:
      print ("out of bounds level : %d. 0x0<=level<=0xff", level)
      return -1

    transition_time_list = utils.convert_int16_msb_lsb_list(transition_time)
    transition_time_msb = transition_time_list['msb']
    transition_time_lsb = transition_time_list['lsb']

    content = [address_mode, destn_msb, destn_lsb, source_ep, self.endpoint, on_off, int(level/100*0xFF), transition_time_msb, transition_time_lsb]

    length = utils.convert_int16_msb_lsb_list(len(content))
    length_msb = length['msb']
    length_lsb = length['lsb']

    checksum = utils.get_checksum(msg_type_msb=msg_type_msb, msg_type_lsb=msg_type_lsb, length_msb=length_msb, length_lsb=length_lsb, data=content)

    data = [msg_type_msb, msg_type_lsb, length_msb, length_lsb, checksum] + content
    bytes_to_send = utils.create_byte_stream_to_send(data_bytes=data)
    self.device.write(bytes_to_send)

    if print_return:
      rsp = [self.synchronous_read(), self.synchronous_read()]
      print (rsp)

  def synchronous_read(self):
    line = self.device.read()
    read_bytes = []

    while line != b'\x03':
      read_bytes.append(line)
      line = self.device.read()

    read_bytes.append(line)
    return read_bytes
