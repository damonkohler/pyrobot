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


class Camera(object):

  """A class representing the OLPC camera."""

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
      self.bus.poll(-1, -1)
      time.sleep(0.25)
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
