/**
 * Promotion Timeline Component
 * Interactive timeline visualization for promotions dashboard
 * Supports drag-to-move, resize dates, click-to-edit, and overlap detection
 */

class PromotionTimeline {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`Container #${containerId} not found`);
            return;
        }

        this.options = {
            months: 3,
            rowHeight: 36,
            headerHeight: 70, // Increased to accommodate month header row
            dayWidth: 10,
            colors: {
                simple_discount: '#93c5fd', // Light Blue (blue-300)
                buy_x_get_y: '#86efac',     // Light Green (green-300)
                bulk: '#fdba74',             // Light Orange (orange-300)
                loyalty: '#d8b4fe',          // Light Purple (purple-300)
                personalized: '#f9a8d4',     // Light Pink (pink-300)
                overlap: 'rgba(254, 226, 226, 0.15)', // Very light red (red-100 at 15% opacity)
                today: '#ef4444',            // Red
                grid: '#e5e7eb'              // Gray
            },
            ...options
        };

        this.data = options.data || { campaigns: [], bulk_config: null, loyalty_periods: [], overlaps: [] };
        this.canvas = null;
        this.ctx = null;
        this.dragState = null;
        this.hoverItem = null;
        this.scrollOffset = 0;
        this.tooltip = null;

        // Calculate date range
        this.today = new Date();
        this.updateDateRange();

        // Branch state code for state-specific holidays (passed via options)
        this.stateCode = options.stateCode || null;

        // Initialize Indian holidays
        this.initializeHolidays();
    }

    /**
     * Initialize Indian government holidays
     * Includes national holidays and state-specific holidays
     */
    initializeHolidays() {
        const currentYear = this.today.getFullYear();
        const nextYear = currentYear + 1;

        // National holidays (applicable to all states)
        this.nationalHolidays = {
            // 2025 National Holidays
            [`${currentYear}-01-26`]: 'Republic Day',
            [`${currentYear}-08-15`]: 'Independence Day',
            [`${currentYear}-10-02`]: 'Gandhi Jayanti',
            // 2026 National Holidays
            [`${nextYear}-01-26`]: 'Republic Day',
            [`${nextYear}-08-15`]: 'Independence Day',
            [`${nextYear}-10-02`]: 'Gandhi Jayanti',
        };

        // Gazetted/Bank holidays (common across India)
        this.gazettedHolidays = {
            // 2025
            [`${currentYear}-01-01`]: 'New Year\'s Day',
            [`${currentYear}-01-14`]: 'Makar Sankranti / Pongal',
            [`${currentYear}-02-26`]: 'Maha Shivaratri',
            [`${currentYear}-03-14`]: 'Holi',
            [`${currentYear}-03-31`]: 'Eid-ul-Fitr',
            [`${currentYear}-04-06`]: 'Ram Navami',
            [`${currentYear}-04-10`]: 'Mahavir Jayanti',
            [`${currentYear}-04-14`]: 'Dr. Ambedkar Jayanti',
            [`${currentYear}-04-18`]: 'Good Friday',
            [`${currentYear}-05-12`]: 'Buddha Purnima',
            [`${currentYear}-06-07`]: 'Eid-ul-Adha (Bakrid)',
            [`${currentYear}-07-06`]: 'Muharram',
            [`${currentYear}-08-16`]: 'Janmashtami',
            [`${currentYear}-09-05`]: 'Milad-un-Nabi',
            [`${currentYear}-10-01`]: 'Dussehra (Maha Navami)',
            [`${currentYear}-10-02`]: 'Dussehra (Vijaya Dashami)',
            [`${currentYear}-10-20`]: 'Diwali (Lakshmi Puja)',
            [`${currentYear}-10-21`]: 'Diwali (Govardhan Puja)',
            [`${currentYear}-11-05`]: 'Guru Nanak Jayanti',
            [`${currentYear}-12-25`]: 'Christmas',
            // 2026
            [`${nextYear}-01-01`]: 'New Year\'s Day',
            [`${nextYear}-01-14`]: 'Makar Sankranti / Pongal',
            [`${nextYear}-02-15`]: 'Maha Shivaratri',
            [`${nextYear}-03-03`]: 'Holi',
            [`${nextYear}-03-20`]: 'Eid-ul-Fitr',
            [`${nextYear}-03-26`]: 'Ram Navami',
            [`${nextYear}-03-30`]: 'Mahavir Jayanti',
            [`${nextYear}-04-03`]: 'Good Friday',
            [`${nextYear}-04-14`]: 'Dr. Ambedkar Jayanti',
            [`${nextYear}-05-01`]: 'Buddha Purnima',
            [`${nextYear}-05-27`]: 'Eid-ul-Adha (Bakrid)',
            [`${nextYear}-06-25`]: 'Muharram',
            [`${nextYear}-08-06`]: 'Janmashtami',
            [`${nextYear}-08-25`]: 'Milad-un-Nabi',
            [`${nextYear}-09-19`]: 'Dussehra (Maha Navami)',
            [`${nextYear}-09-20`]: 'Dussehra (Vijaya Dashami)',
            [`${nextYear}-11-08`]: 'Diwali (Lakshmi Puja)',
            [`${nextYear}-11-09`]: 'Diwali (Govardhan Puja)',
            [`${nextYear}-11-25`]: 'Guru Nanak Jayanti',
            [`${nextYear}-12-25`]: 'Christmas',
        };

        // State-specific holidays (by GST state code)
        this.stateHolidays = {
            // Karnataka (KA = 29)
            '29': {
                [`${currentYear}-11-01`]: 'Karnataka Rajyotsava',
                [`${nextYear}-11-01`]: 'Karnataka Rajyotsava',
            },
            // Maharashtra (MH = 27)
            '27': {
                [`${currentYear}-05-01`]: 'Maharashtra Day',
                [`${currentYear}-02-19`]: 'Chhatrapati Shivaji Jayanti',
                [`${nextYear}-05-01`]: 'Maharashtra Day',
                [`${nextYear}-02-19`]: 'Chhatrapati Shivaji Jayanti',
            },
            // Tamil Nadu (TN = 33)
            '33': {
                [`${currentYear}-01-15`]: 'Pongal (Thai Pongal)',
                [`${currentYear}-04-14`]: 'Tamil New Year',
                [`${nextYear}-01-15`]: 'Pongal (Thai Pongal)',
                [`${nextYear}-04-14`]: 'Tamil New Year',
            },
            // Gujarat (GJ = 24)
            '24': {
                [`${currentYear}-01-14`]: 'Uttarayan',
                [`${currentYear}-05-01`]: 'Gujarat Day',
                [`${nextYear}-01-14`]: 'Uttarayan',
                [`${nextYear}-05-01`]: 'Gujarat Day',
            },
            // Delhi (DL = 07)
            '07': {
                [`${currentYear}-11-01`]: 'Delhi Foundation Day',
                [`${nextYear}-11-01`]: 'Delhi Foundation Day',
            },
            // West Bengal (WB = 19)
            '19': {
                [`${currentYear}-05-09`]: 'Rabindra Jayanti',
                [`${currentYear}-01-23`]: 'Netaji Jayanti',
                [`${nextYear}-05-09`]: 'Rabindra Jayanti',
                [`${nextYear}-01-23`]: 'Netaji Jayanti',
            },
            // Kerala (KL = 32)
            '32': {
                [`${currentYear}-08-28`]: 'Onam',
                [`${currentYear}-11-01`]: 'Kerala Piravi',
                [`${nextYear}-08-17`]: 'Onam',
                [`${nextYear}-11-01`]: 'Kerala Piravi',
            },
            // Andhra Pradesh (AP = 37) / Telangana (TS = 36)
            '37': {
                [`${currentYear}-04-14`]: 'Telugu New Year (Ugadi)',
                [`${nextYear}-04-14`]: 'Telugu New Year (Ugadi)',
            },
            '36': {
                [`${currentYear}-04-14`]: 'Telugu New Year (Ugadi)',
                [`${currentYear}-06-02`]: 'Telangana Formation Day',
                [`${nextYear}-04-14`]: 'Telugu New Year (Ugadi)',
                [`${nextYear}-06-02`]: 'Telangana Formation Day',
            },
        };

        // Combine all holidays
        this.allHolidays = { ...this.nationalHolidays, ...this.gazettedHolidays };

        // Add state-specific holidays if state code is provided
        if (this.stateCode && this.stateHolidays[this.stateCode]) {
            this.allHolidays = { ...this.allHolidays, ...this.stateHolidays[this.stateCode] };
        }
    }

    /**
     * Get holiday name for a date (if any)
     */
    getHoliday(date) {
        const dateStr = date.toISOString().split('T')[0];
        return this.allHolidays[dateStr] || null;
    }

    /**
     * Check if a date is a Sunday
     */
    isSunday(date) {
        return date.getDay() === 0;
    }

    /**
     * Create holiday legend panel
     */
    createHolidayLegend() {
        this.holidayLegend = document.createElement('div');
        this.holidayLegend.className = 'holiday-legend-panel';
        this.holidayLegend.style.cssText = `
            background: linear-gradient(to right, #fffbeb, #fef3c7);
            border-bottom: 1px solid #fcd34d;
            padding: 6px 12px;
            font-size: 12px;
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
            flex-shrink: 0;
        `;

        // Holiday icon and label
        const labelSpan = document.createElement('span');
        labelSpan.innerHTML = '<i class="fas fa-calendar-check" style="color: #d97706; margin-right: 4px;"></i><strong style="color: #92400e;">Holidays:</strong>';
        labelSpan.style.whiteSpace = 'nowrap';
        this.holidayLegend.appendChild(labelSpan);

        // Container for holiday items
        this.holidayItemsContainer = document.createElement('div');
        this.holidayItemsContainer.style.cssText = `
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            align-items: center;
            flex: 1;
        `;
        this.holidayLegend.appendChild(this.holidayItemsContainer);

        // Legend for colors (Sunday indicator)
        const legendInfo = document.createElement('span');
        legendInfo.innerHTML = `
            <span style="display: inline-flex; align-items: center; gap: 4px; margin-left: 12px; color: #6b7280; font-size: 11px; border-left: 1px solid #d1d5db; padding-left: 12px;">
                <span style="width: 12px; height: 12px; background: #fee2e2; border: 1px solid #fca5a5; border-radius: 2px;"></span> Sunday
                <span style="width: 12px; height: 12px; background: #fef3c7; border: 1px solid #fcd34d; border-radius: 2px; margin-left: 8px;"></span> Holiday
            </span>
        `;
        this.holidayLegend.appendChild(legendInfo);

        this.mainWrapper.appendChild(this.holidayLegend);

        // Initial update
        this.updateHolidayLegend();
    }

    /**
     * Update holiday legend with visible holidays
     */
    updateHolidayLegend() {
        if (!this.holidayItemsContainer) return;

        // Get holidays in the visible date range (next 3 months from today for relevance)
        const visibleHolidays = [];
        const checkStart = new Date(this.today);
        const checkEnd = new Date(this.today);
        checkEnd.setMonth(checkEnd.getMonth() + 3);

        let currentDate = new Date(checkStart);
        while (currentDate <= checkEnd) {
            const holiday = this.getHoliday(currentDate);
            if (holiday) {
                visibleHolidays.push({
                    date: new Date(currentDate),
                    name: holiday
                });
            }
            currentDate.setDate(currentDate.getDate() + 1);
        }

        // Clear and rebuild
        this.holidayItemsContainer.innerHTML = '';

        if (visibleHolidays.length === 0) {
            const noHolidays = document.createElement('span');
            noHolidays.textContent = 'No holidays in next 3 months';
            noHolidays.style.color = '#9ca3af';
            noHolidays.style.fontStyle = 'italic';
            this.holidayItemsContainer.appendChild(noHolidays);
        } else {
            // Show up to 6 holidays
            const displayHolidays = visibleHolidays.slice(0, 6);
            displayHolidays.forEach(h => {
                const item = document.createElement('span');
                const dateStr = h.date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
                const isPast = h.date < this.today;
                item.innerHTML = `
                    <span style="
                        display: inline-flex;
                        align-items: center;
                        gap: 4px;
                        padding: 2px 8px;
                        background: ${isPast ? '#f3f4f6' : '#ffffff'};
                        border: 1px solid ${isPast ? '#d1d5db' : '#fcd34d'};
                        border-radius: 12px;
                        color: ${isPast ? '#9ca3af' : '#78350f'};
                        font-size: 11px;
                        ${isPast ? 'text-decoration: line-through;' : ''}
                    ">
                        <span style="font-weight: 600;">${dateStr}</span>
                        <span style="color: ${isPast ? '#9ca3af' : '#92400e'};">${h.name}</span>
                    </span>
                `;
                this.holidayItemsContainer.appendChild(item);
            });

            // Show "and X more" if there are more holidays
            if (visibleHolidays.length > 6) {
                const moreSpan = document.createElement('span');
                moreSpan.textContent = `+${visibleHolidays.length - 6} more`;
                moreSpan.style.cssText = 'color: #6b7280; font-size: 11px; font-style: italic;';
                this.holidayItemsContainer.appendChild(moreSpan);
            }
        }
    }

    /**
     * Get all holidays in a date range
     */
    getHolidaysInRange(startDate, endDate) {
        const holidays = [];
        let currentDate = new Date(startDate);
        while (currentDate <= endDate) {
            const holiday = this.getHoliday(currentDate);
            if (holiday) {
                holidays.push({
                    date: new Date(currentDate),
                    name: holiday
                });
            }
            currentDate.setDate(currentDate.getDate() + 1);
        }
        return holidays;
    }

    updateDateRange() {
        // Rolling year view (12 months / 52 weeks / 365 days)
        // Formula: 1 unit back + current + remaining to make ~12 months total
        //
        // Day view: 1 month back + 11 months forward = 365 days
        // Week view: 1 week back + 51 weeks forward = 52 weeks
        // Month view: 1 month back + 11 months forward = 12 months

        if (this.options.days) {
            // Day view - rolling year (365 days)
            this.viewType = 'day';

            this.startDate = new Date(this.today);
            this.startDate.setMonth(this.startDate.getMonth() - 1); // 1 month back
            this.startDate.setHours(0, 0, 0, 0);

            this.endDate = new Date(this.today);
            this.endDate.setMonth(this.endDate.getMonth() + 11); // 11 months forward
            this.endDate.setHours(23, 59, 59, 999);

            this.totalDays = Math.ceil((this.endDate - this.startDate) / (1000 * 60 * 60 * 24));
            this.options.dayWidth = 25; // Compact for many days

        } else if (this.options.weeks) {
            // Week view - rolling year (52 weeks)
            this.viewType = 'week';

            // Get start of last week (Monday)
            this.startDate = new Date(this.today);
            const dayOfWeek = this.startDate.getDay();
            const daysToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
            this.startDate.setDate(this.startDate.getDate() - daysToMonday - 7); // Last week's Monday
            this.startDate.setHours(0, 0, 0, 0);

            // End at 52 weeks total
            this.endDate = new Date(this.startDate);
            this.endDate.setDate(this.endDate.getDate() + (52 * 7) - 1);
            this.endDate.setHours(23, 59, 59, 999);

            this.totalDays = 52 * 7; // 52 weeks = 364 days
            this.options.dayWidth = 12; // Compact for many weeks

        } else {
            // Month view - rolling year (12 months)
            this.viewType = 'month';

            this.startDate = new Date(this.today);
            this.startDate.setMonth(this.startDate.getMonth() - 1); // 1 month back
            this.startDate.setDate(1); // First day
            this.startDate.setHours(0, 0, 0, 0);

            this.endDate = new Date(this.today);
            this.endDate.setMonth(this.endDate.getMonth() + 11); // 11 months forward
            this.endDate.setDate(0); // Last day of that month
            this.endDate.setHours(23, 59, 59, 999);

            this.totalDays = Math.ceil((this.endDate - this.startDate) / (1000 * 60 * 60 * 24));
            this.options.dayWidth = 5; // Compact for 12 months
        }
    }

    /**
     * Set zoom to day view (shows individual days)
     * @param {number} days - Number of days (typically 1, 3, or 7)
     */
    setDayZoom(days) {
        this.options.days = days;
        this.options.weeks = null;
        this.options.months = null;

        // Clear zoom highlights
        this._highlightMonth = null;
        this._highlightWeek = null;

        this.updateDateRange();
        this.render();

        // Update UI buttons
        this._updateZoomButtons('day');
    }

    /**
     * Set zoom to week view (shows weeks)
     * @param {number} weeks - Number of weeks (typically 6)
     */
    setWeekZoom(weeks = 6) {
        this.options.weeks = weeks;
        this.options.days = null;
        this.options.months = null;

        // Clear zoom highlights
        this._highlightMonth = null;
        this._highlightWeek = null;

        this.updateDateRange();
        this.render();

        // Update UI buttons
        this._updateZoomButtons('week');
    }

    render() {
        this.container.innerHTML = '';

        // Create main wrapper with flex column layout
        this.mainWrapper = document.createElement('div');
        this.mainWrapper.style.display = 'flex';
        this.mainWrapper.style.flexDirection = 'column';
        this.mainWrapper.style.width = '100%';
        this.mainWrapper.style.height = '100%';
        this.container.appendChild(this.mainWrapper);

        // Create fixed header wrapper (sticky)
        this.headerWrapper = document.createElement('div');
        this.headerWrapper.style.position = 'sticky';
        this.headerWrapper.style.top = '0';
        this.headerWrapper.style.zIndex = '10';
        this.headerWrapper.style.backgroundColor = '#ffffff';
        this.headerWrapper.style.overflowX = 'hidden';
        this.headerWrapper.style.flexShrink = '0';
        this.mainWrapper.appendChild(this.headerWrapper);

        // Create holiday legend panel (collapsible)
        this.createHolidayLegend();

        // Create scrollable body wrapper
        this.scrollWrapper = document.createElement('div');
        this.scrollWrapper.style.overflowX = 'auto';
        this.scrollWrapper.style.overflowY = 'auto';
        this.scrollWrapper.style.flex = '1';
        this.scrollWrapper.className = 'timeline-scroll-wrapper';
        this.mainWrapper.appendChild(this.scrollWrapper);

        // Sync horizontal scroll between header and body
        this.scrollWrapper.addEventListener('scroll', () => {
            this.headerWrapper.scrollLeft = this.scrollWrapper.scrollLeft;
        });

        this.createCanvas();
        this.draw();
        this.attachEventListeners();
        this.createTooltip();

        // Scroll to today after render
        this.scrollToToday();
    }

    createCanvas() {
        // Calculate canvas width based on total days and dayWidth (scrollable)
        const canvasWidth = Math.max(this.totalDays * this.options.dayWidth, this.container.clientWidth);
        const campaignCount = this.data.campaigns?.length || 0;

        // Calculate extra rows for sections
        // Section headers: Campaigns, Bulk Discount (if enabled), Loyalty Cards (if configured)
        const sectionHeaderHeight = 24;

        // Bulk section: only if enabled
        const bulkEnabled = this.data.bulk_config?.enabled || false;
        const bulkRowCount = bulkEnabled ? 1 : 0;

        // Loyalty section: only if there are card types
        const loyaltyRowCount = this.data.loyalty_periods?.length || 0;

        // Add extra row for max discount summary (always show when filtered)
        const summaryRowHeight = this._isFiltered ? this.options.rowHeight + 25 : 0;

        // Body height (without header)
        const bodyHeight =
            sectionHeaderHeight + (Math.max(campaignCount, 1)) * this.options.rowHeight + // Campaigns
            (bulkEnabled ? sectionHeaderHeight + bulkRowCount * this.options.rowHeight : 0) + // Bulk (if enabled)
            (loyaltyRowCount > 0 ? sectionHeaderHeight + loyaltyRowCount * this.options.rowHeight : 0) + // Loyalty (if configured)
            summaryRowHeight + 20; // Summary + padding

        const height = Math.max(bodyHeight, 200);

        // Create HEADER canvas (fixed)
        this.headerCanvas = document.createElement('canvas');
        this.headerCanvas.width = canvasWidth * 2; // For retina
        this.headerCanvas.height = this.options.headerHeight * 2;
        this.headerCanvas.style.width = canvasWidth + 'px';
        this.headerCanvas.style.height = this.options.headerHeight + 'px';
        this.headerCanvas.style.display = 'block';

        this.headerCtx = this.headerCanvas.getContext('2d');
        this.headerCtx.scale(2, 2); // Retina scaling

        this.headerWrapper.appendChild(this.headerCanvas);

        // Create BODY canvas (scrollable)
        this.canvas = document.createElement('canvas');
        this.canvas.width = canvasWidth * 2; // For retina
        this.canvas.height = height * 2;
        this.canvas.style.width = canvasWidth + 'px';
        this.canvas.style.height = height + 'px';
        this.canvas.style.display = 'block';

        this.ctx = this.canvas.getContext('2d');
        this.ctx.scale(2, 2); // Retina scaling

        // Append to scroll wrapper
        this.scrollWrapper.appendChild(this.canvas);
    }

    draw() {
        if (!this.ctx || !this.headerCtx) return;

        const width = this.canvas.width / 2;
        const height = this.canvas.height / 2;
        const headerWidth = this.headerCanvas.width / 2;

        // Clear header canvas
        this.headerCtx.fillStyle = '#ffffff';
        this.headerCtx.fillRect(0, 0, headerWidth, this.options.headerHeight);

        // Clear body canvas
        this.ctx.fillStyle = '#f9fafb';
        this.ctx.fillRect(0, 0, width, height);

        // Draw header on header canvas
        this.drawHeader();

        // Draw body content (grid, today marker, sections)
        this.drawGrid();
        this.drawTodayMarker();

        // Draw sections with headers (starting from Y=0 since header is separate)
        let currentY = 0;
        currentY = this.drawCampaignSection(currentY);
        currentY = this.drawBulkDiscountSection(currentY);
        currentY = this.drawLoyaltySection(currentY);

        this.drawOverlapWarnings();
        this.drawLegend();

        // Draw max discount summary row when filtered (fixed at bottom of canvas)
        if (this._isFiltered && this._applicableDiscounts) {
            // Fixed position at bottom - always at canvas height minus summary height
            const summaryY = height - this.options.rowHeight - 30;
            this.drawMaxDiscountSummary(summaryY);
        }
    }

    /**
     * Draw section header with icon
     */
    drawSectionHeader(y, title, icon, color) {
        const ctx = this.ctx;
        const width = this.canvas.width / 2;

        // Section header background
        ctx.fillStyle = '#f3f4f6';
        ctx.fillRect(0, y, width, 24);

        // Section title
        ctx.fillStyle = color || '#374151';
        ctx.font = 'bold 11px Inter, system-ui, sans-serif';
        ctx.fillText(`${icon} ${title}`, 10, y + 16);

        // Bottom border
        ctx.strokeStyle = '#e5e7eb';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(0, y + 24);
        ctx.lineTo(width, y + 24);
        ctx.stroke();

        return y + 24;
    }

    /**
     * Draw campaigns section
     * Respects visibility settings and VIP filtering
     */
    drawCampaignSection(startY) {
        // Check checkbox visibility
        if (this._visibilitySettings && this._visibilitySettings.campaigns === false) {
            return startY; // Hidden by checkbox
        }

        const campaigns = this.data.campaigns || [];
        let y = this.drawSectionHeader(startY, `CAMPAIGNS (${campaigns.length})`, '📢', '#3b82f6');

        if (campaigns.length === 0) {
            // Show empty state with appropriate message
            const ctx = this.ctx;
            ctx.fillStyle = '#9ca3af';
            ctx.font = 'italic 11px Inter, system-ui, sans-serif';

            // Different message based on filter context
            let message = 'No active campaigns in this period';
            if (this._isFiltered) {
                if (this._patientContext && !this._patientContext.is_special_group) {
                    message = 'No campaigns applicable (patient is not VIP)';
                } else if (this._itemContext && this._itemContext.item_id) {
                    message = `No campaigns for: ${this._itemContext.item_name || 'selected item'}`;
                }
            }
            ctx.fillText(message, 20, y + 22);
            return y + this.options.rowHeight;
        }

        // Draw campaign bars
        campaigns.forEach((campaign, index) => {
            this.drawCampaignBar(campaign, y + index * this.options.rowHeight);
        });

        return y + campaigns.length * this.options.rowHeight;
    }

    /**
     * Draw individual campaign bar
     */
    drawCampaignBar(campaign, y) {
        const ctx = this.ctx;
        const startDate = new Date(campaign.start_date);
        const endDate = new Date(campaign.end_date);

        // Skip if outside visible range
        if (endDate < this.startDate || startDate > this.endDate) return;

        const x1 = Math.max(this.dateToX(startDate), 0);
        const x2 = Math.min(this.dateToX(endDate), this.canvas.width / 2);
        const barHeight = this.options.rowHeight - 8;

        // Bar color based on type
        let color = this.options.colors.simple_discount;
        if (campaign.promotion_type === 'buy_x_get_y') {
            color = this.options.colors.buy_x_get_y;
        }

        // Draw bar
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.roundRect(x1, y + 4, Math.max(x2 - x1, 20), barHeight, 4);
        ctx.fill();

        // Personalized indicator (dashed border)
        if (campaign.is_personalized) {
            ctx.strokeStyle = this.options.colors.personalized;
            ctx.lineWidth = 2;
            ctx.setLineDash([4, 2]);
            ctx.stroke();
            ctx.setLineDash([]);
        }

        // Draft indicator (dotted border for editable campaigns)
        const status = campaign.status || 'approved';
        if (status === 'draft') {
            ctx.strokeStyle = '#6b7280'; // Gray
            ctx.lineWidth = 2;
            ctx.setLineDash([2, 2]);
            ctx.stroke();
            ctx.setLineDash([]);
        }

        // Pending approval indicator (solid yellow border)
        if (status === 'pending_approval') {
            ctx.strokeStyle = '#f59e0b'; // Amber
            ctx.lineWidth = 2;
            ctx.stroke();
        }

        // Rejected indicator (red border)
        if (status === 'rejected') {
            ctx.strokeStyle = '#ef4444'; // Red
            ctx.lineWidth = 2;
            ctx.stroke();
            // Semi-transparent overlay
            ctx.fillStyle = 'rgba(239, 68, 68, 0.2)';
            ctx.beginPath();
            ctx.roundRect(x1, y + 4, Math.max(x2 - x1, 20), barHeight, 4);
            ctx.fill();
        }

        // Special group indicator (star)
        if (campaign.target_special_group) {
            ctx.fillStyle = '#fbbf24';
            ctx.font = '10px Inter, system-ui, sans-serif';
            ctx.fillText('★', x1 + 4, y + 14);
        }

        // Campaign label with shadow for better contrast - black text
        ctx.save();
        ctx.shadowColor = 'rgba(255, 255, 255, 0.8)';
        ctx.shadowBlur = 2;
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 0;
        ctx.fillStyle = '#1f2937'; // Dark gray/black text
        ctx.font = 'bold 10px Inter, system-ui, sans-serif';
        const label = campaign.campaign_code || campaign.campaign_name;
        const discountText = campaign.discount_type === 'percentage'
            ? `${campaign.discount_value}%`
            : `₹${campaign.discount_value}`;
        const displayText = `${label} (${discountText})`;

        const textX = x1 + (campaign.target_special_group ? 16 : 6);
        ctx.fillText(displayText, textX, y + barHeight / 2 + 7, x2 - x1 - 20);
        ctx.restore();

        // Store bar bounds for interaction (hover, click, drag)
        campaign._bounds = { x1, y: y + 4, x2, height: barHeight };
    }

    /**
     * Draw bulk discount section
     * Shows based on:
     * - Hospital bulk discount enabled
     * - Filter context: if item selected, only show if item is bulk eligible
     * - Checkbox visibility setting
     */
    drawBulkDiscountSection(startY) {
        const bulkConfig = this.data.bulk_config;

        // Check if section should be hidden
        if (!bulkConfig || !bulkConfig.enabled) {
            return startY; // Not configured
        }

        // If filtered with patient/item context, check bulk eligibility
        // _showBulk is set in _updateSectionsVisibility based on API response
        if (this._isFiltered && this._itemContext && this._itemContext.item_id && !this._showBulk) {
            console.log('[Timeline] Hiding BULK section - item not bulk eligible');
            return startY; // Item not bulk eligible
        }

        // Check checkbox visibility
        if (this._visibilitySettings && this._visibilitySettings.bulk === false) {
            return startY; // Hidden by checkbox
        }

        let y = this.drawSectionHeader(startY, 'BULK DISCOUNT', '📦', '#f97316');

        const ctx = this.ctx;
        const width = this.canvas.width / 2;

        // If filtered with item context, show item-specific info
        if (this._isFiltered && this._applicableDiscounts?.bulk?.applicable) {
            const bulk = this._applicableDiscounts.bulk;
            const barHeight = this.options.rowHeight - 8;

            // Draw bar for applicable bulk discount
            ctx.fillStyle = this.options.colors.bulk;
            ctx.globalAlpha = 0.8;
            ctx.beginPath();
            ctx.roundRect(10, y + 4, width - 20, barHeight, 4);
            ctx.fill();
            ctx.globalAlpha = 1;

            // Label with item-specific discount
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 10px Inter, system-ui, sans-serif';
            const bulkLabel = `${bulk.item_name}: ${bulk.percent}% (min ${bulk.min_count} items)`;
            ctx.fillText(bulkLabel, 18, y + barHeight / 2 + 7);

            return y + this.options.rowHeight;
        }

        // Default: show bulk config bar
        const effectiveFrom = bulkConfig.effective_from ? new Date(bulkConfig.effective_from) : this.startDate;
        const x1 = Math.max(this.dateToX(effectiveFrom), 0);
        const x2 = width;
        const barHeight = this.options.rowHeight - 8;

        ctx.fillStyle = this.options.colors.bulk;
        ctx.globalAlpha = 0.7;
        ctx.beginPath();
        ctx.roundRect(x1, y + 4, x2 - x1, barHeight, 4);
        ctx.fill();
        ctx.globalAlpha = 1;

        // Bulk label with shadow for better contrast - black text
        ctx.save();
        ctx.shadowColor = 'rgba(255, 255, 255, 0.8)';
        ctx.shadowBlur = 2;
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 0;
        ctx.fillStyle = '#1f2937'; // Dark gray/black text
        ctx.font = 'bold 10px Inter, system-ui, sans-serif';
        const bulkLabel = `Min ${bulkConfig.min_service_count || bulkConfig.min_count || 5} items - Per-item discount applies`;
        ctx.fillText(bulkLabel, x1 + 8, y + barHeight / 2 + 7);
        ctx.restore();

        // Store bounds for hover interaction
        this._bulkBounds = {
            x1, y: y + 4, x2, height: barHeight,
            type: 'bulk',
            data: bulkConfig
        };

        return y + this.options.rowHeight;
    }

    /**
     * Draw loyalty cards section
     * Shows based on:
     * - Loyalty card types configured in hospital
     * - Filter context: if patient selected, only show if patient has valid loyalty card
     * - Checkbox visibility setting
     */
    drawLoyaltySection(startY) {
        const loyaltyPeriods = this.data.loyalty_periods || [];

        // Only show section if there are loyalty card types configured
        if (loyaltyPeriods.length === 0) {
            return startY; // Skip section entirely
        }

        // Check checkbox visibility
        if (this._visibilitySettings && this._visibilitySettings.loyalty === false) {
            return startY; // Hidden by checkbox
        }

        // If filtered with patient context, check if patient has valid loyalty card
        // _showLoyalty is set in _updateSectionsVisibility based on patient's loyalty card status
        if (this._isFiltered && this._patientContext && !this._showLoyalty) {
            console.log('[Timeline] Hiding LOYALTY section - patient has no valid loyalty card');
            return startY; // Patient doesn't have a valid loyalty card
        }

        const ctx = this.ctx;
        const width = this.canvas.width / 2;

        // If filtered with patient context and has valid loyalty card, show patient's specific card info
        if (this._isFiltered && this._patientContext && this._patientContext.has_loyalty_card) {
            let y = this.drawSectionHeader(startY, 'LOYALTY CARD (Patient)', '💳', '#a855f7');

            const barHeight = this.options.rowHeight - 8;

            // Show patient's loyalty card with validity info
            const loyaltyDiscount = this._applicableDiscounts?.loyalty;
            if (loyaltyDiscount && loyaltyDiscount.applicable) {
                // Valid loyalty card
                ctx.fillStyle = this.options.colors.loyalty;
                ctx.globalAlpha = 0.8;
                ctx.beginPath();
                ctx.roundRect(10, y + 4, width - 20, barHeight, 4);
                ctx.fill();
                ctx.globalAlpha = 1;

                // Label with card type and validity
                ctx.fillStyle = '#ffffff';
                ctx.font = 'bold 10px Inter, system-ui, sans-serif';
                const validUntil = loyaltyDiscount.valid_until ? ` (Valid until: ${loyaltyDiscount.valid_until})` : '';
                const label = `${loyaltyDiscount.card_type} - ${loyaltyDiscount.percent}% discount${validUntil}`;
                ctx.fillText(label, 18, y + barHeight / 2 + 7);

                // Add valid indicator
                ctx.fillStyle = '#22c55e'; // Green
                ctx.font = 'bold 10px Inter, system-ui, sans-serif';
                ctx.fillText('✓ ACTIVE', width - 80, y + barHeight / 2 + 7);
            } else {
                // Expired loyalty card
                ctx.fillStyle = '#9ca3af'; // Gray
                ctx.globalAlpha = 0.5;
                ctx.beginPath();
                ctx.roundRect(10, y + 4, width - 20, barHeight, 4);
                ctx.fill();
                ctx.globalAlpha = 1;

                ctx.fillStyle = '#ffffff';
                ctx.font = 'bold 10px Inter, system-ui, sans-serif';
                ctx.fillText('Loyalty Card - EXPIRED', 18, y + barHeight / 2 + 7);

                // Add expired indicator
                ctx.fillStyle = '#ef4444'; // Red
                ctx.fillText('✗ EXPIRED', width - 80, y + barHeight / 2 + 7);
            }

            return y + this.options.rowHeight;
        }

        // Default: show all loyalty card types
        let y = this.drawSectionHeader(startY, `LOYALTY CARDS (${loyaltyPeriods.length})`, '💳', '#a855f7');

        // Initialize loyalty bounds array
        this._loyaltyBounds = [];

        // Draw each loyalty card type as a bar
        loyaltyPeriods.forEach((cardType, index) => {
            const rowY = y + index * this.options.rowHeight;
            const barHeight = this.options.rowHeight - 8;
            const x1 = 10;
            const x2 = width - 10;

            // Loyalty is always active (no date range), so draw full width
            ctx.fillStyle = this.options.colors.loyalty;
            ctx.globalAlpha = 0.6;
            ctx.beginPath();
            ctx.roundRect(x1, rowY + 4, x2 - x1, barHeight, 4);
            ctx.fill();
            ctx.globalAlpha = 1;

            // Label with shadow for better contrast - black text
            ctx.save();
            ctx.shadowColor = 'rgba(255, 255, 255, 0.8)';
            ctx.shadowBlur = 2;
            ctx.shadowOffsetX = 0;
            ctx.shadowOffsetY = 0;
            ctx.fillStyle = '#1f2937'; // Dark gray/black text
            ctx.font = 'bold 10px Inter, system-ui, sans-serif';
            const label = `${cardType.card_type_name} - ${cardType.discount_percent}% discount`;
            ctx.fillText(label, 18, rowY + barHeight / 2 + 7);
            ctx.restore();

            // Store bounds for hover interaction
            this._loyaltyBounds.push({
                x1, y: rowY + 4, x2, height: barHeight,
                type: 'loyalty',
                data: cardType
            });
        });

        return y + loyaltyPeriods.length * this.options.rowHeight;
    }

    drawHeader() {
        const width = this.headerCanvas.width / 2;
        const ctx = this.headerCtx;

        // Header background
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, width, this.options.headerHeight);

        // Draw labels based on view type
        if (this.viewType === 'day') {
            this._drawDayHeader(ctx, width);
        } else if (this.viewType === 'week') {
            this._drawWeekHeader(ctx, width);
        } else {
            this._drawMonthHeader(ctx, width);
        }

        // Header bottom border
        ctx.strokeStyle = '#d1d5db';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(0, this.options.headerHeight - 1);
        ctx.lineTo(width, this.options.headerHeight - 1);
        ctx.stroke();
    }

    /**
     * Draw header for day view - shows individual days
     */
    _drawDayHeader(ctx, width) {
        const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        const monthRowHeight = 20; // Height for month header row
        const dayRowStart = monthRowHeight; // Y position where day info starts

        // Store holiday positions for hover detection
        this.holidayPositions = [];

        // First pass: Draw month header row
        let currentDate = new Date(this.startDate);
        let currentMonth = -1;
        let monthStartX = 0;

        while (currentDate <= this.endDate) {
            const x = this.dateToX(currentDate);
            const month = currentDate.getMonth();
            const year = currentDate.getFullYear();

            // If month changed, draw the previous month's header
            if (month !== currentMonth) {
                if (currentMonth !== -1) {
                    // Draw the previous month header
                    this._drawMonthHeaderBlock(ctx, monthStartX, x - monthStartX, currentMonth, year === this.today.getFullYear() + 1 ? year - 1 : this.today.getFullYear(), monthRowHeight);
                }
                monthStartX = x;
                currentMonth = month;
            }

            currentDate.setDate(currentDate.getDate() + 1);
        }
        // Draw the last month header
        if (currentMonth !== -1) {
            const endX = this.dateToX(this.endDate) + this.options.dayWidth;
            this._drawMonthHeaderBlock(ctx, monthStartX, endX - monthStartX, currentMonth, this.endDate.getFullYear(), monthRowHeight);
        }

        // Draw month row separator line
        ctx.strokeStyle = '#9ca3af';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(0, monthRowHeight);
        ctx.lineTo(width, monthRowHeight);
        ctx.stroke();

        // Second pass: Draw day columns
        currentDate = new Date(this.startDate);
        while (currentDate <= this.endDate) {
            const x = this.dateToX(currentDate);
            const isToday = this._isSameDay(currentDate, this.today);
            const isSunday = this.isSunday(currentDate);
            const holiday = this.getHoliday(currentDate);

            // Check if this day is in the highlighted week (from zoom)
            const isHighlightedWeek = this._highlightWeek && this._isInWeek(currentDate, this._highlightWeek);

            // Day column width
            const colWidth = this.options.dayWidth;

            // Background color priority: Today > Holiday > Sunday > Highlighted Week
            if (isToday) {
                ctx.fillStyle = '#dcfce7'; // Green-100 for today
                ctx.fillRect(x, dayRowStart, colWidth, this.options.headerHeight - dayRowStart);
            } else if (holiday) {
                ctx.fillStyle = '#fef3c7'; // Amber-100 for holiday
                ctx.fillRect(x, dayRowStart, colWidth, this.options.headerHeight - dayRowStart);
                // Store holiday position for tooltip
                this.holidayPositions.push({
                    x: x,
                    width: colWidth,
                    y: dayRowStart,
                    height: this.options.headerHeight - dayRowStart,
                    name: holiday,
                    date: new Date(currentDate)
                });
            } else if (isSunday) {
                ctx.fillStyle = '#fee2e2'; // Red-100 for Sunday
                ctx.fillRect(x, dayRowStart, colWidth, this.options.headerHeight - dayRowStart);
            } else if (isHighlightedWeek) {
                ctx.fillStyle = '#dbeafe'; // Blue-100 for zoomed week
                ctx.fillRect(x, dayRowStart, colWidth, this.options.headerHeight - dayRowStart);
            }

            // Day name (Sun, Mon, etc.)
            let dayTextColor = '#374151'; // Default gray
            if (isToday) {
                dayTextColor = '#166534'; // Dark green for today
            } else if (holiday) {
                dayTextColor = '#b45309'; // Amber for holiday
            } else if (isSunday) {
                dayTextColor = '#dc2626'; // Red for Sunday
            } else if (isHighlightedWeek) {
                dayTextColor = '#1e40af'; // Blue for highlighted
            }

            ctx.fillStyle = dayTextColor;
            ctx.font = (isToday || isSunday || holiday) ? 'bold 10px Inter, system-ui, sans-serif' : '10px Inter, system-ui, sans-serif';
            ctx.fillText(dayNames[currentDate.getDay()], x + 3, dayRowStart + 14);

            // Date number
            let dateTextColor = '#6b7280'; // Default gray
            if (isToday) {
                dateTextColor = '#22c55e'; // Green for today
            } else if (holiday) {
                dateTextColor = '#d97706'; // Amber for holiday
            } else if (isSunday) {
                dateTextColor = '#ef4444'; // Red for Sunday
            } else if (isHighlightedWeek) {
                dateTextColor = '#3b82f6'; // Blue for highlighted
            }

            ctx.fillStyle = dateTextColor;
            ctx.font = (isToday || isSunday || holiday) ? 'bold 14px Inter, system-ui, sans-serif' : '14px Inter, system-ui, sans-serif';
            ctx.fillText(currentDate.getDate().toString(), x + 3, dayRowStart + 32);

            // Holiday indicator dot
            if (holiday) {
                ctx.fillStyle = '#f59e0b'; // Amber-500
                ctx.beginPath();
                ctx.arc(x + colWidth - 6, dayRowStart + 8, 3, 0, 2 * Math.PI);
                ctx.fill();
            }

            // Separator line
            ctx.strokeStyle = this.options.colors.grid;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(x, dayRowStart);
            ctx.lineTo(x, this.options.headerHeight);
            ctx.stroke();

            currentDate.setDate(currentDate.getDate() + 1);
        }
    }

    /**
     * Draw a month header block
     */
    _drawMonthHeaderBlock(ctx, x, width, month, year, height) {
        const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                           'July', 'August', 'September', 'October', 'November', 'December'];

        // Check if this is the current month
        const isCurrentMonth = month === this.today.getMonth() && year === this.today.getFullYear();

        // Background for current month
        if (isCurrentMonth) {
            ctx.fillStyle = '#dbeafe'; // Blue-100
            ctx.fillRect(x, 0, width, height);
        }

        // Month name + Year
        ctx.fillStyle = isCurrentMonth ? '#1e40af' : '#374151';
        ctx.font = isCurrentMonth ? 'bold 12px Inter, system-ui, sans-serif' : '12px Inter, system-ui, sans-serif';
        const text = `${monthNames[month]} ${year}`;
        ctx.fillText(text, x + 5, 14);

        // Right border for month
        ctx.strokeStyle = '#9ca3af';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(x + width, 0);
        ctx.lineTo(x + width, height);
        ctx.stroke();
    }

    /**
     * Helper: Check if date is within a specific week
     */
    _isInWeek(date, weekStart) {
        const weekEnd = new Date(weekStart);
        weekEnd.setDate(weekEnd.getDate() + 6);
        weekEnd.setHours(23, 59, 59, 999);
        return date >= weekStart && date <= weekEnd;
    }

    /**
     * Draw header for week view - shows week numbers
     */
    _drawWeekHeader(ctx, width) {
        let currentDate = new Date(this.startDate);
        let weekNum = 0;

        while (currentDate <= this.endDate) {
            const x = this.dateToX(currentDate);
            const weekWidth = 7 * this.options.dayWidth;
            const isThisWeek = this._isThisWeek(currentDate);

            // Check if this week should be highlighted (from zoom)
            const isHighlightedMonth = this._highlightMonth &&
                currentDate.getMonth() === this._highlightMonth.getMonth() &&
                currentDate.getFullYear() === this._highlightMonth.getFullYear();

            // Highlight this week or highlighted month
            if (isThisWeek) {
                ctx.fillStyle = '#dbeafe'; // Blue-100
                ctx.fillRect(x, 0, weekWidth, this.options.headerHeight);
            } else if (isHighlightedMonth) {
                ctx.fillStyle = '#fef3c7'; // Amber-100 for zoomed month
                ctx.fillRect(x, 0, weekWidth, this.options.headerHeight);
            }

            // Week label
            const weekOfYear = this._getWeekNumber(currentDate);
            ctx.fillStyle = isThisWeek ? '#1e40af' : (isHighlightedMonth ? '#92400e' : '#374151');
            ctx.font = (isThisWeek || isHighlightedMonth) ? 'bold 12px Inter, system-ui, sans-serif' : '12px Inter, system-ui, sans-serif';
            ctx.fillText(`Week ${weekOfYear}`, x + 5, 18);

            // Date range for the week
            const weekEnd = new Date(currentDate);
            weekEnd.setDate(weekEnd.getDate() + 6);
            ctx.fillStyle = isThisWeek ? '#3b82f6' : (isHighlightedMonth ? '#b45309' : '#6b7280');
            ctx.font = '10px Inter, system-ui, sans-serif';
            const rangeText = `${currentDate.getDate()} ${currentDate.toLocaleDateString('en-US', { month: 'short' })} - ${weekEnd.getDate()} ${weekEnd.toLocaleDateString('en-US', { month: 'short' })}`;
            ctx.fillText(rangeText, x + 5, 36);

            // Separator line
            ctx.strokeStyle = this.options.colors.grid;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, this.options.headerHeight);
            ctx.stroke();

            currentDate.setDate(currentDate.getDate() + 7);
            weekNum++;
        }
    }

    /**
     * Draw header for month view - shows months
     */
    _drawMonthHeader(ctx, width) {
        ctx.fillStyle = '#374151';
        ctx.font = 'bold 12px Inter, system-ui, sans-serif';

        let currentMonth = new Date(this.startDate);
        currentMonth.setDate(1); // Ensure we start at first of month

        while (currentMonth <= this.endDate) {
            const x = this.dateToX(currentMonth);
            const isThisMonth = this._isSameMonth(currentMonth, this.today);

            // Calculate month width
            const nextMonth = new Date(currentMonth);
            nextMonth.setMonth(nextMonth.getMonth() + 1);
            const monthWidth = this.dateToX(nextMonth) - x;

            // Highlight current month
            if (isThisMonth) {
                ctx.fillStyle = '#dcfce7'; // Green-100
                ctx.fillRect(x, 0, monthWidth, this.options.headerHeight);
            }

            // Month name
            ctx.fillStyle = isThisMonth ? '#166534' : '#374151';
            ctx.font = isThisMonth ? 'bold 13px Inter, system-ui, sans-serif' : 'bold 12px Inter, system-ui, sans-serif';
            const monthName = currentMonth.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
            ctx.fillText(monthName, x + 5, 20);

            // Draw day markers (1, 8, 15, 22)
            ctx.font = '9px Inter, system-ui, sans-serif';
            ctx.fillStyle = '#9ca3af';
            [1, 8, 15, 22].forEach(day => {
                const dayDate = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), day);
                if (dayDate <= this.endDate) {
                    const dayX = this.dateToX(dayDate);
                    ctx.fillText(day.toString(), dayX + 2, 38);
                }
            });

            // Month separator line
            ctx.strokeStyle = this.options.colors.grid;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(x, 25);
            ctx.lineTo(x, this.options.headerHeight);
            ctx.stroke();

            currentMonth.setMonth(currentMonth.getMonth() + 1);
        }
    }

    /**
     * Helper: Check if two dates are the same day
     */
    _isSameDay(date1, date2) {
        return date1.getFullYear() === date2.getFullYear() &&
               date1.getMonth() === date2.getMonth() &&
               date1.getDate() === date2.getDate();
    }

    /**
     * Helper: Check if two dates are in the same month
     */
    _isSameMonth(date1, date2) {
        return date1.getFullYear() === date2.getFullYear() &&
               date1.getMonth() === date2.getMonth();
    }

    /**
     * Helper: Check if date is in the current week
     */
    _isThisWeek(weekStart) {
        const weekEnd = new Date(weekStart);
        weekEnd.setDate(weekEnd.getDate() + 6);
        return this.today >= weekStart && this.today <= weekEnd;
    }

    /**
     * Helper: Get ISO week number
     */
    _getWeekNumber(date) {
        const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
        const dayNum = d.getUTCDay() || 7;
        d.setUTCDate(d.getUTCDate() + 4 - dayNum);
        const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
        return Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
    }

    drawGrid() {
        const width = this.canvas.width / 2;
        const height = this.canvas.height / 2;
        const ctx = this.ctx;

        ctx.strokeStyle = this.options.colors.grid;
        ctx.lineWidth = 0.5;

        // Draw vertical grid lines based on view type (starting from Y=0 since header is separate)
        if (this.viewType === 'day') {
            // Day view: line between each day
            let currentDate = new Date(this.startDate);
            while (currentDate <= this.endDate) {
                const x = this.dateToX(currentDate);
                ctx.beginPath();
                ctx.moveTo(x, 0);
                ctx.lineTo(x, height);
                ctx.stroke();
                currentDate.setDate(currentDate.getDate() + 1);
            }
        } else if (this.viewType === 'week') {
            // Week view: line between each week
            let currentDate = new Date(this.startDate);
            while (currentDate <= this.endDate) {
                const x = this.dateToX(currentDate);
                ctx.beginPath();
                ctx.moveTo(x, 0);
                ctx.lineTo(x, height);
                ctx.stroke();
                currentDate.setDate(currentDate.getDate() + 7);
            }
        } else {
            // Month view: line for each week (Sundays)
            let currentDate = new Date(this.startDate);
            while (currentDate <= this.endDate) {
                if (currentDate.getDay() === 0) { // Sunday
                    const x = this.dateToX(currentDate);
                    ctx.beginPath();
                    ctx.moveTo(x, 0);
                    ctx.lineTo(x, height);
                    ctx.stroke();
                }
                currentDate.setDate(currentDate.getDate() + 1);
            }
        }

        // Horizontal lines for each row (starting from Y=0)
        const campaigns = this.data.campaigns || [];
        for (let i = 0; i <= campaigns.length + 1; i++) {
            const y = i * this.options.rowHeight;
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(width, y);
            ctx.stroke();
        }
    }

    drawTodayMarker() {
        const ctx = this.ctx;
        const height = this.canvas.height / 2;
        const x = this.dateToX(this.today);

        // Today line (starting from Y=0 since header is separate)
        ctx.strokeStyle = this.options.colors.today;
        ctx.lineWidth = 2;
        ctx.setLineDash([5, 3]);
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
        ctx.setLineDash([]);

        // Today label at top of body
        ctx.fillStyle = this.options.colors.today;
        ctx.font = 'bold 10px Inter, system-ui, sans-serif';
        ctx.fillText('Today', x - 15, 12);
    }

    drawBulkLine() {
        const bulkConfig = this.data.bulk_config;
        if (!bulkConfig || !bulkConfig.enabled || !bulkConfig.effective_from) return;

        const ctx = this.ctx;
        const height = this.canvas.height / 2;
        const effectiveDate = new Date(bulkConfig.effective_from);
        const x = this.dateToX(effectiveDate);

        // Bulk active horizontal line
        ctx.strokeStyle = this.options.colors.bulk;
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(x, height - 30);
        ctx.lineTo(this.canvas.width / 2, height - 30);
        ctx.stroke();

        // Start marker
        ctx.fillStyle = this.options.colors.bulk;
        ctx.beginPath();
        ctx.arc(x, height - 30, 5, 0, Math.PI * 2);
        ctx.fill();

        // Label
        ctx.font = '10px Inter, system-ui, sans-serif';
        ctx.fillText('Bulk Active', x + 10, height - 25);
    }

    drawCampaignBars() {
        const campaigns = this.data.campaigns || [];
        const ctx = this.ctx;

        campaigns.forEach((campaign, index) => {
            const y = this.options.headerHeight + (index + 1) * this.options.rowHeight;
            const startDate = new Date(campaign.start_date);
            const endDate = new Date(campaign.end_date);

            const x1 = this.dateToX(startDate);
            const x2 = this.dateToX(endDate);
            const barHeight = this.options.rowHeight - 8;

            // Bar color based on type
            const color = campaign.promotion_type === 'buy_x_get_y'
                ? this.options.colors.buy_x_get_y
                : this.options.colors.simple_discount;

            // Draw bar
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.roundRect(x1, y + 4, Math.max(x2 - x1, 20), barHeight, 4);
            ctx.fill();

            // Personalized indicator (dashed border)
            if (campaign.is_personalized) {
                ctx.strokeStyle = this.options.colors.personalized;
                ctx.lineWidth = 2;
                ctx.setLineDash([4, 2]);
                ctx.stroke();
                ctx.setLineDash([]);
            }

            // Inactive indicator (semi-transparent)
            if (!campaign.is_active) {
                ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
                ctx.beginPath();
                ctx.roundRect(x1, y + 4, Math.max(x2 - x1, 20), barHeight, 4);
                ctx.fill();
            }

            // Campaign code label
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 11px Inter, system-ui, sans-serif';
            const textWidth = ctx.measureText(campaign.campaign_code).width;
            if (x2 - x1 > textWidth + 10) {
                ctx.fillText(campaign.campaign_code, x1 + 8, y + barHeight / 2 + 8);
            }

            // Store bar bounds for interaction
            campaign._bounds = { x1, y: y + 4, x2, height: barHeight };
        });
    }

    drawOverlapWarnings() {
        const overlaps = this.data.overlaps || [];
        const ctx = this.ctx;
        const height = this.canvas.height / 2;

        overlaps.forEach(overlap => {
            const startDate = new Date(overlap.overlap_start);
            const endDate = new Date(overlap.overlap_end);
            const x1 = this.dateToX(startDate);
            const x2 = this.dateToX(endDate);

            // Draw only border/outline for overlap region (not fill) - starting from Y=0
            ctx.strokeStyle = '#fca5a5'; // Light red border (red-300)
            ctx.lineWidth = 2;
            ctx.setLineDash([4, 4]); // Dashed line
            ctx.strokeRect(x1, 5, x2 - x1, height - 10);
            ctx.setLineDash([]); // Reset dash

            // Draw subtle top indicator line
            ctx.strokeStyle = '#f87171'; // red-400
            ctx.lineWidth = 3;
            ctx.beginPath();
            ctx.moveTo(x1, 2);
            ctx.lineTo(x2, 2);
            ctx.stroke();

            // Warning icon at top center
            ctx.fillStyle = '#ef4444';
            ctx.font = 'bold 11px Inter, system-ui, sans-serif';
            ctx.fillText('⚠', x1 + (x2 - x1) / 2 - 6, 18);
        });
    }

    drawLegend() {
        // Legend is drawn in HTML, not canvas
    }

    dateToX(date) {
        const dateObj = date instanceof Date ? date : new Date(date);
        const daysDiff = Math.floor((dateObj - this.startDate) / (1000 * 60 * 60 * 24));
        return daysDiff * this.options.dayWidth;
    }

    xToDate(x) {
        const days = Math.floor(x / this.options.dayWidth);
        const date = new Date(this.startDate);
        date.setDate(date.getDate() + days);
        return date;
    }

    getCampaignAtPoint(x, y) {
        const campaigns = this.data.campaigns || [];
        for (const campaign of campaigns) {
            if (!campaign._bounds) continue;
            const b = campaign._bounds;
            if (x >= b.x1 && x <= b.x2 && y >= b.y && y <= b.y + b.height) {
                return campaign;
            }
        }
        return null;
    }

    /**
     * Get any item at point (campaign, bulk, or loyalty)
     * Returns { type: 'campaign'|'bulk'|'loyalty', data: object } or null
     */
    getItemAtPoint(x, y) {
        // Check campaigns first
        const campaign = this.getCampaignAtPoint(x, y);
        if (campaign) {
            return { type: 'campaign', data: campaign };
        }

        // Check bulk discount
        if (this._bulkBounds) {
            const b = this._bulkBounds;
            if (x >= b.x1 && x <= b.x2 && y >= b.y && y <= b.y + b.height) {
                return { type: 'bulk', data: b.data };
            }
        }

        // Check loyalty cards
        if (this._loyaltyBounds && this._loyaltyBounds.length > 0) {
            for (const bounds of this._loyaltyBounds) {
                if (x >= bounds.x1 && x <= bounds.x2 && y >= bounds.y && y <= bounds.y + bounds.height) {
                    return { type: 'loyalty', data: bounds.data };
                }
            }
        }

        return null;
    }

    getEdgeAtPoint(x, y, campaign) {
        if (!campaign || !campaign._bounds) return null;
        const b = campaign._bounds;
        const edgeThreshold = 8;

        if (Math.abs(x - b.x1) < edgeThreshold && y >= b.y && y <= b.y + b.height) {
            return 'start';
        }
        if (Math.abs(x - b.x2) < edgeThreshold && y >= b.y && y <= b.y + b.height) {
            return 'end';
        }
        return null;
    }

    // Event Handlers
    attachEventListeners() {
        // Body canvas events (campaigns, bulk, loyalty)
        this.canvas.addEventListener('click', this.onClick.bind(this));
        this.canvas.addEventListener('dblclick', this.onDoubleClick.bind(this));
        this.canvas.addEventListener('mousedown', this.onDragStart.bind(this));
        this.canvas.addEventListener('mousemove', this.onMouseMove.bind(this));
        this.canvas.addEventListener('mouseup', this.onDragEnd.bind(this));
        this.canvas.addEventListener('mouseleave', this.onMouseLeave.bind(this));

        // Header canvas events (zoom on click/double-click)
        this.headerCanvas.addEventListener('click', this.onHeaderClick.bind(this));
        this.headerCanvas.addEventListener('dblclick', this.onHeaderDoubleClick.bind(this));
        this.headerCanvas.addEventListener('mousemove', this.onHeaderMouseMove.bind(this));
        this.headerCanvas.addEventListener('mouseleave', this.onHeaderMouseLeave.bind(this));
    }

    /**
     * Handle single-click on header - ZOOM IN (with delay to detect double-click)
     * Month → Week, Week → Day
     */
    onHeaderClick(e) {
        // Clear any pending double-click detection
        if (this._headerClickTimeout) {
            clearTimeout(this._headerClickTimeout);
            this._headerClickTimeout = null;
        }

        const rect = this.headerCanvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const clickedDate = this.xToDate(x);

        // Delay single-click action to allow double-click detection
        this._headerClickTimeout = setTimeout(() => {
            this._headerClickTimeout = null;

            // Single-click = Zoom IN
            if (this.viewType === 'month') {
                // Zoom IN to week view centered on clicked month
                this.zoomToMonth(clickedDate);
            } else if (this.viewType === 'week') {
                // Zoom IN to day view centered on clicked week
                this.zoomToWeek(clickedDate);
            }
            // Day view - can't zoom in further, do nothing on single-click
        }, 250); // 250ms delay to detect double-click
    }

    /**
     * Handle double-click on header - ZOOM OUT
     * Day → Week, Week → Month
     */
    onHeaderDoubleClick(e) {
        // Cancel pending single-click action
        if (this._headerClickTimeout) {
            clearTimeout(this._headerClickTimeout);
            this._headerClickTimeout = null;
        }

        // Double-click = Zoom OUT
        if (this.viewType === 'day') {
            // Zoom OUT to week view
            this.zoomOut();
        } else if (this.viewType === 'week') {
            // Zoom OUT to month view
            this.setZoom(12);
        }
        // Month view - can't zoom out further, do nothing
    }

    /**
     * Handle mouse move on header - show appropriate zoom cursor
     */
    onHeaderMouseMove(e) {
        // Default cursor behavior based on view type
        if (this.viewType === 'month') {
            // Can only zoom in
            this.headerCanvas.style.cursor = 'zoom-in';
        } else if (this.viewType === 'week') {
            // Can zoom in (click) or out (double-click) - show crosshair
            this.headerCanvas.style.cursor = 'pointer';
        } else if (this.viewType === 'day') {
            // Can only zoom out
            this.headerCanvas.style.cursor = 'zoom-out';
        } else {
            this.headerCanvas.style.cursor = 'default';
        }
    }

    /**
     * Handle mouse leave on header
     */
    onHeaderMouseLeave() {
        this.headerCanvas.style.cursor = 'default';
    }

    /**
     * Zoom to week view centered on a specific month
     * @param {Date} date - Any date within the month to zoom into
     */
    zoomToMonth(date) {
        // Get first day of the month
        const monthStart = new Date(date.getFullYear(), date.getMonth(), 1);

        // Set to week view spanning 12 months (52 weeks) from 1 month before clicked month
        this.options.weeks = 52; // 12 months of weeks
        this.options.days = null;
        this.options.months = null;
        this.viewType = 'week';

        // Start from first Monday of the month before
        this.startDate = new Date(monthStart);
        this.startDate.setMonth(this.startDate.getMonth() - 1);
        // Find the Monday of that week
        const dayOfWeek = this.startDate.getDay();
        const daysToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
        this.startDate.setDate(this.startDate.getDate() - daysToMonday);
        this.startDate.setHours(0, 0, 0, 0);

        // End 12 months after start
        this.endDate = new Date(this.startDate);
        this.endDate.setMonth(this.endDate.getMonth() + 12);
        this.endDate.setHours(23, 59, 59, 999);

        this.totalDays = Math.ceil((this.endDate - this.startDate) / (1000 * 60 * 60 * 24));
        this.options.dayWidth = 12; // Slightly narrower for more weeks

        // Store clicked date for highlighting
        this._highlightMonth = new Date(date.getFullYear(), date.getMonth(), 1);

        this.render();

        // Scroll to the clicked month
        this.scrollToDate(monthStart);

        // Update UI buttons
        this._updateZoomButtons('week');
    }

    /**
     * Zoom to day view centered on a specific week
     * @param {Date} date - Any date within the week to zoom into
     */
    zoomToWeek(date) {
        // Get Monday of the clicked week
        const dayOfWeek = date.getDay();
        const daysToMonday = dayOfWeek === 0 ? 6 : dayOfWeek - 1;
        const weekStart = new Date(date);
        weekStart.setDate(weekStart.getDate() - daysToMonday);
        weekStart.setHours(0, 0, 0, 0);

        // Set to day view - 365 days (rolling year)
        this.options.days = 365;
        this.options.weeks = null;
        this.options.months = null;
        this.viewType = 'day';

        // Start from 1 week before the clicked week
        this.startDate = new Date(weekStart);
        this.startDate.setDate(this.startDate.getDate() - 7);
        this.startDate.setHours(0, 0, 0, 0);

        // End 12 months after start
        this.endDate = new Date(this.startDate);
        this.endDate.setMonth(this.endDate.getMonth() + 12);
        this.endDate.setHours(23, 59, 59, 999);

        this.totalDays = Math.ceil((this.endDate - this.startDate) / (1000 * 60 * 60 * 24));
        this.options.dayWidth = 25; // Narrower for more days

        // Store clicked date for highlighting
        this._highlightWeek = new Date(weekStart);

        this.render();

        // Scroll to the clicked week
        this.scrollToDate(weekStart);

        // Update UI buttons
        this._updateZoomButtons('day');
    }

    /**
     * Update zoom button UI to reflect current view
     */
    _updateZoomButtons(viewType) {
        // Deactivate all view buttons
        document.querySelectorAll('.timeline-view-btn').forEach(btn => {
            btn.classList.remove('active', 'bg-blue-100', 'text-blue-700', 'dark:bg-blue-900', 'dark:text-blue-300');
            btn.classList.add('bg-white', 'text-gray-700', 'dark:bg-gray-700', 'dark:text-white');
        });

        // Activate appropriate button based on view type
        const btn = document.querySelector(`.timeline-view-btn[data-view="${viewType}"]`);
        if (btn) {
            btn.classList.add('active', 'bg-blue-100', 'text-blue-700', 'dark:bg-blue-900', 'dark:text-blue-300');
            btn.classList.remove('bg-white', 'text-gray-700', 'dark:bg-gray-700', 'dark:text-white');
        }
    }

    onDoubleClick(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left + (this.scrollWrapper?.scrollLeft || 0);

        // Get the date at click position
        const clickedDate = this.xToDate(x);

        // Zoom to 1 month view centered on clicked month
        this.options.months = 1;

        // Set start date to first of clicked month
        this.startDate = new Date(clickedDate.getFullYear(), clickedDate.getMonth(), 1);
        this.endDate = new Date(clickedDate.getFullYear(), clickedDate.getMonth() + 1, 0);
        this.totalDays = Math.ceil((this.endDate - this.startDate) / (1000 * 60 * 60 * 24));
        this.options.dayWidth = 25;

        // Re-render
        this.render();

        // Update zoom buttons UI if they exist
        document.querySelectorAll('.timeline-zoom-btn').forEach(btn => {
            btn.classList.remove('active', 'bg-blue-100', 'text-blue-700', 'dark:bg-blue-900', 'dark:text-blue-300');
            btn.classList.add('bg-white', 'text-gray-700', 'dark:bg-gray-700', 'dark:text-white');
            if (btn.dataset.months === '1') {
                btn.classList.add('active', 'bg-blue-100', 'text-blue-700', 'dark:bg-blue-900', 'dark:text-blue-300');
                btn.classList.remove('bg-white', 'text-gray-700', 'dark:bg-gray-700', 'dark:text-white');
            }
        });

        // Dispatch event for external handlers
        this.container.dispatchEvent(new CustomEvent('timeline-zoom', {
            detail: { months: 1, date: clickedDate }
        }));
    }

    onClick(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        // Add scroll offset for campaign detection
        const scrollX = this.scrollWrapper?.scrollLeft || 0;
        const adjustedX = x + scrollX;

        const campaign = this.getCampaignAtPoint(adjustedX, y);
        if (campaign && !this.dragState) {
            window.location.href = `/promotions/campaigns/${campaign.campaign_id}`;
        }
    }

    onDragStart(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        // Add scroll offset for campaign detection
        const scrollX = this.scrollWrapper?.scrollLeft || 0;
        const adjustedX = x + scrollX;

        const campaign = this.getCampaignAtPoint(adjustedX, y);
        if (campaign) {
            const edge = this.getEdgeAtPoint(adjustedX, y, campaign);

            // Check if campaign can be edited based on status, launch state, and edge
            const canEdit = this.canEditCampaign(campaign, edge);
            if (!canEdit.allowed) {
                this.canvas.style.cursor = 'not-allowed';
                return; // Don't start drag
            }

            this.dragState = {
                campaign,
                edge,
                startX: x,  // Keep raw x for drag delta calculation
                originalStart: campaign.start_date,
                originalEnd: campaign.end_date,
                requiresReapproval: canEdit.requiresReapproval,
                isRunning: canEdit.isRunning || false,
                canEditStart: canEdit.canEditStart,
                canEditEnd: canEdit.canEditEnd
            };

            this.canvas.style.cursor = edge ? 'ew-resize' : 'move';
        }
    }

    /**
     * Check if a campaign can be edited via drag
     * Rules:
     * - Draft: can edit freely (start and end dates)
     * - Approved but not started (start_date > today): can edit both dates, requires re-approval
     * - Approved and started (start_date <= today): can only edit END date, requires re-approval
     * - Pending approval or rejected: cannot edit via drag
     *
     * Returns: { allowed, requiresReapproval, canEditStart, canEditEnd, reason }
     */
    canEditCampaign(campaign, edge = null) {
        const status = campaign.status || 'approved';
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        const startDate = campaign.start_date ? new Date(campaign.start_date) : null;
        if (startDate) startDate.setHours(0, 0, 0, 0);

        const hasStarted = startDate && startDate <= today;

        // Draft campaigns can always be edited fully
        if (status === 'draft') {
            return {
                allowed: true,
                requiresReapproval: false,
                canEditStart: true,
                canEditEnd: true
            };
        }

        // Approved campaigns
        if (status === 'approved') {
            // Not yet started - can edit both dates but requires re-approval
            if (!hasStarted) {
                return {
                    allowed: true,
                    requiresReapproval: true,
                    canEditStart: true,
                    canEditEnd: true
                };
            }

            // Already started - can only edit end date
            // If trying to edit start or move entire bar, deny
            if (edge === 'start' || edge === null) {
                return {
                    allowed: false,
                    reason: 'Campaign has started. Only end date can be modified.',
                    canEditStart: false,
                    canEditEnd: true
                };
            }

            // Editing end date is allowed - stays approved (immediate effect)
            return {
                allowed: true,
                requiresReapproval: false,  // Running campaigns stay approved
                isRunning: true,  // Flag to show different confirmation
                canEditStart: false,
                canEditEnd: true
            };
        }

        // Pending approval or rejected - cannot edit via drag
        return {
            allowed: false,
            reason: `${status} campaigns cannot be edited via drag.`,
            canEditStart: false,
            canEditEnd: false
        };
    }

    onMouseMove(e) {
        const rect = this.canvas.getBoundingClientRect();
        // For mouse events on canvas, we need raw coordinates without scroll adjustment
        // because canvas coordinates are relative to canvas element, not scroll position
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        if (this.dragState) {
            // Dragging - update preview
            this.draw();

            const deltaX = x - this.dragState.startX;
            const deltaDays = Math.round(deltaX / this.options.dayWidth);

            const dragCampaign = this.dragState.campaign;
            const b = dragCampaign._bounds;

            // Draw drag preview
            this.ctx.fillStyle = 'rgba(59, 130, 246, 0.5)';
            this.ctx.beginPath();
            if (this.dragState.edge === 'start') {
                this.ctx.roundRect(b.x1 + deltaX, b.y, b.x2 - b.x1 - deltaX, b.height, 4);
            } else if (this.dragState.edge === 'end') {
                this.ctx.roundRect(b.x1, b.y, b.x2 - b.x1 + deltaX, b.height, 4);
            } else {
                this.ctx.roundRect(b.x1 + deltaX, b.y, b.x2 - b.x1, b.height, 4);
            }
            this.ctx.fill();
        } else {
            // Hover state - need to add scroll offset for item detection
            const scrollX = this.scrollWrapper?.scrollLeft || 0;
            const adjustedX = x + scrollX;

            // Check for any item (campaign, bulk, loyalty)
            const item = this.getItemAtPoint(adjustedX, y);

            if (item && item.type === 'campaign') {
                const campaign = item.data;
                const edge = this.getEdgeAtPoint(adjustedX, y, campaign);
                const canEdit = this.canEditCampaign(campaign, edge);

                // Show appropriate cursor based on edit permissions
                if (edge && canEdit.allowed) {
                    this.canvas.style.cursor = 'ew-resize';
                } else if (edge && !canEdit.allowed) {
                    // Cannot edit this edge - show not-allowed cursor
                    this.canvas.style.cursor = 'not-allowed';
                    this.showTooltip(e, item);
                } else if (!edge && !canEdit.allowed) {
                    // Cannot move campaign - show not-allowed for center drag
                    this.canvas.style.cursor = 'not-allowed';
                    this.showTooltip(e, item);
                } else {
                    this.canvas.style.cursor = 'pointer';
                    this.showTooltip(e, item);
                }
            } else if (item) {
                // Bulk or Loyalty - show tooltip but not clickable for editing
                this.canvas.style.cursor = 'pointer';
                this.showTooltip(e, item);
            } else {
                this.canvas.style.cursor = 'default';
                this.hideTooltip();
            }
        }
    }

    async onDragEnd(e) {
        if (!this.dragState) return;

        const rect = this.canvas.getBoundingClientRect();
        const x = e.clientX - rect.left;

        const deltaX = x - this.dragState.startX;
        const deltaDays = Math.round(deltaX / this.options.dayWidth);

        if (Math.abs(deltaDays) > 0) {
            const campaign = this.dragState.campaign;
            let newStart = new Date(this.dragState.originalStart);
            let newEnd = new Date(this.dragState.originalEnd);

            if (this.dragState.edge === 'start') {
                newStart.setDate(newStart.getDate() + deltaDays);
            } else if (this.dragState.edge === 'end') {
                newEnd.setDate(newEnd.getDate() + deltaDays);
            } else {
                newStart.setDate(newStart.getDate() + deltaDays);
                newEnd.setDate(newEnd.getDate() + deltaDays);
            }

            // Validate
            if (newEnd >= newStart) {
                // Show appropriate confirmation based on campaign state
                if (this.dragState.isRunning) {
                    // Running campaign - end date change takes effect immediately
                    const confirmed = confirm(
                        'This campaign is currently running.\n\n' +
                        'The end date change will take effect immediately.\n\n' +
                        'Do you want to continue?'
                    );
                    if (!confirmed) {
                        this.dragState = null;
                        this.canvas.style.cursor = 'default';
                        this.draw();
                        return;
                    }
                } else if (this.dragState.requiresReapproval) {
                    // Not-yet-started approved campaign - requires re-approval
                    const confirmed = confirm(
                        'This approved campaign has not yet started.\n\n' +
                        'Editing it will reset its status to Draft and require re-approval.\n\n' +
                        'Do you want to continue?'
                    );
                    if (!confirmed) {
                        this.dragState = null;
                        this.canvas.style.cursor = 'default';
                        this.draw();
                        return;
                    }
                }

                try {
                    const response = await fetch('/promotions/api/timeline-update', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            campaign_id: campaign.campaign_id,
                            start_date: newStart.toISOString().split('T')[0],
                            end_date: newEnd.toISOString().split('T')[0]
                        })
                    });

                    const result = await response.json();
                    if (result.success) {
                        // Update local data
                        campaign.start_date = newStart.toISOString().split('T')[0];
                        campaign.end_date = newEnd.toISOString().split('T')[0];
                        // Update status if it was reset to draft
                        if (result.status_changed) {
                            campaign.status = 'draft';
                        }
                    } else {
                        console.error('Failed to update:', result.message);
                        alert(result.message || 'Failed to update campaign dates');
                    }
                } catch (error) {
                    console.error('Error updating dates:', error);
                }
            }
        }

        this.dragState = null;
        this.canvas.style.cursor = 'default';
        this.draw();
    }

    onMouseLeave() {
        this.hideTooltip();
        if (this.dragState) {
            this.dragState = null;
            this.canvas.style.cursor = 'default';
            this.draw();
        }
    }

    // Tooltip
    createTooltip() {
        this.tooltip = document.createElement('div');
        // Use fixed positioning to avoid overflow clipping issues
        this.tooltip.className = 'fixed hidden bg-gray-900 text-white text-xs rounded-lg px-3 py-2 z-50 shadow-lg';
        this.tooltip.style.pointerEvents = 'none';
        this.tooltip.style.maxWidth = '250px';
        document.body.appendChild(this.tooltip);
    }

    showTooltip(e, item) {
        if (!this.tooltip) return;

        let html = '';

        if (item.type === 'campaign') {
            const campaign = item.data;
            const discount = campaign.discount_type === 'percentage'
                ? `${campaign.discount_value}%`
                : `₹${campaign.discount_value}`;
            const status = campaign.status || 'approved';

            // Status badge colors
            const statusColors = {
                'draft': 'bg-gray-500',
                'pending_approval': 'bg-yellow-500',
                'approved': 'bg-green-500',
                'rejected': 'bg-red-500'
            };
            const statusLabels = {
                'draft': 'Draft',
                'pending_approval': 'Pending',
                'approved': 'Approved',
                'rejected': 'Rejected'
            };

            html = `
                <div class="font-bold">${campaign.campaign_code}</div>
                <div>${campaign.campaign_name}</div>
                <div class="mt-1">
                    <span class="inline-block px-1.5 py-0.5 rounded text-xs ${statusColors[status] || 'bg-gray-500'}">${statusLabels[status] || status}</span>
                </div>
                <div class="mt-1 text-gray-300">
                    ${campaign.start_date} to ${campaign.end_date}
                </div>
                <div class="text-green-300">${discount} off</div>
                <div class="text-gray-400">Uses: ${campaign.current_uses || 0}${campaign.max_total_uses ? '/' + campaign.max_total_uses : ''}</div>
                ${status !== 'draft' ? '<div class="mt-1 text-yellow-300 text-xs"><i class="fas fa-lock mr-1"></i>Dates locked (approved)</div>' : '<div class="mt-1 text-blue-300 text-xs"><i class="fas fa-arrows-alt mr-1"></i>Drag to change dates</div>'}
            `;
        } else if (item.type === 'bulk') {
            const bulk = item.data;
            html = `
                <div class="font-bold text-orange-300">Bulk Discount</div>
                <div class="mt-1">Min items: ${bulk.min_service_count || bulk.min_count || 5}</div>
                <div class="text-gray-300">Each item gets individual discount based on its bulk discount %</div>
                ${bulk.effective_from ? `<div class="text-gray-400 mt-1">Effective from: ${bulk.effective_from}</div>` : ''}
                <div class="text-orange-300 mt-1">Buy more, save more!</div>
            `;
        } else if (item.type === 'loyalty') {
            const loyalty = item.data;
            html = `
                <div class="font-bold text-purple-300">${loyalty.card_type_name}</div>
                <div class="text-green-300 mt-1">${loyalty.discount_percent}% discount</div>
                ${loyalty.description ? `<div class="text-gray-300 mt-1">${loyalty.description}</div>` : ''}
                <div class="text-gray-400 mt-1">Applies to all eligible items</div>
            `;
        }

        this.tooltip.innerHTML = html;

        // Position tooltip using viewport coordinates (fixed positioning)
        this.tooltip.style.left = (e.clientX + 15) + 'px';
        this.tooltip.style.top = (e.clientY - 80) + 'px';
        this.tooltip.classList.remove('hidden');
    }

    hideTooltip() {
        if (this.tooltip) {
            this.tooltip.classList.add('hidden');
        }
    }

    // Public Methods
    setZoom(months) {
        this.options.months = months;
        this.options.days = null;  // Clear day view when switching to month view
        this.options.weeks = null; // Clear week view when switching to month view

        // Clear zoom highlights
        this._highlightMonth = null;
        this._highlightWeek = null;

        this.updateDateRange();
        this.render();

        // Update UI buttons
        this._updateZoomButtons('month');
    }

    /**
     * Zoom out one level (day -> week -> month)
     */
    zoomOut() {
        if (this.viewType === 'day') {
            // Zoom out to week view
            this.setWeekZoom(26);
        } else if (this.viewType === 'week') {
            // Zoom out to month view
            this.setZoom(3);
        }
        // Month view - can't zoom out further

        // Clear highlights
        this._highlightMonth = null;
        this._highlightWeek = null;
    }

    scrollToToday() {
        if (!this.scrollWrapper) return;
        const x = this.dateToX(this.today);
        const containerWidth = this.scrollWrapper.clientWidth;
        // Center today in the visible area
        const scrollPos = Math.max(0, x - containerWidth / 2);
        this.scrollWrapper.scrollLeft = scrollPos;
        // Sync header scroll
        if (this.headerWrapper) {
            this.headerWrapper.scrollLeft = scrollPos;
        }
    }

    scrollToDate(date) {
        if (!this.scrollWrapper) return;
        const x = this.dateToX(date);
        const containerWidth = this.scrollWrapper.clientWidth;
        const scrollPos = Math.max(0, x - containerWidth / 2);
        this.scrollWrapper.scrollLeft = scrollPos;
        // Sync header scroll
        if (this.headerWrapper) {
            this.headerWrapper.scrollLeft = scrollPos;
        }
    }


    async load() {
        try {
            const response = await fetch('/promotions/api/timeline-data');
            this.data = await response.json();
            this.render();
        } catch (error) {
            console.error('Error loading timeline data:', error);
        }
    }

    updateData(newData) {
        this.data = newData;
        this.render();
    }

    // =========================================================================
    // MAX DISCOUNT SUMMARY ROW
    // =========================================================================

    /**
     * Draw the max discount summary row at the bottom of the timeline
     * Shows combined maximum discount from all sources when filters are applied
     * @param {number} startY - The Y position to draw the summary row at
     */
    drawMaxDiscountSummary(startY) {
        const ctx = this.ctx;
        const width = this.canvas.width / 2;
        const discounts = this._applicableDiscounts;

        // Use passed Y position with some padding
        const summaryY = startY + 10;
        const rowHeight = this.options.rowHeight + 5;

        // Draw summary background
        ctx.fillStyle = '#fef3c7'; // Amber-100 background
        ctx.fillRect(0, summaryY, width, rowHeight);

        // Draw top border
        ctx.strokeStyle = '#f59e0b'; // Amber-500
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(0, summaryY);
        ctx.lineTo(width, summaryY);
        ctx.stroke();

        // Calculate max discount
        const maxDiscountInfo = this._calculateMaxDiscount(discounts);

        // Draw warning icon and label
        ctx.fillStyle = '#92400e'; // Amber-800
        ctx.font = 'bold 12px Inter, system-ui, sans-serif';
        ctx.fillText('⚠ MAX DISCOUNT:', 10, summaryY + 20);

        // Draw max discount value (large, prominent)
        ctx.fillStyle = '#dc2626'; // Red-600 for warning
        ctx.font = 'bold 18px Inter, system-ui, sans-serif';
        ctx.fillText(`${maxDiscountInfo.totalPercent.toFixed(1)}%`, 140, summaryY + 22);

        // Draw breakdown
        ctx.fillStyle = '#78350f'; // Amber-900
        ctx.font = '11px Inter, system-ui, sans-serif';
        let breakdownX = 200;

        if (maxDiscountInfo.campaignPercent > 0) {
            ctx.fillStyle = '#3b82f6'; // Blue for campaigns
            ctx.fillText(`Campaign: ${maxDiscountInfo.campaignPercent}%`, breakdownX, summaryY + 20);
            breakdownX += 105;
        }

        if (maxDiscountInfo.bulkPercent > 0) {
            ctx.fillStyle = '#f97316'; // Orange for bulk
            ctx.fillText(`Bulk: ${maxDiscountInfo.bulkPercent}%`, breakdownX, summaryY + 20);
            breakdownX += 75;
        }

        if (maxDiscountInfo.loyaltyPercent > 0) {
            ctx.fillStyle = '#a855f7'; // Purple for loyalty
            ctx.fillText(`Loyalty: ${maxDiscountInfo.loyaltyPercent}%`, breakdownX, summaryY + 20);
            breakdownX += 95;
        }

        if (maxDiscountInfo.standardPercent > 0) {
            ctx.fillStyle = '#6b7280'; // Gray for standard
            ctx.fillText(`Standard: ${maxDiscountInfo.standardPercent}%`, breakdownX, summaryY + 20);
            breakdownX += 100;
        }

        // Draw stacking mode indicator
        ctx.fillStyle = '#6b7280'; // Gray-500
        ctx.font = 'italic 10px Inter, system-ui, sans-serif';
        const stackingText = maxDiscountInfo.stackingMode === 'additional'
            ? '(Additive)'
            : '(Best wins)';
        ctx.fillText(stackingText, breakdownX, summaryY + 20);

        // Draw warning message if discount is high
        if (maxDiscountInfo.totalPercent > 30) {
            ctx.fillStyle = '#dc2626';
            ctx.font = 'bold 10px Inter, system-ui, sans-serif';
            ctx.fillText('⚠ High discount - review promotion overlap!', 10, summaryY + 35);
        }
    }

    /**
     * Calculate the maximum possible discount from all sources
     * Uses API-provided max_discount_percent and discount_breakdown if available
     * @param {Object} discounts - The applicable discounts object
     * @returns {Object} - { totalPercent, campaignPercent, bulkPercent, loyaltyPercent, standardPercent, stackingMode }
     */
    _calculateMaxDiscount(discounts) {
        // If API provided pre-calculated values, use them
        if (discounts.max_discount_percent !== undefined && discounts.discount_breakdown) {
            return {
                totalPercent: discounts.max_discount_percent || 0,
                campaignPercent: discounts.discount_breakdown.campaign || 0,
                bulkPercent: discounts.discount_breakdown.bulk || 0,
                loyaltyPercent: discounts.discount_breakdown.loyalty || 0,
                standardPercent: discounts.discount_breakdown.standard || 0,
                stackingMode: discounts.stacking_mode || 'absolute'
            };
        }

        // Fallback: calculate from individual discounts
        let campaignPercent = 0;
        let bulkPercent = 0;
        let loyaltyPercent = 0;
        let standardPercent = 0;
        let stackingMode = discounts.stacking_mode || 'absolute';

        // Get max campaign discount
        if (discounts.campaigns && discounts.campaigns.length > 0) {
            campaignPercent = Math.max(...discounts.campaigns
                .filter(c => c.discount_type === 'percentage')
                .map(c => c.discount_value || 0), 0);
        }

        // Get bulk discount
        if (discounts.bulk && discounts.bulk.applicable) {
            bulkPercent = discounts.bulk.percent || 0;
        }

        // Get loyalty discount
        if (discounts.loyalty && discounts.loyalty.applicable) {
            loyaltyPercent = discounts.loyalty.percent || 0;
        }

        // Get standard discount
        if (discounts.standard && discounts.standard.applicable) {
            standardPercent = discounts.standard.percent || 0;
        }

        // Calculate total based on stacking mode
        let totalPercent;
        if (stackingMode === 'additional') {
            // Additive mode: Campaign (P1) + max(Bulk, Loyalty) at P2
            const p2Max = Math.max(bulkPercent, loyaltyPercent);
            totalPercent = campaignPercent + p2Max;
        } else {
            // Absolute mode: Best discount wins by priority
            // P1: Campaign, P2: Bulk/Loyalty, P4: Standard
            if (campaignPercent > 0) {
                totalPercent = campaignPercent;
            } else if (bulkPercent > 0 || loyaltyPercent > 0) {
                totalPercent = Math.max(bulkPercent, loyaltyPercent);
            } else {
                totalPercent = standardPercent;
            }
        }

        return {
            totalPercent,
            campaignPercent,
            bulkPercent,
            loyaltyPercent,
            standardPercent,
            stackingMode
        };
    }

    /**
     * Set visibility settings for different discount sections
     * Called from dashboard checkbox filters
     * @param {Object} settings - { campaigns: bool, bulk: bool, loyalty: bool, standard: bool }
     */
    setVisibilitySettings(settings) {
        this._visibilitySettings = settings;
        this.render();
    }

    /**
     * Get current visibility settings
     */
    getVisibilitySettings() {
        return this._visibilitySettings || {
            campaigns: true,
            bulk: true,
            loyalty: true,
            standard: true
        };
    }

    // =========================================================================
    // FILTER METHODS - For showing applicable campaigns based on selection
    // =========================================================================

    /**
     * Set filtered campaigns and highlight applicable discounts
     * Called when user applies patient/service/medicine filter
     *
     * @param {Array} campaigns - Array of campaign objects that apply
     * @param {Object} discounts - Object with discount details { bulk, loyalty, campaigns, max_discount_percent, discount_breakdown }
     * @param {Object} patientContext - Optional patient context { is_special_group, has_loyalty_card, loyalty_card_valid }
     * @param {Object} itemContext - Optional item context { item_type, item_id, item_name }
     */
    setFilteredCampaigns(campaigns, discounts = null, patientContext = null, itemContext = null) {
        // Store original data for clearFilter
        if (!this._originalData) {
            this._originalData = JSON.parse(JSON.stringify(this.data));
        }

        this._isFiltered = true;
        this._applicableDiscounts = discounts;
        this._patientContext = patientContext;
        this._itemContext = itemContext;

        // Update campaigns with filtered data
        this.data.campaigns = campaigns;

        // Update bulk/loyalty visibility based on filter context
        // If patient is selected, only show loyalty if patient has a valid card
        // If service/medicine is selected, only show bulk if item is bulk eligible
        this._updateSectionsVisibility();

        // Re-render with filtered view
        this.render();

        // Show filter info overlay if discounts provided
        if (discounts) {
            this._showFilterInfo(discounts);
        }
    }

    /**
     * Update sections visibility based on filter context
     * - Loyalty: Only show if patient selected AND has valid loyalty card
     * - Bulk: Only show if item selected AND item is bulk eligible
     */
    _updateSectionsVisibility() {
        // For loyalty section - if patient selected, use patient context
        if (this._patientContext) {
            this._showLoyalty = this._patientContext.has_loyalty_card && this._patientContext.loyalty_card_valid;
            console.log('[Timeline] Patient context:', this._patientContext);
            console.log('[Timeline] _showLoyalty:', this._showLoyalty,
                '(has_card:', this._patientContext.has_loyalty_card,
                'valid:', this._patientContext.loyalty_card_valid, ')');
        } else {
            this._showLoyalty = true; // No patient filter, show all loyalty cards
            console.log('[Timeline] No patient context, showing all loyalty cards');
        }

        // For bulk section - if item selected, use discount applicability
        if (this._itemContext && this._itemContext.item_id) {
            this._showBulk = this._applicableDiscounts?.bulk?.applicable || false;
            console.log('[Timeline] Item context:', this._itemContext);
            console.log('[Timeline] _showBulk:', this._showBulk,
                '(bulk.applicable:', this._applicableDiscounts?.bulk?.applicable, ')');
        } else {
            this._showBulk = true; // No item filter, show bulk if enabled
            console.log('[Timeline] No item context, showing bulk if enabled');
        }

        console.log('[Timeline] Visibility - showLoyalty:', this._showLoyalty, 'showBulk:', this._showBulk);
    }

    /**
     * Clear filter and restore all campaigns
     */
    clearFilter() {
        if (this._originalData) {
            this.data = JSON.parse(JSON.stringify(this._originalData));
        }
        this._isFiltered = false;
        this._applicableDiscounts = null;
        this._patientContext = null;
        this._itemContext = null;
        this._showLoyalty = true;
        this._showBulk = true;
        this._hideFilterInfo();
        this.render();
    }

    /**
     * Show filter information overlay
     */
    _showFilterInfo(discounts) {
        // Remove existing overlay if any
        this._hideFilterInfo();

        // Store reference for cleanup
        const self = this;

        const overlay = document.createElement('div');
        overlay.id = 'timeline-filter-info';
        // Use fixed positioning so overlay survives render() cycles
        overlay.className = 'fixed bg-white dark:bg-gray-800 rounded-lg shadow-lg p-3 text-sm z-50 max-w-xs';
        overlay.style.pointerEvents = 'auto';

        let html = '<div class="font-semibold text-gray-900 dark:text-white mb-2 pr-6"><i class="fas fa-filter mr-1 text-blue-500"></i>Applicable Discounts</div>';

        // Show campaign discounts
        if (discounts.campaigns && discounts.campaigns.length > 0) {
            html += '<div class="mb-2">';
            html += '<div class="text-xs text-gray-500 uppercase mb-1">Campaigns</div>';
            discounts.campaigns.forEach(c => {
                const discountText = c.discount_type === 'percentage' ? `${c.discount_value}%` : `₹${c.discount_value}`;
                html += `<div class="flex justify-between items-center py-1 border-b border-gray-100 dark:border-gray-700">
                    <span class="text-gray-700 dark:text-gray-300">${c.campaign_code || c.campaign_name}</span>
                    <span class="font-medium text-green-600">${discountText}</span>
                </div>`;
            });
            html += '</div>';
        }

        // Show bulk discount
        if (discounts.bulk && discounts.bulk.applicable) {
            html += '<div class="mb-2">';
            html += '<div class="text-xs text-gray-500 uppercase mb-1">Bulk Discount</div>';
            html += `<div class="flex justify-between items-center py-1">
                <span class="text-gray-700 dark:text-gray-300">Item bulk discount</span>
                <span class="font-medium text-orange-600">${discounts.bulk.percent}%</span>
            </div>`;
            html += '</div>';
        }

        // Show loyalty discount
        if (discounts.loyalty && discounts.loyalty.applicable) {
            html += '<div>';
            html += '<div class="text-xs text-gray-500 uppercase mb-1">Loyalty Discount</div>';
            html += `<div class="flex justify-between items-center py-1">
                <span class="text-gray-700 dark:text-gray-300">${discounts.loyalty.card_type}</span>
                <span class="font-medium text-purple-600">${discounts.loyalty.percent}%</span>
            </div>`;
            html += '</div>';
        }

        // No discounts found
        if ((!discounts.campaigns || discounts.campaigns.length === 0) &&
            (!discounts.bulk || !discounts.bulk.applicable) &&
            (!discounts.loyalty || !discounts.loyalty.applicable)) {
            html = '<div class="text-gray-500"><i class="fas fa-info-circle mr-1"></i>No applicable discounts found</div>';
        }

        overlay.innerHTML = html;

        // Add close button
        const closeBtn = document.createElement('button');
        closeBtn.className = 'absolute top-1 right-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 p-2 rounded';
        closeBtn.innerHTML = '<i class="fas fa-times"></i>';
        closeBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            self._hideFilterInfo();
        });
        overlay.appendChild(closeBtn);

        // Click anywhere on overlay to dismiss
        overlay.style.cursor = 'pointer';
        overlay.title = 'Click to dismiss';
        overlay.addEventListener('click', function(e) {
            // Don't dismiss if clicking the close button (already handled)
            if (e.target === closeBtn || closeBtn.contains(e.target)) return;
            self._hideFilterInfo();
        });

        // Position fixed relative to viewport, near the container
        const containerRect = this.container.getBoundingClientRect();
        overlay.style.top = (containerRect.top + 10) + 'px';
        overlay.style.left = (containerRect.left + 10) + 'px';

        // Append to body so it survives render() cycles
        document.body.appendChild(overlay);

        // Auto-dismiss after 8 seconds
        this._filterInfoTimeout = setTimeout(() => {
            self._hideFilterInfo();
        }, 8000);
    }

    /**
     * Hide filter information overlay
     */
    _hideFilterInfo() {
        // Clear auto-dismiss timeout
        if (this._filterInfoTimeout) {
            clearTimeout(this._filterInfoTimeout);
            this._filterInfoTimeout = null;
        }

        const existing = document.getElementById('timeline-filter-info');
        if (existing) {
            existing.remove();
        }
    }

    /**
     * Check if timeline is currently filtered
     */
    isFiltered() {
        return this._isFiltered === true;
    }
}

// RoundRect polyfill for older browsers
if (!CanvasRenderingContext2D.prototype.roundRect) {
    CanvasRenderingContext2D.prototype.roundRect = function (x, y, width, height, radius) {
        if (width < 2 * radius) radius = width / 2;
        if (height < 2 * radius) radius = height / 2;
        this.moveTo(x + radius, y);
        this.arcTo(x + width, y, x + width, y + height, radius);
        this.arcTo(x + width, y + height, x, y + height, radius);
        this.arcTo(x, y + height, x, y, radius);
        this.arcTo(x, y, x + width, y, radius);
        this.closePath();
    };
}

// Export for global use
window.PromotionTimeline = PromotionTimeline;
