#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Extract information from data files downloaded from the EU Data Act portal of Volkswagen group.
import logging

from .const import (
    EUDA_DATA_CONVERSION_FLOAT,
    EUDA_DATA_CONVERSION_INT,
    EUDA_DATA_CONVERSION_BOOL,
    EUDA_DATA_CONVERSION_DIVIDE_BY_10,
    EUDA_DATA_CONVERSION_KELVIN_TO_CELSIUS,
    EUDA_DATA_CONVERSION_INT_INVERT,
)

_LOGGER = logging.getLogger(__name__)


class EUDAVehicle:
    # Init connection class
    def __init__(self, conn, data):
        self._logPrefix = data.get("logPrefix", None)
        if self._logPrefix is not None:
            self._LOGGER = logging.getLogger(__name__ + "_" + self._logPrefix)
        else:
            self._LOGGER = _LOGGER

        self._LOGGER.debug(
            conn.anonymise(f"Creating Vehicle class object with data {data}")
        )
        self._connection = conn
        self._vin = data.get("vin", "")
        self._brand = data.get("brand", "")
        self._nickName = data.get("nickName", "")
        self._dashboard = None
        self._states = {}
        self.currentData = {}

    def dashboard(self, **config):
        """Returns dashboard, creates new if none exist."""
        if self._dashboard is None:
            # Init new dashboard if none exist
            from .dashboard import Dashboard

            self._dashboard = Dashboard(self, **config)
        elif config != self._dashboard._config:
            # Init new dashboard on config change
            from .dashboard import Dashboard

            self._dashboard = Dashboard(self, **config)
        return self._dashboard

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
        if self._nickName != "":
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
        if self._brand != "":
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
        return "unknown"

    def getEUDADataFieldValue(self, key=None, conversion=None) -> any:
        """Return value of an EUDA data field identified by key."""
        for element in self.currentData.get("Data", []):
            if element.get("key", "") == key:
                if "value" in element:
                    if conversion == None:
                        return element.get("value", "")
                    elif conversion == EUDA_DATA_CONVERSION_FLOAT:
                        return float(element.get("value", "0"))
                    elif conversion == EUDA_DATA_CONVERSION_INT:
                        return int(element.get("value", "0"))
                    elif conversion == EUDA_DATA_CONVERSION_INT_INVERT:
                        return -int(element.get("value", "0"))
                    elif conversion == EUDA_DATA_CONVERSION_BOOL:
                        if element.get("value", "") == "on":
                            return True
                        if element.get("value", "") == "locked":
                            return True
                        if element.get("value", "") == "1" and element.get("dataFieldName", "").startswith("parking_brake"):
                            return True
                        if element.get("value", "") == "3" and element.get("dataFieldName", "").startswith("open_state"):
                            return True
                    elif conversion == EUDA_DATA_CONVERSION_DIVIDE_BY_10:
                        return int(element.get("value", "0")) / 10
                    elif conversion == EUDA_DATA_CONVERSION_KELVIN_TO_CELSIUS:
                        return (
                            float(element.get("value", "0.0")) / 10 - 273.1
                        )  # The temperature returned from the portal is in Kelvin
                    else:
                        self._LOGGER.warning(f"Unknown conversion type {conversion} in getEUDADataFiledValue()")
        if conversion == EUDA_DATA_CONVERSION_FLOAT:
            return 0.0
        elif conversion == EUDA_DATA_CONVERSION_INT:
            return 0
        elif conversion == EUDA_DATA_CONVERSION_BOOL:
            return False
        elif conversion == EUDA_DATA_CONVERSION_DIVIDE_BY_10:
            return 0.0
        elif conversion == EUDA_DATA_CONVERSION_KELVIN_TO_CELSIUS:
            return 0.0
        elif conversion == EUDA_DATA_CONVERSION_INT_INVERT:
            return 0
        return ""

    def isEUDADataFieldSupported(self, key=None) -> bool:
        """Return true if the EUDA data field identified by key is supported."""
        for element in self.currentData.get("Data", []):
            if (
                element.get("key", "")
                == key
            ):
                if "value" in element:
                    return True
        return False

    def getEUDADataFieldTimestamp(self, key=None) -> str:
        """Return timestamp for an EUDA data field identified by key."""
        for element in self.currentData.get("Data", []):
            if element.get("key", "") == key:
                if "timestampUtc" in element:
                    return element.get("timestampUtc", "unknown")
        return "unknown"


def GetModelFromNickName(nickName: str) -> str:
    posSeparator = nickName.find(" ")
    if posSeparator > 0 and len(nickName) > posSeparator:
        return nickName[posSeparator + 1 :]
    return ""
