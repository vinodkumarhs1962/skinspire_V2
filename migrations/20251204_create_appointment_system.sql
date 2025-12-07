-- ============================================================================
-- Migration: Create Appointment System Tables
-- Date: December 4, 2025
-- Description: Phase 1 of Patient Lifecycle System - Appointment Scheduling
-- ============================================================================

-- ============================================================================
-- 0. ADD APPOINTMENT SETTINGS TO HOSPITALS TABLE
-- ============================================================================
ALTER TABLE hospitals ADD COLUMN IF NOT EXISTS appointment_settings JSONB DEFAULT '{
    "default_slot_duration_minutes": 30,
    "default_max_patients_per_slot": 1,
    "min_advance_booking_hours": 2,
    "max_advance_booking_days": 30,
    "allow_self_service_booking": true,
    "allow_walk_ins": true,
    "reminder_hours_before": [24, 1],
    "auto_cancel_no_confirmation_hours": 24,
    "working_hours_start": "09:00",
    "working_hours_end": "18:00"
}'::jsonb;

COMMENT ON COLUMN hospitals.appointment_settings IS 'Default appointment configuration for the hospital';

-- ============================================================================
-- 0.1 ADD SERVICE/PACKAGE DURATION SETTINGS
-- ============================================================================
-- Add duration field to services if not exists
ALTER TABLE services ADD COLUMN IF NOT EXISTS duration_minutes INT;
ALTER TABLE services ADD COLUMN IF NOT EXISTS allow_online_booking BOOLEAN DEFAULT true;
COMMENT ON COLUMN services.duration_minutes IS 'Default appointment duration for this service (overrides hospital default)';

-- Add duration field to packages if not exists
ALTER TABLE packages ADD COLUMN IF NOT EXISTS session_duration_minutes INT;
ALTER TABLE packages ADD COLUMN IF NOT EXISTS allow_online_booking BOOLEAN DEFAULT true;
COMMENT ON COLUMN packages.session_duration_minutes IS 'Default appointment duration for package sessions (overrides hospital default)';

-- ============================================================================
-- 1. APPOINTMENT TYPES (Master Data)
-- ============================================================================
CREATE TABLE IF NOT EXISTS appointment_types (
    type_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type_code VARCHAR(20) NOT NULL UNIQUE,
    type_name VARCHAR(100) NOT NULL,
    description TEXT,

    -- Configuration
    default_duration_minutes INT NOT NULL DEFAULT 30,
    requires_doctor BOOLEAN DEFAULT true,
    allow_self_booking BOOLEAN DEFAULT true,
    allow_walk_in BOOLEAN DEFAULT true,
    requires_consent BOOLEAN DEFAULT false,

    -- Pricing (optional - for billable appointment types)
    base_fee NUMERIC(10,2),

    -- Display
    color_code VARCHAR(7), -- Hex color for calendar display
    icon_name VARCHAR(50),
    display_order INT DEFAULT 0,

    -- Status
    is_active BOOLEAN DEFAULT true,

    -- Soft delete
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMP WITH TIME ZONE,
    deleted_by VARCHAR(50),

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50),
    updated_by VARCHAR(50)
);

-- Insert default appointment types
INSERT INTO appointment_types (type_code, type_name, default_duration_minutes, requires_doctor, color_code, display_order, description) VALUES
('CONSULTATION', 'Doctor Consultation', 30, true, '#4CAF50', 1, 'Initial or follow-up consultation with doctor'),
('FOLLOW_UP', 'Follow-up Visit', 15, true, '#2196F3', 2, 'Follow-up after previous consultation'),
('PROCEDURE', 'Procedure/Treatment', 60, true, '#FF9800', 3, 'Scheduled procedure or treatment session'),
('SKIN_ANALYSIS', 'Skin Analysis', 30, false, '#9C27B0', 4, 'Skin analysis session - may not require doctor'),
('PACKAGE_SESSION', 'Package Session', 45, true, '#E91E63', 5, 'Session as part of treatment package'),
('WALK_IN', 'Walk-in', 30, true, '#607D8B', 6, 'Walk-in patient without prior appointment'),
('EMERGENCY', 'Emergency', 15, true, '#F44336', 7, 'Emergency consultation')
ON CONFLICT (type_code) DO NOTHING;

