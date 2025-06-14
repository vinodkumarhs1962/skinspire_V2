import os
import shutil
import subprocess
import logging
import sys

def run_command(command):
    """
    Run a shell command and log output
    
    Args:
        command (list): Command to execute
    """
    try:
        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            check=True
        )
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error executing {' '.join(command)}:")
        print(e.stderr)
        raise

def safe_rmtree(path):
    """
    Safely remove a directory tree, handling Windows permission issues
    
    Args:
        path (str): Path to directory to remove
    """
    def handle_readonly(func, path, excinfo):
        """
        Error handler for removing read-only files on Windows
        """
        import stat
        # Is the error an access error?
        if not os.access(path, os.W_OK):
            # Change file mode to allow write
            os.chmod(path, stat.S_IWRITE)
            # Retry the operation
            func(path)
        else:
            # If it's not a permission error, re-raise
            raise

    try:
        # Attempt to remove directory with custom error handler
        shutil.rmtree(path, onerror=handle_readonly)
    except Exception as e:
        print(f"Error removing {path}: {e}")
        # If still fails, try removing files individually
        for root, dirs, files in os.walk(path, topdown=False):
            for name in files:
                try:
                    os.chmod(os.path.join(root, name), 0o666)
                    os.remove(os.path.join(root, name))
                except Exception as file_err:
                    print(f"Could not remove {name}: {file_err}")
            
            for name in dirs:
                try:
                    os.rmdir(os.path.join(root, name))
                except Exception as dir_err:
                    print(f"Could not remove directory {name}: {dir_err}")
        
        # Final attempt to remove root directory
        try:
            os.rmdir(path)
        except Exception as final_err:
            print(f"Final removal failed: {final_err}")

def backup_database():
    """Backup the current database"""
    print("Backing up current database...")
    try:
        # Use explicit backup command with arguments
        run_command(['python', 'scripts/db/backup_manager.py', 'backup'])
    except Exception as e:
        print(f"Backup failed: {e}")
        # Continue even if backup fails

def reset_migrations():
    """
    Reset migrations completely
    
    Steps:
    1. Remove existing migrations folder
    2. Reinitialize migrations
    3. Create initial migration
    4. Upgrade database
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Backup database
    backup_database()
    
    # Remove migrations folder if it exists
    migrations_path = 'migrations'
    if os.path.exists(migrations_path):
        print("Removing existing migrations folder...")
        safe_rmtree(migrations_path)
    
    # Sequence of commands to reset migrations
    commands = [
        ['flask', '--app', 'flask_cli.py', 'db', 'init'],
        ['flask', '--app', 'flask_cli.py', 'db', 'migrate', '-m', 'Initial migration'],
        ['flask', '--app', 'flask_cli.py', 'db', 'upgrade']
    ]
    
    # Execute commands
    for cmd in commands:
        print(f"Executing: {' '.join(cmd)}")
        run_command(cmd)
    
    print("Migration reset completed successfully.")

def main():
    try:
        reset_migrations()
    except Exception as e:
        print(f"Migration reset failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        input("Press Enter to exit...")  # Keeps console window open

if __name__ == '__main__':
    main()