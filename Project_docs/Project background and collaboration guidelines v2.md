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

# SQLAlchemy Detached Entity Quick Reference Guide

## Identifying Detached Entity Errors

### Common Error Patterns
- `DetachedInstanceError: Instance <Model at 0x...> is not bound to a Session`
- Accessing lazy-loaded attributes after a session closes
- Errors occurring in assertions after `with get_db_session()` blocks

### Root Causes
- Accessing entity attributes after its session is closed
- Returning entities from functions where sessions are locally scoped
- Using entities across requests or transactions
- Storing entity objects for later use

## Quick Solutions

### 1. Entity Lifecycle Helper Functions

```python
# In database_service.py
def get_detached_copy(entity):
    """Create safe detached copy of entity"""
    if entity is None:
        return None
    EntityClass = entity.__class__
    detached = EntityClass()
    for key, value in entity.__dict__.items():
        if not key.startswith('_'):
            setattr(detached, key, value)
    return detached

def get_entity_dict(entity):
    """Convert entity to dictionary"""
    if entity is None:
        return None
    return {
        key: value for key, value in entity.__dict__.items()
        if not key.startswith('_')
    }
```

### 2. Test Fixture Pattern

```python
@pytest.fixture
def test_entity(db_session):
    entity = Entity(...)
    db_session.add(entity)
    db_session.flush()
    
    # Safe copy for use after session closes
    detached_copy = get_detached_copy(entity)
    
    yield detached_copy
```

### 3. Primitive Value Extraction

```python
def get_user_info(user_id):
    with get_db_session() as session:
        user = session.query(User).filter_by(id=user_id).first()
        # Extract primitives within session
        return {
            "id": user.id,
            "name": user.name,
            "status": user.status
        }
```

### 4. Eager Loading

```python
from sqlalchemy.orm import joinedload

with get_db_session() as session:
    user = session.query(User).options(
        joinedload(User.profile),
        joinedload(User.roles)
    ).filter_by(id=user_id).first()
    
    # Use data while session is active
```

## When to Use Each Approach

- **Detached Copy**: Test fixtures, simple entity snapshot needs
- **Entity Dictionary**: API responses, serialization cases
- **Primitive Extraction**: When only specific attributes are needed
- **Eager Loading**: Complex entity relationships that must be traversed

## Best Practices

1. Never access entities after session closure without proper handling
2. Use `get_detached_copy()` for test fixtures
3. Use `get_entity_dict()` for API responses
4. Extract needed values within the session context
5. For service functions that may be called with or without an active session:
   ```python
   def process_user(user_id, session=None):
       if session is not None:
           return _do_work(session, user_id)
       with get_db_session() as new_session:
           return _do_work(new_session, user_id)
   ```

## Common Patterns by Context

### Web Routes
```python
@app.route('/api/user/<user_id>')
def get_user(user_id):
    with get_db_session() as session:
        user = session.query(User).get(user_id)
        return jsonify(get_entity_dict(user))
```

### Test Fixtures
```python
@pytest.fixture
def test_user():
    with get_db_session() as session:
        user = create_user(session)
        return get_detached_copy(user)
```

### Service Functions
```python
def get_user_details(user_id):
    with get_db_session() as session:
        user = session.query(User).get(user_id)
        # Process within session context
        return process_user_data(user)
```

This guide provides a quick reference for identifying and fixing detached entity errors while maintaining your centralized database access philosophy.

Ready to collaborate on enhancing the Skinspire Clinic Hospital Management System?

# Skinspire Healthcare CSS - Developer Quick Reference

## 🚀 **Essential Component Classes**

### **Buttons (Color-Coded System)**
```html
<!-- Main Actions -->
<button class="btn-primary">Save Patient</button>
<button class="btn-success">Approve Treatment</button>

<!-- Navigation -->
<button class="btn-secondary">View Records</button>
<button class="btn-outline">Filter Results</button>

<!-- Warnings & Destructive -->
<button class="btn-warning">Edit Record</button>
<button class="btn-danger">Delete Patient</button>

<!-- Sizes -->
<button class="btn-primary btn-sm">Quick Action</button>
<button class="btn-primary btn-lg">Primary CTA</button>
<button class="btn-primary btn-icon-only"><i class="fas fa-save"></i></button>
```