-- ============================================================================
-- 2. DOCTOR SCHEDULES (Weekly Templates)
-- ============================================================================
CREATE TABLE IF NOT EXISTS doctor_schedules (
    schedule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID NOT NULL REFERENCES staff(staff_id),
    branch_id UUID NOT NULL REFERENCES branches(branch_id),

    -- Schedule definition
    day_of_week INT NOT NULL CHECK (day_of_week BETWEEN 0 AND 6), -- 0=Sunday, 6=Saturday
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,

    -- Slot configuration
    slot_duration_minutes INT NOT NULL DEFAULT 30 CHECK (slot_duration_minutes > 0),
    max_patients_per_slot INT DEFAULT 1 CHECK (max_patients_per_slot > 0),

    -- Break time (optional)
    break_start_time TIME,
    break_end_time TIME,

    -- Room/Resource (optional)
    room_id UUID,
    room_name VARCHAR(100),

    -- Status
    is_active BOOLEAN DEFAULT true,
    effective_from DATE,
    effective_until DATE,

    -- Soft delete
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMP WITH TIME ZONE,
    deleted_by VARCHAR(50),

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50),
    updated_by VARCHAR(50),

    -- Constraints
    CONSTRAINT valid_time_range CHECK (start_time < end_time),
    CONSTRAINT valid_break_time CHECK (
        (break_start_time IS NULL AND break_end_time IS NULL) OR
        (break_start_time IS NOT NULL AND break_end_time IS NOT NULL AND
         break_start_time < break_end_time AND
         break_start_time >= start_time AND break_end_time <= end_time)
    ),
    CONSTRAINT valid_effective_dates CHECK (
        (effective_from IS NULL AND effective_until IS NULL) OR
        (effective_from IS NULL AND effective_until IS NOT NULL) OR
        (effective_from IS NOT NULL AND effective_until IS NULL) OR
        (effective_from <= effective_until)
    ),
    UNIQUE(staff_id, branch_id, day_of_week, start_time)
);

-- ============================================================================
-- 3. APPOINTMENT SLOTS (Generated from Schedules)
-- ============================================================================
CREATE TABLE IF NOT EXISTS appointment_slots (
    slot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- References
    staff_id UUID NOT NULL REFERENCES staff(staff_id),
    branch_id UUID NOT NULL REFERENCES branches(branch_id),
    schedule_id UUID REFERENCES doctor_schedules(schedule_id),

    -- Slot timing
    slot_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,

    -- Capacity
    max_bookings INT DEFAULT 1 CHECK (max_bookings > 0),
    current_bookings INT DEFAULT 0 CHECK (current_bookings >= 0),

    -- Availability
    is_available BOOLEAN DEFAULT true,
    is_blocked BOOLEAN DEFAULT false,
    block_reason VARCHAR(255),
    blocked_by UUID,
    blocked_at TIMESTAMP WITH TIME ZONE,

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT valid_slot_time CHECK (start_time < end_time),
    CONSTRAINT valid_bookings CHECK (current_bookings <= max_bookings),
    UNIQUE(staff_id, branch_id, slot_date, start_time)
);

