/**
 * Package Payment Plan - Session Completion
 * Handles session completion modal and API interactions
 *
 * Version: 2.0 - Updated to use Tailwind modals (no Bootstrap)
 * Updated: 2025-11-12
 */

/**
 * Open session completion modal
 * @param {string} sessionId - Session UUID
 * @param {number} sessionNumber - Session number for display
 */
function openSessionModal(sessionId, sessionNumber) {
    console.log('[openSessionModal] Called with:', sessionId, sessionNumber);

    // Set session info
    document.getElementById('modal-session-id').value = sessionId;
    document.getElementById('modal-session-number').textContent = sessionNumber;

    // Set actual date to today
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('actual-date').value = today;

    // Load staff list
    loadStaffList();

    // Show modal - remove hidden class (NOT Bootstrap)
    const modal = document.getElementById('session-modal');
    modal.classList.remove('hidden');
    console.log('[openSessionModal] Modal shown');
}

/**
 * Close session completion modal
 */
function closeSessionModal() {
    const modal = document.getElementById('session-modal');
    modal.classList.add('hidden');
    document.getElementById('session-completion-form').reset();
    console.log('[closeSessionModal] Modal hidden');
}

/**
 * Load staff list for "Performed By" dropdown
 */
async function loadStaffList() {
    try {
        const response = await fetch('/api/staff/active');

        if (!response.ok) {
            console.warn('Staff API not available, using manual entry');
            // Make the field optional if API is not available
            const select = document.getElementById('performed-by');
            select.innerHTML = '<option value="">Select Staff (or leave blank)...</option>';
            select.required = false;
            return;
        }

        const data = await response.json();
        const select = document.getElementById('performed-by');

        // Clear existing options except first
        select.innerHTML = '<option value="">Select Staff...</option>';

        // Add staff options
        if (data.staff && data.staff.length > 0) {
            data.staff.forEach(staff => {
                const option = document.createElement('option');
                option.value = staff.user_id;
                option.textContent = staff.full_name || `${staff.first_name} ${staff.last_name}`;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading staff list:', error);
        // Make the field optional if there's an error
        const select = document.getElementById('performed-by');
        select.innerHTML = '<option value="">Select Staff (or leave blank)...</option>';
        select.required = false;
    }
}

/**
 * Handle session completion form submission
 */
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('session-completion-form');

    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();

            const sessionId = document.getElementById('modal-session-id').value;
            const actualDate = document.getElementById('actual-date').value;
            const performedBy = document.getElementById('performed-by').value;
            const notes = document.getElementById('service-notes').value;

            console.log('[Form Submit] Session:', sessionId, 'Date:', actualDate, 'Staff:', performedBy);

            // Validate required fields
            if (!sessionId || !actualDate) {
                alert('Please fill in all required fields (Session and Date)');
                return;
            }

            if (!performedBy) {
                console.warn('[Form Submit] No staff selected, proceeding anyway');
            }

            // Disable submit button
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Saving...';

            try {
                const url = `/api/package/session/${sessionId}/complete`;
                console.log('[API Call] URL:', url);

                // Get CSRF token
                const csrfToken = document.querySelector('[name=csrf_token]').value;
                console.log('[API Call] CSRF Token:', csrfToken ? 'Present' : 'Missing');

                const response = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({
                        actual_date: actualDate,
                        performed_by: performedBy,
                        notes: notes
                    })
                });

                console.log('[API Response] Status:', response.status);
                const result = await response.json();
                console.log('[API Response] Data:', result);

                if (result.success) {
                    // Success
                    closeSessionModal();
                    alert('Session completed successfully!');
                    console.log('[Success] Reloading page...');
                    location.reload();
                } else {
                    // Error from API
                    console.error('[API Error]:', result.error);
                    alert('Error: ' + (result.error || 'Failed to complete session'));
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalText;
                }
            } catch (error) {
                // Network/parsing error
                console.error('[Exception] Error completing session:', error);
                alert('Error completing session. Please try again.');
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }
        });
    }
});

/**
 * Escape key handler to close modal
 */
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const modal = document.getElementById('session-modal');
        if (modal && !modal.classList.contains('hidden')) {
            closeSessionModal();
        }
    }
});
