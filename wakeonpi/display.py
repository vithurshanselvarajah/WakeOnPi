def set_display(state):
    try:
        from . import config
        import logging

        path = getattr(config, 'BACKLIGHT_PATH', '/sys/class/backlight/10-0045/bl_power')
        with open(path, 'w') as f:
            f.write('0' if state else '1')
    except Exception:
        logging.getLogger('Display').exception('Failed to set backlight')