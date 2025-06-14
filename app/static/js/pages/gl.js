/**
 * General Ledger (GL) JavaScript
 * 
 * Handles all GL-related functionality including:
 * - Financial reporting
 * - GST reporting
 * - Account reconciliation
 * - Transaction management
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize GL components
    initReportFilters();
    initBalanceSheet();
    initProfitLoss();
    initTrialBalance();
    initGSTReports();
    initDataTables();
    initCharts();
    
    // Handle date range selection
    setupDateRangeSelectors();
});

/**
 * Initialize report filters functionality
 */
function initReportFilters() {
    const reportForm = document.getElementById('reportFilterForm');
    const resetButton = document.getElementById('resetFilters');
    
    if (reportForm) {
        // Submit form when any filter changes if auto-submit is checked
        const filterInputs = reportForm.querySelectorAll('select, input:not([type="checkbox"])');
        filterInputs.forEach(input => {
            input.addEventListener('change', function() {
                const autoSubmit = document.getElementById('autoSubmit');
                if (autoSubmit && autoSubmit.checked) {
                    reportForm.submit();
                }
            });
        });
        
        // Apply filters on form submission
        reportForm.addEventListener('submit', function(e) {
            // Validate date range if present
            const fromDate = document.getElementById('from_date');
            const toDate = document.getElementById('to_date');
            
            if (fromDate && toDate && fromDate.value && toDate.value) {
                const fromDateObj = new Date(fromDate.value);
                const toDateObj = new Date(toDate.value);
                
                if (fromDateObj > toDateObj) {
                    e.preventDefault();
                    alert('From date cannot be later than To date');
                    return false;
                }
            }
        });
    }
    
    if (resetButton) {
        resetButton.addEventListener('click', function() {
            resetReportFilters();
        });
    }
}

/**
 * Reset all report filters
 */
function resetReportFilters() {
    const reportForm = document.getElementById('reportFilterForm');
    if (reportForm) {
        reportForm.reset();
        
        // For Select2 dropdowns, need to trigger change event
        const select2Elements = reportForm.querySelectorAll('.select2-hidden-accessible');
        select2Elements.forEach(select => {
            $(select).val(null).trigger('change');
        });
        
        // Redirect to the base URL without params
        window.location.href = window.location.pathname;
    }
}

/**
 * Setup date range selector functionality
 */
