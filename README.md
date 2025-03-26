# mtp

Accessing the filesystem of MTP devices (Smartphones, MP3-Player, etc.) on Windows or Linux with python.

Attention: This a actual a beta-version for the KDE support!

In the mtp directory there are three modules.
- win_access.py
- linux_access.py
- dialog.py

For detailed description see site directory

Tested with:
* Python 3.12 and above
* comptypes 1.4.10
* Windows 10 / 11
* Linux Mint, Zorin, Debian 12 with KDE


## win_access.py
This module implements the access to the Windows WPD functions to read and write MTP devices like smartphones, tablets. etc.

## linux_access.py
This module implements the access to read and write MTP devices like smartphones, tablets. etc. from Linux.
Only GNOME based systems are supported due to kio-fuse on KDE doesn't support the mtp protocol and the Python bindings for KIO don't exist yet.

## dialog.py
dialog.py implements a directory searcher in tkinter that shows the attached MTP devices and the directories on them.


# Changelog
* 2.0.0
    * Removed PortableDevice.get_description
      Use PortableDevice.name, PortableDevice.description
    * removed PortableDeviceContent.upload_stream and .download_stream
      Please use .upload and .download
    * get_properties now returns the modification time and not creation time
    * Corrected calculation of filetime in win_access
    * Added support for KDE (see README)
* 1.3.0
    * Eleminated the need for a programm restart after first use of the comtypes library and modifying the generated wpd access files.
      This requires that you use comtypes 1.4.10 or newer.
    * Updated documentation
* 1.2.0
    * Access MTP devices from Linux
* 1.0.2
    * Fixed a bug when an MTP device doesn't have a userfriendly name
* 1.0.1
    * Fixed crash when during walk a directory is deleted.
    * Fixed full_filename for files was not set.

