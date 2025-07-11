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

from smbus2 import SMBus
import json
import logging
import time

#from mlx90614 import MLX90614              # imported below when class is created
#from w1thermsensor import W1ThermSensor    # imported below when class is created
#import serial                              # imported below when class is created
#import adc.MAX31865                        # imported below when class is created
#import adc.DFRobot_MAX31855                # imported below when class is created
#import adc.SequentMicrosystemsRTDHAT       # imported below when class is created
#import models.pt_rtd                       # imported below when class is created

logger = logging.getLogger("main.measure.sensor")



class k_type_DFRobot_MAX31855:
    # https://github.com/DFRobot/DFRobot_MAX31855/tree/main/raspberrypi/python
    def __init__(self):
        logger.debug("TemperatureMeasureBuildingBlock- k_type_DFRobot_MAX31855 created")
        import adc.DFRobot_MAX31855 as DFRobot_MAX31855
        self.I2C_1       = 0x01
        self.I2C_ADDRESS = 0x10
        #Create MAX31855 object
        self.max31855 = DFRobot_MAX31855(self.I2C_1 ,self.I2C_ADDRESS)


    def get_temperature(self):
        logger.debug("TemperatureMeasureBuildingBlock- k_type_DFRobot_MAX31855 started")
        return self.max31855.read_celsius()



class MLX90614:
    def __init__(self):
        logger.debug("TemperatureMeasureBuildingBlock- MLX90614 created")
        from mlx90614 import MLX90614
        self.bus = SMBus(1)
        self.sensor=MLX90614(self.bus,address=0x5a)

    def sensor_die_temp(self): # not used externally
        logger.debug("TemperatureMeasureBuildingBlock- MLX90614_self started")
        return self.sensor.get_amb_temp()

    def get_temperature(self): # target surface temperature via infrared 
        logger.debug("TemperatureMeasureBuildingBlock- MLX90614_IR started")
        return self.sensor.get_obj_temp()



class sht30:
    def __init__(self):
        logger.debug("TemperatureMeasureBuildingBlock- SHT30 created")
        self.bus = SMBus(1)
        self.bus.write_i2c_block_data(0x44, 0x2C, [0x06])
        time.sleep(0.5)
        self.data = self.bus.read_i2c_block_data(0x44, 0x00, 6)

    def get_temperature(self):
        logger.debug("TemperatureMeasureBuildingBlock- SHT30 started")
        self.temp = self.data[0] * 256 + self.data[1]
        return -45 + (175 * self.temp / 65535.0)



class W1Therm:
    def __init__(self, channel=1):
        logger.debug("TemperatureMeasureBuildingBlock- w1therm created")
        from w1thermsensor import W1ThermSensor
        all_sensors_on_bus = W1ThermSensor.get_available_sensors()
        self.sensor = all_sensors_on_bus[channel - 1] # Accept channel numbers starting at 1 for consistency. Map to zero-indexed list.


    def get_temperature(self):
        logger.debug("TemperatureMeasureBuildingBlock- w1therm started")
        return self.sensor.get_temperature()



class PT100_arduino:
    def __init__(self):
        logger.debug("TemperatureMeasureBuildingBlock- PT100_arduino created")
        import serial
        self.ser = serial.Serial(port='/dev/ttyACM0', baudrate=115200, timeout=1)

    def get_temperature(self):
        logger.debug("TemperatureMeasureBuildingBlock- PT100_arduino started")
        with self.ser as ser:
            if ser.isOpen():
                ser.flushInput()
                time.sleep(0.5)
                data_string = ser.readline().decode('utf-8').strip()
                data = json.loads(data_string)
                self.reading = data["T"]
        return self.reading

    def close(self):
        self.ser.close()



class PT100_raspi_MAX31865:
    def __init__(self, spi_chip_select=1):
        logger.debug("TemperatureMeasureBuildingBlock- PT100_raspi_MAX31865 created")
        import adc.MAX31865
        import models.pt_rtd
        self.MyMax = adc.MAX31865.max31865(spi_cs=spi_chip_select)
        self.MyMax.set_config(VBias=1, continuous=1, filter50Hz=1)
        self.MyRTD = models.pt_rtd.PT_RTD(100) # Create RTD model instance. Unfortunately config is not exposed here to select 100 ohm or 1000 ohm

    def get_temperature(self):
        logger.debug("TemperatureMeasureBuildingBlock- PT100_raspi_MAX31865 started")
        resistance = self.MyMax()
        logger.debug(f"MAX31865 reported RTD resistance as {resistance}")
        return self.MyRTD(resistance) # no need to log temperature as each sample is debug logged in measure.py

    def close(self):
        self.MyMax.spi.close()



class PT100_raspi_sequentmicrosystems_HAT:
    def __init__(self, stack=0, channel=1):
        logger.debug("TemperatureMeasureBuildingBlock- PT100_raspi_sequentmicrosystems_HAT created")
        import adc.SequentMicrosystemsRTDHAT
        import models.pt_rtd
        self.RTD_ADC = adc.SequentMicrosystemsRTDHAT # no class, just get() and getRes() sampling functions
        self.channel = channel # 1-8
        self.stack = stack     # 0-7
        self.MyRTD = models.pt_rtd.PT_RTD(100) # Sequent RTD HAT only supports 100 ohm

    def get_temperature(self):
        logger.debug("TemperatureMeasureBuildingBlock- PT100_raspi_sequentmicrosystems_HAT started on stack " + str(self.stack) + " channel " + str(self.channel))
        resistance = self.RTD_ADC.getRes(self.stack, self.channel)
        logger.debug(f"Sequent reported RTD resistance as {resistance}")
        return self.MyRTD(resistance) # no need to log temperature as each sample is debug logged in measure.py
