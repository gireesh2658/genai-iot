"""
IoTSynth AI - Device Model Module
Defines the core Device dataclass, DeviceCategory, BehaviorType, and validation logic.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Set, Optional, Dict, Any


class DeviceCategory(str, Enum):
    """Recognized IoT device categories."""
    SURVEILLANCE = "Surveillance"
    ENVIRONMENTAL = "Environmental"
    SMART_HOME = "Smart Home"
    CONSUMER_IOT = "Consumer IoT"
    SENSOR = "Sensor"
    INDUSTRIAL = "Industrial"
    MEDICAL = "Medical"
    OTHER = "Other"

    @classmethod
    def from_string(cls, value: str) -> "DeviceCategory":
        """Parse string to DeviceCategory safely (case-insensitive)."""
        clean_val = value.strip().lower()
        for member in cls:
            if member.value.lower() == clean_val:
                return member
        return cls.OTHER


class BehaviorType(str, Enum):
    """Communication pattern behaviors."""
    CONTINUOUS = "continuous"
    PERIODIC = "periodic"
    EVENT_DRIVEN = "event_driven"
    IDLE = "idle"

    @classmethod
    def from_string(cls, value: str) -> "BehaviorType":
        """Parse string to BehaviorType safely (case-insensitive)."""
        clean_val = value.strip().lower()
        for member in cls:
            if member.value.lower() == clean_val:
                return member
        raise ValueError(
            f"Invalid behavior type '{value}'. Supported values: {[m.value for m in cls]}"
        )


STANDARD_PROTOCOLS: Set[str] = {
    "TCP", "UDP", "HTTP", "HTTPS", "MQTT", "COAP", "DNS", "TELNET", "SSH", "RTSP"
}


@dataclass
class Device:
    """
    Representation of an IoT device in the IoTSynth AI simulation environment.
    
    Attributes:
        device_id: Unique string identifier for the device (e.g., 'cam_001').
        device_name: Human-readable name for the device.
        device_category: Category classification of the device.
        supported_protocols: List of communication protocols supported by this device.
        packet_size_min: Minimum packet size in bytes.
        packet_size_max: Maximum packet size in bytes.
        communication_interval: Nominal communication interval in seconds.
        traffic_rate_min: Minimum normal packet transmission rate in packets/sec.
        traffic_rate_max: Maximum normal packet transmission rate in packets/sec.
        behavior_type: Primary communication pattern behavior.
        is_active: Whether the device is active in the simulation.
        description: Optional textual description of the device.
        metadata: Optional dictionary for additional custom attributes.
    """
    device_id: str
    device_name: str
    device_category: str
    supported_protocols: List[str]
    packet_size_min: int
    packet_size_max: int
    communication_interval: float
    traffic_rate_min: float
    traffic_rate_max: float
    behavior_type: str = BehaviorType.PERIODIC.value
    is_active: bool = True
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate device fields after initialization."""
        self.validate()

    def validate(self) -> None:
        """
        Validate all device configuration parameters.
        Raises ValueError if any configuration violates logical constraints.
        """
        if not isinstance(self.device_id, str) or not self.device_id.strip():
            raise ValueError("device_id must be a non-empty string.")

        if not isinstance(self.device_name, str) or not self.device_name.strip():
            raise ValueError("device_name must be a non-empty string.")

        if not isinstance(self.device_category, str) or not self.device_category.strip():
            raise ValueError("device_category must be a non-empty string.")

        if not self.supported_protocols or not isinstance(self.supported_protocols, (list, set, tuple)):
            raise ValueError("supported_protocols must be a non-empty collection of protocol strings.")

        # Normalize protocols to uppercase strings
        normalized_protocols = []
        for p in self.supported_protocols:
            if not isinstance(p, str) or not p.strip():
                raise ValueError(f"Invalid protocol entry: '{p}'. Must be a non-empty string.")
            normalized_protocols.append(p.strip().upper())
        self.supported_protocols = normalized_protocols

        # Validate packet sizes
        if not isinstance(self.packet_size_min, int) or self.packet_size_min <= 0:
            raise ValueError(f"packet_size_min must be a positive integer, got: {self.packet_size_min}")

        if not isinstance(self.packet_size_max, int) or self.packet_size_max <= 0:
            raise ValueError(f"packet_size_max must be a positive integer, got: {self.packet_size_max}")

        if self.packet_size_max < self.packet_size_min:
            raise ValueError(
                f"packet_size_max ({self.packet_size_max}) cannot be less than "
                f"packet_size_min ({self.packet_size_min})."
            )

        # Validate communication interval
        if not isinstance(self.communication_interval, (int, float)) or self.communication_interval < 0:
            raise ValueError(
                f"communication_interval must be a non-negative number, got: {self.communication_interval}"
            )

        # Validate traffic rates
        if not isinstance(self.traffic_rate_min, (int, float)) or self.traffic_rate_min < 0:
            raise ValueError(
                f"traffic_rate_min must be a non-negative number, got: {self.traffic_rate_min}"
            )

        if not isinstance(self.traffic_rate_max, (int, float)) or self.traffic_rate_max < 0:
            raise ValueError(
                f"traffic_rate_max must be a non-negative number, got: {self.traffic_rate_max}"
            )

        if self.traffic_rate_max < self.traffic_rate_min:
            raise ValueError(
                f"traffic_rate_max ({self.traffic_rate_max}) cannot be less than "
                f"traffic_rate_min ({self.traffic_rate_min})."
            )

        # Validate behavior type
        if isinstance(self.behavior_type, BehaviorType):
            self.behavior_type = self.behavior_type.value
        else:
            self.behavior_type = BehaviorType.from_string(str(self.behavior_type)).value

        # Validate is_active
        if not isinstance(self.is_active, bool):
            raise ValueError(f"is_active must be a boolean, got: {type(self.is_active).__name__}")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize device to a standard Python dictionary."""
        return {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "device_category": self.device_category,
            "supported_protocols": list(self.supported_protocols),
            "packet_size_min": self.packet_size_min,
            "packet_size_max": self.packet_size_max,
            "communication_interval": self.communication_interval,
            "traffic_rate_min": self.traffic_rate_min,
            "traffic_rate_max": self.traffic_rate_max,
            "behavior_type": self.behavior_type,
            "is_active": self.is_active,
            "description": self.description,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Device":
        """Deserialize device from a dictionary."""
        return cls(
            device_id=data["device_id"],
            device_name=data["device_name"],
            device_category=data["device_category"],
            supported_protocols=data["supported_protocols"],
            packet_size_min=data["packet_size_min"],
            packet_size_max=data["packet_size_max"],
            communication_interval=data["communication_interval"],
            traffic_rate_min=data["traffic_rate_min"],
            traffic_rate_max=data["traffic_rate_max"],
            behavior_type=data.get("behavior_type", BehaviorType.PERIODIC.value),
            is_active=data.get("is_active", True),
            description=data.get("description", ""),
            metadata=data.get("metadata", {}),
        )