-- ============================================================================
-- 4. APPOINTMENTS (Main Table)
-- ============================================================================
CREATE TABLE IF NOT EXISTS appointments (
    appointment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_number VARCHAR(20) NOT NULL UNIQUE,

    -- References
    patient_id UUID NOT NULL REFERENCES patients(patient_id),
    staff_id UUID REFERENCES staff(staff_id), -- Doctor (optional for some appointment types)
    branch_id UUID NOT NULL REFERENCES branches(branch_id),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),
    slot_id UUID REFERENCES appointment_slots(slot_id),
    appointment_type_id UUID REFERENCES appointment_types(type_id),

    -- Service/Package reference (determines duration if not default)
    service_id UUID REFERENCES services(service_id),
    package_id UUID REFERENCES packages(package_id),
    procedure_order_id UUID, -- Will reference procedure_orders when created in Phase 4

    -- Scheduling
    appointment_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME,
    -- Duration priority: service > package > appointment_type > hospital default
    estimated_duration_minutes INT DEFAULT 30,

    -- Actual timing (for tracking)
    actual_start_time TIMESTAMP WITH TIME ZONE,
    actual_end_time TIMESTAMP WITH TIME ZONE,
    wait_time_minutes INT, -- Calculated: actual_start - scheduled_start

    -- Status workflow
    status VARCHAR(20) NOT NULL DEFAULT 'requested',
    -- Possible values: requested, confirmed, checked_in, in_progress, completed, cancelled, no_show, rescheduled

    -- Booking info
    booking_source VARCHAR(20) NOT NULL DEFAULT 'front_desk',
    -- Possible values: front_desk, self_service, whatsapp, phone, walk_in, referral

    booking_channel VARCHAR(50), -- web, mobile_app, whatsapp_bot, etc.

    -- Clinical info
    chief_complaint TEXT,
    priority VARCHAR(10) DEFAULT 'normal', -- normal, urgent, emergency

    -- Follow-up tracking
    parent_appointment_id UUID REFERENCES appointments(appointment_id),
    is_follow_up BOOLEAN DEFAULT false,
    follow_up_of_consultation_id UUID, -- Link to original consultation

    -- Reschedule tracking
    rescheduled_from_id UUID REFERENCES appointments(appointment_id),
    reschedule_count INT DEFAULT 0,

    -- Notes
    patient_notes TEXT, -- Notes from patient during booking
    internal_notes TEXT, -- Staff notes
    cancellation_reason TEXT,
    no_show_reason TEXT,

    -- Reminders
    reminder_sent BOOLEAN DEFAULT false,
    reminder_sent_at TIMESTAMP WITH TIME ZONE,
    reminder_type VARCHAR(20), -- sms, whatsapp, email
    confirmation_sent BOOLEAN DEFAULT false,
    confirmation_sent_at TIMESTAMP WITH TIME ZONE,

    -- Check-in
    checked_in_at TIMESTAMP WITH TIME ZONE,
    checked_in_by VARCHAR(15), -- References users.user_id
    token_number INT, -- Queue token for the day

    -- Confirmation
    confirmed_at TIMESTAMP WITH TIME ZONE,
    confirmed_by VARCHAR(15), -- References users.user_id

    -- Completion
    completed_at TIMESTAMP WITH TIME ZONE,
    completed_by VARCHAR(15), -- References users.user_id
    consultation_id UUID, -- Link to consultation record when started

    -- Cancellation
    cancelled_at TIMESTAMP WITH TIME ZONE,
    cancelled_by VARCHAR(15), -- References users.user_id

    -- Soft delete
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMP WITH TIME ZONE,
    deleted_by VARCHAR(50),

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50),
    updated_by VARCHAR(50)
);

-- ============================================================================
-- 5. APPOINTMENT STATUS HISTORY (Audit Trail)
-- ============================================================================
CREATE TABLE IF NOT EXISTS appointment_status_history (
    history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_id UUID NOT NULL REFERENCES appointments(appointment_id),

    -- Status change
    old_status VARCHAR(20),
    new_status VARCHAR(20) NOT NULL,

    -- Change info
    changed_by VARCHAR(15), -- References users.user_id
    change_reason TEXT,
    change_source VARCHAR(50), -- user, system, automation

    -- Additional context
    additional_data JSONB, -- For storing extra context

    -- Timestamp
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 6. DOCTOR SCHEDULE EXCEPTIONS (Holidays, Leaves, Blocks)
-- ============================================================================
CREATE TABLE IF NOT EXISTS doctor_schedule_exceptions (
    exception_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    staff_id UUID NOT NULL REFERENCES staff(staff_id),
    branch_id UUID REFERENCES branches(branch_id), -- NULL means all branches

    -- Exception period
    exception_date DATE NOT NULL,
    start_time TIME, -- NULL means whole day
    end_time TIME,

    -- Exception type
    exception_type VARCHAR(30) NOT NULL,
    -- Types: leave, holiday, meeting, training, block, other

    -- Details
    reason TEXT,
    is_recurring BOOLEAN DEFAULT false,
    recurrence_pattern JSONB, -- For recurring exceptions

    -- Status
    is_active BOOLEAN DEFAULT true,

    -- Approval (for leave requests)
    requires_approval BOOLEAN DEFAULT false,
    approved_by VARCHAR(15), -- References users.user_id
    approved_at TIMESTAMP WITH TIME ZONE,
    approval_status VARCHAR(20) DEFAULT 'approved', -- pending, approved, rejected

    -- Soft delete
    is_deleted BOOLEAN DEFAULT false,
    deleted_at TIMESTAMP WITH TIME ZONE,
    deleted_by VARCHAR(50),

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50),
    updated_by VARCHAR(50)
);

