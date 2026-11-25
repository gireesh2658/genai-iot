"""
Curated capture manifest for genuine MAC-attributed CICIoT2023 PCAPNG extraction.

Covers all 8 macro categories (Benign, DDoS, DoS, Mirai, Reconnaissance, Spoofing,
Brute Force, Web-based) across multiple shards per attack category so diverse
physical IoT victim hardware (Audio, Camera, Home Automation, Hub, Lighting,
Power Outlet, NextGen) is represented authentically.
"""

from __future__ import annotations

from typing import List

from synthetic_engine.pcap_device_extractor import CaptureSpec


HF_BASE_URL = "https://huggingface.co/datasets/somnath0100/CICIoT2023Small/resolve/main"

# Window sizes match CICIoT2023 sensors-23-05941 aggregation cadence:
# - W=10 for Benign, Web-based, Brute Force, Reconnaissance, Spoofing
# - W=50 for SlowLoris / HTTP floods
# - W=100 for volumetric DDoS / DoS / Mirai floods
CAPTURE_SPECS: List[CaptureSpec] = [
    # 1. Benign (4 captures, 36 MB each)
    CaptureSpec("benign_0", "PCAPS/Benign_Final/BenignTraffic.pcap", "Benign/BenignTraffic.pcap", "BENIGN", "Benign", 0, 10, 36_000_000, max_windows_per_device=180),
    CaptureSpec("benign_1", "PCAPS/Benign_Final/BenignTraffic1.pcap", "Benign/BenignTraffic1.pcap", "BENIGN", "Benign", 0, 10, 36_000_000, max_windows_per_device=180),
    CaptureSpec("benign_2", "PCAPS/Benign_Final/BenignTraffic2.pcap", "Benign/BenignTraffic2.pcap", "BENIGN", "Benign", 0, 10, 36_000_000, max_windows_per_device=180),
    CaptureSpec("benign_3", "PCAPS/Benign_Final/BenignTraffic3.pcap", "Benign/BenignTraffic3.pcap", "BENIGN", "Benign", 0, 10, 36_000_000, max_windows_per_device=180),

    # 2. Web-based (100% complete PCAP files)
    CaptureSpec("web_backdoor", "PCAPS/Backdoor_Malware/Backdoor_Malware.pcap", "Web/Backdoor_Malware.pcap", "BACKDOOR_MALWARE", "Web-based", 1, 10, None),
    CaptureSpec("web_xss", "PCAPS/XSS/XSS.pcap", "Web/XSS.pcap", "XSS", "Web-based", 1, 10, None),
    CaptureSpec("web_sqli", "PCAPS/SqlInjection/SqlInjection.pcap", "Web/SqlInjection.pcap", "SQLINJECTION", "Web-based", 1, 10, None),
    CaptureSpec("web_cmdinj", "PCAPS/CommandInjection/CommandInjection.pcap", "Web/CommandInjection.pcap", "COMMANDINJECTION", "Web-based", 1, 10, None),
    CaptureSpec("web_hijack", "PCAPS/BrowserHijacking/BrowserHijacking.pcap", "Web/BrowserHijacking.pcap", "BROWSERHIJACKING", "Web-based", 1, 10, None),

    # 3. Brute Force (100% complete file)
    CaptureSpec("bf_dict", "PCAPS/DictionaryBruteForce/DictionaryBruteForce.pcap", "BruteForce/DictionaryBruteForce.pcap", "DICTIONARYBRUTEFORCE", "Brute Force", 1, 10, None, max_windows_per_device=150),

    # 4. Reconnaissance (PingSweep 100% complete + 24 MB slices of remaining 4 subclasses)
    CaptureSpec("recon_ping", "PCAPS/Recon-PingSweep/Recon-PingSweep.pcap", "Recon/Recon-PingSweep.pcap", "RECON-PINGSWEEP", "Reconnaissance", 1, 10, None),
    CaptureSpec("recon_port", "PCAPS/Recon-PortScan/Recon-PortScan.pcap", "Recon/Recon-PortScan.pcap", "RECON-PORTSCAN", "Reconnaissance", 1, 10, 24_000_000, max_windows_per_device=120),
    CaptureSpec("recon_os", "PCAPS/Recon-OSScan/Recon-OSScan.pcap", "Recon/Recon-OSScan.pcap", "RECON-OSSCAN", "Reconnaissance", 1, 10, 24_000_000, max_windows_per_device=120),
    CaptureSpec("recon_host", "PCAPS/Recon-HostDiscovery/Recon-HostDiscovery.pcap", "Recon/Recon-HostDiscovery.pcap", "RECON-HOSTDISCOVERY", "Reconnaissance", 1, 10, 24_000_000, max_windows_per_device=120),
    CaptureSpec("recon_vuln", "PCAPS/VulnerabilityScan/VulnerabilityScan.pcap", "Recon/VulnerabilityScan.pcap", "VULNERABILITYSCAN", "Reconnaissance", 1, 10, 24_000_000, max_windows_per_device=120),

    # 5. Spoofing (both Spoofing attack subclasses)
    CaptureSpec("spoof_dns", "PCAPS/DNS_Spoofing/DNS_Spoofing.pcap", "Spoofing/DNS_Spoofing.pcap", "DNS_SPOOFING", "Spoofing", 1, 10, 32_000_000, max_windows_per_device=150),
    CaptureSpec("spoof_arp", "PCAPS/MITM-ArpSpoofing/MITM-ArpSpoofing.pcap", "Spoofing/MITM-ArpSpoofing.pcap", "MITM-ARPSPOOFING", "Spoofing", 1, 10, 32_000_000, max_windows_per_device=150),

    # 6. DoS (all 4 DoS subclasses across Audio, Camera, Hub, NextGen victim shards)
    CaptureSpec("dos_syn_audio", "PCAPS/DoS-SYN_Flood/DoS-SYN_Flood.pcap", "DoS/DoS-SYN_Flood.pcap", "DOS-SYN_FLOOD", "DoS", 1, 100, 12_000_000),
    CaptureSpec("dos_syn_cam", "PCAPS/DoS-SYN_Flood/DoS-SYN_Flood2.pcap", "DoS/DoS-SYN_Flood2.pcap", "DOS-SYN_FLOOD", "DoS", 1, 100, 12_000_000),
    CaptureSpec("dos_tcp_hub", "PCAPS/DoS-TCP_Flood/DoS-TCP_Flood10.pcap", "DoS/DoS-TCP_Flood10.pcap", "DOS-TCP_FLOOD", "DoS", 1, 100, 12_000_000),
    CaptureSpec("dos_tcp_audio", "PCAPS/DoS-TCP_Flood/DoS-TCP_Flood.pcap", "DoS/DoS-TCP_Flood.pcap", "DOS-TCP_FLOOD", "DoS", 1, 100, 12_000_000),
    CaptureSpec("dos_udp_cam", "PCAPS/DoS-UDP_Flood/DoS-UDP_Flood.pcap", "DoS/DoS-UDP_Flood.pcap", "DOS-UDP_FLOOD", "DoS", 1, 100, 12_000_000),
    CaptureSpec("dos_udp_audio", "PCAPS/DoS-UDP_Flood/DoS-UDP_Flood2.pcap", "DoS/DoS-UDP_Flood2.pcap", "DOS-UDP_FLOOD", "DoS", 1, 100, 12_000_000),
    CaptureSpec("dos_http_0", "PCAPS/DoS-HTTP_Flood/DoS-HTTP_Flood.pcap", "DoS/DoS-HTTP_Flood.pcap", "DOS-HTTP_FLOOD", "DoS", 1, 50, 16_000_000),
    CaptureSpec("dos_http_1", "PCAPS/DoS-HTTP_Flood/DoS-HTTP_Flood1.pcap", "DoS/DoS-HTTP_Flood1.pcap", "DOS-HTTP_FLOOD", "DoS", 1, 50, 16_000_000),

    # 7. Mirai (all 3 Mirai subclasses across Audio, Camera, Hub victim shards)
    CaptureSpec("mirai_greeth_0", "PCAPS/Mirai-greeth_flood/Mirai-greeth_flood.pcap", "Mirai/Mirai-greeth_flood.pcap", "MIRAI-GREETH_FLOOD", "Mirai", 1, 100, 16_000_000),
    CaptureSpec("mirai_greeth_4", "PCAPS/Mirai-greeth_flood/Mirai-greeth_flood4.pcap", "Mirai/Mirai-greeth_flood4.pcap", "MIRAI-GREETH_FLOOD", "Mirai", 1, 100, 12_000_000),
    CaptureSpec("mirai_greip_21", "PCAPS/Mirai-greip_flood/Mirai-greip_flood21.pcap", "Mirai/Mirai-greip_flood21.pcap", "MIRAI-GREIP_FLOOD", "Mirai", 1, 100, 12_000_000),
    CaptureSpec("mirai_greip_0", "PCAPS/Mirai-greip_flood/Mirai-greip_flood.pcap", "Mirai/Mirai-greip_flood.pcap", "MIRAI-GREIP_FLOOD", "Mirai", 1, 100, 12_000_000),
    CaptureSpec("mirai_udp_24", "PCAPS/Mirai-udpplain/Mirai-udpplain24.pcap", "Mirai/Mirai-udpplain24.pcap", "MIRAI-UDPPLAIN", "Mirai", 1, 100, 12_000_000),
    CaptureSpec("mirai_udp_2", "PCAPS/Mirai-udpplain/Mirai-udpplain2.pcap", "Mirai/Mirai-udpplain2.pcap", "MIRAI-UDPPLAIN", "Mirai", 1, 100, 12_000_000),

    # 8. DDoS (all 12 DDoS subclasses spanning Audio, Camera, Power Outlet, Home Automation, Hub)
    CaptureSpec("ddos_syn_audio", "PCAPS/DDoS-SYN_Flood/DDoS-SYN_Flood.pcap", "DDoS/DDoS-SYN_Flood.pcap", "DDOS-SYN_FLOOD", "DDoS", 1, 100, 10_000_000),
    CaptureSpec("ddos_syn_cam", "PCAPS/DDoS-SYN_Flood/DDoS-SYN_Flood1.pcap", "DDoS/DDoS-SYN_Flood1.pcap", "DDOS-SYN_FLOOD", "DDoS", 1, 100, 10_000_000),
    CaptureSpec("ddos_syn_plug", "PCAPS/DDoS-SYN_Flood/DDoS-SYN_Flood4.pcap", "DDoS/DDoS-SYN_Flood4.pcap", "DDOS-SYN_FLOOD", "DDoS", 1, 100, 12_000_000),
    CaptureSpec("ddos_tcp_0", "PCAPS/DDoS-TCP_Flood/DDoS-TCP_Flood.pcap", "DDoS/DDoS-TCP_Flood.pcap", "DDOS-TCP_FLOOD", "DDoS", 1, 100, 10_000_000),
    CaptureSpec("ddos_tcp_1", "PCAPS/DDoS-TCP_Flood/DDoS-TCP_Flood1.pcap", "DDoS/DDoS-TCP_Flood1.pcap", "DDOS-TCP_FLOOD", "DDoS", 1, 100, 10_000_000),
    CaptureSpec("ddos_udp_0", "PCAPS/DDoS-UDP_Flood/DDoS-UDP_Flood.pcap", "DDoS/DDoS-UDP_Flood.pcap", "DDOS-UDP_FLOOD", "DDoS", 1, 100, 10_000_000),
    CaptureSpec("ddos_udp_5", "PCAPS/DDoS-UDP_Flood/DDoS-UDP_Flood5.pcap", "DDoS/DDoS-UDP_Flood5.pcap", "DDOS-UDP_FLOOD", "DDoS", 1, 100, 10_000_000),
    CaptureSpec("ddos_icmp_ha", "PCAPS/DDoS-ICMP_Flood/DDoS-ICMP_Flood16.pcap", "DDoS/DDoS-ICMP_Flood16.pcap", "DDOS-ICMP_FLOOD", "DDoS", 1, 100, 12_000_000),
    CaptureSpec("ddos_icmp_0", "PCAPS/DDoS-ICMP_Flood/DDoS-ICMP_Flood.pcap", "DDoS/DDoS-ICMP_Flood.pcap", "DDOS-ICMP_FLOOD", "DDoS", 1, 100, 10_000_000),
    CaptureSpec("ddos_pshack_1", "PCAPS/DDoS-PSHACK_Flood/DDoS-PSHACK_Flood1.pcap", "DDoS/DDoS-PSHACK_Flood1.pcap", "DDOS-PSHACK_FLOOD", "DDoS", 1, 100, 10_000_000),
    CaptureSpec("ddos_rstfin_0", "PCAPS/DDoS-RSTFINFlood/DDoS-RSTFINFlood.pcap", "DDoS/DDoS-RSTFINFlood.pcap", "DDOS-RSTFINFLOOD", "DDoS", 1, 100, 10_000_000),
    CaptureSpec("ddos_synip_0", "PCAPS/DDoS-SynonymousIP_Flood/DDoS-SynonymousIP_Flood.pcap", "DDoS/DDoS-SynonymousIP_Flood.pcap", "DDOS-SYNONYMOUSIP_FLOOD", "DDoS", 1, 100, 10_000_000),
    CaptureSpec("ddos_ackfrag_12", "PCAPS/DDoS-ACK_Fragmentation/DDoS-ACK_Fragmentation12.pcap", "DDoS/DDoS-ACK_Fragmentation12.pcap", "DDOS-ACK_FRAGMENTATION", "DDoS", 1, 100, 12_000_000),
    CaptureSpec("ddos_icmpfrag_0", "PCAPS/DDoS-ICMP_Fragmentation/DDoS-ICMP_Fragmentation.pcap", "DDoS/DDoS-ICMP_Fragmentation.pcap", "DDOS-ICMP_FRAGMENTATION", "DDoS", 1, 100, 12_000_000),
    CaptureSpec("ddos_udpfrag_12", "PCAPS/DDoS-UDP_Fragmentation/DDoS-UDP_Fragmentation12.pcap", "DDoS/DDoS-UDP_Fragmentation12.pcap", "DDOS-UDP_FRAGMENTATION", "DDoS", 1, 100, 12_000_000),
    CaptureSpec("ddos_slowloris", "PCAPS/DDoS-SlowLoris/DDoS-SlowLoris.pcap", "DDoS/DDoS-SlowLoris.pcap", "DDOS-SLOWLORIS", "DDoS", 1, 50, 16_000_000),
    CaptureSpec("ddos_http", "PCAPS/DDoS-HTTP_Flood/DDoS-HTTP_Flood-.pcap", "DDoS/DDoS-HTTP_Flood-.pcap", "DDOS-HTTP_FLOOD", "DDoS", 1, 50, 16_000_000),
]
