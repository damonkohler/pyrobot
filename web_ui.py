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


class CreateWebController(gsd.App):

  """Control and monitor the Create through a web interface."""

  def __init__(self):
    self.robot = None
    self.sensors = None

  def ResetCreate(self):
    """Create a new Create and CreateSensors, wake it, and control it."""
    self.robot = pyrobot.Create()
    self.sensors = pyrobot.CreateSensors(self.robot)
    self.robot.Control(safe=False)

  def StopForObstacle(self, delay):
    """If we encounter an obstacle, reverse for a moment and return True."""
    start = time.time()
    while time.time() < start + delay:
      self.sensors.GetAll()
      sensors = self.sensors.sensors
      if (sensors['bump-left'] or
          sensors['bump-right'] or
          sensors['virtual-wall']):
        # We have to be going forward to trip the wall sensor, so negative
        # velocity has to be correct.
        self.robot.DriveStraight(-pyrobot.VELOCITY_SLOW)
        time.sleep(1)
        self.robot.Stop()
        return True
      time.sleep(0.1)

  def GET_(self):
    """Render main UI."""
    self.Render(open('templates/index.html').read(), locals())

  def GET_favico_ico(self):
    """Ignore requets for favico.ico."""
    pass

  def GET_forward(self):
    """Drive forward in a straight line for 1 second."""
    self.robot.DriveStraight(pyrobot.VELOCITY_FAST)
    if not self.StopForObstacle(1):
      self.robot.SlowStop(pyrobot.VELOCITY_FAST)

  def GET_reverse(self):
    """Drive backward in a straight line for 1 second."""
    self.robot.DriveStraight(-pyrobot.VELOCITY_FAST)
    time.sleep(1)
    self.robot.SlowStop(-pyrobot.VELOCITY_FAST)

  def GET_left(self):
    """Turn in place to the left."""
    self.robot.TurnInPlace(pyrobot.VELOCITY_SLOW, 'ccw')
    time.sleep(0.25)
    self.robot.Stop()

  def GET_right(self):
    """Turn in place to the right."""
    self.robot.TurnInPlace(pyrobot.VELOCITY_SLOW, 'cw')
    time.sleep(0.25)
    self.robot.Stop()

  def GET_dock(self):
    """Start docking procedures."""
    self.robot.sci.force_seeking_dock()

  def GET_sensors(self):
    """Return a JSON object with various sensor data."""
    self.sensors.GetAll()
    self.sensors.sensors['charging-state'] = \
      pyrobot.CHARGING_STATES[self.sensors.sensors['charging-state']]
    self.wfile.write(simplejson.dumps(self.sensors.sensors))

  def GET_reset(self):
    """Reset the Create."""
    self.ResetCreate()
 

def main():
  if not len(sys.argv) == 3:
    print 'python web_ui.py host port'
    sys.exit(1)
  host, port = sys.argv[1:]
  port = int(port)
  controller = CreateWebController()
  controller.ResetCreate()
  print 'http://%s:%d/' % (host, port)
  controller.Serve(host, port) 


if __name__ == '__main__':
  main()
