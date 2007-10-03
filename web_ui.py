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

"""A web-based user interface using PyRobot and GSD."""

__author__ = "damonkohler@gmail.com (Damon Kohler)"

import os
import sys
import time
import simplejson
import gsd
import pyrobot


class RoombaWebController(gsd.App):

  """Control and monitor the Roomba through a web interface."""

  def __init__(self):
    self.roomba = None
    self.sensors = None

  def ResetRoomba(self):
    """Create a new Roomba and RoombaSensors, wake it, and control it."""
    self.roomba = pyrobot.Roomba()
    self.sensors = pyrobot.RoombaSensors(self.roomba)
    self.roomba.sci.Wake()
    self.roomba.Control(safe=False)

  def GET_(self):
    """Render main UI."""
    self.Render('templates/index.html', locals())

  def GET_favico_ico(self):
    """Ignore requets for favico.ico."""
    pass

  def GET_forward(self):
    """Drive forward in a straight line for 1 second."""
    self.roomba.DriveStraight(pyrobot.VELOCITY_FAST)
    time.sleep(1)
    self.roomba.SlowStop(pyrobot.VELOCITY_FAST)

  def GET_reverse(self):
    """Drive backward in a straight line for 1 second."""
    self.roomba.DriveStraight(-pyrobot.VELOCITY_FAST)
    time.sleep(1)
    self.roomba.SlowStop(-pyrobot.VELOCITY_FAST)

  def GET_left(self):
    """Turn in place to the left."""
    self.roomba.TurnInPlace(pyrobot.VELOCITY_SLOW, 'ccw')
    time.sleep(0.5)
    self.roomba.Stop()

  def GET_right(self):
    """Turn in place to the right."""
    self.roomba.TurnInPlace(pyrobot.VELOCITY_SLOW, 'cw')
    time.sleep(0.5)
    self.roomba.Stop()

  def GET_dock(self):
    """Start docking procedures."""
    self.roomba.sci.force_seeking_dock()
    self.roomba.sci.clean()

  def GET_sensors(self):
    """Return a JSON object with various sensor data."""
    self.sensors.GetAll()
    self.sensors.sensors['charging-state'] = \
      pyrobot.CHARGING_STATES[self.sensors.sensors['charging-state']]
    self.wfile.write(simplejson.dumps(self.sensors.sensors))

  def GET_reset(self):
    """Reset the Roomba."""
    self.ResetRoomba()
 

def main():
  if not len(sys.argv) == 3:
    print 'python web_ui.py host port'
    sys.exit(1)
  host, port = sys.argv[1:]
  port = int(port)
  controller = RoombaWebController()
  controller.ResetRoomba()
  print 'http://%s:%d/' % (host, port)
  controller.Serve(host, port) 

if __name__ == '__main__':
  main()
