"""DDL constants for the additive manual IPv4 slice, not all identifiers."""
NAMESPACE_PATTERN = r'[a-z0-9][a-z0-9._:-]{0,254}'
COLUMNS = ('id','resource_id','identifier_type','identifier_value','normalized_value','namespace',
           'source_type','source_instance','first_seen_at','last_seen_at','verified_at',
           'verification_status','confidence','evidence','valid_from','valid_until','created_at','updated_at')
MANUAL_PREDICATE = "identifier_type IN ('ipv4','IPv4') AND source_type = 'manual'"
OPEN_PREDICATE = MANUAL_PREDICATE + ' AND valid_until IS NULL'
NAMESPACE_CHECK = "NOT (" + MANUAL_PREDICATE + ") OR (namespace IS NOT NULL AND namespace COLLATE \"C\" ~ '^[a-z0-9][a-z0-9._:-]{0,254}$')"
