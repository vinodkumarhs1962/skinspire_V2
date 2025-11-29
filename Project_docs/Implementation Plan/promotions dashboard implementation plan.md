# PROMOTIONS DASHBOARD - Comprehensive Implementation Plan

 Executive Summary

 Build a Promotions Dashboard - a decision-making tool for planning, visualizing, and managing all types of promotions (discounts and campaigns). The       
 dashboard features an integrated timeline view for a 3-month planning horizon with simulation capabilities to preview applicable promotions for any        
 service/medicine.

 Key Terminology: "Promotions" encompasses all discount types:
 - Campaign Promotions (simple discount, buy X get Y)
 - Bulk Promotions (quantity-based)
 - Loyalty Promotions (card-based)
 - Standard Promotions (item-level default)

 ---
 Part 1: Business Rules Reference

 1.1 Campaign Promotion Rules

 | Rule                | Field                | Values                             | Description                                        |
 |---------------------|----------------------|------------------------------------|----------------------------------------------------|
 | Visibility          | is_personalized      | true/false                         | Public (auto-apply) vs Private (manual code entry) |
 | Auto-Apply          | auto_apply           | true/false                         | Automatically apply when conditions met            |
 | Validity            | start_date, end_date | Date                               | Active only within this period                     |
 | Total Usage Cap     | max_total_uses       | Integer                            | Maximum uses across all patients                   |
 | Per-Patient Cap     | max_uses_per_patient | Integer                            | Maximum uses per patient                           |
 | Min Purchase        | min_purchase_amount  | Decimal                            | Minimum invoice amount required                    |
 | Max Discount Cap    | max_discount_amount  | Decimal                            | Maximum discount in currency                       |
 | Promotion Type      | promotion_type       | simple_discount, buy_x_get_y       | Type of promotion                                  |
 | Discount Type       | discount_type        | percentage, fixed_amount           | How discount is calculated                         |
 | Target Scope        | applies_to           | all, services, medicines, packages | Which items eligible                               |
 | Specific Items      | specific_items       | JSON array                         | Specific item IDs if not "all"                     |
 | Priority            | -                    | 1 (Highest)                        | Always wins over other discounts                   |
 | Max Discount Bypass | -                    | Yes                                | Campaigns bypass item's max_discount cap           |

 1.2 Bulk Promotion Rules

 | Rule                 | Field                           | Location | Description                      |
 |----------------------|---------------------------------|----------|----------------------------------|
 | Enable/Disable       | bulk_discount_enabled           | Hospital | Master switch for bulk discounts |
 | Min Quantity         | bulk_discount_min_service_count | Hospital | Threshold (default: 5)           |
 | Effective Date       | bulk_discount_effective_from    | Hospital | Only active after this date      |
 | Service Eligibility  | bulk_discount_percent > 0       | Service  | Item is eligible if % > 0        |
 | Medicine Eligibility | bulk_discount_percent > 0       | Medicine | Item is eligible if % > 0        |
 | Package Eligibility  | -                               | -        | NOT eligible (by design)         |
 | Priority             | -                               | 2        | Lower than campaigns             |
 | Max Discount         | max_discount                    | Item     | Respects cap                     |

 1.3 Loyalty Promotion Rules

 | Rule                | Field                  | Location             | Description                    |
 |---------------------|------------------------|----------------------|--------------------------------|
 | Card Types          | discount_percent       | LoyaltyCardType      | Discount % per card tier       |
 | Patient Requirement | wallet_status='active' | PatientLoyaltyWallet | Must have active wallet        |
 | Discount Mode       | loyalty_discount_mode  | Hospital             | How loyalty combines with bulk |
 | - Absolute          | 'absolute'             | Hospital             | Pick MAX(bulk%, loyalty%)      |
 | - Additional        | 'additional'           | Hospital             | Stack: bulk% + loyalty%        |
 | Priority            | -                      | 2                    | Same as bulk                   |
 | Max Discount        | max_discount           | Item                 | Respects cap                   |

 1.4 Standard Promotion Rules

 | Rule          | Field                     | Location                 | Description                           |
 |---------------|---------------------------|--------------------------|---------------------------------------|
 | Fallback Only | -                         | -                        | Only when no other discount qualifies |
 | Item-Level    | standard_discount_percent | Service/Medicine/Package | Default discount                      |
 | Priority      | -                         | 4 (Lowest)               | Fallback only                         |
 | Max Discount  | max_discount              | Item                     | Respects cap                          |

 1.5 Best Discount Determination (Priority System)

 ┌─────────────────────────────────────────────────────────────────┐
 │  PRIORITY 1: CAMPAIGN PROMOTIONS                                │
 │  ✓ If campaign conditions met → APPLY (bypasses max cap)        │
 │  ✓ Other eligible discounts stored in metadata only             │
 ├─────────────────────────────────────────────────────────────────┤
 │  PRIORITY 2: BULK + LOYALTY PROMOTIONS                          │
 │  ✓ If loyalty_discount_mode = 'absolute':                       │
 │      → Apply MAX(bulk%, loyalty%)                               │
 │  ✓ If loyalty_discount_mode = 'additional':                     │
 │      → Apply (bulk% + loyalty%), capped at max_discount         │
 ├─────────────────────────────────────────────────────────────────┤
 │  PRIORITY 4: STANDARD PROMOTIONS                                │
 │  ✓ Fallback if nothing else applies                             │
 │  ✓ Capped at max_discount                                       │
 └─────────────────────────────────────────────────────────────────┘

 ---
 Part 2: Dashboard Architecture

 2.1 Dashboard Overview

 ┌─────────────────────────────────────────────────────────────────────────┐
 │  PROMOTIONS DASHBOARD                                                    │
 │  Decision-making tool for planning and managing all promotion types      │
 ├─────────────────────────────────────────────────────────────────────────┤
 │                                                                          │
 │  ┌────────────────────────────────────────────────────────────────────┐ │
 │  │                    INTEGRATED TIMELINE VIEW                         │ │
 │  │  Planning horizon: 3 months (configurable 1M/3M/6M)                │ │
 │  │                                                                     │ │
 │  │  - Campaign Promotions (colored bars)                              │ │
 │  │  - Bulk Discount Period (horizontal line with effective date)      │ │
 │  │  - Loyalty Card Periods (tier markers)                             │ │
 │  │                                                                     │ │
 │  │  Interactive: Click, Drag to move, Resize dates, Overlap warnings │ │
 │  └────────────────────────────────────────────────────────────────────┘ │
 │                                                                          │
 │  ┌────────────────────────────────────────────────────────────────────┐ │
 │  │                    SIMULATION PANEL                                 │ │
 │  │  Select Service/Medicine → Preview all applicable promotions        │ │
 │  │  Shows which promotions would apply and calculated discount         │ │
 │  └────────────────────────────────────────────────────────────────────┘ │
 │                                                                          │
 │  ┌────────────────────────────────────────────────────────────────────┐ │
 │  │  TABS: [Campaigns] [Bulk Config] [Loyalty Config] [Analytics]      │ │
 │  │                                                                     │ │
 │  │  Universal Engine CRUD for each promotion type                     │ │
 │  └────────────────────────────────────────────────────────────────────┘ │
 │                                                                          │
 └─────────────────────────────────────────────────────────────────────────┘

 2.2 File Structure

 app/
 ├── config/modules/
 │   └── promotion_config.py (NEW - Entity configuration)
 │
 ├── views/
 │   └── promotion_views.py (NEW - Routes & handlers)
 │
 ├── services/
 │   └── promotion_dashboard_service.py (NEW - Business logic)
 │
 ├── templates/
 │   └── promotions/
 │       ├── dashboard.html (NEW - Main dashboard)
 │       ├── timeline.html (NEW - Full-page timeline)
 │       ├── simulate.html (NEW - Simulation panel)
 │       │
 │       ├── campaigns/
 │       │   ├── list.html (Universal Engine list)
 │       │   ├── create.html (Universal Engine create)
 │       │   └── edit.html (Universal Engine edit)
 │       │
 │       ├── bulk/
 │       │   └── config.html (Bulk discount settings)
 │       │
 │       ├── loyalty/
 │       │   ├── config.html (Loyalty settings)
 │       │   └── card_types.html (Card type management)
 │       │
 │       └── components/
 │           ├── summary_cards.html (Dashboard metrics)
 │           ├── timeline_chart.html (Timeline component)
 │           ├── simulation_panel.html (Simulation UI)
 │           └── overlap_warnings.html (Overlap alerts)
 │
 ├── static/
 │   ├── js/components/
 │   │   ├── promotion_timeline.js (NEW - Interactive timeline)
 │   │   ├── promotion_simulator.js (NEW - Simulation logic)
 │   │   └── promotion_form.js (NEW - Dynamic forms)
 │   │
 │   └── css/components/
 │       └── promotion_dashboard.css (NEW - Using existing classes)
 │
 └── migrations/
     └── create_promotion_analytics_views.sql (NEW - Analytics views)

 ---
 Part 3: Backend Implementation

 3.1 Entity Configuration (promotion_config.py)

 Following Universal Engine pattern from existing configs:

 # Campaign Promotion Fields
 CAMPAIGN_FIELDS = [
     FieldDefinition(name="campaign_code", label="Code", field_type=FieldType.TEXT,
                     show_in_list=True, searchable=True, sortable=True, required=True),
     FieldDefinition(name="campaign_name", label="Name", field_type=FieldType.TEXT,
                     show_in_list=True, searchable=True, required=True),
     FieldDefinition(name="promotion_type", label="Type", field_type=FieldType.SELECT,
                     show_in_list=True, filterable=True,
                     options=[('simple_discount','Simple Discount'),('buy_x_get_y','Buy X Get Y')]),
     FieldDefinition(name="discount_type", label="Discount Type", field_type=FieldType.SELECT,
                     options=[('percentage','Percentage'),('fixed_amount','Fixed Amount')]),
     FieldDefinition(name="discount_value", label="Value", field_type=FieldType.DECIMAL),
     FieldDefinition(name="start_date", label="Start Date", field_type=FieldType.DATE,
                     show_in_list=True, sortable=True, filterable=True),
     FieldDefinition(name="end_date", label="End Date", field_type=FieldType.DATE,
                     show_in_list=True, sortable=True),
     FieldDefinition(name="is_personalized", label="Private", field_type=FieldType.BOOLEAN),
     FieldDefinition(name="is_active", label="Status", field_type=FieldType.BOOLEAN,
                     show_in_list=True, filterable=True),
     FieldDefinition(name="current_uses", label="Usage", field_type=FieldType.INTEGER,
                     show_in_list=True, readonly=True),
     FieldDefinition(name="max_total_uses", label="Max Uses", field_type=FieldType.INTEGER),
 ]

 # Sections for form layout
 SECTIONS = [
     SectionDefinition(name="basic", label="Basic Information", icon="fas fa-info-circle"),
     SectionDefinition(name="discount", label="Discount Configuration", icon="fas fa-percent"),
     SectionDefinition(name="validity", label="Validity & Limits", icon="fas fa-calendar"),
     SectionDefinition(name="targeting", label="Targeting", icon="fas fa-crosshairs"),
     SectionDefinition(name="visibility", label="Visibility", icon="fas fa-eye"),
 ]

 # Actions
 ACTIONS = [
     ActionDefinition(id="create", label="New Campaign", icon="fas fa-plus",
                      button_type=ButtonType.PRIMARY, show_in_list_toolbar=True),
     ActionDefinition(id="toggle", label="Toggle Status", icon="fas fa-toggle-on",
                      button_type=ButtonType.WARNING, requires_selection=True),
     ActionDefinition(id="duplicate", label="Duplicate", icon="fas fa-copy",
                      button_type=ButtonType.SECONDARY, requires_selection=True),
 ]

 3.2 Dashboard Service (promotion_dashboard_service.py)

 class PromotionDashboardService:
     """Service for Promotions Dashboard operations"""

     # ==================== TIMELINE DATA ====================
     def get_timeline_data(self, hospital_id, start_date, end_date):
         """Get all promotion data for timeline visualization"""
         return {
             'campaigns': self._get_campaign_timeline(hospital_id, start_date, end_date),
             'bulk_config': self._get_bulk_timeline(hospital_id),
             'loyalty_periods': self._get_loyalty_timeline(hospital_id),
             'overlaps': self._detect_overlaps(hospital_id, start_date, end_date)
         }

     def update_campaign_dates(self, campaign_id, start_date, end_date):
         """Update campaign dates (for drag-resize in timeline)"""
         # Validate no conflicts, update dates

     def _detect_overlaps(self, hospital_id, start_date, end_date):
         """Detect overlapping campaigns targeting same items"""
         # Return list of overlapping campaign pairs with warning severity

     # ==================== SIMULATION ====================
     def simulate_promotions(self, hospital_id, item_id, item_type,
                            quantity=1, patient_id=None, simulation_date=None):
         """Simulate which promotions would apply to an item"""
         return {
             'item': {'id': item_id, 'type': item_type, 'name': '...'},
             'applicable_promotions': [
                 {
                     'type': 'campaign',
                     'name': 'DIWALI SALE',
                     'discount_percent': 20,
                     'discount_amount': 200,
                     'priority': 1,
                     'would_apply': True,  # Winner
                     'reason': 'Highest priority - campaign promotion'
                 },
                 {
                     'type': 'bulk',
                     'name': 'Bulk Discount',
                     'discount_percent': 10,
                     'discount_amount': 100,
                     'priority': 2,
                     'would_apply': False,
                     'reason': 'Lower priority than campaign'
                 },
                 # ... more
             ],
             'final_discount': {
                 'type': 'campaign',
                 'name': 'DIWALI SALE',
                 'percent': 20,
                 'amount': 200
             },
             'original_price': 1000,
             'final_price': 800
         }

     # ==================== CRUD OPERATIONS ====================
     def get_all_campaigns(self, hospital_id, filters=None, pagination=None):
         """Get campaigns with Universal Engine pattern"""

     def create_campaign(self, hospital_id, data):
         """Create new campaign with validation"""

     def update_campaign(self, hospital_id, campaign_id, data):
         """Update campaign"""

     def toggle_campaign_status(self, hospital_id, campaign_id):
         """Toggle active/inactive"""

     def duplicate_campaign(self, hospital_id, campaign_id):
         """Create copy of existing campaign"""

     # ==================== BULK CONFIG ====================
     def get_bulk_config(self, hospital_id):
         """Get bulk discount configuration"""

     def update_bulk_config(self, hospital_id, data):
         """Update hospital bulk settings"""

     def get_bulk_eligible_items(self, hospital_id, item_type='service'):
         """Get items with bulk_discount_percent > 0"""

     def update_item_bulk_eligibility(self, hospital_id, item_id, item_type, percent):
         """Set bulk discount percent for item"""

     # ==================== LOYALTY CONFIG ====================
     def get_loyalty_config(self, hospital_id):
         """Get loyalty discount configuration"""

     def update_loyalty_mode(self, hospital_id, mode):
         """Update loyalty_discount_mode (absolute/additional)"""

     def get_card_types(self, hospital_id):
         """Get all loyalty card types"""

     def create_card_type(self, hospital_id, data):
         """Create new card type"""

     def update_card_type(self, hospital_id, card_type_id, data):
         """Update card type"""

     # ==================== ANALYTICS ====================
     def get_dashboard_summary(self, hospital_id):
         """Get summary cards data"""
         return {
             'active_campaigns': 12,
             'total_discount_mtd': 45200,
             'most_used_campaign': {'name': 'DIWALI', 'uses': 156},
             'upcoming_campaigns': 3,
             'expiring_soon': 2  # Within 7 days
         }

     def get_discount_breakdown(self, hospital_id, date_range):
         """Get discount by type (pie chart data)"""

     def get_usage_trends(self, hospital_id, campaign_id=None, granularity='daily'):
         """Get usage over time (line chart data)"""

     def get_top_campaigns(self, hospital_id, limit=10):
         """Get top performing campaigns by usage/revenue"""

 3.3 Routes (promotion_views.py)

 promotion_views_bp = Blueprint('promotion_views', __name__, url_prefix='/promotions')

 # ==================== DASHBOARD ====================
 @promotion_views_bp.route('/dashboard')
 def dashboard():
     """Main promotions dashboard"""

 @promotion_views_bp.route('/timeline')
 def timeline_fullpage():
     """Full-page timeline view"""

 # ==================== CAMPAIGNS CRUD ====================
 @promotion_views_bp.route('/campaigns')
 def campaign_list():
     """List all campaigns (Universal Engine list)"""

 @promotion_views_bp.route('/campaigns/create', methods=['GET', 'POST'])
 def campaign_create():
     """Create campaign (Universal Engine create)"""

 @promotion_views_bp.route('/campaigns/<uuid:campaign_id>/edit', methods=['GET', 'POST'])
 def campaign_edit(campaign_id):
     """Edit campaign (Universal Engine edit)"""

 @promotion_views_bp.route('/campaigns/<uuid:campaign_id>/toggle', methods=['POST'])
 def campaign_toggle(campaign_id):
     """Toggle campaign status"""

 @promotion_views_bp.route('/campaigns/<uuid:campaign_id>/duplicate', methods=['POST'])
 def campaign_duplicate(campaign_id):
     """Duplicate campaign"""

 # ==================== BULK CONFIG ====================
 @promotion_views_bp.route('/bulk/config', methods=['GET', 'POST'])
 def bulk_config():
     """Bulk discount configuration page"""

 @promotion_views_bp.route('/bulk/eligible-items')
 def bulk_eligible_items():
     """List and manage bulk-eligible items"""

 # ==================== LOYALTY CONFIG ====================
 @promotion_views_bp.route('/loyalty/config', methods=['GET', 'POST'])
 def loyalty_config():
     """Loyalty discount configuration"""

 @promotion_views_bp.route('/loyalty/card-types', methods=['GET', 'POST'])
 def card_types():
     """Card type management"""

 # ==================== API ENDPOINTS ====================
 @promotion_views_bp.route('/api/timeline-data')
 def api_timeline_data():
     """JSON: Timeline chart data"""

 @promotion_views_bp.route('/api/timeline-update', methods=['POST'])
 def api_timeline_update():
     """JSON: Update campaign dates (drag-resize)"""

 @promotion_views_bp.route('/api/simulate', methods=['POST'])
 def api_simulate():
     """JSON: Simulate promotions for item"""

 @promotion_views_bp.route('/api/summary')
 def api_summary():
     """JSON: Dashboard summary cards"""

 @promotion_views_bp.route('/api/analytics')
 def api_analytics():
     """JSON: Analytics charts data"""

 @promotion_views_bp.route('/api/overlaps')
 def api_overlaps():
     """JSON: Overlap detection results"""

 ---
 Part 4: Frontend Implementation

 4.1 Main Dashboard Template (dashboard.html)

 Using Universal Engine CSS classes:

 {% extends "layouts/dashboard.html" %}

 {% block content %}
 <div class="mb-6">
     <!-- Page Header -->
     <div class="flex justify-between items-center mb-4">
         <div>
             <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
                 <i class="fas fa-tags mr-2"></i>Promotions Dashboard
             </h1>
             <p class="text-sm text-gray-600 dark:text-gray-400">
                 Plan, visualize and manage all promotion types
             </p>
         </div>
         <div class="flex gap-2">
             <a href="{{ url_for('promotion_views.campaign_create') }}" class="btn-primary">
                 <i class="fas fa-plus mr-1"></i>New Campaign
             </a>
         </div>
     </div>

     <!-- Summary Cards (universal-summary-grid) -->
     <div class="universal-summary-grid">
         <div class="universal-stat-card">
             <div class="stat-card-icon primary"><i class="fas fa-bullhorn"></i></div>
             <div class="stat-card-value">{{ summary.active_campaigns }}</div>
             <div class="stat-card-label">Active Campaigns</div>
         </div>
         <div class="universal-stat-card">
             <div class="stat-card-icon success"><i class="fas fa-rupee-sign"></i></div>
             <div class="stat-card-value">₹{{ summary.total_discount_mtd|format_currency }}</div>
             <div class="stat-card-label">Discount Given (MTD)</div>
         </div>
         <div class="universal-stat-card">
             <div class="stat-card-icon info"><i class="fas fa-trophy"></i></div>
             <div class="stat-card-value">{{ summary.most_used.name }}</div>
             <div class="stat-card-label">Top Campaign ({{ summary.most_used.uses }} uses)</div>
         </div>
         <div class="universal-stat-card">
             <div class="stat-card-icon warning"><i class="fas fa-clock"></i></div>
             <div class="stat-card-value">{{ summary.upcoming }}</div>
             <div class="stat-card-label">Starting in 7 Days</div>
         </div>
     </div>
 </div>

 <!-- Timeline Section -->
 <div class="info-card mb-6">
     <div class="info-card-header">
         <h3 class="info-card-title">
             <i class="fas fa-stream mr-2"></i>Planning Timeline
         </h3>
         <div class="flex gap-2">
             <button class="btn-outline btn-sm" data-zoom="1">1M</button>
             <button class="btn-outline btn-sm active" data-zoom="3">3M</button>
             <button class="btn-outline btn-sm" data-zoom="6">6M</button>
             <button class="btn-outline btn-sm" id="today-btn">Today</button>
         </div>
     </div>
     <div class="info-card-body p-0">
         <div id="timeline-container" class="h-96">
             <!-- Timeline rendered by JS -->
         </div>
     </div>
     <div class="info-card-footer">
         <div class="flex gap-4 text-sm">
             <span><span class="inline-block w-4 h-3 bg-blue-500 mr-1"></span>Campaign</span>
             <span><span class="inline-block w-4 h-3 bg-green-500 mr-1"></span>Buy X Get Y</span>
             <span><span class="inline-block w-4 h-1 bg-orange-500 mr-1"></span>Bulk Active</span>
             <span><span class="inline-block w-3 h-3 rounded-full bg-purple-500 mr-1"></span>Loyalty</span>
         </div>
     </div>
 </div>

 <!-- Simulation Panel -->
 <div class="info-card mb-6">
     <div class="info-card-header">
         <h3 class="info-card-title">
             <i class="fas fa-flask mr-2"></i>Promotion Simulator
         </h3>
     </div>
     <div class="info-card-body">
         <div class="grid grid-cols-4 gap-4 mb-4">
             <div class="form-group">
                 <label class="form-label">Item Type</label>
                 <select id="sim-item-type" class="form-select">
                     <option value="service">Service</option>
                     <option value="medicine">Medicine</option>
                     <option value="package">Package</option>
                 </select>
             </div>
             <div class="form-group">
                 <label class="form-label">Select Item</label>
                 <select id="sim-item" class="form-select universal-entity-dropdown">
                     <!-- Populated dynamically -->
                 </select>
             </div>
             <div class="form-group">
                 <label class="form-label">Quantity</label>
                 <input type="number" id="sim-qty" class="form-input" value="1" min="1">
             </div>
             <div class="form-group">
                 <label class="form-label">Simulation Date</label>
                 <input type="date" id="sim-date" class="form-input" value="{{ today }}">
             </div>
         </div>
         <button id="run-simulation" class="btn-primary">
             <i class="fas fa-play mr-1"></i>Simulate
         </button>

         <!-- Simulation Results -->
         <div id="simulation-results" class="mt-4 hidden">
             <!-- Rendered by JS -->
         </div>
     </div>
 </div>

 <!-- Tabs for Configuration -->
 <div class="info-card">
     <div class="border-b border-gray-200 dark:border-gray-700">
         <nav class="flex -mb-px">
             <a href="#campaigns" class="tab-link active">Campaigns</a>
             <a href="#bulk" class="tab-link">Bulk Config</a>
             <a href="#loyalty" class="tab-link">Loyalty Config</a>
             <a href="#analytics" class="tab-link">Analytics</a>
         </nav>
     </div>
     <div class="info-card-body">
         <!-- Tab Content (loaded via AJAX or included) -->
         <div id="tab-content"></div>
     </div>
 </div>
 {% endblock %}

 4.2 Interactive Timeline Component (promotion_timeline.js)

 class PromotionTimeline {
     constructor(container, options = {}) {
         this.container = document.getElementById(container);
         this.options = {
             months: 3,
             rowHeight: 40,
             headerHeight: 50,
             ...options
         };
         this.data = null;
         this.canvas = null;
         this.ctx = null;
         this.dragState = null;
     }

     // ==================== RENDERING ====================
     async load(hospitalId, startDate, endDate) {
         const response = await fetch(`/promotions/api/timeline-data?start=${startDate}&end=${endDate}`);
         this.data = await response.json();
         this.render();
     }

     render() {
         this.container.innerHTML = '';
         this.createCanvas();
         this.drawHeader();
         this.drawGrid();
         this.drawTodayMarker();
         this.drawCampaignBars();
         this.drawBulkLine();
         this.drawLoyaltyMarkers();
         this.drawOverlapWarnings();
         this.attachEventListeners();
     }

     drawCampaignBars() {
         // Draw horizontal bars for each campaign
         // Color by type: blue=simple, green=buy_x_get_y
         // Dashed border for personalized
         this.data.campaigns.forEach((campaign, index) => {
             const y = this.options.headerHeight + (index * this.options.rowHeight);
             const x1 = this.dateToX(campaign.start_date);
             const x2 = this.dateToX(campaign.end_date);

             this.ctx.fillStyle = campaign.promotion_type === 'buy_x_get_y' ? '#22c55e' : '#3b82f6';
             this.ctx.fillRect(x1, y + 5, x2 - x1, this.options.rowHeight - 10);

             // Dashed border for personalized
             if (campaign.is_personalized) {
                 this.ctx.setLineDash([5, 3]);
                 this.ctx.strokeRect(x1, y + 5, x2 - x1, this.options.rowHeight - 10);
                 this.ctx.setLineDash([]);
             }

             // Campaign name label
             this.ctx.fillStyle = '#fff';
             this.ctx.fillText(campaign.campaign_code, x1 + 5, y + 25);
         });
     }

     drawOverlapWarnings() {
         // Highlight overlapping regions
         this.data.overlaps.forEach(overlap => {
             const x1 = this.dateToX(overlap.start);
             const x2 = this.dateToX(overlap.end);

             this.ctx.fillStyle = 'rgba(239, 68, 68, 0.2)'; // Red transparent
             this.ctx.fillRect(x1, 0, x2 - x1, this.container.height);

             // Warning icon
             this.drawWarningIcon(x1 + (x2-x1)/2, 20);
         });
     }

     // ==================== INTERACTIONS ====================
     attachEventListeners() {
         this.canvas.addEventListener('click', this.onClick.bind(this));
         this.canvas.addEventListener('mousedown', this.onDragStart.bind(this));
         this.canvas.addEventListener('mousemove', this.onDragMove.bind(this));
         this.canvas.addEventListener('mouseup', this.onDragEnd.bind(this));
         this.canvas.addEventListener('mousemove', this.onHover.bind(this));
     }

     onClick(e) {
         const campaign = this.getCampaignAtPoint(e.offsetX, e.offsetY);
         if (campaign) {
             this.openEditModal(campaign);
         }
     }

     onDragStart(e) {
         const campaign = this.getCampaignAtPoint(e.offsetX, e.offsetY);
         const edge = this.getEdgeAtPoint(e.offsetX, e.offsetY, campaign);

         if (campaign) {
             this.dragState = {
                 campaign,
                 edge, // 'start', 'end', or 'move'
                 startX: e.offsetX,
                 originalStart: campaign.start_date,
                 originalEnd: campaign.end_date
             };
             this.canvas.style.cursor = edge ? 'ew-resize' : 'move';
         }
     }

     async onDragEnd(e) {
         if (!this.dragState) return;

         const { campaign, edge } = this.dragState;
         const deltaX = e.offsetX - this.dragState.startX;
         const deltaDays = this.xToDays(deltaX);

         let newStart = this.dragState.originalStart;
         let newEnd = this.dragState.originalEnd;

         if (edge === 'start') {
             newStart = this.addDays(newStart, deltaDays);
         } else if (edge === 'end') {
             newEnd = this.addDays(newEnd, deltaDays);
         } else {
             newStart = this.addDays(newStart, deltaDays);
             newEnd = this.addDays(newEnd, deltaDays);
         }

         // API call to update dates
         await fetch('/promotions/api/timeline-update', {
             method: 'POST',
             headers: {'Content-Type': 'application/json'},
             body: JSON.stringify({
                 campaign_id: campaign.campaign_id,
                 start_date: newStart,
                 end_date: newEnd
             })
         });

         this.dragState = null;
         this.canvas.style.cursor = 'default';
         this.load(); // Refresh
     }

     onHover(e) {
         const campaign = this.getCampaignAtPoint(e.offsetX, e.offsetY);
         if (campaign) {
             this.showTooltip(e, campaign);
         } else {
             this.hideTooltip();
         }
     }

     // ==================== CONTROLS ====================
     setZoom(months) {
         this.options.months = months;
         this.render();
     }

     scrollToToday() {
         // Center view on today
     }

     navigatePrev() {
         // Shift view backward
     }

     navigateNext() {
         // Shift view forward
     }
 }

 4.3 Simulation Component (promotion_simulator.js)

 class PromotionSimulator {
     constructor(options) {
         this.itemTypeSelect = document.getElementById('sim-item-type');
         this.itemSelect = document.getElementById('sim-item');
         this.qtyInput = document.getElementById('sim-qty');
         this.dateInput = document.getElementById('sim-date');
         this.runBtn = document.getElementById('run-simulation');
         this.resultsContainer = document.getElementById('simulation-results');

         this.attachEventListeners();
     }

     attachEventListeners() {
         this.itemTypeSelect.addEventListener('change', () => this.loadItems());
         this.runBtn.addEventListener('click', () => this.runSimulation());
     }

     async loadItems() {
         const itemType = this.itemTypeSelect.value;
         const response = await fetch(`/api/${itemType}s/list?limit=100`);
         const data = await response.json();

         this.itemSelect.innerHTML = data.items.map(item =>
             `<option value="${item.id}">${item.name}</option>`
         ).join('');
     }

     async runSimulation() {
         const payload = {
             item_type: this.itemTypeSelect.value,
             item_id: this.itemSelect.value,
             quantity: parseInt(this.qtyInput.value),
             simulation_date: this.dateInput.value
         };

         const response = await fetch('/promotions/api/simulate', {
             method: 'POST',
             headers: {'Content-Type': 'application/json'},
             body: JSON.stringify(payload)
         });

         const result = await response.json();
         this.renderResults(result);
     }

     renderResults(result) {
         this.resultsContainer.classList.remove('hidden');
         this.resultsContainer.innerHTML = `
             <div class="grid grid-cols-2 gap-4">
                 <div class="info-card">
                     <div class="info-card-header">
                         <h4 class="info-card-title">Applicable Promotions</h4>
                     </div>
                     <div class="info-card-body">
                         <table class="data-table compact-table">
                             <thead>
                                 <tr>
                                     <th>Type</th>
                                     <th>Name</th>
                                     <th>Discount</th>
                                     <th>Priority</th>
                                     <th>Status</th>
                                 </tr>
                             </thead>
                             <tbody>
                                 ${result.applicable_promotions.map(p => `
                                     <tr class="${p.would_apply ? 'bg-green-50 dark:bg-green-900/20' : ''}">
                                         <td><span class="badge badge-${this.getTypeBadge(p.type)}">${p.type}</span></td>
                                         <td>${p.name}</td>
                                         <td>${p.discount_percent}% (₹${p.discount_amount})</td>
                                         <td>${p.priority}</td>
                                         <td>${p.would_apply
                                             ? '<span class="badge badge-success">APPLIED</span>'
                                             : `<span class="badge badge-neutral">${p.reason}</span>`}
                                         </td>
                                     </tr>
                                 `).join('')}
                             </tbody>
                         </table>
                     </div>
                 </div>

                 <div class="info-card">
                     <div class="info-card-header">
                         <h4 class="info-card-title">Final Calculation</h4>
                     </div>
                     <div class="info-card-body">
                         <div class="payment-summary-card">
                             <div class="payment-summary-row">
                                 <span class="payment-summary-label">Original Price</span>
                                 <span class="payment-summary-value">₹${result.original_price}</span>
                             </div>
                             <div class="payment-summary-row">
                                 <span class="payment-summary-label">Winning Promotion</span>
                                 <span class="payment-summary-value text-blue-600">${result.final_discount.name}</span>
                             </div>
                             <div class="payment-summary-row">
                                 <span class="payment-summary-label">Discount</span>
                                 <span class="payment-summary-value text-green-600">-₹${result.final_discount.amount}
 (${result.final_discount.percent}%)</span>
                             </div>
                             <div class="payment-summary-row font-bold text-lg">
                                 <span class="payment-summary-label">Final Price</span>
                                 <span class="payment-summary-value">₹${result.final_price}</span>
                             </div>
                         </div>
                     </div>
                 </div>
             </div>
         `;
     }
 }

 ---
 Part 5: Implementation Phases

 Phase 1: Foundation (Day 1)

 - Create promotion_config.py with entity configuration
 - Create promotion_dashboard_service.py with core methods
 - Create promotion_views.py with routes
 - Create database views for analytics

 Phase 2: Dashboard Shell (Day 2)

 - Create dashboard.html with summary cards
 - Create tab structure for configurations
 - Implement summary cards API
 - Style using Universal Engine CSS

 Phase 3: Campaign CRUD (Day 2-3)

 - Campaign list page (Universal Engine list pattern)
 - Campaign create form (sections, validation)
 - Campaign edit form
 - Toggle status, duplicate actions

 Phase 4: Timeline View (Day 3-4)

 - Create promotion_timeline.js component
 - Implement timeline rendering (Canvas)
 - Add drag-to-move functionality
 - Add resize-dates functionality
 - Implement overlap detection & warnings
 - Add zoom controls (1M/3M/6M)
 - Add Today navigation

 Phase 5: Simulation Panel (Day 4)

 - Create promotion_simulator.js
 - Implement item selection with entity dropdown
 - Build simulation API endpoint
 - Render simulation results with priority explanation

 Phase 6: Bulk & Loyalty Config (Day 5)

 - Bulk config page (enable, threshold, effective date)
 - Bulk eligible items management
 - Loyalty config page (mode selection)
 - Card types CRUD

 Phase 7: Analytics (Day 5-6)

 - Discount breakdown pie chart (Chart.js)
 - Usage trends line chart
 - Top campaigns table
 - Revenue impact analysis

 Phase 8: Testing & Polish (Day 6)

 - Test all CRUD operations
 - Test timeline interactions
 - Test simulation accuracy
 - Responsive design verification
 - Dark mode verification
 - Performance optimization

 ---
 Part 6: Database Views (Analytics)

 -- View: Promotion effectiveness summary
 CREATE OR REPLACE VIEW v_promotion_effectiveness AS
 SELECT
     pc.campaign_id,
     pc.campaign_code,
     pc.campaign_name,
     pc.promotion_type,
     pc.start_date,
     pc.end_date,
     pc.is_active,
     COUNT(pul.usage_id) as total_uses,
     SUM(pul.discount_amount) as total_discount_given,
     SUM(pul.invoice_amount) as total_revenue_generated,
     CASE WHEN SUM(pul.invoice_amount) > 0
          THEN (SUM(pul.discount_amount) / SUM(pul.invoice_amount)) * 100
          ELSE 0 END as discount_to_revenue_ratio
 FROM promotion_campaigns pc
 LEFT JOIN promotion_usage_log pul ON pc.campaign_id = pul.campaign_id
 GROUP BY pc.campaign_id;

 -- View: Daily discount breakdown by type
 CREATE OR REPLACE VIEW v_daily_discount_breakdown AS
 SELECT
     DATE(dal.applied_at) as discount_date,
     dal.discount_type,
     COUNT(*) as application_count,
     SUM(dal.discount_amount) as total_discount
 FROM discount_application_log dal
 GROUP BY DATE(dal.applied_at), dal.discount_type;

 -- View: Active promotions timeline
 CREATE OR REPLACE VIEW v_active_promotions_timeline AS
 SELECT
     'campaign' as promotion_category,
     campaign_id as id,
     campaign_code as code,
     campaign_name as name,
     promotion_type as subtype,
     start_date,
     end_date,
     is_active,
     is_personalized
 FROM promotion_campaigns
 WHERE is_deleted = false
 UNION ALL
 SELECT
     'bulk' as promotion_category,
     hospital_id as id,
     'BULK' as code,
     'Bulk Discount' as name,
     NULL as subtype,
     bulk_discount_effective_from as start_date,
     NULL as end_date,
     bulk_discount_enabled as is_active,
     false as is_personalized
 FROM hospitals
 WHERE bulk_discount_enabled = true;

 ---
 Estimated Timeline

 | Phase                        | Days   | Deliverables            |
 |------------------------------|--------|-------------------------|
 | Phase 1: Foundation          | 1      | Config, Service, Routes |
 | Phase 2: Dashboard Shell     | 0.5    | Summary cards, tabs     |
 | Phase 3: Campaign CRUD       | 1.5    | List, Create, Edit      |
 | Phase 4: Timeline            | 1.5    | Interactive timeline    |
 | Phase 5: Simulation          | 0.5    | Simulation panel        |
 | Phase 6: Bulk/Loyalty Config | 1      | Config pages            |
 | Phase 7: Analytics           | 1      | Charts, metrics         |
 | Phase 8: Testing             | 1      | QA, polish              |
 | Total                        | 8 days |                         |

 ---

**Document Created**: November 26, 2025
**Last Updated**: November 26, 2025
**Status**: Ready for Implementation
