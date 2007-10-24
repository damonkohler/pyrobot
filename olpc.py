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

"""One Laptop Per Child (OLPC) specific code.

This module is for use with the OLPC.

"""
__author__ = "damonkohler@gmail.com (Damon Kohler)"

import gst
import shutil
import tempfile
import threading
import time
import traceback
import os
import logging


class PowerManager(object):

  """Access sysfs information about the OLPC's power."""

  def SetDconSleep(self, sleep):
    if sleep:
      logging.debug('Putting DCON to sleep.')
      open('/sys/devices/platform/dcon/sleep', 'w').write('1')
    else:
      logging.debug('Waking up DCON.')
      open('/sys/devices/platform/dcon/sleep', 'w').write('0')

  def GetCapacity(self):
    return open('/sys/class/power_supply/olpc-battery/capacity').read()

  def GetCapacityLevel(self):
    return open('/sys/class/power_supply/olpc-battery/capacity_level').read()

  def GetCurrentAvg(self):
    return open('/sys/class/power_supply/olpc-battery/current_avg').read()

  def GetVoltageAvg(self):
    return open('/sys/class/power_supply/olpc-battery/voltage_avg').read()

  def GetHealth(self):
    return open('/sys/class/power_supply/olpc-battery/health').read()

  def GetTemp(self):
    return open('/sys/class/power_supply/olpc-battery/temp').read()

  def GetTempAmbient(self):
    return open('/sys/class/power_supply/olpc-battery/temp_ambient').read()

  def GetStatus(self):
    return open('/sys/class/power_supply/olpc-battery/status').read()


class Flite(object):

  """Use flite to perform text to speech operations."""

  def Say(self, msg):
    cmd = "/home/olpc/flite -t %r" % msg
    logging.debug('Executing %r.' % cmd)
    os.system(cmd)


class Microphone(object):

  """Interact with the OLPC microphone."""

  def __init__(self, record_path):
    self._record_path = record_path
    unused, self._tmp_path = tempfile.mkstemp(dir='static')
    self.lock = threading.Lock()
    self.pipe = self._GetMicrophonePipe(self._tmp_path)
    self.ConfigureAlsa()
 
  def ConfigureAlsa(self):
    # Playback settings.
    os.system("amixer set 'Master' unmute 25%")
    os.system("amixer set 'Master Mono' unmute 25%")
    os.system("amixer set 'PCM' unmute 50%")
    os.system("amixer set 'Mic' unmute 5%")
    os.system("amixer set 'Mic Boost (+20dB)' unmute")
    os.system("amixer set 'Analog Input' mute")
    os.system("amixer set 'V_REFOUT Enable' unmute")
    # Capture settings.
    os.system("amixer set 'Mic' 5%, 75% unmute captur")
    os.system("amixer set 'Capture' 75%, 75% unmute captur")

  def _GetMicrophonePipe(self, record_path):
    pipe = gst.Pipeline('olpc-microphone')
    elems = []
    
    def Add(name):
      elem = gst.element_factory_make(name, name)
      pipe.add(elem)
      elems.append(elem)

    Add('alsasrc')
    Add('capsfilter')
    Add('queue')
    Add('audioconvert')
    Add('vorbisenc')
    Add('oggmux')
    Add('filesink')

    gst.element_link_many(*elems)
    pipe.get_by_name('filesink').set_property('location', record_path)
    caps = gst.Caps('audio/x-raw-int,rate=8000,channels=1,depth=8')
    pipe.get_by_name('capsfilter').set_property('caps', caps)

    return pipe

  def Record(self, duration=10):
    """Record audio for duration seconds."""
    self.lock.acquire()
    self.pipe.set_state(gst.STATE_PLAYING)
    time.sleep(duration)
    # TODO(damonkohler): This doesn't necessarily always result in a 10 second
    # clip. Need to monitor gst messages to see if it has started.
    self.pipe.set_state(gst.STATE_NULL)
    try:
      shutil.move(self._tmp_path, self._record_path)
    except IOError:
      # NOTE(damonkohler): Ignoring errors for now.
      print 'Failed to move audio recording.'
      traceback.print_exc()
    self.lock.release()

  def StartMicrophone(self, delay=1):
    """Starts a thread to take snapshots every 'delay' seconds."""
    recorder = threading.Thread(target=self._Microphone, args=(delay,))
    recorder.setDaemon(True)
    recorder.start()

  def _Microphone(self, delay):
    """Takes a snapshot at a minimum of every 'delay' seconds."""
    while True:
      self.Record()
      time.sleep(delay)


class Camera(object):

  """Interact with the OLPC camera."""

  def __init__(self, snap_path):
    self._snap_path = snap_path
    unused, self._tmp_path = tempfile.mkstemp(dir='static')
    self.lock = threading.Lock()
    self.pipe = self._GetCameraPipe(self._tmp_path)
    self.bus = self.pipe.get_bus()
    self.bus.add_signal_watch()
    self.bus.connect('message', self._OnGstMessage)

  def _GetCameraPipe(self, snap_path):
    pipe = gst.Pipeline('olpc-camera')
    elems = []
    
    def Add(name):
      elem = gst.element_factory_make(name, name)
      pipe.add(elem)
      elems.append(elem)

    Add('v4l2src')
    Add('ffmpegcolorspace')
    Add('pngenc')
    Add('filesink')

    gst.element_link_many(*elems)
    pipe.get_by_name('filesink').set_property('location', snap_path)

    return pipe

  def Snap(self):
    """Take a snapshot."""
    self.lock.acquire()
    self.pipe.set_state(gst.STATE_PLAYING)
    while not self.lock.acquire(False):
      # TODO(damonkohler): I don't see any other sample code doing this.
      # Instead, they all have a GUI loop of some sort that I think makes
      # everything work. What's the right way to do this?
      self.bus.poll(-1, 1)  # Should be instant if there's anything waiting.
      time.sleep(0.5)
    try:
      shutil.move(self._tmp_path, self._snap_path)
    except IOError:
      # NOTE(damonkohler): Ignoring errors for now.
      print 'Failed to move webcam snapshot.'
      traceback.print_exc()
    self.lock.release()

  def _OnGstMessage(self, bus, message):
    """Called when a GST message is received."""
    t = message.type
    if t == gst.MESSAGE_EOS:
      self.pipe.set_state(gst.STATE_NULL)
      self.lock.release()
    elif t == gst.MESSAGE_ERROR:
      self.pipe.set_state(gst.STATE_NULL)
      self.lock.release()
      # NOTE(damonkohler): Ignoring errors for now.

  def StartWebcam(self, delay=1):
    """Starts a thread to take snapshots every 'delay' seconds."""
    webcam = threading.Thread(target=self._Webcam, args=(delay,))
    webcam.setDaemon(True)
    webcam.start()

  def _Webcam(self, delay):
    """Takes a snapshot at a minimum of every 'delay' seconds."""
    while True:
      self.Snap()
      time.sleep(delay)


if __name__ == '__main__':
  snap_path = 'snap.png'
  c = Camera(snap_path)
  c.Snap()
  print 'Captured snapshot to %s' % snap_path
  record_path = 'record.ogg'
  m = Microphone(record_path)
  m.Record()
  print 'Recorded aduio to %s' % record_path
