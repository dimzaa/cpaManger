/**
 * Dev Mode Utilities
 * 
 * Helpers for filtering test data in the frontend
 */

/**
 * Check if Dev Mode is currently enabled
 */
export function isDevModeEnabled() {
  if (typeof window === 'undefined') return false;
  const stored = localStorage.getItem('dev_mode_enabled');
  return stored ? JSON.parse(stored) : false;
}

/**
 * Filter out test data unless dev mode is enabled
 * 
 * @param {Array} items - Array of items to filter
 * @param {String} testField - Field name that indicates test data (default: 'is_test')
 * @returns {Array} - Filtered array
 */
export function filterTestData(items, testField = 'is_test') {
  if (!Array.isArray(items)) return items;
  
  const showTestData = isDevModeEnabled();
  if (showTestData) return items;
  
  return items.filter(item => !item[testField]);
}

/**
 * Filter municipalities or employees removing test data
 */
export function filterMunicipalities(municipalities) {
  return filterTestData(municipalities, 'is_test');
}

export function filterEmployees(employees) {
  return filterTestData(employees, 'is_test');
}

/**
 * Listen for dev mode changes across tabs/components
 */
export function onDevModeChange(callback) {
  window.addEventListener('devModeChanged', (event) => {
    callback(event.detail.enabled);
  });
}

/**
 * Format test data badge for display
 */
export function getTestDataBadge(isTest) {
  if (!isTest) return null;
  return {
    icon: '🧪',
    label: 'Test Data',
    className: 'bg-purple-100 text-purple-700 border border-purple-300',
  };
}
