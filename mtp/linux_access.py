"""
A module to access Mobile Devices from UNIX via USB connection.
After connecting to gnome desktop the devices can be found under:
/run/user/1000/gvfs/
in the normal file system. If on an other desktop environment. for example KDE
then any process that uses libmtp will be killed and this module will access
libmtp.

Author:  Heribert Füchtenhans

Version: 2025.3.26

For examples please look into the tests directory.

Requirements:
OS:
    Linux

The module contains the following functions:

- 'get_portable_devices' Get all attached portable devices.
- 'get_content_from_device_path' - Get the content of a path.
- 'walk' - Iterates ower all files in a tree.
- 'makedirs' - Creates the directories on the MTP device if they don't exist.

The module contains the following classes:

- 'PortableDeviceContent' - Class for one file, directory or storage
    Public methods:
        get_properties
        get_children
        get_child
        get_path
        create_content
        upload_file
        download_file
        remove

    Public attributes:
        name: Name on the MTP device
        fullname: The full path name
        date_modified: The file date
        size: The size of the file in bytes
        content_type: Type of the entry. One of the WPD_CONTENT_TYPE_ constants

    Exceptions:
        IOError: If something went wrong


- 'PortableDevice' - Class for one portable device found connected
    Public methods:
        get_description
        get_content

    Public attributes:


All functions through IOError when a communication fails.

Examples:
    >>> import mtp.linux_access
    >>> mtp.linux_access.get_portable_devices()
    [<PortableDevice: ('HSG1316', 'HSG1316')>]

Information to the filenames used in MTP:
- The filename consists of the following part:
    devicename/storagename/foldername/....
- The devicename can be found in PortableDevice.devicename
- The storagename is in content returned by PortableDevice.get_content
    It's the the name attribute
- Every PortableDeviceContent has an attribute 'full_filename' that contains the whole
    path of that content
"""

# pylint: disable=global-statement

import ctypes
import datetime
import os
import shutil
import subprocess
from typing import IO, Generator, List, Optional, Tuple, Callable


import mtp.pylibmtp as pylibmtp


# Constants for the type entries returned bei PortableDeviceContent.get_properties
WPD_CONTENT_TYPE_UNDEFINED = -1
WPD_CONTENT_TYPE_STORAGE = 0
WPD_CONTENT_TYPE_DIRECTORY = 1
WPD_CONTENT_TYPE_FILE = 2
WPD_CONTENT_TYPE_DEVICE = 3

# Constants for delete
WPD_DELETE_NO_RECURSION = 0
WPD_DELETE_WITH_RECURSION = 1

_libmtp: pylibmtp.MTP | None = None
_gvfs_found = True
_gvfs_search_path = f"/run/user/{os.getuid()}/gvfs"  # path for gvfs miunted devices


# -------------------------------------------------------------------------------------------------
# Internal functions


def _init_libmtp() -> None:
    """Kills all prgs that use libmtp and connect to libmtp.
    The killed programm will be restarted when needed (tested with Gnome)"""
    global _libmtp, _gvfs_found
    _gvfs_found = False
    if _libmtp is not None:
        return
    # Kill any process that uses libmtp
    # Getting MTP devices from lsusb
    p = subprocess.Popen("lsusb", stdout=subprocess.PIPE, shell=True)
    (output, err) = p.communicate()
    if p.wait() != 0:
        raise IOError("Can't get output from lsusb!")
    for o in output.decode("ascii").split("\n"):
        if o.upper().endswith("(MTP MODE)"):
            bus = o[4:7]
            dev = o[15:18]
            # Get programm that uses libmtp return pid
            p = subprocess.Popen(
                f"fuser -k /dev/bus/usb/{bus}/{dev}", stdout=subprocess.PIPE, shell=True
            )
            (output, _) = p.communicate()
            if p.wait() != 0:
                if len(output) != 0:
                    raise IOError(f'Can\'t get programs that use libmtp: {output.decode("utf-8")}')
                else:
                    # No prg using ist
                    continue
    _libmtp = pylibmtp.MTP()


