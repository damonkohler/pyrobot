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
import threading
import time
import simplejson
import gsd
import pyrobot
import arduino_controller

MINIMUM_BATTERY_LEVEL = 12000  # mV
MAXIMUM_BATTERY_LEVEL = 15000  # mV


class PowerManager(object):

  """Keeps track of the Robot's battery level and docks when necessary."""

  def __init__(self, arduino, robot, sensors):
    self.arduino = arduino
    self.robot = robot
    self.sensors = sensors
    self._join = False
    self._battery_monitor = None

  def _WaitForDock(self):
    """Block until the robot has started charging (i.e. docking complete)."""
    while True:
      self.sensors.GetAll()
      if self.sensors.sensors['charging']:
        return
      time.sleep(5)

  def BatteryMonitor(self):
    """Monitor the Robot's battery level."""
    while not self._join:
      self.sensors.GetAll()
      sensors = self.sensors.sensors
      charging = sensors['charging-state'] in (1, 2, 3)
      # NOTE(damonkohler): Other users have suggested monitoring voltage instead
      # because it's more reliable.
      voltage = sensors['voltage']
      if (voltage < MINIMUM_BATTERY_LEVEL) and not charging:
        self.robot.Dock()
        self._WaitForDock()
        # Disconnect power to the OLPC.
        self.arduino.Relay(False)
      if (voltage > MAXIMUM_BATTERY_LEVEL) and charging:
        # Reconnect power to the OLPC.
        self.arduino.Relay(True)
      time.sleep(5)

  def StartBatteryMonitor(self):
    """Start up the battery monitor."""
    self._battery_monitor = threading.Thread(target=self.BatteryMonitor)
    self._battery_monitor.start()

  def Stop(self):
    """Join all threads."""
    self._join = True
    if self._battery_monitor is not None:
      self._battery_monitor.join()
    self._join = False


class RobotWebController(gsd.App):

  """Control and monitor the Robot through a web interface."""

  def __init__(self, arduino_tty='/dev/ttyUSB0', robot_tty='/dev/ttyUSB1'):
    self.robot = pyrobot.Create(robot_tty)
    self.sensors = pyrobot.CreateSensors(self.robot)
    self.arduino = arduino_controller.ArduinoController(arduino_tty)
    self.power_manager = PowerManager(self.arduino, self.robot, self.sensors)
    self._stop_for_obstacles = True

    self.web_log_stream = StringIO.StringIO()
    web_log_handler = logging.StreamHandler(self.web_log_stream)
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
    web_log_handler.setFormatter(formatter) 
    logging.getLogger('').addHandler(web_log_handler)

  def Start(self):
    """Start controlling the robot."""
    logging.debug('Starting up.')
    try:
      self.arduino.Power(True)
    except arduino_controller.ArduinoControllerError:
      logging.debug('Failed to power on robot.')
    else:
      time.sleep(5)  # HACK(damonkohler): It takes a few seconds to power on.
    self.robot.SoftReset()
    self.robot.Control(safe=False)
    #self.power_manager.Stop()  # Just in case we're trying to restart.
    #self.power_manager.StartBatteryMonitor()

  def StopForObstacle(self, delay):
    """If we encounter an obstacle, reverse for a moment and return True."""
    start = time.time()
    while time.time() < start + delay:
      self.sensors.GetAll()
      sensors = self.sensors.sensors
      if (sensors['bump-left'] or
          sensors['bump-right'] or
          sensors['virtual-wall']):
        # We have to be going forward to trip these sensors, so negative
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
    if self._stop_for_obstacles:
      if not self.StopForObstacle(1):
        self.robot.SlowStop(pyrobot.VELOCITY_FAST)
    else:
      time.sleep(1)
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
    self.robot.Dock()

  def GET_sensors(self):
    """Return a JSON object with various sensor data."""
    try:
      self.sensors.GetAll(blocking=False)
      state = self.sensors.sensors['charging-state']
      self.sensors.sensors['charging-state'] = pyrobot.CHARGING_STATES[state]
    except pyrobot.PyRobotError:
      logging.debug('Failed to retrieve sensor data.')
    except KeyError:
      logging.debug('Bad sensor data :( No charging state found.')
    except IndexError:
      logging.debug('Bad sensor data :( Invalid charging state %r' % state)
    except TypeError:
      logging.debug('Bad sensor data :( Invalid charging state %r' % state)
    self.wfile.write(simplejson.dumps(self.sensors.sensors))

  def GET_light_on(self):
    """Turn the light on."""
    self.arduino.Light(True)

  def GET_light_off(self):
    """Turn the light off."""
    self.arduino.Light(False)

  def GET_create_on(self):
    """Turn the robot on."""
    self.arduino.Power(True)

  def GET_create_off(self):
    """Turn the robot on."""
    self.arduino.Power(False)

  def GET_relay_on(self):
    """Turn the relay on and connect the OLPC power."""
    self.arduino.Relay(True)

  def GET_relay_off(self):
    """Turn the relay off and disconnect the OLPC power."""
    self.arduino.Relay(False)

  def GET_restart(self):
    """Attempt to connect to the Create again."""
    self.Start()

  def GET_soft_reset(self):
    """Issue a soft reset to the Create."""
    self.robot.SoftReset()

  def GET_safe(self):
    """Turn on stopping for obstacles."""
    self._stop_for_obstacles = True

  def GET_full(self):
    """Turn off stopping for obstacles."""
    self._stop_for_obstacles = False

  def GET_log(self):
    """Return a JSON object containing logging messages."""
    log = self.web_log_stream.getvalue()
    self.wfile.write(simplejson.dumps({'log': log}))


def main():
  if not len(sys.argv) == 3:
    print 'python web_ui.py host port'
    sys.exit(1)
  host, port = sys.argv[1:]
  port = int(port)

  logging.basicConfig(level=logging.DEBUG,
                      format='%(asctime)s %(levelname)-8s %(message)s',
                      datefmt='%Y.%m.%d %H:%M:%S')

  controller = RobotWebController()
  controller.Start()
  print 'http://%s:%d/' % (host, port)
  controller.Serve(host, port) 


if __name__ == '__main__':
  main()
