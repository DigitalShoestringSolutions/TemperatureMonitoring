# ----------------------------------------------------------------------
#
#    Temperature Monitoring (Basic solution) -- This digital solution enables, measures,
#    reports and records different  types of temperatures (contact, air, radiated)
#    so that the temperature conditions surrounding a process can be understood and 
#    taken action upon. Suppored sensors include 
#    k-type thermocouples, RTDs, air samplers, and NIR-based sensors.
#    The solution provides a Grafana dashboard that 
#    displays the temperature timeseries, set threshold value, and a state timeline showing 
#    the chnage in temperature. An InfluxDB database is used to store timestamp, temperature, 
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
logger = logging.getLogger("main.measure")
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
logger.addHandler(console_handler)

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

       

        # logger.info("TemperatureMeasureBuildingBlock- STAGE-1 done")
        # self.sensor = config['sensing']['adc']
        # self.Threshold = config['threshold']['th1']                # User sets the threshold in the config file

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

        # get correct ADC module
        #try:
        #    adc_module = importlib.import_module(f"adc.{self.adc_module}")
        #    logger.debug(f"Imported {self.adc_module}")
        #except ModuleNotFoundError as e:
        #    logger.error(f"Unable to import module {self.adc_module}. Stopping!!")
        #    return

        #adc = adc_module.ADC(self.config)

        #---------------- TEST MODULE 2 -------------------

        Threshold = self.config['threshold']['th1']                # User sets the threshold in the config file

        if self.config['sensing']['adc'] == 'MLX90614':
            sensor = sen.MLX90614()
        elif self.config['sensing']['adc'] == 'W1ThermSensor':
            sensor = sen.W1Therm()
        elif self.config['sensing']['adc'] == 'K-type_DFRobot_MAX31855':
            sensor = sen.k_type_DFRobot_MAX31855()
        elif self.config['sensing']['adc'] == 'SHT30':
            sensor = sen.sht30()
        elif self.config['sensing']['adc'] == 'PT100_arduino':
            sensor = sen.PT100_arduino()
        elif self.config['sensing']['adc'] == 'PT100_raspi_MAX31865':
            sensor = sen.PT100_raspi_MAX31865()
        elif self.config['sensing']['adc'] == 'PT100_raspi_SMHAT':
            sensor = sen.PT100_raspi_sequentmicrosystems_HAT()

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
                # sample = sensor
                logger.info("Prorcess TemperatureMeasureBuildingBlock- STAGE-3 done")
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
                num_samples = 0
                sample_accumulator = 0
                print(average_sample)
                logger.info(f"temperature_reading: {average_sample}")

                if average_sample > float(Threshold):
                    AlertVal = 1
                else:
                    AlertVal = 0

                # capture timestamp
                timestamp = datetime.datetime.now(tz=tz).isoformat()

                # convert
                # results = calculation.calculate(average_sample)
                # payload = {**results, **self.constants, "timestamp": timestamp}
                payload = {"machine": self.constants['machine'], "temp": str(average_sample), "AlertVal": str(AlertVal), "Threshold": str(Threshold), "sensor": self.config['sensing']['adc'], "timestamp": timestamp}

                # send
                output = {"path": "", "payload": payload}
                self.dispatch(output)

            # handle sample rate
            if sleep_time <= 0:
                logger.warning(f"previous loop took longer that expected by {-sleep_time}s")
                t = t - sleep_time  # prevent free-wheeling to make up the slack

            sleep_time = t - time.time()
            time.sleep(max(0.0, sleep_time))
        logger.info("done")

    def dispatch(self, output):
        logger.info(f"dispatch to { output['path']} of {output['payload']}")
        self.zmq_out.send_json({'path': output.get('path', ""), 'payload': output['payload']})
