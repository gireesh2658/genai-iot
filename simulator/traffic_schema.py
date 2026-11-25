"""
IoTSynth AI - Traffic Schema Specification (Phase 4.1)
Centralized definition of the 44-attribute synthetic IoT network traffic schema.
Defines column names, feature groups, canonical ordering, and expected data types.
"""

from typing import List, Dict, Set, Any, Tuple


# ==============================================================================
# Feature Group Definitions (Approved 44-Attribute Taxonomy)
# ==============================================================================

# Group A: Original Network Features (38 attributes - excluding redundant 'Tot size')
PROTOCOL_AND_NETWORK_FEATURES: List[str] = [
    "Protocol Type",
    "Header_Length",
    "Time_To_Live",
    "Rate",
    "IAT",
    "Number",
    "Min",
    "Max",
    "AVG",
    "Std",
    "Variance",
    "Tot sum",
]

FLAG_NUMBER_FEATURES: List[str] = [
    "fin_flag_number",
    "syn_flag_number",
    "rst_flag_number",
    "psh_flag_number",
    "ack_flag_number",
    "ece_flag_number",
    "cwr_flag_number",
]

FLAG_COUNT_FEATURES: List[str] = [
    "syn_count",
    "ack_count",
    "fin_count",
    "rst_count",
]

PROTOCOL_INDICATORS: List[str] = [
    "HTTP",
    "HTTPS",
    "DNS",
    "Telnet",
    "SMTP",
    "SSH",
    "IRC",
    "TCP",
    "UDP",
    "DHCP",
    "ARP",
    "ICMP",
    "IGMP",
    "IPv",
    "LLC",
]

ORIGINAL_NETWORK_FEATURES: List[str] = (
    PROTOCOL_AND_NETWORK_FEATURES
    + FLAG_NUMBER_FEATURES
    + FLAG_COUNT_FEATURES
    + PROTOCOL_INDICATORS
)  # 12 + 7 + 4 + 15 = 38 attributes

# Group B: Derived Features (2 attributes)
DERIVED_FEATURES: List[str] = [
    "protocol_name",
    "label_category",
]

# Group C: Simulated Metadata (2 attributes)
SIMULATED_METADATA: List[str] = [
    "device_id",
    "device_category",
]

# Group D: Classification Targets (2 attributes)
CLASSIFICATION_TARGETS: List[str] = [
    "is_attack",
    "label_raw",
]


# ==============================================================================
# Canonical Column Ordering (Exact 44 Attributes)
# ==============================================================================

CANONICAL_SCHEMA_COLUMNS: List[str] = [
    # 1-4: Metadata & Protocol Identifier
    "device_id",
    "device_category",
    "protocol_name",
    "Protocol Type",
    # 5-15: Network Flow Metrics
    "Header_Length",
    "Time_To_Live",
    "Rate",
    "IAT",
    "Number",
    "Min",
    "Max",
    "AVG",
    "Std",
    "Variance",
    "Tot sum",
    # 16-22: Normalized Transport Flag Numbers
    "fin_flag_number",
    "syn_flag_number",
    "rst_flag_number",
    "psh_flag_number",
    "ack_flag_number",
    "ece_flag_number",
    "cwr_flag_number",
    # 23-26: Transport Flag Counts
    "syn_count",
    "ack_count",
    "fin_count",
    "rst_count",
    # 27-41: Protocol Masks / Indicators
    "HTTP",
    "HTTPS",
    "DNS",
    "Telnet",
    "SMTP",
    "SSH",
    "IRC",
    "TCP",
    "UDP",
    "DHCP",
    "ARP",
    "ICMP",
    "IGMP",
    "IPv",
    "LLC",
    # 42-44: Multi-tier Target Labels
    "label_raw",
    "label_category",
    "is_attack",
]

TOTAL_ATTRIBUTES_COUNT: int = len(CANONICAL_SCHEMA_COLUMNS)  # Exactly 44


# ==============================================================================
# Machine Learning & Statistical Typing Classifications
# ==============================================================================

