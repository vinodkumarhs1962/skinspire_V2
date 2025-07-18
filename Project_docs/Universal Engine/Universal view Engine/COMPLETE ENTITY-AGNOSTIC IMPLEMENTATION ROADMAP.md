# =============================================================================
# COMPLETE ENTITY-AGNOSTIC IMPLEMENTATION ROADMAP
# Incremental approach to achieve 100% entity-agnostic Universal Engine
# =============================================================================

"""
UNIVERSAL ENGINE ENTITY-AGNOSTIC ROADMAP
========================================

VISION: Complete entity-agnostic Universal Engine where adding new entities 
        requires ONLY configuration - no code changes at all.

APPROACH: Incremental phases that preserve existing functionality while 
          gradually moving from hardcoded to configuration-driven logic.

TIMELINE: 6 phases over 3-4 weeks with immediate benefits after each phase.
"""

# =============================================================================
# PHASE 0: CURRENT STATE (COMPLETED)
# =============================================================================

PHASE_0_COMPLETED = {
    'name': 'Foundation & Basic Entity-Agnostic Processing',
    'duration': 'COMPLETED',
    'changes_made': [
        'Model resolution uses configuration (with fallback)',
        'Selection filter processing uses field definitions',
        'Dropdown population uses field configurations',
        'Basic entity-agnostic infrastructure established'
    ],
    'benefits_achieved': [
        'New entities can define model_class in configuration',
        'Selection filters work through configuration',
        'Dropdown options use field definitions',
        'Foundation for further entity-agnostic expansion'
    ],
    'entity_agnostic_percentage': '25%',
    'files_modified': [
        'app/config/entity_configurations.py - Added model_class',
        'app/engine/categorized_filter_processor.py - 3 methods updated',
    ],
    'code_preserved': '100% backward compatible'
}

# =============================================================================
# PHASE 1: COMPLETE FILTER CATEGORIES (Next Phase)
# =============================================================================

