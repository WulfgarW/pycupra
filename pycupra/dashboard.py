# Utilities for integration with Home Assistant
# Thanks to molobrakos and Farfar

import logging
from datetime import datetime
from .utilities import camel2slug, convertTimerUtcToLocal

_LOGGER = logging.getLogger(__name__)

class Instrument:
    def __init__(self, component, attr, name, icon=None):
        self.attr = attr
        self.component = component
        self.name = name
        self.vehicle = None
        self.icon = icon
        self.callback = None

    def __repr__(self):
        return self.full_name

    def configurate(self, **args):
        pass

    @property
    def slug_attr(self):
        return camel2slug(self.attr.replace(".", "_"))

    def setup(self, vehicle, **config) -> bool:
        self.vehicle = vehicle
        if not self.is_supported:
            return False

        self.configurate(**config)
        return True

    @property
    def vehicle_name(self):
        return self.vehicle.vin

    @property
    def full_name(self):
        return f"{self.vehicle_name} {self.name}"

    @property
    def is_mutable(self):
        raise NotImplementedError("Must be set")

    @property
    def str_state(self):
        return self.state

    @property
    def state(self):
        if hasattr(self.vehicle, self.attr):
            return getattr(self.vehicle, self.attr)
        else:
            _LOGGER.debug(f'Could not find attribute "{self.attr}"')
        return self.vehicle.get_attr(self.attr)

    @property
    def attributes(self):
        return {}

    @property
    def is_supported(self):
        supported = 'is_' + self.attr + "_supported"
        if hasattr(self.vehicle, supported):
            return getattr(self.vehicle, supported)
        else:
            return False


class Sensor(Instrument):
    def __init__(self, attr, name, icon, unit=None, device_class=None):
        super().__init__(component="sensor", attr=attr, name=name, icon=icon)
        self.device_class = device_class
        self.unit = unit
        self.convert = False

    def configurate(self, **config) -> None:
        if self.unit and config.get('miles', False) is True:
            if "km" == self.unit:
                self.unit = "mi"
                self.convert = True
            elif "km/h" == self.unit:
                self.unit = "mi/h"
                self.convert = True
            elif "l/100km" == self.unit:
                self.unit = "l/100 mi"
                self.convert = True
            elif "kWh/100km" == self.unit:
                self.unit = "kWh/100 mi"
                self.convert = True
        elif self.unit and config.get('scandinavian_miles', False) is True:
            if "km" == self.unit:
                self.unit = "mil"
            elif "km/h" == self.unit:
                self.unit = "mil/h"
            elif "l/100km" == self.unit:
                self.unit = "l/100 mil"
            elif "kWh/100km" == self.unit:
                self.unit = "kWh/100 mil"

        # Init placeholder for parking heater duration
        config.get('parkingheater', 30)
        if "pheater_duration" == self.attr:
            setValue = config.get('climatisation_duration', 30)
            self.vehicle.pheater_duration = setValue

    @property
    def is_mutable(self) -> bool:
        return False

    @property
    def str_state(self):
        if self.unit:
            return f'{self.state} {self.unit}'
        else:
            return f'{self.state}'

    @property
    def state(self):
        val = super().state
        # Convert to miles
        if val and self.unit and "mi" in self.unit and self.convert is True:
            return int(round(val / 1.609344))
        elif val and self.unit and "mi/h" in self.unit and self.convert is True:
            return int(round(val / 1.609344))
        elif val and self.unit and "gal/100 mi" in self.unit and self.convert is True:
            return round(val * 0.4251438, 1)
        elif val and self.unit and "kWh/100 mi" in self.unit and self.convert is True:
            return round(val * 0.4251438, 1)
        elif val and self.unit and "°F" in self.unit and self.convert is True:
            temp = round((val * 9 / 5) + 32, 1)
            return temp
        elif val and self.unit in ['mil', 'mil/h']:
            return val / 10
        else:
            return val


class BinarySensor(Instrument):
    def __init__(self, attr, name, device_class, icon='', reverse_state=False):
        super().__init__(component="binary_sensor", attr=attr, name=name, icon=icon)
        self.device_class = device_class
        self.reverse_state = reverse_state

    @property
    def is_mutable(self) -> bool:
        return False

    @property
    def str_state(self):
        if self.device_class in ["door", "window"]:
            return "Closed" if self.state else "Open"
        if self.device_class == "lock":
            return "Locked" if self.state else "Unlocked"
        if self.device_class == "safety":
            return "Warning!" if self.state else "OK"
        if self.device_class == "plug":
            return "Connected" if self.state else "Disconnected"
        if self.state is None:
            _LOGGER.error(f"Can not encode state {self.attr} {self.state}")
            return "?"
        return "On" if self.state else "Off"

    @property
    def state(self):
        val = super().state

        if isinstance(val, (bool, list)):
            if self.reverse_state:
                if bool(val):
                    return False
                else:
                    return True
            else:
                return bool(val)
        elif isinstance(val, str):
            return val != "Normal"
        return val

    @property
    def is_on(self):
        return self.state


class Switch(Instrument):
    def __init__(self, attr, name, icon):
        super().__init__(component="switch", attr=attr, name=name, icon=icon)

    @property
    def is_mutable(self) -> bool:
        return True

    @property
    def str_state(self) -> str:
        return "On" if self.state else "Off"

    def is_on(self):
        return self.state

    def turn_on(self):
        pass

    def turn_off(self):
        pass

    @property
    def assumed_state(self) -> bool:
        return True

class Button(Instrument):
    def __init__(self, attr, name, icon):
        super().__init__(component="button", attr=attr, name=name, icon=icon)

    @property
    def is_mutable(self) -> bool:
        return True

    def press(self):
        pass


class Climate(Instrument):
    def __init__(self, attr, name, icon):
        super().__init__(component="climate", attr=attr, name=name, icon=icon)

    @property
    def hvac_mode(self):
        pass

    @property
    def target_temperature(self) -> None:
        pass

    def set_temperature(self, **kwargs) -> None:
        pass

    def set_hvac_mode(self, hvac_mode) -> None:
        pass


class ElectricClimatisationClimate(Climate):
    def __init__(self):
        super().__init__(attr="electric_climatisation", name="Electric Climatisation", icon="mdi:radiator")

    @property
    def hvac_mode(self):
        if self.vehicle._requests.get('climatisation', {}).get('id', False):
            _LOGGER.debug('A climatisation request is active. Setting the electric climatisation climate mode to new wanted state (if present).')
            if self.vehicle._wantedStateOfProperty.get('climatisation',{}).get('electric_climatisation', None)!=None:
                return self.vehicle._wantedStateOfProperty.get('climatisation',{}).get('electric_climatisation', None)
        return self.vehicle.electric_climatisation

    @property
    def target_temperature(self):
        if self.vehicle._requests.get('climatisation', {}).get('id', False):
            _LOGGER.debug('A climatisation request is active. Setting the climatisation target temperature to new wanted state (if present).')
            if self.vehicle._wantedStateOfProperty.get('climatisation',{}).get('settings',{}).get('climatisation_target_temperature', None)!=None:
                return self.vehicle._wantedStateOfProperty.get('climatisation',{}).get('settings',{}).get('climatisation_target_temperature', None)
        return self.vehicle.climatisation_target_temperature

    async def set_temperature(self, temperature):
        await self.vehicle.set_climatisation_one_setting('targetTemperatureInCelsius' ,temperature)

    async def set_hvac_mode(self, hvac_mode):
        if hvac_mode:
            await self.vehicle.set_climatisation('electric')
        else:
            await self.vehicle.set_climatisation('off')

