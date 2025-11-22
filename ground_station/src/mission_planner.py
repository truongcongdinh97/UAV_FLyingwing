"""
Mission Planner - Waypoint Editor and Map Interface
Create, edit, and upload waypoints for autonomous flight
"""

import sys
import os
from typing import List, Dict, Tuple
import webbrowser
import tempfile

try:
    import folium
    from folium import plugins
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False
    print("Warning: folium not installed. Install with: pip install folium")

from loguru import logger


class Waypoint:
    """Single waypoint definition"""
    
    def __init__(self, lat: float, lon: float, alt: float = 50.0, 
                 speed: float = 15.0, action: str = "WAYPOINT"):
        self.lat = lat
        self.lon = lon
        self.alt = alt  # meters
        self.speed = speed  # m/s
        self.action = action  # WAYPOINT, LOITER, LAND, RTH
        
    def to_dict(self) -> Dict:
        return {
            "latitude": self.lat,
            "longitude": self.lon,
            "altitude": self.alt,
            "speed": self.speed,
            "action": self.action
        }
    
    def to_mavlink_command(self, seq: int) -> str:
        """Convert to MAVLink mission item format"""
        # MAVLink waypoint: seq, frame, command, current, autocontinue, param1-4, lat, lon, alt
        if self.action == "WAYPOINT":
            cmd = 16  # MAV_CMD_NAV_WAYPOINT
        elif self.action == "LOITER":
            cmd = 17  # MAV_CMD_NAV_LOITER_UNLIM
        elif self.action == "LAND":
            cmd = 21  # MAV_CMD_NAV_LAND
        elif self.action == "RTH":
            cmd = 20  # MAV_CMD_NAV_RETURN_TO_LAUNCH
        else:
            cmd = 16
        
        return f"{seq}\t0\t{cmd}\t0\t1\t0\t0\t0\t0\t{self.lat}\t{self.lon}\t{self.alt}"


class Mission:
    """Collection of waypoints forming a mission"""
    
    def __init__(self, name: str = "New Mission"):
        self.name = name
        self.waypoints: List[Waypoint] = []
        self.home: Tuple[float, float] = (0, 0)  # Set before flight
        
    def add_waypoint(self, wp: Waypoint):
        """Add waypoint to mission"""
        self.waypoints.append(wp)
        logger.info(f"Added waypoint {len(self.waypoints)}: {wp.lat}, {wp.lon}, {wp.alt}m")
    
    def remove_waypoint(self, index: int):
        """Remove waypoint by index"""
        if 0 <= index < len(self.waypoints):
            wp = self.waypoints.pop(index)
            logger.info(f"Removed waypoint {index}")
    
    def clear(self):
        """Clear all waypoints"""
        self.waypoints.clear()
        logger.info("Mission cleared")
    
    def set_home(self, lat: float, lon: float):
        """Set home position"""
        self.home = (lat, lon)
        logger.info(f"Home set: {lat}, {lon}")
    
    def save_to_file(self, filename: str):
        """Save mission to file (MAVLink format)"""
        with open(filename, 'w') as f:
            f.write("QGC WPL 110\n")  # QGroundControl waypoint format
            
            # Home position
            f.write(f"0\t1\t0\t16\t0\t0\t0\t0\t{self.home[0]}\t{self.home[1]}\t0\t1\n")
            
            # Waypoints
            for i, wp in enumerate(self.waypoints, start=1):
                f.write(wp.to_mavlink_command(i) + "\n")
        
        logger.success(f"Mission saved to {filename}")
    
    def load_from_file(self, filename: str):
        """Load mission from file"""
        self.clear()
        
        with open(filename, 'r') as f:
            lines = f.readlines()
            
            for line in lines[1:]:  # Skip header
                parts = line.strip().split('\t')
                if len(parts) >= 12:
                    seq = int(parts[0])
                    cmd = int(parts[2])
                    lat = float(parts[8])
                    lon = float(parts[9])
                    alt = float(parts[10])
                    
                    if seq == 0:  # Home
                        self.set_home(lat, lon)
                    else:
                        # Determine action from command
                        action = "WAYPOINT"
                        if cmd == 17:
                            action = "LOITER"
                        elif cmd == 21:
                            action = "LAND"
                        elif cmd == 20:
                            action = "RTH"
                        
                        wp = Waypoint(lat, lon, alt, action=action)
                        self.add_waypoint(wp)
        
        logger.success(f"Mission loaded from {filename}")
    
    def validate(self) -> Tuple[bool, str]:
        """Validate mission for safety"""
        if len(self.waypoints) == 0:
            return False, "Mission has no waypoints"
        
        if self.home == (0, 0):
            return False, "Home position not set"
        
        # Check altitudes
        for i, wp in enumerate(self.waypoints):
            if wp.alt < 10:
                return False, f"Waypoint {i+1} altitude too low: {wp.alt}m (min 10m)"
            if wp.alt > 150:
                return False, f"Waypoint {i+1} altitude too high: {wp.alt}m (max 150m)"
        
        # Check distances from home
        from math import radians, sin, cos, sqrt, atan2
        R = 6371000  # Earth radius in meters
        
        for i, wp in enumerate(self.waypoints):
            # Calculate distance using Haversine
            lat1, lon1 = radians(self.home[0]), radians(self.home[1])
            lat2, lon2 = radians(wp.lat), radians(wp.lon)
            
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            distance = R * c
            
            if distance > 1000:  # 1km limit
                return False, f"Waypoint {i+1} too far from home: {distance:.0f}m (max 1000m)"
        
        return True, "Mission valid"