function setupDateRangeSelectors() {
    const dateRangeSelector = document.getElementById('date_range');
    if (!dateRangeSelector) return;
    
    const fromDateInput = document.getElementById('from_date');
    const toDateInput = document.getElementById('to_date');
    
    if (!fromDateInput || !toDateInput) return;
    
    dateRangeSelector.addEventListener('change', function() {
        const selectedRange = this.value;
        
        if (!selectedRange) return;
        
        const today = new Date();
        let fromDate = new Date();
        let toDate = new Date();
        
        // Calculate the date range based on selection
        switch (selectedRange) {
            case 'this_month':
                // Start of current month
                fromDate = new Date(today.getFullYear(), today.getMonth(), 1);
                break;
                
            case 'last_month':
                // Start of last month
                fromDate = new Date(today.getFullYear(), today.getMonth() - 1, 1);
                // End of last month
                toDate = new Date(today.getFullYear(), today.getMonth(), 0);
                break;
                
            case 'this_quarter':
                // Start of current quarter
                const currentQuarter = Math.floor(today.getMonth() / 3);
                fromDate = new Date(today.getFullYear(), currentQuarter * 3, 1);
                break;
                
            case 'last_quarter':
                // Start of last quarter
                const lastQuarter = Math.floor(today.getMonth() / 3) - 1;
                if (lastQuarter < 0) {
                    // Last quarter was in previous year
                    fromDate = new Date(today.getFullYear() - 1, 9, 1);
                    toDate = new Date(today.getFullYear() - 1, 11, 31);
                } else {
                    fromDate = new Date(today.getFullYear(), lastQuarter * 3, 1);
                    toDate = new Date(today.getFullYear(), lastQuarter * 3 + 3, 0);
                }
                break;
                
            case 'this_year':
                // Start of current year
                fromDate = new Date(today.getFullYear(), 0, 1);
                break;
                
            case 'last_year':
                // Start of last year
                fromDate = new Date(today.getFullYear() - 1, 0, 1);
                // End of last year
                toDate = new Date(today.getFullYear() - 1, 11, 31);
                break;
                
            case 'financial_year':
                // Determine financial year based on current date
                // Assuming financial year is April to March
                if (today.getMonth() < 3) {
                    // We're in Jan-Mar, so financial year started last calendar year
                    fromDate = new Date(today.getFullYear() - 1, 3, 1);
                    toDate = new Date(today.getFullYear(), 2, 31);
                } else {
                    // We're in Apr-Dec, so financial year started this calendar year
                    fromDate = new Date(today.getFullYear(), 3, 1);
                    toDate = new Date(today.getFullYear() + 1, 2, 31);
                }
                break;
                
            case 'last_financial_year':
                // Last financial year
                if (today.getMonth() < 3) {
                    // We're in Jan-Mar, so last financial year started two calendar years ago
                    fromDate = new Date(today.getFullYear() - 2, 3, 1);
                    toDate = new Date(today.getFullYear() - 1, 2, 31);
                } else {
                    // We're in Apr-Dec, so last financial year started last calendar year
                    fromDate = new Date(today.getFullYear() - 1, 3, 1);
                    toDate = new Date(today.getFullYear(), 2, 31);
                }
                break;
                
            case 'custom':
                // Don't change the dates for custom range
                return;
        }
        
        // Format dates as YYYY-MM-DD for input fields
        fromDateInput.value = formatDateForInput(fromDate);
        toDateInput.value = formatDateForInput(toDate);
        
        // Trigger change event for form auto-submit if enabled
        const event = new Event('change');
        fromDateInput.dispatchEvent(event);
    });
}

/**
 * Format a date object as YYYY-MM-DD for input fields
 */
function formatDateForInput(date) {
    const year = date.getFullYear();
    const month = (date.getMonth() + 1).toString().padStart(2, '0');
    const day = date.getDate().toString().padStart(2, '0');
    return `${year}-${month}-${day}`;
}

/**
 * Initialize balance sheet report functionality
 */
function initBalanceSheet() {
    const balanceSheetForm = document.getElementById('balanceSheetForm');
    
    if (balanceSheetForm) {
        // Export PDF functionality
        const exportPdfBtn = document.getElementById('exportPdfBtn');
        if (exportPdfBtn) {
            exportPdfBtn.addEventListener('click', function() {
                const formData = new FormData(balanceSheetForm);
                formData.append('export_format', 'pdf');
                
                window.location.href = balanceSheetForm.getAttribute('action') + '?' + new URLSearchParams(formData).toString();
            });
        }
        
        // Export Excel functionality
        const exportExcelBtn = document.getElementById('exportExcelBtn');
        if (exportExcelBtn) {
            exportExcelBtn.addEventListener('click', function() {
                const formData = new FormData(balanceSheetForm);
                formData.append('export_format', 'excel');
                
                window.location.href = balanceSheetForm.getAttribute('action') + '?' + new URLSearchParams(formData).toString();
            });
        }
        
        // Print functionality
        const printReportBtn = document.getElementById('printReportBtn');
        if (printReportBtn) {
            printReportBtn.addEventListener('click', function() {
                window.print();
            });
        }
    }
}

/**
 * Initialize profit & loss report functionality
 */