class AuxiliaryClimatisationClimate(Climate):
    def __init__(self):
        super().__init__(attr="auxiliary_climatisation", name="Auxiliary Climatisation", icon="mdi:radiator")

    @property
    def hvac_mode(self):
        if self.vehicle._requests.get('climatisation', {}).get('id', False):
            _LOGGER.debug('A climatisation request is active. Setting the auxiliary climatisation climate mode to new wanted state (if present).')
            if self.vehicle._wantedStateOfProperty.get('climatisation',{}).get('auxiliary_climatisation', None)!=None:
                return self.vehicle._wantedStateOfProperty.get('climatisation',{}).get('auxiliary_climatisation', None)
        return self.vehicle.auxiliary_climatisation

    @property
    def target_temperature(self):
        if self.vehicle._requests.get('climatisation', {}).get('id', False):
            _LOGGER.debug('A climatisation request is active. Setting the climatisation target temperature to new wanted state (if present).')
            if self.vehicle._wantedStateOfProperty.get('climatisation',{}).get('settings',{}).get('climatisation_target_temperature', None)!=None:
                return self.vehicle._wantedStateOfProperty.get('climatisation',{}).get('settings',{}).get('climatisation_target_temperature', None)
        return self.vehicle.climatisation_target_temperature

    async def set_temperature(self, temperature):
        await self.vehicle.set_climatisation_one_setting('targetTemperatureInCelsius' ,temperature)

    async def set_hvac_mode(self, hvac_mode):
        if hvac_mode:
            await self.vehicle.set_climatisation('auxiliary_start')
        else:
            await self.vehicle.set_climatisation('auxiliary_stop')


class CombustionClimatisationClimate(Climate):
    def __init__(self):
        super().__init__(attr="pheater_heating", name="Parking Heater Climatisation", icon="mdi:radiator")

    def configurate(self, **config):
        self.spin = config.get('spin', '')
        self.duration = config.get('combustionengineheatingduration', 30)

    @property
    def hvac_mode(self):
        return self.vehicle.pheater_heating

    @property
    def target_temperature(self):
        return self.vehicle.climatisation_target_temperature

    async def set_temperature(self, temperature):
        await self.vehicle.setClimatisationTargetTemperature(temperature)

    async def set_hvac_mode(self, hvac_mode):
        if hvac_mode:
            await self.vehicle.pheater_climatisation(spin=self.spin, duration=self.duration, mode='heating')
        else:
            await self.vehicle.pheater_climatisation(spin=self.spin, mode='off')


class Position(Instrument):
    def __init__(self):
        super().__init__(component="device_tracker", attr="position", name="Position")

    @property
    def is_mutable(self) -> bool:
        return False

    @property
    def state(self):
        state = super().state #or {}
        return (
            state.get("lat", "?"),
            state.get("lng", "?"),
            state.get("address", "?"),
            state.get("timestamp", None),
        )

    @property
    def str_state(self) -> tuple:
        state = super().state #or {}
        ts = state.get("timestamp", None)
        if isinstance(ts, str):
            time = str(datetime.strptime(ts,'%Y-%m-%dT%H:%M:%SZ').astimezone(tz=None))
        elif isinstance(ts, datetime):
            time = str(ts.astimezone(tz=None))
        else:
            time = None
        return (
            state.get("lat", "?"),
            state.get("lng", "?"),
            state.get("address", "?"),
            time,
        )


class DoorLock(Instrument):
    def __init__(self):
        super().__init__(component="lock", attr="door_locked", name="Door locked")

    def configurate(self, **config):
        self.spin = config.get('spin', '')

    @property
    def is_mutable(self) -> bool:
        return True

    @property
    def str_state(self) -> str:
        return "Locked" if self.state else "Unlocked"

    @property
    def state(self):
        return self.vehicle.door_locked

    @property
    def is_locked(self):
        return self.state

    async def lock(self):
        try:
            response = await self.vehicle.set_lock('lock', self.spin)
            #await self.vehicle.update()
            if self.callback is not None:
                self.callback()
            return response
        except Exception as e:
            _LOGGER.error(f"Lock failed: {e}")
            return False

    async def unlock(self):
        try:
            response = await self.vehicle.set_lock('unlock', self.spin)
            #await self.vehicle.update()
            if self.callback is not None:
                self.callback()
            return response
        except Exception as e:
            _LOGGER.error(f"Unlock failed: {e}")
            return False

    @property
    def attributes(self):
        return dict(last_result = self.vehicle.lock_action_status)


"""class TrunkLock(Instrument):
    def __init__(self):
        super().__init__(component="lock", attr="trunk_locked", name="Trunk locked")

    @property
    def is_mutable(self):
        return True

    @property
    def str_state(self):
        return "Locked" if self.state else "Unlocked"

    @property
    def state(self):
        return self.vehicle.trunk_locked

    @property
    def is_locked(self):
        return self.state

    #async def lock(self):
    #    return None

    #async def unlock(self):
    #    return None
"""
# Switches
class RequestHonkAndFlash(Switch):
    def __init__(self):
        super().__init__(attr="request_honkandflash", name="Start honking and flashing", icon="mdi:car-emergency")

    @property
    def state(self):
        return self.vehicle.request_honkandflash

    async def turn_on(self) -> None:
        await self.vehicle.set_honkandflash('honkandflash')
        #await self.vehicle.update()
        if self.callback is not None:
            self.callback()

    async def turn_off(self) -> None:
        pass

    @property
    def assumed_state(self) -> bool:
        return False

    @property
    def attributes(self) -> dict:
        return dict(last_result = self.vehicle.honkandflash_action_status)


class RequestFlash(Switch):
    def __init__(self):
        super().__init__(attr="request_flash", name="Start flashing", icon="mdi:car-parking-lights")

    @property
    def state(self):
        return self.vehicle.request_flash

    async def turn_on(self) -> None:
        await self.vehicle.set_honkandflash('flash')
        #await self.vehicle.update()
        if self.callback is not None:
            self.callback()

    async def turn_off(self) -> None:
        pass

    @property
    def assumed_state(self) -> bool:
        return False

    @property
    def attributes(self) -> dict:
        return dict(last_result = self.vehicle.honkandflash_action_status)


class RequestRefresh(Switch):
    def __init__(self):
        super().__init__(attr="refresh_data", name="Request wakeup vehicle", icon="mdi:car-connected")

    @property
    def state(self):
        if self.vehicle.refresh_data != None:
            status = self.vehicle.refresh_data
            if status:
                return True
        return False #self.vehicle.refresh_data

    async def turn_on(self) -> None:
        _LOGGER.debug('User has called RequestRefresh().')
        await self.vehicle.set_refresh()
        #await self.vehicle.update(updateType=1) #full update after set_refresh
        #if self.callback is not None:
        #    self.callback()

    async def turn_off(self) -> None:
        pass

    @property
    def assumed_state(self) -> bool:
        return False

    @property
    def attributes(self) -> dict:
        return dict(last_result = self.vehicle.refresh_action_status)

