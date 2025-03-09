# Virtual Environment Manager Documentation

## Overview
The Virtual Environment Manager provides tools for maintaining Python virtual environments for the SkinSpire project, with focus on environment health checks and package management.

## Program Intent & Scope

### Primary Goals
1. Maintain existing virtual environments
2. Install/update missing packages
3. Create new environments when needed
4. Verify environment health
5. Support multiple environments

### Out of Scope
- Project deployment
- Production environment management
- Database migrations
- Application configuration

## Required Files & Dependencies

### Core Files
1. `venv_manager.py` - Main script
2. `requirements.txt` - Package specifications
3. `test_venv_manager.py` - Test suite

### Location Requirements
```
project_root/
├── scripts/
│   └── venv_manager.py
├── tests/
│   └── test_venv_manager.py
└── requirements.txt
```

### requirements.txt Format
- One package per line
- Version specifications using ==
- Comments start with #
- Example:
  ```
  Flask==3.1.0
  SQLAlchemy==2.0.36
  pytest==8.3.4
  ```

## Program Flow

### 1. Environment Detection
- Checks for existing environment at default location
- Default: skinspire-env in AppData/Local/Programs (Windows)
- Can specify alternate environment name via command line

### 2. Health Check Flow
```
Check Environment Health
├── Verify environment exists
├── Check required components
│   ├── Python executable
│   ├── pip executable
│   └── Scripts/bin directory
└── Test basic package import
```

### 3. Package Management Flow
```
Package Management
├── Read requirements.txt
├── Get installed packages
├── Compare versions
├── Identify
│   ├── Missing packages
│   └── Outdated packages
└── Install/Update as needed
```

### 4. Environment Creation Flow (If Needed)
```
Create Environment
├── Remove existing if force=True
├── Create new environment
├── Verify creation
└── Install base packages
```

## Health Checks

### Environment Structure
- Verifies directory structure
- Checks executable permissions
- Validates path configurations

### Package Health
- Verifies pip functionality
- Checks package import capability
- Validates package versions

### File System Checks
- Validates requirements.txt
- Checks write permissions
- Verifies path accessibility

## Usage Examples

### Basic Usage
```bash
# Check existing environment
python scripts/venv_manager.py

# Create new environment
python scripts/venv_manager.py --new-env my-new-env

# Force recreation
python scripts/venv_manager.py --force
```

### Command Line Options
- `--new-env NAME`: Create new environment
- `--force`: Force environment recreation
- Default: Check/update existing environment

## Test Suite Documentation

### Test Categories

1. **Basic Setup Tests**
   - Environment initialization
   - Path configuration
   - File existence

2. **Health Check Tests**
   - Non-existent environment
   - Corrupted environment
   - Healthy environment

3. **Package Management Tests**
   - Package detection
   - Version comparison
   - Installation verification

4. **Environment Creation Tests**
   - New environment creation
   - Force recreation
   - Multiple environments

### Test Data Requirements

1. **Test Environment**
   - Temporary test environment name
   - Isolated from production environment
   - Automatic cleanup

2. **Test Dependencies**
   - pytest
   - Required project packages
   - Platform-specific dependencies

### Running Tests
```bash
# Run all tests
pytest tests/test_venv_manager.py -v

# Run specific test category
pytest tests/test_venv_manager.py -v -k "health"

# Run without platform-specific tests
pytest tests/test_venv_manager.py -v -m "not platform_specific"
```

### Test Result Interpretation
- Success: All health checks pass
- Warning: Non-critical issues
- Failure: Critical environment problems

## Error Handling

### Common Errors
1. Environment not found
2. Corrupted environment
3. Package installation failures
4. Permission issues
5. Network problems

### Error Recovery
- Automatic retry for network issues
- Rollback on failed installations
- Detailed error logging

## Maintenance

### Regular Tasks
1. Update requirements.txt
2. Run health checks
3. Review error logs
4. Clean unused environments

### Best Practices
1. Keep requirements.txt updated
2. Regular health checks
3. Clean temporary environments
4. Monitor disk space

## Troubleshooting

### Common Issues
1. PATH configuration
2. Package conflicts
3. Permission errors
4. Network connectivity

### Resolution Steps
1. Check environment health
2. Verify requirements.txt
3. Review error logs
4. Force recreation if needed