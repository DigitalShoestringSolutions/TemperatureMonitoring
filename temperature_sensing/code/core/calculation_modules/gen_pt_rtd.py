import traceback
import logging

logger = logging.getLogger(__name__)


class PT_RTD:
    def __init__(self, config, variables):
        """
        Convert RTD resistance to Temperature, using 5th order polynomial fit of Temperature as a function of Resistance.
        This fit provides much improved accuracy through the temperature range of [-200C, 660C], particularly near the high
        and low ranges, compared to linear or quadratic fits. The coefficients for this fit were developed in a project documented
        in https://github.com/ewjax/max31865

            temp_C = (c5 * res^5) + (c4 * res^4) + (c3 * res^3) + (c2 * res^2) + (c1 * res) + c0
            Rearrange a bit to make it friendlier (less expensive) to calculate:
            temp_C = res ( res ( res ( res ( res * c5 + c4) + c3) + c2) + c1) + c0

        :return: temperature, in celcius
        """

        self.nominal_resistance = config.get('nominal_resistance', 100)  # e.g. 100 = 100 ohm.

        self.input_variable = variables.get('temperature', 'temperature') # input to physical hardware that this is modeling
        self.output_variable = variables.get('resistance', 'resistance')  # Output of physical hardware that this is modeling


    def calculate(self, var_dict):
        try:
            # Get clamp output voltage
            res = var_dict[self.output_variable]

            if res is not None:

                # re-scale resistance to 100 ohm nominal
                res *= 100 / self.nominal_resistance

                # coeffs for 5th order fit. Assumes nominal resistance of 100 ohm at 0 deg C.
                c5 = -2.10678E-11
                c4 = 2.27311E-08
                c3 = -8.20888E-06
                c2 = 2.38589E-03
                c1 = 2.24745E+00
                c0 = -2.42522E+02

                # do the math
                #   Rearrange a bit to make it friendlier (less expensive) to calculate
                #   temp_C = res ( res ( res ( res ( res * c5 + c4) + c3) + c2) + c1) + c0
                temp_C = res * c5 + c4

                temp_C *= res
                temp_C += c3

                temp_C *= res
                temp_C += c2

                temp_C *= res
                temp_C += c1

                temp_C *= res
                temp_C += c0

                # Set the input current variable
                var_dict[self.input_variable] = temp_C

            else:
                logger.warning(f"PT_RTD: output voltage variable '{self.output_variable}' not found")


        except Exception:
            logger.error(traceback.format_exc())


        return var_dict