function initProfitLoss() {
    const profitLossForm = document.getElementById('profitLossForm');
    
    if (profitLossForm) {
        // Export PDF functionality
        const exportPdfBtn = document.getElementById('exportPdfBtn');
        if (exportPdfBtn) {
            exportPdfBtn.addEventListener('click', function() {
                const formData = new FormData(profitLossForm);
                formData.append('export_format', 'pdf');
                
                window.location.href = profitLossForm.getAttribute('action') + '?' + new URLSearchParams(formData).toString();
            });
        }
        
        // Export Excel functionality
        const exportExcelBtn = document.getElementById('exportExcelBtn');
        if (exportExcelBtn) {
            exportExcelBtn.addEventListener('click', function() {
                const formData = new FormData(profitLossForm);
                formData.append('export_format', 'excel');
                
                window.location.href = profitLossForm.getAttribute('action') + '?' + new URLSearchParams(formData).toString();
            });
        }
        
        // Print functionality
        const printReportBtn = document.getElementById('printReportBtn');
        if (printReportBtn) {
            printReportBtn.addEventListener('click', function() {
                window.print();
            });
        }
        
        // Toggle detail sections
        const toggleButtons = document.querySelectorAll('.toggle-details-btn');
        toggleButtons.forEach(btn => {
            btn.addEventListener('click', function() {
                const detailsId = this.getAttribute('data-details');
                const detailsSection = document.getElementById(detailsId);
                
                if (detailsSection) {
                    detailsSection.classList.toggle('hidden');
                    
                    // Update icon
                    const icon = this.querySelector('svg');
                    if (icon) {
                        icon.classList.toggle('rotate-180');
                    }
                }
            });
        });
    }
}

/**
 * Initialize trial balance functionality
 */
function initTrialBalance() {
    const trialBalanceForm = document.getElementById('trialBalanceForm');
    
    if (trialBalanceForm) {
        // Export PDF functionality
        const exportPdfBtn = document.getElementById('exportPdfBtn');
        if (exportPdfBtn) {
            exportPdfBtn.addEventListener('click', function() {
                const formData = new FormData(trialBalanceForm);
                formData.append('export_format', 'pdf');
                
                window.location.href = trialBalanceForm.getAttribute('action') + '?' + new URLSearchParams(formData).toString();
            });
        }
        
        // Export Excel functionality
        const exportExcelBtn = document.getElementById('exportExcelBtn');
        if (exportExcelBtn) {
            exportExcelBtn.addEventListener('click', function() {
                const formData = new FormData(trialBalanceForm);
                formData.append('export_format', 'excel');
                
                window.location.href = trialBalanceForm.getAttribute('action') + '?' + new URLSearchParams(formData).toString();
            });
        }
        
        // Print functionality
        const printReportBtn = document.getElementById('printReportBtn');
        if (printReportBtn) {
            printReportBtn.addEventListener('click', function() {
                window.print();
            });
        }
    }
}

/**
 * Initialize GST report functionality
 */
function initGSTReports() {
    // GSTR-1 Report
    const gstr1Form = document.getElementById('gstr1Form');
    if (gstr1Form) {
        setupGSTReportExport(gstr1Form, 'gl.export_gstr1');
    }
    
    // GSTR-2A Report
    const gstr2aForm = document.getElementById('gstr2aForm');
    if (gstr2aForm) {
        setupGSTReportExport(gstr2aForm, 'gl.export_gstr2a');
        
        // Initialize tabs for B2B suppliers
        initGSTR2ATabs();
    }
    
    // GSTR-3B Report
    const gstr3bForm = document.getElementById('gstr3bForm');
    if (gstr3bForm) {
        setupGSTReportExport(gstr3bForm, 'gl.export_gstr3b');
    }
}

/**
 * Setup GST report export functions
 */
function setupGSTReportExport(form, exportUrl) {
    // Export JSON functionality
    const exportJsonBtn = document.getElementById('exportJsonBtn');
    if (exportJsonBtn) {
        exportJsonBtn.addEventListener('click', function() {
            const formData = new FormData(form);
            formData.append('export_format', 'json');
            
            window.location.href = exportUrl + '?' + new URLSearchParams(formData).toString();
        });
    }
    
    // Export Excel functionality
    const exportExcelBtn = document.getElementById('exportExcelBtn');
    if (exportExcelBtn) {
        exportExcelBtn.addEventListener('click', function() {
            const formData = new FormData(form);
            formData.append('export_format', 'excel');
            
            window.location.href = exportUrl + '?' + new URLSearchParams(formData).toString();
        });
    }
    
    // Print functionality
    const printReportBtn = document.getElementById('printReportBtn');
    if (printReportBtn) {
        printReportBtn.addEventListener('click', function() {
            window.print();
        });
    }
}

