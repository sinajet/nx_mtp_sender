#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Project Information:
# https://github.com/Heribert17/win_mtp Used this project
# Tested on: DBI Installer, USB File Transfer by Atmosphere-NX
# Not worked with SD Card mount/unmount in hekate

import sys
import os
import argparse
from pathlib import Path

# Handle module path for different execution contexts
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    base_path = Path(sys.executable).parent
    mtp_module_path = base_path / "mtp"
else:
    # Running as Python script
    base_path = Path(__file__).parent
    mtp_module_path = base_path / "mtp"

# Add to Python path
sys.path.insert(0, str(mtp_module_path))

# Now import MTP module components
from mtp.win_access import (
    get_portable_devices,
    makedirs,
    get_content_from_device_path,
    WPD_CONTENT_TYPE_FILE,
    WPD_CONTENT_TYPE_DIRECTORY,
    WPD_CONTENT_TYPE_STORAGE
)


def get_mtp_devices():
    """
    Get list of connected MTP devices in the format:
    [["This PC\\Device Name", "Device Name"]]
    
    Returns:
        list: List of device paths and names
    """
    mtp_devices = []
    try:
        devices = get_portable_devices()
        for device in devices:
            try:
                device_name = device.name
                device_path = f"This PC\\{device_name}\\{device.get_content()[0].name}"
                mtp_devices.append([device_path, device_name])
            except Exception as e:
                print(f"Error processing device: {e}")
            finally:
                device.close()
    except Exception as e:
        print(f"Error getting MTP devices: {e}")
    return mtp_devices


def copy_to_mtp_device(source_path: str, destination_path: str) -> None:
    """
    Copy file or folder from local system to MTP device
    
    Args:
        source_path: Local file/folder path
        destination_path: MTP destination path in format:
            "This PC\\DeviceName\\Storage\\Path\\To\\Destination"
    """
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source path not found: {source_path}")

    parts = destination_path.split("\\")
    if len(parts) < 3 or parts[0] != "This PC":
        raise ValueError("Invalid destination path format. Should be: 'This PC\\DeviceName\\Storage\\...'")
    
    device_name = parts[1]
    storage_name = parts[2]
    mtp_path = "\\".join(parts[3:])
    
    # Find target device
    device = None
    for dev in get_portable_devices():
        if device_name in dev.devicename:
            device = dev
            break
    
    if not device:
        raise ValueError(f"Device not found: {device_name}")
    
    try:
        # Find storage
        storage = None
        for s in device.get_content():
            if s.name == storage_name:
                storage = s
                break
        
        if not storage:
            raise ValueError(f"Storage not found: {storage_name}")
        
        full_mtp_path = f"{device.devicename}\\{storage_name}\\{mtp_path}"
        
        if os.path.isfile(source_path):
            # File copy
            file_name = os.path.basename(source_path)
            parent_path = os.path.dirname(full_mtp_path)
            parent_content = makedirs(device, parent_path)
            parent_content.upload_file(file_name, source_path)
            print(f"File copied: {source_path} => {destination_path}")
        
        elif os.path.isdir(source_path):
            # Folder copy (recursive)
            dir_name = os.path.basename(source_path)
            target_path = f"{full_mtp_path}\\{dir_name}"
            mtp_dir = makedirs(device, target_path)
            
            for root, dirs, files in os.walk(source_path):
                rel_path = os.path.relpath(root, source_path)
                current_mtp_path = target_path if rel_path == "." else os.path.join(target_path, rel_path)
                
                # Only create directories when needed
                if rel_path != ".":
                    mtp_dir = makedirs(device, current_mtp_path.replace("\\", "/"))
                
                for file in files:
                    local_file = os.path.join(root, file)
                    mtp_dir.upload_file(file, local_file)
                    print(f"Copied: {local_file} => {current_mtp_path}\\{file}")
            
            print(f"Folder copied: {source_path} => {target_path}")
    finally:
        device.close()


def exists_in_mtp_device(mtp_path: str) -> bool:
    """
    Check if path exists on MTP device
    
    Args:
        mtp_path: Full MTP path in format:
            "This PC\\DeviceName\\Storage\\Path\\To\\Item"
    
    Returns:
        bool: True if path exists, False otherwise
    """
    try:
        parts = mtp_path.split("\\")
        if len(parts) < 3 or parts[0] != "This PC":
            raise ValueError("Invalid path format. Should be: 'This PC\\DeviceName\\Storage\\...'")
        
        device_name = parts[1]
        storage_path_1 = "\\".join(parts[2:])
        
        for device in get_portable_devices():
            if device_name in device.devicename:
                storage_path = f"{device.devicename}\\{storage_path_1}"
                content = get_content_from_device_path(device, storage_path)
                device.close()
                return content is not None
        return False
    except Exception as e:
        print(f"Existence check error: {e}")
        return False


