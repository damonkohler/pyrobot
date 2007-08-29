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

GST_PIPE = ['v4l2src', 'ffmpegcolorspace', 'pngenc']


class Camera(object):

  """A class representing the OLPC camera."""
  
  def __init__(self, snap_path):
    self.snap_path = snap_path
    temp_file, self._temp_path = tempfile.mkstemp()
    pipe = GST_PIPE + ['filesink location=%s' % self._temp_path]
    self.pipe = gst.parse_launch('!'.join(pipe))
    self.bus = self.pipe.get_bus()

  def Snap(self):
    """Take a snapshot."""
    self.pipe.set_state(gst.STATE_PLAYING)
    for unused in range(25):
      if self.bus.poll(gst.MESSAGE_EOS, 250000000):  # Timeout is in nanosecs.
        shutil.copyfile(self._temp_path, self.snap_path)
        return
      time.sleep(0.25)

  def StartWebcam(self, delay=1):
    """Starts a thread to take snapshots every 'delay' seconds."""
    webcam = threading.Thread(target=self._Webcam, args=(delay,))
    webcam.setDaemon(True)
    webcam.start()

  def _Webcam(self, delay):
    """Takes a snapshot every 'delay' seconds."""
    while True:
      self.Snap()
      time.sleep(delay)


if __name__ == '__main__':
  c = Camera('snap.png')
  c.Snap()