CONTINUOUS_NUMERICAL_FEATURES: List[str] = [
    "Header_Length",
    "Time_To_Live",
    "Rate",
    "IAT",
    "Min",
    "Max",
    "AVG",
    "Std",
    "Variance",
    "Tot sum",
    "fin_flag_number",
    "syn_flag_number",
    "rst_flag_number",
    "psh_flag_number",
    "ack_flag_number",
    "ece_flag_number",
    "cwr_flag_number",
]

DISCRETE_COUNT_FEATURES: List[str] = [
    "Number",
    "syn_count",
    "ack_count",
    "fin_count",
    "rst_count",
    "Protocol Type",
]

BINARY_INDICATOR_FEATURES: List[str] = [
    "HTTP",
    "HTTPS",
    "DNS",
    "Telnet",
    "SMTP",
    "SSH",
    "IRC",
    "TCP",
    "UDP",
    "DHCP",
    "ARP",
    "ICMP",
    "IGMP",
    "IPv",
    "LLC",
    "is_attack",
]

CATEGORICAL_STRING_FEATURES: List[str] = [
    "device_id",
    "device_category",
    "protocol_name",
    "label_raw",
    "label_category",
]

MODEL_INPUT_FEATURES: List[str] = [
    col for col in CANONICAL_SCHEMA_COLUMNS
    if col not in ("device_id", "device_category", "label_raw", "label_category", "is_attack", "protocol_name")
]

# Canonical data types mapping
COLUMN_DATA_TYPES: Dict[str, type] = {
    # String / Categorical
    "device_id": str,
    "device_category": str,
    "protocol_name": str,
    "label_raw": str,
    "label_category": str,
    # Discrete Counts & IDs
    "Protocol Type": int,
    "Number": int,
    "syn_count": int,
    "ack_count": int,
    "fin_count": int,
    "rst_count": int,
    # Continuous Floats
    "Header_Length": float,
    "Time_To_Live": float,
    "Rate": float,
    "IAT": float,
    "Min": float,
    "Max": float,
    "AVG": float,
    "Std": float,
    "Variance": float,
    "Tot sum": float,
    "fin_flag_number": float,
    "syn_flag_number": float,
    "rst_flag_number": float,
    "psh_flag_number": float,
    "ack_flag_number": float,
    "ece_flag_number": float,
    "cwr_flag_number": float,
    # Binary Indicators (0 or 1 integer representation)
    "HTTP": int,
    "HTTPS": int,
    "DNS": int,
    "Telnet": int,
    "SMTP": int,
    "SSH": int,
    "IRC": int,
    "TCP": int,
    "UDP": int,
    "DHCP": int,
    "ARP": int,
    "ICMP": int,
    "IGMP": int,
    "IPv": int,
    "LLC": int,
    "is_attack": int,
}


# ==============================================================================
# Helper Verification Functions
# ==============================================================================

def get_feature_group(column_name: str) -> str:
    """Return the high-level group to which a column belongs."""
    if column_name in SIMULATED_METADATA:
        return "Simulated Metadata"
    elif column_name in DERIVED_FEATURES:
        return "Derived Features"
    elif column_name in CLASSIFICATION_TARGETS:
        return "Classification Targets"
    elif column_name in ORIGINAL_NETWORK_FEATURES:
        return "Original Network Features"
    raise KeyError(f"Unknown column name '{column_name}' not in approved schema.")


def validate_schema_columns(
    columns: List[str],
    check_ordering: bool = True
) -> Tuple[bool, List[str]]:
    """
    Validate that a given list of column names matches the 44 approved columns exactly.
    If check_ordering is True, also verifies canonical column order.
    Returns (is_valid, list_of_errors).
    """
    errors: List[str] = []
    col_set = set(columns)
    expected_set = set(CANONICAL_SCHEMA_COLUMNS)

    missing = expected_set - col_set
    if missing:
        errors.append(f"Missing {len(missing)} required columns: {sorted(list(missing))}")

    unexpected = col_set - expected_set
    if unexpected:
        errors.append(f"Found {len(unexpected)} unexpected columns: {sorted(list(unexpected))}")

    if "Tot size" in col_set:
        errors.append("Column 'Tot size' is forbidden (redundant with 'AVG').")

    if check_ordering and not errors and columns != CANONICAL_SCHEMA_COLUMNS:
        errors.append("Columns present but ordering differs from CANONICAL_SCHEMA_COLUMNS.")

    return len(errors) == 0, errors
