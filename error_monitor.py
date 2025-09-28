#!/usr/bin/env python3
"""
Error Monitor for SteamRip External Downloader
Automatically checks for issues and reports them
"""

import os
import sys
import json
import subprocess
import importlib
from pathlib import Path

class ErrorMonitor:
    def __init__(self):
        self.errors = []
        self.warnings = []
        
    def add_error(self, message):
        self.errors.append(message)
        print(f"[ERROR] {message}")
        
    def add_warning(self, message):
        self.warnings.append(message)
        print(f"[WARNING] {message}")
        
    def check_python_environment(self):
        """Check Python environment and dependencies"""
        print("=== Checking Python Environment ===")
        
        # Check Python version
        version = sys.version_info
        if version < (3, 7):
            self.add_error(f"Python version {version.major}.{version.minor} is too old. Need 3.7+")
        else:
            print(f"[OK] Python version: {version.major}.{version.minor}.{version.micro}")
            
        # Check virtual environment
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            print("[OK] Running in virtual environment")
        else:
            self.add_warning("Not running in virtual environment")
            
    def check_dependencies(self):
        """Check if all required dependencies are installed"""
        print("\n=== Checking Dependencies ===")
        
        required_modules = [
            ("requests", "requests"),
            ("beautifulsoup4", "bs4"),
            ("selenium", "selenium"),
            ("webdriver_manager", "webdriver_manager"),
            ("lxml", "lxml"),
            ("tkinter", "tkinter")
        ]
        
        for module_name, import_name in required_modules:
            try:
                importlib.import_module(import_name)
                print(f"[OK] {module_name} available")
            except ImportError:
                self.add_error(f"{module_name} not available")
                
    def check_files(self):
        """Check if all required files exist"""
        print("\n=== Checking Files ===")
        
        required_files = [
            "main.py",
            "bin/getgamedownloadurl.py",
            "bin/gamedataextractor.py", 
            "bin/gamelistparser.py",
            "requirements.txt",
            "README.md"
        ]
        
        for file_path in required_files:
            if os.path.exists(file_path):
                print(f"[OK] {file_path} exists")
            else:
                self.add_error(f"{file_path} missing")
                
    def check_directories(self):
        """Check if required directories exist"""
        print("\n=== Checking Directories ===")
        
        required_dirs = [
            "data",
            "data/clones",
            "downloads",
            "temp_downloads"
        ]
        
        for dir_path in required_dirs:
            if os.path.exists(dir_path):
                print(f"[OK] {dir_path} exists")
            else:
                self.add_warning(f"{dir_path} missing (will be created automatically)")
                
    def check_brave_browser(self):
        """Check if Brave browser is available"""
        print("\n=== Checking Brave Browser ===")
        
        brave_paths = [
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
            r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe"
        ]
        
        brave_found = False
        for path in brave_paths:
            if os.path.exists(path):
                print(f"[OK] Brave browser found at: {path}")
                brave_found = True
                break
                
        if not brave_found:
            self.add_error("Brave browser not found. Please install Brave browser.")
            
    def check_syntax(self):
        """Check Python syntax of all files"""
        print("\n=== Checking Python Syntax ===")
        
        python_files = [
            "main.py",
            "bin/getgamedownloadurl.py",
            "bin/gamedataextractor.py",
            "bin/gamelistparser.py"
        ]
        
        for file_path in python_files:
            try:
                subprocess.run([sys.executable, "-m", "py_compile", file_path], 
                             capture_output=True, check=True)
                print(f"[OK] {file_path} syntax is valid")
            except subprocess.CalledProcessError as e:
                self.add_error(f"{file_path} has syntax errors: {e.stderr.decode()}")
                
    def check_database_integrity(self):
        """Check database files for integrity"""
        print("\n=== Checking Database Integrity ===")
        
        data_dir = "data/clones"
        if not os.path.exists(data_dir):
            self.add_warning("Database directory doesn't exist yet")
            return
            
        json_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
        
        if not json_files:
            self.add_warning("No database files found")
            return
            
        corrupted_files = []
        for file_name in json_files:
            file_path = os.path.join(data_dir, file_name)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Skip failed_games.json as it has a different structure
                if file_name == "failed_games.json":
                    if isinstance(data, list):
                        print(f"[OK] {file_name} has correct structure (list of failed games)")
                    else:
                        corrupted_files.append(f"{file_name} (should be a list, got {type(data).__name__})")
                    continue
                    
                # Check for required fields in game data files
                required_fields = ['title', 'download_links']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    corrupted_files.append(f"{file_name} (missing: {', '.join(missing_fields)})")
                    
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                corrupted_files.append(f"{file_name} (JSON error: {e})")
            except Exception as e:
                corrupted_files.append(f"{file_name} (error: {e})")
                
        if corrupted_files:
            for file_name in corrupted_files:
                self.add_error(f"Corrupted database file: {file_name}")
        else:
            print(f"[OK] All {len(json_files)} database files are valid")
            
    def run_all_checks(self):
        """Run all checks and return summary"""
        print("SteamRip External Downloader - Error Monitor")
        print("=" * 50)
        
        self.check_python_environment()
        self.check_dependencies()
        self.check_files()
        self.check_directories()
        self.check_brave_browser()
        self.check_syntax()
        self.check_database_integrity()
        
        print("\n" + "=" * 50)
        print("SUMMARY:")
        print(f"Errors: {len(self.errors)}")
        print(f"Warnings: {len(self.warnings)}")
        
        if self.errors:
            print("\nCRITICAL ISSUES FOUND:")
            for error in self.errors:
                print(f"  - {error}")
                
        if self.warnings:
            print("\nWARNINGS:")
            for warning in self.warnings:
                print(f"  - {warning}")
                
        if not self.errors and not self.warnings:
            print("\n[SUCCESS] No issues found! System is ready to use.")
            
        return len(self.errors) == 0

def main():
    monitor = ErrorMonitor()
    success = monitor.run_all_checks()
    
    if success:
        print("\n[RECOMMENDATION] Run the main application: python main.py")
    else:
        print("\n[RECOMMENDATION] Fix the errors above before running the application")
        
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