### **Forms (Essential Patterns)**
```html
<!-- Basic Form Group -->
<div class="form-group">
    <label class="form-label required">Patient Name</label>
    <input type="text" class="form-input" placeholder="Enter name">
    <span class="form-help">Enter legal name as on ID</span>
</div>

<!-- Form Grid Layout -->
<div class="form-grid form-grid-cols-2">
    <div class="form-group">...</div>
    <div class="form-group">...</div>
</div>

<!-- Autocomplete -->
<div class="autocomplete-container">
    <input type="text" class="form-input" placeholder="Search...">
    <div class="autocomplete-results">
        <div class="autocomplete-result">Option 1</div>
    </div>
</div>

<!-- File Upload -->
<div class="file-input-container">
    <input type="file" class="file-input" multiple>
    <div class="file-input-icon"><i class="fas fa-upload"></i></div>
    <div class="file-input-text">Drop files here</div>
</div>
```

### **Status & Alerts**
```html
<!-- Status Badges -->
<span class="status-badge status-active">Active</span>
<span class="status-badge status-pending">Pending</span>
<span class="status-badge status-cancelled">Cancelled</span>

<!-- Alerts -->
<div class="alert alert-success">
    <i class="fas fa-check-circle alert-icon"></i>
    <div class="alert-content">
        <div class="alert-title">Success!</div>
        <div class="alert-message">Patient saved successfully.</div>
    </div>
</div>

<!-- Loading States -->
<div class="loading-text">
    <span class="loading-spinner"></span>
    Loading patient records...
</div>
```

### **Filter Cards**
```html
<div class="filter-card">
    <div class="filter-card-header">
        <h3 class="filter-card-title">
            <i class="fas fa-filter icon-left"></i>Filters
        </h3>
    </div>
    <div class="filter-card-body">
        <!-- Quick Filters -->
        <div class="quick-filters">
            <button class="quick-filter active">Today</button>
            <button class="quick-filter">This Week</button>
        </div>
        
        <!-- Filter Grid -->
        <div class="filter-grid filter-grid-cols-3">
            <div class="form-group">...</div>
        </div>
        
        <!-- Actions -->
        <div class="filter-actions">
            <button class="btn-primary">Apply</button>
            <button class="btn-secondary">Reset</button>
        </div>
    </div>
</div>
```

### **Cards & Data Display**
```html
<!-- Stat Card -->
<div class="stat-card">
    <div class="stat-card-icon primary">
        <i class="fas fa-users"></i>
    </div>
    <div class="stat-card-value">247</div>
    <div class="stat-card-label">Active Patients</div>
</div>

<!-- Patient Card -->
<div class="patient-card critical">
    <div class="patient-card-name">John Doe</div>
    <div class="patient-card-id">PAT-001</div>
    <span class="medical-status critical">Critical</span>
</div>

<!-- Card Grid -->
<div class="card-grid cols-3">
    <div class="stat-card">...</div>
    <div class="patient-card">...</div>
</div>
```

### **Data Tables**
```html
<div class="table-container">
    <table class="data-table">
        <thead>
            <tr>
                <th class="sortable-header">Name</th>
                <th class="text-center">Status</th>
                <th class="action-column">Actions</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>John Doe</td>
                <td class="text-center">
                    <span class="status-badge status-active">Active</span>
                </td>
                <td class="action-column">
                    <div class="action-buttons">
                        <a href="/view" class="action-link"><i class="fas fa-eye"></i></a>
                        <a href="/edit" class="action-link edit"><i class="fas fa-edit"></i></a>
                    </div>
                </td>
            </tr>
        </tbody>
    </table>
</div>
```

---

## 🎨 **Color System**

