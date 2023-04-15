# -*- coding: utf-8 -*-
"""ANT+ Speed/Cadence Device Profile

"""
# pylint: disable=not-context-manager,protected-access
##############################################################################
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
##############################################################################

from __future__ import print_function

from .plus import DeviceProfile
from collections import deque

SPEED_DEFAULT_PAGE = 0x00
SPEED_CUMULATIVE_OPERATING_TIME_PAGE = 0x01
SPEED_MANUFACTURER_ID_PAGE = 0x02
SPEED_PRODUCT_ID = 0x03
SPEED_BATTERY_STATUS_PAGE = 0x04
SPEED_MOTION_AND_SPEED_PAGE = 0x05
SPEED_REQUEST_DATA_PAGE = 0x46


class BikeSpeed(DeviceProfile):
    """ANT+ Bike Speed Monitor"""

    channelPeriod = 8118
    deviceType = 0x7B
    name = 'Bike Speed'

    def __init__(self, node, network, wheel_circumference, callbacks=None):
        """
        :param node: The ANT node to use
        :param network: The ANT network to connect on
        :param callbacks: Dictionary of string-function pairs specifying the callbacks to
                use for each event. In addition to the events supported by `DeviceProfile`,
                `BikeSpeed` also has the following:
                'onSpeedData'
        """
        super(BikeSpeed, self).__init__(node, network, callbacks)

        self._speed = 0.0
        self._distance = 0.0

        self._wheel_circumference = wheel_circumference
        self._bike_speed_event_time         = deque([ 0, 0 ], maxlen=2)
        self._cumulative_speed_revolution   = deque([ 0, 0 ], maxlen=2)

        self._page_toggle_observed = False
        self._page_toggle = None

    def processData(self, data):
        with self.lock:

            page = data[0] & 0x7f
            page_toggle = data[0] >> 7

            if not self._page_toggle_observed:
                if self._page_toggle is None:
                    self._page_toggle = page_toggle
                else:
                    if self._page_toggle != page_toggle:
                        self._page_toggle_observed = True            

            self._bike_speed_event_time.append(int.from_bytes(data[4:6], byteorder='little'))
            self._cumulative_speed_revolution.append(int.from_bytes(data[6:8], byteorder='little'))

            # if page ==

            self._speed = self.calculate_speed(self._wheel_circumference)
            self._distance = self.calculate_distance(self._wheel_circumference)

            callback = self.callbacks.get('onSpeedData')
            if callback:
                callback(self._speed, self._distance)


    def calculate_speed(self, wheel_circumference):
        """The computed speed (km/h) calculated by the connected sensor.
        """

        if self._cumulative_speed_revolution[0] == 0:
            return None
        if self._bike_speed_event_time[0] == 0:
            return None
        
        delta_rev_count = self.wrapDifference(self._cumulative_speed_revolution[1], self._cumulative_speed_revolution[0], 65536)
        delta_event_time = self.wrapDifference(self._bike_speed_event_time[1], self._bike_speed_event_time[0], 65536)

        if delta_event_time > 0:
            return ((wheel_circumference * delta_rev_count * 1024) / delta_event_time) * 3.6 # Units of Kilometers per hour
        else:
            return None
    
    def calculate_distance(self, wheel_circumference):
        """The computed distance travelled between valid sensor events calculated by the connected sensor.
        """

        if self._cumulative_speed_revolution[0] == 0:
            return None

        delta_rev_count = self.wrapDifference(self._cumulative_speed_revolution[1], self._cumulative_speed_revolution[0], 65536)

        return wheel_circumference * delta_rev_count # Units of Meters


class BikeCadence(DeviceProfile):
    """ANT+ Bike Cadence Monitor"""

    channelPeriod = 8102
    deviceType = 0x7A
    name = 'Bike Cadence'

    def __init__(self, node, network, callbacks=None):
        """
        :param node: The ANT node to use
        :param network: The ANT network to connect on
        :param callbacks: Dictionary of string-function pairs specifying the callbacks to
                use for each event. In addition to the events supported by `DeviceProfile`,
                `BikeCadence` also has the following:
                'onCadenceData'
        """
        super(BikeCadence, self).__init__(node, network, callbacks)

        self._cadence = 0.0

        self._bike_cadence_event_time       = deque([ 0, 0 ], maxlen=2)
        self._cumulative_cadence_revolution = deque([ 0, 0 ], maxlen=2)

        self._page_toggle_observed = False
        self._page_toggle = None

    def processData(self, data):
        with self.lock:

            page = data[0] & 0x7f
            page_toggle = data[0] >> 7

            if not self._page_toggle_observed:
                if self._page_toggle is None:
                    self._page_toggle = page_toggle
                else:
                    if self._page_toggle != page_toggle:
                        self._page_toggle_observed = True            

            self._bike_cadence_event_time.append(int.from_bytes(data[4:6], byteorder='little'))
            self._cumulative_cadence_revolution.append(int.from_bytes(data[6:8], byteorder='little'))

            # if page ==

            self._cadence = self.calculate_cadence()

            callback = self.callbacks.get('onCadenceData')
            if callback:
                callback(self._cadence)

    def calculate_cadence(self):
        """The computed cadence calculated by the connected sensor.
        """
        if self._cumulative_cadence_revolution[0] == 0:
            return None
        if self._bike_cadence_event_time[0] == 0:
            return None


        delta_rev_count = self.wrapDifference(self._cumulative_cadence_revolution[1], self._cumulative_cadence_revolution[0], 65536)
        delta_event_time = self.wrapDifference(self._bike_cadence_event_time[1], self._bike_cadence_event_time[0], 65536)

        if delta_event_time > 0:
            return (60 * delta_rev_count * 1024) / delta_event_time # Units of Revolutions per Minute
        else:
            return None

    
