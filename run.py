from wakeonpi import config
from wakeonpi.app import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.SERVICE_PORT, threaded=True)