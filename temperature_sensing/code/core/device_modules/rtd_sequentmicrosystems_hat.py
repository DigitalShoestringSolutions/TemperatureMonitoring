import traceback
import logging
import struct

logger = logging.getLogger(__name__)


class Sequent_8ch_RTD_HAT:

    def __init__(self, config, variables):
        self.channel = config.get('channel')                # No default value here, must be configured
        self.i2c_address = config.get('i2c_address',0x40)   # Use stack number? In the case of this HAT, that is as simple as just 0x40 + stack
        self.i2c = None                                     # Interface created in initialise()
        self.channel_mask = 8                               # maximum valid channel number

        self.input_variable = variables['PT_RTD_resistance'] # Physical input to the sensing hardware that this is modeling

    def initialise(self, interface):
        self.i2c = interface

    def sample(self) -> dict:
        try:
            # Check channel number is valid. Must be an int between 1 and self.channel_mask inclusive.
            if not isinstance(self.channel, int):
                raise TypeError("Sequent_8ch_RTD_HAT supplied with channel " + str(self.channel) + " which is a " + str(type(self.channel)) + " not an int")

            elif (self.channel < 1) or (self.channel > self.channel_mask):  # As marked on silkscreen, this HAT's lowest channel is 1.
                raise ValueError("Sequent_8ch_RTD_HAT supplied with channel number " + str(self.channel) + " cannot be <1  or greater than " + str(self.channel_mask))

            # identify target register 
            register_addr =  59 + (4 * (self.channel - 1))

            # perform reading
            readings = self.i2c.read_register(self.i2c_address, register_addr, 4, stop=False) # read 4 bytes starting at register_addr
            
            # unpack bytes into single resistance float
            resistance = struct.unpack('f', bytearray(readings))[0]

            return {self.input_variable: resistance}

        except Exception as e:
            logger.error(traceback.format_exc())
            raise e
