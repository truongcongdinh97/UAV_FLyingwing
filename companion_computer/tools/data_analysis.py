"""
Data Analysis Tools for UAV Telemetry
Analyze flight logs, plot trajectories, and generate reports
"""

import os
import json
import csv
from datetime import datetime
from typing import List, Dict, Tuple
import matplotlib.pyplot as plt
import numpy as np


class FlightDataAnalyzer:
    """Analyze flight telemetry data"""
    
    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        self.telemetry_data = []
        self.gps_data = []
        self.events = []
        
    def load_session(self, session_id: str):
        """Load all data from a flight session"""
        session_path = os.path.join(self.log_dir, session_id)
        
        # Load telemetry
        telemetry_file = os.path.join(session_path, "telemetry.csv")
        if os.path.exists(telemetry_file):
            with open(telemetry_file, 'r') as f:
                reader = csv.DictReader(f)
                self.telemetry_data = list(reader)
        
        # Load GPS
        gps_file = os.path.join(session_path, "gps.csv")
        if os.path.exists(gps_file):
            with open(gps_file, 'r') as f:
                reader = csv.DictReader(f)
                self.gps_data = list(reader)
        
        # Load events
        events_file = os.path.join(session_path, "events.csv")
        if os.path.exists(events_file):
            with open(events_file, 'r') as f:
                reader = csv.DictReader(f)
                self.events = list(reader)
        
        print(f"Loaded: {len(self.telemetry_data)} telemetry, "
              f"{len(self.gps_data)} GPS, {len(self.events)} events")
    
    def calculate_flight_time(self) -> float:
        """Calculate total flight time in seconds"""
        if not self.telemetry_data:
            return 0.0
        
        start = datetime.fromisoformat(self.telemetry_data[0]['timestamp'])
        end = datetime.fromisoformat(self.telemetry_data[-1]['timestamp'])
        return (end - start).total_seconds()
    
    def calculate_max_altitude(self) -> float:
        """Get maximum altitude reached"""
        if not self.telemetry_data:
            return 0.0
        
        altitudes = [float(d['altitude']) for d in self.telemetry_data if 'altitude' in d]
        return max(altitudes) if altitudes else 0.0
    
    def calculate_average_speed(self) -> float:
        """Calculate average speed"""
        if not self.telemetry_data:
            return 0.0
        
        speeds = [float(d['speed']) for d in self.telemetry_data if 'speed' in d]
        return sum(speeds) / len(speeds) if speeds else 0.0
    
    def calculate_battery_consumption(self) -> Tuple[float, float]:
        """Calculate battery used (voltage drop and current integral)"""
        if not self.telemetry_data:
            return 0.0, 0.0
        
        start_voltage = float(self.telemetry_data[0].get('battery_voltage', 16.8))
        end_voltage = float(self.telemetry_data[-1].get('battery_voltage', 16.8))
        voltage_drop = start_voltage - end_voltage
        
        # Integrate current over time (approximate mAh)
        total_mah = 0.0
        for i in range(1, len(self.telemetry_data)):
            current = float(self.telemetry_data[i].get('battery_current', 0))
            dt = (datetime.fromisoformat(self.telemetry_data[i]['timestamp']) - 
                  datetime.fromisoformat(self.telemetry_data[i-1]['timestamp'])).total_seconds()
            total_mah += current * (dt / 3600) * 1000  # A * h * 1000 = mAh
        
        return voltage_drop, total_mah
    
    def calculate_distance_traveled(self) -> float:
        """Calculate total distance from GPS data (meters)"""
        if len(self.gps_data) < 2:
            return 0.0
        
        total_distance = 0.0
        for i in range(1, len(self.gps_data)):
            lat1 = float(self.gps_data[i-1]['latitude'])
            lon1 = float(self.gps_data[i-1]['longitude'])
            lat2 = float(self.gps_data[i]['latitude'])
            lon2 = float(self.gps_data[i]['longitude'])
            
            # Haversine formula
            R = 6371000  # Earth radius in meters
            phi1 = np.radians(lat1)
            phi2 = np.radians(lat2)
            delta_phi = np.radians(lat2 - lat1)
            delta_lambda = np.radians(lon2 - lon1)
            
            a = np.sin(delta_phi/2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda/2)**2
            c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
            distance = R * c
            
            total_distance += distance
        
        return total_distance
    
    def plot_altitude_profile(self, save_path: str = None):
        """Plot altitude over time"""
        if not self.telemetry_data:
            print("No telemetry data")
            return
        
        times = [(datetime.fromisoformat(d['timestamp']) - 
                  datetime.fromisoformat(self.telemetry_data[0]['timestamp'])).total_seconds()
                 for d in self.telemetry_data]
        altitudes = [float(d['altitude']) for d in self.telemetry_data if 'altitude' in d]
        
        plt.figure(figsize=(12, 6))
        plt.plot(times, altitudes, 'b-', linewidth=2)
        plt.xlabel('Time (seconds)')
        plt.ylabel('Altitude (m)')
        plt.title('Altitude Profile')
        plt.grid(True, alpha=0.3)
        
        # Mark events
        for event in self.events:
            event_time = (datetime.fromisoformat(event['timestamp']) - 
                         datetime.fromisoformat(self.telemetry_data[0]['timestamp'])).total_seconds()
            plt.axvline(x=event_time, color='r', linestyle='--', alpha=0.5)
            plt.text(event_time, max(altitudes)*0.9, event['event'], rotation=90)
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def plot_battery_usage(self, save_path: str = None):
        """Plot battery voltage and current over time"""
        if not self.telemetry_data:
            print("No telemetry data")
            return
        
        times = [(datetime.fromisoformat(d['timestamp']) - 
                  datetime.fromisoformat(self.telemetry_data[0]['timestamp'])).total_seconds()
                 for d in self.telemetry_data]
        voltages = [float(d.get('battery_voltage', 0)) for d in self.telemetry_data]
        currents = [float(d.get('battery_current', 0)) for d in self.telemetry_data]
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # Voltage
        ax1.plot(times, voltages, 'g-', linewidth=2)
        ax1.axhline(y=14.0, color='r', linestyle='--', label='Critical (14.0V)')
        ax1.axhline(y=15.0, color='orange', linestyle='--', label='Warning (15.0V)')
        ax1.set_ylabel('Voltage (V)')
        ax1.set_title('Battery Voltage')
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        # Current
        ax2.plot(times, currents, 'b-', linewidth=2)
        ax2.set_xlabel('Time (seconds)')
        ax2.set_ylabel('Current (A)')
        ax2.set_title('Battery Current')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def plot_flight_path(self, save_path: str = None):
        """Plot GPS trajectory on map"""
        if not self.gps_data:
            print("No GPS data")
            return
        
        lats = [float(d['latitude']) for d in self.gps_data]
        lons = [float(d['longitude']) for d in self.gps_data]
        alts = [float(d['altitude']) for d in self.gps_data]
        
        plt.figure(figsize=(10, 10))
        
        # Color by altitude
        scatter = plt.scatter(lons, lats, c=alts, cmap='viridis', s=10)
        plt.colorbar(scatter, label='Altitude (m)')
        
        # Mark start and end
        plt.plot(lons[0], lats[0], 'go', markersize=15, label='Start')
        plt.plot(lons[-1], lats[-1], 'ro', markersize=15, label='End')
        
        plt.xlabel('Longitude')
        plt.ylabel('Latitude')
        plt.title('Flight Path')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.axis('equal')
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def generate_report(self, output_file: str = None):
        """Generate comprehensive flight report"""
        report = []
        report.append("=" * 60)
        report.append("FLIGHT ANALYSIS REPORT")
        report.append("=" * 60)
        report.append("")
        
        # Flight statistics
        flight_time = self.calculate_flight_time()
        max_alt = self.calculate_max_altitude()
        avg_speed = self.calculate_average_speed()
        voltage_drop, mah_used = self.calculate_battery_consumption()
        distance = self.calculate_distance_traveled()
        
        report.append("FLIGHT STATISTICS:")
        report.append(f"  Flight Time: {flight_time:.1f} seconds ({flight_time/60:.1f} minutes)")
        report.append(f"  Max Altitude: {max_alt:.1f} m")
        report.append(f"  Average Speed: {avg_speed:.1f} m/s")
        report.append(f"  Distance Traveled: {distance:.1f} m ({distance/1000:.2f} km)")
        report.append(f"  Battery Voltage Drop: {voltage_drop:.2f} V")
        report.append(f"  Battery Used: {mah_used:.0f} mAh")
        report.append("")
        
        # Events
        report.append("FLIGHT EVENTS:")
        for event in self.events:
            report.append(f"  [{event['timestamp']}] {event['event']}")
        report.append("")
        
        # Performance metrics
        if flight_time > 0:
            efficiency = distance / (mah_used / 1000) if mah_used > 0 else 0
            report.append("PERFORMANCE METRICS:")
            report.append(f"  Efficiency: {efficiency:.2f} m/Ah")
            report.append(f"  Average Current: {(mah_used / (flight_time/3600)):.2f} A")
        
        report_text = "\n".join(report)
        print(report_text)
        
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report_text)
            print(f"\nReport saved to: {output_file}")
        
        return report_text


# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python data_analysis.py <session_id>")
        print("\nAvailable sessions:")
        
        log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
        if os.path.exists(log_dir):
            sessions = [d for d in os.listdir(log_dir) if os.path.isdir(os.path.join(log_dir, d))]
            for session in sessions:
                print(f"  - {session}")
        sys.exit(1)
    
    session_id = sys.argv[1]
    log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    
    analyzer = FlightDataAnalyzer(log_dir)
    analyzer.load_session(session_id)
    
    # Generate plots
    analyzer.plot_altitude_profile(f"altitude_{session_id}.png")
    analyzer.plot_battery_usage(f"battery_{session_id}.png")
    analyzer.plot_flight_path(f"path_{session_id}.png")
    
    # Generate report
    analyzer.generate_report(f"report_{session_id}.txt")
