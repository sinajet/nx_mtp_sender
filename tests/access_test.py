"""
Test program
"""

import locale
import os
import platform
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

if platform.system() == "Windows":
    import mtp.win_access as mtp_access   # pylint: disable=unused-import,wrong-import-position
else:
    import mtp.linux_access as mtp_access   # pylint: disable=unused-import,wrong-import-position


# ----------------------------------------------------------------------
if __name__ == "__main__":

    def display_childs_with_walk(dev: mtp_access.PortableDevice, root: str) -> None:
        """Show content of device"""
        for root, dirs, files in mtp_access.walk(dev, root):  # type: ignore
            for directory in dirs:
                print(f"dir: {directory.full_filename}")
            for file in files:
                print(f"file: {file.full_filename}")

    def display_child(dev: mtp_access.PortableDevice, root: str) -> None:
        """Show child content"""
        if cont := mtp_access.get_content_from_device_path(dev, root):  # type: ignore
            for child in cont.get_children():
                (
                    _,
                    contenttype,
                    size,
                    date_created,
                    capacity,
                    free,
                    _,
                ) = child.get_properties()
                fullpath = child.full_filename
                typ = "?"
                if contenttype == mtp_access.WPD_CONTENT_TYPE_STORAGE:
                    typ = "S"
                elif contenttype == mtp_access.WPD_CONTENT_TYPE_DIRECTORY:
                    typ = "D"
                elif contenttype == mtp_access.WPD_CONTENT_TYPE_FILE:
                    typ = " "
                print(f"{typ}  {fullpath} Size: {size} Created: {date_created} ", end="")
                if typ == "S":
                    print(f"  Capacity: {capacity}  Free: {free}", end="")
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
        starttime = time.time()
        print("Devices:")
        devicelist = mtp_access.get_portable_devices()
        for _ in range(1_000):
            # time.sleep(0.01)
            for dev in devicelist:
                device_name, device_desc = dev.get_description()
                print(f"  {device_name}: {device_desc}")
                for cont in dev.get_content():
                    values = cont.get_properties()
                    print(f"  Serial-No.: {values[6]}")
                    print("Content:")
                    display_childs_with_walk(dev, device_name)
                    display_child(dev, device_name)
        print(f"Runtime: {time.time() - starttime}")

    main()
