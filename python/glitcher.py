"""Python library to interface the VHDL code using uart."""

import serial
import time
import typing
import sys

import random
from stlink import *
import json
import collections

def config(power=False, trigger=False, retrigger=False, triggered=False, trigger_stay_active=False):
    return 0x80 | trigger_stay_active << 4 | triggered << 3 | retrigger << 2 | trigger << 1 | power

class X(object):
    def __init__(self, ser):
        self.ser = ser
    def read(self, *args):
        return self.ser.read(*args)
    def write(self, *args):
        print('write', args)
        return self.ser.write(*args)

Combo = collections.namedtuple('Combo', 'trigger_count delay duration')

class Glitcher(object):
    # prints a status update after the specified number of attempts
    update_interval: int = 10
    repeats: int = 3

    combo: Combo
    combo_index: int
    combos: list[Combo]
    
    logfilename: str = 'params.log'

    def __init__(self, filename: str, crowbar: bool=False, power_reset: bool=False, randomize: bool=False):
        """
        crowbar: if False assumes we have a regular switch, if True assumes
            we're shorting VDD & Ground, i.e. the default state for the glitch
            pin is off.
        power_reset: If true uses the glitch pin to reset the device between tries.
        """
        self.ser = (serial.Serial(filename, 28800, timeout=.001))
        self.crowbar = crowbar
        self.power_reset = crowbar or power_reset
        self.randomize = False
        self.
    
    def write(self, packet):
        """writes the packet to the serial line."""
        self.ser.write(packet)
        self.ser.flush()
        # heuristic to increase chances that the device actually received
        # the settings.
        time.sleep(len(packet)/self.ser.baudrate)

    def config(self):
        """Sets the params for a glitching attack."""
        combo = self.combo

        assert 1 <= combo.delay <= (1 << 21)
        assert 1 <= combo.duration <= (1 << 7)
        assert 0 <= combo.trigger_count <= (1 << 14)
        
        self.reset()
        self.clear()
        packet = bytearray(7)
        packet[0] = config(power=not self.power_reset)

        # we subtract 1, since we always one cycle delay in processing
        packet[1] = (combo.delay - 1) & 0x7f
        packet[2] = ((combo.delay - 1) >> 7) & 0x7f
        packet[3] = ((combo.delay - 1) >> 14) & 0x7f
        packet[4] = (combo.duration - 1) & 0x7f
        packet[5] = (combo.trigger_count) & 0x7f
        packet[6] = (combo.trigger_count >> 7) & 0x7f
        self.write(packet)        

    def enable_trigger(self):
        """Enables the trigger."""
        self.write(bytearray([config(power=self.crowbar, trigger=True)]))

    def clear(self):
        """Clears any buffered incoming data from the serial line."""
        self.ser.read(1000000)

    def reset(self, power=None):
        """Resets the circuit for the next attack."""
        if power is None: power = not self.power_reset
        self.ser.write(bytearray([config(power=power)]))

    def create_combo(self) -> typing.Iterable[Combo]:
        """Return the array of items to try."""
        raise NotImplementedError()
    
    def status(self):
        return '{:.2f} i={:d} {:s}'.format(100 * self.combo_index / len(self.combos), self.combo_index, self.combo)
      
    def log_result(self, result):
      print('XXX', result, self.status)
      with open(self.logfilename, 'a') as f:
          combo = self.combo
          f.write(json.dumps(dict(
            res=result.decode('latin1'),
            trigger_count=combo.trigger_count,
            delay=combo.delay,
            duration=combo.duration)
          ) + '\n')

    def run_one(self):
      self.config(combo)
      result = self.check()
      if result:
          self.log_result(result)

    def run_all(self):
        self.combos = list(self.create_combo())
        if self.randomize:
          random.shuffle(self.combos)

        start = time.time()
        
        if 1: #while True:
            for i, combo in enumerate(combos):
              self.combo_index = i
              self.combo = combo
              self.status = self.status()
              if i % self.update_interval == 0: 
                  speed = self.update_interval / (time.time() - start)
                  eta = int((len(combo) - i) / speed / 60)
                  start = time.time()
                  print(status, '{:.2f}/s, ETA: {:d}:{:02d}m'.format(speed, eta//60, eta%60), flush=True)
              for j in range(self.repeats):  # try each spot 3 times
                try:
                  self.run_one(j)
                except RuntimeError as e:
                    print(self.status, j, e, flush=True)
                    self.clear()
                except AssertionError as e:
                    print(self.status, j, e)

if __name__ == '__main__':
    import sys
    glitcher = Glitcher(sys.argv[1])#, sys.argv[2])
    try:
        glitcher.run()
    finally:
        glitcher.reset()
        glitcher.reset(power=not CROWBAR)