-- ============================================================================
-- 7. APPOINTMENT REMINDERS LOG
-- ============================================================================
CREATE TABLE IF NOT EXISTS appointment_reminders (
    reminder_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_id UUID NOT NULL REFERENCES appointments(appointment_id),

    -- Reminder details
    reminder_type VARCHAR(20) NOT NULL, -- confirmation, reminder_24h, reminder_1h, follow_up
    channel VARCHAR(20) NOT NULL, -- sms, whatsapp, email, push

    -- Recipient
    recipient_phone VARCHAR(15),
    recipient_email VARCHAR(255),

    -- Message
    message_template VARCHAR(100),
    message_content TEXT,

    -- Status
    status VARCHAR(20) DEFAULT 'pending', -- pending, sent, delivered, failed, cancelled
    sent_at TIMESTAMP WITH TIME ZONE,
    delivered_at TIMESTAMP WITH TIME ZONE,

    -- Response (for WhatsApp confirmations)
    response_received BOOLEAN DEFAULT false,
    response_text TEXT,
    response_at TIMESTAMP WITH TIME ZONE,

    -- Error handling
    error_message TEXT,
    retry_count INT DEFAULT 0,

    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 8. APPOINTMENT SEQUENCE (For generating appointment numbers)
-- ============================================================================
CREATE SEQUENCE IF NOT EXISTS appointment_number_seq START 1;

-- ============================================================================
-- 9. INDEXES FOR PERFORMANCE
-- ============================================================================

-- Appointment indexes
CREATE INDEX IF NOT EXISTS idx_appointments_patient ON appointments(patient_id);
CREATE INDEX IF NOT EXISTS idx_appointments_staff ON appointments(staff_id);
CREATE INDEX IF NOT EXISTS idx_appointments_branch ON appointments(branch_id);
CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(appointment_date);
CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);
CREATE INDEX IF NOT EXISTS idx_appointments_date_status ON appointments(appointment_date, status);
CREATE INDEX IF NOT EXISTS idx_appointments_date_staff ON appointments(appointment_date, staff_id);
CREATE INDEX IF NOT EXISTS idx_appointments_number ON appointments(appointment_number);
CREATE INDEX IF NOT EXISTS idx_appointments_created ON appointments(created_at DESC);

-- Slot indexes
CREATE INDEX IF NOT EXISTS idx_slots_date ON appointment_slots(slot_date);
CREATE INDEX IF NOT EXISTS idx_slots_staff ON appointment_slots(staff_id);
CREATE INDEX IF NOT EXISTS idx_slots_available ON appointment_slots(slot_date, staff_id, is_available, is_blocked);

-- Schedule indexes
CREATE INDEX IF NOT EXISTS idx_schedules_staff ON doctor_schedules(staff_id);
CREATE INDEX IF NOT EXISTS idx_schedules_branch ON doctor_schedules(branch_id);
CREATE INDEX IF NOT EXISTS idx_schedules_active ON doctor_schedules(is_active, is_deleted);

-- Status history indexes
CREATE INDEX IF NOT EXISTS idx_status_history_appointment ON appointment_status_history(appointment_id);
CREATE INDEX IF NOT EXISTS idx_status_history_date ON appointment_status_history(changed_at);

-- Reminder indexes
CREATE INDEX IF NOT EXISTS idx_reminders_appointment ON appointment_reminders(appointment_id);
CREATE INDEX IF NOT EXISTS idx_reminders_status ON appointment_reminders(status);

-- ============================================================================
-- 10. FUNCTIONS
-- ============================================================================

-- Function to get appointment duration based on priority hierarchy
-- Priority: service > package > appointment_type > hospital default
CREATE OR REPLACE FUNCTION get_appointment_duration(
    p_hospital_id UUID,
    p_service_id UUID DEFAULT NULL,
    p_package_id UUID DEFAULT NULL,
    p_appointment_type_id UUID DEFAULT NULL
) RETURNS INT AS $$
DECLARE
    v_duration INT;
    v_hospital_default INT;
