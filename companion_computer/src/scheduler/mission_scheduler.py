"""
Mission Scheduler - Hệ thống trinh sát định kỳ
Tự động cất cánh, thực hiện mission, và hạ cánh theo lịch đặt sẵn
"""

import time
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
from loguru import logger

try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False
    logger.warning("schedule library not available. Install: pip install schedule")


class MissionStatus(Enum):
    """Mission execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass
class ScheduledMission:
    """Scheduled mission definition"""
    name: str
    mission_file: str  # Path to mission waypoint file
    schedule_time: str  # Time in "HH:MM" format or cron-like
    enabled: bool = True
    repeat_daily: bool = True
    
    # Mission parameters
    takeoff_altitude: float = 10.0  # meters
    cruise_altitude: float = 50.0
    cruise_speed: float = 15.0  # m/s
    capture_images: bool = True
    upload_to_server: bool = True
    
    # Safety parameters
    max_duration_minutes: int = 30
    min_battery_percent: int = 30
    max_wind_speed: float = 10.0  # m/s
    require_gps_lock: bool = True
    min_satellites: int = 8
    
    # Execution tracking
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    last_status: MissionStatus = MissionStatus.PENDING
    last_error: Optional[str] = None
    
    # Callbacks
    on_start: Optional[Callable] = None
    on_complete: Optional[Callable] = None
    on_fail: Optional[Callable] = None


class MissionScheduler:
    """Automatic mission scheduler"""
    
    def __init__(self, mavlink_handler, camera_interface=None, 
                 http_client=None, data_logger=None):
        """
        Initialize mission scheduler
        
        Args:
            mavlink_handler: MAVLink handler for FC communication
            camera_interface: Camera for image capture
            http_client: HTTP client for data upload
            data_logger: Data logger
        """
        self.mavlink = mavlink_handler
        self.camera = camera_interface
        self.http_client = http_client
        self.logger = data_logger
        
        self.missions: List[ScheduledMission] = []
        self.is_running = False
        self.scheduler_thread: Optional[threading.Thread] = None
        
        # Current mission tracking
        self.current_mission: Optional[ScheduledMission] = None
        self.mission_start_time: Optional[datetime] = None
        
        # Safety state
        self.is_armed = False
        self.is_flying = False
        self.gps_lock = False
        self.gps_satellites = 0
        self.battery_percent = 100
        self.wind_speed = 0.0
        
        logger.info("📅 Mission Scheduler initialized")
    
    def add_mission(self, mission: ScheduledMission):
        """Add scheduled mission"""
        if not SCHEDULE_AVAILABLE:
            logger.error("schedule library not available")
            return False
        
        self.missions.append(mission)
        
        # Schedule the mission
        if mission.repeat_daily:
            schedule.every().day.at(mission.schedule_time).do(
                self._execute_mission_wrapper, mission
            )
            logger.info(f"📅 Scheduled daily mission '{mission.name}' at {mission.schedule_time}")
        else:
            # One-time mission
            logger.info(f"📅 Added one-time mission '{mission.name}'")
        
        return True
    
    def remove_mission(self, mission_name: str) -> bool:
        """Remove scheduled mission"""
        for mission in self.missions:
            if mission.name == mission_name:
                mission.enabled = False
                self.missions.remove(mission)
                logger.info(f"📅 Removed mission '{mission_name}'")
                return True
        return False
    
    def start_scheduler(self):
        """Start the scheduler background thread"""
        if not SCHEDULE_AVAILABLE:
            logger.error("Cannot start scheduler: schedule library not available")
            return False
        
        if self.is_running:
            logger.warning("Scheduler already running")
            return False
        
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        logger.success("📅 Mission Scheduler STARTED")
        return True
    
    def stop_scheduler(self):
        """Stop the scheduler"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=2.0)
        
        logger.info("📅 Mission Scheduler STOPPED")
    
    def _scheduler_loop(self):
        """Scheduler background loop"""
        while self.is_running:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
    
    def _execute_mission_wrapper(self, mission: ScheduledMission):
        """Wrapper to execute mission (called by scheduler)"""
        if not mission.enabled:
            logger.info(f"Mission '{mission.name}' disabled, skipping")
            return
        
        if self.current_mission is not None:
            logger.warning(f"Mission '{mission.name}' skipped: another mission running")
            return
        
        logger.info(f"📅 Executing scheduled mission: {mission.name}")
        
        # Execute in separate thread to not block scheduler
        mission_thread = threading.Thread(
            target=self._execute_mission,
            args=(mission,),
            daemon=True
        )
        mission_thread.start()
    
    def _execute_mission(self, mission: ScheduledMission):
        """Execute a complete mission"""
        self.current_mission = mission
        self.mission_start_time = datetime.now()
        mission.last_run = self.mission_start_time
        mission.run_count += 1
        
        try:
            # Phase 1: Pre-flight checks
            logger.info(f"🔍 Pre-flight checks for '{mission.name}'")
            if not self._pre_flight_checks(mission):
                raise Exception("Pre-flight checks failed")
            
            # Phase 2: Arm and takeoff
            logger.info(f"🚁 Arming and takeoff to {mission.takeoff_altitude}m")
            if not self._arm_and_takeoff(mission.takeoff_altitude):
                raise Exception("Takeoff failed")
            
            # Phase 3: Load and execute mission
            logger.info(f"📍 Loading mission from {mission.mission_file}")
            if not self._load_mission_waypoints(mission.mission_file):
                raise Exception("Failed to load mission")
            
            logger.info(f"✈️ Executing mission waypoints")
            mission.last_status = MissionStatus.RUNNING
            if not self._execute_waypoint_mission(mission):
                raise Exception("Mission execution failed")
            
            # Phase 4: Return to home
            logger.info(f"🏠 Returning to home")
            if not self._return_to_home():
                raise Exception("RTH failed")
            
            # Phase 5: Land
            logger.info(f"🛬 Landing")
            if not self._land_and_disarm():
                raise Exception("Landing failed")
            
            # Phase 6: Post-mission tasks
            logger.info(f"📤 Post-mission tasks")
            self._post_mission_tasks(mission)
            
            # Success
            mission.last_status = MissionStatus.COMPLETED
            logger.success(f"✅ Mission '{mission.name}' completed successfully")
            
            if mission.on_complete:
                mission.on_complete(mission)
        
        except Exception as e:
            mission.last_status = MissionStatus.FAILED
            mission.last_error = str(e)
            logger.error(f"❌ Mission '{mission.name}' failed: {e}")
            
            # Emergency procedures
            self._emergency_abort()
            
            if mission.on_fail:
                mission.on_fail(mission, str(e))
        
        finally:
            self.current_mission = None
            self.is_flying = False
    
    def _pre_flight_checks(self, mission: ScheduledMission) -> bool:
        """Perform pre-flight checks"""
        checks_passed = True
        
        # Check 1: GPS lock
        if mission.require_gps_lock and not self.gps_lock:
            logger.error("❌ No GPS lock")
            checks_passed = False
        
        # Check 2: GPS satellites
        if self.gps_satellites < mission.min_satellites:
            logger.error(f"❌ Insufficient satellites: {self.gps_satellites} < {mission.min_satellites}")
            checks_passed = False
        
        # Check 3: Battery
        if self.battery_percent < mission.min_battery_percent:
            logger.error(f"❌ Low battery: {self.battery_percent}% < {mission.min_battery_percent}%")
            checks_passed = False
        
        # Check 4: Wind speed
        if self.wind_speed > mission.max_wind_speed:
            logger.error(f"❌ High wind: {self.wind_speed}m/s > {mission.max_wind_speed}m/s")
            checks_passed = False
        
        # Check 5: Already flying
        if self.is_flying:
            logger.error("❌ Already flying")
            checks_passed = False
        
        if checks_passed:
            logger.success("✅ All pre-flight checks passed")
        
        return checks_passed
    
    def _arm_and_takeoff(self, altitude: float) -> bool:
        """Arm motors and takeoff"""
        try:
            # Arm
            logger.info("Arming motors...")
            self.mavlink.send_arm()
            time.sleep(2)
            
            # Takeoff
            logger.info(f"Taking off to {altitude}m...")
            self.mavlink.send_takeoff(altitude)
            
            # Wait for altitude
            timeout = 30  # seconds
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                # In real implementation, check actual altitude from telemetry
                time.sleep(1)
                
                # Simplified: assume takeoff successful after 10s
                if time.time() - start_time > 10:
                    self.is_armed = True
                    self.is_flying = True
                    logger.success("✅ Takeoff complete")
                    return True
            
            logger.error("Takeoff timeout")
            return False
            
        except Exception as e:
            logger.error(f"Arm/takeoff failed: {e}")
            return False
    
    def _load_mission_waypoints(self, mission_file: str) -> bool:
        """Load mission waypoints from file"""
        try:
            # Load waypoint file (QGC WPL format)
            # Real implementation would parse and upload to FC
            logger.info(f"Loading waypoints from {mission_file}")
            
            # Simplified: assume success
            return True
            
        except Exception as e:
            logger.error(f"Failed to load mission: {e}")
            return False
    
    def _execute_waypoint_mission(self, mission: ScheduledMission) -> bool:
        """Execute waypoint mission"""
        try:
            # Set mode to AUTO
            self.mavlink.set_mode("AUTO")
            
            # Monitor mission progress
            start_time = time.time()
            max_duration = mission.max_duration_minutes * 60
            
            while time.time() - start_time < max_duration:
                # Check if mission complete
                # Real implementation: check current waypoint vs total
                
                # Capture images if enabled
                if mission.capture_images and self.camera:
                    # Capture every 5 seconds
                    if int(time.time()) % 5 == 0:
                        self._capture_and_log_image()
                
                # Check for abort conditions
                if self.battery_percent < 20:
                    logger.warning("Low battery, aborting mission")
                    return False
                
                time.sleep(1)
                
                # Simplified: assume complete after 60 seconds
                if time.time() - start_time > 60:
                    logger.success("Mission waypoints completed")
                    return True
            
            logger.warning("Mission timeout")
            return False
            
        except Exception as e:
            logger.error(f"Mission execution error: {e}")
            return False
    
    def _capture_and_log_image(self):
        """Capture image with GPS tag"""
        try:
            if self.camera is None:
                return
            
            frame = self.camera.capture_frame()
            if frame is not None:
                # Save with timestamp and GPS
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"mission_{timestamp}.jpg"
                
                # Save locally
                import cv2
                cv2.imwrite(f"logs/{filename}", frame)
                
                # Upload if enabled
                if self.http_client:
                    # Queue for upload
                    pass
                
                logger.debug(f"Captured image: {filename}")
                
        except Exception as e:
            logger.error(f"Image capture error: {e}")
    
    def _return_to_home(self) -> bool:
        """Return to home position"""
        try:
            logger.info("Initiating RTH...")
            self.mavlink.return_to_home()
            
            # Wait for RTH to complete
            time.sleep(20)  # Simplified
            
            logger.success("✅ RTH complete")
            return True
            
        except Exception as e:
            logger.error(f"RTH failed: {e}")
            return False
    
    def _land_and_disarm(self) -> bool:
        """Land and disarm"""
        try:
            logger.info("Landing...")
            self.mavlink.land()
            
            # Wait for landing
            time.sleep(10)  # Simplified
            
            # Disarm
            logger.info("Disarming...")
            self.mavlink.send_disarm()
            
            self.is_armed = False
            self.is_flying = False
            
            logger.success("✅ Landed and disarmed")
            return True
            
        except Exception as e:
            logger.error(f"Landing failed: {e}")
            return False
    
    def _post_mission_tasks(self, mission: ScheduledMission):
        """Post-mission tasks (upload data, etc.)"""
        try:
            if mission.upload_to_server and self.http_client:
                logger.info("Uploading mission data to server...")
                # Upload logs, images, etc.
                # Real implementation: bulk upload
                time.sleep(2)  # Simulate upload
                logger.success("✅ Data uploaded")
            
        except Exception as e:
            logger.error(f"Post-mission tasks failed: {e}")
    
    def _emergency_abort(self):
        """Emergency abort procedure"""
        logger.error("🚨 EMERGENCY ABORT")
        
        try:
            if self.is_flying:
                # Try RTH first
                logger.warning("Attempting emergency RTH...")
                self.mavlink.return_to_home()
                time.sleep(5)
                
                # If still flying after 30s, emergency land
                # In real implementation, check altitude
        
        except Exception as e:
            logger.error(f"Emergency abort failed: {e}")
    
    def update_telemetry(self, gps_lock: bool, satellites: int, 
                        battery_percent: int, wind_speed: float):
        """Update telemetry for safety checks"""
        self.gps_lock = gps_lock
        self.gps_satellites = satellites
        self.battery_percent = battery_percent
        self.wind_speed = wind_speed
    
    def get_mission_status(self, mission_name: str) -> Optional[Dict]:
        """Get status of a mission"""
        for mission in self.missions:
            if mission.name == mission_name:
                return {
                    "name": mission.name,
                    "enabled": mission.enabled,
                    "last_run": mission.last_run.isoformat() if mission.last_run else None,
                    "next_run": mission.next_run.isoformat() if mission.next_run else None,
                    "run_count": mission.run_count,
                    "last_status": mission.last_status.value,
                    "last_error": mission.last_error
                }
        return None
    
    def list_missions(self) -> List[Dict]:
        """List all scheduled missions"""
        return [
            {
                "name": m.name,
                "schedule": m.schedule_time,
                "enabled": m.enabled,
                "repeat_daily": m.repeat_daily,
                "last_status": m.last_status.value,
                "run_count": m.run_count
            }
            for m in self.missions
        ]


