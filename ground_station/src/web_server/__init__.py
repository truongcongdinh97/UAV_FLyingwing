"""Web server module for ground station"""

from .app import app, socketio

__all__ = ['app', 'socketio']
