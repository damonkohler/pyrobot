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

from __future__ import with_statement

"""A web-based user interface using PyRobot and GSD."""

__author__ = "damonkohler@gmail.com (Damon Kohler)"

import logging
import StringIO
import sys
import simplejson
import gsd
import fido
import Queue
import threading
import urllib2
import motion
import time

FORMAT = '%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s'
DATE_FORMAT = '%H%M%S'
MAX_COMET_QUEUE_SIZE = 50


class WebLogStream(object):

  def __init__(self, queues):
    self.queues = queues

  def open(self, *args, **kwargs):
    pass

  def read(self, *args, **kwargs):
    pass

  def write(self, value):
    for address, queue in self.queues.items():
      queue.put(('logging', value.strip()))
      if queue.qsize() > MAX_COMET_QUEUE_SIZE:
        # We assume the user is no longer listening and remove their queue.
        del self.queues[address]

  def flush(self):
    pass



class FidoWeb(gsd.App):

  """Control and monitor the Robot through a web interface."""

  def __init__(self, arduino_tty='/dev/ttyUSB0', robot_tty='/dev/ttyUSB1'):
    self._fido = fido.Fido(arduino_tty, robot_tty)
    self._motion = motion.MotionController('localhost', 8082)
    self._lock = threading.Lock()
    self._comet_queues = {}
    # Set up logging.
    self.web_log_stream = WebLogStream(self._comet_queues)
    web_log_handler = logging.StreamHandler(self.web_log_stream)
    web_log_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(FORMAT, datefmt=DATE_FORMAT)
    web_log_handler.setFormatter(formatter)
    logging.getLogger('').addHandler(web_log_handler)

  def GET_(self, handler):
    """Render main UI."""
    handler.Render(open('templates/index.html').read(), locals())

  def GET_favicon_ico(self, handler):
    """Ignore requets for favico.ico."""
    pass

  def GetCometQueue(self, handler):
    with self._lock:
      client_addr = handler.client_address[0]
      if client_addr not in self._comet_queues:
        self._comet_queues[client_addr] = Queue.Queue()
        logging.info('New client %s.' % client_addr)
    return self._comet_queues[client_addr]

  def GET_comet(self, handler):
    queue = self.GetCometQueue(handler)
    try:
      key, value = queue.get(timeout=60)
    except Queue.Empty:
      handler.Render('500 Error', response=500)
    else:
      handler.wfile.write(simplejson.dumps({'key': key, 'value': value}))

  def GET_forward(self, handler):
    """Drive forward in a straight line for 1 second."""
    self._fido.Forward()

  def GET_reverse(self, handler):
    """Drive backward in a straight line for 1 second."""
    self._fido.Reverse()

  def GET_left(self, handler):
    """Turn in place to the left."""
    self._fido.Left()

  def GET_right(self, handler):
    """Turn in place to the right."""
    self._fido.Right()

  def GET_undock(self, handler):
    """Backup out of dock."""
    self._fido.Undock()

  def GET_dock(self, handler):
    """Start docking procedures."""
    self._fido.Dock()

  def GET_restart(self, handler):
    """Restart systems in an emergency to get control of the robot."""
    self._fido.Restart()

  def GET_sensors(self, handler):
    """Return a JSON object with various sensor data."""
    handler.wfile.write(simplejson.dumps(self._fido.sensors.data))

  def GET_light_on(self, handler):
    """Turn the light on."""
    logging.info('Turning the light on.')
    self._fido.arduino.PowerLight(True)

  def GET_light_off(self, handler):
    """Turn the light off."""
    logging.info('Turning the light off.')
    self._fido.arduino.PowerLight(False)

  def GET_speak(self, handler, msgs=None):
    """Use flite to do text to speech."""
    self._fido.olpc.Speak(msgs[0])

  def GET_track(self, handler, x, y):
    """Track camera to absolute position x, y."""
    self._motion.Track(x, y)

  def GET_rearview(self, handler):
    """Switch to rearview camera."""
    self._motion.Set('videodevice', '/dev/video0')
    time.sleep(1)
    self._motion.Write()
    time.sleep(1)
    self._motion.Restart()

  def GET_frontview(self, handler):
    """Switch to frontview camera."""
    self._motion.Set('videodevice', '/dev/video1')
    time.sleep(1)
    self._motion.Write()
    time.sleep(1)
    self._motion.Restart()


def main():
  arduino_tty = '/dev/ttyUSB0'
  robot_tty = '/dev/ttyUSB1'
  if len(sys.argv) == 5:
    arduino_tty = sys.argv[3]
    robot_tty = sys.argv[4]

  logging.basicConfig(level=logging.INFO, format=FORMAT, datefmt=DATE_FORMAT)

  fido_web = FidoWeb(arduino_tty, robot_tty)
  fido_web._fido.Start()
  fido_web._motion.Start()
  fido_web.Main()


if __name__ == '__main__':
  main()
