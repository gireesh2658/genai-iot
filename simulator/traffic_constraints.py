"""
IoTSynth AI - Traffic Constraints and Protocol Mapping Module (Phase 4.1)
Encapsulates validation rules for network features, protocol mapping, layering rules,
mathematical consistency checks, and classification target integrity.
"""

import math
from typing import Dict, Any, List, Optional, Tuple, Set
import numpy as np


# ==============================================================================
# Protocol Number & Name Mapping (Layer 3/4 Transport)
# ==============================================================================

KNOWN_PROTOCOL_MAP: Dict[int, str] = {
    0: "HOPOPT",  # IPv6 Hop-by-Hop Option
    1: "ICMP",    # Internet Control Message Protocol
    2: "IGMP",    # Internet Group Management Protocol
    6: "TCP",     # Transmission Control Protocol
    17: "UDP",    # User Datagram Protocol
    47: "GRE",    # Generic Routing Encapsulation (Mirai botnets)
}

REVERSE_PROTOCOL_MAP: Dict[str, int] = {
    name: num for num, name in KNOWN_PROTOCOL_MAP.items()
}
# Add common protocol aliases
REVERSE_PROTOCOL_MAP["HTTP"] = 6    # Uses TCP
REVERSE_PROTOCOL_MAP["HTTPS"] = 6   # Uses TCP
REVERSE_PROTOCOL_MAP["MQTT"] = 6    # Uses TCP
REVERSE_PROTOCOL_MAP["RTSP"] = 6    # Uses TCP
REVERSE_PROTOCOL_MAP["DNS"] = 17    # Standard UDP (or TCP for large transfers)
REVERSE_PROTOCOL_MAP["COAP"] = 17   # Uses UDP


def protocol_number_to_name(proto_num: int, default: Optional[str] = None) -> str:
    """
    Convert an IANA protocol number to a standardized protocol string.
    If default is provided, returns default for unmapped numbers instead of raising ValueError.
    Raises ValueError on negative protocol numbers or unmapped numbers when default is None.
    """
    if not isinstance(proto_num, int) or proto_num < 0:
        raise ValueError(f"Protocol number must be a non-negative integer, got: {proto_num}")
    if proto_num in KNOWN_PROTOCOL_MAP:
        return KNOWN_PROTOCOL_MAP[proto_num]
    if default is not None:
        return default
    raise ValueError(
        f"Unsupported or unmapped protocol number '{proto_num}'. "
        f"Known protocol numbers: {sorted(list(KNOWN_PROTOCOL_MAP.keys()))}"
    )


def protocol_name_to_number(name: str) -> int:
    """
    Convert a protocol name to its primary transport protocol number.
    Raises ValueError on unknown protocol names.
    """
    clean_name = str(name).strip().upper()
    if clean_name in REVERSE_PROTOCOL_MAP:
        return REVERSE_PROTOCOL_MAP[clean_name]
    raise ValueError(
        f"Unsupported protocol name '{name}'. "
        f"Known protocols: {sorted(list(REVERSE_PROTOCOL_MAP.keys()))}"
    )


# ==============================================================================
# Approved Threat Classification Taxonomy
# ==============================================================================

APPROVED_MACRO_CATEGORIES: Set = {
    "Benign",
    "DDoS",
    "DoS",
    "Mirai",
    "Reconnaissance",
    "Spoofing",
    "Brute Force",
    "Web-based",
}