class RequestUpdate(Switch):
    def __init__(self):
        super().__init__(attr="update_data", name="Request full update", icon="mdi:timer-refresh")

    @property
    def state(self) -> bool:
        return False #self.vehicle.update

    async def turn_on(self) -> None:
        _LOGGER.debug('User has called RequestUpdate().')
        await self.vehicle.update(updateType=1) #full update after set_refresh
        if self.callback is not None:
            self.callback()

    async def turn_off(self) -> None:
        pass

    @property
    def assumed_state(self) -> bool:
        return False

    #@property
    #def attributes(self):
    #    return dict()


class RequestUpdateButton(Button): #RequestUpdate as a button (because some users prefer a button)
    def __init__(self):
        super().__init__(attr="update_data_button", name="Request full update button", icon="mdi:timer-refresh")

    async def press(self) -> None:
        _LOGGER.debug('User has called RequestUpdateButton().')
        await self.vehicle.update(updateType=1) #full update after set_refresh
        if self.callback is not None:
            self.callback()

    @property
    def is_supported(self):
        supported = 'is_update_data_supported'
        if hasattr(self.vehicle, supported):
            return getattr(self.vehicle, supported)
        else:
            return False

class RequestRefreshButton(Button): #RequestRefresh as a button (because some users prefer a button)
    def __init__(self):
        super().__init__(attr="refresh_data_button", name="Request wakeup vehicle button", icon="mdi:car-connected")

    async def press(self) -> None:
        _LOGGER.debug('User has called RequestRefreshButton().')
        await self.vehicle.set_refresh()
        #await self.vehicle.update(updateType=1) #full update after set_refresh
        #if self.callback is not None:
        #    self.callback()

    @property
    def is_supported(self):
        supported = 'is_refresh_data_supported'
        if hasattr(self.vehicle, supported):
            return getattr(self.vehicle, supported)
        else:
            return False


class ElectricClimatisation(Switch):
    def __init__(self):
        super().__init__(attr="electric_climatisation", name="Electric Climatisation", icon="mdi:radiator")

    @property
    def state(self):
        if self.vehicle._requests.get('climatisation', {}).get('id', False):
            _LOGGER.debug('A climatisation request is active. Setting the electric climatisation switch to new wanted state (if present).')
            if self.vehicle._wantedStateOfProperty.get('climatisation',{}).get('electric_climatisation', None)!=None:
                return self.vehicle._wantedStateOfProperty.get('climatisation',{}).get('electric_climatisation', None)
        return self.vehicle.electric_climatisation

    async def turn_on(self):
        await self.vehicle.set_climatisation(mode = 'electric')
        #await self.vehicle.update()

    async def turn_off(self):
        await self.vehicle.set_climatisation(mode = 'off')
        #await self.vehicle.update()

    @property
    def assumed_state(self) -> bool:
        return False

    @property
    def attributes(self) -> dict:
        attrs = {}
        if self.vehicle.is_electric_climatisation_attributes_supported:
            attrs = self.vehicle.electric_climatisation_attributes
            attrs['last_result'] = self.vehicle.climater_action_status
        else:
            attrs['last_result'] = self.vehicle.climater_action_status
        return attrs


class AuxiliaryClimatisation(Switch):
    def __init__(self):
        super().__init__(attr="auxiliary_climatisation", name="Auxiliary Climatisation", icon="mdi:radiator")

    def configurate(self, **config):
        self.spin = config.get('spin', '')

    @property
    def state(self):
        if self.vehicle._requests.get('climatisation', {}).get('id', False):
            _LOGGER.debug('A climatisation request is active. Setting the auxiliary climatisation switch to new wanted state (if present).')
            if self.vehicle._wantedStateOfProperty.get('climatisation',{}).get('auxiliary_climatisation', None)!=None:
                return self.vehicle._wantedStateOfProperty.get('climatisation',{}).get('auxiliary_climatisation', None)
        return self.vehicle.auxiliary_climatisation

    async def turn_on(self) -> None:
        await self.vehicle.set_climatisation(mode = 'auxiliary_start', spin = self.spin)
        #await self.vehicle.update()

    async def turn_off(self) -> None:
        await self.vehicle.set_climatisation(mode = 'auxiliary_stop')
        #await self.vehicle.update()

    @property
    def assumed_state(self) -> bool:
        return False

    @property
    def attributes(self) -> dict:
        return dict(last_result = self.vehicle.climater_action_status)


class Charging(Switch):
    def __init__(self):
        super().__init__(attr="charging", name="Charging", icon="mdi:battery")

    @property
    def state(self):
        if self.vehicle._requests.get('batterycharge', {}).get('id', False):
            _LOGGER.debug('A charging request is active. Setting the charging switch to new wanted state (if present).')
            if self.vehicle._wantedStateOfProperty.get('batterycharge',{}).get('charging', None)!=None:
                return self.vehicle._wantedStateOfProperty.get('batterycharge',{}).get('charging', None)
        return self.vehicle.charging

    async def turn_on(self):
        await self.vehicle.set_charger('start')
        #await self.vehicle.update()

    async def turn_off(self):
        await self.vehicle.set_charger('stop')
        #await self.vehicle.update()

    @property
    def assumed_state(self):
        return False

    @property
    def attributes(self):
        return dict(last_result = self.vehicle.charger_action_status)


class WindowHeater(Switch):
    def __init__(self):
        super().__init__(attr="window_heater", name="Window Heater", icon="mdi:car-defrost-rear")

    @property
    def state(self):
        if self.vehicle._requests.get('climatisation', {}).get('id', False):
            _LOGGER.debug('A climatisation request is active. Setting the window heater switch to new wanted state (if present).')
            if self.vehicle._wantedStateOfProperty.get('climatisation',{}).get('window_heater', None)!=None:
                return self.vehicle._wantedStateOfProperty.get('climatisation',{}).get('window_heater', None)
        return self.vehicle.window_heater

    async def turn_on(self):
        await self.vehicle.set_window_heating('start')
        #await self.vehicle.update()

    async def turn_off(self):
        await self.vehicle.set_window_heating('stop')
        #await self.vehicle.update()

    @property
    def assumed_state(self):
        return False


    @property
    def attributes(self):
        return dict(last_result = self.vehicle.climater_action_status)


class SeatHeating(Switch):
    def __init__(self):
        super().__init__(attr="seat_heating", name="Seat Heating", icon="mdi:seat-recline-normal")

    @property
    def state(self):
        #if self.vehicle._requests.get('climatisation', {}).get('id', False):
        #    _LOGGER.debug('A climatisation request is active. Setting the seat heating switch to new wanted state (if present).')
        #    if self.vehicle._wantedStateOfProperty.get('climatisation',{}).get('seat_heating', None)!=None:
        #        return self.vehicle._wantedStateOfProperty.get('climatisation',{}).get('seat_heating', None)
        return self.vehicle.seat_heating

    async def turn_on(self):
        #await self.vehicle.set_seat_heating('start')
        #await self.vehicle.update()
        pass

    async def turn_off(self):
        #await self.vehicle.set_seat_heating('stop')
        #await self.vehicle.update()
        pass

    @property
    def assumed_state(self):
        return False

    #@property
    #def attributes(self):
    #    return dict(last_result = self.vehicle.climater_action_status)


