"""
The MIT License (MIT)

Copyright (c) 2020 Sequent Microsystems

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""

#import smbus  # The only Shoestring edit to the sequent microsystems code: 
import smbus2 as smbus # swapping out the above line for this one.
import struct

# bus = smbus.SMBus(1)    # 0 = /dev/i2c-0 (port I2C0), 1 = /dev/i2c-1 (port I2C1)

DEVICE_ADDRESS = 0x40  # 7 bit address (will be left shifted to add the read write bit)

RTD_TEMPERATURE_ADD = 0
RTD_RESISTANCE_ADD = 59


def get(stack, channel):
    """Get temperature directly using simple linear function calculated in HAT hardware"""
    if stack < 0 or stack > 7:
        raise ValueError('Invalid stack level')
    if channel < 1 or channel > 8:
        raise ValueError('Invalid channel number')
    val = (-273.15)
    bus = smbus.SMBus(1)
    try:
        buff = bus.read_i2c_block_data(DEVICE_ADDRESS + stack, RTD_TEMPERATURE_ADD + (4 * (channel - 1)), 4)
        val = struct.unpack('f', bytearray(buff))
    except Exception as e:
        bus.close()
        raise ValueError('Fail to communicate with the RTD card with message: \"' + str(e) + '\"')
    bus.close()
    return val[0]


def getRes(stack, channel):
    """Get compensated resistance of RTD element, for use in external calculation of temperature"""
    if stack < 0 or stack > 7:
        raise ValueError('Invalid stack level')
    if channel < 1 or channel > 8:
        raise ValueError('Invalid channel number')
    val = (-273.15)
    bus = smbus.SMBus(1)
    try:
        buff = bus.read_i2c_block_data(DEVICE_ADDRESS + stack, RTD_RESISTANCE_ADD + (4 * (channel - 1)), 4)
        val = struct.unpack('f', bytearray(buff))
    except Exception as e:
        bus.close()
        raise ValueError('Fail to communicate with the RTD card with message: \"' + str(e) + '\"')
    bus.close()
    return val[0]
