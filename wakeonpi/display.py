def set_display(state):
    try:
        with open("/sys/class/backlight/10-0045/bl_power", "w") as f:
            f.write("0" if state else "1")
    except Exception as e:
        print(f"Display error: {e}")