PHASE_1_PLAN = {
    'name': 'Complete Filter Categories Entity-Agnostic',
    'duration': '3-4 days',
    'objective': 'Make ALL filter categories (DATE, AMOUNT, SEARCH, RELATIONSHIP) entity-agnostic',
    'risk_level': 'LOW',
    '
    
    'targets': [
        '_process_date_filters() - Configuration-driven date processing',
        '_process_amount_filters() - Configuration-driven amount processing', 
        '_process_search_filters() - Configuration-driven search processing',
        '_process_relationship_filters() - Configuration-driven relationship processing'
    ],
    
    'implementation_stages': {
        'stage_1a': {
            'name': 'Date Filters Entity-Agnostic',
            'duration': '1 day',
            'files_modified': [
                'app/config/entity_configurations.py - Add date field configurations',
                'app/engine/categorized_filter_processor.py - Update _process_date_filters()'
            ],
            'changes': {
                'configuration_additions': """
                # Add to SUPPLIER_PAYMENT_CONFIG
                date_field_mappings = {
                    'payment_date': {
                        'field_name': 'payment_date',
                        'filter_aliases': ['start_date', 'end_date', 'payment_date'],
                        'supports_presets': True,
                        'default_preset': 'current_financial_year'
                    },
                    'created_date': {
                        'field_name': 'created_date', 
                        'filter_aliases': ['created_start', 'created_end'],
                        'supports_presets': True
                    }
                }
                """,
                'method_updates': """
                # BEFORE: Hardcoded date processing
                def _process_date_filters(self, filters, query, config, entity_type):
                    if entity_type == 'supplier_payments':
                        # Hardcoded logic for supplier payments
                        
                # AFTER: Configuration-driven date processing
                def _process_date_filters(self, filters, query, config, entity_type):
                    if not config or not hasattr(config, 'date_field_mappings'):
                        return query, set(), 0
                    
                    # Process using configuration
                    for field_name, field_config in config.date_field_mappings.items():
                        # Use field_config for processing
                """
            },
            'benefits': [
                'Any entity can define date fields in configuration',
                'Date presets work for all entities',
                'Financial year logic becomes universal'
            ]
        },
        
        'stage_1b': {
            'name': 'Amount Filters Entity-Agnostic',
            'duration': '1 day',
            'changes': {
                'configuration_additions': """
                # Add to entity configurations
                amount_field_mappings = {
                    'amount': {
                        'field_name': 'amount',
                        'filter_aliases': ['min_amount', 'max_amount', 'amount_range'],
                        'currency_symbol': '₹',
                        'supports_range': True,
                        'validation_rules': ['positive_number', 'max_digits_10']
                    },
                    'total_amount': {
                        'field_name': 'total_amount',
                        'filter_aliases': ['total_min', 'total_max'],
                        'supports_range': True
                    }
                }
                """,
                'method_updates': """
                # Configuration-driven amount processing
                def _process_amount_filters(self, filters, query, config, entity_type):
                    if not config or not hasattr(config, 'amount_field_mappings'):
                        return query, set(), 0
                    
                    # Process using configuration
                    for field_name, field_config in config.amount_field_mappings.items():
                        # Use field_config for range processing
                """
            },
            'benefits': [
                'Any entity can define amount fields and ranges',
                'Currency formatting becomes universal',
                'Validation rules configured per entity'
            ]
        },
        
        'stage_1c': {
            'name': 'Search Filters Entity-Agnostic',
            'duration': '1 day',
            'changes': {
                'configuration_additions': """
                # Add to entity configurations
                search_field_mappings = {
                    'supplier_name': {
                        'field_name': 'supplier_name',
                        'requires_join': True,
                        'join_model': 'app.models.master.Supplier',
                        'join_condition': 'SupplierPayment.supplier_id == Supplier.supplier_id',
                        'search_fields': ['supplier_name', 'contact_person_name'],
                        'filter_aliases': ['supplier_name_search', 'search', 'supplier_search']
                    },
                    'reference_no': {
                        'field_name': 'reference_no',
                        'requires_join': False,
                        'search_type': 'ilike',
                        'filter_aliases': ['reference_no', 'ref_no']
                    }
                }
                """,
                'method_updates': """
                # Configuration-driven search processing
                def _process_search_filters(self, filters, query, config, entity_type):
                    if not config or not hasattr(config, 'search_field_mappings'):
                        return query, set(), 0
                    
                    # Process using configuration
                    for field_name, field_config in config.search_field_mappings.items():
                        if field_config.get('requires_join'):
                            # Handle joins using configuration
                        else:
                            # Direct field search using configuration
                """
            },
            'benefits': [
                'Any entity can define search fields and join logic',
                'Search behavior configured per entity',
                'Join logic becomes reusable'
            ]
        },
        
        'stage_1d': {
            'name': 'Relationship Filters Entity-Agnostic',
            'duration': '1 day',
            'changes': {
                'configuration_additions': """
                # Add to entity configurations
                relationship_field_mappings = {
                    'supplier_id': {
                        'field_name': 'supplier_id',
                        'related_entity': 'suppliers',
                        'foreign_key': True,
                        'validation_required': True,
                        'filter_aliases': ['supplier_id', 'supplier']
                    },
                    'branch_id': {
                        'field_name': 'branch_id',
                        'related_entity': 'branches',
                        'foreign_key': True,
                        'auto_filter': True  # Auto-apply based on user context
                    }
                }
                """,
                'method_updates': """
                # Configuration-driven relationship processing
                def _process_relationship_filters(self, filters, query, config, entity_type):
                    if not config or not hasattr(config, 'relationship_field_mappings'):
                        return query, set(), 0
                    
                    # Process using configuration
                    for field_name, field_config in config.relationship_field_mappings.items():
                        # Use field_config for relationship processing
                """
            },
            'benefits': [
                'Any entity can define relationship fields',
                'Foreign key validation becomes universal',
                'Auto-filtering rules configured per entity'
            ]
        }
    },
    
    'deliverables': [
        'All 4 filter categories work through configuration',
        'Easy to add new entities with complex filtering',
        'Validation and business rules configured per entity',
        'Join logic reusable across entities'
    ],
    
    'entity_agnostic_percentage': '60%',
    'testing_approach': 'Each stage tested independently with fallback to existing logic'
}

