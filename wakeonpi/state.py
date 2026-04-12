import threading

motion_event = False
last_motion_time = 0
current_frame = None

frame_lock = threading.Lock()

clients_connected = 0
clients_lock = threading.Lock()

main_stream_active = False
main_stream_lock = threading.Lock()

display_on = True
ignore_motion_until = 0