class MissionPlanner:
    """Interactive mission planner with map interface"""
    
    def __init__(self, default_location: Tuple[float, float] = (21.028511, 105.804817)):
        self.mission = Mission()
        self.default_location = default_location
        self.map_html = None
    
    def create_map(self, center: Tuple[float, float] = None) -> folium.Map:
        """Create interactive Folium map"""
        if not FOLIUM_AVAILABLE:
            raise RuntimeError("folium not installed")
        
        if center is None:
            center = self.default_location
        
        # Create map
        m = folium.Map(
            location=center,
            zoom_start=15,
            tiles='OpenStreetMap'
        )
        
        # Add satellite layer
        folium.TileLayer('Esri.WorldImagery', name='Satellite').add_to(m)
        
        # Add home marker if set
        if self.mission.home != (0, 0):
            folium.Marker(
                self.mission.home,
                popup='<b>HOME</b>',
                tooltip='Home Position',
                icon=folium.Icon(color='green', icon='home')
            ).add_to(m)
        
        # Add waypoints
        for i, wp in enumerate(self.mission.waypoints):
            # Marker color based on action
            color = 'blue'
            icon = 'info-sign'
            if wp.action == 'LOITER':
                color = 'orange'
                icon = 'refresh'
            elif wp.action == 'LAND':
                color = 'red'
                icon = 'plane'
            elif wp.action == 'RTH':
                color = 'green'
                icon = 'home'
            
            folium.Marker(
                [wp.lat, wp.lon],
                popup=f'<b>WP{i+1}</b><br>Alt: {wp.alt}m<br>Speed: {wp.speed}m/s<br>Action: {wp.action}',
                tooltip=f'Waypoint {i+1}',
                icon=folium.Icon(color=color, icon=icon)
            ).add_to(m)
            
            # Add label
            folium.Marker(
                [wp.lat, wp.lon],
                icon=folium.DivIcon(html=f'<div style="font-size: 12pt; color: blue; font-weight: bold;">{i+1}</div>')
            ).add_to(m)
        
        # Draw path between waypoints
        if len(self.mission.waypoints) > 1:
            path = [[wp.lat, wp.lon] for wp in self.mission.waypoints]
            folium.PolyLine(
                path,
                color='blue',
                weight=2,
                opacity=0.7
            ).add_to(m)
        
        # Add drawing tools
        plugins.Draw(
            export=False,
            position='topleft',
            draw_options={
                'polyline': False,
                'rectangle': False,
                'circle': False,
                'circlemarker': False,
                'polygon': False,
                'marker': True
            }
        ).add_to(m)
        
        # Add measure control
        plugins.MeasureControl(position='bottomleft').add_to(m)
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        # Add click handler (via JavaScript)
        click_js = """
        function onMapClick(e) {
            var popup = L.popup()
                .setLatLng(e.latlng)
                .setContent("Lat: " + e.latlng.lat.toFixed(6) + "<br>Lon: " + e.latlng.lng.toFixed(6) + 
                           "<br><a href='#' onclick='addWaypoint(" + e.latlng.lat + "," + e.latlng.lng + ")'>Add Waypoint</a>")
                .openOn(this);
        }
        
        function addWaypoint(lat, lon) {
            console.log("Add waypoint: " + lat + ", " + lon);
            alert("To add waypoint, use Python console: mission.add_waypoint(Waypoint(" + lat + ", " + lon + ", 50))");
        }
        """
        
        m.get_root().script.add_child(folium.Element(click_js))
        m.get_root().html.add_child(folium.Element('<script>var map = arguments[0]; map.on("click", onMapClick);</script>'))
        
        return m
    
    def show_map(self):
        """Generate and open map in browser"""
        if not FOLIUM_AVAILABLE:
            logger.error("folium not installed")
            return
        
        m = self.create_map()
        
        # Save to temp file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w')
        m.save(temp_file.name)
        temp_file.close()
        
        self.map_html = temp_file.name
        logger.info(f"Map saved to {self.map_html}")
        
        # Open in browser
        webbrowser.open('file://' + temp_file.name)
        logger.success("Map opened in browser")
    
    def add_waypoint_interactive(self):
        """Add waypoint via console input"""
        print("\n=== Add Waypoint ===")
        try:
            lat = float(input("Latitude: "))
            lon = float(input("Longitude: "))
            alt = float(input("Altitude (m) [50]: ") or "50")
            speed = float(input("Speed (m/s) [15]: ") or "15")
            
            print("\nActions: WAYPOINT, LOITER, LAND, RTH")
            action = input("Action [WAYPOINT]: ").upper() or "WAYPOINT"
            
            wp = Waypoint(lat, lon, alt, speed, action)
            self.mission.add_waypoint(wp)
            
            print(f"✓ Added waypoint {len(self.mission.waypoints)}")
            
        except ValueError as e:
            print(f"✗ Invalid input: {e}")
    
    def grid_pattern(self, center: Tuple[float, float], width: float, height: float, 
                     spacing: float = 50, altitude: float = 50):
        """Generate grid/lawnmower pattern for survey"""
        import math
        
        # Convert meters to degrees (approximate)
        lat_per_m = 1 / 111000
        lon_per_m = 1 / (111000 * math.cos(math.radians(center[0])))
        
        # Calculate grid
        rows = int(height / spacing) + 1
        cols = int(width / spacing) + 1
        
        for row in range(rows):
            y_offset = (row - rows/2) * spacing * lat_per_m
            
            # Alternate direction for each row (lawnmower pattern)
            if row % 2 == 0:
                col_range = range(cols)
            else:
                col_range = range(cols-1, -1, -1)
            
            for col in col_range:
                x_offset = (col - cols/2) * spacing * lon_per_m
                
                lat = center[0] + y_offset
                lon = center[1] + x_offset
                
                wp = Waypoint(lat, lon, altitude)
                self.mission.add_waypoint(wp)
        
        logger.success(f"Generated grid pattern: {len(self.mission.waypoints)} waypoints")
    
    def circular_pattern(self, center: Tuple[float, float], radius: float, 
                        points: int = 12, altitude: float = 50):
        """Generate circular pattern for orbit"""
        import math
        
        lat_per_m = 1 / 111000
        lon_per_m = 1 / (111000 * math.cos(math.radians(center[0])))
        
        for i in range(points):
            angle = 2 * math.pi * i / points
            
            x_offset = radius * math.cos(angle) * lon_per_m
            y_offset = radius * math.sin(angle) * lat_per_m
            
            lat = center[0] + y_offset
            lon = center[1] + x_offset
            
            wp = Waypoint(lat, lon, altitude)
            self.mission.add_waypoint(wp)
        
        logger.success(f"Generated circular pattern: {len(self.mission.waypoints)} waypoints")


