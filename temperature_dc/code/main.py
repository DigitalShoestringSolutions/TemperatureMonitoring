# ----------------------------------------------------------------------
#
#    Temperature Monitoring (Basic solution) -- This digital solution enables, measures,
#    reports and records different  types of temperatures (contact, air, radiated)
#    so that the temperature conditions surrounding a process can be understood and 
#    taken action upon. Supported sensors include 
#    k-type thermocouples, RTDs, air samplers, and NIR-based sensors.
#    The solution provides a Grafana dashboard that 
#    displays the temperature timeseries, set threshold value, and a state timeline showing 
#    the change in temperature. An InfluxDB database is used to store timestamp, temperature, 
#    threshold and status. 
#
#    Copyright (C) 2022  Shoestring and University of Cambridge
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 3 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see https://www.gnu.org/licenses/.
#
# ----------------------------------------------------------------------

# Check config file is valid
# create BBs
# plumb BBs together
# start BBs
# monitor tasks

# packages
import tomli
import time
import logging
import zmq
import os # for fetching environment variables
# local
import measure
import wrapper

logger = logging.getLogger("main")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')  # move to log config file using python functionality


def get_config(env_var="CONFIG_FILE", default_file_path="./config/config.toml"):

    # If an environment variable is set with the specified key, use it as the path to the config file
    env_file_path = os.getenv(env_var) # returns None if env var not set
    if env_file_path:
        config_file_path = env_file_path
    # If no such environment variable, failover to using specified string directly
    else:
        config_file_path = default_file_path

    # Open the file, parse the contents as toml and return as dictionary
    with open(config_file_path, "rb") as f:
        toml_conf = tomli.load(f)
    logger.info(f"config:{toml_conf}")
    return toml_conf


def create_building_blocks(config):
    bbs = {}

    measure_out = {"type": zmq.PUSH, "address": "tcp://127.0.0.1:4000", "bind": True}
    wrapper_in = {"type": zmq.PULL, "address": "tcp://127.0.0.1:4000", "bind": False}

    bbs["measure"] = measure.TemperatureMeasureBuildingBlock(config, measure_out)
    bbs["wrapper"] = wrapper.MQTTServiceWrapper(config, wrapper_in)

    logger.debug(f"bbs {bbs}")
    return bbs


def start_building_blocks(bbs):
    for key in bbs:
        p = bbs[key].start()



if __name__ == "__main__":
    config = get_config()
    # todo set logging level from config file
    bbs = create_building_blocks(config)
    start_building_blocks(bbs)

