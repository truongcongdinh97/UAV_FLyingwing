"""
Geofencing System - Advanced Polygon-based Virtual Fence
Monitor GPS position and enforce no-fly zones with complex polygons
"""

import time
import math
from typing import List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import json

try:
    from shapely.geometry import Point, Polygon
    from shapely.ops import nearest_points
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False
    print("Warning: shapely not installed. Install with: pip install shapely")

from loguru import logger


class FenceAction(Enum):
    """Action to take when fence is breached"""
    WARN = "warn"  # Only log warning
    RTH = "return_to_home"  # Return to home
    LOITER = "loiter"  # Loiter at current position
    LAND = "land"  # Emergency land
    GUIDED_RETURN = "guided_return"  # Intelligent guided return to safe zone


@dataclass
class GeoPoint:
    """Geographic point (latitude, longitude)"""
    lat: float
    lon: float
    
    def to_tuple(self) -> Tuple[float, float]:
        return (self.lon, self.lat)  # Shapely uses (x, y) = (lon, lat)
    
    def __str__(self):
        return f"({self.lat:.6f}, {self.lon:.6f})"


class GeoFence:
    """Single geofence zone (inclusion or exclusion)"""
    
    def __init__(self, name: str, points: List[GeoPoint], 
                 is_exclusion: bool = True, altitude_min: float = 0, 
                 altitude_max: float = 1000):
        """
        Create geofence
        
        Args:
            name: Fence identifier
            points: List of points forming polygon (closed automatically)
            is_exclusion: True = no-fly zone, False = must-fly zone
            altitude_min: Minimum altitude (meters MSL)
            altitude_max: Maximum altitude (meters MSL)
        """
        self.name = name
        self.points = points
        self.is_exclusion = is_exclusion
        self.altitude_min = altitude_min
        self.altitude_max = altitude_max
        
        # Create Shapely polygon
        if SHAPELY_AVAILABLE:
            coords = [p.to_tuple() for p in points]
            self.polygon = Polygon(coords)
            logger.info(f"Geofence '{name}' created: {len(points)} points, "
                       f"{'EXCLUSION' if is_exclusion else 'INCLUSION'}, "
                       f"alt {altitude_min}-{altitude_max}m")
        else:
            self.polygon = None
            logger.warning(f"Geofence '{name}' created without shapely (limited functionality)")
    
    def contains_point(self, point: GeoPoint, altitude: float = 50.0) -> bool:
        """Check if point is inside fence"""
        if not SHAPELY_AVAILABLE:
            # Fallback: simple ray casting algorithm
            return self._point_in_polygon_fallback(point)
        
        # Check altitude bounds
        if not (self.altitude_min <= altitude <= self.altitude_max):
            return False
        
        # Check horizontal containment
        p = Point(point.to_tuple())
        return self.polygon.contains(p)
    
    def distance_to_fence(self, point: GeoPoint) -> float:
        """Calculate distance from point to fence boundary (meters)"""
        if not SHAPELY_AVAILABLE:
            return self._distance_fallback(point)
        
        p = Point(point.to_tuple())
        
        # If inside, return negative distance to boundary
        if self.polygon.contains(p):
            # Distance to nearest edge (negative = inside)
            nearest = nearest_points(p, self.polygon.boundary)[1]
            dist = self._haversine_distance(
                point.lat, point.lon,
                nearest.y, nearest.x
            )
            return -dist
        else:
            # Distance to nearest point on polygon (positive = outside)
            nearest = nearest_points(p, self.polygon)[1]
            dist = self._haversine_distance(
                point.lat, point.lon,
                nearest.y, nearest.x
            )
            return dist
    
    def get_safe_return_point(self, current: GeoPoint) -> Optional[GeoPoint]:
        """Get nearest safe point outside exclusion zone"""
        if not SHAPELY_AVAILABLE or not self.is_exclusion:
            return None
        
        p = Point(current.to_tuple())
        
        # Find nearest point on boundary
        nearest = nearest_points(p, self.polygon.boundary)[1]
        
        # Move 20m beyond boundary
        bearing = self._calculate_bearing(current.lat, current.lon, nearest.y, nearest.x)
        safe_point = self._destination_point(
            GeoPoint(nearest.y, nearest.x),
            distance=20.0,  # 20m buffer
            bearing=bearing
        )
        
        return safe_point
    
    @staticmethod
    def _haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points (meters)"""
        R = 6371000  # Earth radius in meters
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    @staticmethod
    def _calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate bearing from point 1 to point 2 (degrees)"""
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlon = math.radians(lon2 - lon1)
        
        x = math.sin(dlon) * math.cos(lat2_rad)
        y = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon)
        
        bearing = math.atan2(x, y)
        return (math.degrees(bearing) + 360) % 360
    
    @staticmethod
    def _destination_point(point: GeoPoint, distance: float, bearing: float) -> GeoPoint:
        """Calculate destination point given distance and bearing"""
        R = 6371000  # Earth radius
        
        lat1 = math.radians(point.lat)
        lon1 = math.radians(point.lon)
        brng = math.radians(bearing)
        
        lat2 = math.asin(math.sin(lat1) * math.cos(distance/R) +
                        math.cos(lat1) * math.sin(distance/R) * math.cos(brng))
        
        lon2 = lon1 + math.atan2(math.sin(brng) * math.sin(distance/R) * math.cos(lat1),
                                 math.cos(distance/R) - math.sin(lat1) * math.sin(lat2))
        
        return GeoPoint(math.degrees(lat2), math.degrees(lon2))
    
    def _point_in_polygon_fallback(self, point: GeoPoint) -> bool:
        """Fallback point-in-polygon test using ray casting"""
        x, y = point.lon, point.lat
        n = len(self.points)
        inside = False
        
        p1 = self.points[0]
        for i in range(1, n + 1):
            p2 = self.points[i % n]
            
            if y > min(p1.lat, p2.lat):
                if y <= max(p1.lat, p2.lat):
                    if x <= max(p1.lon, p2.lon):
                        if p1.lat != p2.lat:
                            xinters = (y - p1.lat) * (p2.lon - p1.lon) / (p2.lat - p1.lat) + p1.lon
                        if p1.lon == p2.lon or x <= xinters:
                            inside = not inside
            p1 = p2
        
        return inside
    
    def _distance_fallback(self, point: GeoPoint) -> float:
        """Fallback distance calculation (approximate)"""
        # Find closest edge
        min_dist = float('inf')
        
        for i in range(len(self.points)):
            p1 = self.points[i]
            p2 = self.points[(i + 1) % len(self.points)]
            
            dist = self._distance_to_segment(point, p1, p2)
            min_dist = min(min_dist, dist)
        
        # Negative if inside
        if self._point_in_polygon_fallback(point):
            return -min_dist
        return min_dist
    
    def _distance_to_segment(self, point: GeoPoint, p1: GeoPoint, p2: GeoPoint) -> float:
        """Calculate distance from point to line segment"""
        # Simplified: distance to closest endpoint
        d1 = self._haversine_distance(point.lat, point.lon, p1.lat, p1.lon)
        d2 = self._haversine_distance(point.lat, point.lon, p2.lat, p2.lon)
        return min(d1, d2)
    
    def to_dict(self) -> dict:
        """Serialize to dictionary"""
        return {
            "name": self.name,
            "points": [{"lat": p.lat, "lon": p.lon} for p in self.points],
            "is_exclusion": self.is_exclusion,
            "altitude_min": self.altitude_min,
            "altitude_max": self.altitude_max
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GeoFence':
        """Deserialize from dictionary"""
        points = [GeoPoint(p["lat"], p["lon"]) for p in data["points"]]
        return cls(
            name=data["name"],
            points=points,
            is_exclusion=data.get("is_exclusion", True),
            altitude_min=data.get("altitude_min", 0),
            altitude_max=data.get("altitude_max", 1000)
        )


class GeofencingSystem:
    """Complete geofencing system with multiple zones"""
    
    def __init__(self, home_position: GeoPoint, max_distance: float = 1000.0):
        """
        Initialize geofencing system
        
        Args:
            home_position: Home/launch position
            max_distance: Maximum allowed distance from home (meters)
        """
        self.home = home_position
        self.max_distance = max_distance
        self.fences: List[GeoFence] = []
        
        self.breach_count = 0
        self.last_breach_time = 0.0
        self.breach_cooldown = 5.0  # seconds
        
        self.warning_distance = 30.0  # meters - warn when this close to fence
        
        logger.info(f"Geofencing system initialized: Home={home_position}, Max distance={max_distance}m")
    
    def add_fence(self, fence: GeoFence):
        """Add geofence zone"""
        self.fences.append(fence)
        logger.info(f"Added fence: {fence.name}")
    
    def remove_fence(self, name: str) -> bool:
        """Remove geofence by name"""
        for i, fence in enumerate(self.fences):
            if fence.name == name:
                self.fences.pop(i)
                logger.info(f"Removed fence: {name}")
                return True
        return False
    
    def check_position(self, current: GeoPoint, altitude: float) -> Tuple[bool, str, Optional[FenceAction]]:
        """
        Check if current position violates any fence
        
        Returns:
            (is_safe, message, recommended_action)
        """
        # Check max distance from home
        distance_from_home = GeoFence._haversine_distance(
            self.home.lat, self.home.lon,
            current.lat, current.lon
        )
        
        if distance_from_home > self.max_distance:
            logger.error(f"⚠️ MAX DISTANCE BREACH: {distance_from_home:.0f}m from home (max {self.max_distance}m)")
            return False, f"Too far from home: {distance_from_home:.0f}m", FenceAction.RTH
        
        # Check all geofences
        for fence in self.fences:
            inside = fence.contains_point(current, altitude)
            
            if fence.is_exclusion and inside:
                # Inside exclusion zone - BREACH!
                logger.error(f"🚫 FENCE BREACH: Inside exclusion zone '{fence.name}'")
                self.breach_count += 1
                self.last_breach_time = time.time()
                
                return False, f"BREACH: Inside no-fly zone '{fence.name}'", FenceAction.GUIDED_RETURN
            
            elif not fence.is_exclusion and not inside:
                # Outside inclusion zone - BREACH!
                logger.error(f"🚫 FENCE BREACH: Outside required zone '{fence.name}'")
                self.breach_count += 1
                self.last_breach_time = time.time()
                
                return False, f"BREACH: Outside required zone '{fence.name}'", FenceAction.GUIDED_RETURN
            
            # Check proximity warning
            distance = fence.distance_to_fence(current)
            if fence.is_exclusion and 0 < distance < self.warning_distance:
                logger.warning(f"⚠️ FENCE WARNING: {distance:.1f}m from '{fence.name}' exclusion zone")
        
        return True, "Position safe", None
    
    def get_safe_return_point(self, current: GeoPoint) -> Optional[GeoPoint]:
        """Get nearest safe point if currently in breach"""
        # Check which fence is breached
        for fence in self.fences:
            if fence.is_exclusion and fence.contains_point(current):
                # Inside exclusion zone - get safe return point
                return fence.get_safe_return_point(current)
        
        # If too far from home, return home
        distance_from_home = GeoFence._haversine_distance(
            self.home.lat, self.home.lon,
            current.lat, current.lon
        )
        
        if distance_from_home > self.max_distance:
            return self.home
        
        return None
    
    def save_to_file(self, filename: str):
        """Save all geofences to JSON file"""
        data = {
            "home": {"lat": self.home.lat, "lon": self.home.lon},
            "max_distance": self.max_distance,
            "fences": [fence.to_dict() for fence in self.fences]
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.success(f"Geofences saved to {filename}")
    
    def load_from_file(self, filename: str):
        """Load geofences from JSON file"""
        with open(filename, 'r') as f:
            data = json.load(f)
        
        self.home = GeoPoint(data["home"]["lat"], data["home"]["lon"])
        self.max_distance = data["max_distance"]
        
        self.fences.clear()
        for fence_data in data["fences"]:
            fence = GeoFence.from_dict(fence_data)
            self.add_fence(fence)
        
        logger.success(f"Geofences loaded from {filename}")


class GeofenceMonitor:
    """Active geofence monitor that integrates with MAVLink"""
    
    def __init__(self, geofencing_system: GeofencingSystem, mavlink_handler):
        self.system = geofencing_system
        self.mavlink = mavlink_handler
        
        self.is_monitoring = False
        self.current_position: Optional[GeoPoint] = None
        self.current_altitude: float = 0.0
        
        self.last_check_time = 0.0
        self.check_interval = 0.5  # Check every 0.5 seconds
        
    def start_monitoring(self):
        """Start monitoring GPS position"""
        self.is_monitoring = True
        logger.info("🛡️ Geofence monitoring STARTED")
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.is_monitoring = False
        logger.info("Geofence monitoring STOPPED")
    
    def update_position(self, lat: float, lon: float, alt: float):
        """Update current position from GPS"""
        self.current_position = GeoPoint(lat, lon)
        self.current_altitude = alt
        
        # Check if time to perform fence check
        current_time = time.time()
        if current_time - self.last_check_time < self.check_interval:
            return
        
        self.last_check_time = current_time
        
        if not self.is_monitoring:
            return
        
        # Perform fence check
        is_safe, message, action = self.system.check_position(self.current_position, self.current_altitude)
        
        if not is_safe:
            logger.error(f"🚨 FENCE VIOLATION: {message}")
            self._handle_breach(action)
    
    def _handle_breach(self, action: Optional[FenceAction]):
        """Handle fence breach"""
        if action is None:
            return
        
        logger.warning(f"🚨 EXECUTING FENCE ACTION: {action.value}")
        
        if action == FenceAction.RTH:
            # Send RTH command
            logger.info("Sending RTH command to iNav...")
            self.mavlink.return_to_home()
        
        elif action == FenceAction.LOITER:
            # Send loiter command
            logger.info("Sending LOITER command to iNav...")
            self.mavlink.set_mode("LOITER")
        
        elif action == FenceAction.LAND:
            # Send land command
            logger.info("Sending LAND command to iNav...")
            self.mavlink.land()
        
        elif action == FenceAction.GUIDED_RETURN:
            # Calculate safe return point and navigate
            logger.info("Calculating safe return point...")
            safe_point = self.system.get_safe_return_point(self.current_position)
            
            if safe_point:
                logger.info(f"Navigating to safe point: {safe_point}")
                # Send guided waypoint to safe point
                self.mavlink.send_waypoint(safe_point.lat, safe_point.lon, self.current_altitude)
            else:
                # Fallback to RTH
                logger.warning("No safe return point found, executing RTH")
                self.mavlink.return_to_home()


# Preset geofence templates
class GeofenceTemplates:
    """Pre-defined geofence shapes"""
    
    @staticmethod
    def create_star_exclusion(center: GeoPoint, radius: float = 100.0, name: str = "Star Zone") -> GeoFence:
        """Create star-shaped exclusion zone (e.g., around military base)"""
        points = []
        n_points = 10  # 5-pointed star = 10 vertices
        
        for i in range(n_points):
            angle = (2 * math.pi * i / n_points) - math.pi / 2  # Start from top
            
            # Alternate between outer and inner radius
            r = radius if i % 2 == 0 else radius * 0.4
            
            # Calculate point
            lat_offset = r * math.cos(angle) / 111000
            lon_offset = r * math.sin(angle) / (111000 * math.cos(math.radians(center.lat)))
            
            points.append(GeoPoint(center.lat + lat_offset, center.lon + lon_offset))
        
        return GeoFence(name, points, is_exclusion=True)
    
    @staticmethod
    def create_circular_exclusion(center: GeoPoint, radius: float = 50.0, 
                                  name: str = "Circular Zone", segments: int = 16) -> GeoFence:
        """Create circular exclusion zone"""
        points = []
        
        for i in range(segments):
            angle = 2 * math.pi * i / segments
            
            lat_offset = radius * math.cos(angle) / 111000
            lon_offset = radius * math.sin(angle) / (111000 * math.cos(math.radians(center.lat)))
            
            points.append(GeoPoint(center.lat + lat_offset, center.lon + lon_offset))
        
        return GeoFence(name, points, is_exclusion=True)
    
    @staticmethod
    def create_rectangle_exclusion(southwest: GeoPoint, northeast: GeoPoint, 
                                   name: str = "Rectangle Zone") -> GeoFence:
        """Create rectangular exclusion zone"""
        points = [
            GeoPoint(southwest.lat, southwest.lon),  # SW
            GeoPoint(southwest.lat, northeast.lon),  # SE
            GeoPoint(northeast.lat, northeast.lon),  # NE
            GeoPoint(northeast.lat, southwest.lon),  # NW
        ]
        
        return GeoFence(name, points, is_exclusion=True)


# Example usage
if __name__ == "__main__":
    print("=== Geofencing System Test ===\n")
    
    # Home position (example: Hanoi)
    home = GeoPoint(21.028511, 105.804817)
    
    # Create geofencing system
    geo_system = GeofencingSystem(home, max_distance=1000.0)
    
    # Create star-shaped exclusion zone (military base)
    military_base = GeoPoint(21.030, 105.806)
    star_fence = GeofenceTemplates.create_star_exclusion(
        military_base, 
        radius=150.0, 
        name="Military Base"
    )
    geo_system.add_fence(star_fence)
    
    # Create circular exclusion zone (restricted area)
    restricted = GeoPoint(21.027, 105.803)
    circle_fence = GeofenceTemplates.create_circular_exclusion(
        restricted,
        radius=80.0,
        name="Restricted Area"
    )
    geo_system.add_fence(circle_fence)
    
    # Test positions
    test_positions = [
        (GeoPoint(21.029, 105.805), 50.0, "Safe position"),
        (GeoPoint(21.030, 105.806), 50.0, "Inside star zone"),
        (GeoPoint(21.027, 105.803), 50.0, "Inside circle zone"),
        (GeoPoint(21.040, 105.810), 50.0, "Too far from home"),
    ]
    
    print("Testing positions:\n")
    for pos, alt, description in test_positions:
        is_safe, message, action = geo_system.check_position(pos, alt)
        
        status = "✓ SAFE" if is_safe else "✗ BREACH"
        print(f"{status} - {description}")
        print(f"  Position: {pos}")
        print(f"  Message: {message}")
        if action:
            print(f"  Action: {action.value}")
        print()
    
    # Save to file
    geo_system.save_to_file("geofence_config.json")
    print("✓ Geofence configuration saved to geofence_config.json")