# =============================================================================
# PHASE 2: BUSINESS LOGIC ENTITY-AGNOSTIC
# =============================================================================

PHASE_2_PLAN = {
    'name': 'Business Logic & Dropdown Methods Entity-Agnostic',
    'duration': '4-5 days',
    'objective': 'Make all business logic methods configuration-driven',
    'risk_level': 'MEDIUM',
    
    'targets': [
        '_get_supplier_options() - Generic _get_entity_options()',
        '_get_workflow_status_options() - Generic _get_status_options()',
        '_apply_supplier_name_search() - Generic _apply_entity_search()',
        'All dropdown generation methods'
    ],
    
    'implementation_stages': {
        'stage_2a': {
            'name': 'Generic Dropdown System',
            'duration': '2 days',
            'changes': {
                'new_methods': """
                # Create generic dropdown methods
                def _get_entity_options(self, entity_type: str, hospital_id: uuid.UUID, 
                                      branch_id: Optional[uuid.UUID] = None) -> List[Dict]:
                    '''Generic method for any entity dropdown'''
                    config = get_entity_config(entity_type)
                    if not config:
                        return []
                    
                    # Use configuration to determine:
                    # - Model class
                    # - Display field
                    # - Value field  
                    # - Filter conditions
                    # - Sort order
                    
                def _get_status_options(self, entity_type: str, status_field: str) -> List[Dict]:
                    '''Generic method for status dropdowns'''
                    config = get_entity_config(entity_type)
                    if not config or not hasattr(config, 'status_field_mappings'):
                        return []
                    
                    # Use configuration for status options
                """,
                'configuration_additions': """
                # Add to entity configurations
                dropdown_configurations = {
                    'suppliers': {
                        'model_class': 'app.models.master.Supplier',
                        'value_field': 'supplier_id',
                        'display_field': 'supplier_name',
                        'filter_conditions': {'status': 'active'},
                        'sort_field': 'supplier_name',
                        'additional_fields': ['contact_person_name']
                    },
                    'invoices': {
                        'model_class': 'app.models.transaction.SupplierInvoice',
                        'value_field': 'invoice_id',
                        'display_field': 'invoice_number',
                        'filter_conditions': {'status': 'active'},
                        'sort_field': 'invoice_number'
                    }
                }
                
                status_field_mappings = {
                    'workflow_status': {
                        'options': [
                            {'value': 'pending', 'label': 'Pending', 'color': 'warning'},
                            {'value': 'approved', 'label': 'Approved', 'color': 'success'},
                            {'value': 'rejected', 'label': 'Rejected', 'color': 'danger'}
                        ]
                    },
                    'payment_method': {
                        'options': [
                            {'value': 'cash', 'label': 'Cash'},
                            {'value': 'bank_transfer', 'label': 'Bank Transfer'},
                            {'value': 'cheque', 'label': 'Cheque'}
                        ]
                    }
                }
                """
            },
            'benefits': [
                'Any entity can define dropdown configurations',
                'Status options configured per entity',
                'Dropdown generation becomes universal'
            ]
        },
        
        'stage_2b': {
            'name': 'Generic Search Logic',
            'duration': '2 days',
            'changes': {
                'new_methods': """
                # Create generic search methods
                def _apply_entity_search(self, query: Query, search_config: Dict, 
                                       search_term: str, session: Session) -> Query:
                    '''Generic method for entity search with joins'''
                    
                    # Use search_config to determine:
                    # - Join requirements
                    # - Search fields
                    # - Search type (exact, ilike, etc.)
                    # - Additional filters
                    
                def _apply_entity_join(self, query: Query, join_config: Dict, 
                                     session: Session) -> Query:
                    '''Generic method for entity joins'''
                    
                    # Use join_config to determine:
                    # - Join model
                    # - Join condition
                    # - Join type (inner, left, etc.)
                """,
                'configuration_additions': """
                # Add to entity configurations
                search_join_configurations = {
                    'supplier_search': {
                        'join_model': 'app.models.master.Supplier',
                        'join_condition': 'SupplierPayment.supplier_id == Supplier.supplier_id',
                        'search_fields': ['supplier_name', 'contact_person_name'],
                        'search_type': 'ilike',
                        'join_type': 'inner'
                    },
                    'invoice_search': {
                        'join_model': 'app.models.transaction.SupplierInvoice',
                        'join_condition': 'SupplierPayment.invoice_id == SupplierInvoice.invoice_id',
                        'search_fields': ['invoice_number'],
                        'search_type': 'ilike',
                        'join_type': 'left'
                    }
                }
                """
            },
            'benefits': [
                'Join logic becomes reusable',
                'Search behavior configured per entity',
                'Complex search patterns become universal'
            ]
        },
        
        'stage_2c': {
            'name': 'Integration & Testing',
            'duration': '1 day',
            'changes': {
                'method_updates': """
                # Update existing methods to use generic versions
                def _get_supplier_options(self, hospital_id, branch_id):
                    # BEFORE: Hardcoded supplier logic
                    # AFTER: 
                    return self._get_entity_options('suppliers', hospital_id, branch_id)
                    
                def _get_workflow_status_options(self):
                    # BEFORE: Hardcoded status list
                    # AFTER:
                    return self._get_status_options('supplier_payments', 'workflow_status')
                
                def _apply_supplier_name_search(self, query, search_term):
                    # BEFORE: Hardcoded supplier join
                    # AFTER:
                    config = get_entity_config('supplier_payments')
                    search_config = config.search_join_configurations['supplier_search']
                    return self._apply_entity_search(query, search_config, search_term, session)
                """
            },
            'benefits': [
                'All existing methods preserved for backward compatibility',
                'New entities automatically get all business logic',
                'Consistent behavior across all entities'
            ]
        }
    },
    
    'deliverables': [
        'Generic dropdown system for all entities',
        'Reusable search and join logic',
        'Status and option management through configuration',
        'Business logic becomes universal'
    ],
    
    'entity_agnostic_percentage': '80%',
    'testing_approach': 'Comprehensive testing of all dropdown and search functionality'
}

