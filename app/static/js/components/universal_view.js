// File: static/js/components/universal_view.js
// FINAL VERSION: Based on your attached script + your existing component patterns

/**
 * Universal View JavaScript Component
 * Follows your existing Universal Engine patterns while using the class structure from v3.0
 */

class UniversalViewManager {
    constructor() {
        this.activeTab = null;
        this.collapsedSections = new Set();
        this.isInitialized = false;
        
        // Initialize all components
        this.initializeTabs();
        this.initializeAccordions();
        this.initializeCollapsibleSections();
        this.initializeResponsive();
        this.initializeKeyboardNavigation();
        
        console.log('✅ Universal View Manager initialized');
    }
    
    // ==========================================
    // TAB MANAGEMENT (from your attached script)
    // ==========================================
    
    initializeTabs() {
        // Tab navigation
        // document.querySelectorAll('.universal-tab-button').forEach(button => {
        //     button.addEventListener('click', (e) => {
        //         e.preventDefault();
        //         this.switchTab(button.dataset.tab);
        //     });
        // });
        
        // Set initial active tab
        const activeTab = document.querySelector('.universal-tab-button.active');
        if (activeTab) {
            this.activeTab = activeTab.dataset.tab;
        }
        
        // Handle URL hash navigation
        if (window.location.hash && window.location.hash.startsWith('#tab-')) {
            const hashTab = window.location.hash.replace('#tab-', '');
            this.switchTab(hashTab);
        }
    }
    
    switchTab(tabKey) {
        console.log(`[UniversalViewManager] Switching to tab: ${tabKey}`);
        
        // Hide all tab panels
        document.querySelectorAll('.universal-tab-panel').forEach(panel => {
            panel.classList.add('hidden');
        });
        
        // Show selected panel
        const targetPanel = document.getElementById(`tab-${tabKey}`);
        if (targetPanel) {
            targetPanel.classList.remove('hidden');
        }
        
        // Update buttons
        document.querySelectorAll('.universal-tab-button').forEach(button => {
            button.classList.remove('active', 'text-blue-600', 'dark:text-blue-400', 'border-blue-600', 'dark:border-blue-400');
            button.classList.add('text-gray-500', 'dark:text-gray-400', 'border-transparent');
        });
        
        const targetButton = document.querySelector(`[data-tab="${tabKey}"]`);
        if (targetButton) {
            targetButton.classList.remove('text-gray-500', 'dark:text-gray-400', 'border-transparent');
            targetButton.classList.add('active', 'text-blue-600', 'dark:text-blue-400', 'border-blue-600', 'dark:border-blue-400');
        }
        
        this.activeTab = tabKey;
    }
    
    // ==========================================
    // ACCORDION MANAGEMENT (from your attached script)
    // ==========================================
    
    initializeAccordions() {
        
    }
    
    // ==========================================
    // COLLAPSIBLE SECTIONS (within tabs)
    // ==========================================
    
    initializeCollapsibleSections() {
        window.toggleUniversalSection = (sectionKey) => {
            const content = document.getElementById(`content-${sectionKey}`);
            const chevron = document.getElementById(`chevron-${sectionKey}`);
            
            if (content && chevron) {
                if (content.classList.contains('hidden')) {
                    content.classList.remove('hidden');
                    chevron.classList.add('rotated');
                    this.collapsedSections.delete(sectionKey);
                } else {
                    content.classList.add('hidden');
                    chevron.classList.remove('rotated');
                    this.collapsedSections.add(sectionKey);
                }
                console.log('🔄 Toggled section:', sectionKey);
            }
        };
    }
    
    // ==========================================
    // KEYBOARD NAVIGATION (from your attached script)
    // ==========================================
    