APPROVED_RAW_ATTACK_LABELS: Set = {
    "BENIGN",
    # DDoS (12)
    "DDOS-ICMP_FLOOD",
    "DDOS-UDP_FLOOD",
    "DDOS-TCP_FLOOD",
    "DDOS-SYN_FLOOD",
    "DDOS-RSTFINFLOOD",
    "DDOS-PSHACK_FLOOD",
    "DDOS-SYNONYMOUSIP_FLOOD",
    "DDOS-ICMP_FRAGMENTATION",
    "DDOS-ACK_FRAGMENTATION",
    "DDOS-UDP_FRAGMENTATION",
    "DDOS-SLOWLORIS",
    "DDOS-HTTP_FLOOD",
    # DoS (4)
    "DOS-UDP_FLOOD",
    "DOS-TCP_FLOOD",
    "DOS-SYN_FLOOD",
    "DOS-HTTP_FLOOD",
    # Mirai (3)
    "MIRAI-GREETH_FLOOD",
    "MIRAI-UDPPLAIN",
    "MIRAI-GREIP_FLOOD",
    # Reconnaissance (5)
    "VULNERABILITYSCAN",
    "RECON-HOSTDISCOVERY",
    "RECON-OSSCAN",
    "RECON-PORTSCAN",
    "RECON-PINGSWEEP",
    # Spoofing (2)
    "MITM-ARPSPOOFING",
    "DNS_SPOOFING",
    # Brute Force (1)
    "DICTIONARYBRUTEFORCE",
    # Web-based (6)
    "COMMANDINJECTION",
    "BROWSERHIJACKING",
    "XSS",
    "BACKDOOR_MALWARE",
    "SQLINJECTION",
    "UPLOADING_ATTACK",
}


# ==============================================================================
# Constraint Validation Engine
# ==============================================================================