# -------------------------------------------------------------------------------------------------
class PortableDevice:
    """Class with the infos for a connected portable device.
    The instanzes of this class will be created internaly. User should not instanciate them manually
    until you know what you do.

    Public methods:
        close: Must be called when the device is no more needed. This frees the resources
        get_content: Get the content (Storages) of the device

    Public attributes:
        name: Name of the MTP device
        description: Description for the device
        serialnumber: Serialnumber of the device
        devicename: The full name of the device. Use it when building pathes

    Exceptions:
        IOError: If something went wrong
    """

    def __init__(self, device: "str | ctypes._Pointer[pylibmtp.LIBMTP_RawDevice]") -> None:
        """Init the class.

        Args:
            path_to_device: Linux path to the device
        """
        self.description = "Unknown"
        self.name = "Unknown"
        self.serialnumber = "Unknown"
        if type(device) == str:
            self._device = device
            if '=' in device:
                self._device_start_part, self.devicename = device.split("=", 1)
                self._device_start_part += '='
            else:
                self._device_start_part = ''
                self.devicename = device
            if "_" in self.devicename:
                parts = self.devicename.split("_")
                try:
                    self.name = parts[0]
                    self.description = parts[1]
                    self.serialnumber = parts[2]
                except IndexError:
                    pass
        else:
            # We do the killing of the processes that use libmtp just bevor
            # we use libmtp because so the chances that any other programm
            # greps libmtp back is very small
            if _libmtp is None:
                _init_libmtp()
            self._libmntp_device = pylibmtp.MTP(device)
            self._libmntp_device.connect()
            self.name = self._libmntp_device.get_devicename()
            self.description = self._libmntp_device.get_modelname()
            if self.name == "":
                self.name = self.description
            self.serialnumber = self._libmntp_device.get_serialnumber()
            self.devicename = f"{self.name}_{self.description}_{self.serialnumber}"

    def close(self) -> None:
        """To be compatible with libmtp. For gvfs not supported"""
        if not _gvfs_found:
            self._libmntp_device.disconnect()

    def get_content(self) -> List["PortableDeviceContent"]:
        """Get the content of a device. The storages

        Returns:
            A list of instances of PortableDeviceContent, one for each storage

        Examples:
            >>> import mtp.linux_access
            >>> dev = mtp.linux_access.get_portable_devices()
            >>> str(dev[0].get_content())[:33]
            '<PortableDeviceContent c_wchar_p('
        """
        ret_objs: list["PortableDeviceContent"] = []
        try:
            if _gvfs_found:
                for entry in os.listdir(os.path.join(_gvfs_search_path, self._device)):
                    full_name = os.path.join(self.devicename, entry)
                    ret_objs.append(
                        PortableDeviceContent(self, full_name, 0, 0, WPD_CONTENT_TYPE_STORAGE)
                    )
            else:
                if self._libmntp_device is None:
                    raise IOError("Device not initialised. Call get_portable_devices first.")
                for entry in self._libmntp_device.get_storage():
                    full_name = os.path.join(self.devicename, entry[0])
                    pdc = PortableDeviceContent(
                        self, full_name, entry[1], pylibmtp.LIBMTP_FILES_AND_FOLDERS_ROOT, WPD_CONTENT_TYPE_STORAGE
                    )
                    ret_objs.append(pdc)
        except OSError as err:
            raise IOError(f"Can't access {self.devicename}.") from err
        ret_objs.sort(key=lambda entry: entry.name)
        return ret_objs

    def __repr__(self) -> str:
        return f"<PortableDevice: {self.description}>"


