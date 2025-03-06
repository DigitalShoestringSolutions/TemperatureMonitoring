"""Model of a Platinum Resistance Temperature Detector (PT-RTD)"""

class PT_RTD:

    def __init__(self, R_0dC=100):
        self.R_0dC = R_0dC	# The RTD resistance at 0 degrees C. Common standards are 100 and 1000.


    def __call__(self, resistance: float) -> float:
        """shorthand for most common usage"""
        return self.resistance_to_temperature_poly5(resistance)


    def resistance_to_temperature_poly5(self, resistance: float) -> float:
        """
        Convert RTD reading to Temperature, using 5th order polynomial fit of Temperature as a function of Resistance.
        This fit provides much improved accuracy through the temperature range of [-200C, 660C], particularly near the high
        and low ranges, compared to linear fitting functions. The coefficients for this fit were developed in a project documented
        in https://github.com/ewjax/max31865

            temp_C = (c5 * res^5) + (c4 * res^4) + (c3 * res^3) + (c2 * res^2) + (c1 * res) + c0

        :param resistance: RTD element resistance after cable compensation
        :return: temperature, in celsius
        """
		
        # re-scale resistance to 100 ohm nominal
        resistance *= 100 / self.R_0dC

        # coefficients for 5th order fit at 100 ohm nominal resistance
        c5 = -2.10678E-11
        c4 = 2.27311E-08
        c3 = -8.20888E-06
        c2 = 2.38589E-03
        c1 = 2.24745E+00
        c0 = -2.42522E+02

        # do the math
        #   Rearrange a bit to make it friendlier (less expensive) to calculate
        #   temp_C = res ( res ( res ( res ( res * c5 + c4) + c3) + c2) + c1) + c0
        temp_C = resistance * c5 + c4

        temp_C *= resistance
        temp_C += c3

        temp_C *= resistance
        temp_C += c2

        temp_C *= resistance
        temp_C += c1

        temp_C *= resistance
        temp_C += c0

        return temp_C