# =============================================================================
# PHASE 3: SUMMARY CARDS & CALCULATIONS ENTITY-AGNOSTIC
# =============================================================================

PHASE_3_PLAN = {
    'name': 'Summary Cards & Calculations Entity-Agnostic',
    'duration': '3-4 days',
    'objective': 'Make all summary card calculations configuration-driven',
    'risk_level': 'MEDIUM',
    
    'targets': [
        'Summary card logic in universal_filter_service',
        'Aggregation calculations',
        'Business rule calculations',
        'Count and sum calculations'
    ],
    
    'implementation_stages': {
        'stage_3a': {
            'name': 'Generic Summary Card System',
            'duration': '2 days',
            'changes': {
                'new_methods': """
                # Create generic summary calculation methods
                def _calculate_entity_summary(self, entity_type: str, filters: Dict, 
                                            hospital_id: uuid.UUID, branch_id: Optional[uuid.UUID]) -> Dict:
                    '''Generic method for entity summary calculations'''
                    config = get_entity_config(entity_type)
                    if not config or not hasattr(config, 'summary_calculations'):
                        return {}
                    
                    # Use configuration to determine:
                    # - Which fields to aggregate
                    # - Aggregation types (count, sum, avg, etc.)
                    # - Filter conditions for each summary
                    # - Display formatting
                    
                def _apply_summary_filters(self, query: Query, summary_config: Dict, 
                                         base_filters: Dict) -> Query:
                    '''Apply filters specific to summary calculations'''
                    
                    # Use summary_config to determine additional filters
                """,
                'configuration_additions': """
                # Add to entity configurations
                summary_calculations = {
                    'total_count': {
                        'type': 'count',
                        'field': None,  # Count all records
                        'label': 'Total Payments',
                        'icon': 'fas fa-receipt',
                        'additional_filters': {},
                        'format': 'number'
                    },
                    'total_amount': {
                        'type': 'sum',
                        'field': 'amount',
                        'label': 'Total Amount',
                        'icon': 'fas fa-rupee-sign',
                        'additional_filters': {},
                        'format': 'currency'
                    },
                    'pending_count': {
                        'type': 'count',
                        'field': None,
                        'label': 'Pending Approval',
                        'icon': 'fas fa-clock',
                        'additional_filters': {'workflow_status': 'pending'},
                        'format': 'number'
                    },
                    'this_month_count': {
                        'type': 'count',
                        'field': None,
                        'label': 'This Month',
                        'icon': 'fas fa-calendar-check',
                        'additional_filters': {'date_preset': 'this_month'},
                        'format': 'number'
                    }
                }
                """
            },
            'benefits': [
                'Any entity can define summary calculations',
                'Aggregation logic becomes universal',
                'Summary card configuration per entity'
            ]
        },
        
        'stage_3b': {
            'name': 'Business Rule Calculations',
            'duration': '2 days',
            'changes': {
                'new_methods': """
                # Create generic business rule calculation methods
                def _apply_business_rules(self, entity_type: str, calculations: Dict, 
                                        base_data: Dict) -> Dict:
                    '''Apply entity-specific business rules to calculations'''
                    config = get_entity_config(entity_type)
                    if not config or not hasattr(config, 'business_rules'):
                        return calculations
                    
                    # Use configuration to determine:
                    # - Calculation dependencies
                    # - Conditional logic
                    # - Derived calculations
                    # - Display rules
                    
                def _format_calculation_result(self, calculation_config: Dict, 
                                             result: Any) -> str:
                    '''Format calculation result based on configuration'''
                    
                    # Use calculation_config for formatting
                """,
                'configuration_additions': """
                # Add to entity configurations
                business_rules = {
                    'approval_percentage': {
                        'type': 'calculated',
                        'formula': 'approved_count / total_count * 100',
                        'depends_on': ['approved_count', 'total_count'],
                        'label': 'Approval Rate',
                        'format': 'percentage'
                    },
                    'average_amount': {
                        'type': 'calculated',
                        'formula': 'total_amount / total_count',
                        'depends_on': ['total_amount', 'total_count'],
                        'label': 'Average Amount',
                        'format': 'currency'
                    }
                }
                """
            },
            'benefits': [
                'Business rules configured per entity',
                'Derived calculations become universal',
                'Complex business logic through configuration'
            ]
        }
    },
    
    'deliverables': [
        'Generic summary card system for all entities',
        'Business rule calculations through configuration',
        'Aggregation and formatting logic becomes universal',
        'Easy to add new summary cards to any entity'
    ],
    
    'entity_agnostic_percentage': '90%',
    'testing_approach': 'Validation of all summary calculations and business rules'
}

