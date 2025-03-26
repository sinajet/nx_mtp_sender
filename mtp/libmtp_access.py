"""
A module to access Mobile Devices from UNIX via USB connection.
The module uses libmtp.
Attention: if kio uses libmtp, this wound work yet

Author:  Heribert Füchtenhans
Version: 2025.3.14

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
        get_properties        return None
    except IOError as err:
        raise IOError(f"Error reading directory '{path}': {err.args[1]}")

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
        date_created: The file date
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
"""

# pylint: disable=global-statement

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


# -------------------------------------------------------------------------------------------------

def _init_libmtp() -> None:
    """Kills all prgs that use libmtp and connect to libmtp.
    The killed programm will be restarted when needed (tested with Gnome)"""
    global _libmtp
    if _libmtp is not None:
        return
    # Kill any process that uses libmtp
    # Getting MTP devices from lsusb
    p = subprocess.Popen("lsusb", stdout=subprocess.PIPE, shell=True)
    (output, err) = p.communicate()
    if p.wait() != 0:
        raise IOError("Can't get output from lsusb!")
    for o in output.decode("ascii").split('\n'):
        if o.upper().endswith('(MTP MODE)'):
            bus = o[4:7]
            dev = o[15:18]
            # Get programm that uses  libmtp return pid
            p = subprocess.Popen(f'fuser -k /dev/bus/usb/{bus}/{dev}', stdout=subprocess.PIPE, shell=True)
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
        get_description
        get_content

    Public attributes:
        serialnumber

    Exceptions:
        IOError: If something went wrong
    """

    def __init__(self, raw_device) -> None:
        """Init the class.

        Args:
            path_to_device: Linux path to the device
        """
        if _libmtp is None:
            return
        self._device = pylibmtp.MTP(raw_device)
        self._device.connect()
        self._name = self._device.get_devicename()
        self._desc = self._device.get_modelname()
        if self._name == "":
            self._name = self._desc
        self.serialnumber = self._device.get_serialnumber()

    def close(self) -> None:
        """Closes the connection to libmtp"""
        self._device.disconnect()

    def get_description(self) -> Tuple[str, str]:
        """Get the name and the description of the device. If no description is available
        name and description will be identical.

        Returns:
            A tuple with of name, description. Both are "" if no device was found

        Examples:
            >>> import mtp.linux_access
            >>> dev = mtp.linux_access.get_portable_devices()
            >>> dev[0].get_description()
            ('Nokia 6', 'Nokia 6')
        """
        return (self._name, self._desc)

    def get_device_path(self) -> pylibmtp.MTP:
        """Returns the device"""
        return self._device

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
        if self._device is None:
            raise IOError("Device not initialised. Call get_devices first.")
        ret_objs: list["PortableDeviceContent"] = []
        try:
            for entry in self._device.get_storage():
                full_name = os.path.join(self._name, entry[0])
                ret_objs.append(
                    PortableDeviceContent(self, full_name, entry[1], WPD_CONTENT_TYPE_STORAGE)
                )
            ret_objs.sort(key=lambda entry: entry.name)
        except OSError as err:
            raise IOError(f"Can't access storages of {self._name}.") from err
        return ret_objs

    # def get_PDC_for_path(self, path: str) -> PortableDeviceContent:
    #     """Returns the PDC for the given path.
    #     Exception: IOError"""
    #     path = path.replace("\\", os.path.sep).replace("/", os.path.sep)
    #     parts = path.split(os.path.sep)
    #     if parts[0] != dev.get_description()[0]:
    #         raise IOError(f"The path '{path}' is not for this device '{self._name}'")
    #     try:
    #         act_pdc = PortableDeviceContent(dev, path, -1, WPD_CONTENT_TYPE_DEVICE)
    #         for pp in parts[1:]:
    #             if act_pdc.content_type == WPD_CONTENT_TYPE_DEVICE:
    #                 new_ct = WPD_CONTENT_TYPE_STORAGE
    #             else:
    #                 new_ct = WPD_CONTENT_TYPE_DIRECTORY
    #             act_pdc = PortableDeviceContent(dev, act_pdc.full_filename, act_pdc._id, new_ct)
    #         return act_pdc
    #     except IOError as err:
    #         raise IOError(f"Error reading directory '{path}': {err.args[1]}")

    def __repr__(self) -> str:
        return f"<PortableDevice: {self.get_description()}>"


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
        date_created: The file date
        size: The size of the file in bytes
        content_type: Type of the entry. One of the WPD_CONTENT_TYPE_ constants

    Exceptions:
        comtypes.COMError: If something went wrong
    """

    def __init__(self, port_device: PortableDevice, direntry: str, mtp_id: int, typ: int) -> None:
        """ """

        self._port_device = port_device
        self.full_filename = direntry
        self._id = mtp_id
        self.name = os.path.basename(self.full_filename)
        self.content_type = typ
        self.size = -1
        self.date_created = datetime.datetime.now()
        # if typ == WPD_CONTENT_TYPE_FILE:
        #     try:
        #         self.size = os.path.getsize(direntry)
        #         self.date_created = datetime.datetime.fromtimestamp(os.path.getmtime(direntry))
        #     except OSError:
        #         self.content_type = WPD_CONTENT_TYPE_STORAGE
        # elif typ == WPD_CONTENT_TYPE_DEVICE:
        #     self.full_filename = port_device.get_device_path()

    def get_properties(
        self,
    ) -> Tuple[str, int, int, datetime.datetime, int, int, str]:
        """Get the properties of this content.

        Returns:
            name: The name for this content, normaly the file or directory name
            content_type: One of the content type values that descripe the type of the content
                        WPD_CONTENT_TYPE_UNDEFINED, WPD_CONTENT_TYPE_STORAGE,
                        WPD_CONTENT_TYPE_DIRECTORY, WPD_CONTENT_TYPE_FILE, WPD_CONTENT_TYPE_DEVICE
            size: The size of the file or 0 if content ist not a file
            date_created: The reation date of the file or directory
            capacity: The capacity of the storage, only valid if content_type is
                        WPD_CONTENT_TYPE_STORAGE
            free_capacity: The free capacity of the storage, only valid if content_type is
                        WPD_CONTENT_TYPE_STORAGE
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
            self.date_created,
            -1,
            -1,
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
        if not os.path.isdir(self.full_filename):
            return
        for entry in os.listdir(self.full_filename):
            full_name = os.path.join(self.full_filename, entry)
            yield PortableDeviceContent(
                self._port_device,
                full_name,
                4711,   # give id of dir/file
                (WPD_CONTENT_TYPE_DIRECTORY if os.path.isdir(full_name) else WPD_CONTENT_TYPE_FILE),
            )

    def get_child(self, name: str) -> Optional["PortableDeviceContent"]:
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
        fullname = os.path.join(self.full_filename, name)
        if not os.path.exists(fullname):
            return None
        return PortableDeviceContent(
            self._port_device,
            fullname,
            4711, # Give id of dir/file
            (WPD_CONTENT_TYPE_DIRECTORY if os.path.isdir(fullname) else WPD_CONTENT_TYPE_FILE),
        )

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
            >>> dev = mtp.linux_access.get_portaLIBMTP_Get_Folder_Listpeicher\\Android\\data"))[:41]
            "<PortableDeviceContent oE: ('data', 1, -1"
        """
        if not os.path.exists(name):
            return None
        return PortableDeviceContent(
            self._port_device,
            name,
            4711, # Give id of dir/file
            (WPD_CONTENT_TYPE_DIRECTORY if os.path.isdir(name) else WPD_CONTENT_TYPE_FILE),
        )

    def __repr__(self) -> str:
        """ """
        return f"<PortableDeviceContent {self.full_filename}: {self.get_properties()}>"

    def create_content(self, dirname: str) -> None:
        """Creates an empty directory content in this content.

        Args:
            dirname: Name of the directory that shall be created

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
        if os.path.exists(fullname):
            raise IOError(f"Directory '{fullname}' allready exists")
        os.mkdir(fullname)

    def upload_stream(self, filename: str, inputstream: IO[bytes], _: int) -> None:
        """Upload a steam to a file on the MTP device.
        For an easier usage use upload_file

        Args:
            filename: Name of the new file on the MTP device
            inputstream: open python file

        Examples:
            >>> import mtp.linux_access
            >>> dev = mtp.linux_access.get_portable_devices()
            >>> cont = dev[0].get_content()
            >>> mycont = cont[0].get_path("Interner Speicher\\Music\\Test.mp3")
            >>> if mycont: _ = mycont.remove()
            >>> cont = cont[0].get_path("Interner Speicher\\Music")
            >>> name = '..\\..\\Tests\\OnFire.mp3'
            >>> size = os.path.getsize(name)
            >>> inp = open(name, "rb")
            >>> cont.upload_stream("Test.mp3", inp, size)
            >>> inp.close()
        """
        with open(filename, "rb") as outp:
            shutil.copyfileobj(inputstream, outp)

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
        shutil.copy2(inputfilename, filename)

    def download_stream(self, outputstream: IO[bytes]) -> None:
        """Download a file from MTP device.
        The used ProtableDeviceContent instance must be a file!
        For easier usage use download_file

        Args:
            outputstream: Open python file for writing

        Examples:
            >>> import mtp.linux_access
            >>> dev = mtp.linux_access.get_portable_devices()
            >>> cont = dev[0].get_content()
            >>> cont = cont[0].get_path("Interner Speicher\\Ringtones\\hangouts_incoming_call.ogg")
            >>> name = '..\\..\\Tests\\hangouts_incoming_call.ogg'
            >>> outp = open(name, "wb")
            >>> cont.download_stream(outp)
            >>> outp.close()
        """
        with open(self.full_filename, "rb") as inp:
            shutil.copyfileobj(inp, outputstream)

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
        shutil.copy2(self.full_filename, outputfilename)

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
        if self.content_type == WPD_CONTENT_TYPE_FILE:
            os.remove(self.full_filename)
        else:
            shutil.rmtree(self.full_filename)


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
    global _libmtp
    _init_libmtp()
    if _libmtp is None:
        raise IOError("libmtp not initialised. Call get_devoces first.")
    devices: List[PortableDevice] = []
    for entry in _libmtp.detect_devices():
        dev = PortableDevice(entry)
        # Device is not ready if we don't get a content
        if len(dev.get_content()) != 0:
            devices.append(dev)
    return devices


