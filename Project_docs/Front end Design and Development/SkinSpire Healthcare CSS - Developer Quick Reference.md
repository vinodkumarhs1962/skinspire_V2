# SkinSpire Healthcare CSS - Developer Quick Reference

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