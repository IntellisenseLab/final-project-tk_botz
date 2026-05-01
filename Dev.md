## Keeping the repo shared between RaspberryPi and Local

```
sshfs user@remote_host:/path/to/remote/folder /path/to/local/mountpoint
```

## To have permanant USB ports for kobuki and lidar

run a,
```bash
lsusb
```

Then get the device ID of required device.

add a udev rule like,
```bash
sudo nano /etc/udev/rules.d/99-kobuki.rules
```
with following content,
```bash
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6014", SYMLINK+="kobuki", MODE="0666"
```

then reload,
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```