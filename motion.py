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

"""Wrapper for Motion's HTTP control interface.

http://www.lavrsen.dk/twiki/bin/view/Motion/WebHome

"""
__author__ = "damonkohler@gmail.com (Damon Kohler)"

import urllib2
import logging
import os
import subprocess
import signal
import time

MOTION_DIR = '/root/motion/'


class MotionController(object):

  def __init__(self, host, port, thread=0):
    self.host = host
    self.port = port
    self.thread = thread
    self._process = None
    # HACK(damonkohler): Install uvcvideo module.
    os.system('modprobe uvcvideo')

  @property
  def control_url(self):
    return 'http://%s:%s/%d/' % (self.host, self.port, self.thread)

  def Track(self, x, y):
    """Track the camera to absolute position x, y."""
    url = self.control_url + 'track/set?x=%s&y=%s' % (x[0], y[0])
    try:
      urllib2.urlopen(url).read()
    except urllib2.URLError:
      self.Restart()
      self.Track(x, y)

  def Set(self, name, value):
    """Set a config value."""
    logging.info('Setting motion config %s to %s.' % (name, value))
    url = self.control_url + 'config/set?%s=%s' % (name, value)
    urllib2.urlopen(url).read()

  def Write(self):
    """Write settings to config file."""
    logging.info('Writing motion config file.')
    urllib2.urlopen(self.control_url + 'config/writeyes').read()

  def Kill(self):
    """Kill motion process."""
    logging.info('Killing motion.')
    os.kill(self._process.pid, signal.SIGTERM)
    while self._process.poll() is None:
      time.sleep(0.25)
    logging.info('Motion killed.')

  def Start(self):
    """Start motion process."""
    logging.info('Starting motion.')
    if self._process is not None and self._process.poll() is None:
      self.Kill()
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = '/lib:' + MOTION_DIR
    self._process = subprocess.Popen([MOTION_DIR + 'motion'],
        cwd=MOTION_DIR, env=env, shell=True)
    # HACK(damonkohler): Give motion some time to start its httpd servers.
    time.sleep(2)

  def Restart(self):
    """Restart motion."""
    # HACK(damonkohler): This doesn't seem to work. So instead, we kill the
    # process and restart it.
    #urllib2.urlopen(self.control_url + 'action/restart').read()
    self.Kill()
    self.Start()
