"""
Battery Failsafe System - Kịch bản 3
Tính toán năng lượng và quyết định hạ cánh khẩn cấp nếu pin không đủ về nhà
"""

import time
import math
from typing import Optional, Tuple, Dict
from dataclasses import dataclass
from loguru import logger

try:
    from .geofencing import GeoPoint, GeoFence
except ImportError:
    from safety.geofencing import GeoPoint, GeoFence


@dataclass
class BatteryState:
    """Battery telemetry data"""
    voltage: float  # Volts
    current: float  # Amps
    remaining: int  # Percentage (0-100)
    consumed: float  # mAh consumed
    
    def is_critical(self, cells: int = 4) -> bool:
        """Check if voltage is critically low"""
        cell_voltage = self.voltage / cells
        return cell_voltage < 3.3  # 3.3V per cell = critical
    
    def is_warning(self, cells: int = 4) -> bool:
        """Check if voltage is in warning range"""
        cell_voltage = self.voltage / cells
        return cell_voltage < 3.5  # 3.5V per cell = warning


@dataclass
class FlightState:
    """Current flight state"""
    position: GeoPoint
    altitude: float  # meters MSL
    ground_speed: float  # m/s
    heading: float  # degrees
    home_position: GeoPoint
    home_altitude: float  # meters MSL


class EnergyCalculator:
    """Calculate energy consumption and range prediction"""
    
    def __init__(self, battery_capacity_mah: float = 10400.0, 
                 nominal_voltage: float = 14.8,
                 cells: int = 4):
        """
        Initialize energy calculator
        
        Args:
            battery_capacity_mah: Total battery capacity (4S2P = 2x5200 = 10400mAh)
            nominal_voltage: Nominal voltage (4S = 14.8V)
            cells: Number of cells (4S = 4)
        """
        self.capacity_mah = battery_capacity_mah
        self.nominal_voltage = nominal_voltage
        self.cells = cells
        
        # Energy consumption model (from testing)
        self.cruise_power_watts = 150.0  # Average cruise power
        self.climb_power_watts = 250.0   # Power during climb
        self.hover_power_watts = 100.0   # Power in loiter
        
        # Safety margins
        self.reserve_percentage = 20.0   # 20% reserve
        self.min_cell_voltage = 3.3      # Absolute minimum
        
        logger.info(f"Energy calculator: {battery_capacity_mah}mAh, {nominal_voltage}V, {cells}S")
    
    def calculate_distance_to_home(self, current: GeoPoint, home: GeoPoint) -> float:
        """Calculate horizontal distance to home (meters)"""
        R = 6371000  # Earth radius in meters
        
        lat1 = math.radians(current.lat)
        lat2 = math.radians(home.lat)
        dlat = math.radians(home.lat - current.lat)
        dlon = math.radians(home.lon - current.lon)
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def estimate_rth_energy(self, flight_state: FlightState) -> float:
        """
        Estimate energy required to return to home (mAh)
        
        Returns:
            Estimated mAh required for RTH
        """
        # Calculate distance to home
        distance = self.calculate_distance_to_home(
            flight_state.position,
            flight_state.home_position
        )
        
        # Calculate altitude change
        altitude_change = flight_state.home_altitude - flight_state.altitude
        
        # Estimate flight time for horizontal distance
        # Assume cruise speed of 15 m/s
        cruise_speed = 15.0
        horizontal_time = distance / cruise_speed
        
        # Estimate climb/descent time
        # Assume 2 m/s vertical speed
        vertical_speed = 2.0
        vertical_time = abs(altitude_change) / vertical_speed if altitude_change != 0 else 0
        
        # Calculate energy for cruise
        cruise_energy_wh = (self.cruise_power_watts * horizontal_time) / 3600
        
        # Calculate energy for vertical movement
        if altitude_change > 0:  # Climbing
            vertical_energy_wh = (self.climb_power_watts * vertical_time) / 3600
        else:  # Descending
            vertical_energy_wh = (self.cruise_power_watts * 0.5 * vertical_time) / 3600
        
        # Total energy in Wh
        total_energy_wh = cruise_energy_wh + vertical_energy_wh
        
        # Convert to mAh (Wh = V * Ah)
        total_energy_mah = (total_energy_wh / self.nominal_voltage) * 1000
        
        # Add safety margin (20%)
        total_with_margin = total_energy_mah * (1 + self.reserve_percentage / 100)
        
        logger.debug(f"RTH energy estimate: {total_with_margin:.0f}mAh "
                    f"(distance={distance:.0f}m, alt_change={altitude_change:.0f}m)")
        
        return total_with_margin
    
    def calculate_remaining_energy(self, battery: BatteryState) -> float:
        """
        Calculate remaining usable energy (mAh)
        
        Returns:
            Remaining mAh (accounting for voltage cutoff)
        """
        # Calculate remaining based on voltage
        current_cell_voltage = battery.voltage / self.cells
        nominal_cell_voltage = self.nominal_voltage / self.cells
        min_cell_voltage = self.min_cell_voltage
        
        # Linear approximation of remaining capacity based on voltage
        # This is simplified - real LiPo discharge is non-linear
        if current_cell_voltage <= min_cell_voltage:
            return 0.0
        
        voltage_range = nominal_cell_voltage - min_cell_voltage
        voltage_remaining = current_cell_voltage - min_cell_voltage
        voltage_percentage = (voltage_remaining / voltage_range) * 100
        
        # Use the more conservative of voltage-based or coulomb-counting
        voltage_based_mah = (voltage_percentage / 100) * self.capacity_mah
        
        # If consumed data available, use it
        if battery.consumed > 0:
            coulomb_based_mah = self.capacity_mah - battery.consumed
            remaining_mah = min(voltage_based_mah, coulomb_based_mah)
        else:
            remaining_mah = voltage_based_mah
        
        logger.debug(f"Remaining energy: {remaining_mah:.0f}mAh "
                    f"(voltage={current_cell_voltage:.2f}V/cell)")
        
        return remaining_mah
    
    def can_reach_home(self, battery: BatteryState, flight_state: FlightState) -> Tuple[bool, float, str]:
        """
        Determine if UAV can safely reach home
        
        Returns:
            (can_reach, margin_percentage, message)
        """
        remaining_mah = self.calculate_remaining_energy(battery)
        required_mah = self.estimate_rth_energy(flight_state)
        
        if remaining_mah <= 0:
            return False, 0.0, "Battery depleted"
        
        margin_mah = remaining_mah - required_mah
        margin_percentage = (margin_mah / required_mah) * 100
        
        if margin_mah < 0:
            return False, margin_percentage, f"Insufficient energy: need {required_mah:.0f}mAh, have {remaining_mah:.0f}mAh"
        elif margin_percentage < 20:
            return True, margin_percentage, f"Tight margin: {margin_percentage:.0f}% reserve"
        else:
            return True, margin_percentage, f"Safe: {margin_percentage:.0f}% energy reserve"