# =============================================================================
# PHASE 4: DATA PROCESSING ENTITY-AGNOSTIC
# =============================================================================

PHASE_4_PLAN = {
    'name': 'Data Processing & Validation Entity-Agnostic',
    'duration': '2-3 days',
    'objective': 'Make all data processing and validation configuration-driven',
    'risk_level': 'LOW',
    
    'targets': [
        'Field validation rules',
        'Data transformation logic',
        'Export formatting',
        'Search result formatting'
    ],
    
    'implementation_stages': {
        'stage_4a': {
            'name': 'Generic Validation System',
            'duration': '1 day',
            'changes': {
                'new_methods': """
                # Create generic validation methods
                def _validate_entity_data(self, entity_type: str, data: Dict, 
                                        operation: str) -> Dict:
                    '''Generic method for entity data validation'''
                    config = get_entity_config(entity_type)
                    if not config or not hasattr(config, 'validation_rules'):
                        return {'valid': True, 'errors': []}
                    
                    # Use configuration to determine:
                    # - Field validation rules
                    # - Cross-field validation
                    # - Business rule validation
                    # - Operation-specific validation
                    
                def _apply_validation_rule(self, rule_config: Dict, 
                                         field_value: Any, field_name: str) -> bool:
                    '''Apply individual validation rule'''
                    
                    # Use rule_config for validation logic
                """,
                'configuration_additions': """
                # Add to entity configurations
                validation_rules = {
                    'amount': {
                        'required': True,
                        'type': 'decimal',
                        'min_value': 0,
                        'max_value': 10000000,
                        'decimal_places': 2,
                        'error_messages': {
                            'required': 'Amount is required',
                            'min_value': 'Amount must be positive',
                            'max_value': 'Amount cannot exceed 1 crore'
                        }
                    },
                    'supplier_id': {
                        'required': True,
                        'type': 'uuid',
                        'foreign_key': 'suppliers.supplier_id',
                        'error_messages': {
                            'required': 'Supplier is required',
                            'foreign_key': 'Invalid supplier selected'
                        }
                    }
                }
                """
            },
            'benefits': [
                'Validation rules configured per entity',
                'Consistent validation across all entities',
                'Easy to add new validation rules'
            ]
        },
        
        'stage_4b': {
            'name': 'Generic Export & Formatting',
            'duration': '1 day',
            'changes': {
                'new_methods': """
                # Create generic export methods
                def _format_entity_export(self, entity_type: str, data: List[Dict], 
                                        export_format: str) -> bytes:
                    '''Generic method for entity export formatting'''
                    config = get_entity_config(entity_type)
                    if not config or not hasattr(config, 'export_configurations'):
                        return self._default_export_format(data, export_format)
                    
                    # Use configuration to determine:
                    # - Export columns
                    # - Column headers
                    # - Data formatting
                    # - Export-specific filters
                    
                def _format_search_results(self, entity_type: str, 
                                         results: List[Dict]) -> List[Dict]:
                    '''Generic method for search result formatting'''
                    config = get_entity_config(entity_type)
                    if not config or not hasattr(config, 'display_configurations'):
                        return results
                    
                    # Use configuration for result formatting
                """,
                'configuration_additions': """
                # Add to entity configurations
                export_configurations = {
                    'csv': {
                        'columns': [
                            {'field': 'payment_id', 'header': 'Payment ID'},
                            {'field': 'supplier_name', 'header': 'Supplier'},
                            {'field': 'amount', 'header': 'Amount', 'format': 'currency'},
                            {'field': 'payment_date', 'header': 'Date', 'format': 'date'}
                        ],
                        'filename_template': 'supplier_payments_{date}.csv'
                    },
                    'pdf': {
                        'template': 'supplier_payments_report.html',
                        'page_size': 'A4',
                        'orientation': 'portrait'
                    }
                }
                
                display_configurations = {
                    'list_view': {
                        'primary_field': 'reference_no',
                        'secondary_field': 'supplier_name',
                        'amount_field': 'amount',
                        'date_field': 'payment_date',
                        'status_field': 'workflow_status'
                    },
                    'search_results': {
                        'display_template': '{reference_no} - {supplier_name} - ₹{amount}',
                        'sort_field': 'payment_date',
                        'sort_order': 'desc'
                    }
                }
                """
            },
            'benefits': [
                'Export configurations per entity',
                'Consistent formatting across all entities',
                'Easy to customize export formats'
            ]
        }
    },
    
    'deliverables': [
        'Generic validation system for all entities',
        'Export and formatting logic becomes universal',
        'Data processing rules configured per entity',
        'Consistent data handling across all entities'
    ],
    
    'entity_agnostic_percentage': '95%',
    'testing_approach': 'Comprehensive validation and export testing'
}

