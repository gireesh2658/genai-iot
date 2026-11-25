"""
Deterministic PCAPNG Packet-Window Feature Extractor with Official Hardware Device Attribution.

Extracts 44 canonical schema columns (MODEL_INPUT_FEATURES + protocol_name + label_raw +
label_category + is_attack + device_id + device_category) plus provenance/role metadata
strictly from real CICIoT2023 PCAPNG packet captures using verified L2 MAC address
mappings from Neto et al. (2023), Sensors 23(13):5941 (PMC10346235 Table 1).

Privacy & Scientific Integrity:
- Never writes raw MAC addresses or IP addresses into output DataFrames/Parquet/CSVs.
- Excludes gateway/bridge/broadcast/multicast MACs from IoT device entities.
- Partitions each packet to at most one verified hardware device owner so no packet
  is ever duplicated across device streams or train/validation/test splits.
"""

from __future__ import annotations

import hashlib
import json
import struct
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from simulator.traffic_constraints import KNOWN_PROTOCOL_MAP
from simulator.traffic_schema import MODEL_INPUT_FEATURES


# Canonical protocol numbers matching CICIoT2023
PROTO_HOPOPT = 0
PROTO_ICMP = 1
PROTO_TCP = 6
PROTO_UDP = 17
PROTO_GRE = 47

SUPPORTED_CANONICAL_PROTOS = {PROTO_HOPOPT, PROTO_ICMP, PROTO_TCP, PROTO_UDP, PROTO_GRE}


@dataclass(frozen=True)
class CaptureSpec:
    """Metadata describing one PCAPNG capture file and its session-level label."""

    capture_id: str
    rel_url_path: str
    local_rel_path: str
    label_raw: str
    label_category: str
    is_attack: int
    window_size: int
    max_download_bytes: Optional[int]  # None => full file
    max_windows_per_device: Optional[int] = None


def load_mac_registry(registry_path: Path) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """Load verified physical MAC -> pseudonym registry JSON."""
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    mac_map = {entry["mac_address"].lower(): entry for entry in payload["devices"]}
    return mac_map, payload


def trim_to_pcapng_block_boundary(raw_bytes: bytes) -> bytes:
    """
    Truncate a streamed prefix of a PCAPNG file at the last complete valid block boundary
    so the saved file is 100% structurally valid PCAPNG.
    """
    n = len(raw_bytes)
    if n < 28:
        raise ValueError("Data too short to be valid PCAPNG.")
    btype0 = struct.unpack_from("<I", raw_bytes, 0)[0]
    if btype0 != 0x0A0D0D0A:
        raise ValueError(f"Expected PCAPNG SHB magic 0x0a0d0d0a, got {hex(btype0)}")
    endian_magic = struct.unpack_from("<I", raw_bytes, 8)[0]
    endian = "<" if endian_magic == 0x1A2B3C4D else ">"
    pos = 0
    while pos + 12 <= n:
        _bt, blen = struct.unpack_from(endian + "II", raw_bytes, pos)
        if blen < 12 or pos + blen > n:
            break
        pos += blen
    return raw_bytes[:pos]


def _parse_idb_ts_unit(pcap_bytes: bytes, endian: str) -> float:
    """Parse PCAPNG IDB if_tsresol option (code=9); defaults to 1e-6 seconds per spec."""
    n = len(pcap_bytes)
    pos = 0
    while pos + 12 <= n:
        btype, blen = struct.unpack_from(endian + "II", pcap_bytes, pos)
        if blen < 12 or pos + blen > n:
            break
        if btype == 0x00000001 and blen >= 20:
            opt_pos = pos + 16
            opt_end = pos + blen - 4
            while opt_pos + 4 <= opt_end:
                ocode, olen = struct.unpack_from(endian + "HH", pcap_bytes, opt_pos)
                opt_pos += 4
                if ocode == 0:
                    break
                if ocode == 9 and olen >= 1 and opt_pos < opt_end:
                    val = pcap_bytes[opt_pos]
                    if val & 0x80:
                        return float(2 ** (-(val & 0x7F)))
                    return float(10 ** (-val))
                opt_pos += (olen + 3) & ~3
            return 1e-6
        pos += blen
    return 1e-6


