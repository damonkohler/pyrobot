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

import logging
import StringIO
import sys
import simplejson
import gsd
import fido

FORMAT = '%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s'
DATE_FORMAT = '%H%M%S'


class FidoWeb(gsd.App):

  """Control and monitor the Robot through a web interface."""

  def __init__(self, arduino_tty='/dev/ttyUSB0', robot_tty='/dev/ttyUSB1'):
    self._fido = fido.Fido(arduino_tty, robot_tty)
    # Set up logging.
    self.web_log_stream = StringIO.StringIO()
    web_log_handler = logging.StreamHandler(self.web_log_stream)
    web_log_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(FORMAT)
    web_log_handler.setFormatter(formatter)
    logging.getLogger('').addHandler(web_log_handler)

  def GET_(self):
    """Render main UI."""
    self.Render(open('templates/index.html').read(), locals())

  def GET_favico_ico(self):
    """Ignore requets for favico.ico."""
    pass

  def GET_forward(self):
    """Drive forward in a straight line for 1 second."""
    self._fido.Forward()

  def GET_reverse(self):
    """Drive backward in a straight line for 1 second."""
    self._fido.Reverse()

  def GET_left(self):
    """Turn in place to the left."""
    self._fido.Left()

  def GET_right(self):
    """Turn in place to the right."""
    self._fido.Right()

  def GET_undock(self):
    """Backup out of dock."""
    self._fido.Undock()

  def GET_dock(self):
    """Start docking procedures."""
    self._fido.Dock()

  def GET_restart(self):
    """Restart systems in an emergency to get control of the robot."""
    self._fido.Restart()

  def GET_sensors(self):
    """Return a JSON object with various sensor data."""
    self.wfile.write(simplejson.dumps(self._fido.sensors.data))

  def GET_light_on(self):
    """Turn the light on."""
    logging.info('Turning the light on.')
    self._fido.arduino.PowerLight(True)

  def GET_light_off(self):
    """Turn the light off."""
    logging.info('Turning the light off.')
    self._fido.arduino.PowerLight(False)

  def GET_log(self):
    """Return a JSON object containing the last 500 logging messages."""
    log = '\n'.join(self.web_log_stream.getvalue().split('\n')[-500:])
    self.wfile.write(simplejson.dumps({'log': log}))

  def GET_speak(self, msgs=None):
    """Use flite to do text to speech."""
    self._fido.olpc.Speak(msgs[0])


def main():
  if not len(sys.argv) > 2:
    print 'python web_ui.py host port'
    sys.exit(1)
  host, port = sys.argv[1:3]
  port = int(port)

  arduino_tty = '/dev/ttyUSB0'
  robot_tty = '/dev/ttyUSB1'
  if len(sys.argv) == 5:
    arduino_tty = sys.argv[3]
    robot_tty = sys.argv[4]

  logging.basicConfig(level=logging.INFO, format=FORMAT, datefmt=DATE_FORMAT)

  fido_web = FidoWeb(arduino_tty, robot_tty)
  fido_web._fido.Start()
  print 'http://%s:%d/' % (host, port)
  fido_web.Serve(host, port)


if __name__ == '__main__':
  main()
