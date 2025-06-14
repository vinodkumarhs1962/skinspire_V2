Enhanced user Auhentication Implemenation: 

Current Implementation vs. Your Vision

Patient Registration:

Current: Patients can select hospital/branch or get a default if not specified
Your vision: Hospital should be determined by app/web parameters, not user selection
Patients can not have access to functionality, without email and phone verification.  This check configurable at hospital level 


Branch Selection for Patients:

Current: Optional based on UI implementation
Your vision: Either selected by patient or determined by reception staff


Hospital Admin Creation:

Current: No specific flow for super admin to create hospital admins
Your vision: Only super admin can assign users to hospitals and create hospital admins


Staff Registration & Assignment:

Current: Staff selects hospital/branch during registration, approval process exists
Your vision: Staff registration is hospital-specific (determined by portal), branch assignment by hospital admin


Verification:

Current: Email and phone verification exists but not enforced before role assignment
Your vision: Mandatory verification before role assignment



What Needs to be Modified

Patient Registration Flow:

Remove hospital selection for patients, get it from app/portal parameters
Make branch selection optional based on context


Super Admin Interface:

Create specific UI for super admin to manage hospital admins
Add functionality to assign users to hospitals


Hospital Context:

Ensure staff registration inherits hospital context from portal/app
Make hospital field read-only for staff


Staff Approval Process:

Enhance approval process to require verification before role assignment
Add branch assignment to approval workflow


Verification Enforcement:

Add checks to ensure email/phone verification before role assignment

The ENhancements will be planned in Groups.

Implementation Groups
Group 1: Verification System Enhancement

Make email/phone verification configurable at hospital level
Enforce verification checks before granting access to functionality for both patients and staff
Create a hospital settings configuration table/model for verification requirements

Group 2: Registration Flow Modifications

Modify patient registration to inherit hospital context from app/web parameters
Update staff registration to use hospital context and enforce approval workflow
Make branch selection conditional based on user type and configuration

Group 3: Approval Workflow Enhancements

Ensure staff approval process includes branch assignment
Add verification status checks to approval workflow
Improve approval UI for hospital administrators

Group 4: Admin Dashboard Foundations

Create basic super admin dashboard for hospital management
Develop hospital admin dashboard for staff approval and management
Implement role assignment functionality

Group 5: Hospital Configuration System

Create hospital settings management interface
Implement encryption keys and settings at hospital level
Add hospital-specific configuration options

Starting Point: Group 1 (Verification System)
Let's start with enhancing the verification system to make it configurable and enforced:

Create a hospital settings model for verification requirements
Modify the verification service to check hospital settings
Add verification enforcement middleware for protected routes

This will give us a solid foundation for the patient and staff management workflows.