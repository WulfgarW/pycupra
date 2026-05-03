#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#Extract information from data files downloaded from the EU Data Act portal of Volkswagen group.
import logging

from .const import (
    EUDA_SHORT_TERM_DATA_START_MILEAGE_KEY,
    EUDA_SHORT_TERM_DATA_MILEAGE_KEY,
    EUDA_SHORT_TERM_DATA_TRAVEL_TIME_KEY,
    EUDA_SHORT_TERM_DATA_AVERAGE_FUEL_CONSUMPTION_KEY,
    EUDA_SHORT_TERM_DATA_AVERAGE_ELECTR_ENGINE_CONSUMPTION_KEY,
    EUDA_LONG_TERM_DATA_START_MILEAGE_KEY,
    EUDA_LONG_TERM_DATA_MILEAGE_KEY,
    EUDA_LONG_TERM_DATA_TRAVEL_TIME_KEY,
    EUDA_LONG_TERM_DATA_AVERAGE_FUEL_CONSUMPTION_KEY,
    EUDA_LONG_TERM_DATA_AVERAGE_ELECTR_ENGINE_CONSUMPTION_KEY,
    EUDA_LONG_TERM_DATA_AVERAGE_SPEED_KEY,

    EUDA_OUTSIDE_TEMPERATURE_KEY,
    EUDA_OIL_LEVEL_ACTUAL_LEVEL_KEY,
    EUDA_PARKING_BRAKE_KEY,
)

_LOGGER = logging.getLogger(__name__)

