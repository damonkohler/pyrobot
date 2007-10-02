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

import os
import sys
import time
import simplejson
import BaseHTTPServer

import pyrobot


class RoombaWebController(BaseHTTPServer.BaseHTTPRequestHandler):

  """Control and monitor the Roomba through a web interface."""

  def __init__(self):
    self.roomba = None
    self.sensors = None

  def __call__(self, *args, **kwargs):
    """We want a single controller across all threads."""
    # BaseHTTPRequestHandler is old-style. No super for us! :(
    BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, *args, **kwargs)
    return self

  def ResetRoomba(self):
    """Create a new Roomba and RoombaSensors, wake it, and control it."""
    self.roomba = pyrobot.Roomba()
    self.sensors = pyrobot.RoombaSensors(self.roomba)
    self.roomba.sci.Wake()
    self.roomba.Control(safe=False)

  def _SendHeaders(self):
    """Send response headers."""
    self.send_response(200)
    self.send_header("Content-type", "text/html")
    self.end_headers()

  def _RenderTemplate(self, template):
    """Render a template to the output stream."""
    template_file = open(os.path.join('templates', template))
    self.wfile.write(template_file.read())

  def _WriteStaticFile(self, static):
    """Write a static file to the output stream."""
    static_file = open(os.path.join('static', static))
    self.wfile.write(static_file.read())

  def do_HEAD(self):
    """Send headers on HEAD request."""
    self._SendHeaders()

  def do_GET(self):
    """Render index template or delegate to another GET handler."""
    self._SendHeaders()
    if self.path == '/':
      self._RenderTemplate('index.html')
    elif self.path == '/favico.ico':
      return
    elif self.path.startswith('/static'):
      self._WriteStaticFile(self.path[len('/static/'):])
    else:
      request = self.path.split('?')[0]
      request = request.replace('/', '_')
      handler = getattr(self, 'GET%s' % request)
      handler()

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
  assert len(sys.argv) == 3
  host, port = sys.argv[1:]
  port = int(port)
  controller = RoombaWebController()
  controller.ResetRoomba()
  server = BaseHTTPServer.HTTPServer((host, port), controller)
  print 'http://%s:%d/' % (host, port)
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    pass
  finally:
    server.close()


if __name__ == '__main__':
  main()
