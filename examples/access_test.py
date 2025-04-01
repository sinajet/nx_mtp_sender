"""
Test the functions in mtp and also serve as example for usage.
Be aware that there is no error handling in these examples. Error handling
should be used for production code
"""

import os
import platform
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if platform.system() == "Windows":
    import mtp.win_access as mtp_access  # pylint: disable=unused-import,wrong-import-position

    on_windows = True
else:
    import mtp.linux_access as mtp_access  # pylint: disable=unused-import,wrong-import-position

    on_windows = False


TESTNUMBER = 7  # 1 - 7
TESTRUNS = 1


def test_connect_disconnct() -> None:
    """Test connection and disconnection to device"""
    for i in range(TESTRUNS):
        print(f"Find devices on test run {i+1}:")
        for dev in mtp_access.get_portable_devices():
            print(
                f"Found device: Name: {dev.name}: Desc.: {dev.description}: Serialnr.: {dev.serialnumber}"
            )
            dev.close()


def test_list_storages() -> None:
    """Test list storages of device"""
    for dev in mtp_access.get_portable_devices():
        for i in range(TESTRUNS):
            for storage in dev.get_content():
                print(f"Found Storage: {storage.full_filename}")
        dev.close()


def test_list_childs_with_walk() -> None:
    """Test get all childs with walk"""

    def error_function(error: str) -> bool:
        """Error function"""
        print(f"Error: {error}")
        return True

    for dev in mtp_access.get_portable_devices():
        for i in range(TESTRUNS):
            for storage in dev.get_content():
                print(f"Walk Storage: {storage.full_filename}")
                count = 0
                for root, dirs, files in mtp_access.walk(dev, storage.full_filename, None, error_function):  # type: ignore
                    for directory in dirs:
                        count += 1
                        # print(f"dir: {directory.full_filename}")
                    for file in files:
                        count += 1
                        # print(f"file: {file.full_filename}")
                print(f"   Found {count} entries on that storage.")
        dev.close()


def test_get_cont_from_path() -> None:
    """Test get cont from a path"""
    for dev in mtp_access.get_portable_devices():
        for i in range(TESTRUNS):
            cont = mtp_access.get_content_from_device_path(dev, f"{dev.devicename}/Interner gemeinsamer Speicher/Android/data/com.google.android.apps.maps/cache/diskcache")  # type: ignore
            print(f"Content found: {cont}")
        dev.close()


def test_create_delete_folder() -> None:
    """Create / Delete Folder"""
    for dev in mtp_access.get_portable_devices():
        for i in range(TESTRUNS):
            new_path = os.path.join(dev.get_content()[0].full_filename, "example/temp")
            cont = mtp_access.makedirs(dev, new_path)  # type: ignore
            print(f"Content created: {cont}")
            if cont is not None:
                cont.remove()
                print(f"   Content (temp) removed")
        dev.close()


def test_create_delete_file() -> None:
    """Create / Delete files"""
    mtp_filename = "music.mp3"
    uploadfilename = os.path.join(os.path.dirname(__file__), "music.mp3")
    downloadfilename = os.path.join(os.path.dirname(__file__), "test.mp3")
    for dev in mtp_access.get_portable_devices():
        print(f"Device: {dev.devicename}")
        for i in range(TESTRUNS):
            # Create the directory for the new file
            new_path = os.path.join(dev.get_content()[0].full_filename, "example/temp")
            cont = mtp_access.makedirs(dev, new_path)  # type: ignore
            # Delete the file if it exists
            fcont = cont.get_child(mtp_filename)
            if fcont is not None:
                fcont.remove()
            # Upload the file to the mtp device
            print(f"Uploading file, test nr {i}")
            cont.upload_file(mtp_filename, uploadfilename)
            # Test if it exists on the MTP device
            fcont = cont.get_child(mtp_filename)
            if fcont is None:
                print(f"Could not create file {mtp_filename}")
                continue
            # Download the file. If the file in download folder exists, delete it first
            if os.path.exists(downloadfilename):
                os.remove(downloadfilename)
            print("Downloading file")
            fcont.download_file(downloadfilename)
            # Test if download was successfull and file sizes are the same
            if not os.path.exists(downloadfilename):
                print(f"Could not download file test.mp3")
                continue
            if os.path.getsize(uploadfilename) != os.path.getsize(downloadfilename):
                print(f"Filesizes of uploaded and download file are different.")
            os.remove(downloadfilename)
        dev.close()


def test_display_childs() -> None:
    """test to show all cont, but doesn't use walk.
    For walking through the content of a directory tree use walk, it's much faster"""

    def show_childs(dev: mtp_access.PortableDevice, root: str) -> None:
        """Show all cont, but don't use walk"""
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
                    typ = "F"
                print(f"{typ}  {fullpath} Size: {size} Created: {date_created} ")
                if contenttype in (
                    mtp_access.WPD_CONTENT_TYPE_STORAGE,
                    mtp_access.WPD_CONTENT_TYPE_DIRECTORY,
                ):
                    show_childs(dev, fullpath)
        else:
            print(f"{root} not found")

    for dev in mtp_access.get_portable_devices():
        for storage in dev.get_content():
            print(f"Storage: {storage.full_filename}")
            show_childs(dev, storage.full_filename)
            break
        print("Closing device")
        dev.close()


def main() -> None:
    """Hauptprogramm"""
    if TESTNUMBER == 0:  # all test
        test_connect_disconnct()
        test_list_storages()
        test_list_childs_with_walk()
        test_get_cont_from_path()
        test_create_delete_folder()
        test_create_delete_file()
        test_display_childs()
    elif TESTNUMBER == 1:
        test_connect_disconnct()
    elif TESTNUMBER == 2:
        test_list_storages()
    elif TESTNUMBER == 3:
        test_list_childs_with_walk()
    elif TESTNUMBER == 4:
        test_get_cont_from_path()
    elif TESTNUMBER == 5:
        test_create_delete_folder()
    elif TESTNUMBER == 6:
        test_create_delete_file()
    elif TESTNUMBER == 7:
        test_display_childs()


# ----------------------------------------------------------------------
if __name__ == "__main__":
    main()
