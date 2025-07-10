# HTML Template Development Guide - Centralized CSS Styling

## Overview
This guide provides standards for developing HTML templates that adhere to centralized CSS styling using Tailwind's @apply directives for a Hospital Management System.

## Core Design Principles

### 1. Modular Component-Based Architecture
- Create reusable components for common UI elements
- Maintain consistent styling across all modules
- Use semantic HTML structure
- Implement responsive design patterns

### 2. Centralized Styling Structure
```css
/* styles.css - Main stylesheet using Tailwind @apply directives */

/* Base Components */
.btn-primary {
    @apply bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg 
           transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500;
}

.btn-secondary {
    @apply bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-2 px-4 rounded-lg 
           border border-gray-300 transition-colors duration-200;
}

.btn-danger {
    @apply bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-4 rounded-lg 
           transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-red-500;
}
```

## Color Coding System

### Medical/Healthcare Color Palette
```css
:root {
    /* Primary Colors */
    --color-medical-blue: #2563eb;      /* Primary actions, links */
    --color-medical-green: #059669;     /* Success, available */
    --color-medical-red: #dc2626;       /* Emergency, danger */
    --color-medical-orange: #ea580c;    /* Warnings, pending */
    
    /* Secondary Colors */
    --color-light-blue: #dbeafe;        /* Backgrounds, info */
    --color-light-green: #dcfce7;       /* Success backgrounds */
    --color-light-red: #fee2e2;         /* Error backgrounds */
    --color-light-orange: #fed7aa;      /* Warning backgrounds */
    
    /* Neutral Colors */
    --color-gray-50: #f9fafb;           /* Page backgrounds */
    --color-gray-100: #f3f4f6;          /* Card backgrounds */
    --color-gray-200: #e5e7eb;          /* Borders */
    --color-gray-600: #4b5563;          /* Secondary text */
    --color-gray-900: #111827;          /* Primary text */
}
```

### Status Color Coding
```css
/* Status Indicators */
.status-active { @apply bg-green-100 text-green-800 border-green-200; }
.status-pending { @apply bg-yellow-100 text-yellow-800 border-yellow-200; }
.status-inactive { @apply bg-gray-100 text-gray-800 border-gray-200; }
.status-emergency { @apply bg-red-100 text-red-800 border-red-200; }
.status-completed { @apply bg-blue-100 text-blue-800 border-blue-200; }
```

## Standard Component Classes

### 1. Layout Components
```css
/* Page Layout */
.page-container {
    @apply min-h-screen bg-gray-50;
}

.content-wrapper {
    @apply max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6;
}

.page-header {
    @apply bg-white shadow-sm border-b border-gray-200 mb-6;
}

.page-title {
    @apply text-2xl font-semibold text-gray-900 py-4;
}
```

### 2. Card Components
```css
.card {
    @apply bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden;
}

.card-header {
    @apply bg-gray-50 px-6 py-4 border-b border-gray-200;
}

.card-title {
    @apply text-lg font-medium text-gray-900;
}

.card-body {
    @apply p-6;
}
```

### 3. Form Components
```css
.form-group {
    @apply mb-4;
}

.form-label {
    @apply block text-sm font-medium text-gray-700 mb-2;
}

.form-input {
    @apply w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none 
           focus:ring-2 focus:ring-blue-500 focus:border-transparent;
}

.form-select {
    @apply w-full px-3 py-2 border border-gray-300 rounded-lg bg-white 
           focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent;
}

.form-error {
    @apply text-sm text-red-600 mt-1;
}
```

### 4. Table Components
```css
.table-container {
    @apply overflow-x-auto shadow-sm border border-gray-200 rounded-lg;
}

.table {
    @apply min-w-full divide-y divide-gray-200;
}

.table-header {
    @apply bg-gray-50;
}

.table-header-cell {
    @apply px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider;
}

.table-row {
    @apply bg-white hover:bg-gray-50 transition-colors duration-150;
}

.table-cell {
    @apply px-6 py-4 whitespace-nowrap text-sm text-gray-900;
}
```

### 5. Button Variations
```css
.btn-group {
    @apply flex space-x-2;
}

.btn-sm {
    @apply py-1 px-3 text-sm;
}

.btn-lg {
    @apply py-3 px-6 text-lg;
}

.btn-icon {
    @apply p-2 rounded-lg;
}
```

### 6. Navigation Components
```css
.nav-tabs {
    @apply flex border-b border-gray-200;
}

.nav-tab {
    @apply px-4 py-2 text-sm font-medium text-gray-500 hover:text-gray-700 
           border-b-2 border-transparent hover:border-gray-300;
}

.nav-tab-active {
    @apply text-blue-600 border-blue-600;
}
```

