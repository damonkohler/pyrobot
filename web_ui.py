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
import olpc


class PowerManager(object):

  """Keeps track of the Robot's battery level and docks when necessary."""

  def __init__(self, arduino, robot, sensors):
    self.arduino = arduino
    self.robot = robot
    self.sensors = sensors
    self.olpc_pm = olpc.PowerManager()
    self._join = False
    self._battery_monitor = None

  def _GetAggregateSensorData(self):
    """Return a dict of all robot and OLPC sensor data."""
    sensor_data = {}
    self.sensors.GetAll()
    sensor_data.update(self.sensors.data)
    sensor_data.update(self.olpc_pm.GetAllSensorData())
    return sensor_data

  def BatteryMonitor(self):
    """Monitor the robot and OLPC battery levels to control charging.

    The following table illustrates when the batteries will be charging:

                                        Robot      OLPC
    Charging sources available:           Y          -
    + Robot battery charging              Y          N
    + OLPC battery not Normal or Full     Y          Y (overrides prev.)
    Charging sources not available        N          N

    """
    while not self._join:
      sensor_data = self._GetAggregateSensorData()
      if sensor_data['charging-sources-available']:
        if not sensor_data['charging-state']:
          self.robot.SoftReset()  # Robot won't charge until we reset it.
          continue  # Need to update sensor data.
        if sensor_data['charging-state'] not in (1, 2):
          # Robot is not charging or is trickle charging.
          self.arduino.PowerOlpc(True)
        elif sensor_data['olpc_status'] not in ('Normal', 'Full'):
          # OLPC power state is getting critical.
          self.arduino.PowerOlpc(True)
        else:
          # Let the robot charge until it's done or the OLPC needs power.
          self.arduino.PowerOlpc(False)
      else:
        # No charging sources available.
        self.arduino.PowerOlpc(False)

  def StartBatteryMonitor(self):
    """Start up the battery monitor."""
    self._battery_monitor = threading.Thread(target=self.BatteryMonitor)
    self._battery_monitor.setDaemon(True)
    self._battery_monitor.start()

  def Stop(self):
    """Join all threads."""
    self._join = True
    if self._battery_monitor is not None:
      self._battery_monitor.join()
    self._join = False

  def Dock(self):
    """Drive the robot into the docking station.

    This is required since the cover-and-dock demo doesn't drive the robot
    fast enough to get into the dock when it has extra gear on it (it weighs
    too much). It would probably work on carpet if it's squishy enough though.

    """
    while True:
      sensor_data = self._GetAggregateSensorData()
      opcode = sensor_data['remote-opcode']
      if opcode == pyrobot.REMOTE_OPCODES['red_buoy']:
        self.robot.Drive(pyrobot.VELCOITY_SLOW, 500)
      if opcode == pyrobot.REMOTE_OPCODES['green_buoy']:
        self.robot.Drive(pyrobot.VELOCITY_SLOW, -500)
      if opcode == pyrobot.REMOTE_OPCODES['red_buoy_and_green_buoy']:
        self.robot.DriveStraight(pyrobot.VELOCITY_FAST)
      if sensor_data['bump-left'] or sensor_data['bump-right']:
        self.robot.Stop()
        self.robot.SoftReset()
        break
      time.sleep(1)


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
    self.power_manager.Stop()  # Just in case we're trying to restart.
    self.power_manager.StartBatteryMonitor()
    self.power_manager.olpc_pm.SetDconSleep(True)

  def StopForObstacle(self, delay):
    """If we encounter an obstacle, reverse for a moment and return True."""
    start = time.time()
    while time.time() < start + delay:
      self.sensors.GetAll()
      sensors = self.sensors.data
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
    sensor_data = {}
    try:
      self.sensors.GetAll(blocking=False)
    except pyrobot.PyRobotError:
      logging.debug('Failed to retrieve sensor data.')
    else:
      state = self.sensors.data['charging-state']
      try:
        self.sensors.data['charging-state'] = pyrobot.CHARGING_STATES[state]
      except KeyError:
        logging.debug('Bad sensor data :( No charging state found.')
      except IndexError, TypeError:
        logging.debug('Bad sensor data :( Invalid charging state %r' % state)
    sensor_data.update(self.sensors.data)

    olpc_pm = olpc.PowerManager()
    sensor_data.update(olpc_pm.GetAll())

    self.wfile.write(simplejson.dumps(sensor_data))

  def GET_light_on(self):
    """Turn the light on."""
    logging.debug('Turning the light on.')
    self.arduino.Light(True)

  def GET_light_off(self):
    """Turn the light off."""
    logging.debug('Turning the light off.')
    self.arduino.Light(False)

  def GET_robot_on(self):
    """Turn the robot on."""
    logging.debug('Turning the robot on.')
    self.arduino.PowerRobot(True)

  def GET_robot_off(self):
    """Turn the robot off."""
    logging.debug('Turning the robot off.')
    self.arduino.PowerRobot(False)

  def GET_relay_on(self):
    """Turn the relay on and connect the OLPC power."""
    logging.debug('Turning the relay on.')
    self.arduino.PowerOlpc(True)

  def GET_relay_off(self):
    """Turn the relay off and disconnect the OLPC power."""
    logging.debug('Turning the relay off.')
    self.arduino.PowerOlpc(False)

  def GET_restart(self):
    """Attempt to connect to the Create again."""
    logging.debug('Restarting...')
    self.Start()

  def GET_soft_reset(self):
    """Issue a soft reset to the Create."""
    self.robot.SoftReset()

  def GET_safe(self):
    """Turn on stopping for obstacles."""
    logging.debug('Turning on stopping for obstacles.')
    self._stop_for_obstacles = True

  def GET_full(self):
    """Turn off stopping for obstacles."""
    logging.debug('Turning off stopping for obstacles.')
    self._stop_for_obstacles = False

  def GET_log(self):
    """Return a JSON object containing the last 500 logging messages."""
    log = '\n'.join(self.web_log_stream.getvalue().split('\n')[-500:])
    self.wfile.write(simplejson.dumps({'log': log}))

  def GET_say(self, msgs=None):
    """Use flite to do text to speech."""
    msgs = msgs or ['Nothing to say.']
    flite = olpc.Flite()
    for msg in msgs:
      flite.Say(msg)


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