class BatteryClimatisation(Switch):
    def __init__(self):
        super().__init__(attr="climatisation_without_external_power", name="Climatisation setting off-grid climatisation", icon="mdi:battery-arrow-down")

    @property
    def state(self):
        if self.vehicle._requests.get('climatisation', {}).get('id', False):
            _LOGGER.debug('A climatisation request is active. Setting the off-grid climatisation switch to new wanted state (if present).')
            if self.vehicle._wantedStateOfProperty.get('climatisation',{}).get('settings',{}).get('climatisationWithoutExternalPower', None)!=None:
                return self.vehicle._wantedStateOfProperty.get('climatisation',{}).get('settings',{}).get('climatisationWithoutExternalPower', None)
        return self.vehicle.climatisation_without_external_power

    async def turn_on(self):
        #await self.vehicle.set_battery_climatisation(True) # will become obsolete
        await self.vehicle.set_climatisation_one_setting('climatisationWithoutExternalPower',True)
        #await self.vehicle.update()

    async def turn_off(self):
        #await self.vehicle.set_battery_climatisation(False) # will become obsolete
        await self.vehicle.set_climatisation_one_setting('climatisationWithoutExternalPower',False)
        #await self.vehicle.update()

    @property
    def assumed_state(self):
        return False

    @property
    def attributes(self):
        return dict(last_result = self.vehicle.climater_action_status)

class ClimatisationSettingZoneFrontLeft(Switch):
    def __init__(self):
        super().__init__(attr="climatisation_zone_front_left", name="Climatisation setting zone front left", icon="mdi:car-seat-heater")

    @property
    def state(self):
        if self.vehicle._requests.get('climatisation', {}).get('id', False):
            _LOGGER.debug('A climatisation request is active. Setting the zone front left enabled switch to new wanted state (if present).')
            if self.vehicle._wantedStateOfProperty.get('climatisation',{}).get('settings',{}).get('zoneFrontLeftEnabled', None)!=None:
                return self.vehicle._wantedStateOfProperty.get('climatisation',{}).get('settings',{}).get('zoneFrontLeftEnabled', None)
        return self.vehicle.climatisation_zone_front_left

    async def turn_on(self):
        await self.vehicle.set_climatisation_one_setting('zoneFrontLeftEnabled',True)
        #await self.vehicle.update()

    async def turn_off(self):
        await self.vehicle.set_climatisation_one_setting('zoneFrontLeftEnabled',False)
        #await self.vehicle.update()

    @property
    def assumed_state(self):
        return False

    @property
    def attributes(self):
        return dict(last_result = self.vehicle.climater_action_status)

class ClimatisationSettingZoneFrontRight(Switch):
    def __init__(self):
        super().__init__(attr="climatisation_zone_front_right", name="Climatisation setting zone front right", icon="mdi:car-seat-heater")

    @property
    def state(self):
        if self.vehicle._requests.get('climatisation', {}).get('id', False):
            _LOGGER.debug('A climatisation request is active. Setting the zone front right enabled switch to new wanted state (if present).')
            if self.vehicle._wantedStateOfProperty.get('climatisation',{}).get('settings',{}).get('zoneFrontRightEnabled', None)!=None:
                return self.vehicle._wantedStateOfProperty.get('climatisation',{}).get('settings',{}).get('zoneFrontRightEnabled', None)
        return self.vehicle.climatisation_zone_front_right

    async def turn_on(self):
        await self.vehicle.set_climatisation_one_setting('zoneFrontRightEnabled',True)
        #await self.vehicle.update()

    async def turn_off(self):
        await self.vehicle.set_climatisation_one_setting('zoneFrontRightEnabled',False)
        #await self.vehicle.update()

    @property
    def assumed_state(self):
        return False

    @property
    def attributes(self):
        return dict(last_result = self.vehicle.climater_action_status)


class ClimatisationSettingAtUnlock(Switch):
    def __init__(self):
        super().__init__(attr="climatisation_at_unlock", name="Climatisation setting climatisation at unlock", icon="mdi:radiator")

    @property
    def state(self):
        if self.vehicle._requests.get('climatisation', {}).get('id', False):
            _LOGGER.debug('A climatisation request is active. Setting the climatisation at unlock switch to new wanted state (if present).')
            if self.vehicle._wantedStateOfProperty.get('climatisation',{}).get('settings',{}).get('climatisationAtUnlock', None)!=None:
                return self.vehicle._wantedStateOfProperty.get('climatisation',{}).get('settings',{}).get('climatisationAtUnlock', None)
        return self.vehicle.climatisation_at_unlock

    async def turn_on(self):
        await self.vehicle.set_climatisation_one_setting('climatisationAtUnlock',True)
        #await self.vehicle.update()

    async def turn_off(self):
        await self.vehicle.set_climatisation_one_setting('climatisationAtUnlock',False)
        #await self.vehicle.update()

    @property
    def assumed_state(self):
        return False

    @property
    def attributes(self):
        return dict(last_result = self.vehicle.climater_action_status)


class ClimatisationSettingWindowHeatingEnabled(Switch):
    def __init__(self):
        super().__init__(attr="climatisation_window_heating_enabled", name="Climatisation setting window heating enabled", icon="mdi:car-defrost-rear")

    @property
    def state(self):
        if self.vehicle._requests.get('climatisation', {}).get('id', False):
            _LOGGER.debug('A climatisation request is active. Setting the window heating enabled switch to new wanted state (if present).')
            if self.vehicle._wantedStateOfProperty.get('climatisation',{}).get('settings',{}).get('windowHeatingEnabled', None)!=None:
                return self.vehicle._wantedStateOfProperty.get('climatisation',{}).get('settings',{}).get('windowHeatingEnabled', None)
        return self.vehicle.climatisation_window_heating_enabled

    async def turn_on(self):
        await self.vehicle.set_climatisation_one_setting('windowHeatingEnabled',True)
        #await self.vehicle.update()

    async def turn_off(self):
        await self.vehicle.set_climatisation_one_setting('windowHeatingEnabled',False)
        #await self.vehicle.update()

    @property
    def assumed_state(self):
        return False

    @property
    def attributes(self):
        return dict(last_result = self.vehicle.climater_action_status)


class PHeaterHeating(Switch):
    def __init__(self):
        super().__init__(attr="pheater_heating", name="Parking Heater Heating", icon="mdi:radiator")

    def configurate(self, **config):
        self.spin = config.get('spin', '')
        self.duration = config.get('combustionengineheatingduration', 30)

    @property
    def state(self):
        return self.vehicle.pheater_heating

    async def turn_on(self):
        await self.vehicle.set_pheater(mode='heating', spin=self.spin)
        #await self.vehicle.update()

    async def turn_off(self):
        await self.vehicle.set_pheater(mode='off', spin=self.spin)
        #await self.vehicle.update()

    @property
    def assumed_state(self):
        return False

    @property
    def attributes(self):
        return dict(last_result = self.vehicle.pheater_action_status)


