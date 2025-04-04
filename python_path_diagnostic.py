# python_path_diagnostic.py
import os
import sys
import platform

def print_diagnostic_info():
    """
    Print detailed information about Python environment and paths
    """
    print("\n--- Python Environment Path Diagnostic ---")
    
    # Current working directory
    print(f"Current Working Directory: {os.getcwd()}")
    
    # Python executable path
    print(f"Python Executable: {sys.executable}")
    
    # Python version
    print(f"Python Version: {sys.version}")
    
    # Platform information
    print(f"Platform: {platform.platform()}")
    
    # Python path
    print("\nPython Path (sys.path):")
    for idx, path in enumerate(sys.path, 1):
        print(f"{idx}. {path}")
    
    # Environment variables related to Python path
    print("\nRelevant Environment Variables:")
    env_vars = [
        'PYTHONPATH',
        'PYTHONHOME',
        'VIRTUAL_ENV',
        'PATH'
    ]
    
    for var in env_vars:
        value = os.environ.get(var, 'Not set')
        print(f"{var}: {value}")
    
    print("\n--- End of Diagnostic Information ---\n")

if __name__ == '__main__':
    print_diagnostic_info()