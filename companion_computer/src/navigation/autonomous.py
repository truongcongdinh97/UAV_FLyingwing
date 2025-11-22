"""
Autonomous Navigation Algorithms
Path planning, obstacle avoidance, and intelligent behaviors
"""

import math
from typing import List, Tuple, Optional
from dataclasses import dataclass
import numpy as np
from loguru import logger


@dataclass
class Position:
    """3D position in GPS coordinates"""
    lat: float
    lon: float
    alt: float  # meters MSL


@dataclass
class Velocity:
    """3D velocity vector"""
    vx: float  # m/s north
    vy: float  # m/s east
    vz: float  # m/s up


class NavigationAlgorithms:
    """Collection of autonomous navigation algorithms"""
    
    @staticmethod
    def distance(pos1: Position, pos2: Position) -> float:
        """Calculate horizontal distance between two positions (meters)"""
        R = 6371000  # Earth radius in meters
        
        lat1, lon1 = math.radians(pos1.lat), math.radians(pos1.lon)
        lat2, lon2 = math.radians(pos2.lat), math.radians(pos2.lon)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    @staticmethod
    def bearing(pos1: Position, pos2: Position) -> float:
        """Calculate bearing from pos1 to pos2 (degrees, 0=North)"""
        lat1, lon1 = math.radians(pos1.lat), math.radians(pos1.lon)
        lat2, lon2 = math.radians(pos2.lat), math.radians(pos2.lon)
        
        dlon = lon2 - lon1
        
        x = math.sin(dlon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        
        bearing = math.atan2(x, y)
        return (math.degrees(bearing) + 360) % 360
    
    @staticmethod
    def destination_point(pos: Position, distance: float, bearing: float) -> Position:
        """Calculate destination point given distance and bearing"""
        R = 6371000  # Earth radius in meters
        
        lat1 = math.radians(pos.lat)
        lon1 = math.radians(pos.lon)
        brng = math.radians(bearing)
        
        lat2 = math.asin(math.sin(lat1) * math.cos(distance/R) +
                        math.cos(lat1) * math.sin(distance/R) * math.cos(brng))
        
        lon2 = lon1 + math.atan2(math.sin(brng) * math.sin(distance/R) * math.cos(lat1),
                                 math.cos(distance/R) - math.sin(lat1) * math.sin(lat2))
        
        return Position(math.degrees(lat2), math.degrees(lon2), pos.alt)
    
    @staticmethod
    def cross_track_error(current: Position, start: Position, end: Position) -> float:
        """
        Calculate cross-track error (distance from current position to line between start and end)
        Positive = right of track, Negative = left of track
        """
        R = 6371000  # Earth radius
        
        d13 = NavigationAlgorithms.distance(start, current) / R
        brng12 = math.radians(NavigationAlgorithms.bearing(start, end))
        brng13 = math.radians(NavigationAlgorithms.bearing(start, current))
        
        dxt = math.asin(math.sin(d13) * math.sin(brng13 - brng12)) * R
        return dxt
    
    @staticmethod
    def along_track_distance(current: Position, start: Position, end: Position) -> float:
        """Calculate distance along track from start"""
        R = 6371000
        
        d13 = NavigationAlgorithms.distance(start, current) / R
        dxt = NavigationAlgorithms.cross_track_error(current, start, end) / R
        
        dat = math.acos(math.cos(d13) / math.cos(dxt)) * R
        return dat


class PathFollower:
    """Path following controller for waypoint navigation"""
    
    def __init__(self, lookahead_distance: float = 20.0, max_bank_angle: float = 30.0):
        self.lookahead_distance = lookahead_distance  # meters
        self.max_bank_angle = max_bank_angle  # degrees
        
        self.current_waypoint_index = 0
        self.waypoints: List[Position] = []
        
    def set_waypoints(self, waypoints: List[Position]):
        """Set waypoint list"""
        self.waypoints = waypoints
        self.current_waypoint_index = 0
        logger.info(f"Path set with {len(waypoints)} waypoints")
    
    def calculate_steering(self, current_pos: Position, current_velocity: Velocity) -> Tuple[float, float]:
        """
        Calculate desired heading and bank angle to follow path
        Returns: (desired_heading, desired_bank_angle)
        """
        if not self.waypoints or self.current_waypoint_index >= len(self.waypoints):
            return 0.0, 0.0
        
        # Get current and next waypoint
        target_wp = self.waypoints[self.current_waypoint_index]
        
        # Check if reached waypoint
        distance_to_wp = NavigationAlgorithms.distance(current_pos, target_wp)
        if distance_to_wp < 10.0:  # Within 10m
            self.current_waypoint_index += 1
            logger.info(f"Reached waypoint {self.current_waypoint_index}")
            
            if self.current_waypoint_index >= len(self.waypoints):
                logger.success("Mission complete!")
                return 0.0, 0.0
            
            target_wp = self.waypoints[self.current_waypoint_index]
        
        # Calculate desired heading to waypoint
        desired_heading = NavigationAlgorithms.bearing(current_pos, target_wp)
        
        # Calculate current heading from velocity
        current_heading = math.degrees(math.atan2(current_velocity.vy, current_velocity.vx))
        current_heading = (current_heading + 360) % 360
        
        # Calculate heading error
        heading_error = desired_heading - current_heading
        
        # Normalize to [-180, 180]
        if heading_error > 180:
            heading_error -= 360
        elif heading_error < -180:
            heading_error += 360
        
        # Calculate bank angle (simple proportional control)
        desired_bank = np.clip(heading_error * 0.5, -self.max_bank_angle, self.max_bank_angle)
        
        return desired_heading, desired_bank
    
    def calculate_altitude_command(self, current_pos: Position) -> float:
        """Calculate desired altitude"""
        if not self.waypoints or self.current_waypoint_index >= len(self.waypoints):
            return current_pos.alt
        
        target_wp = self.waypoints[self.current_waypoint_index]
        return target_wp.alt


class LoiterController:
    """Loiter (circular orbit) controller"""
    
    def __init__(self, center: Position, radius: float = 50.0, clockwise: bool = True):
        self.center = center
        self.radius = radius  # meters
        self.clockwise = clockwise
        
    def calculate_steering(self, current_pos: Position) -> Tuple[float, float]:
        """Calculate heading and bank to maintain loiter"""
        # Calculate bearing to center
        bearing_to_center = NavigationAlgorithms.bearing(current_pos, self.center)
        
        # Calculate distance from center
        distance_from_center = NavigationAlgorithms.distance(current_pos, self.center)
        
        # Calculate tangent heading (perpendicular to radius)
        if self.clockwise:
            tangent_heading = (bearing_to_center + 90) % 360
        else:
            tangent_heading = (bearing_to_center - 90) % 360
        
        # Proportional control to maintain radius
        radius_error = distance_from_center - self.radius
        correction_angle = np.clip(radius_error * 2.0, -30, 30)  # degrees
        
        # Adjust heading based on radius error
        if radius_error > 0:  # Too far from center
            desired_heading = (bearing_to_center + correction_angle) % 360
        else:  # Too close to center
            desired_heading = (tangent_heading - correction_angle) % 360
        
        # Calculate bank angle (for circular motion)
        # Bank angle = atan(v^2 / (r * g))
        # Assuming v = 15 m/s
        v = 15.0
        g = 9.81
        bank_angle = math.degrees(math.atan(v**2 / (self.radius * g)))
        
        if not self.clockwise:
            bank_angle = -bank_angle
        
        return desired_heading, bank_angle


class ObstacleAvoidance:
    """Simple obstacle avoidance using potential fields"""
    
    def __init__(self, obstacle_threshold: float = 30.0, max_avoidance_angle: float = 45.0):
        self.obstacle_threshold = obstacle_threshold  # meters
        self.max_avoidance_angle = max_avoidance_angle  # degrees
        
    def calculate_avoidance_vector(self, current_pos: Position, 
                                   obstacles: List[Position]) -> Tuple[float, float]:
        """
        Calculate avoidance heading correction
        Returns: (avoidance_heading_correction, urgency_factor)
        """
        if not obstacles:
            return 0.0, 0.0
        
        # Calculate repulsive force from obstacles
        total_force_x = 0.0
        total_force_y = 0.0
        
        for obstacle in obstacles:
            distance = NavigationAlgorithms.distance(current_pos, obstacle)
            
            if distance < self.obstacle_threshold:
                # Calculate repulsive force (inverse square law)
                force_magnitude = (self.obstacle_threshold - distance) / self.obstacle_threshold
                force_magnitude = force_magnitude ** 2
                
                # Direction away from obstacle
                bearing_to_obstacle = NavigationAlgorithms.bearing(current_pos, obstacle)
                away_bearing = (bearing_to_obstacle + 180) % 360
                
                # Convert to x, y components
                force_x = force_magnitude * math.cos(math.radians(away_bearing))
                force_y = force_magnitude * math.sin(math.radians(away_bearing))
                
                total_force_x += force_x
                total_force_y += force_y
        
        if total_force_x == 0 and total_force_y == 0:
            return 0.0, 0.0
        
        # Convert force to heading correction
        avoidance_angle = math.degrees(math.atan2(total_force_y, total_force_x))
        avoidance_magnitude = math.sqrt(total_force_x**2 + total_force_y**2)
        
        # Clamp avoidance angle
        avoidance_correction = np.clip(avoidance_angle, 
                                      -self.max_avoidance_angle, 
                                      self.max_avoidance_angle)
        
        return avoidance_correction, min(avoidance_magnitude, 1.0)


class WindEstimator:
    """Estimate wind velocity from ground track and airspeed"""
    
    def __init__(self):
        self.wind_vx = 0.0  # m/s north
        self.wind_vy = 0.0  # m/s east
        self.samples = []
        
    def update(self, ground_velocity: Velocity, airspeed: float, heading: float):
        """Update wind estimate"""
        # Airspeed vector
        air_vx = airspeed * math.cos(math.radians(heading))
        air_vy = airspeed * math.sin(math.radians(heading))
        
        # Wind = Ground velocity - Air velocity
        wind_vx = ground_velocity.vx - air_vx
        wind_vy = ground_velocity.vy - air_vy
        
        # Moving average filter
        self.samples.append((wind_vx, wind_vy))
        if len(self.samples) > 10:
            self.samples.pop(0)
        
        self.wind_vx = sum(s[0] for s in self.samples) / len(self.samples)
        self.wind_vy = sum(s[1] for s in self.samples) / len(self.samples)
    
    def get_wind_speed_direction(self) -> Tuple[float, float]:
        """Get wind speed and direction"""
        speed = math.sqrt(self.wind_vx**2 + self.wind_vy**2)
        direction = math.degrees(math.atan2(self.wind_vy, self.wind_vx))
        direction = (direction + 360) % 360
        
        return speed, direction


# Example usage
if __name__ == "__main__":
    print("=== Navigation Algorithms Test ===\n")
    
    # Test waypoint navigation
    waypoints = [
        Position(21.028, 105.804, 50),
        Position(21.029, 105.805, 60),
        Position(21.030, 105.804, 50),
        Position(21.029, 105.803, 40),
    ]
    
    follower = PathFollower(lookahead_distance=20.0)
    follower.set_waypoints(waypoints)
    
    # Simulate current position
    current = Position(21.0285, 105.8045, 45)
    velocity = Velocity(10, 5, 0)
    
    heading, bank = follower.calculate_steering(current, velocity)
    print(f"Path Following:")
    print(f"  Desired Heading: {heading:.1f}°")
    print(f"  Desired Bank: {bank:.1f}°")
    
    # Test loiter
    print(f"\nLoiter Control:")
    loiter = LoiterController(Position(21.029, 105.804, 50), radius=50, clockwise=True)
    heading, bank = loiter.calculate_steering(current)
    print(f"  Loiter Heading: {heading:.1f}°")
    print(f"  Loiter Bank: {bank:.1f}°")
    
    # Test obstacle avoidance
    print(f"\nObstacle Avoidance:")
    obstacles = [Position(21.0287, 105.8047, 50)]
    avoider = ObstacleAvoidance(obstacle_threshold=30.0)
    correction, urgency = avoider.calculate_avoidance_vector(current, obstacles)
    print(f"  Avoidance Correction: {correction:.1f}°")
    print(f"  Urgency: {urgency:.2f}")
