
```markdown
# MTP Device File Manager

![MTP Logo](https://img.icons8.com/color/96/000000/usb.png)

A Python command-line utility for managing files on MTP devices (Switch, Android,, etc.) via Windows.

## Features

- 📋 List connected MTP devices
- 📁 Copy files/folders to MTP devices
- ❓ Check if path exists on device
- 🗑️ Delete files/folders from device
- 📏 Get size of files/folders on device
- ⚙️ Simple CLI for automation and scripting

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/mtp-file-manager.git
cd mtp-file-manager
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

> **Note**: Requires Windows with [Windows Portable Devices API](https://learn.microsoft.com/en-us/windows/win32/mtp/mtp-porting-kit)

## Usage

### List connected devices
```bash
python mtp_manager.py list-devices
```
Example output:
```
This PC\ Switch\SD Card |  Switch
This PC\Galaxy S23\Internal storage | Galaxy S23
```

### Copy file/folder to device
```bash
python mtp_manager.py copy "local_file.txt" "This PC\My Device\Internal storage\Documents"
```

### Check if path exists
```bash
python mtp_manager.py exists "This PC\ Switch\SD Card\atmosphere\config"
```
Returns `True` or `False` with exit code 0/1

### Delete file/folder
```bash
python mtp_manager.py delete "This PC\My Device\Internal storage\old_file.txt"
```

### Get item size (bytes)
```bash
python mtp_manager.py size "This PC\My Device\Internal storage\large_folder"
```

## Compatibility

| Device/Software       | Status     | Notes                          |
|-----------------------|------------|--------------------------------|
| 🎮 Switch    | ✅ Tested  | Works with Atmosphere-NX USB File Transfer and DBI Installer |
| 🤖 Android Devices    | ✅ Tested  | Most modern Android devices    |
| ⚠️ Hekate SD Card     | ❌ Unsupported | SD card mount/unmount in hekate |

## Known Limitations

- Windows-only (due to WPD API dependency)
- Large file transfers may be slower than dedicated tools
- Recursive operations on large directories may take time

## Acknowledgments

This project uses components from the [win_mtp](https://github.com/Heribert17/win_mtp) project.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## License

MIT License - see [LICENSE](LICENSE) file for details.
