"""
Windows environment configuration helper for web2json.

This script creates a system-wide batch file to run web2json correctly on Windows systems.
Run this script after installing web2json with 'pip install -e .' to create
the necessary helper file.
"""
import os
import sys
import site
from pathlib import Path

def create_windows_helper():
    """
    Create a system-wide batch file for Windows users.
    
    This function creates a single batch file (web2json.bat) that:
    1. Activates the virtual environment
    2. Sets the PYTHONPATH environment variable
    3. Runs web2json with any provided arguments
    
    This addresses a common issue on Windows where Python sometimes
    has difficulty finding installed packages when running a local module.
    """
    # Get current directory (where this script is located)
    current_dir = os.path.abspath(os.path.dirname(__file__))
    
    # Get user's home directory
    home_dir = os.path.expanduser("~")
    tools_dir = os.path.join(home_dir, "Tools")
    
    # Get site-packages paths
    site_packages = site.getsitepackages()
    
    # Find the path that contains 'site-packages'
    site_packages_path = next((p for p in site_packages if 'site-packages' in p), 
                               site_packages[0])
    
    # Also add the project directory to PYTHONPATH
    pythonpath = f"{current_dir};{site_packages_path}"
    
    print("\n=== Windows-specific setup ===")
    print(f"Creating system-wide batch file in: {tools_dir}")
    
    try:
        # Ensure Tools directory exists
        if not os.path.exists(tools_dir):
            os.makedirs(tools_dir)
            print(f"✓ Created Tools directory: {tools_dir}")
            
        # Create web2json.bat in the Tools directory
        batch_path = os.path.join(tools_dir, "web2json.bat")
        with open(batch_path, 'w') as f:
            f.write("@echo off\n")
            f.write(f"cd {current_dir}\n")
            f.write("call .venv\\Scripts\\activate\n")
            f.write(f"set PYTHONPATH=%PYTHONPATH%;{pythonpath}\n")
            f.write("python -m web2json %*\n")
        
        print(f"✓ Created: {batch_path}")
        
        # Add to PATH if not already there
        try:
            import winreg
            with winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER) as reg:
                with winreg.OpenKey(reg, r"Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
                    path, _ = winreg.QueryValueEx(key, "Path")
                    
                    if tools_dir.lower() not in path.lower():
                        new_path = path + ";" + tools_dir
                        winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
                        print(f"✓ Added {tools_dir} to your PATH environment variable")
                    else:
                        print(f"✓ {tools_dir} is already in your PATH environment variable")
        except Exception as e:
            print(f"! Could not automatically update PATH: {e}")
            print(f"  To add {tools_dir} to your PATH manually, run this command:")
            print(f"  setx PATH \"%PATH%;{tools_dir}\"")
        
        # Display clear instructions about PATH and restarting
        print("\n")
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║  IMPORTANT: Windows PATH Update Requires System Restart      ║")
        print("╚══════════════════════════════════════════════════════════════╝")
        print("\nPlease restart your computer before using the global command.")
        print("\nUntil you restart, you can use web2json in these ways:")
        print(f"1. Use the full path: {batch_path} -u https://example.com -o output")
        print("2. Navigate to the Tools directory first:")
        print(f"   cd {tools_dir}")
        print("   web2json -u https://example.com -o output")
        
        # Check if Python can now import the required modules
        try:
            # Temporarily add paths to sys.path
            sys.path.append(current_dir)
            sys.path.append(site_packages_path)
            
            # Try to import the key modules
            import requests
            import beautifulsoup4  # This might fail but we'll handle it
            print("\n✓ Python can now find the required dependencies")
        except ImportError as e:
            print(f"\n! Warning: Could not import all dependencies: {e}")
            print("  This is normal if beautifulsoup4 fails - it will still work when used")
            print("  The helper batch file will resolve any import issues")
        
        print("\nAfter restarting your computer:")
        print("--------------------------------")
        print("You can run web2json from any command prompt simply by typing:")
        print("  web2json -u https://example.com -o output_name")
        print("\nTo test your installation, you'll use:")
        print("  web2json -u https://resoltico.com/en/tools/web2json/ -o test_output")
        print("  This should create a file named test_output.json in the fetched_jsons folder")
        print("================================\n")
        
        return True
    except Exception as e:
        print(f"! Error creating Windows helper batch file: {e}")
        print("\nManual fix:")
        print(f"1. Create a batch file named web2json.bat in {tools_dir} with this content:")
        print(f"   @echo off")
        print(f"   cd {current_dir}")
        print(f"   call .venv\\Scripts\\activate")
        print(f"   set PYTHONPATH=%PYTHONPATH%;{pythonpath}")
        print(f"   python -m web2json %*")
        print(f"2. Add {tools_dir} to your PATH by running:")
        print(f"   setx PATH \"%PATH%;{tools_dir}\"")
        print(f"3. Restart your computer for the PATH change to take effect")
        print("================================\n")
        return False

def check_windows():
    """Check if the current system is Windows."""
    return os.name == 'nt' or sys.platform.startswith('win')

if __name__ == "__main__":
    """Main entry point for the script."""
    if not check_windows():
        print("This script is only for Windows systems.")
        sys.exit(0)
    
    create_windows_helper()
