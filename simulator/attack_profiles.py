"""
IoTSynth AI - Attack Profiles Module (Phase 4.3)
Defines attack taxonomies, attack profile metadata, and mappings covering all
33 CICIoT2023 malicious traffic classes across 7 attack macro families.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Set


class AttackCategory(str, Enum):
    """Approved Macro Threat Categories from CICIoT2023 taxonomy."""
    DDOS = "DDoS"
    DOS = "DoS"
    MIRAI = "Mirai"
    RECONNAISSANCE = "Reconnaissance"
    SPOOFING = "Spoofing"
    BRUTE_FORCE = "Brute Force"
    WEB_BASED = "Web-based"


@dataclass(frozen=True)
class AttackProfile:
    """
    Profile specification for a synthetic attack behavior.
    """
    attack_id: str
    label_raw: str
    label_category: str
    protocol_name: str
    protocol_type: int
    packet_size_min: int
    packet_size_max: int
    rate_min: float
    rate_max: float
    default_window_size: int
    tcp_flags: Dict[str, Any] = field(default_factory=dict)
    application_masks: Dict[str, int] = field(default_factory=dict)
    description: str = ""

    def __post_init__(self) -> None:
        """Validate attack profile attributes."""
        if not self.attack_id or not isinstance(self.attack_id, str):
            raise ValueError("attack_id must be a non-empty string.")
        if not self.label_raw or not isinstance(self.label_raw, str):
            raise ValueError("label_raw must be a non-empty string.")
        if self.label_category not in [c.value for c in AttackCategory]:
            raise ValueError(f"label_category '{self.label_category}' must be one of {[c.value for c in AttackCategory]}")
        if self.packet_size_min > self.packet_size_max:
            raise ValueError(f"packet_size_min ({self.packet_size_min}) cannot exceed packet_size_max ({self.packet_size_max})")
        if self.rate_min > self.rate_max or self.rate_min <= 0:
            raise ValueError(f"Invalid rate bounds: [{self.rate_min}, {self.rate_max}]")


# ==============================================================================
# Complete Attack Catalog (All 33 CICIoT2023 Malicious Attack Classes)
# ==============================================================================

ATTACK_PROFILES: Dict[str, AttackProfile] = {
    # --------------------------------------------------------------------------
    # 1. DDoS Attacks (12 classes)
    # --------------------------------------------------------------------------
    "DDOS-SYN_FLOOD": AttackProfile(
        attack_id="ddos_syn_flood",
        label_raw="DDOS-SYN_FLOOD",
        label_category=AttackCategory.DDOS.value,
        protocol_name="TCP",
        protocol_type=6,
        packet_size_min=60,
        packet_size_max=64,
        rate_min=10000.0,
        rate_max=50000.0,
        default_window_size=100,
        tcp_flags={"syn_ratio": 1.0, "ack_ratio": 0.0, "rst_ratio": 0.0, "fin_ratio": 0.0, "psh_ratio": 0.0},
        application_masks={"TCP": 1, "UDP": 0, "IPv": 1, "LLC": 1},
        description="Distributed SYN flooding targeting connection state exhaustion."
    ),
    "DDOS-TCP_FLOOD": AttackProfile(
        attack_id="ddos_tcp_flood",
        label_raw="DDOS-TCP_FLOOD",
        label_category=AttackCategory.DDOS.value,
        protocol_name="TCP",
        protocol_type=6,
        packet_size_min=60,
        packet_size_max=128,
        rate_min=10000.0,
        rate_max=45000.0,
        default_window_size=100,
        tcp_flags={"syn_ratio": 0.5, "ack_ratio": 0.5, "rst_ratio": 0.0, "fin_ratio": 0.0, "psh_ratio": 0.2},
        application_masks={"TCP": 1, "UDP": 0, "IPv": 1, "LLC": 1},
        description="High-rate generic TCP packet flood."
    ),
    "DDOS-UDP_FLOOD": AttackProfile(
        attack_id="ddos_udp_flood",
        label_raw="DDOS-UDP_FLOOD",
        label_category=AttackCategory.DDOS.value,
        protocol_name="UDP",
        protocol_type=17,
        packet_size_min=60,
        packet_size_max=512,
        rate_min=15000.0,
        rate_max=60000.0,
        default_window_size=100,
        tcp_flags={},
        application_masks={"TCP": 0, "UDP": 1, "IPv": 1, "LLC": 1},
        description="Distributed high-volume UDP datagram flood."
    ),
    "DDOS-ICMP_FLOOD": AttackProfile(
        attack_id="ddos_icmp_flood",
        label_raw="DDOS-ICMP_FLOOD",
        label_category=AttackCategory.DDOS.value,
        protocol_name="ICMP",
        protocol_type=1,
        packet_size_min=60,
        packet_size_max=128,
        rate_min=15000.0,
        rate_max=60000.0,
        default_window_size=100,
        tcp_flags={},
        application_masks={"TCP": 0, "UDP": 0, "ICMP": 1, "IPv": 1, "LLC": 1},
        description="Massive ICMP Echo Request flood saturating host processing."
    ),
    "DDOS-RSTFINFLOOD": AttackProfile(
        attack_id="ddos_rstfinflood",
        label_raw="DDOS-RSTFINFLOOD",
        label_category=AttackCategory.DDOS.value,
        protocol_name="TCP",
        protocol_type=6,
        packet_size_min=60,
        packet_size_max=64,
        rate_min=10000.0,
        rate_max=45000.0,
        default_window_size=100,
        tcp_flags={"syn_ratio": 0.0, "ack_ratio": 0.0, "rst_ratio": 0.5, "fin_ratio": 0.5, "psh_ratio": 0.0},
        application_masks={"TCP": 1, "UDP": 0, "IPv": 1, "LLC": 1},
        description="Simultaneous RST and FIN flag flood tearing down active states."
    ),
    "DDOS-PSHACK_FLOOD": AttackProfile(
        attack_id="ddos_pshack_flood",
        label_raw="DDOS-PSHACK_FLOOD",
        label_category=AttackCategory.DDOS.value,
        protocol_name="TCP",
        protocol_type=6,
        packet_size_min=64,
        packet_size_max=512,
        rate_min=10000.0,
        rate_max=45000.0,
        default_window_size=100,
        tcp_flags={"syn_ratio": 0.0, "ack_ratio": 1.0, "rst_ratio": 0.0, "fin_ratio": 0.0, "psh_ratio": 1.0},
        application_masks={"TCP": 1, "UDP": 0, "IPv": 1, "LLC": 1},
        description="High-rate PSH-ACK flood forcing kernel buffer processing."
    ),
    "DDOS-SYNONYMOUSIP_FLOOD": AttackProfile(
        attack_id="ddos_synonymousip_flood",
        label_raw="DDOS-SYNONYMOUSIP_FLOOD",
        label_category=AttackCategory.DDOS.value,
        protocol_name="TCP",
        protocol_type=6,
        packet_size_min=60,
        packet_size_max=64,
        rate_min=10000.0,
        rate_max=40000.0,
        default_window_size=100,
        tcp_flags={"syn_ratio": 0.9, "ack_ratio": 0.1, "rst_ratio": 0.0, "fin_ratio": 0.0, "psh_ratio": 0.0},
        application_masks={"TCP": 1, "UDP": 0, "IPv": 1, "LLC": 1},
        description="LAND-like attack with identical source/destination parameters."
    ),
    "DDOS-ICMP_FRAGMENTATION": AttackProfile(
        attack_id="ddos_icmp_fragmentation",
        label_raw="DDOS-ICMP_FRAGMENTATION",
        label_category=AttackCategory.DDOS.value,
        protocol_name="ICMP",
        protocol_type=1,
        packet_size_min=28,
        packet_size_max=512,
        rate_min=5000.0,
        rate_max=25000.0,
        default_window_size=100,
        tcp_flags={},
        application_masks={"TCP": 0, "UDP": 0, "ICMP": 1, "IPv": 1, "LLC": 1},
        description="Fragmented ICMP flood exhausting reassembly memory."
    ),
    "DDOS-ACK_FRAGMENTATION": AttackProfile(
        attack_id="ddos_ack_fragmentation",
        label_raw="DDOS-ACK_FRAGMENTATION",
        label_category=AttackCategory.DDOS.value,
        protocol_name="TCP",
        protocol_type=6,
        packet_size_min=40,
        packet_size_max=512,
        rate_min=5000.0,
        rate_max=25000.0,
        default_window_size=100,
        tcp_flags={"syn_ratio": 0.0, "ack_ratio": 1.0, "rst_ratio": 0.0, "fin_ratio": 0.0, "psh_ratio": 0.0},
        application_masks={"TCP": 1, "UDP": 0, "IPv": 1, "LLC": 1},
        description="Fragmented TCP ACK flood disrupting IP reassembly."
    ),
    "DDOS-UDP_FRAGMENTATION": AttackProfile(
        attack_id="ddos_udp_fragmentation",
        label_raw="DDOS-UDP_FRAGMENTATION",
        label_category=AttackCategory.DDOS.value,
        protocol_name="UDP",
        protocol_type=17,
        packet_size_min=28,
        packet_size_max=512,
        rate_min=5000.0,
        rate_max=25000.0,
        default_window_size=100,
        tcp_flags={},
        application_masks={"TCP": 0, "UDP": 1, "IPv": 1, "LLC": 1},
        description="Fragmented UDP packet flood."
    ),
    "DDOS-SLOWLORIS": AttackProfile(
        attack_id="ddos_slowloris",
        label_raw="DDOS-SLOWLORIS",
        label_category=AttackCategory.DDOS.value,
        protocol_name="TCP",
        protocol_type=6,
        packet_size_min=64,
        packet_size_max=256,
        rate_min=10.0,
        rate_max=100.0,
        default_window_size=50,
        tcp_flags={"syn_ratio": 0.05, "ack_ratio": 0.95, "rst_ratio": 0.0, "fin_ratio": 0.0, "psh_ratio": 0.3},
        application_masks={"TCP": 1, "UDP": 0, "HTTP": 1, "IPv": 1, "LLC": 1},
        description="Slow-rate HTTP connection exhaustion holding sockets open."
    ),
    "DDOS-HTTP_FLOOD": AttackProfile(
        attack_id="ddos_http_flood",
        label_raw="DDOS-HTTP_FLOOD",
        label_category=AttackCategory.DDOS.value,
        protocol_name="TCP",
        protocol_type=6,
        packet_size_min=64,
        packet_size_max=1024,
        rate_min=2000.0,
        rate_max=15000.0,
        default_window_size=100,
        tcp_flags={"syn_ratio": 0.05, "ack_ratio": 0.95, "rst_ratio": 0.0, "fin_ratio": 0.0, "psh_ratio": 0.4},
        application_masks={"TCP": 1, "UDP": 0, "HTTP": 1, "IPv": 1, "LLC": 1},
        description="Volumetric HTTP GET/POST request flood."
    ),

    # --------------------------------------------------------------------------
    # 2. DoS Attacks (Single source floods) (4 classes)
    # --------------------------------------------------------------------------
    "DOS-SYN_FLOOD": AttackProfile(
        attack_id="dos_syn_flood",
        label_raw="DOS-SYN_FLOOD",
        label_category=AttackCategory.DOS.value,
        protocol_name="TCP",
        protocol_type=6,
        packet_size_min=60,
        packet_size_max=64,
        rate_min=5000.0,
        rate_max=30000.0,
        default_window_size=100,
        tcp_flags={"syn_ratio": 1.0, "ack_ratio": 0.0, "rst_ratio": 0.0, "fin_ratio": 0.0, "psh_ratio": 0.0},
        application_masks={"TCP": 1, "UDP": 0, "IPv": 1, "LLC": 1},
        description="Single-source TCP SYN flooding targeting connection queues."
    ),
    "DOS-TCP_FLOOD": AttackProfile(
        attack_id="dos_tcp_flood",
        label_raw="DOS-TCP_FLOOD",
        label_category=AttackCategory.DOS.value,
        protocol_name="TCP",
        protocol_type=6,
        packet_size_min=60,
        packet_size_max=128,
        rate_min=5000.0,
        rate_max=30000.0,
        default_window_size=100,
        tcp_flags={"syn_ratio": 0.5, "ack_ratio": 0.5, "rst_ratio": 0.0, "fin_ratio": 0.0, "psh_ratio": 0.2},
        application_masks={"TCP": 1, "UDP": 0, "IPv": 1, "LLC": 1},
        description="Single-source elevated TCP packet transmission."
    ),
    "DOS-UDP_FLOOD": AttackProfile(
        attack_id="dos_udp_flood",
        label_raw="DOS-UDP_FLOOD",
        label_category=AttackCategory.DOS.value,
        protocol_name="UDP",
        protocol_type=17,
        packet_size_min=60,
        packet_size_max=512,
        rate_min=8000.0,
        rate_max=35000.0,
        default_window_size=100,
        tcp_flags={},
        application_masks={"TCP": 0, "UDP": 1, "IPv": 1, "LLC": 1},
        description="Single-source UDP packet flood saturating target ingress."
    ),
    "DOS-HTTP_FLOOD": AttackProfile(
        attack_id="dos_http_flood",
        label_raw="DOS-HTTP_FLOOD",
        label_category=AttackCategory.DOS.value,
        protocol_name="TCP",
        protocol_type=6,
        packet_size_min=64,
        packet_size_max=1024,
        rate_min=1000.0,
        rate_max=8000.0,
        default_window_size=100,
        tcp_flags={"syn_ratio": 0.05, "ack_ratio": 0.95, "rst_ratio": 0.0, "fin_ratio": 0.0, "psh_ratio": 0.4},
        application_masks={"TCP": 1, "UDP": 0, "HTTP": 1, "IPv": 1, "LLC": 1},
        description="Single-source high-frequency HTTP requests."
    ),

    # --------------------------------------------------------------------------
    # 3. Mirai Botnet Attacks (3 classes)
    # --------------------------------------------------------------------------
    "MIRAI-GREETH_FLOOD": AttackProfile(
        attack_id="mirai_greeth_flood",
        label_raw="MIRAI-GREETH_FLOOD",
        label_category=AttackCategory.MIRAI.value,
        protocol_name="GRE",
        protocol_type=47,
        packet_size_min=128,
        packet_size_max=1024,
        rate_min=3000.0,
        rate_max=15000.0,
        default_window_size=100,
        tcp_flags={},
        application_masks={"TCP": 0, "UDP": 0, "IPv": 1, "LLC": 1},
        description="Mirai botnet GRE Ethernet tunneling flood."
    ),
    "MIRAI-GREIP_FLOOD": AttackProfile(
        attack_id="mirai_greip_flood",
        label_raw="MIRAI-GREIP_FLOOD",
        label_category=AttackCategory.MIRAI.value,
        protocol_name="GRE",
        protocol_type=47,
        packet_size_min=128,
        packet_size_max=1024,
        rate_min=3000.0,
        rate_max=15000.0,
        default_window_size=100,
        tcp_flags={},
        application_masks={"TCP": 0, "UDP": 0, "IPv": 1, "LLC": 1},
        description="Mirai botnet GRE IP protocol tunneling flood."
    ),
    "MIRAI-UDPPLAIN": AttackProfile(
        attack_id="mirai_udpplain",
        label_raw="MIRAI-UDPPLAIN",
        label_category=AttackCategory.MIRAI.value,
        protocol_name="UDP",
        protocol_type=17,
        packet_size_min=128,
        packet_size_max=1460,
        rate_min=5000.0,
        rate_max=30000.0,
        default_window_size=100,
        tcp_flags={},
        application_masks={"TCP": 0, "UDP": 1, "IPv": 1, "LLC": 1},
        description="Mirai botnet high-bandwidth raw UDP payload flood."
    ),

    # --------------------------------------------------------------------------
    # 4. Reconnaissance Attacks (5 classes)
    # --------------------------------------------------------------------------
    "RECON-PORTSCAN": AttackProfile(
        attack_id="recon_portscan",
        label_raw="RECON-PORTSCAN",
        label_category=AttackCategory.RECONNAISSANCE.value,
        protocol_name="TCP",
        protocol_type=6,
        packet_size_min=60,
        packet_size_max=80,
        rate_min=100.0,
        rate_max=1500.0,
        default_window_size=10,
        tcp_flags={"syn_ratio": 0.8, "ack_ratio": 0.2, "rst_ratio": 0.0, "fin_ratio": 0.0, "psh_ratio": 0.0},
        application_masks={"TCP": 1, "UDP": 0, "IPv": 1, "LLC": 1},
        description="Probing consecutive target ports with TCP SYN probes."
    ),
    "RECON-HOSTDISCOVERY": AttackProfile(
        attack_id="recon_hostdiscovery",
        label_raw="RECON-HOSTDISCOVERY",
        label_category=AttackCategory.RECONNAISSANCE.value,
        protocol_name="ICMP",
        protocol_type=1,
        packet_size_min=60,
        packet_size_max=100,
        rate_min=50.0,
        rate_max=800.0,
        default_window_size=10,
        tcp_flags={},
        application_masks={"TCP": 0, "UDP": 0, "ICMP": 1, "IPv": 1, "LLC": 1},
        description="Network range host discovery using ICMP echo requests."
    ),
    "RECON-OSSCAN": AttackProfile(
        attack_id="recon_osscan",
        label_raw="RECON-OSSCAN",
        label_category=AttackCategory.RECONNAISSANCE.value,
        protocol_name="TCP",
        protocol_type=6,
        packet_size_min=60,
        packet_size_max=128,
        rate_min=50.0,
        rate_max=600.0,
        default_window_size=10,
        tcp_flags={"syn_ratio": 0.5, "ack_ratio": 0.3, "rst_ratio": 0.2, "fin_ratio": 0.0, "psh_ratio": 0.0},
        application_masks={"TCP": 1, "UDP": 0, "IPv": 1, "LLC": 1},
        description="Probing TCP/IP stack fingerprints with varied flag combinations."
    ),
    "RECON-PINGSWEEP": AttackProfile(
        attack_id="recon_pingsweep",
        label_raw="RECON-PINGSWEEP",
        label_category=AttackCategory.RECONNAISSANCE.value,
        protocol_name="ICMP",
        protocol_type=1,
        packet_size_min=60,
        packet_size_max=84,
        rate_min=20.0,
        rate_max=400.0,
        default_window_size=10,
        tcp_flags={},
        application_masks={"TCP": 0, "UDP": 0, "ICMP": 1, "IPv": 1, "LLC": 1},
        description="Sequential ICMP ping sweeps across local subnet."
    ),
    "VULNERABILITYSCAN": AttackProfile(
        attack_id="vulnerabilityscan",
        label_raw="VULNERABILITYSCAN",
        label_category=AttackCategory.RECONNAISSANCE.value,
        protocol_name="TCP",
        protocol_type=6,
        packet_size_min=64,
        packet_size_max=512,
        rate_min=100.0,
        rate_max=1200.0,
        default_window_size=10,
        tcp_flags={"syn_ratio": 0.1, "ack_ratio": 0.9, "rst_ratio": 0.0, "fin_ratio": 0.0, "psh_ratio": 0.4},
        application_masks={"TCP": 1, "UDP": 0, "HTTP": 1, "IPv": 1, "LLC": 1},
        description="Automated scanning targeting known service vulnerabilities."
    ),

    # --------------------------------------------------------------------------
    # 5. Spoofing Attacks (2 classes)
    # --------------------------------------------------------------------------
    "DNS_SPOOFING": AttackProfile(
        attack_id="dns_spoofing",
        label_raw="DNS_SPOOFING",
        label_category=AttackCategory.SPOOFING.value,
        protocol_name="UDP",
        protocol_type=17,
        packet_size_min=80,
        packet_size_max=512,
        rate_min=100.0,
        rate_max=1500.0,
        default_window_size=10,
        tcp_flags={},
        application_masks={"TCP": 0, "UDP": 1, "DNS": 1, "IPv": 1, "LLC": 1},
        description="Forged DNS response injection directing IoT queries to attacker."
    ),
    "MITM-ARPSPOOFING": AttackProfile(
        attack_id="mitm_arpspoofing",
        label_raw="MITM-ARPSPOOFING",
        label_category=AttackCategory.SPOOFING.value,
        protocol_name="UDP",  # Transport indicator abstraction for L2 ARP poison frames
        protocol_type=17,
        packet_size_min=42,
        packet_size_max=64,
        rate_min=50.0,
        rate_max=800.0,
        default_window_size=10,
        tcp_flags={},
        application_masks={"TCP": 0, "UDP": 1, "ARP": 1, "IPv": 1, "LLC": 1},
        description="Gratuitous ARP cache poisoning redirecting gateway traffic."
    ),

    # --------------------------------------------------------------------------
    # 6. Brute Force Attacks (1 class)
    # --------------------------------------------------------------------------
    "DICTIONARYBRUTEFORCE": AttackProfile(
        attack_id="dictionarybruteforce",
        label_raw="DICTIONARYBRUTEFORCE",
        label_category=AttackCategory.BRUTE_FORCE.value,
        protocol_name="TCP",
        protocol_type=6,
        packet_size_min=64,
        packet_size_max=384,
        rate_min=50.0,
        rate_max=800.0,
        default_window_size=10,
        tcp_flags={"syn_ratio": 0.05, "ack_ratio": 0.95, "rst_ratio": 0.0, "fin_ratio": 0.0, "psh_ratio": 0.3},
        application_masks={"TCP": 1, "UDP": 0, "SSH": 1, "IPv": 1, "LLC": 1},
        description="Automated credential guessing over Telnet/SSH/HTTP authentication."
    ),

    # --------------------------------------------------------------------------
    # 7. Web-based Attacks (6 classes)
    # --------------------------------------------------------------------------
    "COMMANDINJECTION": AttackProfile(
        attack_id="commandinjection",
        label_raw="COMMANDINJECTION",
        label_category=AttackCategory.WEB_BASED.value,
        protocol_name="TCP",
        protocol_type=6,
        packet_size_min=80,
        packet_size_max=1024,
        rate_min=20.0,
        rate_max=400.0,
        default_window_size=10,
        tcp_flags={"syn_ratio": 0.05, "ack_ratio": 0.95, "rst_ratio": 0.0, "fin_ratio": 0.0, "psh_ratio": 0.4},
        application_masks={"TCP": 1, "UDP": 0, "HTTP": 1, "IPv": 1, "LLC": 1},
        description="OS command injection payload via vulnerable IoT web parameters."
    ),
    "SQLINJECTION": AttackProfile(
        attack_id="sqlinjection",
        label_raw="SQLINJECTION",
        label_category=AttackCategory.WEB_BASED.value,
        protocol_name="TCP",
        protocol_type=6,
        packet_size_min=80,
        packet_size_max=1024,
        rate_min=20.0,
        rate_max=400.0,
        default_window_size=10,
        tcp_flags={"syn_ratio": 0.05, "ack_ratio": 0.95, "rst_ratio": 0.0, "fin_ratio": 0.0, "psh_ratio": 0.4},
        application_masks={"TCP": 1, "UDP": 0, "HTTP": 1, "IPv": 1, "LLC": 1},
        description="SQL injection probes against embedded IoT database backends."
    ),
    "XSS": AttackProfile(
        attack_id="xss",
        label_raw="XSS",
        label_category=AttackCategory.WEB_BASED.value,
        protocol_name="TCP",
        protocol_type=6,
        packet_size_min=80,
        packet_size_max=800,
        rate_min=20.0,
        rate_max=400.0,
        default_window_size=10,
        tcp_flags={"syn_ratio": 0.05, "ack_ratio": 0.95, "rst_ratio": 0.0, "fin_ratio": 0.0, "psh_ratio": 0.3},
        application_masks={"TCP": 1, "UDP": 0, "HTTP": 1, "IPv": 1, "LLC": 1},
        description="Cross-site scripting payload injection into device web UI."
    ),
    "BROWSERHIJACKING": AttackProfile(
        attack_id="browserhijacking",
        label_raw="BROWSERHIJACKING",
        label_category=AttackCategory.WEB_BASED.value,
        protocol_name="TCP",
        protocol_type=6,
        packet_size_min=80,
        packet_size_max=800,
        rate_min=20.0,
        rate_max=400.0,
        default_window_size=10,
        tcp_flags={"syn_ratio": 0.05, "ack_ratio": 0.95, "rst_ratio": 0.0, "fin_ratio": 0.0, "psh_ratio": 0.3},
        application_masks={"TCP": 1, "UDP": 0, "HTTP": 1, "IPv": 1, "LLC": 1},
        description="Malicious redirection of management portal traffic."
    ),
    "BACKDOOR_MALWARE": AttackProfile(
        attack_id="backdoor_malware",
        label_raw="BACKDOOR_MALWARE",
        label_category=AttackCategory.WEB_BASED.value,
        protocol_name="TCP",
        protocol_type=6,
        packet_size_min=64,
        packet_size_max=1200,
        rate_min=10.0,
        rate_max=500.0,
        default_window_size=10,
        tcp_flags={"syn_ratio": 0.1, "ack_ratio": 0.9, "rst_ratio": 0.0, "fin_ratio": 0.0, "psh_ratio": 0.5},
        application_masks={"TCP": 1, "UDP": 0, "HTTP": 1, "IPv": 1, "LLC": 1},
        description="Post-exploitation backdoor communications to external C2."
    ),
    "UPLOADING_ATTACK": AttackProfile(
        attack_id="uploading_attack",
        label_raw="UPLOADING_ATTACK",
        label_category=AttackCategory.WEB_BASED.value,
        protocol_name="TCP",
        protocol_type=6,
        packet_size_min=128,
        packet_size_max=1460,
        rate_min=50.0,
        rate_max=1000.0,
        default_window_size=10,
        tcp_flags={"syn_ratio": 0.05, "ack_ratio": 0.95, "rst_ratio": 0.0, "fin_ratio": 0.0, "psh_ratio": 0.6},
        application_masks={"TCP": 1, "UDP": 0, "HTTP": 1, "IPv": 1, "LLC": 1},
        description="Unrestricted file upload of malicious firmware / shell scripts."
    ),
}


# ==============================================================================
# Helper Lookup Functions
# ==============================================================================

def get_attack_profile(key: str) -> AttackProfile:
    """
    Retrieve an AttackProfile by raw label or attack_id (case-insensitive).
    Raises KeyError if not found.
    """
    clean = str(key).strip().upper()
    if clean in ATTACK_PROFILES:
        return ATTACK_PROFILES[clean]

    # Try matching by attack_id
    clean_id = str(key).strip().lower()
    for profile in ATTACK_PROFILES.values():
        if profile.attack_id.lower() == clean_id:
            return profile

    raise KeyError(
        f"Unknown attack identifier '{key}'. "
        f"Available raw labels: {sorted(list(ATTACK_PROFILES.keys()))}"
    )


def list_attack_profiles() -> List[AttackProfile]:
    """Return all defined attack profiles."""
    return list(ATTACK_PROFILES.values())


def list_attacks_by_category(category: str) -> List[AttackProfile]:
    """Filter attack profiles by macro attack category (case-insensitive)."""
    clean_cat = str(category).strip().lower()
    return [
        p for p in ATTACK_PROFILES.values()
        if p.label_category.lower() == clean_cat
    ]


def get_raw_labels_for_category(category: str) -> List[str]:
    """Return raw attack labels belonging to a specific macro category."""
    return [p.label_raw for p in list_attacks_by_category(category)]