    initializeKeyboardNavigation() {
        document.addEventListener('keydown', (e) => {
            // Tab navigation with Ctrl/Cmd + number keys
            if (e.ctrlKey || e.metaKey) {
                const tabNumber = parseInt(e.key);
                if (tabNumber >= 1 && tabNumber <= 9) {
                    const tabs = document.querySelectorAll('.universal-tab-button');
                    if (tabs[tabNumber - 1]) {
                        e.preventDefault();
                        this.switchTab(tabs[tabNumber - 1].dataset.tab);
                    }
                }
            }
            
            // Arrow key navigation within tabs
            if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
                const focusedElement = document.activeElement;
                if (focusedElement && focusedElement.classList.contains('universal-tab-button')) {
                    e.preventDefault();
                    const tabs = Array.from(document.querySelectorAll('.universal-tab-button'));
                    const currentIndex = tabs.indexOf(focusedElement);
                    
                    let newIndex;
                    if (e.key === 'ArrowLeft') {
                        newIndex = currentIndex > 0 ? currentIndex - 1 : tabs.length - 1;
                    } else {
                        newIndex = currentIndex < tabs.length - 1 ? currentIndex + 1 : 0;
                    }
                    
                    tabs[newIndex].focus();
                    this.switchTab(tabs[newIndex].dataset.tab);
                }
            }
        });
    }
    
    // ==========================================
    // RESPONSIVE BEHAVIOR (from your attached script)
    // ==========================================
    
    initializeResponsive() {
        const handleResize = () => {
            const isMobile = window.innerWidth < 768;
            const tabbedView = document.querySelector('.universal-tabbed-view');
            
            if (tabbedView) {
                if (isMobile) {
                    tabbedView.classList.add('mobile-responsive');
                    this.enableMobileOptimizations();
                } else {
                    tabbedView.classList.remove('mobile-responsive');
                    this.disableMobileOptimizations();
                }
            }
        };
        
        window.addEventListener('resize', handleResize);
        handleResize(); // Initial check
    }
    
    enableMobileOptimizations() {
        // Add swipe navigation for mobile
        this.initializeSwipeNavigation();
        
        // Ensure tab navigation is scrollable
        const tabNav = document.querySelector('.universal-tab-navigation nav');
        if (tabNav) {
            tabNav.style.overflowX = 'auto';
            tabNav.style.scrollBehavior = 'smooth';
        }
        
        console.log('📱 Mobile optimizations enabled');
    }
    
    disableMobileOptimizations() {
        // Remove swipe navigation for desktop
        this.destroySwipeNavigation();
    }
    
    // ==========================================
    // MOBILE SWIPE NAVIGATION (from your attached script)
    // ==========================================
    
    initializeSwipeNavigation() {
        const tabContent = document.querySelector('.universal-tab-content');
        if (!tabContent) return;
        
        let startX = 0;
        let startY = 0;
        
        tabContent.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
        });
        
        tabContent.addEventListener('touchend', (e) => {
            if (!startX || !startY) return;
            
            const endX = e.changedTouches[0].clientX;
            const endY = e.changedTouches[0].clientY;
            
            const diffX = startX - endX;
            const diffY = startY - endY;
            
            // Check if horizontal swipe is dominant
            if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 50) {
                const tabs = Array.from(document.querySelectorAll('.universal-tab-button'));
                const currentIndex = tabs.findIndex(tab => tab.classList.contains('active'));
                
                if (diffX > 0 && currentIndex < tabs.length - 1) {
                    // Swipe left - next tab
                    this.switchTab(tabs[currentIndex + 1].dataset.tab);
                } else if (diffX < 0 && currentIndex > 0) {
                    // Swipe right - previous tab
                    this.switchTab(tabs[currentIndex - 1].dataset.tab);
                }
            }
            
            startX = 0;
            startY = 0;
        });
    }
    
    destroySwipeNavigation() {
        // Remove swipe event listeners if needed
        // Implementation can be added if needed for cleanup
    }
    
    // ==========================================
    // UTILITY METHODS (from your attached script + global pattern)
    // ==========================================
    
    showAllSections() {
        document.querySelectorAll('.universal-accordion-content.hidden').forEach(content => {
            content.classList.remove('hidden');
            const sectionKey = content.id.replace('accordion-content-', '');
            this.collapsedSections.delete(sectionKey);
        });
        
        document.querySelectorAll('[id^="content-"].hidden').forEach(content => {
            content.classList.remove('hidden');
            const sectionKey = content.id.replace('content-', '');
            this.collapsedSections.delete(sectionKey);
        });
        
        // Rotate all chevrons
        document.querySelectorAll('[id^="accordion-chevron-"], [id^="chevron-"]').forEach(chevron => {
            chevron.classList.add('rotated');
        });
        
        console.log('📖 Expanded all sections');
    }
    
    hideAllSections() {
        document.querySelectorAll('.universal-accordion-content:not(.hidden)').forEach(content => {
            content.classList.add('hidden');
            const sectionKey = content.id.replace('accordion-content-', '');
            this.collapsedSections.add(sectionKey);
        });
        
        document.querySelectorAll('[id^="content-"]:not(.hidden)').forEach(content => {
            content.classList.add('hidden');
            const sectionKey = content.id.replace('content-', '');
            this.collapsedSections.add(sectionKey);
        });
        
        // Reset all chevrons
        document.querySelectorAll('[id^="accordion-chevron-"], [id^="chevron-"]').forEach(chevron => {
            chevron.classList.remove('rotated');
        });
        
        console.log('📖 Collapsed all sections');
    }
    
    getCurrentTab() {
        return this.activeTab;
    }
    
    getVisibleFields() {
        const activePanel = document.querySelector('.universal-tab-panel:not(.hidden)');
        if (activePanel) {
            return activePanel.querySelectorAll('.universal-field-group');
        }
        return document.querySelectorAll('.universal-field-group');
    }
    initializeCollapsibleSections() {
        // Initialize collapsible sections within tabs
        document.querySelectorAll('.universal-collapsible-section').forEach(section => {
            const header = section.querySelector('.universal-section-header');
            if (header) {
                header.addEventListener('click', () => {
                    const sectionKey = header.dataset.section;
                    this.toggleSection(sectionKey);
                });
            }
        });
    }
    
    toggleSection(sectionKey) {
        const content = document.getElementById(`content-${sectionKey}`);
        const chevron = document.getElementById(`chevron-${sectionKey}`);
        
        if (!content) {
            console.warn('Section content not found:', sectionKey);
            return;
        }
        
        if (content.classList.contains('hidden')) {
            content.classList.remove('hidden');
            if (chevron) chevron.classList.add('rotated');
            this.collapsedSections.delete(sectionKey);
        } else {
            content.classList.add('hidden');
            if (chevron) chevron.classList.remove('rotated');
            this.collapsedSections.add(sectionKey);
        }
        
        console.log('🔄 Toggled section:', sectionKey);
    }
    
    
    // ==========================================
    // NEW UTILITY METHODS
    // ==========================================
    
    getEntityType() {
        // Extract entity type from page data or URL
        const entityMeta = document.querySelector('meta[name="entity-type"]');
        if (entityMeta) return entityMeta.content;
        
        // Fallback to URL parsing
        const pathMatch = window.location.pathname.match(/\/universal\/([^\/]+)/);
        return pathMatch ? pathMatch[1] : 'unknown';
    }
    
    restoreTabState() {
        // Restore previously active tab from sessionStorage
        try {
            const savedTab = sessionStorage.getItem(`universal_view_active_tab_${this.getEntityType()}`);
            if (savedTab && document.querySelector(`[data-tab="${savedTab}"]`)) {
                this.switchTab(savedTab);
                return true;
            }
        } catch (e) {
            // Silently fail
        }
        return false;
    }
    
    // ==========================================
    // PRINT & EXPORT INTEGRATION
    // ==========================================
    
    printView() {
        // Integrate with your existing print functionality
        this.showAllSections(); // Expand everything before printing
        
        // Use your existing loading state utilities
        if (typeof showLoadingState === 'function') {
            showLoadingState();
        }
        
        setTimeout(() => {
            window.print();
            
            if (typeof hideLoadingState === 'function') {
                hideLoadingState();
            }
        }, 300);
    }
    
    exportView(format = 'pdf') {
        // Integrate with your existing export system
        const entityType = this.getEntityType();
        const currentTab = this.activeTab;
        
        // Call your existing export handler
        if (typeof handleUniversalExport === 'function') {
            handleUniversalExport(entityType, format, {
                activeTab: currentTab,
                visibleSections: Array.from(this.collapsedSections)
            });
        }
    }
    
    // ==========================================
    // ENHANCED RESPONSIVE FEATURES
    // ==========================================
    
    initializeResponsive() {
        // Your existing responsive code plus:
        
        // Handle orientation changes
        window.addEventListener('orientationchange', () => {
            this.handleOrientationChange();
        });
        
        // Responsive tab overflow
        this.handleTabOverflow();
        window.addEventListener('resize', () => {
            this.handleTabOverflow();
        });
    }
    
    handleTabOverflow() {
        const tabContainer = document.querySelector('.universal-tab-navigation nav');
        if (!tabContainer) return;
        
        const containerWidth = tabContainer.offsetWidth;
        const tabs = Array.from(tabContainer.querySelectorAll('.universal-tab-button'));
        let totalWidth = 0;
        
        tabs.forEach(tab => {
            totalWidth += tab.offsetWidth;
        });
        
        if (totalWidth > containerWidth) {
            tabContainer.classList.add('tab-overflow');
            // Could add scroll buttons here
        } else {
            tabContainer.classList.remove('tab-overflow');
        }
    }
    
    handleOrientationChange() {
        // Recalculate layouts after orientation change
        setTimeout(() => {
            this.handleTabOverflow();
        }, 100);
    }

    checkTabVisibility() {
        const isEditMode = document.body.classList.contains('edit-mode') || 
                        window.location.href.includes('/edit/');
        
        document.querySelectorAll('.universal-tab-button').forEach(button => {
            const tabKey = button.getAttribute('data-tab');
            
            // Configuration tab only visible in edit mode
            if (tabKey === 'configuration') {
                button.style.display = isEditMode ? 'flex' : 'none';
                
                // Hide the tab panel as well
                const tabPanel = document.getElementById(`tab-${tabKey}`);
                if (tabPanel && !isEditMode) {
                    tabPanel.classList.add('hidden');
                }
            }
        });
    }

}