class PHeaterVentilation(Switch):
    def __init__(self):
        super().__init__(attr="pheater_ventilation", name="Parking Heater Ventilation", icon="mdi:radiator")

    def configurate(self, **config):
        self.spin = config.get('spin', '')
        self.duration = config.get('combustionengineclimatisationduration', 30)

    @property
    def state(self):
        return self.vehicle.pheater_ventilation

    async def turn_on(self):
        await self.vehicle.set_pheater(mode='ventilation', spin=self.spin)
        #await self.vehicle.update()

    async def turn_off(self):
        await self.vehicle.set_pheater(mode='off', spin=self.spin)
        #await self.vehicle.update()

    @property
    def assumed_state(self):
        return False

    @property
    def attributes(self):
        return dict(last_result = self.vehicle.pheater_action_status)


class SlowCharge(Switch):
    def __init__(self):
        super().__init__(attr="slow_charge", name="Slow charge", icon="mdi:battery")

    @property
    def state(self):
        if self.vehicle._requests.get('batterycharge', {}).get('id', False):
            _LOGGER.debug('A charging request is active. Setting the slow charge switch to new wanted state (if present).')
            if self.vehicle._wantedStateOfProperty.get('batterycharge',{}).get('settings',{}).get('slow_charge', None)!=None:
                return self.vehicle._wantedStateOfProperty.get('batterycharge',{}).get('settings',{}).get('slow_charge', None)
        return self.vehicle.slow_charge

    async def turn_on(self):
        await self.vehicle.set_charger_current('reduced')
        #await self.vehicle.update()

    async def turn_off(self):
        await self.vehicle.set_charger_current('maximum')
        #await self.vehicle.update()

    @property
    def assumed_state(self):
        return False


    @property
    def attributes(self):
        return dict(last_result = self.vehicle.charger_action_status)


class Warnings(Sensor):
    def __init__(self):
        super().__init__(attr="warnings", name="Warnings", icon="mdi:alarm-light")

    @property
    def state(self):
        return self.vehicle.warnings

    @property
    def assumed_state(self):
        return False

    @property
    def attributes(self):
        attrs = {'warnings': 'No warnings'}
        if self.vehicle.attrs.get('warninglights', {}).get('statuses',[]):
            warningTextList = []
            for elem in self.vehicle.attrs['warninglights']['statuses']:
                if isinstance(elem, dict):
                    if elem.get('text',''):
                        warningTextList.append(elem.get('text',''))
            attrs['warnings'] = warningTextList
        return attrs

"""class Engine(Switch):
    def __init__(self):
        super().__init__(attr="engine", name="Engine", icon="mdi:engine")

    @property
    def state(self):
        return self.vehicle.engine

    async def turn_on(self):
        _LOGGER.exception(f'turn_on not defined for "{self.attr}"')
        #await self.vehicle.set_engine('start')
        #await self.vehicle.update() # hinterher auskommentieren

    async def turn_off(self):
        _LOGGER.exception(f'turn_off not defined for "{self.attr}"')
        #await self.vehicle.set_engine('stop')
        await self.vehicle.update() # hinterher auskommentieren

    @property
    def assumed_state(self):
        return False


    @property
    def attributes(self):
        return dict(last_result = self.vehicle.engine_action_status)
"""
class ChargingBatteryCare(Switch):
    def __init__(self):
        super().__init__(attr="charging_battery_care", name="Charging battery care", icon="mdi:battery-heart-variant")

    @property
    def state(self):
        if self.vehicle._requests.get('batterycharge', {}).get('id', False):
            _LOGGER.debug('A charging request is active. Setting the charging battery care switch to new wanted state (if present).')
            if self.vehicle._wantedStateOfProperty.get('batterycharge',{}).get('settings',{}).get('charging_battery_care', None)!=None:
                return self.vehicle._wantedStateOfProperty.get('batterycharge',{}).get('settings',{}).get('charging_battery_care', None)
        return self.vehicle.charging_battery_care

    async def turn_on(self):
        #_LOGGER.exception(f'turn_on not defined for "{self.attr}"')
        await self.vehicle.set_battery_care(True)
        #await self.vehicle.update() 

    async def turn_off(self):
        #_LOGGER.exception(f'turn_off not defined for "{self.attr}"')
        await self.vehicle.set_battery_care(False)
        #await self.vehicle.update() 

    @property
    def assumed_state(self):
        return False


    #@property
    #def attributes(self):
    #    return dict(last_result = self.vehicle.chargingBatteryCare_action_status)

class ClimatisationTimer1(Switch):
    def __init__(self):
        super().__init__(attr="climatisation_timer1", name="Climatisation timer 1", icon="mdi:radiator")

    def configurate(self, **config):
        self.spin = config.get('spin', '')

    @property
    def state(self):
        if self.vehicle.climatisation_timer1 != None:
            status = self.vehicle.climatisation_timer1.get("enabled", "")
            if status:
                return True
        return False

    async def turn_on(self):
        if self.vehicle._relevantCapabilties.get('climatisationTimers', {}).get('active', False):
            await self.vehicle.set_climatisation_timer_active(id=1, action="on")
        else:
            await self.vehicle.set_auxiliary_heating_timer_active(id=1, action="on", spin=self.spin)
        #await self.vehicle.update()

    async def turn_off(self):
        if self.vehicle._relevantCapabilties.get('climatisationTimers', {}).get('active', False):
            await self.vehicle.set_climatisation_timer_active(id=1, action="off")
        else:
            await self.vehicle.set_auxiliary_heating_timer_active(id=1, action="off", spin=self.spin)
        #await self.vehicle.update()

    @property
    def assumed_state(self):
        return False

    @property
    def attributes(self):
        return dict(self.vehicle.climatisation_timer1)

class ClimatisationTimer2(Switch):
    def __init__(self):
        super().__init__(attr="climatisation_timer2", name="Climatisation timer 2", icon="mdi:radiator")

    def configurate(self, **config):
        self.spin = config.get('spin', '')

    @property
    def state(self):
        if self.vehicle.climatisation_timer2 != None:
            status = self.vehicle.climatisation_timer2.get("enabled", "")
            if status:
                return True
        return False

    async def turn_on(self):
        if self.vehicle._relevantCapabilties.get('climatisationTimers', {}).get('active', False):
            await self.vehicle.set_climatisation_timer_active(id=2, action="on")
        else:
            await self.vehicle.set_auxiliary_heating_timer_active(id=2, action="on", spin=self.spin)
        #await self.vehicle.update()

    async def turn_off(self):
        if self.vehicle._relevantCapabilties.get('climatisationTimers', {}).get('active', False):
            await self.vehicle.set_climatisation_timer_active(id=2, action="off")
        else:
            await self.vehicle.set_auxiliary_heating_timer_active(id=2, action="off", spin=self.spin)
        #await self.vehicle.update()

    @property
    def assumed_state(self):
        return False

    @property
    def attributes(self):
        return dict(self.vehicle.climatisation_timer2)

