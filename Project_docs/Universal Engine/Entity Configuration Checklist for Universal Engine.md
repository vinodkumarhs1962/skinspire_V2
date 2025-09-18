# Entity Configuration Checklist for Universal Engine
## Lessons Learned from Medicine Configuration Errors

### ⚠️ CRITICAL: Always Verify Against Actual Source Files

**NEVER assume parameter names or enum values. ALWAYS check:**
1. `core_definitions.py` for exact parameter names and enum values
2. `master.py` or relevant model files for actual field/relationship names
3. Working examples like `supplier_config.py` for correct patterns

---

## 1. EntityConfiguration Parameters Checklist

### ✅ REQUIRED Parameters (Must be in exact order)
```python
EntityConfiguration(
    # These MUST come first and in this order:
    entity_type="entity_name",          # Singular, lowercase
    name="Entity",                       # Display name
    plural_name="Entities",              # Plural display name
    service_name="entities",             # Service identifier
    table_name="entities",               # Database table
    primary_key="entity_id",             # Primary key field
    title_field="name",                  # Field for titles
    subtitle_field="description",        # Field for subtitles
    icon="fas fa-icon",                  # FontAwesome icon
    page_title="Entity Management",      # Page title
    description="Manage entities",       # Page description
    searchable_fields=["field1", "field2"],  # Search fields
    default_sort_field="name",           # Sort field
    default_sort_direction="asc",        # Sort direction (asc/desc)
    fields=ENTITY_FIELDS,                # Field definitions list
    actions=ENTITY_ACTIONS,              # Action definitions list
    summary_cards=[],                    # Summary cards (can be empty list)
    permissions={                        # Permissions dict
        'view': 'entity.view',
        'create': 'entity.create',
        'edit': 'entity.edit',
        'delete': 'entity.delete'
    },
```

### ✅ OPTIONAL Parameters (After required ones)
```python
    # Optional parameters come AFTER all required ones:
    filter_category_mapping=MAPPING,
    view_layout=VIEW_LAYOUT,
    section_definitions=SECTIONS,
    form_section_definitions=SECTIONS,
    entity_category=EntityCategory.MASTER,
    allowed_operations=[...],
    enable_soft_delete=True,  # NOT 'soft_delete'
    enable_audit_trail=True,  # NOT 'audit_trail'
    default_filters={...}
)
```

### ❌ INVALID Parameters (Don't use these)
- `soft_delete` → Use `enable_soft_delete`
- `audit_trail` → Use `enable_audit_trail`
- `branch_aware` → Not a valid parameter

---

## 2. Enum Values Verification

### ✅ FilterCategory (from filter_categories.py)
```python
FilterCategory.DATE        # NOT DATE_RANGE
FilterCategory.AMOUNT      # NOT RANGE
FilterCategory.SEARCH      # NOT TEXT
FilterCategory.SELECTION   # NOT SINGLE_SELECT
FilterCategory.RELATIONSHIP
```

### ✅ ButtonType (from core_definitions.py)
```python
ButtonType.PRIMARY
ButtonType.SECONDARY   # NOT DEFAULT
ButtonType.OUTLINE
ButtonType.WARNING
ButtonType.DANGER
ButtonType.SUCCESS
ButtonType.INFO
```

### ✅ CRUDOperation (from core_definitions.py)
```python
CRUDOperation.CREATE
CRUDOperation.READ
CRUDOperation.UPDATE
CRUDOperation.DELETE
CRUDOperation.LIST
CRUDOperation.VIEW      # NOT SEARCH
CRUDOperation.DOCUMENT
CRUDOperation.EXPORT
CRUDOperation.BULK_UPDATE
CRUDOperation.BULK_DELETE
```

### ✅ FieldType (from core_definitions.py)
```python
FieldType.TEXT
FieldType.NUMBER
FieldType.CURRENCY
FieldType.SELECT
FieldType.DATE
FieldType.DATETIME
FieldType.UUID
FieldType.BOOLEAN
# ... check core_definitions.py for complete list
```

---

## 3. Component Definitions

### ✅ SectionDefinition
```python
SectionDefinition(
    key="section_key",        # NOT 'name'
    title="Section Title",
    icon="fas fa-icon",
    columns=2,
    order=1,
    collapsible=False,
    default_collapsed=False
)
```

### ✅ ActionDefinition
```python
ActionDefinition(
    id="action_id",           # NOT 'name'
    label="Action Label",
    button_type=ButtonType.PRIMARY,
    icon="fas fa-icon",
    permission="entity.action"
)
```

### ✅ TabDefinition
```python
TabDefinition(
    key='tab_key',
    label='Tab Label',
    icon='fas fa-icon',
    sections={...},
    order=1,
    default_active=False
)
```