# -------------------------------------------------------------------------------------------------
class PortableDeviceContent:  # pylint: disable=too-many-instance-attributes
    """Class for one file, directory or storage with it's properties.
    This class is only internaly created, use it only to read the properties

    Args:
        port_device: Portable device instance.
        dirpath: Path to the directory or file
        typ: WPD_CONTENT_TYPE_FILE for files or WPD_CONTENT_TYPE_DEVICE

    Public methods:
        get_properties
        get_children
        get_child
        get_path
        create_content
        upload_file
        download_file
        remove

    Public attributes:
        name: Name on the MTP device
        fullname: The full path name
        date_modified: The file date
        size: The size of the file in bytes
        content_type: Type of the entry. One of the WPD_CONTENT_TYPE_ constants

    Exceptions:
        IOError: If something went wrong
    """

    def __init__(
        self, port_device: PortableDevice, dirpath: str, storage_id: int, entry_id: int, typ: int,
        size: int = 0, date_modified:int = 0
    ) -> None:
        """ """

        self._port_device = port_device
        self.full_filename = dirpath
        self.name = os.path.basename(dirpath)
        self.storage_id = storage_id
        self.entry_id = entry_id
        self.content_type = typ
        self.size = -1
        self.date_modified = datetime.datetime.now()
        if typ == WPD_CONTENT_TYPE_FILE:
            if _gvfs_found:
                try:
                    full_filename = os.path.join(_gvfs_search_path, port_device._device_start_part + dirpath)
                    self.size = os.path.getsize(full_filename)
                    self.date_modified = datetime.datetime.fromtimestamp(os.path.getmtime(full_filename))
                except OSError:
                    self.content_type = WPD_CONTENT_TYPE_STORAGE
            else:
                self.size = size
                self.date_modified = datetime.datetime.fromtimestamp(date_modified)
        elif typ == WPD_CONTENT_TYPE_DEVICE:
            self.full_filename = port_device.devicename

    def get_properties(
        self,
    ) -> Tuple[str, int, int, datetime.datetime, str]:
        """Get the properties of this content.

        Returns:
            name: The name for this content, normaly the file or directory name
            content_type: One of the content type values that descripe the type of the content
                        WPD_CONTENT_TYPE_UNDEFINED, WPD_CONTENT_TYPE_STORAGE,
                        WPD_CONTENT_TYPE_DIRECTORY, WPD_CONTENT_TYPE_FILE, WPD_CONTENT_TYPE_DEVICE
            size: The size of the file or 0 if content ist not a file
            date_modified: The reation date of the file or directory
            serialnumber: The serial number of the device, only valid if content_type is
                        WPD_CONTENT_TYPE_DEVICE

        Examples:
            >>> import mtp.linux_access
            >>> dev = mtp.linux_access.get_portable_devices()
            >>> cont = dev[0].get_content()
            >>> cont[0].get_properties()
            ('HSG1316', 0, -1, datetime.datetime(1970, 1, 1, 0, 0), -1, -1, 'DQVSSCM799999999')
        """
        return (
            self.name,
            self.content_type,
            self.size,
            self.date_modified,
            self._port_device.serialnumber,
        )

    def get_children(self) -> Generator["PortableDeviceContent", None, None]:
        """Get the child items of a folder.

        Returns:
            A Generator of PortableDeviceContent instances each representing a child entry.

        Examples:
            >>> import mtp.linux_access
            >>> dev = mtp.linux_access.get_portable_devices()
            >>> cont = dev[0].get_content()
            >>> str(cont[0].get_children()[0])[:58]
            "<PortableDeviceContent s10001: ('Interner Speicher', 0, -1"
        """
        if _gvfs_found:
            full_filename = os.path.join(_gvfs_search_path, self._port_device._device_start_part + self.full_filename )
            if not os.path.isdir(full_filename):
                return
            for entry in os.listdir(full_filename):
                full_name = os.path.join(self.full_filename, entry)
                yield PortableDeviceContent(
                    self._port_device,
                    full_name,
                    1,
                    0,
                    (
                        WPD_CONTENT_TYPE_DIRECTORY
                        if os.path.isdir(os.path.join(full_filename, entry))
                        else WPD_CONTENT_TYPE_FILE
                    ),
                )
        else:
            if _libmtp is None:
                return
            for entry in self._port_device._libmntp_device.get_files_and_folder(self.storage_id, self.entry_id):
                yield PortableDeviceContent(
                    self._port_device,
                    os.path.join(self.full_filename, entry.filename.decode("utf-8")),
                    self.storage_id,
                    entry.item_id,
                    (
                        WPD_CONTENT_TYPE_DIRECTORY
                        if entry.filetype == 0 # pylibmtp.LIBMTP_Filetype["FOLDER"].value
                        else WPD_CONTENT_TYPE_FILE
                    ),
                    entry.filesize,
                    entry.modificationdate
                )

    def get_child(self, name: str) -> "PortableDeviceContent | None":
        """Returns a PortableDeviceContent for one child whos name is known.
        The search is case sensitive.

        Args:
            name: The name of the file or directory to search

        Returns:
            The PortableDeviceContent instance of the child or None if the child could not be
            found.

        Examples:
            >>> import mtp.linux_access
            >>> dev = mtp.linux_access.get_portable_devices()
            >>> cont = dev[0].get_content()
            >>> str(cont[0].get_child("Interner Speicher"))[:58]
            "<PortableDeviceContent s10001: ('Interner Speicher', 0, -1"
        """
        if _gvfs_found:
            fullname = os.path.join(_gvfs_search_path, self._port_device._device_start_part + self.full_filename, name)
            if not os.path.exists(fullname):
                return None
            return PortableDeviceContent(
                self._port_device,
                os.path.join(self.full_filename, name),
                1,
                1,
                (WPD_CONTENT_TYPE_DIRECTORY if os.path.isdir(fullname) else WPD_CONTENT_TYPE_FILE),
            )
        else:
            if _libmtp is None:
                return
            for entry in self._port_device._libmntp_device.get_files_and_folder(self.storage_id, self.entry_id):
                entry_filename = entry.filename.decode("UTF-8")
                if entry_filename != name:
                    continue
                # Ok found, so do a direct return
                return PortableDeviceContent(
                    self._port_device,
                    os.path.join(self.full_filename, entry_filename),
                    self.storage_id,
                    entry.item_id,
                    (
                        WPD_CONTENT_TYPE_DIRECTORY
                        if entry.filetype == pylibmtp.LIBMTP_Filetype["FOLDER"]
                        else WPD_CONTENT_TYPE_FILE
                    ),
                    entry.filesize,
                    entry.modificationdate
                )
            return None

    def get_path(self, name: str) -> Optional["PortableDeviceContent"]:
        """Returns a PortableDeviceContent for a child who's path in the tree is known

        Args:
            name: The pathname to the child. Each path entry must be separated by the
                    os.path.sep character.

        Returns:
            The PortableDeviceContent instance of the child or None if the child could not be
            found.

        Examples:
            >>> import mtp.linux_access
            >>> dev = mtp.linux_access.get_portable_devices()
            >>> cont = dev[0].get_content()
            >>> str(cont[0].get_path("Interner Speicher\\Android\\data"))[:41]
            "<PortableDeviceContent oE: ('data', 1, -1"
        """
        if _gvfs_found:
            full_filename = os.path.join(_gvfs_search_path, self._port_device._device_start_part + name)
            if not os.path.exists(full_filename):
                return None
            return PortableDeviceContent(
                self._port_device,
                name,
                1,
                1,
                (WPD_CONTENT_TYPE_DIRECTORY if os.path.isdir(full_filename) else WPD_CONTENT_TYPE_FILE),
            )
        else:
            cur: Optional["PortableDeviceContent"] = self
            for part in name.split(os.path.sep):
                if not cur:
                    return None
                cur = cur.get_child(part)
            return cur

    def __repr__(self) -> str:
        """ """
        return f"<PortableDeviceContent {self.full_filename}: {self.get_properties()}>"

    def create_content(self, dirname: str) -> 'PortableDeviceContent':
        """Creates an empty directory content in this content.

        Args:
            dirname: Name of the directory that shall be created

        Return:
            PortableDeviceContent for the new directory

        Examples:
            >>> import mtp.linux_access
            >>> dev = mtp.linux_access.get_portable_devices()
            >>> cont = dev[0].get_content()
            >>> mycont = cont[0].get_path("Interner Speicher\\Music\\MyMusic")
            >>> if mycont: _ = mycont.remove()
            >>> cont = cont[0].get_path("Interner Speicher\\Music")
            >>> cont.create_content("MyMusic")
        """
        fullname = os.path.join(self.full_filename, dirname)
        if _gvfs_found:
            full_filename = os.path.join(_gvfs_search_path, self._port_device._device_start_part + fullname)
            if os.path.exists(full_filename):
                raise IOError(f"Directory '{fullname}' allready exists")
            os.mkdir(full_filename)
            pdc = PortableDeviceContent(self._port_device, fullname, 0, 0, WPD_CONTENT_TYPE_DIRECTORY)
        else:
            try:
                id = self._port_device._libmntp_device.create_folder(dirname, self.entry_id, self.storage_id)
                pdc = PortableDeviceContent(self._port_device, fullname, self.storage_id, id, WPD_CONTENT_TYPE_DIRECTORY)
            except Exception:
                raise IOError(f"Error creating directory '{fullname}'")
        return pdc


    def upload_file(self, filename: str, inputfilename: str) -> None:
        """Upload of a file to MTP device.

        Args:
            filename: Name of the new file on the MTP device
            inputfilename: Name of the file that shall be uploaded

        Examples:
            >>> import mtp.linux_access
            >>> dev = mtp.linux_access.get_portable_devices()
            >>> cont = dev[0].get_content()
            >>> mycont = cont[0].get_path("Interner Speicher\\Music\\Test.mp3")
            >>> if mycont: _ = mycont.remove()
            >>> cont = cont[0].get_path("Interner Speicher\\Music")
            >>> name = '..\\..\\Tests\\OnFire.mp3'
            >>> cont.upload_file("Test.mp3", name)
        """
        if _gvfs_found:
            full_filename = os.path.join(_gvfs_search_path, self._port_device._device_start_part + self.full_filename, filename)
            shutil.copyfile(inputfilename, full_filename)
        else:
            self._port_device._libmntp_device.send_file_from_file(inputfilename, filename, self.storage_id, self.entry_id, None)


    def download_file(self, outputfilename: str) -> None:
        """Download of a file from MTP device
        The used ProtableDeviceContent instance must be a file!

        Args:
            outputfilename: Name of the file the MTP file shall be written to. Any existing
                            content will be replaced.

        Examples:
            >>> import mtp.linux_access
            >>> dev = mtp.linux_access.get_portable_devices()
            >>> cont = dev[0].get_content()
            >>> cont = cont[0].get_path("Interner Speicher\\Ringtones\\hangouts_incoming_call.ogg")
            >>> name = '..\\..\\Tests\\hangouts_incoming_call.ogg'
            >>> cont.download_file(name)
        """
        if _gvfs_found:
            full_filename = os.path.join(_gvfs_search_path, self._port_device._device_start_part + self.full_filename)
            shutil.copy2(full_filename, outputfilename)
        else:
            self._port_device._libmntp_device.get_file_to_file(self.entry_id, outputfilename)

    def remove(self) -> None:
        """Deletes the current directory or file.

        Return:
            0 on OK, else a windows errorcode

        Examples:
            >>> import mtp.linux_access
            >>> dev = mtp.linux_access.get_portable_devices()
            >>> cont = dev[0].get_content()
            >>> mycont = cont[0].get_path("Interner Speicher\\Music\\Test.mp3")
            >>> if mycont: _ = mycont.remove()
            >>> cont = cont[0].get_path("Interner Speicher\\Music")
            >>> name = '..\\..\\Tests\\OnFire.mp3'
            >>> cont.upload_file("Test.mp3", name)
            >>> cont = dev[0].get_content()
            >>> mycont = cont[0].get_path("Interner Speicher\\Music\\Test.mp3")
            >>> mycont.remove()
            0
        """
        if _gvfs_found:
            full_name = os.path.join(_gvfs_search_path, self._port_device._device_start_part + self.full_filename)
            if not os.path.exists(full_name):
                return
            if self.content_type == WPD_CONTENT_TYPE_FILE:
                os.remove(full_name)
            else:
                shutil.rmtree(full_name)
        else:
            self._port_device._libmntp_device.delete_object(self.entry_id)


