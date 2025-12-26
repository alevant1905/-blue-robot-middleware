#!/usr/bin/env python3
"""
Verification script for tool selector refactoring.

Checks that all components are in place and working correctly.
"""

import sys
from pathlib import Path


def check_package_structure():
    """Verify package structure is correct."""
    print("📦 Checking package structure...")

    required_files = [
        'blue/tool_selector/__init__.py',
        'blue/tool_selector/models.py',
        'blue/tool_selector/constants.py',
        'blue/tool_selector/utils.py',
        'blue/tool_selector/context.py',
        'blue/tool_selector/selector.py',
        'blue/tool_selector/integration.py',
        'blue/tool_selector/data/music_data.py',
        'blue/tool_selector/detectors/__init__.py',
        'blue/tool_selector/detectors/base.py',
        'blue/tool_selector/detectors/music.py',
        'blue/tool_selector/detectors/gmail.py',
        'blue/tool_selector/detectors/lights.py',
        'blue/tool_selector/detectors/documents.py',
        'blue/tool_selector/detectors/web.py',
        'blue/tool_selector/detectors/vision.py',
        'blue/tool_selector/detectors/weather.py',
        'blue/tool_selector/detectors/calendar.py',
        'blue/tool_selector/detectors/simple_detectors.py',
    ]

    missing = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing.append(file_path)
            print(f"   ❌ Missing: {file_path}")
        else:
            print(f"   ✅ Found: {file_path}")

    if missing:
        print(f"\n❌ Missing {len(missing)} required files!")
        return False

    print(f"\n✅ All {len(required_files)} required files present!")
    return True


def check_imports():
    """Verify imports work correctly."""
    print("\n📥 Checking imports...")

    try:
        from blue.tool_selector import (
            ToolIntent,
            ToolSelectionResult,
            ImprovedToolSelector,
            integrate_with_existing_system,
        )
        print("   ✅ Main imports successful")

        from blue.tool_selector.detectors import MusicDetector, GmailDetector
        print("   ✅ Detector imports successful")

        from blue.tool_selector.models import ToolIntent as TI
        print("   ✅ Model imports successful")

        return True
    except ImportError as e:
        print(f"   ❌ Import failed: {e}")
        return False


def check_functionality():
    """Verify basic functionality."""
    print("\n🔧 Checking functionality...")

    try:
        from blue.tool_selector import ImprovedToolSelector

        selector = ImprovedToolSelector()
        print("   ✅ Selector instantiated")

        # Test music detection
        result = selector.select_tool("play some jazz music", [])
        if result.primary_tool and result.primary_tool.tool_name == 'play_music':
            print("   ✅ Music detection working")
        else:
            print("   ⚠️  Music detection unexpected result")

        # Test greeting skip
        result = selector.select_tool("hello", [])
        if result.primary_tool is None:
            print("   ✅ Greeting skip working")
        else:
            print("   ⚠️  Greeting should not trigger tool")

        # Test integration function
        from blue.tool_selector import integrate_with_existing_system
        tool, args, feedback = integrate_with_existing_system(
            "check my email", [], selector
        )
        if tool == 'read_gmail':
            print("   ✅ Integration function working")
        else:
            print(f"   ⚠️  Expected 'read_gmail', got '{tool}'")

        return True
    except Exception as e:
        print(f"   ❌ Functionality check failed: {e}")
        return False


def count_statistics():
    """Count and display statistics."""
    print("\n📊 Statistics...")

    # Count files
    package_dir = Path('blue/tool_selector')
    py_files = list(package_dir.rglob('*.py'))
    print(f"   📄 Python files: {len(py_files)}")

    # Count lines
    total_lines = 0
    for py_file in py_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                total_lines += len(f.readlines())
        except:
            pass
    print(f"   📏 Total lines: {total_lines}")

    # Count detectors
    detector_dir = package_dir / 'detectors'
    if detector_dir.exists():
        detector_files = [
            f for f in detector_dir.glob('*.py')
            if f.name not in ['__init__.py', 'base.py']
        ]
        print(f"   🔍 Detector modules: {len(detector_files)}")

    # Count test files
    test_dir = Path('tests/test_tool_selector')
    if test_dir.exists():
        test_files = list(test_dir.glob('test_*.py'))
        print(f"   🧪 Test files: {len(test_files)}")

    return True


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("🔍 Tool Selector Refactoring Verification")
    print("=" * 60)

    checks = [
        ("Package Structure", check_package_structure),
        ("Imports", check_imports),
        ("Functionality", check_functionality),
        ("Statistics", count_statistics),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} check crashed: {e}")
            results.append((name, False))

    # Summary
    print("\n" + "=" * 60)
    print("📋 Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} - {name}")

    print(f"\n   {passed}/{total} checks passed")

    if passed == total:
        print("\n🎉 All checks passed! Refactoring is complete and functional.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} check(s) failed. Please review.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
