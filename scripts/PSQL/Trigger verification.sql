SELECT 
    event_object_table as table_name,
    trigger_name,
    event_manipulation as trigger_event,
    action_statement as trigger_action,
    action_timing as timing
FROM information_schema.triggers 
WHERE trigger_schema = 'public'
ORDER BY event_object_table, trigger_name;  