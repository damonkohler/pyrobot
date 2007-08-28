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

"""iRobot Roomba/Create Serial Control Interface (SCI).

PyRobot was originally based on openinterface.py, developed by iRobot
Corporation. Many of the docstrings from openinterface.py, particularly those
which describe the specification, are also used here.

"""
__author__ = "damonkohler@gmail.com (Damon Kohler)"

import serial
import struct
import time

ROOMBA_OPCODES = dict(
    start = 128,
    baud = 129,
    control = 130,
    safe = 131,
    full = 132,
    power = 133,
    spot = 134,
    cover = 135,
    demo = 136,
    drive = 137,
    motors = 138,
    leds = 139,
    song = 140,
    play_song = 141,
    sensors = 142,
    cover_and_seek_dock = 143,
    )

CREATE_OPCODES = dict(
    pwm_low_side_drivers = 144,
    direct_drive = 145,
    # 146?
    digital_outputs = 147,
    stream = 148,
    query_list = 149,
    pause_resume_stream = 150,
    send_ir = 151,
    script = 152,
    play_script = 153,
    show_script = 154,
    wait_time = 155,
    wait_distance = 156,
    wait_angle = 157,
    wait_event = 158,
    )

IR_OPCODES = dict(
    left = 129,
    forward = 130,
    right = 131,
    spot = 132,
    max = 133,
    small = 134,
    medium = 135,
    large = 136,
    clean = 136,
    #stop = 137, Duplicate.
    power = 138,
    arc_left = 139,
    arc_right = 140,
    #stop = 141, Duplicate.
    download = 142,
    seek_dock = 143,
    # 144-240?
    reserved = 240,
    # 241?
    force_field = 242,
    # 243?
    green_buoy = 244,
    # 245?
    red_buoy_and_force = 246,
    # 247?
    red_buoy = 248,
    # 249-251?
    red_and_green_buoy = 252,
    red_green_and_force = 254,
    )

# From: http://www.harmony-central.com/MIDI/Doc/table2.html
MIDI_TABLE = {'rest': 0, 'R': 0, 'pause': 0,
              'G1': 31, 'G#1': 32, 'A1': 33,
              'A#1': 34, 'B1': 35,

              'C2': 36, 'C#2': 37, 'D2': 38,
              'D#2': 39, 'E2': 40, 'F2': 41,
              'F#2': 42, 'G2': 43, 'G#2': 44,
              'A2': 45, 'A#2': 46, 'B2': 47,

              'C3': 48, 'C#3': 49, 'D3': 50,
              'D#3': 51, 'E3': 52, 'F3': 53,
              'F#3': 54, 'G3': 55, 'G#3': 56,
              'A3': 57, 'A#3': 58, 'B3': 59,

              'C4': 60, 'C#4': 61, 'D4': 62,
              'D#4': 63, 'E4': 64, 'F4': 65,
              'F#4': 66, 'G4': 67, 'G#4': 68,
              'A4': 69, 'A#4': 70, 'B4': 71,

              'C5': 72, 'C#5': 73, 'D5': 74,
              'D#5': 75, 'E5': 76, 'F5': 77,
              'F#5': 78, 'G5': 79, 'G#5': 80,
              'A5': 81, 'A#5': 82, 'B5': 83,

              'C6': 84, 'C#6': 85, 'D6': 86,
              'D#6': 87, 'E6': 88, 'F6': 89,
              'F#6': 90, 'G6': 91, 'G#6': 92,
              'A6': 93, 'A#6': 94, 'B6': 95,

              'C7': 96, 'C#7': 97, 'D7': 98,
              'D#7': 99, 'E7': 100, 'F7': 101,
              'F#7': 102, 'G7': 103, 'G#7': 104,
              'A7': 105, 'A#7': 106, 'B7': 107,

              'C8': 108, 'C#8': 109, 'D8': 110,
              'D#8': 111, 'E8': 112, 'F8': 113,
              'F#8': 114, 'G8': 115, 'G#8': 116,
              'A8': 117, 'A#8': 118, 'B8': 119,

              'C9': 120, 'C#9': 121, 'D9': 122,
              'D#9': 123, 'E9': 124, 'F9': 125,
              'F#9': 126, 'G9': 127}

# Drive constants.
RADIUS_TURN_IN_PLACE_CW = -1
RADIUS_TURN_IN_PLACE_CCW = 1
RADIUS_STRAIGHT = 32768
RADIUS_MAX = 2000

