# zfs_helper
Python ZFS menu driven config util

## Installation
ZFS helper requires `urwid` framework. I wrote it with 2.1.0 but it may also work on earlier versions.
```
python3 -m pip install urwid
```
On debian based distros package will need `zfsutils-linux, debootstrap, gdisk, zfs-initramfs`. Good news it will check and install everyithing itself.
RedHat... It's work in progress.

## Usage
```
sudo python3 zfs_helper.py
```
