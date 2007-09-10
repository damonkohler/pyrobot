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

"""A web-based user interface using PyRobot.

This web interface is designed for use with an OLPC controlled Roomba.

"""
__author__ = "damonkohler@gmail.com (Damon Kohler)"

import olpc
import os
import pyrobot
import web
import sys
import time
import simplejson

render = web.template.render('templates/')


class RoombaWebController(object):

  """Control and monitor the Roomba through a web interface."""

  def __init__(self):
    self.roomba = None
    self.sensors = None

  # TODO(damonkohler): This is dumb.
  def __call__(self):
    """Pretend to construct ourselves by returning self when called.

    web.py expects callables in the URL mapping (why?), but we want to keep
    just one instance of this class.

    """
    return self

  def StartWebcam(self):
    """Start up the OLPC webcam feed."""
    if not os.path.exists('static'):
      os.mkdir('static')
    camera = olpc.Camera('static/webcam.png')
    camera.StartWebcam()

  def StartMicrophone(self):
    """Start up the OLPC microphone feed."""
    if not os.path.exists('static'):
      os.mkdir('static')
    microphone = olpc.Microphone('static/sound.ogg')
    microphone.StartMicrophone()

  def ResetRoomba(self):
    """Create a new Roomba and RoombaSensors, wake it, and control it."""
    self.roomba = pyrobot.Roomba()
    self.sensors = pyrobot.RoombaSensors(self.roomba)
    self.roomba.sci.Wake()
    self.roomba.Control()

  GET = web.autodelegate('GET_')

  def GET_(self):
    """Display the UI."""
    print render.index()

  def GET_kill(self):
    """Kill the web server."""
    sys.exit(0)

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
    print simplejson.dumps(self.sensors.sensors)

  def GET_reset(self):
    """Reset the Roomba."""
    self.ResetRoomba()
 

def main():
  controller = RoombaWebController()
  controller.ResetRoomba()
  controller.StartWebcam()
  controller.StartMicrophone()
  web.webapi.internalerror = web.debugerror
  urls = ('/(.*)', 'controller')
  web.run(urls, locals())


if __name__ == '__main__':
  main()