def delete_from_mtp_device(mtp_path: str) -> bool:
    """
    Delete file/folder from MTP device
    
    Args:
        mtp_path: Full MTP path in format:
            "This PC\\DeviceName\\Storage\\Path\\To\\Item"
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        parts = mtp_path.split("\\")
        if len(parts) < 3 or parts[0] != "This PC":
            raise ValueError("Invalid path format. Should be: 'This PC\\DeviceName\\Storage\\...'")
        
        device_name = parts[1]
        storage_path_1 = "\\".join(parts[2:])
        
        for device in get_portable_devices():
            if device_name in device.devicename:
                storage_path = f"{device.devicename}\\{storage_path_1}"
                content = get_content_from_device_path(device, storage_path)
                if not content:
                    print(f"Path not found: {mtp_path}")
                    return False
                
                content.remove()
                print(f"Deleted: {mtp_path}")
                return True
        return False
    except Exception as e:
        print(f"Deletion error: {e}")
        return False
    finally:
        device.close()


def get_mtp_folder_size(folder_content) -> int:
    """
    Calculate folder size recursively on MTP device
    
    Args:
        folder_content: PortableDeviceContent object
    
    Returns:
        int: Total size in bytes
    """
    total_size = 0
    stack = [folder_content]
    
    while stack:
        current = stack.pop()
        try:
            for child in current.get_children():
                if child.content_type == WPD_CONTENT_TYPE_FILE:
                    total_size += child.size
                elif child.content_type in (WPD_CONTENT_TYPE_DIRECTORY, WPD_CONTENT_TYPE_STORAGE):
                    stack.append(child)
        except Exception as e:
            print(f"Size calculation error: {e}")
    return total_size


def get_mtp_item_size(mtp_path: str) -> int:
    """
    Get size of file or folder on MTP device
    
    Args:
        mtp_path: Full MTP path in format:
            "This PC\\DeviceName\\Storage\\Path\\To\\Item"
    
    Returns:
        int: Size in bytes (0 if not found)
    """
    try:
        parts = mtp_path.split("\\")
        if len(parts) < 3 or parts[0] != "This PC":
            raise ValueError("Invalid path format. Should be: 'This PC\\DeviceName\\Storage\\...'")
        
        device_name = parts[1]
        storage_path_1 = "\\".join(parts[2:])
        
        for device in get_portable_devices():
            if device_name in device.devicename:
                storage_path = f"{device.devicename}\\{storage_path_1}"
                content = get_content_from_device_path(device, storage_path)
                
                if not content:
                    return 0
                if content.content_type == WPD_CONTENT_TYPE_FILE:
                    return content.size
                if content.content_type in (WPD_CONTENT_TYPE_DIRECTORY, WPD_CONTENT_TYPE_STORAGE):
                    return get_mtp_folder_size(content)
                return 0
        return 0
    except Exception as e:
        print(f"Size retrieval error: {e}")
        return 0
    finally:
        device.close()


def main():
    """Command-line interface for MTP operations"""
    parser = argparse.ArgumentParser(description="MTP Device File Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # List devices command
    list_parser = subparsers.add_parser("list-devices", help="List connected MTP devices")

    # Copy command
    copy_parser = subparsers.add_parser("copy", help="Copy file/folder to MTP device")
    copy_parser.add_argument("source", help="Local source path")
    copy_parser.add_argument("destination", help="MTP destination path")

    # Exists command
    exists_parser = subparsers.add_parser("exists", help="Check path existence on MTP")
    exists_parser.add_argument("path", help="MTP path to check")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete path from MTP device")
    delete_parser.add_argument("path", help="MTP path to delete")

    # Size command
    size_parser = subparsers.add_parser("size", help="Get size of MTP path")
    size_parser.add_argument("path", help="MTP path to get size of")

    args = parser.parse_args()

    try:
        if args.command == "list-devices":
            devices = get_mtp_devices()
            for device_path, device_name in devices:
                print(f"{device_path} | {device_name}")

        elif args.command == "copy":
            copy_to_mtp_device(args.source, args.destination)

        elif args.command == "exists":
            exists = exists_in_mtp_device(args.path)
            print(exists)
            sys.exit(0 if exists else 1)

        elif args.command == "delete":
            success = delete_from_mtp_device(args.path)
            print(success)
            sys.exit(0 if success else 1)

        elif args.command == "size":
            size = get_mtp_item_size(args.path)
            print(size)

    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()