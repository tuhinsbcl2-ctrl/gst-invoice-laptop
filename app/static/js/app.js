/**
 * NIBRITY ENTERPRISE – GST Billing App
 * Frontend JavaScript utilities
 */

/**
 * Format a number in Indian currency format (₹1,00,000.00)
 */
function formatINR(amount) {
    if (isNaN(amount)) return '0.00';
    return Number(amount).toLocaleString('en-IN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

/**
 * Debounce utility
 */
function debounce(fn, delay) {
    let timer;
    return function(...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}

/**
 * Auto-dismiss flash messages after 5 seconds
 */
document.addEventListener('DOMContentLoaded', function () {
    const alerts = document.querySelectorAll('.alert.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) bsAlert.close();
        }, 5000);
    });
});
