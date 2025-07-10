<!-- =============================================================================
UNIVERSAL TEMPLATES - INTEGRATED WITH EXISTING TEMPLATE STRUCTURE
Following SkinSpire HMS Existing Template Patterns
============================================================================= -->

<!-- =============================================================================
FILE: app/templates/pages/universal/entity_list.html
PURPOSE: Universal entity list page following your existing page template patterns
============================================================================= -->

{% extends "layouts/dashboard.html" %}  {# Your existing dashboard layout #}

{% block page_title %}{{ config.plural_name }}{% endblock %}

{% block content %}
<div class="page-container">  {# Following your existing page container pattern #}
    
    <!-- Page Header - Following your existing header pattern -->
    <div class="page-header flex justify-between items-center mb-6">
        <div class="flex items-center space-x-3">
            <i class="{{ config.icon }} text-2xl text-blue-600"></i>
            <h1 class="text-3xl font-bold text-gray-900 dark:text-white">{{ config.plural_name }}</h1>
        </div>
        
        <!-- Action Buttons - Using your existing button styles -->
        <div class="flex space-x-2">
            <button type="button" class="btn btn-outline" onclick="exportData()">
                <i class="fas fa-download"></i> Export
            </button>
            {% if has_permission(current_user, config.permissions.module_name, config.permissions.create_permission) %}
            <a href="{{ url_for('universal.entity_create', entity_type=config.entity_type.value) }}" 
               class="btn btn-primary">
                <i class="fas fa-plus"></i> Add {{ config.name }}
            </a>
            {% endif %}
        </div>
    </div>

    <!-- Universal Search Component - Uses your existing component structure -->
    {% include 'components/universal/entity_search.html' %}

    <!-- Results Summary - Following your existing info display pattern -->
    <div class="results-summary mb-4 flex justify-between items-center">
        <div class="text-sm text-gray-600 dark:text-gray-400">
            Showing {{ pagination.page }} of {{ pagination.pages }} pages 
            ({{ pagination.total }} total {{ config.plural_name.lower() }})
        </div>
        
        <!-- View Controls - Using your existing control patterns -->
        <div class="flex items-center space-x-4">
            <div class="view-mode-selector">
                <button class="btn btn-sm {% if request.args.get('view_mode', 'table') == 'table' %}btn-primary{% else %}btn-outline{% endif %}" 
                        onclick="setViewMode('table')">
                    <i class="fas fa-table"></i>
                </button>
                <button class="btn btn-sm {% if request.args.get('view_mode') == 'card' %}btn-primary{% else %}btn-outline{% endif %}" 
                        onclick="setViewMode('card')">
                    <i class="fas fa-th"></i>
                </button>
            </div>
            
            <!-- Per Page Selector - Using your existing form styles -->
            <select name="per_page" class="form-select form-select-sm" onchange="changePerPage(this.value)">
                <option value="25" {% if pagination.per_page == 25 %}selected{% endif %}>25</option>
                <option value="50" {% if pagination.per_page == 50 %}selected{% endif %}>50</option>
                <option value="100" {% if pagination.per_page == 100 %}selected{% endif %}>100</option>
            </select>
        </div>
    </div>

    <!-- Summary Statistics - Using your existing card styles -->
    {% if summary_stats and config.display.show_summary_stats %}
    <div class="summary-cards mb-6">
        {% include 'components/universal/summary_stats.html' %}
    </div>
    {% endif %}

    <!-- Universal List Display - Following your existing component pattern -->
    <div class="list-container">
        {% if request.args.get('view_mode') == 'card' %}
            {% include 'components/universal/entity_cards.html' %}
        {% else %}
            {% include 'components/universal/entity_table.html' %}
        {% endif %}
    </div>

    <!-- Pagination - Using your existing pagination component -->
    {% if pagination.pages > 1 %}
    <div class="pagination-container mt-6">
        {% include 'components/universal/entity_pagination.html' %}
    </div>
    {% endif %}
</div>

<!-- Universal JavaScript - Following your existing JS organization -->
<script src="{{ url_for('static', filename='js/components/universal-search.js') }}"></script>
<script src="{{ url_for('static', filename='js/components/universal-actions.js') }}"></script>
{% endblock %}

<!-- =============================================================================
FILE: app/templates/components/universal/entity_search.html
PURPOSE: Universal search component following your existing component patterns
============================================================================= -->

<div class="search-card bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-6">  {# Your existing card styles #}
    <form method="GET" action="" class="space-y-4">  {# Your existing form spacing #}
        
        <!-- Quick Search Row -->
        <div class="grid grid-cols-1 lg:grid-cols-4 gap-4">
            
            <!-- Main Search Input - Using your existing form input styles -->
            <div class="lg:col-span-2">
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Quick Search
                </label>
                <div class="relative">
                    <input type="text" 
                           name="search" 
                           value="{{ request.args.get('search', '') }}"
                           placeholder="Search {{ config.default_search_fields|join(', ') }}..."
                           class="form-input pr-10">  {# Your existing form-input class #}
                    <div class="absolute inset-y-0 right-0 pr-3 flex items-center">
                        <i class="fas fa-search text-gray-400"></i>
                    </div>
                </div>
            </div>

            <!-- Date Filter - Following your existing date input pattern -->
            {% set date_fields = config.fields|selectattr('field_type', 'equalto', 'date')|selectattr('filterable')|list %}
            {% if date_fields %}
            <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Date Range
                </label>
                <select name="date_preset" class="form-select" onchange="handleDatePreset(this.value)">
                    <option value="">All Dates</option>
                    <option value="today" {% if request.args.get('date_preset') == 'today' %}selected{% endif %}>Today</option>
                    <option value="this_week" {% if request.args.get('date_preset') == 'this_week' %}selected{% endif %}>This Week</option>
                    <option value="this_month" {% if request.args.get('date_preset') == 'this_month' %}selected{% endif %}>This Month</option>
                    <option value="custom" {% if request.args.get('date_preset') == 'custom' %}selected{% endif %}>Custom Range</option>
                </select>
            </div>
            {% endif %}

            <!-- Primary Status Filter - Using your existing select styles -->
            {% set status_fields = config.fields|selectattr('field_type', 'equalto', 'status_badge')|selectattr('filterable')|list %}
            {% if status_fields %}
            {% set status_field = status_fields[0] %}
            <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    {{ status_field.label }}
                </label>
                <select name="{{ status_field.name }}" class="form-select">
                    <option value="">All {{ status_field.label }}</option>
                    {% for option in status_field.options %}
                    <option value="{{ option.value }}" 
                            {% if request.args.get(status_field.name) == option.value %}selected{% endif %}>
                        {{ option.label }}
                    </option>
                    {% endfor %}
                </select>
            </div>
            {% endif %}
        </div>

        <!-- Advanced Filters (Collapsible) - Following your existing collapsible pattern -->
        <div class="advanced-filters" id="advancedFilters" style="display: none;">
            <div class="border-t pt-4 mt-4">
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    
                    <!-- Dynamic Filter Fields -->
                    {% for field in config.fields %}
                    {% if field.filterable and field.field_type not in ['date', 'status_badge'] %}
                    <div>
                        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                            {{ field.label }}
                        </label>
                        
                        {% if field.field_type == 'select' %}
                        <select name="{{ field.name }}" class="form-select">
                            <option value="">All {{ field.label }}</option>
                            {% for option in field.options %}
                            <option value="{{ option.value }}" 
                                    {% if request.args.get(field.name) == option.value %}selected{% endif %}>
                                {{ option.label }}
                            </option>
                            {% endfor %}
                        </select>
                        
                        {% elif field.field_type == 'foreign_key' %}
                        <select name="{{ field.name }}" class="form-select" data-entity="{{ field.related_entity }}">
                            <option value="">All {{ field.label }}</option>
                            <!-- Options loaded dynamically based on related entity -->
                        </select>
                        
                        {% else %}
                        <input type="text" 
                               name="{{ field.name }}" 
                               value="{{ request.args.get(field.name, '') }}"
                               placeholder="Filter by {{ field.label.lower() }}"
                               class="form-input">
                        {% endif %}
                    </div>
                    {% endif %}
                    {% endfor %}
                </div>
            </div>
        </div>

        <!-- Action Buttons - Using your existing button styles -->
        <div class="flex justify-between items-center">
            <div class="flex space-x-2">
                <button type="submit" class="btn btn-primary">
                    <i class="fas fa-search"></i> Search
                </button>
                <button type="button" onclick="clearFilters()" class="btn btn-outline">
                    <i class="fas fa-times"></i> Clear
                </button>
                <button type="button" onclick="toggleAdvancedFilters()" class="btn btn-outline">
                    <i class="fas fa-filter"></i> Advanced
                </button>
            </div>
            
            <!-- Active Filter Chips - Following your existing badge pattern -->
            <div class="active-filters flex flex-wrap gap-2">
                {% for key, value in request.args.items() %}
                {% if value and key not in ['page', 'per_page', 'view_mode'] %}
                <span class="badge badge-info">  {# Your existing badge class #}
                    {{ key }}: {{ value }}
                    <button type="button" onclick="removeFilter('{{ key }}')" class="ml-1 text-xs">×</button>
                </span>
                {% endif %}
                {% endfor %}
            </div>
        </div>
    </form>
</div>

<!-- =============================================================================
FILE: app/templates/components/universal/entity_table.html
PURPOSE: Universal table component following your existing table patterns
============================================================================= -->

<div class="table-container bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">  {# Your existing table container #}
    {% if items %}
    <div class="overflow-x-auto">
        <table class="table table-auto w-full">  {# Your existing table classes #}
            
            <!-- Table Header - Following your existing table header pattern -->
            <thead class="bg-gray-50 dark:bg-gray-700">
                <tr>
                    {% for field in list_fields %}
                    <th class="table-header {% if field.sortable %}sortable cursor-pointer{% endif %}"
                        {% if field.sortable %}onclick="sortBy('{{ field.name }}')"{% endif %}>
                        <div class="flex items-center space-x-2">
                            <span>{{ field.label }}</span>
                            {% if field.sortable %}
                            <i class="fas fa-sort text-gray-400 text-xs"></i>
                            {% endif %}
                        </div>
                    </th>
                    {% endfor %}
                    
                    <!-- Actions Column -->
                    {% if actions %}
                    <th class="table-header text-center">Actions</th>
                    {% endif %}
                </tr>
            </thead>
            
            <!-- Table Body -->
            <tbody class="divide-y divide-gray-200 dark:divide-gray-600">
                {% for item in items %}
                <tr class="table-row hover:bg-gray-50 dark:hover:bg-gray-700">  {# Your existing table row classes #}
                    
                    <!-- Dynamic Field Columns -->
                    {% for field in list_fields %}
                    <td class="table-cell">  {# Your existing table cell class #}
                        {% include 'components/universal/field_renderers.html' %}
                    </td>
                    {% endfor %}
                    
                    <!-- Actions Column -->
                    {% if actions %}
                    <td class="table-cell text-center">
                        <div class="action-buttons flex justify-center space-x-2">
                            {% for action in actions %}
                            {% include 'components/universal/action_button.html' %}
                            {% endfor %}
                        </div>
                    </td>
                    {% endif %}
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% else %}
    <!-- Empty State - Following your existing empty state pattern -->
    <div class="empty-state text-center py-12">
        <i class="{{ config.icon }} text-4xl text-gray-400 mb-4"></i>
        <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">No {{ config.plural_name }} Found</h3>
        <p class="text-gray-500 dark:text-gray-400 mb-4">
            Try adjusting your search criteria or add a new {{ config.name.lower() }}.
        </p>
        {% if has_permission(current_user, config.permissions.module_name, config.permissions.create_permission) %}
        <a href="{{ url_for('universal.entity_create', entity_type=config.entity_type.value) }}" 
           class="btn btn-primary">
            <i class="fas fa-plus"></i> Add {{ config.name }}
        </a>
        {% endif %}
    </div>
    {% endif %}
</div>

<!-- =============================================================================
FILE: app/templates/components/universal/field_renderers.html
PURPOSE: Universal field rendering following your existing field display patterns
============================================================================= -->

{% set field_value = item.get(field.name, '') %}

{% if field.field_type == 'text' %}
    <span class="text-sm text-gray-900 dark:text-gray-100">
        {{ field_value|truncate(50, true) if field_value else '-' }}
    </span>

{% elif field.field_type == 'patient_mrn' %}
    <div class="mrn-display">
        <span class="font-mono text-sm font-medium text-blue-600">{{ field_value }}</span>
    </div>

{% elif field.field_type == 'gst_number' %}
    <div class="gst-display">
        <span class="font-mono text-sm text-gray-900 dark:text-gray-100">{{ field_value }}</span>
    </div>

{% elif field.field_type == 'invoice_number' %}
    <div class="invoice-number">
        <span class="font-medium text-sm text-gray-900 dark:text-gray-100">{{ field_value }}</span>
    </div>

{% elif field.field_type == 'date' %}
    <span class="text-sm text-gray-900 dark:text-gray-100">
        {{ field_value|strftime('%Y-%m-%d') if field_value else '-' }}
    </span>

{% elif field.field_type == 'datetime' %}
    <span class="text-sm text-gray-900 dark:text-gray-100">
        {{ field_value|strftime('%Y-%m-%d %H:%M') if field_value else '-' }}
    </span>

{% elif field.field_type == 'amount' %}
    <div class="amount-display text-right">
        <span class="font-medium text-sm text-gray-900 dark:text-gray-100">
            ₹{{ "%.2f"|format(field_value|float) if field_value else '0.00' }}
        </span>
    </div>

{% elif field.field_type == 'status_badge' %}
    {% set status_option = field.options|selectattr('value', 'equalto', field_value)|first %}
    {% if status_option %}
    <span class="status-badge {{ status_option.class }}">  {# Your existing status badge classes #}
        {{ status_option.label }}
    </span>
    {% else %}
    <span class="status-badge status-default">{{ field_value }}</span>
    {% endif %}

{% elif field.field_type == 'boolean' %}
    {% if field_value %}
    <i class="fas fa-check-circle text-green-500"></i>
    {% else %}
    <i class="fas fa-times-circle text-red-500"></i>
    {% endif %}

{% elif field.field_type == 'foreign_key' %}
    <span class="text-sm text-gray-900 dark:text-gray-100">
        {{ item.get(field.name + '_display') or field_value or '-' }}
    </span>

{% elif field.field_type == 'phone' %}
    <div class="phone-display">
        <a href="tel:{{ field_value }}" class="text-blue-600 hover:text-blue-800 text-sm">
            {{ field_value }}
        </a>
    </div>

{% elif field.field_type == 'email' %}
    <div class="email-display">
        <a href="mailto:{{ field_value }}" class="text-blue-600 hover:text-blue-800 text-sm">
            {{ field_value|truncate(30, true) }}
        </a>
    </div>

{% else %}
    <!-- Default text rendering -->
    <span class="text-sm text-gray-900 dark:text-gray-100">
        {{ field_value|truncate(50, true) if field_value else '-' }}
    </span>

{% endif %}

<!-- =============================================================================
FILE: app/templates/components/universal/action_button.html  
PURPOSE: Universal action button following your existing button patterns
============================================================================= -->

{% if action.handler_type == 'standard' %}
    <!-- Standard CRUD actions -->
    {% if action.action_id == 'view' %}
    <a href="{{ url_for('universal.entity_view', entity_type=config.entity_type.value, id=item.get(config.primary_key)) }}" 
       class="btn btn-sm btn-outline" title="{{ action.label }}">
        <i class="{{ action.icon }}"></i>
    </a>
    
    {% elif action.action_id == 'edit' %}
    <a href="{{ url_for('universal.entity_edit', entity_type=config.entity_type.value, id=item.get(config.primary_key)) }}" 
       class="btn btn-sm btn-primary" title="{{ action.label }}">
        <i class="{{ action.icon }}"></i>
    </a>
    
    {% elif action.action_id == 'delete' %}
    <button type="button" 
            onclick="confirmDelete('{{ item.get(config.primary_key) }}')"
            class="btn btn-sm btn-danger" 
            title="{{ action.label }}">
        <i class="{{ action.icon }}"></i>
    </button>
    {% endif %}

{% elif action.handler_type == 'custom' %}
    <!-- Custom actions - delegate to entity-specific handlers -->
    {% if config.entity_type.value == 'supplier_invoices' %}
        {% if action.action_id == 'view' %}
        <a href="{{ url_for('supplier_views.view_supplier_invoice', invoice_id=item.get('invoice_id')) }}" 
           class="btn btn-sm btn-outline" title="View Invoice">
            <i class="{{ action.icon }}"></i>
        </a>
        
        {% elif action.action_id == 'payment' %}
        <a href="{{ url_for('supplier_views.record_payment', invoice_id=item.get('invoice_id')) }}" 
           class="btn btn-sm btn-success" title="Record Payment">
            <i class="{{ action.icon }}"></i>
        </a>
        {% endif %}
    
    {% elif config.entity_type.value == 'patients' %}
        {% if action.action_id == 'appointments' %}
        <a href="{{ url_for('patient_views.patient_appointments', patient_id=item.get('patient_id')) }}" 
           class="btn btn-sm btn-info" title="Appointments">
            <i class="{{ action.icon }}"></i>
        </a>
        
        {% elif action.action_id == 'billing' %}
        <a href="{{ url_for('patient_views.patient_billing', patient_id=item.get('patient_id')) }}" 
           class="btn btn-sm btn-warning" title="Billing History">
            <i class="{{ action.icon }}"></i>
        </a>
        {% endif %}
    
    {% else %}
        <!-- Fallback for unhandled custom actions -->
        <button type="button" 
                onclick="handleCustomAction('{{ action.action_id }}', '{{ item.get(config.primary_key) }}')"
                class="btn btn-sm {{ action.css_classes }}" 
                title="{{ action.label }}">
            <i class="{{ action.icon }}"></i>
        </button>
    {% endif %}

{% elif action.handler_type == 'ajax' %}
    <!-- AJAX actions -->
    <button type="button" 
            onclick="executeAjaxAction('{{ action.action_id }}', '{{ item.get(config.primary_key) }}')"
            class="btn btn-sm {{ action.css_classes }}" 
            title="{{ action.label }}"
            {% if action.confirmation_required %}
            data-confirm="{{ action.confirmation_message }}"
            {% endif %}>
        <i class="{{ action.icon }}"></i>
    </button>

{% endif %}

<!-- =============================================================================
FILE: app/templates/components/universal/entity_pagination.html
PURPOSE: Universal pagination following your existing pagination patterns  
============================================================================= -->

<div class="pagination-wrapper flex justify-between items-center">  {# Your existing pagination wrapper #}
    
    <!-- Page Info -->
    <div class="text-sm text-gray-600 dark:text-gray-400">
        Page {{ pagination.page }} of {{ pagination.pages }} 
        ({{ pagination.total }} total {{ config.plural_name.lower() }})
    </div>
    
    <!-- Pagination Controls - Using your existing pagination styles -->
    <nav class="pagination" aria-label="Pagination">
        {% if pagination.has_prev %}
        <a href="{{ url_for(request.endpoint, page=1, **request.args) }}" 
           class="pagination-btn" title="First Page">
            <i class="fas fa-angle-double-left"></i>
        </a>
        <a href="{{ url_for(request.endpoint, page=pagination.prev_num, **request.args) }}" 
           class="pagination-btn" title="Previous Page">
            <i class="fas fa-angle-left"></i>
        </a>
        {% endif %}
        
        <!-- Page Numbers -->
        {% for page_num in pagination.iter_pages() %}
        {% if page_num %}
        {% if page_num != pagination.page %}
        <a href="{{ url_for(request.endpoint, page=page_num, **request.args) }}" 
           class="pagination-btn">{{ page_num }}</a>
        {% else %}
        <span class="pagination-btn active">{{ page_num }}</span>
        {% endif %}
        {% else %}
        <span class="pagination-ellipsis">…</span>
        {% endif %}
        {% endfor %}
        
        {% if pagination.has_next %}
        <a href="{{ url_for(request.endpoint, page=pagination.next_num, **request.args) }}" 
           class="pagination-btn" title="Next Page">
            <i class="fas fa-angle-right"></i>
        </a>
        <a href="{{ url_for(request.endpoint, page=pagination.pages, **request.args) }}" 
           class="pagination-btn" title="Last Page">
            <i class="fas fa-angle-double-right"></i>
        </a>
        {% endif %}
    </nav>
</div>

<!-- =============================================================================
FILE: app/templates/components/universal/summary_stats.html
PURPOSE: Summary statistics component following your existing card patterns
============================================================================= -->

<div class="stats-grid grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
    
    <!-- Total Count Card -->
    <div class="stat-card bg-white dark:bg-gray-800 rounded-lg shadow p-6">  {# Your existing card styles #}
        <div class="flex items-center">
            <div class="flex-shrink-0">
                <i class="{{ config.icon }} text-2xl text-blue-500"></i>
            </div>
            <div class="ml-4">
                <p class="text-sm font-medium text-gray-500 dark:text-gray-400">Total {{ config.plural_name }}</p>
                <p class="text-2xl font-semibold text-gray-900 dark:text-white">{{ summary_stats.total_count }}</p>
            </div>
        </div>
    </div>
    
    <!-- Entity-specific stats -->
    {% if config.entity_type.value == 'supplier_invoices' %}
    
    <!-- Total Amount Card -->
    <div class="stat-card bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div class="flex items-center">
            <div class="flex-shrink-0">
                <i class="fas fa-rupee-sign text-2xl text-green-500"></i>
            </div>
            <div class="ml-4">
                <p class="text-sm font-medium text-gray-500 dark:text-gray-400">Total Amount</p>
                <p class="text-2xl font-semibold text-gray-900 dark:text-white">
                    ₹{{ "%.2f"|format(summary_stats.total_amount|float) if summary_stats.total_amount else '0.00' }}
                </p>
            </div>
        </div>
    </div>
    
    <!-- Pending Invoices Card -->
    <div class="stat-card bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div class="flex items-center">
            <div class="flex-shrink-0">
                <i class="fas fa-clock text-2xl text-yellow-500"></i>
            </div>
            <div class="ml-4">
                <p class="text-sm font-medium text-gray-500 dark:text-gray-400">Pending Payments</p>
                <p class="text-2xl font-semibold text-gray-900 dark:text-white">{{ summary_stats.pending_count or 0 }}</p>
            </div>
        </div>
    </div>
    
    <!-- Average Amount Card -->
    <div class="stat-card bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div class="flex items-center">
            <div class="flex-shrink-0">
                <i class="fas fa-chart-line text-2xl text-purple-500"></i>
            </div>
            <div class="ml-4">
                <p class="text-sm font-medium text-gray-500 dark:text-gray-400">Average Amount</p>
                <p class="text-2xl font-semibold text-gray-900 dark:text-white">
                    ₹{{ "%.2f"|format(summary_stats.average_amount|float) if summary_stats.average_amount else '0.00' }}
                </p>
            </div>
        </div>
    </div>
    
    {% endif %}
</div>

<!-- =============================================================================
JAVASCRIPT INTEGRATION - Following your existing JS organization
FILE: app/static/js/components/universal-search.js
============================================================================= -->

<script>
// Universal search functionality following your existing JS patterns

// Search form handling
function handleDatePreset(preset) {
    const startDateInput = document.querySelector('input[name="start_date"]');
    const endDateInput = document.querySelector('input[name="end_date"]');
    
    if (preset === 'today') {
        const today = new Date().toISOString().split('T')[0];
        if (startDateInput) startDateInput.value = today;
        if (endDateInput) endDateInput.value = today;
    } else if (preset === 'this_week') {
        // Calculate this week's dates
        const today = new Date();
        const firstDay = new Date(today.setDate(today.getDate() - today.getDay()));
        const lastDay = new Date(today.setDate(today.getDate() - today.getDay() + 6));
        
        if (startDateInput) startDateInput.value = firstDay.toISOString().split('T')[0];
        if (endDateInput) endDateInput.value = lastDay.toISOString().split('T')[0];
    } else if (preset === 'this_month') {
        // Calculate this month's dates
        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);
        
        if (startDateInput) startDateInput.value = firstDay.toISOString().split('T')[0];
        if (endDateInput) endDateInput.value = lastDay.toISOString().split('T')[0];
    }
}

// Clear all filters
function clearFilters() {
    const form = document.querySelector('.search-card form');
    if (form) {
        // Clear all input fields
        form.querySelectorAll('input[type="text"], input[type="date"], select').forEach(input => {
            input.value = '';
        });
        
        // Submit the cleared form
        form.submit();
    }
}

// Toggle advanced filters
function toggleAdvancedFilters() {
    const advancedFilters = document.getElementById('advancedFilters');
    if (advancedFilters) {
        advancedFilters.style.display = advancedFilters.style.display === 'none' ? 'block' : 'none';
    }
}

// Remove specific filter
function removeFilter(filterName) {
    const url = new URL(window.location);
    url.searchParams.delete(filterName);
    window.location.href = url.toString();
}

// Change view mode
function setViewMode(mode) {
    const url = new URL(window.location);
    url.searchParams.set('view_mode', mode);
    window.location.href = url.toString();
}

// Change items per page
function changePerPage(perPage) {
    const url = new URL(window.location);
    url.searchParams.set('per_page', perPage);
    url.searchParams.set('page', '1'); // Reset to first page
    window.location.href = url.toString();
}

// Sort by field
function sortBy(fieldName) {
    const url = new URL(window.location);
    const currentSort = url.searchParams.get('sort_field');
    const currentOrder = url.searchParams.get('sort_order');
    
    url.searchParams.set('sort_field', fieldName);
    
    // Toggle sort order if same field
    if (currentSort === fieldName && currentOrder === 'asc') {
        url.searchParams.set('sort_order', 'desc');
    } else {
        url.searchParams.set('sort_order', 'asc');
    }
    
    window.location.href = url.toString();
}

// Export data
function exportData() {
    const url = new URL(window.location);
    url.searchParams.set('export', 'csv');
    window.open(url.toString(), '_blank');
}

// Custom action handling
function handleCustomAction(actionId, entityId) {
    // Delegate to entity-specific handlers
    console.log(`Handling custom action: ${actionId} for entity: ${entityId}`);
    
    // This can be extended based on your specific requirements
    // Example: redirect to custom action handlers
    const entityType = document.querySelector('[data-entity-type]')?.dataset.entityType;
    if (entityType && actionId) {
        window.location.href = `/universal/${entityType}/${entityId}/action/${actionId}`;
    }
}

// Confirm delete action
function confirmDelete(entityId) {
    if (confirm('Are you sure you want to delete this item?')) {
        // Handle delete action
        console.log(`Deleting entity: ${entityId}`);
        // Implement delete logic here
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize any additional functionality
    console.log('Universal search initialized');
});
</script>