class EUDAVehicle:
  # Init connection class
    def __init__(self, conn, data):
        self._logPrefix = data.get('logPrefix', None)
        if self._logPrefix is not None:
            self._LOGGER= logging.getLogger(__name__+"_"+self._logPrefix)
        else:
            self._LOGGER = _LOGGER

        self._LOGGER.debug(conn.anonymise(f'Creating Vehicle class object with data {data}'))
        self._connection = conn
        self._vin = data.get('vin', '')
        self._brand = data.get('brand', '')
        self._nickName = data.get('nickName', '')
        self._dashboard = None
        self._states = {}
        self.currentData = {}

    @property
    def vin(self):
        return self._vin

    @property
    def unique_id(self):
        return self.vin

    @property
    def nickname(self):
        return self._nickName

    @property
    def is_nickname_supported(self) -> bool:
        """Return true if nickname is supported."""
        if self._nickName != '':
            return True
        else:
            return False

    @property
    def brand(self):
        """Return brand"""
        return self._brand

    @property
    def is_brand_supported(self) -> bool:
        """Return true if brand is supported."""
        if self._brand != '':
            return True
        else:
            return False

    @property
    def model(self):
        """Return model"""
        return GetModelFromNickName(self._nickName).lower()

    @property
    def model_year(self):
        """Return model year"""
        return 'unknown'

    @property
    def outside_temperature(self) -> float:
        """Return outside temperature in °C."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_OUTSIDE_TEMPERATURE_KEY:
                if 'value' in element:
                    return float(element.get('value','0.0'))/10 - 273.1 # The temperature returnd from the portal is in Kelvin
        return 0.0

    @property
    def is_outside_temperature_supported(self) -> bool:
        """Return true if outside temperature is supported."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_OUTSIDE_TEMPERATURE_KEY:
                if 'value' in element:
                    return True
        return False

    def outside_temperature_timestamp(self) -> str:
        """Return timestamp for outside temperature."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_OUTSIDE_TEMPERATURE_KEY:
                if 'timestampUtc' in element:
                    return element.get('timestampUtc','unknown')
        return 'unknown'

    @property
    def oil_level(self) -> float:
        """Return oil level in %."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_OIL_LEVEL_ACTUAL_LEVEL_KEY:
                if 'value' in element:
                    return float(element.get('value','0'))
        return 0.0

    @property
    def is_oil_level_supported(self) -> bool:
        """Return true if oil level is supported."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_OIL_LEVEL_ACTUAL_LEVEL_KEY:
                if 'value' in element:
                    return True
        return False

    @property
    def parking_brake(self) -> bool:
        """Return parking brake value."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_PARKING_BRAKE_KEY:
                if 'value' in element:
                    if element.get('value','0') != '0':
                        return True
        return False

    @property
    def is_parking_brake_supported(self) -> bool:
        """Return true if parking brake is supported."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_PARKING_BRAKE_KEY:
                if 'value' in element:
                    return True
        return False

    def parking_brake_timestamp(self) -> str:
        """Return timestamp for parking brake value."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_PARKING_BRAKE_KEY:
                if 'timestampUtc' in element:
                    return element.get('timestampUtc','unknown')
        return 'unknown'

    @property
    def long_term_start_mileage(self) -> int:
        """Return long term start mileage."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_LONG_TERM_DATA_START_MILEAGE_KEY:
                if 'value' in element:
                    return int(element.get('value','0'))
        return 0

    @property
    def is_long_term_start_mileage_supported(self) -> bool:
        """Return true if long term start mileage is supported."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_LONG_TERM_DATA_START_MILEAGE_KEY:
                if 'value' in element:
                    return True
        return False

    @property
    def long_term_distance(self) -> int:
        """Return long term distance."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_LONG_TERM_DATA_MILEAGE_KEY:
                if 'value' in element:
                    return int(element.get('value','0'))
        return 0

    @property
    def is_long_term_distance_supported(self) -> bool:
        """Return true if long term distance is supported."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_LONG_TERM_DATA_MILEAGE_KEY:
                if 'value' in element:
                    return True
        return False

    @property
    def long_term_duration(self) -> int:
        """Return long term duration."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_LONG_TERM_DATA_TRAVEL_TIME_KEY:
                if 'value' in element:
                    return int(element.get('value','0'))
        return 0

    @property
    def is_long_term_duration_supported(self) -> bool:
        """Return true if long term duration is supported."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_LONG_TERM_DATA_TRAVEL_TIME_KEY:
                if 'value' in element:
                    return True
        return False

    @property
    def long_term_average_electric_consumption(self) -> float:
        """Return long term average electric consumption."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_LONG_TERM_DATA_AVERAGE_ELECTR_ENGINE_CONSUMPTION_KEY:
                if 'value' in element:
                    return int(element.get('value','0'))/10
        return 0.0

    @property
    def is_long_term_average_electric_consumption_supported(self) -> bool:
        """Return true if long term average electric consumption is supported."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_LONG_TERM_DATA_AVERAGE_ELECTR_ENGINE_CONSUMPTION_KEY:
                if 'value' in element:
                    return True
        return False

    @property
    def long_term_average_fuel_consumption(self) -> float:
        """Return long term average fuel consumption."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_LONG_TERM_DATA_AVERAGE_FUEL_CONSUMPTION_KEY:
                if 'value' in element:
                    return int(element.get('value','0'))/10
        return 0.0

    @property
    def is_long_term_average_fuel_consumption_supported(self) -> bool:
        """Return true if long term average fuel consumption is supported."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_LONG_TERM_DATA_AVERAGE_FUEL_CONSUMPTION_KEY:
                if 'value' in element:
                    return True
        return False

    @property
    def long_term_average_speed(self) -> int:
        """Return long term average speed."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_LONG_TERM_DATA_AVERAGE_SPEED_KEY:
                if 'value' in element:
                    return int(element.get('value','0'))
        return 0

    @property
    def is_long_term_average_speed_supported(self) -> bool:
        """Return true if long term aveage speed is supported."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_LONG_TERM_DATA_AVERAGE_SPEED_KEY:
                if 'value' in element:
                    return True
        return False

    @property
    def short_term_start_mileage(self) -> int:
        """Return short term start mileage."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_SHORT_TERM_DATA_START_MILEAGE_KEY:
                if 'value' in element:
                    return int(element.get('value','0'))
        return 0

    @property
    def is_short_term_start_mileage_supported(self) -> bool:
        """Return true if short term start mileage is supported."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_SHORT_TERM_DATA_START_MILEAGE_KEY:
                if 'value' in element:
                    return True
        return False

    @property
    def short_term_distance(self) -> int:
        """Return short term distance."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_SHORT_TERM_DATA_MILEAGE_KEY:
                if 'value' in element:
                    return int(element.get('value','0'))
        return 0

    @property
    def is_short_term_distance_supported(self) -> bool:
        """Return true if short term distance is supported."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_SHORT_TERM_DATA_MILEAGE_KEY:
                if 'value' in element:
                    return True
        return False

    @property
    def short_term_duration(self) -> int:
        """Return short term duration."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_SHORT_TERM_DATA_TRAVEL_TIME_KEY:
                if 'value' in element:
                    return int(element.get('value','0'))
        return 0

    @property
    def is_short_term_duration_supported(self) -> bool:
        """Return true if short term duration is supported."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_SHORT_TERM_DATA_TRAVEL_TIME_KEY:
                if 'value' in element:
                    return True
        return False

    @property
    def short_term_average_electric_consumption(self) -> float:
        """Return short term average electric consumption."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_SHORT_TERM_DATA_AVERAGE_ELECTR_ENGINE_CONSUMPTION_KEY:
                if 'value' in element:
                    return int(element.get('value','0'))/10
        return 0.0

    @property
    def is_short_term_average_electric_consumption_supported(self) -> bool:
        """Return true if short term average electric consumption is supported."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_SHORT_TERM_DATA_AVERAGE_ELECTR_ENGINE_CONSUMPTION_KEY:
                if 'value' in element:
                    return True
        return False

    @property
    def short_term_average_fuel_consumption(self) -> float:
        """Return short term average fuel consumption."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_SHORT_TERM_DATA_AVERAGE_FUEL_CONSUMPTION_KEY:
                if 'value' in element:
                    return int(element.get('value','0'))/10
        return 0.0

    @property
    def is_short_term_average_fuel_consumption_supported(self) -> bool:
        """Return true if short term average fuel consumption is supported."""
        for element in self.currentData.get('Data', []):
            if element.get('key','') == EUDA_SHORT_TERM_DATA_AVERAGE_FUEL_CONSUMPTION_KEY:
                if 'value' in element:
                    return True
        return False


def GetModelFromNickName(nickName: str) -> str:
    posSeparator = nickName.find(' ')
    if posSeparator>0 and len(nickName)>posSeparator:
        return nickName[posSeparator+1:]
    return '' 
    
