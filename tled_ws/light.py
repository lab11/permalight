import requests
import json
import yaml

class Light():
  def __init__(self, channel, webapp_host, webapp_port):
    self.channel = channel
    self.host=webapp_host
    self.port=webapp_port

  def on(self):
    headers = {'Content-Type': 'application/json'}
    data = {'channel': self.channel}
    url = self.host+":%d"%self.port+"/on"
    rsp = requests.post(url, data=json.dumps(data), headers=headers)
    return rsp.text

  def off(self):
    headers = {'Content-Type': 'application/json'}
    data = {'channel': self.channel}
    url = self.host+":%d"%self.port+"/off"
    rsp = requests.post(url, data=json.dumps(data), headers=headers)
    return rsp.text

  def get_state(self):
    headers = {'Content-Type': 'application/json'}
    data = {'channel': self.channel}
    url = self.host+":%d"%self.port+"/get_state"
    rsp = requests.get(url, data=json.dumps(data), headers=headers).text
    return json.loads(rsp)['state']
