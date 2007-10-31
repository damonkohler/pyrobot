#!/usr/bin/python

# The MIT License
#
# Copyright (c) 2007 Damon Kohler
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""Additional controls for the Create through an Arduino.

This module is designed for use with the included Arduino sketch.

"""
__author__ = "damonkohler@gmail.com (Damon Kohler)"

import logging
import serial
import time

SERIAL_TIMEOUT = 2  # Number of seconds to wait for reads. 2 is generous.


class ArduinoControllerError(Exception):
  pass


class ArduinoController(object):

  """Controls for the Arduino."""

  def __init__(self, tty='/dev/ttyUSB0'):
    logging.debug('Connecting to Arduino using %s' % tty)
    self.ser = serial.Serial(tty, baudrate=9600, timeout=SERIAL_TIMEOUT)
    self.ser.open()
    time.sleep(2)  # HACK(damonkohler): It takes a few seconds to open.

  def _TogglePower(self):
    """Toggles the power button on the Create."""
    self.ser.write('P')  # 'P' for power.

  def _CheckPower(self):
    """Check to see if the Create is turned on."""
    logging.debug('Checking power.')
    self.ser.write('S')  # 'S' for sense or status.
    data = self.ser.read()
    if not data:
      raise ArduinoControllerError('Unable to read power status.')
    return bool(int(data))

  def PowerRobot(self, power):
    """Power the Create on or off."""
    on = self._CheckPower()
    if power and not on:
      logging.debug('Turning the robot on.')
      self._TogglePower()
    elif not power and on:
      logging.debug('Turning the robot off.')
      self._TogglePower()

  def Light(self, power):
    """Power the light on or off."""
    if power:
      self.ser.write('L')  # 'L' for light.
    else:
      self.ser.write('D')  # 'D' for dark.

  def PowerOlpc(self, power):
    """Power the relay on or off to connect/disconnect the OLPC."""
    if power:
      self.ser.write('V')  # 'V' for victory.
    else:
      self.ser.write('R')  # 'R' for relay.
