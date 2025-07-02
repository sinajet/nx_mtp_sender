import subprocess

class NxMtpHandler:
    def __init__(self, exe_path):
        """
        MTP Operations Handler
        
        Parameters:
            exe_path (str): Full path to nx_mtp_sender.exe
        """
        self.exe_path = exe_path
    
    def _get_device_id(self):
        """Get first device ID from list-devices command"""
        result = subprocess.run(
            [self.exe_path, "list-devices"],
            shell=True,
            capture_output=True,
            text=True
        )
        devices = result.stdout.splitlines()
        if not devices:
            raise Exception("No MTP devices found")
        return devices[0].split(" | ")[0]

    def copy(self, source_path, destination_path):
        """
        Copy file/folder to MTP device
        
        Parameters:
            source_path (str): Full local source path
            destination_path (str): Full device destination path (including device ID)
        """
        device_id = self._get_device_id()
        full_destination = f"{device_id}\\{destination_path}"
        
        result = subprocess.run(
            [self.exe_path, "copy", source_path, full_destination],
            shell=True,
            capture_output=True,
            text=True
        )
        return result.stdout

    def exists(self, device_path):
        """Check if path exists on device"""
        device_id = self._get_device_id()
        full_path = f"{device_id}\\{device_path}"
        
        result = subprocess.run(
            [self.exe_path, "exists", full_path],
            shell=True,
            capture_output=True,
            text=True
        )
        return result.stdout.strip()

    def delete(self, device_path):
        """Delete file/folder from device"""
        device_id = self._get_device_id()
        full_path = f"{device_id}\\{device_path}"
        
        result = subprocess.run(
            [self.exe_path, "delete", full_path],
            shell=True,
            capture_output=True,
            text=True
        )
        return result.stdout

    def size(self, device_path):
        """Get file/folder size on device"""
        device_id = self._get_device_id()
        full_path = f"{device_id}\\{device_path}"
        
        result = subprocess.run(
            [self.exe_path, "size", full_path],
            shell=True,
            capture_output=True,
            text=True
        )
        return result.stdout.strip()


# Usage Example:
handler = NxMtpHandler("d:\\mypro\\switch patch installer\\installer\\nx_mtp_sender.exe")

# Copy file (user provides full paths)
copy_result = handler.copy(
    source_path="D:\\mypro\\switch patch installer\\installer\\-.png",
    destination_path="retroarch\\Roms\\-.png"
)
print(copy_result)

# Check existence
exists_result = handler.exists("retroarch\\Roms\\New folder\\- - Copy (2).png")
print(exists_result)

# Delete folder
delete_result = handler.delete("retroarch\\Roms\\New folder")
print(delete_result)

# Get file size
size_result = handler.size("retroarch\\Roms\\New folder\\- - Copy (2).png")
print(size_result)