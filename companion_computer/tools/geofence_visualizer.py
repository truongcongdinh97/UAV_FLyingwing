"""
Geofence Map Visualizer
Visualize geofences on interactive map with Folium
"""

import folium
from folium import plugins
import webbrowser
import tempfile
from typing import List

try:
    from safety.geofencing import GeoPoint, GeoFence, GeofencingSystem
    from loguru import logger
except ImportError:
    print("Run from companion_computer directory")
    exit(1)


class GeofenceMapVisualizer:
    """Visualize geofences on interactive map"""
    
    def __init__(self, geofencing_system: GeofencingSystem):
        self.system = geofencing_system
    
    def create_map(self) -> folium.Map:
        """Create interactive map with geofences"""
        # Center on home
        m = folium.Map(
            location=[self.system.home.lat, self.system.home.lon],
            zoom_start=15,
            tiles='OpenStreetMap'
        )
        
        # Add satellite layer
        folium.TileLayer('Esri.WorldImagery', name='Satellite').add_to(m)
        
        # Add home marker
        folium.Marker(
            [self.system.home.lat, self.system.home.lon],
            popup='<b>HOME</b><br>Launch Position',
            tooltip='Home Position',
            icon=folium.Icon(color='green', icon='home', prefix='fa')
        ).add_to(m)
        
        # Add max distance circle
        folium.Circle(
            location=[self.system.home.lat, self.system.home.lon],
            radius=self.system.max_distance,
            popup=f'Max Distance: {self.system.max_distance}m',
            color='blue',
            fill=False,
            weight=2,
            dashArray='10, 5'
        ).add_to(m)
        
        # Add each geofence
        for fence in self.system.fences:
            self._add_fence_to_map(m, fence)
        
        # Add drawing tools
        plugins.Draw(
            export=True,
            position='topleft',
            draw_options={
                'polyline': False,
                'rectangle': True,
                'circle': True,
                'circlemarker': False,
                'polygon': True,
                'marker': False
            }
        ).add_to(m)
        
        # Add measure control
        plugins.MeasureControl(position='bottomleft', primary_length_unit='meters').add_to(m)
        
        # Add fullscreen option
        plugins.Fullscreen(position='topright').add_to(m)
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        return m
    
    def _add_fence_to_map(self, m: folium.Map, fence: GeoFence):
        """Add single geofence to map"""
        # Get coordinates
        coords = [[p.lat, p.lon] for p in fence.points]
        
        # Color based on type
        if fence.is_exclusion:
            color = 'red'
            fill_color = 'red'
            fill_opacity = 0.2
            icon_color = 'red'
            fence_type = "NO-FLY ZONE"
        else:
            color = 'green'
            fill_color = 'green'
            fill_opacity = 0.1
            icon_color = 'green'
            fence_type = "MUST-FLY ZONE"
        
        # Create polygon
        folium.Polygon(
            locations=coords,
            popup=f'<b>{fence.name}</b><br>{fence_type}<br>Alt: {fence.altitude_min}-{fence.altitude_max}m',
            tooltip=fence.name,
            color=color,
            fill=True,
            fill_color=fill_color,
            fill_opacity=fill_opacity,
            weight=3
        ).add_to(m)
        
        # Add label at center
        center_lat = sum(p.lat for p in fence.points) / len(fence.points)
        center_lon = sum(p.lon for p in fence.points) / len(fence.points)
        
        folium.Marker(
            [center_lat, center_lon],
            icon=folium.DivIcon(
                html=f'<div style="font-size: 10pt; color: {color}; font-weight: bold; '
                     f'text-align: center; background: white; padding: 2px 5px; '
                     f'border: 2px solid {color}; border-radius: 3px;">'
                     f'{fence.name}</div>'
            )
        ).add_to(m)
    
    def show_map(self):
        """Generate and open map in browser"""
        m = self.create_map()
        
        # Save to temp file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w')
        m.save(temp_file.name)
        temp_file.close()
        
        logger.info(f"Map saved to {temp_file.name}")
        
        # Open in browser
        webbrowser.open('file://' + temp_file.name)
        logger.success("Map opened in browser")
        
        return temp_file.name
    
    def save_map(self, filename: str = "geofence_map.html"):
        """Save map to file"""
        m = self.create_map()
        m.save(filename)
        logger.success(f"Map saved to {filename}")


# Example usage
if __name__ == "__main__":
    from safety.geofencing import GeofenceTemplates
    
    print("=== Geofence Map Visualizer ===\n")
    
    # Create system
    home = GeoPoint(21.028511, 105.804817)
    geo_system = GeofencingSystem(home, max_distance=1000.0)
    
    # Add example fences
    # 1. Star-shaped military base
    military = GeoPoint(21.030, 105.806)
    star = GeofenceTemplates.create_star_exclusion(military, radius=150.0, name="Military Base ⭐")
    geo_system.add_fence(star)
    
    # 2. Circular restricted area
    restricted = GeoPoint(21.027, 105.803)
    circle = GeofenceTemplates.create_circular_exclusion(restricted, radius=80.0, name="Restricted Area 🚫")
    geo_system.add_fence(circle)
    
    # 3. Rectangular airport zone
    sw = GeoPoint(21.029, 105.808)
    ne = GeoPoint(21.031, 105.810)
    rect = GeofenceTemplates.create_rectangle_exclusion(sw, ne, name="Airport Zone ✈️")
    geo_system.add_fence(rect)
    
    # Visualize
    visualizer = GeofenceMapVisualizer(geo_system)
    visualizer.show_map()
    
    print("\n✓ Map opened in browser!")
    print("\nFeatures:")
    print("  • Green home marker")
    print("  • Blue max distance circle")
    print("  • Red exclusion zones (no-fly)")
    print("  • Drawing tools (top-left)")
    print("  • Measurement tools (bottom-left)")
