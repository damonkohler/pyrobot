In order to support the QuickCam Orbit, UVC must be installed on the OLPC. I have compiled a version for kernel 2.6.22-20071105.1.olpc.c97f1348f3114fa that's available in the downloads section.

# Quick Start #

```
user@host$ scp uvcvideo.ko root@olpc:~root
user@host$ ssh root@olpc
root@olpc$ cp uvcvideo.ko /lib/modules/`uname -r`/kernel/drivers/usb/class
root@olpc$ depmod && modprobe uvcvideo
```

# Compiling #

To compile the module, I extracted the kernel-devel package, then pointed the Makefile toward the extracted source.

```
$ wget http://dev.laptop.org/~dilinger/stable/kernel-devel-`uname -r`.i586.rpm
```