// ==========================================
// GLOBAL FUNCTIONS : UniversalViewManager
// ==========================================

// These are the functions your template is actually calling
window.switchUniversalTab = (tabKey) => {
    // Ensure manager exists
    if (!window.universalViewManager) {
        console.warn('View manager not initialized, creating now...');
        window.universalViewManager = new UniversalViewManager();
    }
    window.universalViewManager.switchTab(tabKey);
};

window.toggleUniversalAccordion = (sectionKey) => {
    // Ensure manager exists
    if (!window.universalViewManager) {
        console.warn('View manager not initialized, creating now...');
        window.universalViewManager = new UniversalViewManager();
    }
    window.universalViewManager.toggleAccordion(sectionKey);
};

// Set up accordion toggle functionality - global functions like your existing components
window.toggleUniversalAccordion = (sectionKey) => {
    const content = document.getElementById(`accordion-content-${sectionKey}`);
    const chevron = document.getElementById(`accordion-chevron-${sectionKey}`);
    
    if (content && chevron) {
        if (content.classList.contains('hidden')) {
            content.classList.remove('hidden');
            chevron.classList.add('rotated');
            this.collapsedSections.delete(sectionKey);
        } else {
            content.classList.add('hidden');
            chevron.classList.remove('rotated');
            this.collapsedSections.add(sectionKey);
        }
        console.log('🔄 Toggled accordion section:', sectionKey);
    }
};