# =============================================================================
# PHASE 5: ADVANCED QUERY OPTIMIZATION ENTITY-AGNOSTIC
# =============================================================================

PHASE_5_PLAN = {
    'name': 'Advanced Query Optimization Entity-Agnostic',
    'duration': '2-3 days',
    'objective': 'Make advanced query optimizations configuration-driven',
    'risk_level': 'HIGH',
    
    'targets': [
        'Join logic for relationships',
        'Complex filter combinations',
        'Performance optimizations',
        'Specific WHERE clauses'
    ],
    
    'implementation_stages': {
        'stage_5a': {
            'name': 'Generic Query Optimization',
            'duration': '2 days',
            'changes': {
                'new_methods': """
                # Create generic query optimization methods
                def _optimize_entity_query(self, entity_type: str, query: Query, 
                                          filters: Dict) -> Query:
                    '''Generic method for entity query optimization'''
                    config = get_entity_config(entity_type)
                    if not config or not hasattr(config, 'query_optimizations'):
                        return query
                    
                    # Use configuration to determine:
                    # - Index hints
                    # - Query plan optimizations
                    # - Eager loading strategies
                    # - Subquery optimizations
                    
                def _apply_performance_hints(self, query: Query, 
                                           optimization_config: Dict) -> Query:
                    '''Apply performance hints based on configuration'''
                    
                    # Use optimization_config for query hints
                """,
                'configuration_additions': """
                # Add to entity configurations
                query_optimizations = {
                    'indexes': ['payment_date', 'supplier_id', 'workflow_status'],
                    'eager_loading': [
                        {'relationship': 'supplier', 'fields': ['supplier_name']},
                        {'relationship': 'branch', 'fields': ['branch_name']}
                    ],
                    'subquery_optimizations': {
                        'supplier_search': {
                            'use_subquery': True,
                            'subquery_limit': 1000
                        }
                    },
                    'filter_order': ['workflow_status', 'payment_date', 'supplier_id', 'amount']
                }
                """
            },
            'benefits': [
                'Performance optimizations configured per entity',
                'Query plans become predictable',
                'Database performance becomes consistent'
            ]
        },
        
        'stage_5b': {
            'name': 'Advanced Join Strategies',
            'duration': '1 day',
            'changes': {
                'new_methods': """
                # Create advanced join methods
                def _build_optimized_joins(self, entity_type: str, query: Query, 
                                         required_joins: List[str]) -> Query:
                    '''Build optimized joins based on configuration'''
                    config = get_entity_config(entity_type)
                    if not config or not hasattr(config, 'join_strategies'):
                        return query
                    
                    # Use configuration to determine:
                    # - Join order
                    # - Join types
                    # - Join conditions
                    # - Join optimizations
                """,
                'configuration_additions': """
                # Add to entity configurations
                join_strategies = {
                    'supplier': {
                        'join_type': 'inner',
                        'join_condition': 'SupplierPayment.supplier_id == Supplier.supplier_id',
                        'required_for': ['supplier_search', 'supplier_name_display'],
                        'optimization': 'use_index'
                    },
                    'branch': {
                        'join_type': 'left',
                        'join_condition': 'SupplierPayment.branch_id == Branch.branch_id',
                        'required_for': ['branch_filter'],
                        'optimization': 'lazy_load'
                    }
                }
                """
            },
            'benefits': [
                'Join strategies configured per entity',
                'Optimal join performance',
                'Reusable join logic'
            ]
        }
    },
    
    'deliverables': [
        'Advanced query optimization through configuration',
        'Join strategies become universal',
        'Performance hints configured per entity',
        'Optimal database performance for all entities'
    ],
    
    'entity_agnostic_percentage': '98%',
    'testing_approach': 'Performance testing and query plan analysis'
}