# -------------------------------------------------------------------------------------------------
# Globale functions


def get_portable_devices() -> list[PortableDevice]:
    """Get all attached portable devices.

    Returns:
        A list of PortableDevice one for each found MTP device. The list is empty if no device
            was found.

    Exceptions:
        IOError: If something went wrong

    Examples:
        >>> import mtp.linux_access
        >>> mtp.linux_access.get_portable_devices()
        [<PortableDevice: ('HSG1316', 'HSG1316')>]
    """
    global _gvfs_found
    devices: List[PortableDevice] = []
    if not os.path.exists(_gvfs_search_path):
        # We assume, we are not on a GNOME system with installed gvfs
        # So we try to use libmtp
        if _libmtp is None:
            _init_libmtp()
        for entry in _libmtp.detect_devices(): # type: ignore
            dev = PortableDevice(entry)
            # Device is not ready if we don't get a content
            if len(dev.get_content()) != 0:
                devices.append(dev)
    else:
        _gvfs_found = True
        for entry in os.scandir(_gvfs_search_path):
            dev = PortableDevice(entry.name)
            # Device is not ready if we don't get a content
            if len(dev.get_content()) != 0:
                devices.append(dev)
    return devices


def get_content_from_device_path(dev: PortableDevice, fpath: str) -> PortableDeviceContent | None:
    """Get the content of a path.

    Args:
        dev: The instance of PortableDevice where the path is searched
        fpath: The pathname of the file or directory

    Returns:
        An instance of PortableDeviceContent if the path is an existing file or directory
            else None is returned.

    Exceptions:
        IOError: If something went wrong

    Examples:
        >>> import mtp.linux_access
        >>> dev = mtp.linux_access.get_portable_devices()
        >>> n = "HSG1316\\Interner Speicher\\Ringtones"
        >>> w =mtp.linux_access.get_content_from_device_path(dev[0], n)
        >>> str(w)[:46]
        "<PortableDeviceContent o3: ('Ringtones', 1, -1"
    """
    fpath = fpath.replace("\\", os.path.sep).replace("/", os.path.sep)
    if fpath == dev.devicename:
        raise IOError("get_content_from_device_path needs a devicename and a storage as paramter")
    if _gvfs_found:
        full_fpath = os.path.join(_gvfs_search_path, dev._device_start_part + fpath)
        if os.path.isdir(full_fpath):
            content_type = WPD_CONTENT_TYPE_DIRECTORY
        else:
            content_type = WPD_CONTENT_TYPE_FILE
        return PortableDeviceContent(
            dev,
            fpath,
            1,
            1,
            content_type,
        )
    else:
        parts = fpath.split(os.sep)
        storname_to_search = os.path.join(parts[0], parts[1])
        found_stor = None
        for stor in dev.get_content():
            if stor.full_filename == storname_to_search:
                found_stor = stor
                break
        if found_stor is None:
            raise IOError(f"The storage {storname_to_search} could not be found")
        cont = found_stor
        for pp in parts[2:]:
            cont = cont.get_child(pp)
            if cont is None:
                return None
        return cont