window.toggleUniversalSection = (sectionKey) => {
    if (!window.universalViewManager) {
        window.universalViewManager = new UniversalViewManager();
    }
    window.universalViewManager.toggleSection(sectionKey);
};

// Enhanced print function
window.printUniversalView = () => {
    if (!window.universalViewManager) {
        window.universalViewManager = new UniversalViewManager();
    }
    window.universalViewManager.printView();
};

// New export function
window.exportUniversalView = (format) => {
    if (!window.universalViewManager) {
        window.universalViewManager = new UniversalViewManager();
    }
    window.universalViewManager.exportView(format);
};

// ==========================================
// GLOBAL FUNCTIONS (Following your existing component patterns)
// ==========================================

// Global utility functions for template usage
window.showAllUniversalSections = () => {
    if (window.universalViewManager) {
        window.universalViewManager.showAllSections();
    }
};

window.hideAllUniversalSections = () => {
    if (window.universalViewManager) {
        window.universalViewManager.hideAllSections();
    }
};

// Print functionality (like your existing utilities)
window.printUniversalView = () => {
    // Use existing loading state functions if available
    if (typeof showLoadingState === 'function') {
        showLoadingState();
    }
    
    setTimeout(() => {
        window.print();
        
        if (typeof hideLoadingState === 'function') {
            hideLoadingState();
        }
    }, 100);
    
    console.log('🖨️ Printing view');
};

// Export functionality (following your existing pattern)
window.exportUniversalView = () => {
    // This would integrate with your existing export system
    console.log('Export functionality - integrate with existing handleUniversalExport');
};

// ==========================================
// INITIALIZATION (Following your existing DOM ready pattern)
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    // Only initialize if view template elements exist
    if (document.querySelector('.universal-tabbed-view') || 
        document.querySelector('.universal-accordion-view') ||
        document.querySelector('.universal-field-section')) {
        
        window.universalViewManager = new UniversalViewManager();
    }
});


// ==========================================
// CSS UTILITIES (Add rotation class)
// ==========================================

// Add rotation utility CSS
const style = document.createElement('style');
style.textContent = `
.rotated {
    transform: rotate(180deg) !important;
    transition: transform 0.2s ease-in-out !important;
}
`;
document.head.appendChild(style);

console.log('📋 Universal View JavaScript component loaded');

