"""Safety module for geofencing, emergency procedures, and GPS denial handling"""

from .geofencing import (
    GeoPoint,
    GeoFence,
    GeofencingSystem,
    GeofenceMonitor,
    GeofenceTemplates,
    FenceAction
)

from .battery_failsafe import (
    BatteryFailsafeSystem,
    BatteryState,
    EnergyCalculator
)

# NEW: GPS Monitor (Pilot-Assisted Mode) - Recommended for real flights
from .gps_monitor import (
    GPSMonitor,
    PilotAlertManager,
    GPSStatus,
    GPSData
)

# LEGACY: GPS Denial Handler (Research Only)
# Warning: Do not use for actual flight control
from .gps_denial_handler import (
    GPSDenialHandler,
    GPSAnomalyDetector,
    DeadReckoningNavigator,
    GPSState,
    EscapeAction
)

__all__ = [
    # Geofencing
    'GeoPoint',
    'GeoFence',
    'GeofencingSystem',
    'GeofenceMonitor',
    'GeofenceTemplates',
    'FenceAction',
    # Battery failsafe
    'BatteryFailsafeSystem',
    'BatteryState',
    'EnergyCalculator',
    # GPS Monitor (NEW - Recommended)
    'GPSMonitor',
    'PilotAlertManager',
    'GPSStatus',
    'GPSData',
    # GPS denial (LEGACY - Research only)
    'GPSDenialHandler',
    'GPSAnomalyDetector',
    'DeadReckoningNavigator',
    'GPSState',
    'EscapeAction'
]