class EmergencyLandingSite:
    """Find suitable emergency landing sites"""
    
    def __init__(self, min_distance: float = 100.0, max_distance: float = 500.0):
        self.min_distance = min_distance
        self.max_distance = max_distance
    
    def find_nearest_safe_site(self, current: GeoPoint, 
                               exclusion_zones: list = None) -> Optional[GeoPoint]:
        """
        Find nearest emergency landing site
        
        In real implementation, this would:
        - Use terrain database
        - Analyze camera feed for flat areas
        - Avoid obstacles and exclusion zones
        - Consider wind direction
        
        For now, returns a point 200m in opposite direction of home
        """
        # Simplified: land nearby in safe direction
        # In production, integrate with AI vision system
        
        logger.warning("Emergency landing site selection: Using simplified algorithm")
        
        # Calculate bearing away from home (simplification)
        # Real system would use terrain analysis
        safe_distance = 200.0  # 200m from current position
        
        # Use current position with slight offset
        # Real implementation: computer vision + terrain analysis
        offset_lat = 0.001  # ~100m north
        offset_lon = 0.001  # ~100m east
        
        landing_site = GeoPoint(
            current.lat + offset_lat,
            current.lon + offset_lon
        )
        
        logger.info(f"Emergency landing site: {landing_site}")
        return landing_site