/**
 * Initialize tabs for GSTR-2A report
 */
function initGSTR2ATabs() {
    const tabs = document.querySelectorAll('[data-tabs-target]');
    const tabContents = document.querySelectorAll('[role="tabpanel"]');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const target = document.querySelector(tab.dataset.tabsTarget);
            
            tabContents.forEach(tc => {
                tc.classList.add('hidden');
            });
            
            tabs.forEach(t => {
                t.setAttribute('aria-selected', false);
                t.classList.remove('border-blue-600', 'text-blue-600', 'dark:text-blue-400', 'dark:border-blue-400');
                t.classList.add('border-transparent');
            });
            
            tab.setAttribute('aria-selected', true);
            tab.classList.remove('border-transparent');
            tab.classList.add('border-blue-600', 'text-blue-600', 'dark:text-blue-400', 'dark:border-blue-400');
            target.classList.remove('hidden');
        });
    });
    
    // Set default active tab
    if (tabs.length > 0) {
        tabs[0].click();
    }
}

/**
 * Initialize DataTables for GL tables
 */
function initDataTables() {
    // Only initialize if DataTables library is available
    if (typeof $.fn.DataTable !== 'undefined') {
        // Transaction list table
        const transactionTable = $('#transactionListTable');
        if (transactionTable.length) {
            transactionTable.DataTable({
                responsive: true,
                dom: '<"top"flp>rt<"bottom"ip>',
                language: {
                    search: "_INPUT_",
                    searchPlaceholder: "Search transactions...",
                    lengthMenu: "Show _MENU_ entries per page",
                    info: "Showing _START_ to _END_ of _TOTAL_ entries",
                },
                pageLength: 25,
                order: [[0, 'desc']], // Sort by date descending by default
                columnDefs: [
                    { orderable: false, targets: [-1] } // Disable sorting on action column
                ]
            });
        }
        
        // Account list table
        const accountTable = $('#accountListTable');
        if (accountTable.length) {
            accountTable.DataTable({
                responsive: true,
                dom: '<"top"flp>rt<"bottom"ip>',
                language: {
                    search: "_INPUT_",
                    searchPlaceholder: "Search accounts...",
                    lengthMenu: "Show _MENU_ entries per page",
                    info: "Showing _START_ to _END_ of _TOTAL_ entries",
                },
                pageLength: 25,
                order: [[1, 'asc']], // Sort by account number by default
            });
        }
    }
}

/**
 * Initialize GL-related charts
 */
