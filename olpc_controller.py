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


class OlpcController(object):

  def __init__(self):
    self.sensors = OlpcSensors()

  def SetDconSleep(self, sleep):
    if sleep:
      logging.info('Putting DCON to sleep.')
      open('/sys/devices/platform/dcon/sleep', 'w').write('1')
    else:
      logging.info('Waking up DCON.')
      open('/sys/devices/platform/dcon/sleep', 'w').write('0')

  def ConfigureAudio(self):
    logging.info('Configuring audio.')
    # HACK(damonkohler): Install oss pcm sound module for flite.
    os.system('modprobe snd-pcm-oss')
    # NOTE(damonkohler): The following settings were borrowed and modified
    # from the measure activity.
    # Playback settings.
    os.system("amixer set 'Master' unmute 85%")  # Used to be 25%.
    os.system("amixer set 'Master Mono' unmute 25%")
    os.system("amixer set 'PCM' unmute 85%")  # Used to be 50%.
    os.system("amixer set 'Mic' mute 5%")  # Used to be 'unmute'.
    os.system("amixer set 'Mic Boost (+20dB)' unmute")
    #os.system("amixer set 'Analog Input' mute")  # Not found.
    os.system("amixer set 'V_REFOUT Enable' unmute")
    # Capture settings. Used to be 'unmute'.
    os.system("amixer set 'Mic' 5%, 75% mute captur")
    os.system("amixer set 'Capture' 75%, 75% mute captur")

  def StreamAudio(self, host, port):
    self.audio_stream = AudioStream(host, port)
    self.audio_stream.Start()

  def Speak(self, msg):
    """Use flite to perform text to speech operations."""
    logging.info('Speaking %r.' % msg)
    cmd = "/home/olpc/flite -t %r" % msg
    logging.debug('Executing %r.' % cmd)
    os.system(cmd)


class OlpcSensors(object):

  """Access sysfs information about the OLPC's power."""

  def __init__(self):
    self.data = {}

  def GetCapacity(self):
    return int(open('/sys/class/power_supply/olpc-battery/capacity').read())

  def GetCapacityLevel(self):
    return open('/sys/class/power_supply/olpc-battery/capacity_level').read()

  def GetCurrentAvg(self):
    return int(open('/sys/class/power_supply/olpc-battery/current_avg').read())

  def GetVoltageAvg(self):
    return int(open('/sys/class/power_supply/olpc-battery/voltage_avg').read())

  def GetHealth(self):
    return open('/sys/class/power_supply/olpc-battery/health').read()


  def GetTemp(self):
    return int(open('/sys/class/power_supply/olpc-battery/temp').read())

  def GetTempAmbient(self):
    return int(open('/sys/class/power_supply/olpc-battery/temp_ambient').read())

  def GetStatus(self):
    return open('/sys/class/power_supply/olpc-battery/status').read()

  def GetAll(self):
    """Update data dict with all sensor data."""
    self.data['olpc_capacity'] = self.GetCapacity()
    self.data['olpc_capacity_level'] = self.GetCapacityLevel()
    self.data['olpc_current_avg'] = self.GetCurrentAvg()
    self.data['olpc_voltage_avg'] = self.GetVoltageAvg()
    self.data['olpc_health'] = self.GetHealth()
    self.data['olpc_temp'] = self.GetTemp()
    self.data['olpc_temp_ambient'] = self.GetTempAmbient()
    self.data['olpc_status'] = self.GetStatus()


class AudioStream(object):

  """Stream audio from the OLPC microphone to an Icecast server."""

  def __init__(self, host, port, password):
    self.pipe = self._GetAudioPipe(host, port, password)

  def _GetAudioPipe(self, host, port, password):
    pipe = gst.Pipeline('olpc-audio')
    caps = gst.Caps('audio/x-raw-int,rate=8000,channels=1,depth=8')
    elems = []

    def Add(name, properties=None):
      elem = gst.element_factory_make(name, name)
      properties = properties or {}
      for property, value in properties.iteritems():
        elem.set_property(property, value)
      pipe.add(elem)
      elems.append(elem)

    Add('alsasrc')
    Add('capsfilter', {'caps': caps})
    Add('audioconvert')
    Add('vorbisenc')
    Add('shout2send', {'ip': host, 'port': port, 'password': password,
                       'mount': '/olpc.ogg'})

    gst.element_link_many(*elems)
    return pipe

  def Start(self):
    self.pipe.set_state(gst.STATE_PLAYING)

  def Stop(self):
    self.pipe.set_state(gst.STATE_NULL)


class Video(object):

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
