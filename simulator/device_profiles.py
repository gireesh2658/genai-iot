"""
IoTSynth AI - Predefined Device Profiles Module
Defines template specifications for six core IoT device types and helper utilities.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

from simulator.device import Device, DeviceCategory, BehaviorType


@dataclass(frozen=True)
class DeviceProfile:
    """
    Blueprint profile specification used to instantiate concrete Device instances.
    Profiles are immutable templates and decoupled from individual device IDs.
    """
    profile_name: str
    device_category: str
    default_protocols: List[str]
    packet_size_min: int
    packet_size_max: int
    communication_interval: float
    traffic_rate_min: float
    traffic_rate_max: float
    behavior_type: str
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def create_device(
        self,
        device_id: str,
        device_name: Optional[str] = None,
        **overrides: Any
    ) -> Device:
        """
        Instantiate a concrete Device object based on this profile template.
        Allows overriding default parameters.
        """
        name = device_name or f"{self.profile_name}_{device_id}"
        protocols = overrides.get("supported_protocols", list(self.default_protocols))
        pkt_min = overrides.get("packet_size_min", self.packet_size_min)
        pkt_max = overrides.get("packet_size_max", self.packet_size_max)
        interval = overrides.get("communication_interval", self.communication_interval)
        rate_min = overrides.get("traffic_rate_min", self.traffic_rate_min)
        rate_max = overrides.get("traffic_rate_max", self.traffic_rate_max)
        behavior = overrides.get("behavior_type", self.behavior_type)
        desc = overrides.get("description", self.description)
        meta = dict(self.metadata)
        meta.update(overrides.get("metadata", {}))

        return Device(
            device_id=device_id,
            device_name=name,
            device_category=self.device_category,
            supported_protocols=protocols,
            packet_size_min=pkt_min,
            packet_size_max=pkt_max,
            communication_interval=interval,
            traffic_rate_min=rate_min,
            traffic_rate_max=rate_max,
            behavior_type=behavior,
            description=desc,
            metadata=meta,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize profile blueprint to dictionary."""
        return {
            "profile_name": self.profile_name,
            "device_category": self.device_category,
            "default_protocols": list(self.default_protocols),
            "packet_size_min": self.packet_size_min,
            "packet_size_max": self.packet_size_max,
            "communication_interval": self.communication_interval,
            "traffic_rate_min": self.traffic_rate_min,
            "traffic_rate_max": self.traffic_rate_max,
            "behavior_type": self.behavior_type,
            "description": self.description,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeviceProfile":
        """Deserialize profile blueprint from dictionary."""
        return cls(
            profile_name=data["profile_name"],
            device_category=data["device_category"],
            default_protocols=list(data["default_protocols"]),
            packet_size_min=int(data["packet_size_min"]),
            packet_size_max=int(data["packet_size_max"]),
            communication_interval=float(data["communication_interval"]),
            traffic_rate_min=float(data["traffic_rate_min"]),
            traffic_rate_max=float(data["traffic_rate_max"]),
            behavior_type=str(data.get("behavior_type", BehaviorType.PERIODIC.value)),
            description=str(data.get("description", "")),
            metadata=dict(data.get("metadata", {})),
        )


# ==============================================================================
# Six Predefined IoT Device Profiles (Phase 3 Core Specification)
# ==============================================================================

SMART_CAMERA_PROFILE = DeviceProfile(
    profile_name="smart_camera",
    device_category=DeviceCategory.SURVEILLANCE.value,
    default_protocols=["TCP", "UDP", "HTTPS", "RTSP"],
    packet_size_min=64,
    packet_size_max=1460,
    communication_interval=0.04,  # Approx 25 fps video telemetry/stream cadence
    traffic_rate_min=25.0,
    traffic_rate_max=150.0,
    behavior_type=BehaviorType.CONTINUOUS.value,
    description="Surveillance camera with continuous video streaming, remote monitoring, and telemetry.",
    metadata={"framerate": 25, "resolution": "1080p", "streaming_protocol": "RTSP"}
)

SMART_THERMOSTAT_PROFILE = DeviceProfile(
    profile_name="smart_thermostat",
    device_category=DeviceCategory.ENVIRONMENTAL.value,
    default_protocols=["MQTT", "TCP", "UDP"],
    packet_size_min=54,
    packet_size_max=256,
    communication_interval=30.0,  # Periodic temperature updates every 30s
    traffic_rate_min=0.1,
    traffic_rate_max=2.0,
    behavior_type=BehaviorType.PERIODIC.value,
    description="Environmental thermostat sending periodic temperature and humidity readings.",
    metadata={"reporting_interval_seconds": 30, "sensor_types": ["temperature", "humidity"]}
)

SMART_BULB_PROFILE = DeviceProfile(
    profile_name="smart_bulb",
    device_category=DeviceCategory.SMART_HOME.value,
    default_protocols=["TCP", "UDP", "MQTT"],
    packet_size_min=42,
    packet_size_max=180,
    communication_interval=10.0,  # Heartbeat when idle; event-driven state shifts
    traffic_rate_min=0.05,
    traffic_rate_max=5.0,
    behavior_type=BehaviorType.EVENT_DRIVEN.value,
    description="Connected lighting with event-driven state changes and low-volume keep-alives.",
    metadata={"control_protocol": "MQTT", "dimmable": True}
)

SMART_SPEAKER_PROFILE = DeviceProfile(
    profile_name="smart_speaker",
    device_category=DeviceCategory.CONSUMER_IOT.value,
    default_protocols=["TCP", "UDP", "HTTPS", "DNS"],
    packet_size_min=60,
    packet_size_max=1200,
    communication_interval=2.0,  # Periodic cloud sync, bursts during audio streaming
    traffic_rate_min=2.0,
    traffic_rate_max=50.0,
    behavior_type=BehaviorType.PERIODIC.value,
    description="Voice-assisted consumer device with periodic cloud sync and bursty audio buffering.",
    metadata={"audio_supported": True, "voice_recognition": "cloud_assisted"}
)

SMART_PLUG_PROFILE = DeviceProfile(
    profile_name="smart_plug",
    device_category=DeviceCategory.SMART_HOME.value,
    default_protocols=["MQTT", "TCP", "UDP"],
    packet_size_min=48,
    packet_size_max=192,
    communication_interval=15.0,  # Periodic power-monitoring telemetry updates
    traffic_rate_min=0.1,
    traffic_rate_max=3.0,
    behavior_type=BehaviorType.PERIODIC.value,
    description="Smart home power switch broadcasting power-monitoring metrics and switch states.",
    metadata={"power_metering": True, "voltage_monitoring": True}
)

MOTION_SENSOR_PROFILE = DeviceProfile(
    profile_name="motion_sensor",
    device_category=DeviceCategory.SENSOR.value,
    default_protocols=["MQTT", "UDP", "COAP"],
    packet_size_min=40,
    packet_size_max=128,
    communication_interval=60.0,  # Infrequent heartbeat; burst on detected movement
    traffic_rate_min=0.02,
    traffic_rate_max=10.0,
    behavior_type=BehaviorType.EVENT_DRIVEN.value,
    description="Passive infrared sensor transmitting immediate alert bursts on motion detection.",
    metadata={"detection_technology": "PIR", "battery_operated": True}
)

PREDEFINED_PROFILES: Dict[str, DeviceProfile] = {
    "smart_camera": SMART_CAMERA_PROFILE,
    "smart_thermostat": SMART_THERMOSTAT_PROFILE,
    "smart_bulb": SMART_BULB_PROFILE,
    "smart_speaker": SMART_SPEAKER_PROFILE,
    "smart_plug": SMART_PLUG_PROFILE,
    "motion_sensor": MOTION_SENSOR_PROFILE,
}


def get_profile(name: str) -> DeviceProfile:
    """
    Retrieve a predefined device profile by name (case-insensitive).
    Raises KeyError if profile is not recognized.
    """
    clean_name = name.strip().lower()
    if clean_name in PREDEFINED_PROFILES:
        return PREDEFINED_PROFILES[clean_name]
    available = list(PREDEFINED_PROFILES.keys())
    raise KeyError(f"Unknown device profile '{name}'. Available profiles: {available}")


def list_predefined_profiles() -> List[str]:
    """Return names of all predefined device profiles."""
    return list(PREDEFINED_PROFILES.keys())


def save_profiles_to_directory(directory_path: str) -> List[str]:
    """
    Export all predefined device profiles to JSON files inside the given directory.
    Returns list of written file paths.
    """
    os.makedirs(directory_path, exist_ok=True)
    saved_files = []
    for name, profile in PREDEFINED_PROFILES.items():
        file_path = os.path.join(directory_path, f"{name}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f, indent=2)
        saved_files.append(file_path)
    return saved_files
