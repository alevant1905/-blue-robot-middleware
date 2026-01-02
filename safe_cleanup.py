#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Safe Cleanup Script for Blue Robot Middleware
==============================================
Removes unnecessary files and directories while preserving core functionality.

This script will:
1. Remove backup/duplicate files
2. Remove old cleanup scripts
3. Remove test files
4. Remove redundant uploads directory
5. Optionally review camera images

Run with: python safe_cleanup.py
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Base directory
BASE_DIR = Path(__file__).parent.resolve()

# Files to delete
FILES_TO_DELETE = [
    "bluetools2.py.backup",
    "bluetoolsclaude.py",
    "blue.db",  # Duplicate - keep data/blue.db
    "cleanup_script.py",
    "cleanup_script_v2.py",
    "test_documents.py",
]

# Directories to delete
DIRS_TO_DELETE = [
    "uploads",  # Redundant with uploaded_documents/
]

def format_size(size_bytes):
    """Format bytes to human readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def get_file_info(filepath):
    """Get file size and modification time."""
    try:
        stat = filepath.stat()
        size = stat.st_size
        mtime = datetime.fromtimestamp(stat.st_mtime)
        return size, mtime
    except:
        return 0, None

def scan_camera_images():
    """Scan for camera images in uploaded_documents."""
    uploaded_docs = BASE_DIR / "uploaded_documents"
    if not uploaded_docs.exists():
        return []

    camera_images = sorted(uploaded_docs.glob("camera_NEW_*.jpg"))
    return camera_images

def main():
    print("=" * 70)
    print("🧹 Blue Robot Middleware - Safe Cleanup Script")
    print("=" * 70)
    print()

    total_size = 0
    deleted_files = []
    skipped_files = []

    # Step 1: Delete unnecessary files
    print("📄 SCANNING FILES TO DELETE...")
    print()

    for filename in FILES_TO_DELETE:
        filepath = BASE_DIR / filename
        if filepath.exists():
            size, mtime = get_file_info(filepath)
            total_size += size
            print(f"  ✓ Found: {filename}")
            print(f"    Size: {format_size(size)}")
            if mtime:
                print(f"    Modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
            deleted_files.append((filepath, size))
        else:
            print(f"  ⊘ Not found: {filename} (already deleted)")
            skipped_files.append(filename)

    print()

    # Step 2: Delete unnecessary directories
    print("📁 SCANNING DIRECTORIES TO DELETE...")
    print()

    for dirname in DIRS_TO_DELETE:
        dirpath = BASE_DIR / dirname
        if dirpath.exists() and dirpath.is_dir():
            dir_size = sum(f.stat().st_size for f in dirpath.rglob('*') if f.is_file())
            file_count = sum(1 for _ in dirpath.rglob('*') if _.is_file())
            total_size += dir_size
            print(f"  ✓ Found: {dirname}/")
            print(f"    Size: {format_size(dir_size)}")
            print(f"    Files: {file_count}")
            deleted_files.append((dirpath, dir_size))
        else:
            print(f"  ⊘ Not found: {dirname}/ (already deleted)")
            skipped_files.append(dirname)

    print()

    # Step 3: Report camera images
    print("📸 SCANNING CAMERA IMAGES...")
    print()

    camera_images = scan_camera_images()
    if camera_images:
        camera_size = sum(img.stat().st_size for img in camera_images)
        print(f"  ℹ Found {len(camera_images)} camera images")
        print(f"    Total size: {format_size(camera_size)}")
        print(f"    Location: uploaded_documents/")
        print()
        print("  Recent images:")
        for img in camera_images[-5:]:  # Show last 5
            size, mtime = get_file_info(img)
            print(f"    - {img.name} ({format_size(size)}) - {mtime.strftime('%Y-%m-%d %H:%M')}")
        print()
        print("  ⚠ Camera images NOT automatically deleted - review manually if needed")
    else:
        print("  ✓ No camera images found")

    print()
    print("=" * 70)
    print("📊 CLEANUP SUMMARY")
    print("=" * 70)
    print()
    print(f"  Files/folders to delete: {len(deleted_files)}")
    print(f"  Total size to free: {format_size(total_size)}")
    print(f"  Camera images (manual review): {len(camera_images)}")
    print()

    # Confirmation
    if not deleted_files:
        print("✨ Nothing to delete - your project is already clean!")
        return

    print("The following will be PERMANENTLY DELETED:")
    print()
    for filepath, size in deleted_files:
        print(f"  ❌ {filepath.name} ({format_size(size)})")
    print()

    response = input("Continue with deletion? (yes/no): ").strip().lower()

    if response not in ['yes', 'y']:
        print()
        print("❌ Cleanup cancelled - no files were deleted")
        return

    # Perform deletion
    print()
    print("🗑️  DELETING FILES...")
    print()

    success_count = 0
    error_count = 0

    for filepath, size in deleted_files:
        try:
            if filepath.is_file():
                filepath.unlink()
                print(f"  ✓ Deleted file: {filepath.name}")
            elif filepath.is_dir():
                shutil.rmtree(filepath)
                print(f"  ✓ Deleted directory: {filepath.name}/")
            success_count += 1
        except Exception as e:
            print(f"  ✗ Error deleting {filepath.name}: {e}")
            error_count += 1

    print()
    print("=" * 70)
    print("✅ CLEANUP COMPLETE")
    print("=" * 70)
    print()
    print(f"  Successfully deleted: {success_count} items")
    print(f"  Errors: {error_count}")
    print(f"  Space freed: {format_size(total_size)}")
    print()

    if camera_images:
        print("📸 NEXT STEPS:")
        print(f"  Review {len(camera_images)} camera images in uploaded_documents/")
        print("  Delete manually if not needed:")
        print(f"    cd uploaded_documents")
        print(f"    # Review and delete: rm camera_NEW_*.jpg")
        print()

    print("🎉 Your Blue Robot project is now cleaner!")
    print()

if __name__ == "__main__":
    main()