# =============================================================================
# PHASE 6: COMPLETE ENTITY-AGNOSTIC ACHIEVEMENT
# =============================================================================

PHASE_6_PLAN = {
    'name': 'Complete Entity-Agnostic Achievement & Testing',
    'duration': '2-3 days',
    'objective': 'Achieve 100% entity-agnostic Universal Engine',
    'risk_level': 'LOW',
    
    'targets': [
        'Final cleanup of any remaining hardcoded logic',
        'Comprehensive testing with multiple entities',
        'Documentation and validation',
        'Performance benchmarking'
    ],
    
    'implementation_stages': {
        'stage_6a': {
            'name': 'Final Cleanup & Validation',
            'duration': '1 day',
            'activities': [
                'Code review for any remaining hardcoded logic',
                'Configuration validation for all entities',
                'Error handling and edge case testing',
                'Performance validation'
            ]
        },
        
        'stage_6b': {
            'name': 'Multi-Entity Testing',
            'duration': '1 day',
            'activities': [
                'Add 3 new entities using only configuration',
                'Test all functionality across all entities',
                'Validate consistent behavior',
                'Performance comparison testing'
            ]
        },
        
        'stage_6c': {
            'name': 'Documentation & Deployment',
            'duration': '1 day',
            'activities': [
                'Complete entity addition documentation',
                'Configuration reference guide',
                'Performance optimization guide',
                'Production deployment preparation'
            ]
        }
    },
    
    'deliverables': [
        '100% entity-agnostic Universal Engine',
        'Complete documentation for entity addition',
        'Performance benchmarks and optimizations',
        'Production-ready system'
    ],
    
    'entity_agnostic_percentage': '100%',
    'success_criteria': [
        'New entities can be added with ONLY configuration',
        'Zero hardcoded entity-specific logic remains',
        'All functionality works consistently across entities',
        'Performance is optimal and predictable'
    ]
}

