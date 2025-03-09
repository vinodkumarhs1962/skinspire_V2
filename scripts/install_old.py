# scripts/install.py
# INFO:__main__:Using existing virtual environment: skinspire-env
# INFO:__main__:Location: C:\Users\vinod\AppData\Local\Programs\skinspire-env
import subprocess
import sys
import os
from pathlib import Path
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def detect_virtual_env():
    """Detect if running in virtual environment and get details"""
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        venv_path = sys.prefix
        venv_name = os.path.basename(venv_path)
        logger.info(f"Using existing virtual environment: {venv_name}")
        logger.info(f"Location: {venv_path}")
        return venv_path
    return None

def update_path_config(venv_path):
    """Update path configuration for existing environment"""
    if venv_path:
        paths = {
            "VENV_PATH": venv_path,
            "SCRIPTS_PATH": str(Path(venv_path) / "Scripts" if os.name == 'nt' else "bin"),
            "PYTHON_PATH": str(Path(venv_path) / "Scripts" / "python.exe" if os.name == 'nt' else "bin/python"),
            "PIP_PATH": str(Path(venv_path) / "Scripts" / "pip.exe" if os.name == 'nt' else "bin/pip"),
            "PROJECT_ROOT": str(Path(__file__).parent.parent)
        }
        
        path_config = Path(__file__).parent.parent / "path_config.json"
        with open(path_config, 'w') as f:
            json.dump(paths, f, indent=4)
        logger.info(f"Updated path configuration in {path_config}")

def install_dependencies():
    """Install required build tools and dependencies"""
    try:
        # Detect virtual environment
        venv_path = detect_virtual_env()
        if not venv_path:
            logger.error("Not running in a virtual environment!")
            logger.info("Please activate skinspire-env first")
            return False

        # Update path configuration
        update_path_config(venv_path)

        # Install build tools
        logger.info("Installing/Updating build tools...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True)
        subprocess.run([sys.executable, "-m", "pip", "install", "build"], check=True)

        # Install the project in development mode
        project_root = Path(__file__).parent.parent
        logger.info("Installing project in development mode...")
        subprocess.run([
            sys.executable, 
            "-m", 
            "pip", 
            "install", 
            "-e", 
            str(project_root)
        ], check=True)

        logger.info("Installation completed successfully!")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Installation failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = install_dependencies()
    sys.exit(0 if success else 1)