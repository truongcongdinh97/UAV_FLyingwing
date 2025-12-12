"""
Communication module initialization
"""

from .serial_comm import SerialCommunication
from .mavlink_handler import MAVLinkHandler

__all__ = ['SerialCommunication', 'MAVLinkHandler']
