#!/usr/bin/env python3
"""
Test script to verify integration between main.py and getgamedownloadurl.py
"""

import os
import sys
import subprocess

def test_getgamedownloadurl_script():
    """Test if getgamedownloadurl.py can be imported as a module"""
    print("=== Testing getgamedownloadurl.py ===")
    
    # Check if the script exists
    script_path = "bin/getgamedownloadurl.py"
    if not os.path.exists(script_path):
        print(f"[ERROR] {script_path} not found")
        return False
    
    # Test importing the module
    try:
        from bin.getgamedownloadurl import get_direct_download_url
        print("[SUCCESS] Successfully imported getgamedownloadurl module")
        return True
    except ImportError as e:
        print(f"[ERROR] Failed to import getgamedownloadurl module: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error importing module: {e}")
        return False

def test_main_integration():
    """Test if main.py can import and use the bin modules"""
    print("\n=== Testing main.py integration ===")
    
    # Check if main.py exists
    if not os.path.exists("main.py"):
        print("[ERROR] main.py not found")
        return False
    
    # Test importing the modules
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath("main.py")))
        from bin import gamelistparser, gamedataextractor
        print("[SUCCESS] Successfully imported bin modules")
        return True
    except ImportError as e:
        print(f"[ERROR] Failed to import bin modules: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error during import: {e}")
        return False

def test_python_environment():
    """Test Python environment and dependencies"""
    print("\n=== Testing Python Environment ===")
    
    # Check Python version
    python_version = sys.version_info
    print(f"[INFO] Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version < (3, 7):
        print("[WARNING] Python 3.7+ recommended")
    
    # Check if virtual environment exists
    if os.path.exists("env"):
        print("[INFO] Virtual environment found")
    else:
        print("[INFO] No virtual environment found, using system Python")
    
    # Test required modules
    required_modules = [
        ("requests", "requests"),
        ("beautifulsoup4", "bs4"), 
        ("selenium", "selenium"),
        ("webdriver_manager", "webdriver_manager")
    ]
    
    missing_modules = []
    for module_name, import_name in required_modules:
        try:
            __import__(import_name)
            print(f"[SUCCESS] {module_name} available")
        except ImportError:
            print(f"[ERROR] {module_name} not available")
            missing_modules.append(module_name)
    
    if missing_modules:
        print(f"\n[WARNING] Missing modules: {', '.join(missing_modules)}")
        print("[INFO] Install with: pip install " + " ".join(missing_modules))
        return False
    
    return True

def main():
    """Run all tests"""
    print("SteamRip External Downloader - Integration Test")
    print("=" * 50)
    
    tests = [
        test_python_environment,
        test_main_integration,
        test_getgamedownloadurl_script
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"[ERROR] Test failed with exception: {e}")
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("[SUCCESS] All tests passed! Integration should work correctly.")
        return 0
    else:
        print("[WARNING] Some tests failed. Please check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