class ClimatisationTimer3(Switch):
    def __init__(self):
        super().__init__(attr="climatisation_timer3", name="Climatisation timer 3", icon="mdi:radiator")

    def configurate(self, **config):
        self.spin = config.get('spin', '')

    @property
    def state(self):
        if self.vehicle.climatisation_timer3 != None:
            status = self.vehicle.climatisation_timer3.get("enabled", "")
            if status:
                return True
        return False

    async def turn_on(self):
        if self.vehicle._relevantCapabilties.get('climatisationTimers', {}).get('active', False):
            await self.vehicle.set_climatisation_timer_active(id=3, action="on")
        else:
            await self.vehicle.set_auxiliary_heating_timer_active(id=3, action="on", spin=self.spin)
        #await self.vehicle.update()

    async def turn_off(self):
        if self.vehicle._relevantCapabilties.get('climatisationTimers', {}).get('active', False):
            await self.vehicle.set_climatisation_timer_active(id=3, action="off")
        else:
            await self.vehicle.set_auxiliary_heating_timer_active(id=3, action="off", spin=self.spin)
        #await self.vehicle.update()

    @property
    def assumed_state(self):
        return False

    @property
    def attributes(self):
        return dict(self.vehicle.climatisation_timer3)

class DepartureTimer1(Switch):
    def __init__(self):
        super().__init__(attr="departure1", name="Departure timer 1", icon="mdi:radiator")

    def configurate(self, **config):
        self.spin = config.get('spin', '')

    @property
    def state(self):
        if self.vehicle.departure1 != None:
            status = self.vehicle.departure1.get("enabled", "")
            if status:
                return True
        #else:
        return False

    async def turn_on(self):
        await self.vehicle.set_timer_active(id=1, action="on")
        #await self.vehicle.update()

    async def turn_off(self):
        await self.vehicle.set_timer_active(id=1, action="off")
        #await self.vehicle.update()

    @property
    def assumed_state(self):
        return False

    @property
    def attributes(self):
        return dict(self.vehicle.departure1)


class DepartureTimer2(Switch):
    def __init__(self):
        super().__init__(attr="departure2", name="Departure timer 2", icon="mdi:radiator")

    def configurate(self, **config):
        self.spin = config.get('spin', '')

    @property
    def state(self):
        if self.vehicle.departure2 != None:
            status = self.vehicle.departure2.get("enabled", "")
            if status:
                return True
        #else:
        return False

    async def turn_on(self):
        await self.vehicle.set_timer_active(id=2, action="on")
        #await self.vehicle.update()

    async def turn_off(self):
        await self.vehicle.set_timer_active(id=2, action="off")
        #await self.vehicle.update()

    @property
    def assumed_state(self):
        return False

    @property
    def attributes(self):
        return dict(self.vehicle.departure2)

class DepartureTimer3(Switch):
    def __init__(self):
        super().__init__(attr="departure3", name="Departure timer 3", icon="mdi:radiator")

    def configurate(self, **config):
        self.spin = config.get('spin', '')

    @property
    def state(self):
        if self.vehicle.departure3 != None:
            status = self.vehicle.departure3.get("enabled", "")
            if status:
                return True
        #else:
        return False

    async def turn_on(self):
        await self.vehicle.set_timer_active(id=3, action="on")
        #await self.vehicle.update()

    async def turn_off(self):
        await self.vehicle.set_timer_active(id=3, action="off")
        #await self.vehicle.update()

    @property
    def assumed_state(self):
        return False

    @property
    def attributes(self):
        return dict(self.vehicle.departure3)

class DepartureProfile1(Switch):
    def __init__(self):
        super().__init__(attr="departure_profile1", name="Departure profile 1", icon="mdi:radiator")

    def configurate(self, **config):
        self.spin = config.get('spin', '')

    @property
    def state(self):
        status = self.vehicle.departure_profile1.get("enabled", "")
        if status:
            return True
        else:
            return False

    async def turn_on(self):
        await self.vehicle.set_departure_profile_active(id=1, action="on")
        #await self.vehicle.update()

    async def turn_off(self):
        await self.vehicle.set_departure_profile_active(id=1, action="off")
        #await self.vehicle.update()

    @property
    def assumed_state(self):
        return False

    @property
    def attributes(self):
        return dict(convertTimerUtcToLocal(self.vehicle.departure_profile1))

class DepartureProfile2(Switch):
    def __init__(self):
        super().__init__(attr="departure_profile2", name="Departure profile 2", icon="mdi:radiator")

    def configurate(self, **config):
        self.spin = config.get('spin', '')

    @property
    def state(self):
        status = self.vehicle.departure_profile2.get("enabled", "")
        if status:
            return True
        else:
            return False

    async def turn_on(self):
        await self.vehicle.set_departure_profile_active(id=2, action="on")
        #await self.vehicle.update()

    async def turn_off(self):
        await self.vehicle.set_departure_profile_active(id=2, action="off")
        #await self.vehicle.update()

    @property
    def assumed_state(self):
        return False

    @property
    def attributes(self):
        return dict(convertTimerUtcToLocal(self.vehicle.departure_profile2))

class DepartureProfile3(Switch):
    def __init__(self):
        super().__init__(attr="departure_profile3", name="Departure profile 3", icon="mdi:radiator")

    def configurate(self, **config):
        self.spin = config.get('spin', '')

    @property
    def state(self):
        status = self.vehicle.departure_profile3.get("enabled", "")
        if status:
            return True
        else:
            return False

    async def turn_on(self):
        await self.vehicle.set_departure_profile_active(id=3, action="on")
        #await self.vehicle.update()

    async def turn_off(self):
        await self.vehicle.set_departure_profile_active(id=3, action="off")
        #await self.vehicle.update()

    @property
    def assumed_state(self):
        return False

    @property
    def attributes(self):
        return dict(convertTimerUtcToLocal(self.vehicle.departure_profile3))


class RequestResults(Sensor):
    def __init__(self):
        super().__init__(attr="request_results", name="Request results", icon="mdi:chat-alert", unit=None)

    @property
    def state(self):
        if self.vehicle.request_results.get('state', False):
            return self.vehicle.request_results.get('state')
        return 'N/A'

    @property
    def assumed_state(self):
        return False

    @property
    def attributes(self):
        return dict(self.vehicle.request_results)

class ChargingState(BinarySensor):
    def __init__(self):
        super().__init__(attr="charging_state", name="Charging state", icon="mdi:battery-charging", device_class='power')

    @property
    def state(self):
        return self.vehicle.charging_state

    @property
    def assumed_state(self):
        return False

    @property
    def attributes(self):
        attr = {}
        #state = self.vehicle.attrs.get('charging', {}).get('status', {}).get('state', '')
        #type = self.vehicle.attrs.get('charging', {}).get('status', {}).get('charging', {}).get('type', '')
        #mode = self.vehicle.attrs.get('charging', {}).get('status', {}).get('charging', {}).get('mode', '')
        state = self.vehicle.attrs.get('mycar', {}).get('services', {}).get('charging', {}).get('status', '')
        type = self.vehicle.attrs.get('charging', {}).get('status', {}).get('charging', {}).get('type', '')
        mode = self.vehicle.attrs.get('mycar', {}).get('services', {}).get('charging', {}).get('chargeMode', '')
        if state in {'charging','Charging', 'conservation','Conservation'}:
            attr['state']=state.lower()
            if type != '':
                attr['type']=type
            if mode != '':
                attr['mode']=mode
        return attr