# Example usage
if __name__ == "__main__":
    print("=== Mission Planner ===\n")
    
    # Create planner
    planner = MissionPlanner(default_location=(21.028511, 105.804817))  # Hanoi
    
    # Set home
    planner.mission.set_home(21.028511, 105.804817)
    
    # Example: Add manual waypoints
    planner.mission.add_waypoint(Waypoint(21.029, 105.805, 50, 15))
    planner.mission.add_waypoint(Waypoint(21.030, 105.806, 60, 15))
    planner.mission.add_waypoint(Waypoint(21.029, 105.807, 50, 15))
    planner.mission.add_waypoint(Waypoint(21.028, 105.806, 40, 15, action="LAND"))
    
    # Or generate pattern
    # planner.grid_pattern((21.029, 105.805), width=200, height=200, spacing=50, altitude=50)
    # planner.circular_pattern((21.029, 105.805), radius=100, points=12, altitude=50)
    
    # Validate
    valid, msg = planner.mission.validate()
    if valid:
        print(f"✓ Mission valid: {msg}")
    else:
        print(f"✗ Mission invalid: {msg}")
    
    # Save mission
    planner.mission.save_to_file("mission_example.txt")
    
    # Show map
    if FOLIUM_AVAILABLE:
        print("\nOpening map in browser...")
        planner.show_map()
        print("Map opened! Add waypoints in Python console:")
        print("  planner.mission.add_waypoint(Waypoint(lat, lon, alt))")
        print("  planner.show_map()  # Refresh map")
    else:
        print("\nInstall folium for interactive map:")
        print("  pip install folium")