BEGIN
    -- 1. First check service duration
    IF p_service_id IS NOT NULL THEN
        SELECT duration_minutes INTO v_duration
        FROM services
        WHERE service_id = p_service_id AND duration_minutes IS NOT NULL;
        IF v_duration IS NOT NULL THEN
            RETURN v_duration;
        END IF;
    END IF;

    -- 2. Check package session duration
    IF p_package_id IS NOT NULL THEN
        SELECT session_duration_minutes INTO v_duration
        FROM packages
        WHERE package_id = p_package_id AND session_duration_minutes IS NOT NULL;
        IF v_duration IS NOT NULL THEN
            RETURN v_duration;
        END IF;
    END IF;

    -- 3. Check appointment type default duration
    IF p_appointment_type_id IS NOT NULL THEN
        SELECT default_duration_minutes INTO v_duration
        FROM appointment_types
        WHERE type_id = p_appointment_type_id AND default_duration_minutes IS NOT NULL;
        IF v_duration IS NOT NULL THEN
            RETURN v_duration;
        END IF;
    END IF;

    -- 4. Fall back to hospital default
    SELECT (appointment_settings->>'default_slot_duration_minutes')::INT INTO v_hospital_default
    FROM hospitals
    WHERE hospital_id = p_hospital_id;

    RETURN COALESCE(v_hospital_default, 30); -- Ultimate fallback: 30 minutes
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_appointment_duration IS 'Returns appointment duration in minutes based on priority: service > package > appointment_type > hospital default';

-- Function to generate appointment number
CREATE OR REPLACE FUNCTION generate_appointment_number()
RETURNS VARCHAR(20) AS $$
DECLARE
    new_number VARCHAR(20);
    date_part VARCHAR(8);
    seq_part VARCHAR(6);
BEGIN
    date_part := TO_CHAR(CURRENT_DATE, 'YYYYMMDD');
    seq_part := LPAD(NEXTVAL('appointment_number_seq')::TEXT, 6, '0');
    new_number := 'APT' || date_part || seq_part;
    RETURN new_number;
END;
$$ LANGUAGE plpgsql;

-- Function to check slot availability
CREATE OR REPLACE FUNCTION check_slot_availability(
    p_staff_id UUID,
    p_branch_id UUID,
    p_date DATE,
    p_start_time TIME
) RETURNS BOOLEAN AS $$
DECLARE
    slot_record RECORD;
BEGIN
    SELECT * INTO slot_record
    FROM appointment_slots
    WHERE staff_id = p_staff_id
      AND branch_id = p_branch_id
      AND slot_date = p_date
      AND start_time = p_start_time
      AND is_available = true
      AND is_blocked = false
      AND current_bookings < max_bookings;

    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Function to increment slot booking count
