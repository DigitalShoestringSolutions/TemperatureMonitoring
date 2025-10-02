
"""Configure analysis module for temperature monitoring.

Compares temperature readings to thresholds and posts alert 

"""

import logging

# Internal module imports
from trigger.engine import TriggerEngine
import config_manager
import paho.mqtt.publish as pahopublish
import json


# Parse command-line arguments and configure logging again based on those
args = config_manager.handle_args()
logging.basicConfig(level=args["log_level"])
logger = logging.getLogger(__name__)

# Load configuration from config files
config = config_manager.get_config(
    args.get("module_config_file"), args.get("user_config_file")
)

# Initialize the trigger engine with loaded configuration
trigger = TriggerEngine(config)

## -------------

# Default value for global variable
OldAlertVal = 0

# Main function
@trigger.mqtt.event("temperature_monitoring/#")
async def threshlds(topic, payload, config={}):
    """Receives an MQTT message, compares the contained temperature reading to thresholds and send a new MQTT message with the topic suffix `/alerts`
    
    :param str topic:    The resolved topic of the incomming MQTT message
    :param dict payload: The payload of the incomming MQTT message, expecting json loaded as dict
    :param dict config:  The module config
    """
    global OldAlertVal # allow this func to save previous value in global variable

    # extract machine name and temperature reading from payload
    machine = payload["machine"]
    temperature = float(payload["temperature"])

    # extract thresholds from machine-specific config
    high_threshold = float(config["high_thresholds"]["machines"].get(machine, config["high_thresholds"]["default"]))
    low_threshold = float(config["low_thresholds"]["machines"].get(machine, config["low_thresholds"]["default"]))

    # compare temperature reading to thresholds
    if temperature > high_threshold:
        AlertVal = 1
    elif temperature < low_threshold:
        AlertVal = -1
    else:
        AlertVal = 0

    # iif results have changed, publish result
    if AlertVal != OldAlertVal:
        output_payload = {
            "timestamp"     : payload["timestamp"], # directly recycle
            "machine"       : machine,
            "AlertVal"      : AlertVal,
            "ThresholdLow"  : low_threshold,
            "ThresholdHigh" : high_threshold,
        }
        pahopublish.single(topic=topic + "/alerts", payload=json.dumps(output_payload), hostname=config.get("output_broker", "mqtt.docker.local"), retain=True)
    else:
        pass # New message would be a repeat of the old, don't spam. Sounds like a good idea until the broker crashes and loses the retained message.

    # Save result for next time
    OldAlertVal = AlertVal