## Template Structure Standards

### Base Template Structure
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Hospital Management System{% endblock %}</title>
    <link href="{{ url_for('static', filename='css/styles.css') }}" rel="stylesheet">
</head>
<body class="page-container">
    <!-- Navigation -->
    <nav class="navbar">
        {% include 'partials/navigation.html' %}
    </nav>
    
    <!-- Main Content -->
    <main class="content-wrapper">
        {% block content %}{% endblock %}
    </main>
    
    <!-- Footer -->
    <footer class="footer">
        {% include 'partials/footer.html' %}
    </footer>
    
    <script src="{{ url_for('static', filename='js/app.js') }}"></script>
</body>
</html>
```

### Standard Page Layout
```html
{% extends "base.html" %}

{% block content %}
<div class="page-header">
    <div class="flex justify-between items-center">
        <h1 class="page-title">{{ page_title }}</h1>
        <div class="btn-group">
            {% block header_actions %}{% endblock %}
        </div>
    </div>
</div>

<div class="card">
    <div class="card-header">
        <h2 class="card-title">{{ card_title }}</h2>
    </div>
    <div class="card-body">
        {% block card_content %}{% endblock %}
    </div>
</div>
{% endblock %}
```

## Form Standards

### Standard Form Layout
```html
<form method="POST" class="space-y-6">
    {{ csrf_token() }}
    
    <div class="form-group">
        <label for="field_name" class="form-label">Field Label *</label>
        <input type="text" id="field_name" name="field_name" class="form-input" required>
        {% if errors.field_name %}
            <p class="form-error">{{ errors.field_name[0] }}</p>
        {% endif %}
    </div>
    
    <div class="btn-group">
        <button type="submit" class="btn-primary">Save</button>
        <a href="{{ url_for('module.list') }}" class="btn-secondary">Cancel</a>
    </div>
</form>
```

## List/Table Standards

### Standard Data Table
```html
<div class="table-container">
    <table class="table">
        <thead class="table-header">
            <tr>
                <th class="table-header-cell">Column 1</th>
                <th class="table-header-cell">Column 2</th>
                <th class="table-header-cell">Actions</th>
            </tr>
        </thead>
        <tbody class="divide-y divide-gray-200">
            {% for item in items %}
            <tr class="table-row">
                <td class="table-cell">{{ item.field1 }}</td>
                <td class="table-cell">{{ item.field2 }}</td>
                <td class="table-cell">
                    <div class="btn-group">
                        <a href="{{ url_for('module.view', id=item.id) }}" class="btn-sm btn-secondary">View</a>
                        <a href="{{ url_for('module.edit', id=item.id) }}" class="btn-sm btn-primary">Edit</a>
                    </div>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</div>
```

## Icon Standards

### Icon Usage Guidelines
```html
<!-- Use consistent icon library (e.g., Heroicons, Feather Icons) -->
<button class="btn-primary">
    <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
    </svg>
    Add New
</button>
```

## Responsive Design Guidelines

### Responsive Breakpoints
```css
/* Mobile First Approach */
.responsive-grid {
    @apply grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4;
}

.responsive-table {
    @apply block md:table;
}

.mobile-stack {
    @apply flex flex-col space-y-2 md:flex-row md:space-y-0 md:space-x-2;
}
```

## Print Styles

### Print-Specific Classes
```css
@media print {
    .print-hide { display: none !important; }
    .print-show { display: block !important; }
    .print-page-break { page-break-before: always; }
}
```

## Accessibility Standards

### ARIA and Semantic HTML
```html
<!-- Always include proper labels and ARIA attributes -->
<button class="btn-primary" aria-label="Add new patient">
    <span aria-hidden="true">+</span>
    Add Patient
</button>

<!-- Use semantic HTML -->
<section aria-labelledby="section-title">
    <h2 id="section-title">Patient Information</h2>
    <!-- content -->
</section>
```

## Implementation Checklist

### For Each New Template:
- [ ] Extends base template
- [ ] Uses centralized CSS classes
- [ ] Implements responsive design
- [ ] Includes proper form validation
- [ ] Uses semantic HTML
- [ ] Implements accessibility features
- [ ] Includes print styles where needed
- [ ] Uses consistent color coding
- [ ] Implements proper error handling
- [ ] Includes CSRF protection

### Code Review Standards:
- [ ] No inline styles
- [ ] Consistent class naming
- [ ] Proper component hierarchy
- [ ] Mobile responsiveness tested
- [ ] Cross-browser compatibility
- [ ] Performance optimized
- [ ] Security best practices followed