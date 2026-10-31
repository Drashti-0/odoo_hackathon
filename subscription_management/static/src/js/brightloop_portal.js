/** @odoo-module **/

/**
 * Brightloop Subscription Management – Portal & Signup Client Interaction
 * Enforces real-time password security criteria and interactive UX feedback.
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Interactive Password Strength Checker on Signup Form
    const passwordInput = document.getElementById('bl_password');
    if (passwordInput) {
        const meterContainer = document.createElement('div');
        meterContainer.id = 'bl_password_meter';
        meterContainer.className = 'bl-password-meter bl-meter-weak';
        meterContainer.innerHTML = '<span><i class="fa fa-info-circle"></i> Password must contain >8 characters, uppercase, lowercase, and a symbol.</span>';
        passwordInput.parentNode.insertBefore(meterContainer, passwordInput.nextSibling);

        passwordInput.addEventListener('input', (e) => {
            const val = e.target.value;
            const hasLen = val.length > 8;
            const hasUpper = /[A-Z]/.test(val);
            const hasLower = /[a-z]/.test(val);
            const hasDigit = /[0-9]/.test(val);
            const hasSpecial = /[!@#$%^&*()_+\-=\[\]{}|;':",.<>?/~`]/.test(val);

            const score = [hasLen, hasUpper, hasLower, hasDigit, hasSpecial].filter(Boolean).length;

            if (score === 5) {
                meterContainer.className = 'bl-password-meter bl-meter-strong';
                meterContainer.innerHTML = '<span><i class="fa fa-check-circle"></i> Strong password! Meets all Brightloop security criteria.</span>';
            } else if (score >= 3) {
                meterContainer.className = 'bl-password-meter bl-meter-medium';
                meterContainer.innerHTML = '<span><i class="fa fa-exclamation-circle"></i> Moderate: Ensure length > 8, uppercase, number & symbol.</span>';
            } else {
                meterContainer.className = 'bl-password-meter bl-meter-weak';
                meterContainer.innerHTML = '<span><i class="fa fa-times-circle"></i> Too weak: Must have >8 chars, uppercase, lowercase & symbol.</span>';
            }
        });
    }

    // 2. Format Status Pills on Table Rows
    const statusBadges = document.querySelectorAll('.bl-status');
    statusBadges.forEach(badge => {
        const text = (badge.textContent || '').trim().toLowerCase();
        if (text === 'active' || text === 'paid') {
            badge.classList.add('bl-status-active');
        } else if (text === 'partial' || text === 'partially_paid') {
            badge.classList.add('bl-status-partial');
        } else if (text === 'paused') {
            badge.classList.add('bl-status-paused');
        } else if (text === 'closed' || text === 'cancel' || text === 'expired') {
            badge.classList.add('bl-status-closed');
        } else {
            badge.classList.add('bl-status-draft');
        }
    });
});
