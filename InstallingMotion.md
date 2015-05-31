Since yum is intolerably slow on the OLPC and I haven't been able to find a good repository for packages, I hacked up a tarball for [Motion](http://www.lavrsen.dk/twiki/bin/view/Motion/WebHome) from the apt package on my Ubuntu Gusty box. It's available in the downloads section.

# Steps to build tarball #

  1. Install the latest stable version of [Motion](http://www.lavrsen.dk/twiki/bin/view/Motion/WebHome).
  1. Create a directory to store the tarball (i.e. `mkdir ~/motion`)
  1. Copy the libraries listed by `/lib/ld-linux.so.2 --list $(which motion)` into `~/motion`.
  1. Use the `go` script in the motion tarball to start up motion with the correct `LD_LIBRARY_PATH`.

# Quirks/Ugliness #

~~I haven't been able to prevent motion from generating movies when it detects motion. Since space is at a bit of a premium on the OLPC, I set up a crontab to delete `/tmp/motion` every 10 minutes (`*/10 * * * * rm -rf /tmp/motion`).~~

The [Motion wiki](http://www.lavrsen.dk/twiki/bin/view/Motion/FrequentlyAskedQuestions#How_do_I_disable_or_enable_makin) explains how to disable generating movie files when motion is detected.

Also, I haven't been able to make permission changes to `/dev/video*` devices permanent even with changes to `/etc/udev/rules.d/*`. So, I run Motion as root.