### **Button Colors (Semantic)**
- **Blue (`btn-primary`)** → Save, Create, Submit, Main Actions
- **Indigo (`btn-secondary`)** → Navigate, Back, View, Lists  
- **Gray (`btn-outline`)** → Filters, Download, Print, Utilities
- **Orange (`btn-warning`)** → Edit, Modify, Update
- **Red (`btn-danger`)** → Delete, Cancel, Remove
- **Green (`btn-success`)** → Approve, Confirm, Payment

### **Status Colors**
- **Green** → Active, Approved, Paid, Completed, Stable
- **Yellow** → Pending, Partial, Processing, In Progress
- **Red** → Inactive, Cancelled, Unpaid, Critical, Failed
- **Blue** → Info, New, Scheduled
- **Gray** → Draft, Unknown, Disabled

---

## 📱 **Responsive Classes**

### **Grid Layouts**
```html
<!-- Form Grids -->
<div class="form-grid form-grid-cols-2">   <!-- 2 cols on desktop, 1 on mobile -->
<div class="form-grid form-grid-cols-3">   <!-- 3 cols on desktop, 1 on mobile -->
<div class="form-grid form-grid-cols-4">   <!-- 4 cols on desktop, 2 on tablet -->

<!-- Card Grids -->
<div class="card-grid cols-2">             <!-- 2 cols on desktop, 1 on mobile -->
<div class="card-grid cols-4">             <!-- 4 cols on desktop, 1 on mobile -->

<!-- Filter Grids -->
<div class="filter-grid filter-grid-cols-3"> <!-- Auto-responsive -->
```

### **Responsive Utilities**
```html
<td class="hidden-mobile">Phone</td>       <!-- Hide on mobile -->
<td class="hidden-tablet">Email</td>       <!-- Hide on tablet -->
```

---

## 🏥 **Healthcare-Specific Components**

### **Medical Status**
```html
<!-- Patient Priority -->
<span class="priority-indicator priority-critical"></span>
<span class="medical-status critical">Critical</span>

<!-- Vital Signs -->
<div class="vital-signs-group">
    <div class="form-group">
        <label class="form-label">BP</label>
        <input type="text" class="form-input" placeholder="120/80">
    </div>
</div>
```

### **Medical Forms**
```html
<!-- Medical History Section -->
<div class="medical-history-section">
    <h3 class="medical-history-title">
        <i class="fas fa-notes-medical"></i>Medical History
    </h3>
    <!-- Content -->
</div>

<!-- Medication Item -->
<div class="medication-item">
    <div>
        <div class="medication-name">Lisinopril 10mg</div>
        <div class="medication-details">Once daily</div>
    </div>
    <button class="medication-remove">Remove</button>
</div>

<!-- HIPAA Notice -->
<div class="hipaa-notice">
    <i class="fas fa-shield-alt hipaa-notice-icon"></i>
    <div class="hipaa-notice-text">HIPAA compliant form</div>
</div>
```

### **Multi-Step Forms**
```html
<div class="form-steps">
    <div class="form-step completed">
        <div class="form-step-number">1</div>
        <div class="form-step-label">Personal Info</div>
    </div>
    <div class="form-step active">
        <div class="form-step-number">2</div>
        <div class="form-step-label">Medical History</div>
    </div>
</div>
```

---

## ⚡ **Common Patterns**

### **Page Layout Template**
```html
<div class="container mx-auto px-4 py-6">
    <!-- Page Header -->
    <div class="flex justify-between items-center mb-6">
        <h1 class="text-2xl font-bold">Page Title</h1>
        <div class="space-x-2">
            <button class="btn-secondary">Secondary Action</button>
            <button class="btn-primary">Primary Action</button>
        </div>
    </div>
    
    <!-- Filters -->
    <div class="filter-card">...</div>
    
    <!-- Content -->
    <div class="info-card">
        <!-- Table or Cards -->
    </div>
    
    <!-- Footer Actions -->
    <div class="footer-actions">
        <button class="btn-secondary">Cancel</button>
        <button class="btn-primary">Save</button>
    </div>
</div>
```

