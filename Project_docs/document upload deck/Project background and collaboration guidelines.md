# Skinspire Clinic - Hospital Management System
## Project Synopsis

### System Overview
Skinspire Clinic is developing a cloud-hosted healthcare management system designed for mid-size multispecialty hospitals. The system supports multi-tenant architecture, enabling independent instances per hospital while allowing multiple branches within each instance.

### Key Technical Architecture
- Development Environment: Python 3.12.8
- Web Framework: Flask 3.1.0
- Database: PostgreSQL
- ORM: SQLAlchemy
- Additional Tools: Polars (Data Analysis), ReportLab (Reporting)

### Technology Stack

#### Backend Technologies
- **Language**: Python 3.12.8
- **Framework**: Flask 3.1.0
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Validation**: WTForms
- **Security**: CSRF protection, Input validation

#### Frontend Technologies
- **CSS Framework**: Tailwind CSS
- **JavaScript**: Vanilla JS (Progressive Enhancement)
- **Templates**: Jinja2
- **Responsive**: Mobile-first design


### Core Functional Modules
1. Patient Management
2. Clinical Operations
3. Pharmacy Management
4. Financial Management
5. User Authorization
6. Staff Management

### Technical Design Philosophy
- Modular Architecture
- Security-Focused Design
- Responsive User Experience
- Comprehensive Logging
- EMR Compliance

## Collaboration Guidelines

### Development Guidelines
- Please follow comprehensive development Guidelines described in Skinspire Clinic HMS Technical Development Guidelines v2.0 
- This document provides projct best practices for handling critical errors and standards and approaches to be followed

### Core Communication Principles
- Prioritize incremental, backward-compatible improvements
- Preserve existing code structure and functionality
- Provide minimal invasive, targeted solutions
- Maintain clear, precise communication

### Separation of Concerns
- presentation layer HTML.  use of javascript only where it is essential to deliver required user experience. 
- Forms should define structure and validation rules
- Controllers should handle data population and business logic
- Services should handle database operations

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
├─────────────────────────────────────────────────────────────┤
│  Forms (Basic Validation)  │  Templates  │  User Interface  │
├─────────────────────────────────────────────────────────────┤
│                    CONTROLLER LAYER                         │
├─────────────────────────────────────────────────────────────┤
│     Views/Controllers (Request Handling & Coordination)     │
├─────────────────────────────────────────────────────────────┤
│                    SERVICE LAYER                            │
├─────────────────────────────────────────────────────────────┤
│  Business Logic  │  Validations  │  Payment Processing      │
├─────────────────────────────────────────────────────────────┤
│                    DATA ACCESS LAYER                        │
├─────────────────────────────────────────────────────────────┤
│     Models (SQLAlchemy)    │    Database Operations         │
├─────────────────────────────────────────────────────────────┤
│                    DATABASE LAYER                           │
├─────────────────────────────────────────────────────────────┤
│   PostgreSQL   │   Indexes   │   Constraints   │   Views    │
└─────────────────────────────────────────────────────────────┘
```
### Data Flow Architecture

```
User Input → Form Validation → Controller → Service Layer Validation 
    ↓
Business Logic Processing → Database Operations → Response Generation
    ↓
Template Rendering → User Interface Update
```
### Project Structure and Organization
####  Key Directories
skinspire_v2/
├── app/                            # Main application package
│   ├── api/                        # API endpoints
│   │   ├── routes/                 # API route definitions by module
│   ├── config/                     # Configuration files
│   ├── core/                       # Core system functionality
│   │   ├── environment.py          # Environment management
│   │   ├── db_operations/          # Database operations
│   ├── database/                   # Database connection and SQL
│   │   ├── triggers/               # SQL trigger definitions
│   ├── forms/                      # Form definitions by module
│   ├── models/                     # SQLAlchemy models
│   │   ├── base.py                 # Base classes and mixins
│   │   ├── master.py               # Master data models
│   │   ├── transaction.py          # Transaction models
│   ├── security/                   # Security components
│   │   ├── authentication/         # Authentication logic
│   │   ├── authorization/          # Authorization/RBAC
│   │   ├── encryption/             # Data encryption
│   ├── services/                   # Business logic services
│   ├── static/                     # Frontend assets
│   ├── templates/                  # Jinja2 templates
│   │   ├── components/             # Reusable UI components
│   │   ├── layouts/                # Page layouts
│   ├── utils/                      # Utility functions
│   ├── views/                      # Web view handlers
├── migrations/                     # Alembic migrations
├── scripts/                        # Management scripts
│   ├── manage_db.py                # Database management CLI
├── tests/                          # Test suite
│   ├── test_environment.py         # Testing environment setup
│   ├── conftest.py                 # Test fixtures


### Improvement Approach
- Keyword: "Incrementally improve"
- Maintain existing module interfaces
- Ensure consumer modules remain unaffected
- Explicitly highlight potential impacts

### Error Handling
- Fix ONLY the specific error
- No bundled improvements or refactoring
- Modify only error-related lines
- Provide minimal, targeted solutions

### Context and Understanding
- Carefully review all provided modules in attachments or in Project knowledge area
- Ask for clarification if context is unclear
- Verify project structure before suggesting changes
- Reference attached modules in recommendations
- Please dont assume variables names, routes, methods in other artifacts  
- Please ask if you do not find in attached documents or Project kknowledge

### Problem-Solving Method
1. Understand current implementation
2. Identify precise issue
3. Propose minimal solution
4. Explain rationale
5. Highlight potential consequences

### Key Guiding Phrases
- "Incrementally improve"
- "Maintain existing structure"
- "Backward compatible enhancement"

### Important Considerations
- Prioritize existing code integrity
- Minimize disruption to current system
- Provide clear, step-by-step explanations
- Offer multiple perspectives when appropriate

Ready to collaborate on enhancing the Skinspire Clinic Hospital Management System?