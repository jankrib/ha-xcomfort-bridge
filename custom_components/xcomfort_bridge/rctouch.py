import logging
from math import ceil

import rx

from homeassistant.components.climate import ClimateEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback


from .const import DOMAIN, VERBOSE

_LOGGER = logging.getLogger(__name__)


def log(msg: str):
    if VERBOSE:
        _LOGGER.warning(msg)

class RcTouch:
    def __init__(self, bridge, device_id, name,device, state):
        self.bridge = bridge
        self.device_id = device_id
        self._device = device
        self.name = name
        self.state = rx.subject.BehaviorSubject(state)        

class RcTouchState:    
    # Typical 310-message
    #{"item":[{"deviceId":17,"info":[{"text":"1222","type":2,"value":"20.9"},{"text":"1223","type":2,"icon":1,"value":"42.5"}]},{"roomId":14,"mode":3,"valve":100,"setpoint":21,"temp":20.9,"humidity":42.5,"power":238.1,"frostDanger":0,"heatDanger":0,"windoorsOpen":0}]}

    def __init__(self, payload, power=0, setpoint=0, mode=0):    
        self.power = power     
        self.setpoint = setpoint   
        self.mode = mode    
        if 'info' in payload:
            for info in payload['info']:
                if info['text'] == "1222":
                    self.current_temperature = float(info['value'])
                if info['text'] == "1223":
                    self.current_humidity = float(info['value'])
        if 'item' in payload:
            for item in payload['item']:
                if 'deviceId' in item:
                    for info in item['info']:
                        if info['text'] == "1222":
                            self.current_temperature = float(info['value'])
                        if info['text'] == "1223":
                            self.current_humidity = int(info['value'])
                if 'roomId' in item:
                    if 'power' in item:
                        self.power = float(item['power'])  
                    if 'setpoint' in item:
                        self.setpoint = float(item['setpoint'])
                    if 'mode' in item:
                        self.mode = item['mode']
    def __str__(self):
        return f"RcTouchState({self.current_temperature}, {self.current_humidity}, {self.power}, {self.mode})"

    __repr__ = __str__                               