function initCharts() {
    // Only initialize if Chart.js library is available
    if (typeof Chart !== 'undefined') {
        // Income vs Expenses Chart
        const incomeExpenseCtx = document.getElementById('incomeExpenseChart');
        if (incomeExpenseCtx) {
            // Extract data from the HTML data attributes
            const labels = JSON.parse(incomeExpenseCtx.getAttribute('data-labels') || '[]');
            const incomeData = JSON.parse(incomeExpenseCtx.getAttribute('data-income') || '[]');
            const expenseData = JSON.parse(incomeExpenseCtx.getAttribute('data-expenses') || '[]');
            
            new Chart(incomeExpenseCtx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Income',
                            data: incomeData,
                            backgroundColor: '#10B981', // Green
                            borderColor: '#059669',
                            borderWidth: 1
                        },
                        {
                            label: 'Expenses',
                            data: expenseData,
                            backgroundColor: '#EF4444', // Red
                            borderColor: '#DC2626',
                            borderWidth: 1
                        }
                    ]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    return ' Rs.' + value.toLocaleString();
                                },
                                color: document.documentElement.classList.contains('dark') ? '#E5E7EB' : '#374151'
                            },
                            grid: {
                                color: document.documentElement.classList.contains('dark') ? '#374151' : '#E5E7EB'
                            }
                        },
                        x: {
                            ticks: {
                                color: document.documentElement.classList.contains('dark') ? '#E5E7EB' : '#374151'
                            },
                            grid: {
                                color: document.documentElement.classList.contains('dark') ? '#374151' : '#E5E7EB'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            labels: {
                                color: document.documentElement.classList.contains('dark') ? '#E5E7EB' : '#374151'
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.dataset.label || '';
                                    const value = context.raw || 0;
                                    return `${label}:  Rs.${value.toLocaleString()}`;
                                }
                            }
                        }
                    }
                }
            });
        }
        
        // Cash Flow Chart
        const cashFlowCtx = document.getElementById('cashFlowChart');
        if (cashFlowCtx) {
            // Extract data from the HTML data attributes
            const labels = JSON.parse(cashFlowCtx.getAttribute('data-labels') || '[]');
            const inflows = JSON.parse(cashFlowCtx.getAttribute('data-inflows') || '[]');
            const outflows = JSON.parse(cashFlowCtx.getAttribute('data-outflows') || '[]');
            const netFlow = JSON.parse(cashFlowCtx.getAttribute('data-netflow') || '[]');
            
            new Chart(cashFlowCtx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Net Cash Flow',
                            data: netFlow,
                            borderColor: '#3B82F6', // Blue
                            backgroundColor: 'rgba(59, 130, 246, 0.1)',
                            borderWidth: 2,
                            fill: false,
                            tension: 0.1,
                            yAxisID: 'y1'
                        },
                        {
                            label: 'Cash Inflows',
                            data: inflows,
                            borderColor: '#10B981', // Green
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            borderWidth: 1,
                            fill: true,
                            tension: 0.1,
                            yAxisID: 'y'
                        },
                        {
                            label: 'Cash Outflows',
                            data: outflows,
                            borderColor: '#EF4444', // Red
                            backgroundColor: 'rgba(239, 68, 68, 0.1)',
                            borderWidth: 1,
                            fill: true,
                            tension: 0.1,
                            yAxisID: 'y'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            position: 'left',
                            title: {
                                display: true,
                                text: 'Inflows & Outflows',
                                color: document.documentElement.classList.contains('dark') ? '#E5E7EB' : '#374151'
                            },
                            ticks: {
                                callback: function(value) {
                                    return ' Rs.' + value.toLocaleString();
                                },
                                color: document.documentElement.classList.contains('dark') ? '#E5E7EB' : '#374151'
                            },
                            grid: {
                                color: document.documentElement.classList.contains('dark') ? '#374151' : '#E5E7EB'
                            }
                        },
                        y1: {
                            beginAtZero: false,
                            position: 'right',
                            title: {
                                display: true,
                                text: 'Net Flow',
                                color: document.documentElement.classList.contains('dark') ? '#E5E7EB' : '#374151'
                            },
                            ticks: {
                                callback: function(value) {
                                    return ' Rs.' + value.toLocaleString();
                                },
                                color: document.documentElement.classList.contains('dark') ? '#E5E7EB' : '#374151'
                            },
                            grid: {
                                display: false
                            }
                        },
                        x: {
                            ticks: {
                                color: document.documentElement.classList.contains('dark') ? '#E5E7EB' : '#374151'
                            },
                            grid: {
                                color: document.documentElement.classList.contains('dark') ? '#374151' : '#E5E7EB'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            labels: {
                                color: document.documentElement.classList.contains('dark') ? '#E5E7EB' : '#374151'
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.dataset.label || '';
                                    const value = context.raw || 0;
                                    return `${label}:  Rs.${value.toLocaleString()}`;
                                }
                            }
                        }
                    }
                }
            });
        }
    }
}


/**
 * Export module functions
 */
export {
    initBalanceSheet,
    initProfitLoss,
    initTrialBalance,
    initGSTReports
};