class SpeedCadence(DeviceProfile):
    """ANT+ Speed/Cadence Monitor"""

    channelPeriod = 8086
    deviceType = 0x79
    name = 'Speed/Cadence'

    def __init__(self, node, network, wheel_circumference, callbacks=None):
        """
        :param node: The ANT node to use
        :param network: The ANT network to connect on
        :param callbacks: Dictionary of string-function pairs specifying the callbacks to
                use for each event. In addition to the events supported by `DeviceProfile`,
                `SpeedCadence` also has the following:
                'onSpeedData'
                'onCadenceData'
        """
        super(SpeedCadence, self).__init__(node, network, callbacks)

        self._speed = 0.0
        self._cadence = 0.0
        self._distance = 0.0

        self._wheel_circumference = wheel_circumference

        self._bike_cadence_event_time       = deque([ 0, 0 ], maxlen=2)
        self._cumulative_cadence_revolution = deque([ 0, 0 ], maxlen=2)
        self._bike_speed_event_time         = deque([ 0, 0 ], maxlen=2)
        self._cumulative_speed_revolution   = deque([ 0, 0 ], maxlen=2)

    def processData(self, data):
        page = data[0]
        with self.lock:
            if (page & 0x0F) <= 5:
                # Cadence data on bytes [0:4]
                # print(f"Bike Cadence Event Time: { int.from_bytes(data[0:2], byteorder='little') }")
                # print(f"Cumulative Cadence Revolution: { int.from_bytes(data[2:4], byteorder='little') }")
                self._bike_cadence_event_time.append(int.from_bytes(data[0:2], byteorder='little'))
                self._cumulative_cadence_revolution.append(int.from_bytes(data[2:4], byteorder='little'))

                # Speed data on bytes [4:8]
                # print(f"Bike Speed Event Time: { int.from_bytes(data[4:6], byteorder='little') }")
                # print(f"Cumulative Speed Revolution: { int.from_bytes(data[6:8], byteorder='little') }")
                self._bike_speed_event_time.append(int.from_bytes(data[4:6], byteorder='little'))
                self._cumulative_speed_revolution.append(int.from_bytes(data[6:8], byteorder='little'))

                # print(f"Cadence Event Time: { self._bike_cadence_event_time }")
                # print(f"Cumulative Cadence Revolution: { self._cumulative_cadence_revolution }")
                # print(f"Bike Speed Event Time: { self._bike_speed_event_time }")
                # print(f"Cumulative Speed Revolution: { self._cumulative_speed_revolution }")

                self._speed = self.calculate_speed(self._wheel_circumference)
                self._distance = self.calculate_distance(self._wheel_circumference)
                self._cadence = self.calculate_cadence()

                callback = self.callbacks.get('onSpeedData')
                if callback:
                    callback(self._speed, self._distance)

                callback = self.callbacks.get('onCadenceData')
                if callback:
                    callback(self._cadence)

    def calculate_speed(self, wheel_circumference):
        """The computed speed (km/h) calculated by the connected sensor.
        """

        if self._cumulative_speed_revolution[0] == 0:
            return None
        if self._bike_speed_event_time[0] == 0:
            return None
        
        delta_rev_count = self.wrapDifference(self._cumulative_speed_revolution[1], self._cumulative_speed_revolution[0], 65536)
        delta_event_time = self.wrapDifference(self._bike_speed_event_time[1], self._bike_speed_event_time[0], 65536)

        if delta_event_time > 0:
            return ((wheel_circumference * delta_rev_count * 1024) / delta_event_time) * 3.6 # Units of Kilometers per hour
        else:
            return None
    
    def calculate_distance(self, wheel_circumference):
        """The computed distance travelled between valid sensor events calculated by the connected sensor.
        """

        if self._cumulative_speed_revolution[0] == 0:
            return None

        delta_rev_count = self.wrapDifference(self._cumulative_speed_revolution[1], self._cumulative_speed_revolution[0], 65536)

        return wheel_circumference * delta_rev_count # Units of Meters

    def calculate_cadence(self):
        """The computed cadence calculated by the connected sensor.
        """
        if self._cumulative_cadence_revolution[0] == 0:
            return None
        if self._bike_cadence_event_time[0] == 0:
            return None


        delta_rev_count = self.wrapDifference(self._cumulative_cadence_revolution[1], self._cumulative_cadence_revolution[0], 65536)
        delta_event_time = self.wrapDifference(self._bike_cadence_event_time[1], self._bike_cadence_event_time[0], 65536)

        if delta_event_time > 0:
            return (60 * delta_rev_count * 1024) / delta_event_time # Units of Revolutions per Minute
        else:
            return None

