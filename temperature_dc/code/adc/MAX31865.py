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

import spidev
from math import sqrt
import time

class max31865:

	# Register definitions
	REG_CONFIG_READ = 0x00
	REG_CONFIG_WRITE = 0x80
	REG_RTD_READING = 0x01


	def __init__(self, R_Ref=430, spi_bus=0, spi_cs=1, spi_speed=7629, spi_clock_polarity=1, spi_clock_phase=1):

		self.R_Ref = R_Ref	# ADC full scale. Ideally around 4*R_0dC. Product we recommend is specified to have a 430Ω 0.1% resistor.

		self.spi = spidev.SpiDev()
		self.spi.open(spi_bus, spi_cs)
		self.spi.max_speed_hz = spi_speed
		self.spi.mode = (spi_clock_polarity << 1 | spi_clock_phase)	# 0b11 or else...


	def __call__(self):
		return self.calculate_resistance(self._read_adc())


	def _read_regs(self, first_reg_addr,  nregs=8):
		"""Read nregs consecutive registers, starting from first_reg_addr"""

		"""
		A note on the registers of the MAX31865:
		00h = Config
		01h = RTD MSBs
		02h = RTD LSBs
		03h = High Fault Threshold MSB
		04h = High Fault Threshold LSB
		05h = Low Fault Threshold MSB
		06h = Low Fault Threshold LSB
		07h = Fault Status
		"""

		resp = self.spi.xfer2([first_reg_addr] + [0]*nregs)[1:] # Ignore first byte as it was while the command was being clocked in
		return resp


	def _write_reg(self, reg_addr, data):
		self.spi.writebytes([reg_addr, data])			# Can be temperamental and cause seg faults, but behaving today.
#		self.spi.xfer2([reg_addr, data])			# More reliable, even when discarding the response.


	def _bytes_to_15bit(self, MSBs_byte, LSBs_byte):
		"""extract a 15bit int from two bytes, MSB justified"""
		return ((MSBs_byte <<8 | LSBs_byte) >> 1)


	def _read_adc(self):
		"""clock data out of the adc and return as int"""
		reading_bytes = self._read_regs(self.REG_RTD_READING, 2)
		ADC_Code = self._bytes_to_15bit(reading_bytes[0], reading_bytes[1])
		return ADC_Code



	def set_config(self, VBias=0, continuous=0, oneshot=0, threewire=0, faultdetect=0, faultclear=0, filter50Hz=0):
		"""
		Overwrite the config register:
		---------------
		bit 7: Vbias (1=ON, 0=OFF). Needs to be on in either mode to get new readings.
		bit 6: Conversion Mode (1=Auto/Continuous, 0=OFF/Manual)
		bit 5: 1-shot (1=1-shot on, auto cleared)
		bit 4: 3-wire select (1=3 wire config, 0=2 or 4 wire config)
		bits 3-2: fault detection cycle (0=none, otherwise see data sheet)
		bit 1: fault status clear (1=Clear any fault, auto cleared)
		bit 0: 50/60 Hz filter select (1=50Hz, 0=60Hz)
		"""

		new_config_byte = (VBias << 7 | continuous << 6 | oneshot << 5 | threewire << 4 | faultdetect << 2 | faultclear << 1 | filter50Hz)
		self._write_reg(self.REG_CONFIG_WRITE, new_config_byte)


	def oneshot(self):
		"""Request a single reading without otherwise changing the config."""
		current_config = self._read_regs(self.REG_CONFIG_READ, 1)[0]
		new_config = (current_config  | 0b00100000)
		self._write_reg(self.REG_CONFIG_WRITE, new_config)


	def calculate_resistance(self, adc_code, adc_fullscale=32768):
		"""Calculate the resistance of the RTD, with R_Ref as full scale """
		R_RTD = self.R_Ref * adc_code / adc_fullscale
		return R_RTD


class PT_RTD:

	def __init__(self, R_0dC, a=3.9083e-3, b=-5.775e-7, c_pos=0, c_neg=-4.18301e-12):

		self.R_0dC = R_0dC	# The RTD resistance at 0 degrees C. Common standards are 100 and 1000.

		# A great model of PT-RTD resistance vs temperature is the Callendar-Van Dusen equation:
		# R_RTD = R_0dC * (1 + a*T + b*T**2 + c*(T-100)*T**3)
		# Standard constants (IEC7751/SAMA) as default

		self.a = a
		self.b = b
		self.c_pos = c_pos	# For temperatures above 0 degrees C
		self.c_neg = c_neg	# For temperatures below 0 degrees C


	def __call__(self, resistance):
		"""shorthand for most common usage"""
		return self.calculate_temperature_quadratic(resistance)


	def calculate_temperature_linear(self, resistance):

		# Linear approximation:
		T_C_linear = ((resistance / self.R_0dC) - 1) / self.a
		return T_C_linear

	def calculate_temperature_quadratic(self, resistance):

		# Quadratic approximation (unfortunately the constants do not follow convention):
		# R_RTD / R_0dC = 1 + aT + bt^2
		# T = (-a +- sqrt(a^2-4b(1-R_RTD/R_0dC))) / 2b
		T_C_quadratic = ( -self.a + sqrt((self.a**2)-4*self.b*(1-(resistance/self.R_0dC))) )/(2*self.b)
		return T_C_quadratic

#	def calculate_temperature_quartic(self, resistance):
		# Full Callendar-Van Dussen, improves on quad below 0dC.
		# tbd


# test
if __name__ == '__main__':

	MyMax = max31865()
	MyMax.set_config(VBias=1, filter50Hz=1)
	time.sleep(0.5)
	MyRTD = PT_RTD(100)

	# test in oneshot mode
	print("oneshot mode:")
	for i in range(5):
		MyMax.oneshot()
		time.sleep(0.1) # after activating oneshot measurement, conversion takes about 60ms until DATA_READY falls low (=ready). 100ms is safe margin.
		print(MyRTD(MyMax()))
		time.sleep(1)
	time.sleep(1)

	# test in continuous mode
	print("continuous mode:")
	MyMax.set_config(VBias=1, continuous=1, filter50Hz=1)
	time.sleep(0.5)

	for i in range(5):
		print(MyRTD(MyMax()))
		time.sleep(1)

	MyMax.spi.close()