VELOCITY_MAX = 500  # mm/s
VELOCITY_SLOW = VELOCITY_MAX * 0.33
VELOCITY_QUICK = VELOCITY_MAX * 0.66
VELOCITY_FAST = VELOCITY_MAX

WHEEL_SEPARATION = 298  # mm


class SerialCommandInterface(object):

  """A higher-level wrapper around PySerial specifically designed for use with
  iRobot's SCI.

  """
  def __init__(self, tty, baudrate):
    self.ser = serial.Serial(tty, baudrate=baudrate)
    self.ser.open()
    self.opcodes = {}

  def Wake(self):
    """Wake up robot."""
    self.ser.setRTS(0)
    time.sleep(0.1)
    self.ser.setRTS(1)
    time.sleep(1)  # Technically it should wake after 500ms.

  def AddOpcodes(self, opcodes):
    """Add available opcodes to the SCI."""
    self.opcodes.update(opcodes)

  def Send(self, bytes):
    """Send a string of bytes to the robot."""
    self.ser.write(struct.pack('B' * len(bytes), *bytes))

  def __getattr__(self, name):
    """Creates methods for opcodes on the fly.

    Each opcode method sends the opcode optionally followed by a string of
    bytes.

    """
    if name in self.opcodes:
      def SendOpcode(*bytes):
        self.Send([self.opcodes[name]] + list(bytes))
      return SendOpcode
    raise AttributeError


class Roomba(object):

  """Represents a Roomba robot."""

  def __init__(self, tty='/dev/ttyUSB0'):
    self.sci = SerialCommandInterface(tty, 57600)
    self.sci.AddOpcodes(ROOMBA_OPCODES)

  def Control(self):
    """Start the robot's SCI interface and place it in safe mode."""
    self.sci.start()
    self.sci.control()

  def Drive(self, velocity, radius):
    """Controls Roomba's drive wheels.

    NOTE(damonkohler): The following specification applies to both the Roomba
    and the Create.

    The Roomba takes four data bytes, interpreted as two 16-bit signed values
    using two's complement. The first two bytes specify the average velocity
    of the drive wheels in millimeters per second (mm/s), with the high byte
    being sent first. The next two bytes specify the radius in millimeters at
    which Roomba will turn. The longer radii make Roomba drive straighter,
    while the shorter radii make Roomba turn more. The radius is measured from
    the center of the turning circle to the center of Roomba.

    A Drive command with a positive velocity and a positive radius makes
    Roomba drive forward while turning toward the left. A negative radius
    makes Roomba turn toward the right. Special cases for the radius make
    Roomba turn in place or drive straight, as specified below. A negative
    velocity makes Roomba drive backward.

    Also see DriveStraight and TurnInPlace convenience methods.

    """
    assert struct.calcsize('H') == 2, 'Expecting 2-byte shorts. Doh!'
    # Mask integers to 2 bytes.
    velocity = int(velocity) & 0xffff
    radius = int(radius) & 0xffff
    # Pack as shorts to get 2 x 2 byte integers. Unpack as 4 bytes to send.
    # TODO(damonkohler): The 4 unpacked bytes will just be repacked later,
    # that seems dumb to me.
    bytes = struct.unpack('4B', struct.pack('>2H', velocity, radius))
    self.sci.drive(*bytes)

  def Stop(self, duration=None):
    """Set velocity and radius to 0 to stop the robot after optionally
    delaying for 'duration' seconds.

    """
    if duration is not None:
      time.sleep(duration)
    self.Drive(0, 0)

  def DriveStraight(self, velocity):
    """Drive in a straight line."""
    self.Drive(velocity, RADIUS_STRAIGHT)

  def TurnInPlace(self, velocity, direction):
    """Turn in place either clockwise or counter-clockwise."""
    valid_directions = {'cw': RADIUS_TURN_IN_PLACE_CW,
                        'ccw': RADIUS_TURN_IN_PLACE_CCW}
    self.Drive(velocity, valid_directions[direction])


if __name__ == '__main__':
  """Do a little dance."""
  r = Roomba()
  r.sci.Wake()
  r.Control()
  time.sleep(0.25)
  r.TurnInPlace(VELOCITY_QUICK, 'cw')
  time.sleep(0.25)
  r.TurnInPlace(VELOCITY_QUICK, 'ccw')
  time.sleep(0.25)
  r.DriveStraight(VELOCITY_FAST)
  r.Stop(0.25)
