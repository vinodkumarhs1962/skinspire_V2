-- Campaign Hook Configuration Table
-- Purpose: Configure hospital-specific campaign pricing hooks (plugin architecture)
-- Date: 2025-11-17
-- Database: skinspire_dev, skinspire_prod

-- Drop existing table if exists (for development)
DROP TABLE IF EXISTS campaign_hook_config CASCADE;

-- Create campaign hook configuration table
CREATE TABLE IF NOT EXISTS campaign_hook_config (
    hook_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Hospital Reference
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),

    -- Hook Identification
    hook_name VARCHAR(100) NOT NULL,
    hook_description TEXT,
    hook_type VARCHAR(50) NOT NULL, -- 'api_endpoint', 'python_module', 'sql_function'

    -- Hook Implementation
    hook_endpoint VARCHAR(500), -- API endpoint URL (if hook_type = 'api_endpoint')
    hook_module_path VARCHAR(500), -- Python module path (if hook_type = 'python_module')
    hook_function_name VARCHAR(100), -- Function name to call
    hook_sql_function VARCHAR(200), -- SQL function name (if hook_type = 'sql_function')

    -- Hook Activation
    is_active BOOLEAN DEFAULT true,
    priority INTEGER DEFAULT 100, -- Lower number = higher priority (if multiple hooks)

    -- Applicability
    applies_to_medicines BOOLEAN DEFAULT false,
    applies_to_services BOOLEAN DEFAULT false,
    applies_to_packages BOOLEAN DEFAULT false,

    -- Effective Period
    effective_from DATE,
    effective_to DATE,

    -- Hook Configuration (JSON for flexibility)
    hook_config JSONB, -- Custom configuration parameters for the hook

    -- Authentication (for API hooks)
    api_auth_type VARCHAR(50), -- 'none', 'basic', 'bearer', 'api_key'
    api_auth_credentials TEXT, -- Encrypted credentials

    -- Performance & Monitoring
    timeout_ms INTEGER DEFAULT 5000, -- Timeout in milliseconds
    retry_attempts INTEGER DEFAULT 0, -- Number of retries on failure
    cache_results BOOLEAN DEFAULT false, -- Cache campaign results
    cache_ttl_seconds INTEGER DEFAULT 300, -- Cache TTL in seconds

    -- Audit Fields
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(100),
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMP WITH TIME ZONE,
    deleted_by VARCHAR(100),

    -- Constraints
    CONSTRAINT campaign_hook_config_hospital_hook_unique UNIQUE(hospital_id, hook_name, is_deleted),
    CONSTRAINT campaign_hook_config_type_check CHECK (hook_type IN ('api_endpoint', 'python_module', 'sql_function')),
    CONSTRAINT campaign_hook_config_effective_period_check CHECK (effective_to IS NULL OR effective_to >= effective_from)
);

-- Indexes for performance
CREATE INDEX idx_campaign_hook_hospital ON campaign_hook_config(hospital_id) WHERE is_deleted = false;
CREATE INDEX idx_campaign_hook_active ON campaign_hook_config(is_active) WHERE is_deleted = false;
CREATE INDEX idx_campaign_hook_type ON campaign_hook_config(hook_type) WHERE is_deleted = false;
CREATE INDEX idx_campaign_hook_effective_period ON campaign_hook_config(effective_from, effective_to) WHERE is_deleted = false;
CREATE INDEX idx_campaign_hook_priority ON campaign_hook_config(priority) WHERE is_active = true AND is_deleted = false;
CREATE INDEX idx_campaign_hook_medicines ON campaign_hook_config(applies_to_medicines) WHERE applies_to_medicines = true AND is_deleted = false;
CREATE INDEX idx_campaign_hook_services ON campaign_hook_config(applies_to_services) WHERE applies_to_services = true AND is_deleted = false;
CREATE INDEX idx_campaign_hook_packages ON campaign_hook_config(applies_to_packages) WHERE applies_to_packages = true AND is_deleted = false;

-- Comments
COMMENT ON TABLE campaign_hook_config IS 'Hospital-specific campaign pricing hooks (plugin architecture)';
COMMENT ON COLUMN campaign_hook_config.hook_type IS 'Type of hook: api_endpoint (HTTP call), python_module (Python function), sql_function (PostgreSQL function)';
COMMENT ON COLUMN campaign_hook_config.hook_config IS 'JSON configuration for hook-specific parameters (e.g., discount rules, eligibility criteria)';
COMMENT ON COLUMN campaign_hook_config.priority IS 'Lower number = higher priority. If multiple hooks apply, highest priority runs first';
COMMENT ON COLUMN campaign_hook_config.cache_results IS 'Cache campaign results to reduce repeated hook calls';

-- Sample data (optional - comment out for production)
/*
INSERT INTO campaign_hook_config (
    hospital_id,
    hook_name,
    hook_description,
    hook_type,
    hook_module_path,
    hook_function_name,
    is_active,
    priority,
    applies_to_medicines,
    applies_to_services,
    applies_to_packages,
    effective_from,
    effective_to,
    hook_config,
    timeout_ms,
    cache_results,
    cache_ttl_seconds,
    created_by
) VALUES (
    (SELECT hospital_id FROM hospitals LIMIT 1), -- First hospital
    'Diwali Campaign 2025',
    '20% discount on all medicines during Diwali festival',
    'python_module',
    'app.campaigns.diwali_campaign',
    'apply_diwali_discount',
    true,
    10,
    true,
    false,
    false,
    '2025-11-01',
    '2025-11-15',
    '{
        "discount_percentage": 20,
        "min_purchase_amount": 500,
        "max_discount_amount": 1000,
        "excluded_categories": ["controlled_substances"]
    }'::jsonb,
    3000,
    true,
    600,
    'system_admin'
);
*/

-- Migration complete
SELECT 'Campaign hook configuration table created successfully' AS status;
