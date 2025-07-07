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

 
# run at poll rate
# make requests
# extract variables
# output variables

import datetime
import logging
import multiprocessing
import time
import sensor_select as sen
import zmq

# logging.basicConfig(filename='/app_temp.log', level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("main.measure") # applies a schema similar to above inherited from main's logger
#logger.setLevel(logging.INFO) # log level is inherited from main's logger, unless it is overwritten here

context = zmq.Context()

 
class TemperatureMeasureBuildingBlock(multiprocessing.Process):
    def __init__(self, config, zmq_conf):
        super().__init__()

        self.config = config
        self.constants = config['constants']

        # declarations
        self.zmq_conf = zmq_conf
        self.zmq_out = None

        self.collection_interval = config['sampling']['sample_interval']
        self.sample_count = config['sampling']['sample_count']



    def do_connect(self):
        self.zmq_out = context.socket(self.zmq_conf['type'])
        if self.zmq_conf["bind"]:
            self.zmq_out.bind(self.zmq_conf["address"])
        else:
            self.zmq_out.connect(self.zmq_conf["address"])

    def run(self):
        logger.info("started run")

        self.do_connect()

        # timezone determination
        __dt = -1 * (time.timezone if (time.localtime().tm_isdst == 0) else time.altzone)
        tz = datetime.timezone(datetime.timedelta(seconds=__dt))
        #
        today = datetime.datetime.now().date()
        next_check = (datetime.datetime(today.year, today.month, today.day) + datetime.timedelta(days=1)).timestamp()

        run = True
        period = self.collection_interval


        # Load user-set thresholds and channel from the config file
        th_low = float(self.config['threshold']['low'])
        th_high = float(self.config['threshold']['high'])
        channel = self.config['sensing'].get('channel', 1) # any device that has multiple channels will include a channel 1, even if zero indexed.

        # Enable the selected sensor
        if self.config['sensing']['adc'] == 'MLX90614':
            sensor = sen.MLX90614()
        elif self.config['sensing']['adc'] == 'W1ThermSensor':
            sensor = sen.W1Therm(channel)
        elif self.config['sensing']['adc'] == 'K-type_DFRobot_MAX31855':
            sensor = sen.k_type_DFRobot_MAX31855()
        elif self.config['sensing']['adc'] == 'SHT30':
            sensor = sen.sht30()
        elif self.config['sensing']['adc'] == 'PT100_arduino':
            sensor = sen.PT100_arduino()
        elif self.config['sensing']['adc'] == 'PT100_raspi_MAX31865':
            sensor = sen.PT100_raspi_MAX31865(spi_chip_select=channel) # channel is interpreted as chip select for MAX31865. 0 or 1.
        elif self.config['sensing']['adc'] == 'PT100_raspi_SMHAT':
            stack   = 0
            while channel > 8: # channels > 8 will be referred to higher up the stack (0-7). Allows for all 64 potential channels to be called from a single int.
                stack   += 1   # allow large stack numbers, but >7 will fail at runtime.
                channel -= 8
            sensor = sen.PT100_raspi_sequentmicrosystems_HAT(stack, channel)

        else:
            raise Exception(f'ADC "{self.config["sensing"]["adc"]}" not recognised/supported')

        num_samples = 0
        sample_accumulator = 0

        sleep_time = period
        t = time.time()
        while run:
            t += period


            # Collect samples from ADC
            try:
                sample = sensor.get_temperature()
                logger.debug(f"adding sample {sample} to accumulator")
                sample_accumulator += sample
                num_samples+=1
            except Exception as e:
                logger.error(f"Sampling led to exception{e}")


            # handle timestamps and timezones
            if time.time() > next_check:
                __dt = -1 * (time.timezone if (time.localtime().tm_isdst == 0) else time.altzone)
                tz = datetime.timezone(datetime.timedelta(seconds=__dt))
                # set up next check
                today = datetime.datetime.now().date()
                next_check = (datetime.datetime(today.year, today.month, today.day) + datetime.timedelta(
                    days=1)).timestamp()

            # dispatch messages
            if num_samples >= self.sample_count:
                average_sample = sample_accumulator / self.sample_count
                logger.debug(f"average temperature_reading {average_sample} from {num_samples} valid samples") # reading is part of full message, which is info logged below. Don't duplicate.
                num_samples = 0
                sample_accumulator = 0

                # Compare against thresholds 
                if average_sample > th_high:
                    AlertVal = 1
                elif average_sample < th_low:
                    AlertVal = -1
                else:
                    AlertVal = 0

                # capture timestamp
                timestamp = datetime.datetime.now(tz=tz).isoformat()

                # convert
                payload = {"machine": self.constants['machine'], "temp": average_sample, "AlertVal": AlertVal, "ThresholdLow": th_low, "ThresholdHigh": th_high, "sensor": self.config['sensing']['adc'], "timestamp": timestamp}

                # send
                self.dispatch(payload)

            # handle sample rate
            if sleep_time <= 0:
                logger.warning(f"previous loop took longer that expected by {-sleep_time}s")
                t = t - sleep_time  # prevent free-wheeling to make up the slack

            sleep_time = t - time.time()
            time.sleep(max(0.0, sleep_time))

        logger.info("done")

    def dispatch(self, payload):
        logger.info(payload)
        self.zmq_out.send_json({'path': "", 'payload': payload})
