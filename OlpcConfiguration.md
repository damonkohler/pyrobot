These are the steps I've taken to configure the OLPC for Fido development.

# OLPC Builds #

See [how to update](http://wiki.laptop.org/go/Autoreinstallation_image) on http://wiki.laptop.org.

My OLPC is a B2-7 which falls under the classification of a B2-1 system. So, it's recommended that I use the 406.15 build. However, I've had reasonable success with build 623. I am using the later builds because they contain drivers for the Arduino USB-to-serial chipset.

It's important to pick a stable build as opposed to a development build if you want to build kernel modules. The kernel-devel packages for the various stable builds are available here: http://dev.laptop.org/~dilinger/stable/

I was unable to find the devel package for the kernel used in build 623, so I [installed](http://wiki.laptop.org/go/Kernel) kernel-2.6.22-20071105.1.olpc.c97f1348f3114fa and then used its kernel-devel counterpart to compile the UvcModule.


# Disable Sugar in /etc/inittab #

Sugar consumes a lot of resources. Since Fido doesn't need it, it's convenient to change the default run level in /etc/inittab to 3 instead of 5.


# Networking #

I have been unable to get NetworkManager to work successfully. I recommend disabling NetworkManger and enabling the standard network script:

```
root$ cd /etc/rc3.d
root$ mv S98NetworkManager K98NetworkManager
root$ mv K90network S90network
```

Next, configure wireless to connect to your network:

```
root$ vi /etc/sysconfig/network-scripts/ifcfg-eth0
```

Make the following changes and additions:

```
ONBOOT=yes
TYPE=Wireless
ESSID="your_ssid"
KEY="your_wep_key"
```

Then test it:

```
root$ /etc/init.d/NetworkManager stop
root$ ifup eth0
root$ ifconfig
```

You might also want to reboot and make sure your network starts up automatically.

I've found that the network connection can die on occasion and will not come back automatically. So, I also have a script in my root crontab that runs every 10 minutes to keep the network connection alive.

```
#!/bin/bash

ping -c 1 -w 1 router && exit 0

ifdown eth0
ifup eth0
```


# SSH #

First give root and olpc a password from the developer console.

```
root$ passwd
root$ passwd olpc
```

Now you should be able to SSH. It's also nice to distribute SSH keys to avoid having to type your password:

```
root$ mkdir ~root/.ssh
root$ mkdir ~olpc/.ssh
root$ cat ~root/id_rsa.pub >> ~root/.ssh/authorized_keys
root$ cat ~root/id_rsa.pub >> ~olpc/.ssh/authorized_keys
```