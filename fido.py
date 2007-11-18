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

"""Fido is a telepresence robot."""

__author__ = "damonkohler@gmail.com (Damon Kohler)"

import logging
import sys
import threading
import time
import pyrobot
import arduino_controller
import olpc_controller
import random

SENSOR_DELAY = 0.05
MOVE_DELAY = 1
TURN_DELAY = 0.25
DOCKING_TIME_LIMIT = 60
POWER_MANAGER_DELAY = 60

# TODO(damonkohler): Keep some global state about our velocity and default
# movement velocities/durations? It would be nice not to have to pass it
# around the whole time.


class Fido(object):

  """Fido is a telepresence robot."""

  def __init__(self, arduino_tty='/dev/ttyUSB0', robot_tty='/dev/ttyUSB1'):
    self.arduino = arduino_controller.ArduinoController(arduino_tty)
    self.robot = pyrobot.Create(robot_tty)
    self.robot.safe = False  # Use full mode for control.
    self.olpc = olpc_controller.OlpcController()
    # Add Fido services.
    self.sensors = FidoSensors(self)
    self.power_manager = FidoPowerManager(self)

  def StartServices(self):
    logging.info('Starting up Fido services.')
    self.sensors.Start()
    time.sleep(5)  # Give the sensors a chance to update.
    self.power_manager.Start()

  def StartRobot(self):
    logging.info('Starting up the robot.')
    self.arduino.PowerOlpc(False)
    self.arduino.PowerRobot(True)
    self.robot.SoftReset()
    self.robot.Control()
    if not self.arduino.CheckPower():
      logging.warn('Failed to start robot. Retrying.')
      self.StartRobot()

  def StartOlpc(self):
    logging.info('Starting up the OLPC.')
    self.olpc.SetDconSleep(True)
    self.olpc.ConfigureAudio()
    #self.olpc.StreamAudio('10.171.236.100', 8000)

  def Start(self):
    """Start controlling the robot."""
    self.StartOlpc()
    self.StartRobot()
    self.StartServices()

  def Forward(self, safe=True):
    """Drive forward, stopping for obstacles by default."""
    logging.info('Forward.')
    self.robot.DriveStraight(pyrobot.VELOCITY_FAST)
    if safe and (not self.StopForObstacle(MOVE_DELAY)):
      self.robot.SlowStop(pyrobot.VELOCITY_FAST)
    elif not safe:
      time.sleep(MOVE_DELAY)
      self.robot.Stop()

  def Reverse(self):
    """Drive in reverse."""
    logging.info('Reverse.')
    self.robot.DriveStraight(-pyrobot.VELOCITY_FAST)
    time.sleep(MOVE_DELAY)
    self.robot.SlowStop(-pyrobot.VELOCITY_FAST)

  def Right(self):
    """Turn in place to the right."""
    logging.info('Right.')
    self.robot.TurnInPlace(pyrobot.VELOCITY_SLOW, 'cw')
    time.sleep(TURN_DELAY)
    self.robot.Stop()

  def Left(self):
    """Turn in place to the left."""
    logging.info('Left.')
    self.robot.TurnInPlace(pyrobot.VELOCITY_SLOW, 'ccw')
    time.sleep(TURN_DELAY)
    self.robot.Stop()

  def StopForObstacle(self, delay):
    """If we encounter an obstacle, reverse for a moment and return True."""
    start = time.time()
    while time.time() < start + delay:
      if (self.robot.sensors['bump-left'] or
          self.robot.sensors['bump-right'] or
          self.robot.sensors['virtual-wall']):
        logging.info('Oof!')
        # We have to be going forward to trip these sensors, so negative
        # velocity has to be correct.
        self.robot.DriveStraight(-pyrobot.VELOCITY_SLOW)
        time.sleep(MOVE_DELAY)
        self.robot.Stop()
        return True

  def Restart(self):
    logging.info('Restarting.')
    self.StartRobot()

  def Undock(self):
    """Backup out of the dock."""
    logging.info('Disengaging from dock.')
    self.power_manager.Stop()
    self.StartRobot()
    self.Left()  # This helps it get out of the dock.
    self.Reverse()
    self.power_manager.Start()

  def Dock(self):
    """Drive the robot into the docking station.

    This is required since the cover-and-dock demo doesn't drive the robot
    fast enough to get into the dock when it has extra gear on it (it weighs
    too much). It would probably work on carpet if it's squishy enough though.

    """
    def FastDock():
      self.robot.Control()
      self.Reverse()
      self.robot.DriveStraight(pyrobot.VELOCITY_MAX)
      start = time.time()
      while (time.time() - start < 10
             and (not self.sensors['bump-left'])
             and (not self.sensors['bump-right'])):
        time.sleep(SENSOR_DELAY)
      self.robot.Stop()
      time.sleep(1)  # Give the sensors some time to update.
      if self.sensors['charging-sources-available']:
        logging.info('Docking succeeded!')
        return True

    def Retry():
      logging.info('Docking failed. Retrying.')
      self.robot.Control()
      [self.Reverse() for i in range(3)]
      direction = 'cw'
      if random.random() > 0.5:
        direction = 'ccw'
      self.robot.TurnInPlace(pyrobot.VELOCITY_SLOW, direction)
      time.sleep(random.uniform(0.5, 2))
      self.robot.Dock()

    logging.info('Docking.')
    self.robot.Dock()
    start = time.time()
    while time.time() - start < DOCKING_TIME_LIMIT:
      opcode = self.sensors['remote-opcode']
      if opcode == 'red-buoy-and-green-buoy-and-force-field':
        while True:
          if (self.sensors['cliff-left-signal'] < 1200 or
              self.sensors['cliff-right-signal'] < 1200):
            if FastDock():
              return
            else:
              Retry()
              break
          time.sleep(SENSOR_DELAY)
      time.sleep(SENSOR_DELAY)
    self.robot.Control()
    self.robot.Stop()
    logging.info('Docking timed out.')