### ✅ ViewLayoutConfiguration
```python
ViewLayoutConfiguration(
    type=LayoutType.TABBED,   # NOT 'layout_type'
    tabs=TABS_DICT,
    default_tab='basic',
    responsive_breakpoint='md'
)
```

---

## 4. Model Relationship Verification

### ✅ ALWAYS Check Model Relationships
Before accessing related fields in code:

1. **Check the actual model definition:**
```python
# In master.py, check:
class Medicine(Base):
    category = relationship("MedicineCategory", ...)  # relationship name
    
class MedicineCategory(Base):
    name = Column(String(100), ...)  # actual field name
```

2. **Use correct attribute names:**
```python
# WRONG:
medicine.category.category_name  # Assumes field is 'category_name'

# RIGHT:
medicine.category.name  # Uses actual field 'name' from model
```

---

## 5. Entity Registry Configuration

### ✅ Register Entity Correctly
```python
# In entity_registry.py:
"medicine": EntityRegistration(  # Singular form
    category=EntityCategory.MASTER,
    module="app.config.modules.medicine_config",
    service_class="app.services.medicine_service.MedicineService",
    model_class="app.models.master.Medicine"
)
```

### ✅ Handle Singular/Plural in API
```python
# In universal_api.py, handle both forms:
if entity_type == 'medicines':
    config_entity_type = 'medicine'  # Map plural to singular

# Route handling:
elif entity_type in ['medicine', 'medicines']:  # Accept both
    results = search_medicines(...)
```

---

## 6. Common Pitfalls to Avoid

### ❌ DON'T
1. **Don't assume parameter names** - Always check `core_definitions.py`
2. **Don't duplicate parameters** - e.g., `actions` appearing twice
3. **Don't use outdated enum values** - e.g., `FilterCategory.TEXT` doesn't exist
4. **Don't assume model field names** - Always check the actual model
5. **Don't mix required and optional parameters** - Required must come first

### ✅ DO
1. **Copy from a working example** like `supplier_config.py`
2. **Verify every enum value** against source files
3. **Check model relationships** before accessing nested attributes
4. **Test incrementally** - Add basic config first, then enhance
5. **Read error messages carefully** - They often point to the exact issue

---

## 7. Step-by-Step Configuration Process

### Step 1: Start with Minimal Required Config
```python
ENTITY_CONFIG = EntityConfiguration(
    # Add ONLY required parameters first
    # Test that this works
)
```

### Step 2: Add Optional Parameters One by One
```python
# Add each optional parameter and test:
filter_category_mapping=...  # Test
view_layout=...              # Test
section_definitions=...      # Test
```

### Step 3: Verify All Enum Values
- Open `core_definitions.py` in one window
- Open `filter_categories.py` in another
- Verify EVERY enum value you use

### Step 4: Check Model Relationships
- Open the model file (`master.py`)
- Verify relationship names and field names
- Update any code that accesses these relationships

### Step 5: Test Entity Search
- Ensure API handles both singular and plural forms
- Verify all accessed model attributes exist
- Test with and without related data

---

## 8. Debugging Checklist

When you get an error:

1. **"got an unexpected keyword argument"**
   - Check exact parameter name in `EntityConfiguration` class
   - Verify you're not using deprecated parameters

2. **"has no attribute"**
   - Check the actual model definition
   - Verify relationship and field names

3. **"type object 'X' has no attribute 'Y'"**
   - Check the enum definition for correct values
   - Don't assume enum values exist

4. **"keyword argument repeated"**
   - Search for duplicate parameters in your config
   - Ensure parameters appear only once

---

## 9. Documentation References

Always keep these files open when creating configs:
1. `core_definitions.py` - All dataclass definitions and enums
2. `filter_categories.py` - FilterCategory enum values
3. `master.py` or relevant model file - Model definitions
4. `supplier_config.py` - Working example to copy from
5. `entity_registry.py` - For entity registration

---

## 10. Final Validation Checklist

Before considering configuration complete:

- [ ] All required EntityConfiguration parameters present and in order?
- [ ] No duplicate parameters?
- [ ] All enum values verified against source?
- [ ] All model relationships verified?
- [ ] Entity registered in entity_registry.py?
- [ ] API handles singular/plural forms?
- [ ] Search function uses correct model attributes?
- [ ] No assumed parameter names or values?
- [ ] Tested basic CRUD operations?
- [ ] Error-free entity search/dropdown?

---

## Key Takeaway

**NEVER ASSUME - ALWAYS VERIFY**: Every parameter name, every enum value, every model field must be verified against the actual source code. What seems logical or consistent might not be what's actually implemented.