def walk(
    dev: PortableDevice,
    path: str,
    callback: Optional[Callable[[str], bool]] = None,
    error_callback: Optional[Callable[[str], bool]] = None,
) -> Generator[
    tuple[str, list[PortableDeviceContent], list[PortableDeviceContent]],
    None,
    None,
]:
    """Iterates ower all files in a tree just like os.walk

    Args:
        dev: Portable device to iterate in
        path: path from witch to iterate
        callback: when given, a function that takes one argument (the selected file) and returns
                a boolean. If the returned value is false, walk will cancel and return empty
                list.
                the callback is usefull to show for example a progress because reading thousands
                of file from one MTP directory lasts very long.
        error_callback: when given, a function that takes one argument (the errormessage) and returns
                a boolean. If the returned value is false, walk will cancel and return empty
                list.

    Returns:
        A tuple with this content:
            A string with the root directory
            A list of PortableDeviceContent for the directories  in the directory
            A list of PortableDeviceContent for the files in the directory

    Exceptions:
        IOError: If something went wrong

    Examples:
        >>> import mtp.linux_access
        >>> dev = mtp.linux_access.get_portable_devices()
        >>> n = "HSG1316\\Interner Speicher\\Ringtones"
        >>> for r, d, f in mtp.linux_access.walk(dev[0], n):
        ...     for f1 in f:
        ...             print(f1.name)
        ...
        hangouts_message.ogg
        hangouts_incoming_call.ogg
    """
    path = path.replace("\\", os.path.sep).replace("/", os.path.sep)
    if (cont := get_content_from_device_path(dev, path)) is None:
        return
    walk_cont: list[PortableDeviceContent] = [cont]
    while walk_cont:
        cont = walk_cont[0]
        del walk_cont[0]
        directories: list[PortableDeviceContent] = []
        files: list[PortableDeviceContent] = []
        try:
            for child in cont.get_children():
                contenttype = child.content_type
                if contenttype in [
                    WPD_CONTENT_TYPE_STORAGE,
                    WPD_CONTENT_TYPE_DIRECTORY,
                ]:
                    directories.append(child)
                elif contenttype == WPD_CONTENT_TYPE_FILE:
                    files.append(child)
                if callback and not callback(child.full_filename):
                    directories = []
                    files = []
                    return
            directories.sort(key=lambda ent: ent.full_filename)
            files.sort(key=lambda ent: ent.full_filename)
            yield cont.full_filename, directories, files
        except Exception as err:
            if error_callback is not None:
                if not error_callback(str(err)):
                    directories = []
                    files = []
                    return
            raise IOError from err
        walk_cont.extend(directories)