class FidoService(object):

  """A FidoService runs in a separate thread and can be started and stopped."""

  def __init__(self, fido):
    self.name = self.__class__.__name__
    self.fido = fido
    self._join = False
    self._thread = None

  def Loop(self):
    """Should be overridden by subclass to define a single loop iteration."""
    raise NotImplementedError

  def _Loop(self):
    """Loop until asked to stop."""
    while not self._join:
      try:
        self.Loop()
      except:
        logging.info('Exception in service %s.' % self.name)
        raise

  def Start(self):
    """Start up the service."""
    if self._thread is not None:
      logging.info('Restarting service %s.' % self.name)
      self.Stop()
    else:
      logging.info('Starting service %s.' % self.name)
    self._thread = threading.Thread(target=self._Loop)
    self._thread.setDaemon(True)
    self._thread.start()

  def Stop(self):
    """Stop the service."""
    self._join = True
    if self._thread is not None:
      self._thread.join()
      self._thread = None
    self._join = False

  def Delay(self, seconds):
    """Sleep while still checking if Stop was called."""
    start = time.time()
    while time.time() - start < seconds and not self._join:
      time.sleep(0.01)


class FidoPowerManager(FidoService):

  """Connects the OLPC power when charging sources are available."""

  def Loop(self):
    """Connect the OLPC power to the robot if a charging source is available."""
    if 'charging-sources-available' not in self.fido.sensors:
      logging.info('Invalid sensor data.')
    elif self.fido.sensors['charging-sources-available']:
      logging.info('Charging source available.')
      if self.fido.sensors['charging-state'] == 'not-charging':
        self.fido.robot.SoftReset()  # Robot won't charge until we reset it.
      self.fido.arduino.PowerOlpc(True)
    else:
      # No charging sources available.
      self.fido.arduino.PowerOlpc(False)
    self.Delay(POWER_MANAGER_DELAY)


class FidoSensors(FidoService):

  """Periodically updates sensor data from the OLPC and the robot."""

  def __init__(self, fido):
    super(FidoSensors, self).__init__(fido)
    self.data = {}

  def Loop(self):
    """Get sensor data from robot and OLPC."""
    self.fido.olpc.sensors.GetAll()
    try:
      self.fido.robot.sensors.GetAll()
    except pyrobot.PyRobotError, e:
      logging.warn(e)
    else:
      self.data.update(self.fido.robot.sensors.data)
      self.data.update(self.fido.olpc.sensors.data)
    self.Delay(SENSOR_DELAY)

  def __getitem__(self, name):
    return self.data[name]

  def __contains__(self, name):
    return name in self.data