# Example usage
if __name__ == "__main__":
    print("=== Mission Scheduler Test ===\n")
    
    if not SCHEDULE_AVAILABLE:
        print("ERROR: schedule library not installed")
        print("Install: pip install schedule")
        exit(1)
    
    # Mock handlers
    class MockMAVLink:
        def send_arm(self): print("→ ARM")
        def send_disarm(self): print("→ DISARM")
        def send_takeoff(self, alt): print(f"→ TAKEOFF {alt}m")
        def land(self): print("→ LAND")
        def return_to_home(self): print("→ RTH")
        def set_mode(self, mode): print(f"→ MODE {mode}")
    
    mavlink = MockMAVLink()
    
    # Create scheduler
    scheduler = MissionScheduler(mavlink)
    scheduler.update_telemetry(gps_lock=True, satellites=12, battery_percent=100, wind_speed=3.0)
    
    # Add test mission
    mission = ScheduledMission(
        name="Morning Patrol",
        mission_file="missions/patrol.txt",
        schedule_time="06:00",
        repeat_daily=True,
        takeoff_altitude=10.0,
        cruise_altitude=50.0,
        capture_images=True,
        upload_to_server=True
    )
    
    scheduler.add_mission(mission)
    
    # List missions
    print("Scheduled missions:")
    for m in scheduler.list_missions():
        print(f"  • {m['name']} at {m['schedule']} ({'enabled' if m['enabled'] else 'disabled'})")
    
    print("\nScheduler ready. Missions will execute at scheduled times.")
    print("For immediate test, use: scheduler._execute_mission(mission)")
