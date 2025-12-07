# Appointment System Reference Documentation

**Version:** 1.1
**Created:** December 7, 2025
**Updated:** December 7, 2025
**Status:** Phase 1 Implementation Complete
**Module:** Patient Lifecycle System - Appointments

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Business Rules](#3-business-rules)
4. [Database Schema](#4-database-schema)
5. [Models (SQLAlchemy)](#5-models-sqlalchemy)
6. [API Endpoints](#6-api-endpoints)
7. [Services](#7-services)
8. [Views & Templates](#8-views--templates)
9. [Workflow & Status Transitions](#9-workflow--status-transitions)
10. [Resource Management](#10-resource-management)
11. [Google Calendar Integration](#11-google-calendar-integration)
12. [Configuration](#12-configuration)
13. [Files Reference](#13-files-reference)

---

## 1. Overview

### 1.1 Purpose
The Appointment System is Phase 1 of the Patient Lifecycle System, providing comprehensive scheduling capabilities for a dermatology/aesthetics clinic.

### 1.2 Key Features
- **Doctor Schedule Management**: Weekly availability templates with break times
- **Slot Generation**: Auto-generate appointment slots from doctor schedules
- **Booking Workflow**: Front desk and walk-in patient booking
- **Resource Allocation**: Room and therapist assignment for procedures
- **Queue Management**: Today's patient queue with check-in and status tracking
- **Calendar Views**: Daily, weekly, and monthly calendar with drag-and-drop reschedule
- **Google Calendar Integration**: One-way sync to staff's Google Calendar
- **Appointment Types**: Consultation, Follow-up, Procedure, Walk-in, etc.

### 1.3 Target User Flows
1. **Front Desk Booking**: Patient selection -> Service/Date/Time -> Resource allocation -> Confirmation
2. **Walk-in Registration**: Quick registration with immediate check-in
3. **Appointment Management**: Edit, reschedule, cancel via context menu
4. **Queue Management**: Check-in, start, complete workflow

---

## 2. Architecture

### 2.1 Component Overview

```
app/
├── models/
│   └── appointment.py          # SQLAlchemy models
├── api/routes/
│   ├── appointment_api.py      # REST API endpoints
│   └── google_calendar_api.py  # Google Calendar OAuth & sync
├── services/
│   ├── appointment_service.py  # Business logic
│   ├── slot_generator_service.py  # Slot generation
│   └── google_calendar_service.py # Google Calendar sync
├── views/
│   └── appointment_views.py    # Flask view routes
├── templates/appointment/
│   ├── dashboard.html          # Main appointment dashboard
│   ├── book.html               # Booking wizard
│   ├── calendar.html           # Calendar view
│   ├── queue.html              # Today's queue
│   └── ...                     # Other templates
└── config/modules/
    └── appointment_config.py   # Entity configuration
```

### 2.2 Authentication
- **Session-based (Web)**: Uses `@login_required` decorator for browser-based access
- **Token-based (API)**: Uses `@token_required` decorator for programmatic access

---

## 3. Business Rules

### 3.1 Booking Rules

| Rule ID | Rule | Implementation |
|---------|------|----------------|
| BR-001 | **Duration Priority**: Appointment duration is determined by: Service > Package > Appointment Type > Hospital Default > 30 min fallback | `get_appointment_duration()` function in database, `_get_appointment_duration()` in service |
| BR-002 | **Slot Capacity**: Each slot has maximum bookings limit (default: 1). Cannot overbook. | `current_bookings < max_bookings` check in `AppointmentSlot` |
| BR-003 | **Blocked Slots**: Blocked slots cannot accept bookings | `is_blocked = false` required for booking |
| BR-004 | **Walk-ins Auto Check-in**: Walk-in appointments are immediately checked in and assigned a token | `book_walk_in()` calls `check_in()` automatically |
| BR-005 | **Appointment Number**: Auto-generated as APT{YYYYMMDD}{6-digit sequence} | Database trigger `trg_appointment_number` |
| BR-006 | **Service/Package Cannot Change**: Once booked, service/package cannot be modified - must cancel and rebook | Edit endpoint explicitly blocks this |

### 3.2 Status Transition Rules

| Rule ID | Rule | Implementation |
|---------|------|----------------|
| BR-010 | **Confirm**: Only `requested` appointments can be confirmed | `confirm()` checks `status == STATUS_REQUESTED` |
| BR-011 | **Check-in**: Only `requested` or `confirmed` appointments can be checked in | `check_in()` validates status |
| BR-012 | **Start**: Only `checked_in` appointments can be started | `start()` checks `status == STATUS_CHECKED_IN` |
| BR-013 | **Complete**: Only `in_progress` appointments can be completed | `complete()` validates status |
| BR-014 | **Cancel/No-Show**: Terminal status appointments cannot be cancelled or marked no-show | Checks `status not in TERMINAL_STATUSES` |
| BR-015 | **Reschedule**: Only `requested` or `confirmed` appointments can be rescheduled | `can_reschedule()` method |
| BR-016 | **Edit Restriction**: `completed`, `cancelled`, `no_show` appointments cannot be edited | Edit endpoint checks status |

### 3.3 Queue Management Rules

| Rule ID | Rule | Implementation |
|---------|------|----------------|
| BR-020 | **Queue Priority Order**: Emergency > Urgent > Normal, then by start time | `ORDER BY CASE priority... THEN start_time` |
| BR-021 | **Token Number**: Sequential per branch per day, assigned at check-in | `get_next_token_number()` function |
| BR-022 | **Wait Time Calculation**: `actual_start_time - checked_in_at` in minutes | Calculated in `start()` method |
| BR-023 | **Waiting Patients**: Checked-in but not yet in-progress, ordered by check-in time | `get_waiting_patients()` method |

### 3.4 Slot Management Rules

| Rule ID | Rule | Implementation |
|---------|------|----------------|
| BR-030 | **Slot Booking Increment**: When appointment is booked, slot's `current_bookings` increments | `increment_slot_booking()` trigger |
| BR-031 | **Slot Release on Cancel/No-Show**: When appointment is cancelled or marked no-show, slot booking count decrements | `decrement_slot_booking()` trigger |
| BR-032 | **Slot Auto-Unavailable**: When `current_bookings >= max_bookings`, `is_available` becomes false | Trigger logic |
| BR-033 | **Break Time Slots**: Slots overlapping with doctor's break time are not generated | `get_slots_for_date()` method |
| BR-034 | **Schedule Effective Dates**: Schedules respect `effective_from` and `effective_until` dates | Slot generation checks dates |

### 3.5 Resource Allocation Rules

| Rule ID | Rule | Implementation |
|---------|------|----------------|
| BR-040 | **Room Conflict Check**: Cannot allocate room if already booked for overlapping time | `allocate_appointment_resources()` conflict check |
| BR-041 | **Staff Conflict Check**: Cannot allocate staff if already assigned for overlapping time | Same conflict check for staff |
| BR-042 | **Allocation Status**: `pending` -> `partial` (room OR staff) -> `complete` (room AND staff) | Updated in allocation endpoint |
| BR-043 | **Approval on Allocation**: Optionally confirm appointment when allocating resources | `approve` parameter in request |
| BR-044 | **Multiple Staff Support**: Can allocate multiple therapists/nurses to one appointment | `staff_ids` array in request |

### 3.6 Reschedule Rules

| Rule ID | Rule | Implementation |
|---------|------|----------------|
| BR-050 | **Reschedule Creates New Appointment**: Original is marked `rescheduled`, new appointment is created | `reschedule()` method |
| BR-051 | **Reschedule Count Tracking**: New appointment inherits and increments `reschedule_count` | `new_appointment.reschedule_count = old + 1` |
| BR-052 | **Reschedule Links**: `rescheduled_from_id` links new to original | Foreign key relationship |
| BR-053 | **Original Slot Released**: Old appointment's slot booking count is decremented | `slot.cancel_booking()` called |
| BR-054 | **Properties Inherited**: Chief complaint, notes, service/package, type all carry forward | Copied in `reschedule()` |

### 3.7 Google Calendar Sync Rules

| Rule ID | Rule | Implementation |
|---------|------|----------------|
| BR-060 | **One-Way Sync**: Skinspire -> Google Calendar only (no pull from Google) | Push-only implementation |
| BR-061 | **Staff-Specific**: Events pushed to assigned doctor's calendar only | Uses `staff_id` to get token |
| BR-062 | **Event ID Storage**: Google Calendar event ID stored in `appointments.external_refs` | JSONB field |
| BR-063 | **Create on Book**: New event created when appointment is booked/rescheduled | `action='create'` |
| BR-064 | **Update on Edit**: Event updated when date/time/details change | `action='update'` |
| BR-065 | **Delete on Cancel**: Event deleted when appointment is cancelled or marked no-show | `action='delete'` |
| BR-066 | **Non-Blocking**: Google Calendar sync failures don't block appointment operations | Try-except with logging |
| BR-067 | **Token Refresh**: Access tokens auto-refresh 5 minutes before expiry | `get_staff_access_token()` checks expiry |

### 3.8 Notification Rules

| Rule ID | Rule | Implementation |
|---------|------|----------------|
| BR-070 | **Confirmation Notification**: Sent when appointment is confirmed | `_queue_notification(session, appointment, 'confirmation')` |
| BR-071 | **Follow-up Reminder**: Queued when appointment is completed | `_queue_notification(session, appointment, 'follow_up')` |
| BR-072 | **Reminder Types**: confirmation, reminder_24h, reminder_1h, follow_up, reschedule | `AppointmentReminder.REMINDER_TYPES` |
| BR-073 | **Channels**: SMS, WhatsApp, Email, Push notifications | `AppointmentReminder.CHANNELS` |

### 3.9 Validation Rules

| Rule ID | Rule | Implementation |
|---------|------|----------------|
| BR-080 | **Valid Day of Week**: 0-6 (Sunday-Saturday) | Database CHECK constraint |
| BR-081 | **Valid Time Range**: Start time must be before end time | Database CHECK constraint |
| BR-082 | **Positive Duration**: Slot duration must be > 0 | Database CHECK constraint |
| BR-083 | **Valid Bookings**: `current_bookings <= max_bookings` and `>= 0` | Database CHECK constraints |
| BR-084 | **Break Time Validation**: Break start/end must be within schedule time and break_start < break_end | Database CHECK constraint |
| BR-085 | **Unique Slot**: One slot per staff/branch/date/time combination | UNIQUE constraint |
| BR-086 | **Unique Schedule**: One schedule per staff/branch/day/time combination | UNIQUE constraint |

---

## 4. Database Schema

### 3.1 Core Tables

#### appointment_types (Master Data)
```sql
CREATE TABLE appointment_types (
    type_id UUID PRIMARY KEY,
    type_code VARCHAR(20) NOT NULL UNIQUE,
    type_name VARCHAR(100) NOT NULL,
    description TEXT,
    default_duration_minutes INT DEFAULT 30,
    requires_doctor BOOLEAN DEFAULT true,
    allow_self_booking BOOLEAN DEFAULT true,
    allow_walk_in BOOLEAN DEFAULT true,
    requires_consent BOOLEAN DEFAULT false,
    base_fee NUMERIC(10,2),
    color_code VARCHAR(7),  -- Hex color for calendar
    icon_name VARCHAR(50),
    display_order INT DEFAULT 0,
    is_active BOOLEAN DEFAULT true
);
```

**Default Types:**
| Code | Name | Duration | Color |
|------|------|----------|-------|
| CONSULTATION | Doctor Consultation | 30 min | #4CAF50 |
| FOLLOW_UP | Follow-up Visit | 15 min | #2196F3 |
| PROCEDURE | Procedure/Treatment | 60 min | #FF9800 |
| SKIN_ANALYSIS | Skin Analysis | 30 min | #9C27B0 |
| PACKAGE_SESSION | Package Session | 45 min | #E91E63 |
| WALK_IN | Walk-in | 30 min | #607D8B |
| EMERGENCY | Emergency | 15 min | #F44336 |

#### doctor_schedules (Weekly Templates)
```sql
CREATE TABLE doctor_schedules (
    schedule_id UUID PRIMARY KEY,
    staff_id UUID NOT NULL REFERENCES staff(staff_id),
    branch_id UUID NOT NULL REFERENCES branches(branch_id),
    day_of_week INT NOT NULL CHECK (0-6), -- 0=Sunday
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    slot_duration_minutes INT DEFAULT 30,
    max_patients_per_slot INT DEFAULT 1,
    break_start_time TIME,
    break_end_time TIME,
    room_id UUID,
    room_name VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    effective_from DATE,
    effective_until DATE,
    UNIQUE(staff_id, branch_id, day_of_week, start_time)
);
```

#### appointment_slots (Generated Slots)
```sql
CREATE TABLE appointment_slots (
    slot_id UUID PRIMARY KEY,
    staff_id UUID NOT NULL REFERENCES staff(staff_id),
    branch_id UUID NOT NULL REFERENCES branches(branch_id),
    schedule_id UUID REFERENCES doctor_schedules(schedule_id),
    slot_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    max_bookings INT DEFAULT 1,
    current_bookings INT DEFAULT 0,
    is_available BOOLEAN DEFAULT true,
    is_blocked BOOLEAN DEFAULT false,
    block_reason VARCHAR(255),
    UNIQUE(staff_id, branch_id, slot_date, start_time)
);
```

#### appointments (Main Table)
```sql
CREATE TABLE appointments (
    appointment_id UUID PRIMARY KEY,
    appointment_number VARCHAR(20) NOT NULL UNIQUE,

    -- Core References
    patient_id UUID NOT NULL REFERENCES patients(patient_id),
    staff_id UUID REFERENCES staff(staff_id),  -- Doctor
    branch_id UUID NOT NULL REFERENCES branches(branch_id),
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),
    slot_id UUID REFERENCES appointment_slots(slot_id),
    appointment_type_id UUID REFERENCES appointment_types(type_id),

    -- Service/Package Reference
    service_id UUID REFERENCES services(service_id),
    package_id UUID REFERENCES packages(package_id),
    package_plan_id UUID REFERENCES package_payment_plans(plan_id),

    -- Scheduling
    appointment_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME,
    estimated_duration_minutes INT DEFAULT 30,
    actual_start_time TIMESTAMP WITH TIME ZONE,
    actual_end_time TIMESTAMP WITH TIME ZONE,
    wait_time_minutes INT,

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'requested',
    booking_source VARCHAR(20) DEFAULT 'front_desk',
    priority VARCHAR(10) DEFAULT 'normal',

    -- Clinical Info
    chief_complaint TEXT,
    patient_notes TEXT,
    internal_notes TEXT,

    -- Follow-up/Reschedule Tracking
    parent_appointment_id UUID REFERENCES appointments(appointment_id),
    is_follow_up BOOLEAN DEFAULT false,
    rescheduled_from_id UUID REFERENCES appointments(appointment_id),
    reschedule_count INT DEFAULT 0,

    -- Check-in
    checked_in_at TIMESTAMP WITH TIME ZONE,
    checked_in_by UUID,
    token_number INT,

    -- Resource Allocation
    room_id UUID REFERENCES rooms(room_id),
    therapist_id UUID REFERENCES staff(staff_id),
    resource_allocation_status VARCHAR(20) DEFAULT 'pending',

    -- Approval Workflow
    requires_approval BOOLEAN DEFAULT true,
    approved_at TIMESTAMP WITH TIME ZONE,
    approved_by VARCHAR(100),

    -- External Integrations
    external_refs JSONB DEFAULT '{}',
    -- Stores: { "google_calendar_event_id": "..." }

    -- Cancellation
    cancellation_reason TEXT,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    cancelled_by UUID
);
```

### 3.2 Supporting Tables

#### appointment_status_history (Audit Trail)
Automatically populated by database trigger when status changes.

#### doctor_schedule_exceptions (Leaves/Holidays)
Stores exceptions to doctor schedules: leaves, holidays, meeting blocks.

#### appointment_reminders (Notification Log)
Tracks SMS/WhatsApp/Email reminders sent to patients.

### 3.3 Resource Management Tables

#### rooms
```sql
CREATE TABLE rooms (
    room_id UUID PRIMARY KEY,
    hospital_id UUID NOT NULL REFERENCES hospitals(hospital_id),
    branch_id UUID NOT NULL REFERENCES branches(branch_id),
    room_code VARCHAR(20) NOT NULL,
    room_name VARCHAR(100) NOT NULL,
    room_type VARCHAR(30) NOT NULL, -- procedure, ot, consultation, treatment, laser, recovery
    capacity INTEGER DEFAULT 1,
    features JSONB,
    default_slot_duration_minutes INTEGER DEFAULT 30,
    buffer_minutes INTEGER DEFAULT 10,
    is_active BOOLEAN DEFAULT true,
    UNIQUE(branch_id, room_code)
);
```

#### appointment_resources (Resource Allocation)
```sql
CREATE TABLE appointment_resources (
    allocation_id UUID PRIMARY KEY,
    appointment_id UUID NOT NULL REFERENCES appointments(appointment_id),
    resource_type VARCHAR(20) NOT NULL, -- room, doctor, therapist, nurse
    room_id UUID REFERENCES rooms(room_id),
    staff_id UUID REFERENCES staff(staff_id),
    allocation_start TIMESTAMP NOT NULL,
    allocation_end TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'reserved' -- reserved, confirmed, in_use, completed, cancelled
);
```

### 3.4 Database Functions

| Function | Purpose |
|----------|---------|
| `generate_appointment_number()` | Auto-generates APT{YYYYMMDD}{SEQ} numbers |
| `get_appointment_duration()` | Returns duration based on: service > package > type > hospital default |
| `check_slot_availability()` | Checks if a slot can accept more bookings |
| `increment_slot_booking()` | Increments booking count on slot |
| `decrement_slot_booking()` | Decrements booking count on cancellation |
| `get_next_token_number()` | Gets next queue token for a branch/date |

### 3.5 Database Triggers

| Trigger | Purpose |
|---------|---------|
| `trg_appointment_number` | Auto-generates appointment number on INSERT |
| `trg_appointment_status_log` | Logs status changes to history table |
| `trg_appointment_slot_update` | Updates slot booking counts on INSERT/UPDATE |

### 3.6 Database Views

| View | Purpose |
|------|---------|
| `v_todays_appointments` | Today's appointments with patient/doctor info |
| `v_doctor_weekly_schedule` | Doctor schedules with day names |
| `v_available_slots` | Available slots for booking |
| `v_doctor_appointment_stats` | Appointment statistics by doctor |

---

## 4. Models (SQLAlchemy)

**File:** `app/models/appointment.py`

### 4.1 AppointmentType
Master data for appointment categories.

```python
class AppointmentType(Base, TimestampMixin, SoftDeleteMixin):
    type_id: UUID (PK)
    type_code: str (unique)
    type_name: str
    default_duration_minutes: int = 30
    requires_doctor: bool = True
    allow_self_booking: bool = True
    color_code: str  # Hex color
    is_active: bool = True
```

### 4.2 DoctorSchedule
Weekly availability templates.

```python
class DoctorSchedule(Base, TimestampMixin, SoftDeleteMixin):
    schedule_id: UUID (PK)
    staff_id: UUID (FK -> staff)
    branch_id: UUID (FK -> branches)
    day_of_week: int  # 0=Sunday, 6=Saturday
    start_time: Time
    end_time: Time
    slot_duration_minutes: int = 30
    max_patients_per_slot: int = 1
    break_start_time: Time (optional)
    break_end_time: Time (optional)

    # Methods
    get_slots_for_date(target_date) -> list[tuple]
```

### 4.3 AppointmentSlot
Generated time slots for booking.

```python
class AppointmentSlot(Base):
    slot_id: UUID (PK)
    staff_id: UUID (FK -> staff)
    branch_id: UUID (FK -> branches)
    schedule_id: UUID (FK -> doctor_schedules)
    slot_date: Date
    start_time: Time
    end_time: Time
    max_bookings: int = 1
    current_bookings: int = 0
    is_available: bool = True
    is_blocked: bool = False

    # Properties
    @hybrid_property available_spots -> int
    @hybrid_property is_bookable -> bool

    # Methods
    book() -> bool
    cancel_booking() -> bool
    block(reason, blocked_by)
    unblock()
```

### 4.4 Appointment
Main appointments table.

```python
class Appointment(Base, TimestampMixin, SoftDeleteMixin):
    appointment_id: UUID (PK)
    appointment_number: str (unique)
    patient_id: UUID (FK -> patients)
    staff_id: UUID (FK -> staff)  # Doctor
    branch_id: UUID (FK -> branches)
    hospital_id: UUID (FK -> hospitals)

    # Scheduling
    appointment_date: Date
    start_time: Time
    end_time: Time
    estimated_duration_minutes: int = 30

    # Status
    status: str = 'requested'
    booking_source: str = 'front_desk'
    priority: str = 'normal'

    # Resource Allocation
    room_id: UUID (FK -> rooms)
    therapist_id: UUID (FK -> staff)

    # External Integrations
    external_refs: JSONB = {}

    # Status Constants
    STATUS_REQUESTED = 'requested'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_CHECKED_IN = 'checked_in'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_NO_SHOW = 'no_show'
    STATUS_RESCHEDULED = 'rescheduled'

    # Methods
    confirm(user_id)
    check_in(user_id, token_number)
    start(user_id)
    complete(user_id, consultation_id)
    cancel(user_id, reason)
    mark_no_show(user_id, reason)
    can_reschedule() -> bool
```

### 4.5 AppointmentStatusHistory
Audit trail for status changes.

### 4.6 DoctorScheduleException
Exceptions to doctor schedules (leaves, holidays).

### 4.7 AppointmentReminder
Log of reminders sent to patients.

---

## 5. API Endpoints

**File:** `app/api/routes/appointment_api.py`
**Base URL:** `/api/appointment`

### 5.1 Slot Availability

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/slots/available` | Token | Get available slots for date |
| GET | `/slots/summary` | Token | Get slot availability summary for date range |

### 5.2 Appointment Booking

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/book` | Token | Book new appointment |
| POST | `/walk-in` | Token | Book walk-in appointment |

### 5.3 Appointment Management

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/{appointment_id}` | Token | Get appointment details |
| PUT | `/{appointment_id}` | Token | Update appointment |
| POST | `/{appointment_id}/confirm` | Token | Confirm appointment |
| POST | `/{appointment_id}/check-in` | Token | Check in patient |
| POST | `/{appointment_id}/start` | Token | Start appointment |
| POST | `/{appointment_id}/complete` | Token | Complete appointment |
| POST | `/{appointment_id}/cancel` | Token | Cancel appointment |
| POST | `/{appointment_id}/reschedule` | Token | Reschedule appointment |

### 5.4 Queue Management

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/queue/today` | Token | Get today's queue |

### 5.5 Calendar & Dashboard

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/calendar/events` | Token | Get appointments for calendar view |

### 5.6 Web Endpoints (Session Auth)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/web/<id>` | Session | Get appointment details |
| PUT | `/web/<id>/edit` | Session | Edit appointment |
| POST | `/web/<id>/cancel` | Session | Cancel appointment |
| POST | `/web/<id>/reschedule` | Session | Reschedule appointment |
| POST | `/web/<id>/start` | Session | Start appointment |
| POST | `/web/<id>/complete` | Session | Complete appointment |
| POST | `/web/complete-multiple` | Session | Complete multiple appointments |
| GET | `/web/doctors` | Session | Get doctors list |
| GET | `/web/rooms` | Session | Get rooms list |
| GET | `/web/therapists` | Session | Get therapists list |
| GET | `/web/calendar-events` | Session | Get calendar events |

### 5.7 Schedule Management

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/schedules` | Token | Get doctor schedules |
| POST | `/schedules` | Token | Create schedule |
| PUT | `/schedules/{schedule_id}` | Token | Update schedule |
| DELETE | `/schedules/{schedule_id}` | Token | Delete schedule |
| POST | `/slots/generate` | Token | Generate slots for date range |
| POST | `/slots/block` | Token | Block slot |

### 5.8 Request/Response Examples

**Book Appointment:**
```json
POST /api/appointment/book
{
    "patient_id": "uuid",
    "branch_id": "uuid",
    "appointment_date": "2025-12-15",
    "start_time": "10:00",
    "staff_id": "uuid",
    "appointment_type_id": "uuid",
    "chief_complaint": "Skin consultation",
    "priority": "normal",
    "booking_source": "front_desk"
}
```

**Edit Appointment:**
```json
PUT /api/appointment/web/{id}/edit
{
    "appointment_date": "2025-12-16",
    "start_time": "11:00",
    "staff_id": "uuid",
    "room_id": "uuid",
    "therapist_id": "uuid",
    "priority": "urgent",
    "internal_notes": "Patient requested morning slot"
}
```

**Cancel Appointment:**
```json
POST /api/appointment/web/{id}/cancel
{
    "reason": "Patient requested cancellation"
}
```

---

## 6. Services

### 6.1 AppointmentService

**File:** `app/services/appointment_service.py`

Core business logic for appointment operations.

```python
class AppointmentService:
    # Booking
    book_appointment(...) -> Appointment
    book_walk_in(...) -> Appointment

    # Status Management
    confirm_appointment(appointment_id, user_id) -> Appointment
    check_in_appointment(appointment_id, user_id) -> Appointment
    start_appointment(appointment_id, user_id) -> Appointment
    complete_appointment(appointment_id, user_id) -> Appointment
    cancel_appointment(appointment_id, user_id, reason) -> Appointment
    mark_no_show(appointment_id, user_id, reason) -> Appointment

    # Rescheduling
    reschedule_appointment(appointment_id, new_date, new_time, ...) -> Appointment

    # Queries
    get_available_slots(branch_id, target_date, staff_id) -> List[Slot]
    get_todays_queue(branch_id, staff_id) -> List[Appointment]
    get_appointment_by_id(appointment_id) -> Appointment

    # Duration Calculation
    _get_appointment_duration(hospital_id, service_id, package_id, type_id) -> int
```

### 6.2 SlotGeneratorService

**File:** `app/services/slot_generator_service.py`

Generates appointment slots from doctor schedules.

```python
class SlotGeneratorService:
    generate_slots(branch_id, staff_id, start_date, end_date) -> List[Slot]
    get_slot_availability_summary(branch_id, start_date, end_date, staff_id) -> dict
```

### 6.3 GoogleCalendarService

**File:** `app/services/google_calendar_service.py`

One-way sync from Skinspire to Google Calendar.

```python
class GoogleCalendarService:
    # OAuth Flow
    get_authorization_url(staff_id, state) -> str
    exchange_code_for_tokens(code) -> dict

    # Token Management
    save_staff_tokens(staff_id, tokens) -> bool
    get_staff_access_token(staff_id) -> str

    # Calendar Operations
    push_appointment_event(appointment_id, action='create') -> bool
    # action: 'create', 'update', 'delete'

    # Status
    is_staff_linked(staff_id) -> bool
    unlink_staff_calendar(staff_id) -> bool
```

**Token Storage:**
Tokens are stored in `staff.settings` JSONB field:
```json
{
    "google_calendar": {
        "access_token": "...",
        "refresh_token": "...",
        "expires_at": "2025-12-07T12:00:00",
        "is_linked": true
    }
}
```

**Event ID Storage:**
Google Calendar event IDs are stored in `appointments.external_refs`:
```json
{
    "google_calendar_event_id": "event123abc"
}
```

---

## 7. Views & Templates

### 7.1 View Routes

**File:** `app/views/appointment_views.py`
**Base URL:** `/appointments`

| Route | Template | Description |
|-------|----------|-------------|
| `/` | `dashboard.html` | Main appointment dashboard |
| `/book` | `book.html` | Booking wizard |
| `/calendar` | `calendar.html` | Calendar view |
| `/queue` | `queue.html` | Today's queue |
| `/schedules` | `schedules.html` | Doctor schedule management |
| `/schedules/create` | `schedule_form.html` | Create/edit schedule |
| `/exceptions` | `exceptions.html` | Schedule exceptions |
| `/reports` | `reports.html` | Appointment reports |
| `/detail/<id>` | `detail.html` | Appointment detail view |
| `/resource-calendar` | `resource_calendar.html` | Resource calendar view |
| `/walk-in` | `walk_in.html` | Walk-in registration |

### 7.2 Templates

**Location:** `app/templates/appointment/`

| Template | Purpose |
|----------|---------|
| `dashboard.html` | Main dashboard with Today's View, Queue, and Calendar tabs |
| `book.html` | Multi-step booking wizard |
| `calendar.html` | FullCalendar-based calendar view |
| `queue.html` | Patient queue management |
| `schedules.html` | Doctor schedule list |
| `schedule_form.html` | Create/edit schedule form |
| `exceptions.html` | Leave/holiday management |
| `reports.html` | Appointment reports |
| `detail.html` | Individual appointment detail |
| `resource_calendar.html` | Room/resource calendar |
| `walk_in.html` | Walk-in registration form |
| `slot_picker.html` | Time slot picker component |

### 7.3 Dashboard Features

The main dashboard (`dashboard.html`) includes:

1. **Date Navigation**: Previous/Today/Next buttons with date picker
2. **View Tabs**:
   - Today's View: Timeline with appointments
   - Queue: Patient queue with check-in status
   - Weekly Calendar: FullCalendar with drag-and-drop
   - Resource Calendar: Room availability view

3. **Right-Click Context Menu**:
   - Start Appointment
   - Complete Appointment
   - Reschedule
   - Edit Appointment
   - Cancel Appointment

4. **Modals**:
   - Reschedule Modal (with calendar)
   - Edit Appointment Modal
   - Cancel Appointment Modal

### 7.4 Calendar Configuration

Uses FullCalendar library:
```javascript
{
    initialView: 'dayGridMonth',
    headerToolbar: {
        left: 'prev,next today',
        center: 'title',
        right: 'dayGridMonth,timeGridWeek,timeGridDay'
    },
    editable: true,  // Drag and drop enabled
    droppable: true,
    slotMinTime: '08:00:00',
    slotMaxTime: '20:00:00',
    allDaySlot: false,
    eventDidMount: function(info) {
        // Add right-click context menu
    }
}
```

---

## 8. Workflow & Status Transitions

### 8.1 Status Flow Diagram

```
                                    ┌──────────────┐
                                    │   REQUESTED  │
                                    └──────┬───────┘
                                           │
                              ┌────────────┼────────────┐
                              │            │            │
                              ▼            ▼            ▼
                       ┌──────────┐  ┌───────────┐  ┌──────────┐
                       │ CANCELLED│  │ CONFIRMED │  │ WALK-IN  │
                       └──────────┘  └─────┬─────┘  └────┬─────┘
                                           │             │
                                           └──────┬──────┘
                                                  │
                                                  ▼
                                         ┌──────────────┐
                                         │  CHECKED_IN  │
                                         └──────┬───────┘
                                                │
                              ┌─────────────────┼─────────────────┐
                              │                 │                 │
                              ▼                 ▼                 ▼
                       ┌──────────┐      ┌────────────┐    ┌─────────┐
                       │  NO_SHOW │      │ IN_PROGRESS│    │CANCELLED│
                       └──────────┘      └─────┬──────┘    └─────────┘
                                               │
                                               ▼
                                        ┌───────────┐
                                        │ COMPLETED │
                                        └───────────┘
```

### 8.2 Valid Transitions

| From Status | To Status | Trigger |
|-------------|-----------|---------|
| requested | confirmed | User confirmation |
| requested | cancelled | User cancellation |
| confirmed | checked_in | Patient check-in |
| confirmed | cancelled | User cancellation |
| confirmed | no_show | Mark as no-show |
| checked_in | in_progress | Start appointment |
| checked_in | no_show | Mark as no-show |
| in_progress | completed | Complete appointment |

### 8.3 Booking Sources

| Source | Description |
|--------|-------------|
| front_desk | Booked by front desk staff |
| scheduled | Pre-scheduled appointment |
| online | Patient self-service booking |
| phone | Phone booking |
| walk_in | Walk-in patient |
| app | Mobile app booking |
| kiosk | Self-service kiosk |

### 8.4 Priority Levels

| Priority | Description | Queue Order |
|----------|-------------|-------------|
| emergency | Medical emergency | 1 (highest) |
| urgent | Urgent consultation | 2 |
| normal | Standard appointment | 3 |

---

## 9. Resource Management

### 9.1 Room Types

| Type | Description |
|------|-------------|
| procedure | Procedure rooms |
| ot | Operating theater |
| consultation | Consultation rooms |
| treatment | Treatment rooms |
| laser | Laser treatment rooms |
| recovery | Recovery areas |

### 9.2 Resource Allocation Workflow

1. **During Booking**: Select room and therapist (optional)
2. **Pre-Appointment**: Confirm resource allocation
3. **Check-in**: Verify resource availability
4. **Completion**: Release resources

### 9.3 Staff Resources

Staff marked with `is_resource = true` appear as therapist/nurse options:
- Therapists
- Nurses
- Treatment assistants

---

## 11. Google Calendar Integration

### 11.1 Overview

The system provides **one-way push sync** from Skinspire to Google Calendar. When appointments are created, updated, or cancelled in Skinspire, the corresponding events are pushed to the assigned staff member's Google Calendar.

**Key Characteristics:**
- Staff-specific: Each doctor/staff links their own Google Calendar
- One-way: Changes only flow from Skinspire -> Google Calendar
- Non-blocking: Sync failures don't affect appointment operations
- Automatic token refresh: Expired tokens are refreshed automatically

### 11.2 Administrator Setup (One-time)

#### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" -> "New Project"
3. Enter project name (e.g., "Skinspire Calendar Integration")
4. Click "Create"

#### Step 2: Enable Google Calendar API

1. In Google Cloud Console, go to **APIs & Services** -> **Library**
2. Search for "Google Calendar API"
3. Click on "Google Calendar API"
4. Click **"Enable"**

#### Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** -> **OAuth consent screen**
2. Select **External** user type (or Internal if using Google Workspace)
3. Fill in required fields:
   - App name: "Skinspire Clinic Management"
   - User support email: your email
   - Developer contact email: your email
4. Click "Save and Continue"
5. Add scopes: Click "Add or Remove Scopes"
   - Search for `https://www.googleapis.com/auth/calendar.events`
   - Select it and click "Update"
6. Click "Save and Continue"
7. Add test users (if External): Add staff email addresses
8. Click "Save and Continue"

#### Step 4: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** -> **Credentials**
2. Click **"Create Credentials"** -> **"OAuth client ID"**
3. Select Application type: **"Web application"**
4. Name: "Skinspire Web Client"
5. Add Authorized redirect URIs:
   - Development: `http://localhost:5000/api/google-calendar/oauth/callback`
   - Production: `https://your-domain.com/api/google-calendar/oauth/callback`
6. Click **"Create"**
7. Download or copy:
   - **Client ID**: `xxxx.apps.googleusercontent.com`
   - **Client Secret**: `GOCSPX-xxxxx`

#### Step 5: Configure Environment Variables

Add to your `.env` file or environment:

```bash
# Google Calendar Integration
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5000/api/google-calendar/oauth/callback
```

For production, update `GOOGLE_REDIRECT_URI` to your production URL.

#### Step 6: Verify Setup

Restart the application and check logs:
```
INFO - Google Calendar integration configured
```

If you see:
```
WARNING - Google Calendar integration not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.
```
The environment variables are not set correctly.

---

### 11.3 Staff Linking Steps (Per Doctor/Staff)

Each staff member who wants their appointments synced to their Google Calendar must complete this one-time linking process.

#### Method 1: From Staff Settings Page

1. Staff logs into Skinspire
2. Navigate to **Settings** or **Profile** page
3. Find "Google Calendar" section
4. Click **"Link Google Calendar"**
5. Browser redirects to Google sign-in
6. Staff signs in with their Google account (work or personal)
7. Google shows consent screen:
   - "Skinspire Clinic Management wants to access your Google Account"
   - Permission: "See, edit, share, and permanently delete all the calendars you can access using Google Calendar"
8. Staff clicks **"Allow"**
9. Browser redirects back to Skinspire
10. Success message: "Google Calendar linked successfully!"

#### Method 2: API-Initiated Link

```javascript
// 1. Get authorization URL
fetch('/api/google-calendar/link?staff_id=' + staffId)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 2. Redirect user to Google
            window.location.href = data.auth_url;
        }
    });

// 3. After consent, Google redirects to:
// /api/google-calendar/oauth/callback?code=xxx&state={"staff_id":"xxx"}

// 4. System exchanges code for tokens and stores them
```

#### Method 3: Direct Redirect

Navigate directly to:
```
GET /api/google-calendar/link/redirect?staff_id={staff_uuid}
```
This will immediately redirect to Google's consent screen.

---

### 11.4 Patient Calendar Integration (Future/Planned)

**Current Status:** Not yet implemented

**Planned Features:**
- Patients can optionally link their Google Calendar
- Appointment confirmation creates event in patient's calendar
- Includes appointment details, location, doctor name
- Reminder notifications via Google Calendar

**Planned Implementation Steps:**

1. **Patient initiates link** (from booking confirmation page or patient portal)
2. **OAuth flow similar to staff** but with patient_id in state
3. **Token storage** in `patients.settings` JSONB field
4. **Event push on booking confirmation**:
   - Summary: "Appointment at Skinspire Clinic"
   - Description: Doctor name, service, instructions
   - Location: Branch address
   - Reminders: 24h and 1h before

**API Endpoints (to be implemented):**
- `GET /api/google-calendar/patient/link` - Initiate patient OAuth
- `GET /api/google-calendar/patient/oauth/callback` - Handle callback
- `POST /api/google-calendar/patient/unlink` - Unlink patient calendar
- `GET /api/google-calendar/patient/status` - Check link status

---

### 11.5 API Reference

#### Check Integration Status
```
GET /api/google-calendar/status
```
Response:
```json
{
    "success": true,
    "is_configured": true,
    "is_linked": true,
    "message": "Google Calendar integration available"
}
```

#### Initiate Staff Link
```
GET /api/google-calendar/link?staff_id={uuid}
```
Response:
```json
{
    "success": true,
    "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
    "message": "Redirect user to auth_url to complete linking"
}
```

#### Direct Redirect to Google
```
GET /api/google-calendar/link/redirect?staff_id={uuid}
```
Redirects immediately to Google OAuth consent screen.

#### OAuth Callback (System Use)
```
GET /api/google-calendar/oauth/callback?code={code}&state={json}
```
Exchanges authorization code for tokens, stores them, redirects to settings page.

#### Unlink Calendar
```
POST /api/google-calendar/unlink
Content-Type: application/json

{
    "staff_id": "uuid"
}
```
Response:
```json
{
    "success": true,
    "message": "Google Calendar unlinked successfully"
}
```

#### Check Staff Calendar Status
```
GET /api/google-calendar/staff/{staff_id}/status
```
Response:
```json
{
    "success": true,
    "staff_id": "uuid",
    "is_linked": true
}
```

#### Test Push Event
```
POST /api/google-calendar/push-test
Content-Type: application/json

{
    "appointment_id": "uuid"
}
```
Response:
```json
{
    "success": true,
    "message": "Event pushed to Google Calendar successfully"
}
```

---

### 11.6 Token Storage

Tokens are stored in `staff.settings` JSONB field:

```json
{
    "google_calendar": {
        "access_token": "ya29.xxx...",
        "refresh_token": "1//0xxx...",
        "token_type": "Bearer",
        "expires_at": "2025-12-07T14:00:00",
        "linked_at": "2025-12-07T10:00:00",
        "is_linked": true
    }
}
```

Google Calendar event IDs are stored in `appointments.external_refs`:

```json
{
    "google_calendar_event_id": "abc123xyz"
}
```

---

### 11.7 Event Sync Operations

| Trigger | Action | Google Calendar API |
|---------|--------|---------------------|
| Appointment booked | Create event | `POST /calendars/primary/events` |
| Appointment rescheduled | Delete old + Create new | `DELETE` then `POST` |
| Appointment edited | Update event | `PUT /calendars/primary/events/{id}` |
| Appointment cancelled | Delete event | `DELETE /calendars/primary/events/{id}` |
| Appointment no-show | Delete event | `DELETE /calendars/primary/events/{id}` |

### 11.8 Event Data Structure

```json
{
    "summary": "Appointment: John Smith",
    "description": "Phone: +91 9876543210\nMRN: MRN001234\nChief Complaint: Acne treatment\nType: Procedure\nStatus: confirmed\nAppointment #: APT20251207000001\n\n--- Managed by Skinspire ---",
    "start": {
        "dateTime": "2025-12-15T10:00:00",
        "timeZone": "Asia/Kolkata"
    },
    "end": {
        "dateTime": "2025-12-15T10:30:00",
        "timeZone": "Asia/Kolkata"
    },
    "reminders": {
        "useDefault": false,
        "overrides": [
            {"method": "popup", "minutes": 15}
        ]
    }
}
```

---

### 11.9 Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| "Google Calendar not configured" | Environment variables not set | Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET |
| "Staff not linked to Google Calendar" | Staff hasn't completed OAuth | Staff should link their calendar |
| "Token refresh failed" | Refresh token revoked or expired | Staff should re-link their calendar |
| "Google Calendar API has not been used in project" | API not enabled | Enable Google Calendar API in Google Cloud Console |
| "Event not found" (404) | Event deleted in Google Calendar | System creates new event |

---

### 11.10 Troubleshooting

#### Calendar not syncing?

1. Check if integration is configured:
   ```
   GET /api/google-calendar/status
   ```

2. Check if staff is linked:
   ```
   GET /api/google-calendar/staff/{staff_id}/status
   ```

3. Check application logs for errors:
   ```
   grep "Google Calendar" app.log
   ```

4. Test push manually:
   ```
   POST /api/google-calendar/push-test
   {"appointment_id": "uuid"}
   ```

#### Token refresh issues?

- Staff may have revoked access from Google Account settings
- Solution: Staff should unlink and re-link their calendar

#### Duplicate events?

- Old issue: Event ID wasn't being stored
- Fixed by: `external_refs.google_calendar_event_id` storage
- If still occurring: Check that `external_refs` column exists and migration ran

---

## 12. Configuration

### 12.1 Hospital Appointment Settings

Stored in `hospitals.appointment_settings` JSONB:

```json
{
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
}
```

### 11.2 Duration Priority

Appointment duration is determined by (in order):
1. Service duration (`services.duration_minutes`)
2. Package session duration (`packages.session_duration_minutes`)
3. Appointment type default (`appointment_types.default_duration_minutes`)
4. Hospital default (`hospitals.appointment_settings.default_slot_duration_minutes`)
5. Fallback: 30 minutes

### 11.3 Entity Configuration

**File:** `app/config/modules/appointment_config.py`

Defines entity configuration for universal CRUD operations.

---

## 12. Files Reference

### 12.1 Models
- `app/models/appointment.py` - SQLAlchemy models

### 12.2 API
- `app/api/routes/appointment_api.py` - REST API endpoints

### 12.3 Services
- `app/services/appointment_service.py` - Business logic
- `app/services/slot_generator_service.py` - Slot generation
- `app/services/google_calendar_service.py` - Google Calendar integration

### 12.4 Views
- `app/views/appointment_views.py` - Flask view routes

### 12.5 Templates
- `app/templates/appointment/dashboard.html`
- `app/templates/appointment/book.html`
- `app/templates/appointment/calendar.html`
- `app/templates/appointment/queue.html`
- `app/templates/appointment/schedules.html`
- `app/templates/appointment/schedule_form.html`
- `app/templates/appointment/exceptions.html`
- `app/templates/appointment/reports.html`
- `app/templates/appointment/detail.html`
- `app/templates/appointment/resource_calendar.html`
- `app/templates/appointment/walk_in.html`
- `app/templates/appointment/slot_picker.html`

### 12.6 Configuration
- `app/config/modules/appointment_config.py`

### 12.7 Migrations
- `migrations/20251204_create_appointment_system.sql` - Core tables
- `migrations/20251205_enhance_appointments.sql` - Enhancements
- `migrations/20251205_resource_management_system.sql` - Room/resource tables
- `migrations/20251206_add_is_resource_to_staff.sql` - Staff resource flag
- `migrations/20251207_add_metadata_to_appointments.sql` - External refs column

### 12.8 Static Assets
- `app/static/js/pages/appointment.js` - Page-specific JavaScript

---

## Appendix A: Common Operations

### A.1 Book an Appointment

```python
from app.services.appointment_service import appointment_service

appointment = appointment_service.book_appointment(
    session=session,
    patient_id=patient_uuid,
    branch_id=branch_uuid,
    hospital_id=hospital_uuid,
    appointment_date=date(2025, 12, 15),
    start_time=time(10, 0),
    staff_id=doctor_uuid,
    chief_complaint="Skin consultation",
    booking_source='front_desk',
    user_id=current_user_id
)
```

### A.2 Check In Patient

```python
from app.services.database_service import get_db_session
from app.models.appointment import Appointment

with get_db_session() as session:
    appointment = session.query(Appointment).get(appointment_uuid)
    appointment.check_in(user_id=current_user_id, token_number=5)
```

### A.3 Push to Google Calendar

```python
from app.services.google_calendar_service import google_calendar_service

# After appointment is created/updated
google_calendar_service.push_appointment_event(
    str(appointment.appointment_id),
    action='create'  # or 'update' or 'delete'
)
```

---

## Appendix B: Future Enhancements / Next Steps

### B.1 Patient Journey Tracking (Post Check-in)

**Current Gap:** After check-in, detailed journey stages are not tracked. We only capture high-level status.

**Proposed Enhancement:** Track granular patient journey stages with timestamps for analytics:

#### Proposed Journey Stages

| Stage | Description | Timestamp Field |
|-------|-------------|-----------------|
| `checked_in` | Patient arrives and checks in | `checked_in_at` (exists) |
| `vitals_started` | Nurse starts taking vitals | `vitals_started_at` |
| `vitals_completed` | Vitals completed, waiting for doctor | `vitals_completed_at` |
| `consultation_started` | Doctor starts consultation | `consultation_started_at` (actual_start_time) |
| `consultation_ended` | Doctor completes consultation | `consultation_ended_at` |
| `procedure_started` | Procedure/treatment begins | `procedure_started_at` |
| `procedure_ended` | Procedure/treatment ends | `procedure_ended_at` |
| `billing_started` | Billing process begins | `billing_started_at` |
| `billing_completed` | Payment/checkout complete | `billing_completed_at` |
| `departed` | Patient leaves clinic | `departed_at` |

#### Proposed Schema Changes

```sql
-- Option 1: Add columns to appointments table
ALTER TABLE appointments ADD COLUMN vitals_started_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE appointments ADD COLUMN vitals_completed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE appointments ADD COLUMN consultation_started_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE appointments ADD COLUMN consultation_ended_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE appointments ADD COLUMN procedure_started_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE appointments ADD COLUMN procedure_ended_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE appointments ADD COLUMN billing_started_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE appointments ADD COLUMN billing_completed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE appointments ADD COLUMN departed_at TIMESTAMP WITH TIME ZONE;

-- Option 2: Create journey_events table for flexibility
CREATE TABLE appointment_journey_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    appointment_id UUID NOT NULL REFERENCES appointments(appointment_id),
    event_type VARCHAR(30) NOT NULL,  -- vitals_started, consultation_started, etc.
    event_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    performed_by UUID REFERENCES staff(staff_id),
    location_id UUID REFERENCES rooms(room_id),
    notes TEXT,
    metadata JSONB
);
```

#### Calculated Metrics

| Metric | Formula | Purpose |
|--------|---------|---------|
| **Pre-Consultation Wait** | `consultation_started - checked_in` | Time patient waits before seeing doctor |
| **Consultation Duration** | `consultation_ended - consultation_started` | Time spent with doctor |
| **Procedure Duration** | `procedure_ended - procedure_started` | Time for treatment |
| **Billing Wait** | `billing_started - (procedure_ended OR consultation_ended)` | Wait before checkout |
| **Billing Duration** | `billing_completed - billing_started` | Time to complete payment |
| **Total Visit Duration** | `departed - checked_in` | End-to-end clinic visit time |
| **Doctor Utilization** | Sum of consultation durations / available hours | Doctor efficiency |

#### Analytics Dashboard Views

```sql
-- Daily wait time analysis
CREATE VIEW v_daily_wait_times AS
SELECT
    appointment_date,
    branch_id,
    AVG(EXTRACT(EPOCH FROM (consultation_started_at - checked_in_at))/60) as avg_wait_minutes,
    MAX(EXTRACT(EPOCH FROM (consultation_started_at - checked_in_at))/60) as max_wait_minutes,
    COUNT(*) as total_appointments
FROM appointments
WHERE consultation_started_at IS NOT NULL AND checked_in_at IS NOT NULL
GROUP BY appointment_date, branch_id;

-- Doctor efficiency report
CREATE VIEW v_doctor_efficiency AS
SELECT
    staff_id,
    appointment_date,
    COUNT(*) as patients_seen,
    AVG(EXTRACT(EPOCH FROM (consultation_ended_at - consultation_started_at))/60) as avg_consultation_mins,
    SUM(EXTRACT(EPOCH FROM (consultation_ended_at - consultation_started_at))/60) as total_consultation_mins
FROM appointments
WHERE consultation_ended_at IS NOT NULL
GROUP BY staff_id, appointment_date;
```

### B.2 Patient Calendar Integration

As documented in Section 11.4, patient calendar linking is planned but not yet implemented.

### B.3 Additional Planned Enhancements

1. **Automated Reminders**: SMS/WhatsApp reminders 24h and 1h before appointment
2. **Online Booking Portal**: Patient self-service booking with slot selection
3. **Waitlist Management**: Allow patients to join waitlist for cancelled slots
4. **Recurring Appointments**: Support for treatment packages with recurring sessions
5. **Multi-doctor Appointments**: Appointments requiring multiple specialists
6. **Telemedicine Integration**: Video consultation support
7. **Mobile App Notifications**: Push notifications for patients
8. **Analytics Dashboard**: Real-time clinic efficiency metrics
9. **Predictive No-Show**: ML model to predict no-shows and overbooking optimization

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Dec 7, 2025 | Claude Code | Initial documentation |
| 1.1 | Dec 7, 2025 | Claude Code | Added business rules (Section 3), comprehensive Google Calendar integration steps (Section 11), patient journey tracking proposal (Appendix B) |

---

*End of Appointment System Reference Documentation*
