# scripts/venv_manager.py
# python scripts/venv_manager.py --name skinspire_v2_env

import os
import sys
import json
import subprocess
import venv
from pathlib import Path
from datetime import datetime

class VenvManager:
    def __init__(self, venv_name="venv"):
        # Base project path is the parent directory of the script
        self.base_path = Path(__file__).parent.parent
        
        # Virtual environment will be created in the project directory
        self.venv_name = venv_name
        self.venv_path = self.base_path / self.venv_name
        
        # Scripts directory based on OS
        self.scripts_path = self.venv_path / ("Scripts" if os.name == 'nt' else "bin")
        
        # Path to global Python (used for creating the virtual environment)
        self.global_python = Path(sys.executable)
        
        # Virtual environment Python and pip
        self.python_path = self.scripts_path / ("python.exe" if os.name == 'nt' else "python")
        self.pip_path = self.scripts_path / ("pip.exe" if os.name == 'nt' else "pip")
        
        # Project requirements file
        self.requirements_path = self.base_path / "requirements.txt"
        
        # Logs for tracking operations
        self.logs = []
        
        # Store path information in project folder
        self.path_config = self.base_path / "path_config.json"

    def run_pip_command(self, *args):
        """Run a pip command with the virtual environment's Python"""
        try:
            cmd = [str(self.python_path), "-m", "pip"]
            cmd.extend(args)
            
            self.log(f"Running command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.log(f"Failed to run pip command: {result.stderr}", error=True)
                return False
                
            self.log(result.stdout.strip())
            return True
        except Exception as e:
            self.log(f"Error running pip command: {str(e)}", error=True)
            return False

    def check_and_install_packages(self):
        """Check and install missing or outdated packages"""
        # First upgrade pip
        if not self.run_pip_command("install", "--upgrade", "pip"):
            return False
            
        # Then install setuptools and wheel
        if not self.run_pip_command("install", "setuptools", "wheel"):
            return False
            
        # Install from requirements file if it exists
        if self.requirements_path.exists():
            if not self.run_pip_command("install", "-r", str(self.requirements_path)):
                return False
            self.log("Successfully installed all requirements")
        else:
            self.log("requirements.txt not found - skipping package installation", error=True)
            
        return True

    def check_venv_health(self):
        """Check if virtual environment is healthy"""
        try:
            if not self.venv_path.exists():
                self.log("Virtual environment not found")
                return False

            # Check for key components
            if not self.python_path.exists():
                self.log(f"Python executable not found at {self.python_path}", error=True)
                return False
                
            if not self.pip_path.exists():
                self.log(f"Pip executable not found at {self.pip_path}", error=True)
                return False

            # Try running Python to verify it works
            try:
                result = subprocess.run(
                    [str(self.python_path), "-V"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                self.log(f"Using virtual environment Python: {result.stdout.strip()}")
                self.log(f"Virtual environment location: {self.venv_path}")
                return True
            except subprocess.CalledProcessError as e:
                self.log(f"Failed to verify Python: {e.stderr}", error=True)
                return False

        except Exception as e:
            self.log(f"Error checking environment health: {str(e)}", error=True)
            return False

    def create_venv(self, force=False):
        """Create virtual environment using global Python"""
        try:
            if self.venv_path.exists():
                if not force:
                    self.log(f"Virtual environment already exists at: {self.venv_path}")
                    return True
                else:
                    self.log("Removing existing virtual environment...")
                    import shutil
                    shutil.rmtree(self.venv_path)

            self.log(f"Creating virtual environment at: {self.venv_path}")
            self.log(f"Using global Python: {self.global_python}")
            
            # Use the global Python to create the virtual environment
            result = subprocess.run(
                [str(self.global_python), "-m", "venv", str(self.venv_path)],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self.log(f"Failed to create virtual environment: {result.stderr}", error=True)
                return False
                
            self.log("Virtual environment created successfully")
            return True

        except Exception as e:
            self.log(f"Failed to create virtual environment: {str(e)}", error=True)
            return False

    def update_path_config(self):
        """Update path_config.json with current paths"""
        try:
            path_data = {
                "VENV_PATH": str(self.venv_path),
                "SCRIPTS_PATH": str(self.scripts_path),
                "PYTHON_PATH": str(self.python_path),
                "PIP_PATH": str(self.pip_path),
                "PROJECT_ROOT": str(self.base_path),
                "GLOBAL_PYTHON": str(self.global_python),
                "UPDATED_AT": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            with open(self.path_config, 'w') as f:
                json.dump(path_data, f, indent=4)
                
            self.log(f"Updated path configuration at {self.path_config}")
            return True
        except Exception as e:
            self.log(f"Failed to update path configuration: {str(e)}", error=True)
            return False

    def create_activate_script(self):
        """Create a convenient activation script"""
        try:
            activate_path = self.base_path / "activate.bat"
            
            with open(activate_path, 'w') as f:
                f.write(f"""@echo off
call "{self.scripts_path}\\activate.bat"
echo Virtual environment activated for Skinspire project
echo Python path: {self.python_path}
""")
                
            self.log(f"Created activation script at {activate_path}")
            return True
        except Exception as e:
            self.log(f"Failed to create activation script: {str(e)}", error=True)
            return False

    def log(self, message, error=False):
        """Log progress"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"{'ERROR: ' if error else ''}{message}")
        self.logs.append({
            "timestamp": timestamp,
            "message": message,
            "is_error": error
        })

    def run(self, force_create=False):
        """Main execution flow"""
        try:
            # Print current Python info
            self.log(f"Global Python: {self.global_python}")
            self.log(f"Project directory: {self.base_path}")
            
            # Check environment health
            if not self.check_venv_health() or force_create:
                # Environment doesn't exist or is corrupted, create new one
                if not self.create_venv(force=force_create):
                    return False

            # Update path configuration
            self.update_path_config()
            
            # Create activation script
            self.create_activate_script()

            # Check and install packages
            if not self.check_and_install_packages():
                self.log("Warning: Some packages may not have been installed correctly.", error=True)
                self.log("You may need to manually install packages after activating the environment.")
                # Continue execution even if package installation fails

            self.log("Environment setup completed successfully!")
            self.log(f"To activate, run: {self.base_path / 'activate.bat'}")
            return True

        except Exception as e:
            self.log(f"Unexpected error: {str(e)}", error=True)
            return False

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Manage Python virtual environment')
    parser.add_argument('--force', action='store_true', help='Force recreation of virtual environment')
    parser.add_argument('--name', default='venv', help='Name of virtual environment folder (default: venv)')
    args = parser.parse_args()

    manager = VenvManager(venv_name=args.name)
    success = manager.run(force_create=args.force)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()