def get_content_from_device_path(dev: PortableDevice, path: str) -> PortableDeviceContent | None:
    """Get the content of a path.

    Args:
        dev: The instance of PortableDevice where the path is searched
        path: The pathname of the file or directory

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
    # return dev.get_PDC_for_path(path)


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
    if not (cont := get_content_from_device_path(dev, path)):
        return
    cont.full_filename = path
    walk_cont: list[PortableDeviceContent] = [cont]
    while walk_cont:
        cont = walk_cont[0]
        del walk_cont[0]
        directories: list[PortableDeviceContent] = []
        files: list[PortableDeviceContent] = []
        try:
            for child in cont.get_children():
                (_, contenttype, _, _, _, _, _) = child.get_properties()
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
            yield cont.full_filename, sorted(directories, key=lambda ent: ent.full_filename), sorted(
                files, key=lambda ent: ent.full_filename
            )
        except Exception as err:
            if error_callback is not None:
                if not error_callback(str(err)):
                    directories = []
                    files = []
                    return
        walk_cont.extend(directories)


def makedirs(dev: PortableDevice, path: str) -> PortableDeviceContent:
    """Creates the directories in path on the MTP device if they don't exist.

    Args:
        dev: Portable device to create the dirs on
        path: pathname of the dir to create. Any directoriues in path that don't exist
            will e created automatically.
    Exceptions:
        IOError: If something went wrongmtp = pylibmtp.MTP()

        >>> str(mtp.linux_access.makedirs(dev[0], n))[:22]
        '<PortableDeviceContent'
    """
    dev_name, _ = dev.get_description()
    path = path.replace(dev_name, dev.get_device_path().get_devicename(), 1)

    try:
        os.makedirs(path, exist_ok=True)
        return PortableDeviceContent(dev, path, 0, WPD_CONTENT_TYPE_DIRECTORY)
    except IOError as err:
        raise IOError(f"Error creating directory '{path}': {err.args[1]}") from err


# ----------------------------------------------------------------------
if __name__ == "__main__":
    devicelist = get_portable_devices()
    for dev in devicelist:
        device_name, device_desc = dev.get_description()
        print(f"Device:  {device_name}: {device_desc}")
        print(f"  Serial-No.: {dev.serialnumber}")
        for cont in dev.get_content():
            values = cont.get_properties()
            print(f'Storage: {values[0]}')
            for root, dirs, files in walk(dev, device_name):
                # for directory in dirs:
                #     print(f"dir: {directory.full_filename}")
                for file in files:
                    print(f"file: {file.full_filename}")