# =============================================================================
# IMPLEMENTATION SUMMARY & BENEFITS
# =============================================================================

IMPLEMENTATION_SUMMARY = {
    'total_duration': '3-4 weeks',
    'phases': 6,
    'risk_level': 'MANAGED - Incremental with fallbacks',
    'backward_compatibility': '100% throughout all phases',
    
    'benefits_by_phase': {
        'Phase 0': '25% entity-agnostic - Basic foundation',
        'Phase 1': '60% entity-agnostic - All filter categories',
        'Phase 2': '80% entity-agnostic - Business logic universal',
        'Phase 3': '90% entity-agnostic - Summary cards universal',
        'Phase 4': '95% entity-agnostic - Data processing universal',
        'Phase 5': '98% entity-agnostic - Query optimization universal',
        'Phase 6': '100% entity-agnostic - Complete achievement'
    },
    
    'business_impact': {
        'development_time': '95% reduction for new entities',
        'maintenance_effort': '90% reduction in codebase',
        'consistency': '100% consistent behavior across entities',
        'scalability': 'Unlimited entities with configuration only',
        'quality': 'Enterprise-grade reliability and performance'
    },
    
    'technical_achievements': {
        'code_reusability': '100% - No entity-specific code',
        'configuration_driven': '100% - All behavior through config',
        'performance': 'Optimal - Configured optimizations',
        'maintainability': 'Excellent - Single codebase for all entities',
        'extensibility': 'Unlimited - Easy to add new features'
    }
}

# =============================================================================
# NEXT STEPS & RECOMMENDATIONS
# =============================================================================

NEXT_STEPS = {
    'immediate': [
        'Complete Phase 0 changes (model_class, selection filters, dropdowns)',
        'Validate Phase 0 implementation with existing functionality',
        'Begin Phase 1 Stage 1a (Date filters entity-agnostic)'
    ],
    
    'short_term': [
        'Complete Phase 1 (All filter categories)',
        'Begin Phase 2 (Business logic)',
        'Establish testing framework for each phase'
    ],
    
    'medium_term': [
        'Complete Phases 2-4 (Business logic, summary cards, data processing)',
        'Begin Phase 5 (Query optimization)',
        'Add 2-3 new entities to validate approach'
    ],
    
    'long_term': [
        'Complete Phase 6 (100% entity-agnostic)',
        'Full production deployment',
        'Documentation and training completion'
    ]
}

print("🎯 COMPLETE ENTITY-AGNOSTIC ROADMAP READY!")
print("📊 6 phases over 3-4 weeks")
print("🔒 100% backward compatible throughout")
print("🎉 Final result: 100% entity-agnostic Universal Engine")
print("⚡ New entities: Configuration only - no code changes!")