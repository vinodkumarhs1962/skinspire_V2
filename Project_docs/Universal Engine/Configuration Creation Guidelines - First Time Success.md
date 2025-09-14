# Configuration Creation Guidelines - First Time Success

## CRITICAL RULES FOR CONFIGURATION FILES

### 1. **COPY FROM WORKING EXAMPLES**
- **ALWAYS** use an existing working configuration as a template
- **NEVER** add parameters not seen in other working configs
- If `purchase_orders_config.py` works, copy its EXACT structure
- If `supplier_payment_config.py` works, copy its EXACT pattern

### 2. **PARAMETER VERIFICATION**
Before adding ANY parameter to a configuration:
- Check if it exists in at least one other working config file
- If unsure, ASK: "Is parameter X valid for EntityConfiguration?"
- NEVER invent parameters like `model_class`, `sort_order` etc.

### 3. **STRUCTURE MATCHING**
```python
# If other configs use DICTIONARY:
ENTITY_DOCUMENT_CONFIGS = {
    "key1": DocumentConfiguration(...),
    "key2": DocumentConfiguration(...)
}

# DON'T use LIST:
ENTITY_DOCUMENT_CONFIGS = [  # WRONG!
    DocumentConfiguration(...),
]
```

### 4. **MINIMAL CHANGES ONLY**
When fixing errors:
- Remove ONLY the invalid parameter
- Don't add new parameters "to be helpful"
- Don't restructure working code
- Don't add features not requested

### 5. **VERIFICATION CHECKLIST**
Before providing any configuration:
- [ ] Based on a working example from the project?
- [ ] Every parameter exists in other configs?
- [ ] Structure matches other working configs?
- [ ] No assumptions made about parameters?
- [ ] Checked against core_definitions.py?

## SPECIFIC EXAMPLES

### ✅ CORRECT Approach:
```python
# Check purchase_orders_config.py first
# See it uses: document_configs = { "invoice": ..., "report": ... }
# Copy EXACT structure for new entity
```

### ❌ WRONG Approach:
```python
# Adding creative parameters:
model_class="..."  # Not in other configs!
sort_order="..."   # Doesn't exist!
sections=[DocumentSection(...)]  # Too complex!
```

## THE MASTER TEMPLATE PATTERN

When creating new entity configs, use this verification:

1. **Find Similar Entity**
   - Transaction entity? → Copy from `purchase_orders_config.py`
   - Master entity? → Copy from `supplier_config.py`
   - Payment entity? → Copy from `supplier_payment_config.py`

2. **Use ONLY These Parameters**
   ```python
   EntityConfiguration(
       # REQUIRED (from core_definitions.py)
       entity_type, name, plural_name, service_name,
       table_name, primary_key, title_field, subtitle_field,
       icon, page_title, description, searchable_fields,
       default_sort_field, default_sort_direction,
       fields, actions, summary_cards, permissions,
       
       # OPTIONAL (check if used in similar configs)
       view_layout, section_definitions,
       filter_category_mapping, default_filters,
       category_configs, primary_date_field,
       primary_amount_field, entity_category,
       universal_crud_enabled, allowed_operations,
       include_calculated_fields, enable_audit_trail,
       enable_soft_delete, enable_bulk_operations,
       enable_saved_filter_suggestions, enable_auto_submit,
       document_enabled, document_configs, default_document,
       document_permissions
   )
   ```

3. **For EntitySearchConfiguration**
   ```python
   EntitySearchConfiguration(
       # ONLY these parameters exist:
       target_entity, search_fields, display_template,
       min_chars, max_results, sort_field,
       additional_filters, service_method,
       cache_timeout, placeholder_template
       # NO sort_order, NO model_class!
   )
   ```

## WHEN IN DOUBT

**ASK THESE QUESTIONS:**
1. "Show me a working example of [EntityConfiguration] from the project"
2. "What parameters does [ClassName] accept according to core_definitions.py?"
3. "Show me how [similar_entity] handles this"
4. "Show me how purchase_orders_config.py defines this configuration"  - example

**NEVER:**
- Assume a parameter exists
- Add "helpful" extra parameters
- Create complex structures without verification
- Mix patterns from different sources