class BatteryFailsafeSystem:
    """Complete battery failsafe system"""
    
    def __init__(self, mavlink_handler, 
                 battery_capacity_mah: float = 10400.0,
                 cells: int = 4):
        """
        Initialize battery failsafe system
        
        Args:
            mavlink_handler: MAVLink handler for sending commands
            battery_capacity_mah: Total battery capacity
            cells: Number of cells (4S = 4)
        """
        self.mavlink = mavlink_handler
        self.energy_calc = EnergyCalculator(battery_capacity_mah, cells=cells)
        self.landing_site_finder = EmergencyLandingSite()
        
        self.is_monitoring = False
        self.failsafe_triggered = False
        self.last_check_time = 0.0
        self.check_interval = 5.0  # Check every 5 seconds
        
        # State tracking
        self.current_battery: Optional[BatteryState] = None
        self.current_flight: Optional[FlightState] = None
        
        # Alert thresholds
        self.warning_margin_percent = 30.0  # Warn at 30% margin
        self.critical_margin_percent = 10.0  # Critical at 10% margin
        
        logger.info("🔋 Battery failsafe system initialized")
    
    def start_monitoring(self):
        """Start battery monitoring"""
        self.is_monitoring = True
        self.failsafe_triggered = False
        logger.info("🔋 Battery monitoring STARTED")
    
    def stop_monitoring(self):
        """Stop battery monitoring"""
        self.is_monitoring = False
        logger.info("🔋 Battery monitoring STOPPED")
    
    def update_battery(self, voltage: float, current: float, 
                      remaining: int, consumed: float = 0.0):
        """Update battery state from telemetry"""
        self.current_battery = BatteryState(voltage, current, remaining, consumed)
    
    def update_flight_state(self, lat: float, lon: float, alt: float,
                           ground_speed: float, heading: float,
                           home_lat: float, home_lon: float, home_alt: float):
        """Update flight state from telemetry"""
        self.current_flight = FlightState(
            position=GeoPoint(lat, lon),
            altitude=alt,
            ground_speed=ground_speed,
            heading=heading,
            home_position=GeoPoint(home_lat, home_lon),
            home_altitude=home_alt
        )
    
    def check_battery_failsafe(self) -> Tuple[bool, str]:
        """
        Perform battery failsafe check
        
        Returns:
            (failsafe_needed, reason)
        """
        current_time = time.time()
        
        # Rate limiting
        if current_time - self.last_check_time < self.check_interval:
            return False, "Rate limited"
        
        self.last_check_time = current_time
        
        if not self.is_monitoring:
            return False, "Not monitoring"
        
        if self.current_battery is None or self.current_flight is None:
            logger.warning("Battery or flight state not available")
            return False, "No telemetry"
        
        battery = self.current_battery
        flight = self.current_flight
        
        # Check 1: Critical voltage
        if battery.is_critical(cells=self.energy_calc.cells):
            logger.error(f"🚨 CRITICAL VOLTAGE: {battery.voltage}V")
            return True, "Critical voltage - immediate landing required"
        
        # Check 2: Can reach home?
        can_reach, margin, message = self.energy_calc.can_reach_home(battery, flight)
        
        if not can_reach:
            logger.error(f"🚨 CANNOT REACH HOME: {message}")
            return True, f"Insufficient energy for RTH: {message}"
        
        # Check 3: Low margin warning
        if margin < self.critical_margin_percent:
            logger.error(f"🚨 CRITICAL MARGIN: {margin:.0f}% - {message}")
            return True, f"Critical energy margin: {margin:.0f}%"
        
        elif margin < self.warning_margin_percent:
            logger.warning(f"⚠️ LOW MARGIN: {margin:.0f}% - {message}")
            # Don't trigger failsafe yet, just warn
            return False, f"Low energy margin: {margin:.0f}%"
        
        else:
            logger.debug(f"✓ Battery OK: {margin:.0f}% margin")
            return False, "Battery OK"
    
    def execute_battery_failsafe(self, reason: str):
        """
        Execute battery failsafe action
        
        Decision logic:
        1. If can barely reach home (0-10% margin) → Immediate RTH
        2. If cannot reach home → Emergency landing at nearest safe site
        3. If critical voltage → Immediate emergency landing
        """
        if self.failsafe_triggered:
            logger.debug("Failsafe already triggered")
            return
        
        self.failsafe_triggered = True
        logger.error(f"🚨 EXECUTING BATTERY FAILSAFE: {reason}")
        
        battery = self.current_battery
        flight = self.current_flight
        
        if battery is None or flight is None:
            logger.error("Cannot execute failsafe: no telemetry")
            return
        
        # Check if we can reach home
        can_reach, margin, message = self.energy_calc.can_reach_home(battery, flight)
        
        if can_reach and margin > 0:
            # Immediate RTH
            logger.warning("🏠 INITIATING IMMEDIATE RTH")
            self.mavlink.return_to_home()
            
        else:
            # Emergency landing
            logger.error("🚨 INITIATING EMERGENCY LANDING")
            
            # Find landing site
            landing_site = self.landing_site_finder.find_nearest_safe_site(
                flight.position
            )
            
            if landing_site:
                # Navigate to landing site
                logger.info(f"Emergency landing site: {landing_site}")
                self.mavlink.send_waypoint(
                    landing_site.lat,
                    landing_site.lon,
                    flight.altitude - 10.0  # Descend 10m first
                )
                
                # Wait brief moment then land
                time.sleep(2.0)
                self.mavlink.land()
            else:
                # Last resort: land immediately
                logger.error("🚨 NO SAFE SITE - LANDING IMMEDIATELY")
                self.mavlink.land()
    
    def get_status(self) -> Dict:
        """Get current battery failsafe status"""
        if self.current_battery is None or self.current_flight is None:
            return {"status": "No telemetry"}
        
        can_reach, margin, message = self.energy_calc.can_reach_home(
            self.current_battery,
            self.current_flight
        )
        
        remaining = self.energy_calc.calculate_remaining_energy(self.current_battery)
        required = self.energy_calc.estimate_rth_energy(self.current_flight)
        distance = self.energy_calc.calculate_distance_to_home(
            self.current_flight.position,
            self.current_flight.home_position
        )
        
        return {
            "voltage": self.current_battery.voltage,
            "remaining_mah": remaining,
            "required_rth_mah": required,
            "distance_to_home_m": distance,
            "can_reach_home": can_reach,
            "energy_margin_percent": margin,
            "status": message,
            "failsafe_triggered": self.failsafe_triggered
        }