def makedirs(dev: PortableDevice, path: str) -> PortableDeviceContent:
    """Creates the directories in path on the MTP device if they don't exist.

    Args:
        dev: Portable device to create the dirs on
        path: pathname of the dir to create. Any directories in path that don't exist
            will be created automatically.
    Exceptions:
        IOError: If something went wrong

    Examples:
        >>> import mtp.linux_access
        >>> dev = mtp.linux_access.get_portable_devices()
        >>> n = "HSG1316\\Interner Speicher\\Music\\MyMusic\\Test1"
        >>> str(mtp.linux_access.makedirs(dev[0], n))[:22]
        '<PortableDeviceContent'
    """
    path = path.replace("\\", os.path.sep).replace("/", os.path.sep)
    if _gvfs_found:
        try:
            fullpath = os.path.join(_gvfs_search_path, dev._device_start_part + path)
            if not os.path.exists(fullpath):
                os.makedirs(fullpath, exist_ok=True)
            cont = get_content_from_device_path(dev, path)
        except (IOError, IndexError) as err:
            raise IOError(f"Error creating directory '{path}': {err.args[1]}") from err
        if cont is None:
            raise IOError(f"Error creating directory '{path}'")
    else:
        found_stor = None
        parts = path.split(os.sep)
        if len(parts) <= 2:
            raise IOError(f"Devicename and or storage are missing in  {path}")
        storname_to_search = os.path.join(parts[0], parts[1])
        for stor in dev.get_content():
            if stor.full_filename == storname_to_search:
                found_stor = stor
                break
        if found_stor is None:
            raise IOError(f"The storage {storname_to_search} could not be found")
        cont = found_stor
        for pp in parts[2:]:
            par_cont = cont
            cont = cont.get_child(pp)
            if cont is None:
                cont = par_cont.create_content(pp)
            if cont is None:
                raise IOError(f"Error creating directory '{path}'")
    return cont