CREATE OR REPLACE FUNCTION increment_slot_booking(p_slot_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    updated_count INT;
BEGIN
    UPDATE appointment_slots
    SET current_bookings = current_bookings + 1,
        is_available = CASE WHEN current_bookings + 1 >= max_bookings THEN false ELSE true END,
        updated_at = CURRENT_TIMESTAMP
    WHERE slot_id = p_slot_id
      AND current_bookings < max_bookings;

    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count > 0;
END;
$$ LANGUAGE plpgsql;

-- Function to decrement slot booking count (on cancellation)
CREATE OR REPLACE FUNCTION decrement_slot_booking(p_slot_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    updated_count INT;
BEGIN
    UPDATE appointment_slots
    SET current_bookings = GREATEST(0, current_bookings - 1),
        is_available = true,
        updated_at = CURRENT_TIMESTAMP
    WHERE slot_id = p_slot_id;

    GET DIAGNOSTICS updated_count = ROW_COUNT;
    RETURN updated_count > 0;
END;
$$ LANGUAGE plpgsql;

-- Function to get next token number for a branch on a date
CREATE OR REPLACE FUNCTION get_next_token_number(
    p_branch_id UUID,
    p_date DATE
) RETURNS INT AS $$
DECLARE
    next_token INT;
BEGIN
    SELECT COALESCE(MAX(token_number), 0) + 1 INTO next_token
    FROM appointments
    WHERE branch_id = p_branch_id
      AND appointment_date = p_date
      AND token_number IS NOT NULL;

    RETURN next_token;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 11. TRIGGERS
-- ============================================================================

-- Trigger to auto-generate appointment number
CREATE OR REPLACE FUNCTION trigger_generate_appointment_number()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.appointment_number IS NULL OR NEW.appointment_number = '' THEN
        NEW.appointment_number := generate_appointment_number();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_appointment_number ON appointments;
CREATE TRIGGER trg_appointment_number
    BEFORE INSERT ON appointments
    FOR EACH ROW
    EXECUTE FUNCTION trigger_generate_appointment_number();

-- Trigger to log status changes
CREATE OR REPLACE FUNCTION trigger_log_appointment_status_change()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO appointment_status_history (
            appointment_id,
            old_status,
            new_status,
            changed_by,
            change_source,
            changed_at
        ) VALUES (
            NEW.appointment_id,
            OLD.status,
            NEW.status,
            NEW.updated_by,
            'system',
            CURRENT_TIMESTAMP
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_appointment_status_log ON appointments;
CREATE TRIGGER trg_appointment_status_log
    AFTER UPDATE ON appointments
    FOR EACH ROW
    EXECUTE FUNCTION trigger_log_appointment_status_change();

-- Trigger to update slot booking count on appointment creation
CREATE OR REPLACE FUNCTION trigger_update_slot_on_appointment()
RETURNS TRIGGER AS $$
BEGIN
    -- On INSERT: Increment slot booking
    IF TG_OP = 'INSERT' AND NEW.slot_id IS NOT NULL AND NEW.status NOT IN ('cancelled', 'no_show') THEN
        PERFORM increment_slot_booking(NEW.slot_id);

    -- On UPDATE: Handle status changes
    ELSIF TG_OP = 'UPDATE' THEN
        -- If slot changed, update both old and new slots
        IF OLD.slot_id IS DISTINCT FROM NEW.slot_id THEN
            IF OLD.slot_id IS NOT NULL THEN
                PERFORM decrement_slot_booking(OLD.slot_id);
            END IF;
            IF NEW.slot_id IS NOT NULL AND NEW.status NOT IN ('cancelled', 'no_show') THEN
                PERFORM increment_slot_booking(NEW.slot_id);
            END IF;
        -- If status changed to cancelled/no_show, decrement
        ELSIF OLD.status NOT IN ('cancelled', 'no_show') AND NEW.status IN ('cancelled', 'no_show') THEN
            IF NEW.slot_id IS NOT NULL THEN
                PERFORM decrement_slot_booking(NEW.slot_id);
            END IF;
        -- If status changed from cancelled to active, increment
        ELSIF OLD.status IN ('cancelled', 'no_show') AND NEW.status NOT IN ('cancelled', 'no_show') THEN
            IF NEW.slot_id IS NOT NULL THEN
                PERFORM increment_slot_booking(NEW.slot_id);
            END IF;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_appointment_slot_update ON appointments;
CREATE TRIGGER trg_appointment_slot_update
    AFTER INSERT OR UPDATE ON appointments
    FOR EACH ROW
    EXECUTE FUNCTION trigger_update_slot_on_appointment();

-- ============================================================================
-- 12. VIEWS
-- ============================================================================

-- View: Today's appointments queue
CREATE OR REPLACE VIEW v_todays_appointments AS
SELECT
    a.appointment_id,
    a.appointment_number,
    a.appointment_date,
    a.start_time,
    a.end_time,
    a.status,
    a.priority,
    a.token_number,
    a.chief_complaint,
    a.is_follow_up,
    a.booking_source,
    a.checked_in_at,
    a.actual_start_time,
    p.patient_id,
    p.first_name || ' ' || COALESCE(p.last_name, '') AS patient_name,
    COALESCE(p.contact_info->>'mobile', p.contact_info->>'phone') AS patient_phone,
    s.staff_id AS doctor_id,
    s.first_name || ' ' || COALESCE(s.last_name, '') AS doctor_name,
    at.type_name AS appointment_type,
    at.color_code,
    b.name AS branch_name,
    a.branch_id,
    CASE
        WHEN a.status = 'checked_in' THEN
            EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - a.checked_in_at)) / 60
        ELSE NULL
    END AS waiting_minutes
FROM appointments a
JOIN patients p ON a.patient_id = p.patient_id
LEFT JOIN staff s ON a.staff_id = s.staff_id
LEFT JOIN appointment_types at ON a.appointment_type_id = at.type_id
JOIN branches b ON a.branch_id = b.branch_id
WHERE a.appointment_date = CURRENT_DATE
  AND a.is_deleted = false
  AND a.status NOT IN ('cancelled')
ORDER BY
    CASE a.priority
        WHEN 'emergency' THEN 1
        WHEN 'urgent' THEN 2
        ELSE 3
    END,
    a.start_time;

-- View: Doctor's schedule for a week
CREATE OR REPLACE VIEW v_doctor_weekly_schedule AS
SELECT
    ds.schedule_id,
    ds.staff_id,
    s.first_name || ' ' || COALESCE(s.last_name, '') AS doctor_name,
    ds.branch_id,
    b.name AS branch_name,
    ds.day_of_week,
    CASE ds.day_of_week
        WHEN 0 THEN 'Sunday'
        WHEN 1 THEN 'Monday'
        WHEN 2 THEN 'Tuesday'
        WHEN 3 THEN 'Wednesday'
        WHEN 4 THEN 'Thursday'
        WHEN 5 THEN 'Friday'
        WHEN 6 THEN 'Saturday'
    END AS day_name,
    ds.start_time,
    ds.end_time,
    ds.slot_duration_minutes,
    ds.max_patients_per_slot,
    ds.break_start_time,
    ds.break_end_time,
    ds.is_active
FROM doctor_schedules ds
JOIN staff s ON ds.staff_id = s.staff_id
JOIN branches b ON ds.branch_id = b.branch_id
WHERE ds.is_deleted = false
  AND ds.is_active = true
ORDER BY ds.staff_id, ds.day_of_week, ds.start_time;

-- View: Available slots for booking
CREATE OR REPLACE VIEW v_available_slots AS
SELECT
    sl.slot_id,
    sl.staff_id,
    s.first_name || ' ' || COALESCE(s.last_name, '') AS doctor_name,
    sl.branch_id,
    b.name AS branch_name,
    sl.slot_date,
    sl.start_time,
    sl.end_time,
    sl.max_bookings,
    sl.current_bookings,
    sl.max_bookings - sl.current_bookings AS available_spots
FROM appointment_slots sl
JOIN staff s ON sl.staff_id = s.staff_id
JOIN branches b ON sl.branch_id = b.branch_id
WHERE sl.is_available = true
  AND sl.is_blocked = false
  AND sl.current_bookings < sl.max_bookings
  AND sl.slot_date >= CURRENT_DATE
ORDER BY sl.slot_date, sl.start_time;

-- View: Appointment statistics by doctor
CREATE OR REPLACE VIEW v_doctor_appointment_stats AS
SELECT
    s.staff_id,
    s.first_name || ' ' || COALESCE(s.last_name, '') AS doctor_name,
    a.branch_id,
    b.name AS branch_name,
    a.appointment_date,
    COUNT(*) AS total_appointments,
    COUNT(*) FILTER (WHERE a.status = 'completed') AS completed,
    COUNT(*) FILTER (WHERE a.status = 'cancelled') AS cancelled,
    COUNT(*) FILTER (WHERE a.status = 'no_show') AS no_shows,
    COUNT(*) FILTER (WHERE a.status IN ('requested', 'confirmed')) AS pending,
    AVG(CASE WHEN a.wait_time_minutes IS NOT NULL THEN a.wait_time_minutes END) AS avg_wait_time
FROM appointments a
JOIN staff s ON a.staff_id = s.staff_id
JOIN branches b ON a.branch_id = b.branch_id
WHERE a.is_deleted = false
GROUP BY s.staff_id, s.first_name, s.last_name, a.branch_id, b.name, a.appointment_date
ORDER BY a.appointment_date DESC, s.staff_id;

-- ============================================================================
-- 13. GRANT PERMISSIONS
-- ============================================================================
-- Add appropriate grants based on your user/role setup

-- ============================================================================
-- 14. COMMENTS
-- ============================================================================
COMMENT ON TABLE appointments IS 'Main appointments table for scheduling patient visits';
COMMENT ON TABLE appointment_slots IS 'Generated time slots for appointment booking';
COMMENT ON TABLE doctor_schedules IS 'Weekly schedule templates for doctors';
COMMENT ON TABLE appointment_types IS 'Master data for appointment categories';
COMMENT ON TABLE appointment_status_history IS 'Audit trail for appointment status changes';
COMMENT ON TABLE doctor_schedule_exceptions IS 'Doctor leaves, holidays, and schedule blocks';
COMMENT ON TABLE appointment_reminders IS 'Log of appointment reminders sent';

COMMENT ON COLUMN appointments.status IS 'Status: requested, confirmed, checked_in, in_progress, completed, cancelled, no_show, rescheduled';
COMMENT ON COLUMN appointments.booking_source IS 'Booking source: front_desk, self_service, whatsapp, phone, walk_in, referral';
COMMENT ON COLUMN appointments.priority IS 'Priority: normal, urgent, emergency';

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