class TrafficConstraintValidator:
    """
    Validates synthetic traffic records against physical network constraints,
    mathematical bounds, protocol layering, and target label integrity.
    """

    @classmethod
    def validate_finite_numbers(cls, record: Dict[str, Any]) -> List[str]:
        """Verify all numeric fields are finite (reject NaN, +inf, -inf)."""
        errors = []
        for key, val in record.items():
            if isinstance(val, (int, float)):
                if math.isnan(val) or math.isinf(val):
                    errors.append(f"Field '{key}' has non-finite numeric value: {val}")
        return errors

    @classmethod
    def validate_non_negative_metrics(cls, record: Dict[str, Any]) -> List[str]:
        """Verify volumetric and timing metrics are non-negative."""
        errors = []
        non_negative_fields = [
            "Header_Length", "Time_To_Live", "Rate", "IAT", "Number",
            "Min", "Max", "AVG", "Std", "Variance", "Tot sum",
            "syn_count", "ack_count", "fin_count", "rst_count"
        ]
        for field in non_negative_fields:
            if field in record:
                val = record[field]
                if isinstance(val, (int, float)) and val < 0:
                    errors.append(f"Field '{field}' cannot be negative, got: {val}")
        return errors

    @classmethod
    def validate_discrete_counts(cls, record: Dict[str, Any]) -> List[str]:
        """Verify discrete count and ID fields are integer-valued and Number >= 1."""
        errors = []
        count_fields = ["Number", "syn_count", "ack_count", "fin_count", "rst_count", "Protocol Type"]
        for field in count_fields:
            if field in record:
                val = record[field]
                if isinstance(val, (int, float)):
                    if not (isinstance(val, int) or (isinstance(val, float) and val.is_integer())):
                        errors.append(f"Field '{field}' must be integer-valued, got: {val}")
                elif val is not None:
                    errors.append(f"Field '{field}' must be numeric integer, got: {type(val).__name__}")

        num = record.get("Number")
        if isinstance(num, (int, float)) and num < 1:
            errors.append(f"Packet count 'Number' must be at least 1, got: {num}")

        return errors

    @classmethod
    def validate_protocol_name(cls, record: Dict[str, Any]) -> List[str]:
        """Verify protocol_name matches canonical transport protocol derived from Protocol Type."""
        errors = []
        proto_type = record.get("Protocol Type")
        proto_name = record.get("protocol_name")

        if not isinstance(proto_name, str) or not proto_name.strip():
            errors.append(f"Field 'protocol_name' must be a non-empty string, got: {proto_name}")
            return errors

        if isinstance(proto_type, int) and proto_type in KNOWN_PROTOCOL_MAP:
            expected_name = KNOWN_PROTOCOL_MAP[proto_type]
            if proto_name.strip().upper() != expected_name:
                errors.append(
                    f"Mismatched protocol: Protocol Type {proto_type} requires protocol_name '{expected_name}', "
                    f"got: '{proto_name}'."
                )
        return errors

    @classmethod
    def validate_packet_size_bounds(cls, record: Dict[str, Any]) -> List[str]:
        """Verify Min <= AVG <= Max when Number > 0."""
        errors = []
        p_min = record.get("Min")
        p_avg = record.get("AVG")
        p_max = record.get("Max")
        num = record.get("Number", 1)

        if isinstance(p_min, (int, float)) and isinstance(p_max, (int, float)):
            if p_min > p_max:
                errors.append(f"Packet size Min ({p_min}) cannot exceed Max ({p_max}).")

        if isinstance(p_min, (int, float)) and isinstance(p_avg, (int, float)):
            # Tolerance for floating rounding
            if p_avg < p_min - 0.01:
                errors.append(f"Packet size AVG ({p_avg}) cannot be less than Min ({p_min}).")

        if isinstance(p_max, (int, float)) and isinstance(p_avg, (int, float)):
            if p_avg > p_max + 0.01:
                errors.append(f"Packet size AVG ({p_avg}) cannot exceed Max ({p_max}).")

        # Mathematical consistency relation: AVG ~= Tot sum / Number (when Number > 0)
        tot_sum = record.get("Tot sum")
        if (
            isinstance(tot_sum, (int, float))
            and isinstance(num, (int, float))
            and isinstance(p_avg, (int, float))
            and num > 0
        ):
            expected_avg = tot_sum / num
            if abs(p_avg - expected_avg) > 0.05:  # Floating precision tolerance
                errors.append(
                    f"Inconsistent byte average: AVG is {p_avg}, but Tot sum / Number is {expected_avg:.2f}."
                )

        # Statistical relation: Std ~= sqrt(Variance)
        std_val = record.get("Std")
        var_val = record.get("Variance")
        if (
            isinstance(std_val, (int, float))
            and isinstance(var_val, (int, float))
            and var_val >= 0
        ):
            expected_std = math.sqrt(var_val)
            if not np.isclose(std_val, expected_std, atol=0.05, rtol=1e-3):
                errors.append(
                    f"Inconsistent dispersion: Std is {std_val}, but sqrt(Variance) is {expected_std:.4f}."
                )

        return errors

    @classmethod
    def validate_binary_indicators(cls, record: Dict[str, Any]) -> List[str]:
        """Verify protocol indicator masks are strictly 0 or 1."""
        errors = []
        indicators = [
            "HTTP", "HTTPS", "DNS", "Telnet", "SMTP", "SSH", "IRC",
            "TCP", "UDP", "DHCP", "ARP", "ICMP", "IGMP", "IPv", "LLC"
        ]
        for ind in indicators:
            if ind in record:
                val = record[ind]
                if val not in (0, 1, 0.0, 1.0):
                    errors.append(f"Protocol indicator '{ind}' must be 0 or 1, got: {val}")
        return errors

    @classmethod
    def validate_flag_numbers(cls, record: Dict[str, Any]) -> List[str]:
        """Verify normalized flag ratios are between 0.0 and 1.0."""
        errors = []
        flag_nums = [
            "fin_flag_number", "syn_flag_number", "rst_flag_number",
            "psh_flag_number", "ack_flag_number", "ece_flag_number", "cwr_flag_number"
        ]
        for fn in flag_nums:
            if fn in record:
                val = record[fn]
                if isinstance(val, (int, float)) and not (0.0 <= val <= 1.0):
                    errors.append(f"Flag number '{fn}' must be in [0.0, 1.0], got: {val}")
        return errors

    @classmethod
    def validate_protocol_layering(cls, record: Dict[str, Any]) -> List[str]:
        """
        Verify protocol compatibility:
        - TCP and UDP are mutually exclusive for a single transport flow.
        - If Protocol Type is ICMP (1), then TCP=0, UDP=0, and TCP flags/counts=0.
        - HTTP requires TCP transport (TCP=1).
        - HTTPS requires TCP or UDP (QUIC) transport.
        - DNS requires UDP or TCP transport.
        """
        errors = []
        tcp = record.get("TCP", 0)
        udp = record.get("UDP", 0)
        icmp = record.get("ICMP", 0)
        proto_type = record.get("Protocol Type")

        # Transport mutual exclusivity
        if tcp == 1 and udp == 1:
            errors.append("Invalid transport configuration: TCP and UDP cannot both be 1 for a single flow.")

        # ICMP constraints
        if proto_type == 1 or icmp == 1:
            if tcp == 1 or udp == 1:
                errors.append("ICMP flows cannot assert TCP=1 or UDP=1.")
            tcp_flags = ["syn_count", "ack_count", "fin_count", "rst_count"]
            for flag in tcp_flags:
                if record.get(flag, 0) > 0:
                    errors.append(f"ICMP flows cannot carry TCP flag count '{flag}' > 0.")
            flag_nums = [
                "fin_flag_number", "syn_flag_number", "rst_flag_number",
                "psh_flag_number", "ack_flag_number", "ece_flag_number", "cwr_flag_number"
            ]
            for fn in flag_nums:
                if record.get(fn, 0.0) > 0.0:
                    errors.append(f"ICMP flows cannot carry TCP flag number '{fn}' > 0.")

        # Application layer over transport
        if record.get("HTTP", 0) == 1 and tcp != 1:
            errors.append("HTTP traffic must be transported over TCP (TCP=1).")

        if record.get("HTTPS", 0) == 1 and tcp == 0 and udp == 0:
            errors.append("HTTPS traffic requires TCP or UDP (QUIC) transport.")

        if record.get("DNS", 0) == 1 and tcp == 0 and udp == 0:
            errors.append("DNS traffic requires UDP or TCP transport.")

        return errors

    @classmethod
    def validate_classification_targets(cls, record: Dict[str, Any]) -> List[str]:
        """Verify integrity of is_attack, label_category, and label_raw."""
        errors = []
        is_attack = record.get("is_attack")
        macro = record.get("label_category")
        raw = record.get("label_raw")

        if is_attack not in (0, 1):
            errors.append(f"Target 'is_attack' must be 0 or 1, got: {is_attack}")

        if macro not in APPROVED_MACRO_CATEGORIES:
            errors.append(f"Target 'label_category' '{macro}' not in approved categories: {APPROVED_MACRO_CATEGORIES}")

        if raw not in APPROVED_RAW_ATTACK_LABELS:
            errors.append(f"Target 'label_raw' '{raw}' not in approved attack labels list.")

        # Consistency between binary and category
        if is_attack == 0:
            if macro != "Benign" or raw != "BENIGN":
                errors.append(f"When is_attack == 0, label_category must be 'Benign' and label_raw 'BENIGN', got: ({macro}, {raw})")
        elif is_attack == 1:
            if macro == "Benign" or raw == "BENIGN":
                errors.append(f"When is_attack == 1, labels cannot be Benign/BENIGN, got: ({macro}, {raw})")

        return errors

    @classmethod
    def validate_record(cls, record: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Execute all constraint validations against a dictionary record.
        Returns (is_valid, list_of_errors).
        """
        all_errors: List[str] = []
        all_errors.extend(cls.validate_finite_numbers(record))
        all_errors.extend(cls.validate_non_negative_metrics(record))
        all_errors.extend(cls.validate_discrete_counts(record))
        all_errors.extend(cls.validate_protocol_name(record))
        all_errors.extend(cls.validate_packet_size_bounds(record))
        all_errors.extend(cls.validate_binary_indicators(record))
        all_errors.extend(cls.validate_flag_numbers(record))
        all_errors.extend(cls.validate_protocol_layering(record))
        all_errors.extend(cls.validate_classification_targets(record))
        return len(all_errors) == 0, all_errors
