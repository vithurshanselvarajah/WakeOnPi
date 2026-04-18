import time
import cv2
import numpy as np
from datetime import datetime
from . import state, config, system

def set_notification(message, duration=5):
    with state.overlay_lock:
        state.overlay_message = message
        state.overlay_expires = time.time() + duration


def clear_notification():
    with state.overlay_lock:
        state.overlay_message = None
        state.overlay_expires = 0


def get_notification():
    with state.overlay_lock:
        if state.overlay_message and time.time() < state.overlay_expires:
            return state.overlay_message
        return None


def draw_overlay(frame):
    if not config.OVERLAY_ENABLED:
        return frame
    
    h, w = frame.shape[:2]
    overlay = frame.copy()
    position = config.OVERLAY_POSITION or "top-right"
    
    lines = []
    
    if config.OVERLAY_SHOW_TIME:
        lines.append(datetime.now().strftime("%H:%M:%S"))
    
    if config.OVERLAY_SHOW_STATS:
        stats = system.get_stats()
        lines.append(f"CPU: {stats['cpu_usage']}%  {stats['cpu_temp']}°C")
        lines.append(f"MEM: {stats['memory_percent']}%")
        lines.append(f"DISK: {stats['storage_free_gb']}GB free")
    
    notification = get_notification()
    if notification:
        lines.append(notification)
    
    if state.motion_event:
        lines.append("● MOTION")
    
    if not lines:
        return frame
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    thickness = 1
    padding = 8
    line_height = 20
    
    max_width = 0
    for line in lines:
        (tw, th), _ = cv2.getTextSize(line, font, font_scale, thickness)
        max_width = max(max_width, tw)
    
    box_w = max_width + padding * 2
    box_h = len(lines) * line_height + padding * 2
    
    if "top" in position:
        y_start = 10
    else:
        y_start = h - box_h - 10
    
    if "right" in position:
        x_start = w - box_w - 10
    else:
        x_start = 10
    
    cv2.rectangle(overlay, (x_start, y_start), (x_start + box_w, y_start + box_h), (0, 0, 0), -1)
    frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)
    
    for i, line in enumerate(lines):
        y = y_start + padding + (i + 1) * line_height - 5
        color = (0, 255, 0) if "MOTION" in line else (255, 255, 255)
        if notification and line == notification:
            color = (0, 200, 255)
        cv2.putText(frame, line, (x_start + padding, y), font, font_scale, color, thickness, cv2.LINE_AA)
    
    return frame