# Example usage
if __name__ == "__main__":
    print("=== Battery Failsafe System Test ===\n")
    
    # Mock MAVLink handler
    class MockMAVLink:
        def return_to_home(self):
            print("→ MAVLink: RTH command sent")
        
        def land(self):
            print("→ MAVLink: LAND command sent")
        
        def send_waypoint(self, lat, lon, alt):
            print(f"→ MAVLink: Waypoint sent ({lat:.6f}, {lon:.6f}, {alt:.0f}m)")
    
    mavlink = MockMAVLink()
    
    # Create failsafe system (4S2P = 10400mAh)
    failsafe = BatteryFailsafeSystem(mavlink, battery_capacity_mah=10400.0, cells=4)
    failsafe.start_monitoring()
    
    # Simulate scenarios
    print("Scenario 1: Good battery, close to home")
    print("-" * 50)
    failsafe.update_battery(voltage=16.0, current=10.0, remaining=80, consumed=2000)
    failsafe.update_flight_state(
        lat=21.029, lon=105.805, alt=50,
        ground_speed=15.0, heading=90,
        home_lat=21.028, home_lon=105.804, home_alt=10
    )
    
    need_failsafe, reason = failsafe.check_battery_failsafe()
    print(f"Failsafe needed: {need_failsafe}")
    print(f"Reason: {reason}")
    print(f"Status: {failsafe.get_status()}\n")
    
    print("\nScenario 2: Low battery, far from home")
    print("-" * 50)
    failsafe.update_battery(voltage=14.0, current=10.0, remaining=25, consumed=8000)
    failsafe.update_flight_state(
        lat=21.035, lon=105.815, alt=100,
        ground_speed=15.0, heading=180,
        home_lat=21.028, home_lon=105.804, home_alt=10
    )
    
    need_failsafe, reason = failsafe.check_battery_failsafe()
    print(f"Failsafe needed: {need_failsafe}")
    print(f"Reason: {reason}")
    
    if need_failsafe:
        failsafe.execute_battery_failsafe(reason)
    
    print(f"\nStatus: {failsafe.get_status()}")