def _select_packet_owner(
    src_mac: str,
    dst_mac: str,
    mac_map: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Disjointly attribute an Ethernet frame to at most one verified Table-1 device.

    Priority when both endpoints are Table-1 devices:
    1. Victim non-NextGen hardware device over NextGen attacker node.
    2. Otherwise eth_src (transmitting endpoint).
    Gateway routers, virtual bridges, VM MACs, broadcast, and multicast are never returned.
    """
    src_info = mac_map.get(src_mac)
    dst_info = mac_map.get(dst_mac)
    if src_info is None and dst_info is None:
        return None
    if src_info is not None and dst_info is None:
        return src_info
    if dst_info is not None and src_info is None:
        return dst_info
    assert src_info is not None and dst_info is not None
    if src_info["testbed_role"] == "attacker" and dst_info["testbed_role"] == "victim":
        return dst_info
    if dst_info["testbed_role"] == "attacker" and src_info["testbed_role"] == "victim":
        return src_info
    return src_info


def _extract_packet_tuple(pkt: bytes, orig_len: int, ts_sec: float) -> Tuple[Any, ...]:
    """Extract lightweight L2/L3/L4 header attributes matching CICIoT2023 feature units."""
    cap_len = len(pkt)
    if cap_len < 14:
        return (ts_sec, orig_len, 0.0, PROTO_HOPOPT, 0.0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    ethertype = struct.unpack_from(">H", pkt, 12)[0]
    l3_off = 14
    if ethertype == 0x8100 and cap_len >= 18:  # 802.1Q VLAN
        ethertype = struct.unpack_from(">H", pkt, 16)[0]
        l3_off = 18

    is_arp = 1 if ethertype == 0x0806 else 0
    is_ipv = 1 if ethertype in (0x0800, 0x86DD) else 0
    is_llc = 1 if ethertype >= 0x0600 and is_arp == 0 else (1 if ethertype < 0x0600 else 0)

    hdr_len = 0.0
    ttl = 0.0
    ip_proto = PROTO_HOPOPT
    fin = syn = rst = psh = ack = ece = cwr = 0
    http = https = dns = telnet = smtp = ssh = irc = tcp_f = udp_f = dhcp = icmp_f = igmp_f = 0

    if ethertype == 0x0800 and cap_len >= l3_off + 20:  # IPv4
        ihl = (pkt[l3_off] & 0x0F) * 4
        if ihl < 20:
            ihl = 20
        ttl = float(pkt[l3_off + 8])
        raw_proto = int(pkt[l3_off + 9])
        l4_off = l3_off + ihl

        if raw_proto == 6:  # TCP
            ip_proto = PROTO_TCP
            tcp_f = 1
            if cap_len >= l4_off + 14:
                sport, dport = struct.unpack_from(">HH", pkt, l4_off)
                data_off = ((pkt[l4_off + 12] >> 4) & 0x0F) * 4
                hdr_len = float(max(20, min(60, data_off)))
                flags = pkt[l4_off + 13]
                fin = 1 if (flags & 0x01) else 0
                syn = 1 if (flags & 0x02) else 0
                rst = 1 if (flags & 0x04) else 0
                psh = 1 if (flags & 0x08) else 0
                ack = 1 if (flags & 0x10) else 0
                ece = 1 if (flags & 0x40) else 0
                cwr = 1 if (flags & 0x80) else 0
                ports = (sport, dport)
                if 80 in ports or 8080 in ports or 8008 in ports:
                    http = 1
                if 443 in ports or 8443 in ports:
                    https = 1
                if 53 in ports:
                    dns = 1
                if 23 in ports:
                    telnet = 1
                if 25 in ports or 587 in ports or 465 in ports:
                    smtp = 1
                if 22 in ports:
                    ssh = 1
                if 6667 in ports or 194 in ports:
                    irc = 1
            else:
                hdr_len = 20.0
        elif raw_proto == 17:  # UDP
            ip_proto = PROTO_UDP
            udp_f = 1
            hdr_len = 8.0
            if cap_len >= l4_off + 4:
                sport, dport = struct.unpack_from(">HH", pkt, l4_off)
                ports = (sport, dport)
                if 53 in ports or 5353 in ports:
                    dns = 1
                if 67 in ports or 68 in ports:
                    dhcp = 1
                if 80 in ports:
                    http = 1
                if 443 in ports:
                    https = 1
        elif raw_proto == 1:  # ICMP
            ip_proto = PROTO_ICMP
            icmp_f = 1
            hdr_len = 0.0
        elif raw_proto == 2:  # IGMP
            ip_proto = PROTO_HOPOPT
            igmp_f = 1
            hdr_len = 0.0
        elif raw_proto == 47:  # GRE
            ip_proto = PROTO_GRE
            hdr_len = 0.0
        else:
            ip_proto = PROTO_HOPOPT
            hdr_len = 0.0
    elif ethertype == 0x86DD and cap_len >= l3_off + 40:  # IPv6
        ttl = float(pkt[l3_off + 7])
        nxt = int(pkt[l3_off + 6])
        l4_off = l3_off + 40
        if nxt == 6:
            ip_proto = PROTO_TCP
            tcp_f = 1
            if cap_len >= l4_off + 14:
                sport, dport = struct.unpack_from(">HH", pkt, l4_off)
                data_off = ((pkt[l4_off + 12] >> 4) & 0x0F) * 4
                hdr_len = float(max(20, min(60, data_off)))
                flags = pkt[l4_off + 13]
                fin = 1 if (flags & 0x01) else 0
                syn = 1 if (flags & 0x02) else 0
                rst = 1 if (flags & 0x04) else 0
                psh = 1 if (flags & 0x08) else 0
                ack = 1 if (flags & 0x10) else 0
                ece = 1 if (flags & 0x40) else 0
                cwr = 1 if (flags & 0x80) else 0
                if 443 in (sport, dport):
                    https = 1
                if 80 in (sport, dport):
                    http = 1
                if 53 in (sport, dport) or 5353 in (sport, dport):
                    dns = 1
        elif nxt == 17:
            ip_proto = PROTO_UDP
            udp_f = 1
            hdr_len = 8.0
            if cap_len >= l4_off + 4:
                sport, dport = struct.unpack_from(">HH", pkt, l4_off)
                if 53 in (sport, dport) or 5353 in (sport, dport):
                    dns = 1
                if 546 in (sport, dport) or 547 in (sport, dport):
                    dhcp = 1
        elif nxt == 58:  # ICMPv6 -> map cleanly to ICMP indicator
            ip_proto = PROTO_ICMP
            icmp_f = 1

    return (
        ts_sec,
        float(orig_len),
        hdr_len,
        ip_proto,
        ttl,
        fin,
        syn,
        rst,
        psh,
        ack,
        ece,
        cwr,
        http,
        https,
        dns,
        telnet,
        smtp,
        ssh,
        irc,
        tcp_f,
        udp_f,
        dhcp,
        is_arp,
        icmp_f,
        igmp_f,
        is_ipv,
        is_llc,
    )


def extract_windows_from_pcapng(
    pcap_path: Path,
    spec: CaptureSpec,
    mac_map: Dict[str, Dict[str, Any]],
    min_window_packets: int = 5,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Parse one PCAPNG file into non-overlapping per-device sequential packet windows.
    Returns (list of feature dicts, extraction diagnostics).
    """
    data = pcap_path.read_bytes()
    n = len(data)
    if n < 28 or struct.unpack_from("<I", data, 0)[0] != 0x0A0D0D0A:
        raise ValueError(f"{pcap_path} is not a valid PCAPNG file.")
    endian = "<" if struct.unpack_from("<I", data, 8)[0] == 0x1A2B3C4D else ">"
    ts_unit = _parse_idb_ts_unit(data, endian)

    per_device_pkts: Dict[str, List[Tuple[Any, ...]]] = defaultdict(list)
    total_epbs = 0
    matched_epbs = 0
    pos = 0
    while pos + 12 <= n:
        btype, blen = struct.unpack_from(endian + "II", data, pos)
        if blen < 12 or pos + blen > n:
            break
        if btype == 0x00000006 and blen >= 32:
            total_epbs += 1
            ts_hi, ts_lo, cap_len, orig_len = struct.unpack_from(endian + "IIII", data, pos + 12)
            pkt_off = pos + 28
            if cap_len >= 14 and pkt_off + cap_len <= pos + blen - 4:
                pkt = data[pkt_off:pkt_off + cap_len]
                dst_mac = ":".join(f"{b:02x}" for b in pkt[0:6])
                src_mac = ":".join(f"{b:02x}" for b in pkt[6:12])
                owner = _select_packet_owner(src_mac, dst_mac, mac_map)
                if owner is not None:
                    matched_epbs += 1
                    ts_sec = ((ts_hi << 32) | ts_lo) * ts_unit
                    per_device_pkts[owner["device_id"]].append(_extract_packet_tuple(pkt, orig_len, ts_sec))
        pos += blen

    dev_lookup = {entry["device_id"]: entry for entry in mac_map.values()}
    rows: List[Dict[str, Any]] = []
    wsize = spec.window_size

    for dev_id in sorted(per_device_pkts.keys()):
        pkts = per_device_pkts[dev_id]
        pkts.sort(key=lambda c: c[0])
        dev_meta = dev_lookup[dev_id]
        dev_rows = 0
        for start in range(0, len(pkts), wsize):
            chunk = pkts[start:start + wsize]
            if len(chunk) < min_window_packets:
                continue
            if spec.max_windows_per_device is not None and dev_rows >= spec.max_windows_per_device:
                break

            num = len(chunk)
            ts_arr = np.array([c[0] for c in chunk], dtype=np.float64)
            len_arr = np.array([c[1] for c in chunk], dtype=np.float64)
            hdr_arr = np.array([c[2] for c in chunk], dtype=np.float64)
            proto_list = [int(c[3]) for c in chunk]
            ttl_arr = np.array([c[4] for c in chunk], dtype=np.float64)

            dt = float(max(0.0, ts_arr[-1] - ts_arr[0]))
            diffs = np.diff(ts_arr)
            iat = float(np.mean(np.maximum(diffs, 0.0))) if len(diffs) > 0 else 0.0
            rate = float(min(3_500_000.0, num / dt)) if dt > 1e-6 else float(min(3_500_000.0, num / 1e-5))

            dom_proto = Counter(proto_list).most_common(1)[0][0]
            if dom_proto not in SUPPORTED_CANONICAL_PROTOS:
                dom_proto = PROTO_HOPOPT
            proto_name = KNOWN_PROTOCOL_MAP.get(dom_proto, "HOPOPT")

            tot_sum = float(np.sum(len_arr))
            vmin = float(np.min(len_arr))
            vmax = float(np.max(len_arr))
            vavg = float(tot_sum / num)
            vvar = float(np.var(len_arr))
            vstd = float(np.sqrt(max(0.0, vvar)))

            fin_c = int(sum(c[5] for c in chunk))
            syn_c = int(sum(c[6] for c in chunk))
            rst_c = int(sum(c[7] for c in chunk))
            psh_c = int(sum(c[8] for c in chunk))
            ack_c = int(sum(c[9] for c in chunk))
            ece_c = int(sum(c[10] for c in chunk))
            cwr_c = int(sum(c[11] for c in chunk))

            row = {
                "Header_Length": round(float(np.mean(hdr_arr)), 6),
                "Protocol Type": int(dom_proto),
                "Time_To_Live": round(float(np.mean(ttl_arr)), 6),
                "Rate": round(rate, 6),
                "fin_flag_number": round(fin_c / num, 6),
                "syn_flag_number": round(syn_c / num, 6),
                "rst_flag_number": round(rst_c / num, 6),
                "psh_flag_number": round(psh_c / num, 6),
                "ack_flag_number": round(ack_c / num, 6),
                "ece_flag_number": round(ece_c / num, 6),
                "cwr_flag_number": round(cwr_c / num, 6),
                "ack_count": ack_c,
                "syn_count": syn_c,
                "fin_count": fin_c,
                "rst_count": rst_c,
                "HTTP": round(sum(c[12] for c in chunk) / num, 6),
                "HTTPS": round(sum(c[13] for c in chunk) / num, 6),
                "DNS": round(sum(c[14] for c in chunk) / num, 6),
                "Telnet": round(sum(c[15] for c in chunk) / num, 6),
                "SMTP": round(sum(c[16] for c in chunk) / num, 6),
                "SSH": round(sum(c[17] for c in chunk) / num, 6),
                "IRC": round(sum(c[18] for c in chunk) / num, 6),
                "TCP": round(sum(c[19] for c in chunk) / num, 6),
                "UDP": round(sum(c[20] for c in chunk) / num, 6),
                "DHCP": round(sum(c[21] for c in chunk) / num, 6),
                "ARP": round(sum(c[22] for c in chunk) / num, 6),
                "ICMP": round(sum(c[23] for c in chunk) / num, 6),
                "IGMP": round(sum(c[24] for c in chunk) / num, 6),
                "IPv": round(sum(c[25] for c in chunk) / num, 6),
                "LLC": round(sum(c[26] for c in chunk) / num, 6),
                "Tot sum": int(round(tot_sum)),
                "Min": int(round(vmin)),
                "Max": int(round(vmax)),
                "AVG": round(vavg, 6),
                "Std": round(vstd, 6),
                "IAT": round(iat, 6),
                "Number": int(num),
                "Variance": round(vvar, 6),
                "protocol_name": proto_name,
                "label_raw": spec.label_raw,
                "label_category": spec.label_category,
                "is_attack": int(spec.is_attack),
                "device_id": dev_id,
                "device_category": dev_meta["official_category"],
                "testbed_role": dev_meta["testbed_role"],
                "capture_id": spec.capture_id,
            }
            rows.append(row)
            dev_rows += 1

    diag = {
        "capture_id": spec.capture_id,
        "label_raw": spec.label_raw,
        "label_category": spec.label_category,
        "total_epbs": total_epbs,
        "matched_official_device_epbs": matched_epbs,
        "active_devices": len(per_device_pkts),
        "extracted_windows": len(rows),
    }
    return rows, diag


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
