import traceback
import logging
import struct

logger = logging.getLogger(__name__)


class Sequent_8ch_RTD_HAT:

    def __init__(self, config, variables):
        self.channel = config.get('adc_channel')            # No default value here, must be configured
        self.i2c_address = config.get('i2c_address',0x40)   # Use stack number? In this case address is just 0x40 + stack
        self.i2c = None                                     # Interface created in initialise()
        self.channel_mask = 8                               # maximum valid channel number

        self.input_variable = variables['PT_RTD_resistance'] # when we say input ... this is the output of this building block?

    def initialise(self, interface):
        self.i2c = interface

    def sample(self):
        try:
            # Check channel number is valid. Must be an int between 1 and self.channel_mask inclusive.
            if not isinstance(self.channel, int):
                raise TypeError("Sequent_8ch_RTD_HAT supplied with channel " + str(self.channel) + " which is a " + str(type(self.channel)) + " not an int")

            elif (self.channel < 1) or (self.channel > self.channel_mask):  # As marked on silkscreen, this HAT's lowest channel is 1.
                raise ValueError("Sequent_8ch_RTD_HAT supplied with channel number " + str(self.channel) + " cannot be negative or greater than mask " + str(self.channel_mask))

            # prepare register byte
            register_addr =  59 + (4 * (self.channel - 1))

            # perform reading
            readings = self.i2c.read_register(self.i2c_address, register_addr, 4, stop=False) # read 4 bytes starting at register_addr
            
            # calculate resistance
            resistance = struct.unpack('f', bytearray(readings))[0]

            return {self.input_variable: resistance}

        except Exception as e:
            logger.error(traceback.format_exc())
            raise e
