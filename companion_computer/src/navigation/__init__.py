"""Navigation module for autonomous flight and GPS denial handling"""

from .autonomous import (
    Position,
    Velocity,
    NavigationAlgorithms,
    PathFollower,
    LoiterController,
    ObstacleAvoidance,
    WindEstimator
)

from .geolocation import (
    calculate_target_geolocation
)

# EKF-Integrated GPS Denial - import with fallback
try:
    from .ekf_integrated_gps_denial import (
        ExtendedKalmanFilter,
        EKFIntegratedDeadReckoningNavigator,
        EKFIntegratedGPSDenialHandler
    )
    EKF_AVAILABLE = True
except ImportError:
    EKF_AVAILABLE = False

# Hybrid GPS Denial System - import with fallback
try:
    from .hybrid_gps_denial_system import (
        NavigationMode,
        ComputeLocation,
        AirspeedReading,
        MS4525DOAirspeedSensor,
        QuantumFilterComparator,
        MLAdaptiveTuner,
        HybridGPSDenialSystem,
        assess_rpi_capability
    )
    HYBRID_SYSTEM_AVAILABLE = True
except ImportError:
    HYBRID_SYSTEM_AVAILABLE = False

__all__ = [
    # Autonomous navigation
    'Position',
    'Velocity', 
    'NavigationAlgorithms',
    'PathFollower',
    'LoiterController',
    'ObstacleAvoidance',
    'WindEstimator',
    # Geolocation
    'calculate_target_geolocation',
    # EKF GPS Denial (if available)
    'EKF_AVAILABLE',
    # Hybrid System (if available)
    'HYBRID_SYSTEM_AVAILABLE',
]

if EKF_AVAILABLE:
    __all__.extend([
        'ExtendedKalmanFilter',
        'EKFIntegratedDeadReckoningNavigator',
        'EKFIntegratedGPSDenialHandler'
    ])

if HYBRID_SYSTEM_AVAILABLE:
    __all__.extend([
        'NavigationMode',
        'ComputeLocation',
        'AirspeedReading',
        'MS4525DOAirspeedSensor',
        'QuantumFilterComparator',
        'MLAdaptiveTuner',
        'HybridGPSDenialSystem',
        'assess_rpi_capability'
    ])
