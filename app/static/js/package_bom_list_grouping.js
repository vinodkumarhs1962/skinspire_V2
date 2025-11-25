/**
 * Package BOM Items List - Visual Grouping by Package
 * Adds visual divider lines when package_name changes
 */

document.addEventListener('DOMContentLoaded', function() {
    // Find the BOM items table
    const table = document.querySelector('.universal-data-table tbody');

    if (!table) {
        console.log('Table not found for package grouping');
        return;
    }

    const rows = table.querySelectorAll('tr');
    let previousPackageName = null;

    rows.forEach((row, index) => {
        // Find the package name cell (usually first or second column)
        const cells = row.querySelectorAll('td');

        // Try to find package name cell by checking for text content
        // Assuming package_name is in one of the early columns
        let packageNameCell = null;
        let currentPackageName = null;

        // Look for package name in first few columns
        for (let i = 0; i < Math.min(3, cells.length); i++) {
            const cellText = cells[i].textContent.trim();
            // Skip if it's a number (likely row number or ID)
            if (cellText && !/^\d+$/.test(cellText)) {
                // Check if this looks like a package name (has some length)
                if (cellText.length > 5) {
                    packageNameCell = cells[i];
                    currentPackageName = cellText;
                    break;
                }
            }
        }

        // If package name found and it's different from previous, add divider
        if (currentPackageName && previousPackageName && currentPackageName !== previousPackageName) {
            // Add a CSS class to create visual separation
            row.classList.add('package-group-start');
        }

        previousPackageName = currentPackageName;
    });

    console.log(`Package BOM grouping applied to ${rows.length} rows`);
});

/**
 * Handle approve action with POST form submission
 * Used for approve buttons in row actions
 */
window.handleApproveAction = function(url, message) {
    if (!confirm(message)) {
        return false;
    }

    // Create a form dynamically
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = url;

    // Get CSRF token
    const csrfInput = document.querySelector('[name=csrf_token]');
    if (csrfInput) {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'csrf_token';
        input.value = csrfInput.value;
        form.appendChild(input);
    } else {
        // Try to get it from meta tag
        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        if (csrfMeta) {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'csrf_token';
            input.value = csrfMeta.content;
            form.appendChild(input);
        } else {
            alert('Security token not found. Please refresh the page and try again.');
            return false;
        }
    }

    // Submit the form
    document.body.appendChild(form);
    form.submit();
    return false;
};