class AreaAlarm(BinarySensor):
    def __init__(self):
        super().__init__(attr="area_alarm", name="Area alarm", icon="mdi:alarm-light", device_class=None)

    @property
    def state(self):
        return self.vehicle.area_alarm

    @property
    def assumed_state(self):
        return False

    @property
    def attributes(self):
        attr = {}
        type = self.vehicle.attrs.get('areaAlarm', {}).get('type', '')
        zones = self.vehicle.attrs.get('areaAlarm', {}).get('zones', [])
        timestamp = self.vehicle.attrs.get('areaAlarm', {}).get('timestamp', 0)
        if type != '':
            attr['type']=type
            if len(zones) > 0:
                attr['zone']=zones[0]
            if timestamp != 0:
                attr['timestamp']=timestamp
        return attr

def create_instruments():
    return [
        Position(),
        DoorLock(),
        #TrunkLock(),
        RequestFlash(),
        RequestHonkAndFlash(),
        RequestRefresh(),
        RequestUpdate(),
        RequestRefreshButton(),
        RequestUpdateButton(),
        WindowHeater(),
        BatteryClimatisation(),
        ClimatisationSettingZoneFrontLeft(),
        ClimatisationSettingZoneFrontRight(),
        ClimatisationSettingAtUnlock(),
        ClimatisationSettingWindowHeatingEnabled(),
        ElectricClimatisation(),
        AuxiliaryClimatisation(),
        PHeaterVentilation(),
        PHeaterHeating(),
        ElectricClimatisationClimate(),
        AuxiliaryClimatisationClimate(),
        #CombustionClimatisationClimate(),
        Charging(),
        ChargingBatteryCare(),
        Warnings(),
        SlowCharge(),
        RequestResults(),
        #Engine(),
        ClimatisationTimer1(),
        ClimatisationTimer2(),
        ClimatisationTimer3(),
        DepartureTimer1(),
        DepartureTimer2(),
        DepartureTimer3(),
        DepartureProfile1(),
        DepartureProfile2(),
        DepartureProfile3(),
        ChargingState(),
        AreaAlarm(),
        Sensor(
            attr="distance",
            name="Odometer",
            icon="mdi:speedometer",
            unit="km",
            device_class="distance"
        ),
        Sensor(
            attr="battery_level",
            name="Battery level",
            icon="mdi:battery",
            unit="%",
            device_class="battery"
        ),
        Sensor(
            attr="min_charge_level",
            name="Minimum charge level",
            icon="mdi:battery-positive",
            unit="%",
            device_class="battery"
        ),
        Sensor(
            attr="target_soc",
            name="Target state of charge",
            icon="mdi:battery-positive",
            unit="%",
            device_class="battery"
        ),
        Sensor(
            attr="adblue_level",
            name="Adblue level",
            icon="mdi:fuel",
            unit="km",
            device_class="distance"
        ),
        Sensor(
            attr="fuel_level",
            name="Fuel level",
            icon="mdi:fuel",
            unit="%",
        ),
        Sensor(
            attr="service_inspection",
            name="Service inspection days",
            icon="mdi:garage",
            unit="days",
        ),
        Sensor(
            attr="service_inspection_distance",
            name="Service inspection distance",
            icon="mdi:garage",
            unit="km",
            device_class="distance"
        ),
        Sensor(
            attr="oil_inspection",
            name="Oil inspection days",
            icon="mdi:oil",
            unit="days",
        ),
        Sensor(
            attr="oil_inspection_distance",
            name="Oil inspection distance",
            icon="mdi:oil",
            unit="km",
            device_class="distance"
        ),
        Sensor(
            attr="last_connected",
            name="Last connected",
            icon="mdi:clock",
            device_class="timestamp"
        ),
        Sensor(
            attr="last_full_update",
            name="Last full update",
            icon="mdi:clock",
            device_class="timestamp"
        ),
        Sensor(
            attr="parking_time",
            name="Parking time",
            icon="mdi:clock",
            device_class="timestamp"
        ),
        Sensor(
            attr="charging_time_left",
            name="Charging time left",
            icon="mdi:battery-charging-100",
            unit="min",
            device_class="duration"
        ),
        Sensor(
            attr="charging_estimated_end_time",
            name="Charging estimated end time",
            icon="mdi:battery-charging-100",
            device_class="timestamp"
        ),
        Sensor(
            attr="charging_power",
            name="Charging power",
            icon="mdi:flash",
            unit="kW",
            device_class="power"
        ),
        Sensor(
            attr="charge_rate",
            name="Charging rate",
            icon="mdi:battery-heart",
            unit="km/h",
            device_class="speed"
        ),
        Sensor(
            attr="electric_range",
            name="Electric range",
            icon="mdi:car-electric",
            unit="km",
            device_class="distance"
        ),
        Sensor(
            attr="combustion_range",
            name="Combustion range",
            icon="mdi:car",
            unit="km",
            device_class="distance"
        ),
        Sensor(
            attr="combined_range",
            name="Combined range",
            icon="mdi:car",
            unit="km",
            device_class="distance"
        ),
        Sensor(
            attr="charge_max_ampere",
            name="Charger max ampere",
            icon="mdi:flash",
            #unit="A",
            #device_class="current"
        ),
        Sensor(
            attr="climatisation_target_temperature",
            name="Climatisation target temperature",
            icon="mdi:thermometer",
            unit="°C",
            device_class="temperature"
        ),
        Sensor(
            attr="climatisation_time_left",
            name="Climatisation time left",
            icon="mdi:clock",
            unit="min",
            device_class="duration"
        ),
        Sensor(
            attr="climatisation_estimated_end_time",
            name="Climatisation estimated end time",
            icon="mdi:clock",
            device_class="timestamp"
        ),
        Sensor(
            attr="trip_last_average_speed",
            name="Last trip average speed",
            icon="mdi:speedometer",
            unit="km/h",
            device_class="speed"
        ),
        Sensor(
            attr="trip_last_average_electric_consumption",
            name="Last trip average electric consumption",
            icon="mdi:car-battery",
            unit="kWh/100km",
            device_class="energy_distance"
        ),
        Sensor(
            attr="trip_last_average_fuel_consumption",
            name="Last trip average fuel consumption",
            icon="mdi:fuel",
            unit="l/100km",
        ),
        Sensor(
            attr="trip_last_duration",
            name="Last trip duration",
            icon="mdi:clock",
            unit="min",
            device_class="duration"
        ),
        Sensor(
            attr="trip_last_length",
            name="Last trip length",
            icon="mdi:map-marker-distance",
            unit="km",
            device_class="distance"
        ),
        Sensor(
            attr="trip_last_recuperation",
            name="Last trip recuperation",
            icon="mdi:battery-plus",
            unit="kWh/100km",
            device_class="energy_distance"
        ),
        Sensor(
            attr="trip_last_average_recuperation",
            name="Last trip average recuperation",
            icon="mdi:battery-plus",
            unit="kWh/100km",
            device_class="energy_distance"
        ),
        Sensor(
            attr="trip_last_average_auxiliary_consumption",
            name="Last trip average auxiliary consumption",
            icon="mdi:flash",
            unit="kWh/100km",
            device_class="energy_distance"
        ),
        Sensor(
            attr="trip_last_average_aux_consumer_consumption",
            name="Last trip average auxiliary consumer consumption",
            icon="mdi:flash",
            unit="kWh/100km",
            device_class="energy_distance"
        ),
        Sensor(
            attr="trip_last_total_electric_consumption",
            name="Last trip total electric consumption",
            icon="mdi:car-battery",
            unit="kWh/100km",
            device_class="energy_distance"
        ),
        Sensor(
            attr="trip_last_cycle_average_speed",
            name="Last cycle average speed",
            icon="mdi:speedometer",
            unit="km/h",
            device_class="speed"
        ),
        Sensor(
            attr="trip_last_cycle_average_electric_consumption",
            name="Last cycle average electric consumption",
            icon="mdi:car-battery",
            unit="kWh/100km",
            device_class="energy_distance"
        ),
        Sensor(
            attr="trip_last_cycle_average_fuel_consumption",
            name="Last cycle average fuel consumption",
            icon="mdi:fuel",
            unit="l/100km",
        ),
        Sensor(
            attr="trip_last_cycle_average_auxiliary_consumption",
            name="Last cycle average auxiliary consumption",
            icon="mdi:flash",
            unit="kWh/100km",
            device_class="energy_distance"
        ),
        Sensor(
            attr="trip_last_cycle_duration",
            name="Last cycle duration",
            icon="mdi:clock",
            unit="min",
            device_class="duration"
        ),
        Sensor(
            attr="trip_last_cycle_length",
            name="Last cycle length",
            icon="mdi:map-marker-distance",
            unit="km",
            device_class="distance"
        ),
        Sensor(
            attr="trip_last_cycle_recuperation",
            name="Last cycle recuperation",
            icon="mdi:battery-plus",
            unit="kWh/100km",
            device_class="energy_distance"
        ),
        Sensor(
            attr="trip_last_cycle_average_recuperation",
            name="Last cycle average recuperation",
            icon="mdi:battery-plus",
            unit="kWh/100km",
            device_class="energy_distance"
        ),
        Sensor(
            attr="trip_last_cycle_average_aux_consumer_consumption",
            name="Last cycle average auxiliary consumer consumption",
            icon="mdi:flash",
            unit="kWh/100km",
            device_class="energy_distance"
        ),
        Sensor(
            attr="trip_last_cycle_total_electric_consumption",
            name="Last cycle total electric consumption",
            icon="mdi:car-battery",
            unit="kWh/100km",
            device_class="energy_distance"
        ),
        Sensor(
            attr="model_image_large",
            name="Model image URL (Large)",
            icon="mdi:file-image",
        ),
        Sensor(
            attr="model_image_small",
            name="Model image URL (Small)",
            icon="mdi:file-image",
        ),
        Sensor(
            attr="pheater_status",
            name="Parking Heater heating/ventilation status",
            icon="mdi:radiator",
        ),
        Sensor(
            attr="pheater_duration",
            name="Parking Heater heating/ventilation duration",
            icon="mdi:timer",
            unit="minutes",
            device_class="duration"
        ),
        Sensor(
            attr="outside_temperature",
            name="Outside temperature",
            icon="mdi:thermometer",
            unit="°C",
            device_class="temperature"
        ),
        Sensor(
            attr="requests_remaining",
            name="Requests remaining",
            icon="mdi:chat-alert",
            unit="",
        ),
        BinarySensor(
            attr="external_power",
            name="External power",
            device_class="power"
        ),
        BinarySensor(
            attr="energy_flow",
            name="Energy flow",
            device_class="power"
        ),
        #BinarySensor(
        #    attr="charging_state",
        #    name="Charging state",
        #    device_class="power"
        #),
        BinarySensor(
            attr="engine",
            name="Engine Status",
            device_class="running",
            icon="mdi:engine"
        ),
        BinarySensor(
            attr="parking_light",
            name="Parking light",
            device_class="light",
            icon="mdi:car-parking-lights"
        ),
        BinarySensor(
            attr="door_locked",
            name="Doors locked",
            device_class="lock",
            reverse_state=False
        ),
        BinarySensor(
            attr="door_closed_left_front",
            name="Door closed left front",
            device_class="door",
            reverse_state=False,
            icon="mdi:car-door"
        ),
        BinarySensor(
            attr="door_closed_right_front",
            name="Door closed right front",
            device_class="door",
            reverse_state=False,
            icon="mdi:car-door"
        ),
        BinarySensor(
            attr="door_closed_left_back",
            name="Door closed left back",
            device_class="door",
            reverse_state=False,
            icon="mdi:car-door"
        ),
        BinarySensor(
            attr="door_closed_right_back",
            name="Door closed right back",
            device_class="door",
            reverse_state=False,
            icon="mdi:car-door"
        ),
        BinarySensor(
            attr="trunk_locked",
            name="Trunk locked",
            device_class="lock",
            reverse_state=False
        ),
        BinarySensor(
            attr="trunk_closed",
            name="Trunk closed",
            device_class="door",
            reverse_state=False
        ),
        BinarySensor(
            attr="hood_closed",
            name="Hood closed",
            device_class="door",
            reverse_state=False
        ),
        BinarySensor(
            attr="charging_cable_connected",
            name="Charging cable connected",
            device_class="plug",
            reverse_state=False
        ),
        BinarySensor(
            attr="charging_cable_locked",
            name="Charging cable locked",
            device_class="lock",
            reverse_state=False
        ),
        BinarySensor(
            attr="sunroof_closed",
            name="Sunroof closed",
            device_class="window",
            reverse_state=False
        ),
        BinarySensor(
            attr="windows_closed",
            name="Windows closed",
            device_class="window",
            reverse_state=False
        ),
        BinarySensor(
            attr="window_closed_left_front",
            name="Window closed left front",
            device_class="window",
            reverse_state=False
        ),
        BinarySensor(
            attr="window_closed_left_back",
            name="Window closed left back",
            device_class="window",
            reverse_state=False
        ),
        BinarySensor(
            attr="window_closed_right_front",
            name="Window closed right front",
            device_class="window",
            reverse_state=False
        ),
        BinarySensor(
            attr="window_closed_right_back",
            name="Window closed right back",
            device_class="window",
            reverse_state=False
        ),
        BinarySensor(
            attr="vehicle_moving",
            name="Vehicle Moving",
            device_class="moving"
        ),
        BinarySensor(
            attr="request_in_progress",
            name="Request in progress",
            device_class="connectivity"
        ),
    ]


class Dashboard:
    def __init__(self, vehicle, **config):
        self._config = config
        self.instruments = [
            instrument
            for instrument in create_instruments()
            if instrument.setup(vehicle, **config)
        ]
        _LOGGER.debug("Supported instruments: " + ", ".join(str(inst.attr) for inst in self.instruments))

