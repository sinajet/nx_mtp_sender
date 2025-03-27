"""
Test program
"""

import locale
import os
import platform
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if platform.system() == "Windows":
    import mtp.win_access as mtp_access  # pylint: disable=unused-import,wrong-import-position
    on_windows = True
# elif not os.path.exists(f"/run/user/{os.getuid()}/gvfs"):
# import mtp.libmtp_access as mtp_access
else:
    import mtp.linux_access as mtp_access  # pylint: disable=unused-import,wrong-import-position
    on_windows = False


TESTNUMBER = 6 # 1 - 6
TESTRUNS = 3

def display_childs_with_walk(dev: mtp_access.PortableDevice, root: str) -> int:
    """Show content of device"""
    count = 0
    for root, dirs, files in mtp_access.walk(dev, root):  # type: ignore
        for directory in dirs:
            count += 1
            # print(f"dir: {directory.full_filename}")
        for file in files:
            count += 1
            # print(f"file: {file.full_filename}")
    return count

def display_child(dev: mtp_access.PortableDevice, root: str) -> None:
    """Show child content"""
    if cont := mtp_access.get_content_from_device_path(dev, root):  # type: ignore
        for child in cont.get_children():
            (_, contenttype, size, date_created, _) = child.get_properties()
            fullpath = child.full_filename
            typ = "?"
            if contenttype == mtp_access.WPD_CONTENT_TYPE_STORAGE:
                typ = "S"
            elif contenttype == mtp_access.WPD_CONTENT_TYPE_DIRECTORY:
                typ = "D"
            elif contenttype == mtp_access.WPD_CONTENT_TYPE_FILE:
                typ = " "
            print(f"{typ}  {fullpath} Size: {size} Created: {date_created} ", end="")
            print()
            if contenttype in (
                mtp_access.WPD_CONTENT_TYPE_STORAGE,
                mtp_access.WPD_CONTENT_TYPE_DIRECTORY,
            ):
                display_child(dev, fullpath)
    else:
        print(f"{root} not found")


def main() -> None:
    """Hauptprogramm"""
    locale.setlocale(locale.LC_ALL, "")
    if TESTNUMBER == 1:
        # Test connection and disconnection to device
        for i in range(TESTRUNS):
            print(f"Find devices on test run {i+1}:")
            for dev in mtp_access.get_portable_devices():
                print(
                    f"Found device: Name: {dev.name}: Desc.: {dev.description}: Serialnr.: {dev.serialnumber}"
                )
                dev.close()
    elif TESTNUMBER == 2:
        # Test list storages of device
        for dev in mtp_access.get_portable_devices():
            for i in range(TESTRUNS):
                for storage in dev.get_content():
                    print(f"Found Storage: {storage.name}")
            dev.close()
    elif TESTNUMBER == 3:
        # Test display all childs with walk
        for dev in mtp_access.get_portable_devices():
            for i in range(TESTRUNS):
                for storage in dev.get_content():
                    print(f"Walk Storage: {storage.full_filename}")
                    count = display_childs_with_walk(dev, storage.full_filename)
                    print(f'   Found {count} entries on that storage.')
            dev.close()
    elif TESTNUMBER == 4:
        # Test get cont from a path
        for dev in mtp_access.get_portable_devices():
            for i in range(TESTRUNS):
                cont = mtp_access.get_content_from_device_path(dev, f"{dev.devicename}/SD-Karte/Musik/zz_Sonstiges/Diverses/ZARAH LEANDER/ZARAH LEANDER UND DIE MOONLIGHTS - WUNDERLAND BEI NACHT     1960.mp3")  # type: ignore
                print(f'Content found: {cont}')
    elif TESTNUMBER == 5:
        # Create / Delete Folder
        for dev in mtp_access.get_portable_devices():
            for i in range(TESTRUNS):
                new_path = os.path.join(dev.get_content()[0].full_filename, 'Füchtenhans/temp')
                cont = mtp_access.makedirs(dev, new_path) # type: ignore
                print(f'Content created: {cont}')
                if cont is not None:
                    cont.remove()
                    print(f'   Content (temp) removed')
            dev.close()
    elif TESTNUMBER == 6:
        # Create / Delete files
        uploadfilename = '/home/heribert/Musik/Yanni/The Very Best of Yanni/01 Aria.mp3'
        if not os.path.exists(uploadfilename):
            uploadfilename =  r'C:\Windows\WindowsUpdate.log' if on_windows else '/usr/bin/python3'
        outfilename = r'C:\temp\test.mp3' if on_windows else '/home/heribert/tmp/test.mp3'
        os.makedirs(os.path.dirname(outfilename), exist_ok=True)
        for dev in mtp_access.get_portable_devices():
            print(f'Device: {dev.devicename}')
            for i in range(TESTRUNS):
                new_path = os.path.join(dev.get_content()[0].full_filename, 'Füchtenhans/temp')
                cont = mtp_access.makedirs(dev, new_path) # type: ignore
                fcont = cont.get_child("test.mp3")
                if fcont is not None:
                    fcont.remove()
                print(f'Uploading file, test nr {i}')
                cont.upload_file('test.mp3', uploadfilename)
                fcont = cont.get_child("test.mp3")
                if fcont is None:
                    print(f'Could not create file test.mp3')
                    continue
                if os.path.exists(outfilename):
                    os.remove(outfilename)
                print('Downloading file')
                fcont.download_file(outfilename)
                if not os.path.exists(outfilename):
                    print(f'Could not download file test.mp3')
                    continue
                if os.path.getsize(uploadfilename) != os.path.getsize(outfilename):
                    print(f'Filesizes of uploaded and download file are different.')
            dev.close()

# ----------------------------------------------------------------------
if __name__ == "__main__":
    main()