### **Form Section Template**
```html
<form class="space-y-6">
    <!-- Section 1 -->
    <div class="medical-history-section">
        <h3 class="medical-history-title">Section Title</h3>
        <div class="form-grid form-grid-cols-2">
            <!-- Form fields -->
        </div>
    </div>
    
    <!-- Section Divider -->
    <hr class="form-section-divider">
    
    <!-- Section 2 -->
    <div class="insurance-card">
        <!-- Insurance fields -->
    </div>
    
    <!-- Actions -->
    <div class="footer-actions">
        <button type="button" class="btn-secondary">Cancel</button>
        <button type="submit" class="btn-primary">Save</button>
    </div>
</form>
```

### **List Page Template**
```html
<!-- Summary Cards -->
<div class="card-grid cols-4 mb-6">
    <div class="stat-card">...</div>
</div>

<!-- Filters -->
<div class="filter-card mb-6">...</div>

<!-- Data Table -->
<div class="info-card">
    <div class="table-container">
        <table class="data-table">...</table>
    </div>
</div>
```

---

## 🔍 **Troubleshooting**

### **Common Issues**
```css
/* Fix: Icons not showing */
.fas, .far { font-family: "Font Awesome 5 Free" !important; }

/* Fix: Button spacing */
.btn-primary .icon-left { margin-right: 0.5rem !important; }

/* Fix: Table overflow */
.table-container { overflow-x: auto !important; }

/* Fix: Form validation */
.form-input.error { border-color: rgb(239 68 68) !important; }
```

### **Dark Mode Classes**
```html
<!-- Most components have built-in dark mode -->
<div class="info-card">       <!-- Auto dark mode -->
<button class="btn-primary">  <!-- Auto dark mode -->

<!-- Manual dark mode -->
<div class="dark:bg-gray-800">...</div>
```

---

## 📋 **Checklist for New Templates**

### **✅ Before You Start**
- [ ] Import app.css in your template
- [ ] Include FontAwesome for icons
- [ ] Plan your page layout (header, filters, content, footer)

### **✅ Form Development**
- [ ] Use `form-group` for all form fields
- [ ] Add `required` class to required labels
- [ ] Include `form-help` for guidance text
- [ ] Use appropriate input types (autocomplete, file, date)
- [ ] Group related fields with `form-grid`

### **✅ Data Display**
- [ ] Use `status-badge` for all status indicators
- [ ] Apply color-coded buttons consistently
- [ ] Include `action-buttons` for table actions
- [ ] Add loading states with `loading-spinner`
- [ ] Use appropriate card types for content

### **✅ Responsive Design**
- [ ] Test on mobile, tablet, and desktop
- [ ] Use responsive grid classes
- [ ] Hide non-essential columns on mobile
- [ ] Ensure touch-friendly button sizes

### **✅ Accessibility**
- [ ] Add proper ARIA labels
- [ ] Ensure keyboard navigation works
- [ ] Test with screen readers
- [ ] Maintain color contrast ratios

### **✅ Healthcare Standards**
- [ ] Include HIPAA notices where appropriate
- [ ] Use medical status indicators consistently
- [ ] Implement proper patient identification
- [ ] Add audit trail information

---

## 🎯 **Quick CSS Customization**

### **CSS Variables (Available)**
```css
:root {
    --healthcare-primary: rgb(59 130 246);    /* Blue */
    --healthcare-secondary: rgb(99 102 241);  /* Indigo */
    --healthcare-success: rgb(34 197 94);     /* Green */
    --healthcare-warning: rgb(245 158 11);    /* Amber */
    --healthcare-danger: rgb(239 68 68);      /* Red */
}
```

### **Custom Component Override**
```css
/* Override in your template styles */
.my-custom-card {
    @apply info-card;
    /* Add custom styles */
    border-left: 4px solid var(--healthcare-primary);
}
```

---

**Remember: Use components first, customize only when necessary!** 

For complex requirements, extend existing components rather than creating new CSS from scratch. This maintains consistency and reduces maintenance overhead.

**Happy coding!** 🚀