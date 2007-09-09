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

urls = (
    '/', 'Index',
    '/forward', 'Forward',
    '/reverse', 'Reverse',
    '/left', 'Left',
    '/right', 'Right',
    '/dock', 'Dock',
    '/webcam', 'Webcam',
    '/sensors', 'Sensors',
    '/kill', 'Kill',
    )

render = web.template.render('templates/')

roomba = pyrobot.Roomba()
sensors = pyrobot.RoombaSensors(roomba)
roomba.Control()

if not os.path.exists('static'):
  os.mkdir('static')
camera = olpc.Camera('static/webcam.png')
camera.StartWebcam()


class Index(object):

  """Display the interface."""

  def GET(self):
    print render.index()


class Kill(object):

  """Kill the web server."""

  def GET(self):
    sys.exit(0)


class Forward(object):

  """Drive forward in a straight line for 1 second."""

  def GET(self):
    roomba.DriveStraight(pyrobot.VELOCITY_FAST)
    time.sleep(1)
    roomba.Stop()
    web.seeother('/')


class Reverse(object):

  """Drive backward in a straight line for 1 second."""

  def GET(self):
    roomba.DriveStraight(-pyrobot.VELOCITY_FAST)
    time.sleep(1)
    roomba.Stop()
    web.seeother('/')


class Left(object):

  """Turn in place to the left for 0.25 seconds."""

  def GET(self):
    roomba.TurnInPlace(pyrobot.VELOCITY_FAST, 'ccw')
    time.sleep(0.25)
    roomba.Stop()
    web.seeother('/')


class Right(object):

  """Turn in place to the right for 0.25 seconds."""

  def GET(self):
    roomba.TurnInPlace(pyrobot.VELOCITY_FAST, 'cw')
    time.sleep(0.25)
    roomba.Stop()
    web.seeother('/')


class Dock(object):

  """Start docking procedures."""

  def GET(self):
    roomba.sci.force_seeking_dock()
    roomba.sci.clean()
    web.seeother('/')

class Sensors(object):

  """Return a JSON object with various sensor data."""

  def GET(self):
    sensors.GetAll()
    sensors.sensors['charging-state'] = \
      pyrobot.CHARGING_STATES[sensors.sensors['charging-state']]
    print simplejson.dumps(sensors.sensors)
 

web.webapi.internalerror = web.debugerror

if __name__ == '__main__':
  web.run(urls, globals(), web.reloader)
