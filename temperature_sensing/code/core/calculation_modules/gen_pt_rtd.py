import traceback
import logging

logger = logging.getLogger(__name__)


class PT_RTD:
    def __init__(self, config,variables):
        self.nominal_resistance = config.get('nominal_resistance', 100)  # e.g. 100 = 100 ohm.
        self.nominal_temperature = config.get('nominal_temperature', 0)  # temperature at this resistance e.g. 0 = 0 deg C

        self.output_voltage_variable = variables.get('voltage_out')
        self.input_current_variable = variables.get('current_in', 'current')

    def calculate(self, var_dict): # still needs adapting from power. Merge in get_poly5().
        try:
            # Get clamp output voltage
            v_clamp = var_dict[self.output_voltage_variable]

            if v_clamp is not None:

                # Multiply clamp output voltage by nominal ratio to get input current
                current = (v_clamp / self.nominal_voltage) * self.nominal_current

                # Set the input current variable
                var_dict[self.input_current_variable] = current

            else:
                logger.warning(f"PT_RTD: output voltage variable '{self.output_voltage_variable}' not found")

        except Exception:
            logger.error(traceback.format_exc())

        return var_dict


def get_poly5(res) -> float:
    """
    Convert RTD reading to Temperature, using 5th order polynomial fit of Temperature as a function of Resistance.
    This fit provides much improved accuracy through the temperature range of [-200C, 660C], particularly near the high
    and low ranges, compared to the default linear fitting function baked into the Sequent RTD Data Acquisition
    Stackable Card for Raspberry Pi.  The coefficients for this fit were developed in a project documented
    in https://github.com/ewjax/max31865

        temp_C = (c5 * res^5) + (c4 * res^4) + (c3 * res^3) + (c2 * res^2) + (c1 * res) + c0

    :param stack: 0-7, which hat to read
    :param channel: 1-8, which RTD to read on indicated hat
    :return: temperature, in celcius
    """

    # coeffs for 5th order fit
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

    return temp_C