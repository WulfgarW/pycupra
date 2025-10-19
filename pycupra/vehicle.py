#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vehicle class for pycupra."""
import re
import logging
import asyncio
import json
from typing import Any

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from json import dumps as to_json
from collections import OrderedDict
from .utilities import find_path, is_valid_path, convert_datetime_to_string
from .exceptions import (
    SeatConfigException,
    SeatException,
    SeatEULAException,
    SeatServiceUnavailable,
    SeatThrottledException,
    SeatInvalidRequestException,
    SeatRequestInProgressException
)
from .const import (
    APP_URI,
    FIREBASE_STATUS_NOT_INITIALISED,
    FIREBASE_STATUS_ACTIVATED,
    FIREBASE_STATUS_ACTIVATION_FAILED,
    FIREBASE_STATUS_ACTIVATION_STOPPED,
    FIREBASE_STATUS_NOT_WANTED,
)

from .firebase import Firebase, readFCMCredsFile, writeFCMCredsFile

_LOGGER = logging.getLogger(__name__)

DATEZERO = datetime(1970,1,1)
class Vehicle:
    def __init__(self, conn, data):
        _LOGGER.debug(conn.anonymise(f'Creating Vehicle class object with data {data}'))
        self._connection = conn
        self._url = data.get('vin', '')
        self._connectivities = data.get('connectivities', '')
        self._capabilities = data.get('capabilities', [])
        self._specification = data.get('specification', {})
        self._properties = data.get('properties', {})
        self._apibase = APP_URI
        self._secbase = 'https://msg.volkswagen.de'
        self._modelimages = None
        self._discovered = False
        self._dashboard = None
        self._states = {}
        self._firebaseCredentialsFileName = None
        self._firebaseLastMessageId = ''
        self.firebaseStatus = FIREBASE_STATUS_NOT_INITIALISED
        self.firebase = None
        self.updateCallback = None

        self._requests = {
            'departuretimer': {'status': '', 'timestamp': DATEZERO},
            'departureprofile': {'status': '', 'timestamp': DATEZERO},
            'batterycharge': {'status': '', 'timestamp': DATEZERO},
            'climatisation': {'status': '', 'timestamp': DATEZERO},
            'refresh': {'status': '', 'timestamp': DATEZERO},
            'lock': {'status': '', 'timestamp': DATEZERO},
            'honkandflash': {'status': '', 'timestamp': DATEZERO},
            'preheater': {'status': '', 'timestamp': DATEZERO},
            'remaining': -1,
            'latest': '',
            'state': ''
        }
        self._climate_duration = 30

        self._relevantCapabilties = {
            'measurements': {'active': False, 'reason': 'not supported', },
            'climatisation': {'active': False, 'reason': 'not supported'},
            'tripStatistics': {'active': False, 'reason': 'not supported', 'supportsCyclicTrips': False},
            'vehicleHealthInspection': {'active': False, 'reason': 'not supported'},
            'vehicleHealthWarnings': {'active': False, 'reason': 'not supported'},
            'state': {'active': False, 'reason': 'not supported'},
            'charging': {'active': False, 'reason': 'not supported', 'supportsTargetStateOfCharge': False},
            'chargingProfiles': {'active': False, 'reason': 'not supported', "supportsTimerClimatisation": False,"supportsVehiclePositionedInProfileID": False,"supportsSingleTimer": False},
            'honkAndFlash': {'active': False, 'reason': 'not supported'},
            'parkingPosition': {'active': False, 'reason': 'not supported'},
            'departureTimers': {'active': False, 'reason': 'not supported', 'supportsSingleTimer': False},
            'departureProfiles': {'active': False, 'reason': 'not supported', 'supportsSingleTimer': False},
            'transactionHistoryLockUnlock': {'active': False, 'reason': 'not supported'},
            'transactionHistoryHonkFlash': {'active': False, 'reason': 'not supported'},
        }

        self._last_full_update = datetime.now(tz=None) - timedelta(seconds=1200)
        # Timestamps for the last API calls
        self._last_get_statusreport = datetime.now(tz=None) - timedelta(seconds=600)
        self._last_get_departure_timers = datetime.now(tz=None) - timedelta(seconds=600)
        self._last_get_departure_profiles = datetime.now(tz=None) - timedelta(seconds=600)
        self._last_get_charger = datetime.now(tz=None) - timedelta(seconds=600)
        self._last_get_climater = datetime.now(tz=None) - timedelta(seconds=600)
        self._last_get_mileage = datetime.now(tz=None) - timedelta(seconds=600)
        self._last_get_position = datetime.now(tz=None) - timedelta(seconds=600)


 #### API get and set functions ####
  # Init and update vehicle data
    async def discover(self) -> None:
        """Discover vehicle and initial data."""
        #await asyncio.gather(
        #    self.get_basiccardata(),
        #    return_exceptions=True
        #)
        # Extract information of relevant capabilities
        if self._capabilities != None:
            for capa in self._capabilities:
                id=capa.get('id', '')
                if self._relevantCapabilties.get(id, False):
                    data={}
                    data['active']=capa.get('active', False)
                    if capa.get('user-enabled', False):
                        data['reason']='user-enabled'
                    else:
                        data['reason']=capa.get('user-enabled', False)
                    if capa.get('status', False):
                        data['reason']=capa.get('status', '')
                    if capa.get('parameters', False):
                        if capa['parameters'].get('supportsCyclicTrips',False)==True or capa['parameters'].get('supportsCyclicTrips',False)=='true':
                            data['supportsCyclicTrips']=True
                        if capa['parameters'].get('supportsTargetStateOfCharge',False)==True or capa['parameters'].get('supportsTargetStateOfCharge',False)=='true':
                            data['supportsTargetStateOfCharge']=True
                        if capa['parameters'].get('supportsSingleTimer',False)==True or capa['parameters'].get('supportsSingleTimer',False)=='true':
                            data['supportsSingleTimer']=True
                        if capa['parameters'].get('supportsVehiclePositionedInProfileID',False)==True or capa['parameters'].get('supportsVehiclePositionedInProfileID',False)=='true':
                            data['supportsVehiclePositionedInProfileID']=True
                        if capa['parameters'].get('supportsTimerClimatisation',False)==True or capa['parameters'].get('supportsTimerClimatisation',False)=='true':
                            data['supportsTimerClimatisation']=True
                    self._relevantCapabilties[id].update(data)
        else:
            _LOGGER.warning(f"No capabilities information stored for vehicle with VIN {self.vin}")
       
        # Get URLs for model image
        self._modelimages = await self.get_modelimageurl()

        self._discovered = datetime.now()

    async def update(self, updateType=0) -> bool:
        """Try to fetch data for all known API endpoints."""
        # Update vehicle information if not discovered or stale information
        if not self._discovered:
            await self.discover()
        else:
            # Rediscover if data is older than 2 hours
            hourago = datetime.now() - timedelta(hours = 2)
            if self._discovered < hourago:
                await self.discover()

        # Fetch all data if car is not deactivated
        if not self.deactivated:
            try:
                if self.attrs.get('areaAlarm', {}) !={}:
                    # Delete an area alarm if it is older than 900 seconds
                    alarmTimestamp = self.attrs.get('areaAlarm', {}).get('timestamp', 0)
                    if alarmTimestamp < datetime.now(tz=None) - timedelta(seconds= 900):
                        self.attrs.pop("areaAlarm")

                if self.firebaseStatus == FIREBASE_STATUS_ACTIVATED:
                    # Check, if fcmpushclient still started
                    if not self.firebase._pushClient.is_started():
                        _LOGGER.warning(f'firebaseStatus={self.firebaseStatus}, but state of push client is not started. Changing firebaseStatus to {FIREBASE_STATUS_ACTIVATION_STOPPED}')
                        self.firebaseStatus = FIREBASE_STATUS_ACTIVATION_STOPPED

                    fullUpdateExpired = datetime.now(tz=None) - timedelta(seconds= 1700)
                    oldMileage = self.distance
                    if self._last_get_mileage < datetime.now(tz=None) - timedelta(seconds= 300):
                        await self.get_mileage()
                        if self.distance > oldMileage:
                            # self.distance has changed. So it's time for a full update
                            _LOGGER.debug(f'Mileage has changed. Old value: {oldMileage}, new value {self.distance}. This calls for a full update.')
                            updateType = 1
                else:
                    fullUpdateExpired = datetime.now(tz=None) - timedelta(seconds= 1100)

                if self.firebaseStatus == FIREBASE_STATUS_ACTIVATION_STOPPED:
                    # Trying to activate firebase connection again
                    """_LOGGER.debug(f'As firebase status={self.firebaseStatus}, fcmpushclient.start() is called.')
                    await self.firebase._pushClient.start()
                    #await asyncio.sleep(5)
                    if self.firebase._pushClient.is_started():
                        self.firebaseStatus = FIREBASE_STATUS_ACTIVATED
                        _LOGGER.debug(f'Successfully restarted push client. New firebase status={self.firebaseStatus}')
                    else:
                        _LOGGER.warning(f'Restart of push client failed. Firebase status={self.firebaseStatus}')"""
                    newStatus = await self.stopFirebase()
                    if newStatus != FIREBASE_STATUS_NOT_INITIALISED:
                        _LOGGER.debug(f'stopFirebase() not successful.')
                        # Although stopFirebase() was not successful, the firebase status is reset to FIREBASE_STATUS_NOT_INITIALISED to allow a new initialisation
                        self.firebaseStatus = FIREBASE_STATUS_NOT_INITIALISED
                    newStatus = await self.initialiseFirebase(self._firebaseCredentialsFileName, self.updateCallback)
                    if newStatus == FIREBASE_STATUS_ACTIVATED:
                        _LOGGER.debug(f'Reinitialisation of firebase successful.New firebase status={self.firebaseStatus}.')
                    else:
                        self.firebaseStatus = FIREBASE_STATUS_ACTIVATION_STOPPED
                        _LOGGER.warning(f'Reinitialisation of firebase failed. New firebase status={self.firebaseStatus}.')

                if self._connection._session_nightlyUpdateReduction:
                    # nightlyUpdateReduction is activated
                    if datetime.now(tz=None).hour<5 or datetime.now(tz=None).hour>=22:
                        # current time is within the night interval
                        if hasattr(self, '_last_full_update'):
                            _LOGGER.debug(f'last_full_update= {self._last_full_update}, fullUpdateExpired= {fullUpdateExpired}.')
                        if updateType<1 and (hasattr(self, '_last_full_update') and self._last_full_update>fullUpdateExpired):
                            _LOGGER.debug('Nightly update reduction is active and current time within 22:00 and 5:00. So we skip small update.')
                            return True

                # Data to be updated most often
                await asyncio.gather(
                    #self.get_charger(),
                    self.get_basiccardata(),
                    self.get_statusreport(),
                    return_exceptions=True
                )

                if hasattr(self, '_last_full_update'):
                    _LOGGER.debug(f'last_full_update= {self._last_full_update}, fullUpdateExpired= {fullUpdateExpired}.')
                if updateType!=1 and (hasattr(self, '_last_full_update') and self._last_full_update>fullUpdateExpired):
                    _LOGGER.debug(f'Just performed small update for vehicle with VIN {self._connection.anonymise(self.vin)}.')
                    return True
                
                # Data to be updated less often
                if self.firebaseStatus != FIREBASE_STATUS_ACTIVATED:
                    await self.get_mileage() 


                await asyncio.gather(
                    #self.get_statusreport(),
                    self.get_charger(),
                    self.get_preheater(),
                    self.get_climater(),
                    self.get_trip_statistic(), 
                    self.get_position(),
                    self.get_maintenance(),
                    self.get_vehicleHealthWarnings(),
                    self.get_departure_timers(),
                    self.get_departure_profiles(),
                    #self.get_modelimageurl(), #commented out, because getting the images discover() should be sufficient
                    return_exceptions=True
                )
                self._last_full_update = datetime.now(tz=None)
                _LOGGER.debug(f'Performed full update for vehicle with VIN {self._connection.anonymise(self.vin)}.')
                _LOGGER.debug(f'So far about {self._connection._sessionRequestCounter} API calls since {self._connection._sessionRequestTimestamp}.')
            except:
                raise SeatException("Update failed")
            return True
        else:
            _LOGGER.info(f'Vehicle with VIN {self._connection.anonymise(self.vin)} is deactivated.')
            return False
        return True

  # Data collection functions
    async def get_modelimageurl(self):
        """Fetch the URL for model image."""
        return await self._connection.getModelImageURL(self.vin, self._apibase)

    async def get_basiccardata(self) -> bool:
        """Fetch basic car data."""
        data = await self._connection.getBasicCarData(self.vin, self._apibase)
        if data:
            self._states.update(data)
            return True
        else:
            _LOGGER.debug('Could not fetch basic car data')
            return False

    async def get_mileage(self) -> bool:
        """Fetch basic car data."""
        data = await self._connection.getMileage(self.vin, self._apibase)
        if data:
            self._states.update(data)
            self._last_get_mileage = datetime.now(tz=None)
            return True
        else:
            _LOGGER.debug('Could not fetch mileage data')
            return False

    async def get_preheater(self) -> None:
        """Fetch pre-heater data if function is enabled."""
        _LOGGER.info('get_preheater() not implemented yet')
        #if self._relevantCapabilties.get('#dont know the name for the preheater capability', {}).get('active', False):
        #    if not await self.expired('rheating_v1'):
        #        data = await self._connection.getPreHeater(self.vin, self._apibase)
        #        if data:
        #            self._states.update(data)
        #        else:
        #            _LOGGER.debug('Could not fetch preheater data')
        #else:
        #    self._requests.pop('preheater', None)

    async def get_climater(self) -> bool:
        """Fetch climater data if function is enabled."""
        if self._relevantCapabilties.get('climatisation', {}).get('active', False):
            data = await self._connection.getClimater(self.vin, self._apibase, deepcopy(self.attrs.get('climater',{})))
            if data:
                self._states.update(data)
                self._last_get_climater = datetime.now(tz=None)
                return True
            else:
                _LOGGER.debug('Could not fetch climater data')
        return False
        #else:
        #    self._requests.pop('climatisation', None)

    async def get_trip_statistic(self) -> bool:
        """Fetch trip data if function is enabled."""
        if self._relevantCapabilties.get('tripStatistics', {}).get('active', False):
            data = await self._connection.getTripStatistics(self.vin, self._apibase, self._relevantCapabilties['tripStatistics'].get('supportsCyclicTrips', False))
            if data:
                self._states.update(data)
                return True
            else:
                _LOGGER.debug('Could not fetch trip statistics')
        return False

    async def get_position(self) -> bool:
        """Fetch position data if function is enabled."""
        if self._relevantCapabilties.get('parkingPosition', {}).get('active', False):
            data = await self._connection.getPosition(self.vin, self._apibase)
            if data:
                # Reset requests remaining to 15 if parking time has been updated
                if data.get('findCarResponse', {}).get('parkingTimeUTC', False):
                    try:
                        newTime = data.get('findCarResponse').get('parkingTimeUTC')
                        oldTime = self.attrs.get('findCarResponse').get('parkingTimeUTC')
                        if newTime > oldTime:
                            self.requests_remaining = 15
                    except:
                        pass
                self._states.update(data)
                self._last_get_position = datetime.now(tz=None)
                return True
            else:
                _LOGGER.debug('Could not fetch any positional data')
        return False

    async def get_vehicleHealthWarnings(self) -> bool:
        if self._relevantCapabilties.get('vehicleHealthWarnings', {}).get('active', False):
            data = await self._connection.getVehicleHealthWarnings(self.vin, self._apibase)
            if data:
                self._states.update(data)
                return True
            else:
                _LOGGER.debug('Could not fetch vehicle health warnings')
        return False

    async def get_statusreport(self) -> bool:
        """Fetch status data if function is enabled."""
        if self._relevantCapabilties.get('state', {}).get('active', False):
            data = await self._connection.getVehicleStatusReport(self.vin, self._apibase)
            if data:
                self._states.update(data)
                self._last_get_statusreport = datetime.now(tz=None)
                return True
            else:
                _LOGGER.debug('Could not fetch status report')
        return False

    async def get_maintenance(self) -> bool:
        """Fetch maintenance data if function is enabled."""
        if self._relevantCapabilties.get('vehicleHealthInspection', {}).get('active', False):
            data = await self._connection.getMaintenance(self.vin, self._apibase)
            if data:
                self._states.update(data)
                return True
            else:
                _LOGGER.debug('Could not fetch status report')
        return False

    async def get_charger(self) -> bool:
        """Fetch charger data if function is enabled."""
        if self._relevantCapabilties.get('charging', {}).get('active', False):
            data = await self._connection.getCharger(self.vin, self._apibase, deepcopy(self.attrs.get('charging',{})))
            if data:
                self._states.update(data)
                self._last_get_charger = datetime.now(tz=None)
                return True
            else:
                _LOGGER.debug('Could not fetch charger data')
        return False

    async def get_departure_timers(self) -> bool:
        """Fetch timer data if function is enabled."""
        if self._relevantCapabilties.get('departureTimers', {}).get('active', False):
            data = await self._connection.getDeparturetimer(self.vin, self._apibase)
            if data:
                self._states.update(data)
                self._last_get_departure_timers = datetime.now(tz=None)
                return True
            else:
                _LOGGER.debug('Could not fetch timers')
        return False

    async def get_departure_profiles(self) -> bool:
        """Fetch timer data if function is enabled."""
        if self._relevantCapabilties.get('departureProfiles', {}).get('active', False):
            data = await self._connection.getDepartureprofiles(self.vin, self._apibase)
            if data:
                self._states.update(data)
                self._last_get_departure_profiles = datetime.now(tz=None)
                return True
            else:
                _LOGGER.debug('Could not fetch timers')
        return False

    #async def wait_for_request(self, section, request, retryCount=36):
        """Update status of outstanding requests."""
        """retryCount -= 1
        if (retryCount == 0):
            _LOGGER.info(f'Timeout while waiting for result of {request}.')
            return 'Timeout'
        try:
            status = await self._connection.get_request_status(self.vin, section, request, self._apibase)
            _LOGGER.info(f'Request for {section} with ID {request}: {status}')
            if status == 'In progress':
                self._requests['state'] = 'In progress'
                await asyncio.sleep(5)
                return await self.wait_for_request(section, request, retryCount)
            else:
                self._requests['state'] = status
                return status
        except Exception as error:
            _LOGGER.warning(f'Exception encountered while waiting for request status: {error}')
            return 'Exception'"""

  # Data set functions
   # API endpoint charging
    async def set_charger_current(self, value) -> bool:
        """Set charger current"""
        if self.is_charging_supported:
            data: dict[str, Any] = {}
            # Set charger max ampere to integer value
            if isinstance(value, int):
                if 1 <= int(value) <= 255:
                    # VW-Group API charger current request
                    if self._relevantCapabilties.get('charging', {}).get('active', False):
                        data = {'maxChargeCurrentAc': int(value)}
                        if int(value)==252:
                            data = {'maxChargeCurrentAc': 'reduced'}
                        elif int(value)==254:
                            data = {'maxChargeCurrentAc': 'maximum'}
                        else:
                            data = {'maxChargeCurrentAcInAmperes': int(value)}
                else:
                    _LOGGER.error(f'Set charger maximum current to {value} is not supported.')
                    raise SeatInvalidRequestException(f'Set charger maximum current to {value} is not supported.')
            # Mimick app and set charger max ampere to Maximum/Reduced
            elif isinstance(value, str):
                if value in ['Maximum', 'maximum', 'Max', 'max', 'Minimum', 'minimum', 'Min', 'min', 'Reduced', 'reduced']:
                    # VW-Group API charger current request
                    if self._relevantCapabilties.get('charging', {}).get('active', False):
                        value = 'maximum' if value in ['Maximum', 'maximum', 'Max', 'max'] else 'reduced'
                        data = {'maxChargeCurrentAc': value}
                else:
                    _LOGGER.error(f'Set charger maximum current to {value} is not supported.')
                    raise SeatInvalidRequestException(f'Set charger maximum current to {value} is not supported.')
            else:
                _LOGGER.error(f'Data type passed is invalid.')
                raise SeatInvalidRequestException(f'Invalid data type.')
            return await self.set_charger('settings', data)
        else:
            _LOGGER.error('No charger support.')
            raise SeatInvalidRequestException('No charger support.')

    async def set_charger_target_soc(self, value) -> bool:
        """Set target state of charge"""
        if self.is_charging_supported:
            if isinstance(value, int):
                if 1 <= int(value) <= 100:
                    # VW-Group API charger current request
                    if self._relevantCapabilties.get('charging', {}).get('active', False) and self._relevantCapabilties.get('charging', {}).get('supportsTargetStateOfCharge', False):
                        data= deepcopy(self.attrs.get('charging',{}).get('info',{}).get('settings',{}))
                        if data=={}:
                            _LOGGER.error(f'Can not set target soc, because currently no charging settings are present.')
                            raise SeatInvalidRequestException(f'Set target soc not possible. Charging settings not present.')
                        data['targetSoc'] = int(value)
                    else: 
                        _LOGGER.warning(f'Can not set target soc, because vehicle does not support this feature.')
                        return False
                else:
                    _LOGGER.error(f'Set target soc to {value} is not supported.')
                    raise SeatInvalidRequestException(f'Set target soc to {value} is not supported.')
            # Mimick app and set charger max ampere to Maximum/Reduced
            else:
                _LOGGER.error(f'Data type passed is invalid.')
                raise SeatInvalidRequestException(f'Invalid data type.')
            return await self.set_charger('settings', data)
        else:
            _LOGGER.error('No charger support.')
            raise SeatInvalidRequestException('No charger support.')

    async def set_charger(self, action, data=None) -> bool:
        """Charging actions."""
        if not self._relevantCapabilties.get('charging', {}).get('active', False):
            _LOGGER.info('Remote start/stop of charger is not supported.')
            raise SeatInvalidRequestException('Remote start/stop of charger is not supported.')
        if self._requests['batterycharge'].get('id', False):
            timestamp = self._requests.get('batterycharge', {}).get('timestamp', datetime.now())
            expired = datetime.now() - timedelta(minutes=1)
            if expired > timestamp:
                self._requests.get('batterycharge', {}).pop('id')
            else:
                raise SeatRequestInProgressException('Charging action already in progress')
        if self._relevantCapabilties.get('charging', {}).get('active', False):
            if action in ['start', 'Start', 'On', 'on']:
                mode='start'
            elif action in ['stop', 'Stop', 'Off', 'off']:
                mode='stop'
            elif action=='settings':
                mode=action
            else:
                _LOGGER.error(f'Invalid charger action: {action}. Must be either start, stop or setSettings')
                raise SeatInvalidRequestException(f'Invalid charger action: {action}. Must be either start, stop or setSettings')
        try:
            self._requests['latest'] = 'Charger'
            response = await self._connection.setCharger(self.vin, self._apibase, mode, data)
            if not response:
                self._requests['batterycharge'] = {'status': 'Failed'}
                _LOGGER.error(f'Failed to {action} charging')
                raise SeatException(f'Failed to {action} charging')
            else:
                self._requests['remaining'] = response.get('rate_limit_remaining', -1)
                self._requests['batterycharge'] = {
                    'timestamp': datetime.now(),
                    'status': response.get('state', 'Unknown'),
                    'id': response.get('id', 0)
                }
                # if firebaseStatus is FIREBASE_STATUS_ACTIVATED, the request is assumed successful. Waiting for push notification before rereading status
                if self.firebaseStatus == FIREBASE_STATUS_ACTIVATED:
                    _LOGGER.debug('POST request for charger assumed successful. Waiting for push notification')
                    return True
                # Update the charger data and check, if they have changed as expected
                retry = 0
                actionSuccessful = False
                while not actionSuccessful and retry < 2:
                    await asyncio.sleep(15)
                    await self.get_charger()
                    await self.get_basiccardata() # We get both, get_charger() and get_basiccardata()
                    if mode == 'start':
                        if self.charging:
                            actionSuccessful = True
                    elif mode == 'stop':
                        if not self.charging:
                            actionSuccessful = True
                    elif mode == 'settings':
                        if data.get('targetSoc',0) ==  self.target_soc: # In case targetSoc is changed
                            actionSuccessful = True
                        if data.get('maxChargeCurrentAc','') ==  self.charge_max_ampere: # In case 'maximum', 'reduced'
                            actionSuccessful = True
                        if data.get('maxChargeCurrentAcInAmperes',0) ==  self.charge_max_ampere: # In case of a numerical value for charge current
                            actionSuccessful = True
                    else:
                        _LOGGER.error(f'Missing code in vehicle._set_charger() for mode {mode}')
                        raise
                    retry = retry +1
                if actionSuccessful:
                    _LOGGER.debug('POST request for charger successful. New status as expected.')
                    self._requests.get('batterycharge', {}).pop('id')
                    return True
                _LOGGER.error('Response to POST request seemed successful but the charging status did not change as expected.')
                return False
        except (SeatInvalidRequestException, SeatException):
            raise
        except Exception as error:
            _LOGGER.warning(f'Failed to {action} charging - {error}')
            self._requests['batterycharge'] = {'status': 'Exception'}
            raise SeatException(f'Failed to execute set charger - {error}')

   # API endpoint departuretimer
    async def set_charge_limit(self, limit=50) -> bool:
        """ Set minimum state of charge limit for departure timers or departure profiles. """
        if (not self._relevantCapabilties.get('departureTimers', {}).get('active', False) and 
            not self._relevantCapabilties.get('departureProfiles', {}).get('active', False) and 
            not self._relevantCapabilties.get('charging', {}).get('active', False)):
            _LOGGER.info('Set charging limit is not supported.')
            raise SeatInvalidRequestException('Set charging limit is not supported.')
        if self._relevantCapabilties.get('departureTimers', {}).get('active', False) :
            # Vehicle has departure timers
            data = {}
            if isinstance(limit, int):
                if limit in [0, 10, 20, 30, 40, 50]:
                    data['minSocPercentage'] = limit
                else:
                    raise SeatInvalidRequestException(f'Charge limit must be one of 0, 10, 20, 30, 40 or 50.')
            else:
                raise SeatInvalidRequestException(f'Charge limit "{limit}" is not supported.')
            return await self._set_timers(data)
        elif self._relevantCapabilties.get('departureProfiles', {}).get('active', False):
            # Vehicle has departure profiles
            data= deepcopy(self.attrs.get('departureProfiles'))
            if isinstance(limit, int):
                if limit in [0, 10, 20, 30, 40, 50]:
                    data['minSocPercentage'] = limit
                else:
                    raise SeatInvalidRequestException(f'Charge limit must be one of 0, 10, 20, 30, 40 or 50.')
            else:
                raise SeatInvalidRequestException(f'Charge limit "{limit}" is not supported.')
            return await self._set_departure_profiles(data, action='minSocPercentage')
        return False

    async def set_timer_active(self, id=1, action='off') -> bool:
        """ Activate/deactivate departure timers. """
        data: dict[str, Any] = {}
        supported = "is_departure" + str(id) + "_supported"
        if getattr(self, supported) is not True:
            raise SeatConfigException(f'This vehicle does not support timer id {id}.')
        if self._relevantCapabilties.get('departureTimers', {}).get('active', False):
            allTimers= self.attrs.get('departureTimers').get('timers', [])
            for singleTimer in allTimers:
                if singleTimer.get('id',-1)==id:
                    if action in ['on', 'off']:
                        if action=='on':
                            enabled=True
                        else:
                            enabled=False
                        singleTimer['enabled'] = enabled
                        data = {
                            'timers' : []
                        }
                        data['timers'].append(singleTimer)
                    else:
                        raise SeatInvalidRequestException(f'Timer action "{action}" is not supported.')
                    return await self._set_timers(data)
            raise SeatInvalidRequestException(f'Departure timer id {id} not found.')
        else:
            raise SeatInvalidRequestException('Departure timers are not supported.')

    async def set_timer_schedule(self, id, schedule={}) -> bool:
        """ Set departure timer schedule. """
        data: dict[str, Any] = {}
        # Validate required user inputs
        supported = "is_departure" + str(id) + "_supported"
        if getattr(self, supported) is not True:
            raise SeatConfigException(f'Timer id {id} is not supported for this vehicle.')
        else:
            _LOGGER.debug(f'Timer id {id} is supported')
        if not schedule:
            raise SeatInvalidRequestException('A schedule must be set.')
        if not isinstance(schedule.get('enabled', ''), bool):
            raise SeatInvalidRequestException('The enabled variable must be set to True or False.')
        if not isinstance(schedule.get('recurring', ''), bool):
            raise SeatInvalidRequestException('The recurring variable must be set to True or False.')
        if not re.match('^[0-9]{2}:[0-9]{2}$', schedule.get('time', '')):
            raise SeatInvalidRequestException('The time for departure must be set in 24h format HH:MM.')

        # Validate optional inputs
        if schedule.get('recurring', False):
            if not re.match('^[yn]{7}$', schedule.get('days', '')):
                raise SeatInvalidRequestException('For recurring schedules the days variable must be set to y/n mask (mon-sun with only wed enabled): nnynnnn.')
        elif not schedule.get('recurring'):
            if not re.match('^[0-9]{4}-[0-9]{2}-[0-9]{2}$', schedule.get('date', '')):
                raise SeatInvalidRequestException('For single departure schedule the date variable must be set to YYYY-mm-dd.')

        if self._relevantCapabilties.get('departureTimers', {}).get('active', False):
            # Sanity check for off-peak hours
            if not isinstance(schedule.get('nightRateActive', False), bool):
                raise SeatInvalidRequestException('The off-peak active variable must be set to True or False')
            if schedule.get('nightRateStart', None) is not None:
                if not re.match('^[0-9]{2}:[0-9]{2}$', schedule.get('nightRateStart', '')):
                    raise SeatInvalidRequestException('The start time for off-peak hours must be set in 24h format HH:MM.')
            if schedule.get('nightRateEnd', None) is not None:
                if not re.match('^[0-9]{2}:[0-9]{2}$', schedule.get('nightRateEnd', '')):
                    raise SeatInvalidRequestException('The start time for off-peak hours must be set in 24h format HH:MM.')

            # Check if charging/climatisation is set and correct
            if not isinstance(schedule.get('operationClimatisation', False), bool):
                raise SeatInvalidRequestException('The climatisation enable variable must be set to True or False')
            if not isinstance(schedule.get('operationCharging', False), bool):
                raise SeatInvalidRequestException('The charging variable must be set to True or False')

            # Validate temp setting, if set
            if schedule.get("targetTemp", None) is not None:
                if not 16 <= int(schedule.get("targetTemp", None)) <= 30:
                    raise SeatInvalidRequestException('Target temp must be integer value from 16 to 30')
                else:
                    data['temp'] = int(schedule.get('targetTemp'))
                    raise SeatInvalidRequestException('Target temp (yet) not supported.')

            # Validate charge target and current
            if schedule.get("targetChargeLevel", None) is not None:
                if not 0 <= int(schedule.get("targetChargeLevel", None)) <= 100:
                    raise SeatInvalidRequestException('Target charge level must be 0 to 100')
                else:
                    raise SeatInvalidRequestException('targetChargeLevel (yet) not supported.')
            if schedule.get("chargeMaxCurrent", None) is not None:
                raise SeatInvalidRequestException('chargeMaxCurrent (yet) not supported.')
                if isinstance(schedule.get('chargeMaxCurrent', None), str):
                    if not schedule.get("chargeMaxCurrent", None) in ['Maximum', 'maximum', 'Max', 'max', 'Minimum', 'minimum', 'Min', 'min', 'Reduced', 'reduced']:
                        raise SeatInvalidRequestException('Charge current must be one of Maximum/Minimum/Reduced')
                elif isinstance(schedule.get('chargeMaxCurrent', None), int):
                    if not 1 <= int(schedule.get("chargeMaxCurrent", 254)) < 255:
                        raise SeatInvalidRequestException('Charge current must be set from 1 to 254')
                else:
                    raise SeatInvalidRequestException('Invalid type for charge max current variable')
            
            # Prepare data and execute
            data['id'] = id
            # Converting schedule to data map
            if schedule.get("enabled",False):
                data['enabled']=True
            else:
                data['enabled']=False
            if schedule.get("operationCharging",False):
                data['charging']=True
            else:
                data['charging']=False
            if schedule.get("operationClimatisation",False):
                data['climatisation']=True
            else:
                data['climatisation']=False
            if schedule.get("nightRateAcvtive", False):
                preferedChargingTimes= [{
                    "id" : 1,
                    "enabled" : True,
                    "startTimeLocal" : schedule.get('nightRateStart',"00:00"),
                    "endTimeLocal" : schedule.get('nightRateStop',"00:00")
                    }]
            else:
                preferedChargingTimes= [{
                    "id" : 1,
                    "enabled" : False,
                    "startTimeLocal" : "00:00",
                    "endTimeLocal" : "00:00"
                    }]
            if schedule.get("recurring",False):
                data['recurringTimer']= {
                    "startTimeLocal": schedule.get('time',"00:00"),
                    "recurringOn":{""
                        "mondays":(schedule.get('days',"nnnnnnn")[0]=='y'),
                        "tuesdays":(schedule.get('days',"nnnnnnn")[1]=='y'),
                        "wednesdays":(schedule.get('days',"nnnnnnn")[2]=='y'),
                        "thursdays":(schedule.get('days',"nnnnnnn")[3]=='y'),
                        "fridays":(schedule.get('days',"nnnnnnn")[4]=='y'),
                        "saturdays":(schedule.get('days',"nnnnnnn")[5]=='y'),
                        "sundays":(schedule.get('days',"nnnnnnn")[6]=='y'),
                        #"preferredChargingTimes": preferedChargingTimes
                    }
                }
            else:
                startDateTime = datetime.fromisoformat(schedule.get('date',"2025-01-01")+'T'+schedule.get('time',"00:00"))
                _LOGGER.info(f'startDateTime={startDateTime.strftime("%Y-%m-%dT%H:%M:%SZ")}')
                data['singleTimer']= {
                    "startDateTime": startDateTime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    #"preferredChargingTimes": preferedChargingTimes
                    }
            data["preferredChargingTimes"]= preferedChargingTimes
                
            # Now we have to embed the data for the timer 'id' in timers[]
            data={
                'timers' : [data]
            }
            return await self._set_timers(data)
        else:
            _LOGGER.info('Departure timers are not supported.')
            raise SeatInvalidRequestException('Departure timers are not supported.')

    async def _set_timers(self, data=None) -> bool:
        """ Set departure timers. """
        if not self._relevantCapabilties.get('departureTimers', {}).get('active', False):
            raise SeatInvalidRequestException('Departure timers are not supported.')
        if self._requests['departuretimer'].get('id', False):
            timestamp = self._requests.get('departuretimer', {}).get('timestamp', datetime.now())
            expired = datetime.now() - timedelta(minutes=1)
            if expired > timestamp:
                self._requests.get('departuretimer', {}).pop('id')
            else:
                raise SeatRequestInProgressException('Scheduling of departure timer is already in progress')

        try:
            self._requests['latest'] = 'Departuretimer'
            response = await self._connection.setDeparturetimer(self.vin, self._apibase, data, spin=False)
            if not response:
                self._requests['departuretimer'] = {'status': 'Failed'}
                _LOGGER.error('Failed to execute departure timer request')
                raise SeatException('Failed to execute departure timer request')
            else:
                self._requests['remaining'] = response.get('rate_limit_remaining', -1)
                self._requests['departuretimer'] = {
                    'timestamp': datetime.now(),
                    'status': response.get('state', 'Unknown'),
                    'id': response.get('id', 0),
                }
                # if firebaseStatus is FIREBASE_STATUS_ACTIVATED, the request is assumed successful. Waiting for push notification before rereading status
                if self.firebaseStatus == FIREBASE_STATUS_ACTIVATED:
                    _LOGGER.debug('POST request for change of departure timers assumed successful. Waiting for push notification')
                    return True
                # Update the departure timers data and check, if they have changed as expected
                retry = 0
                actionSuccessful = False
                while not actionSuccessful and retry < 2:
                    await asyncio.sleep(15)
                    await self.get_departure_timers()
                    if data.get('minSocPercentage',False):
                        if data.get('minSocPercentage',-2)==self.attrs.get('departureTimers',{}).get('minSocPercentage',-1):
                            actionSuccessful=True
                    else:
                        _LOGGER.debug('Checking if new departure timer is as expected:')
                        timerData = data.get('timers',[])[0]
                        timerDataId = timerData.get('id',False)
                        timerDataCopy = deepcopy(timerData)
                        timerDataCopy['enabled']=True
                        if timerDataId:
                            newTimers = self.attrs.get('departureTimers',{}).get('timers',[])
                            for newTimer in newTimers:
                                if newTimer.get('id',-1)==timerDataId:
                                    _LOGGER.debug(f'Value of timer sent:{timerData}')
                                    _LOGGER.debug(f'Value of timer read:{newTimer}')
                                    if timerData==newTimer: 
                                        actionSuccessful=True
                                    elif timerDataCopy==newTimer: 
                                        _LOGGER.debug('Data written and data read are the same, but the timer is activated.')
                                        actionSuccessful=True
                                    break
                    retry = retry +1
                if True: #actionSuccessful:
                    #_LOGGER.debug('POST request for departure timers successful. New status as expected.')
                    self._requests.get('departuretimer', {}).pop('id')
                    return True
                _LOGGER.error('Response to POST request seemed successful but the departure timers status did not change as expected.')
                return False
        except (SeatInvalidRequestException, SeatException):
            raise
        except Exception as error:
            _LOGGER.warning(f'Failed to execute departure timer request - {error}')
            self._requests['departuretimer'] = {'status': 'Exception'}
        raise SeatException('Failed to set departure timer schedule')

    async def set_departure_profile_schedule(self, id, schedule={}) -> bool:
        """ Set departure profile schedule. """
        data = {}
        # Validate required user inputs
        supported = "is_departure_profile" + str(id) + "_supported"
        if getattr(self, supported) is not True:
            raise SeatConfigException(f'Departure profile id {id} is not supported for this vehicle.')
        else:
            _LOGGER.debug(f'Departure profile id {id} is supported')
        if not schedule:
            raise SeatInvalidRequestException('A schedule must be set.')
        if not isinstance(schedule.get('enabled', ''), bool):
            raise SeatInvalidRequestException('The enabled variable must be set to True or False.')
        if not isinstance(schedule.get('recurring', ''), bool):
            raise SeatInvalidRequestException('The recurring variable must be set to True or False.')
        if not re.match('^[0-9]{2}:[0-9]{2}$', schedule.get('time', '')):
            raise SeatInvalidRequestException('The time for departure must be set in 24h format HH:MM.')

        # Validate optional inputs
        if schedule.get('recurring', False):
            if not re.match('^[yn]{7}$', schedule.get('days', '')):
                raise SeatInvalidRequestException('For recurring schedules the days variable must be set to y/n mask (mon-sun with only wed enabled): nnynnnn.')
        elif not schedule.get('recurring'):
            if not re.match('^[0-9]{4}-[0-9]{2}-[0-9]{2}$', schedule.get('date', '')):
                raise SeatInvalidRequestException('For single departure profile schedule the date variable must be set to YYYY-mm-dd.')

        if self._relevantCapabilties.get('departureProfiles', {}).get('active', False):
            # Check if profileIds is set and correct
            if schedule.get('chargingProgramId', False):
                # At the moment, only one charging program id is supported
                chargingProgramId = int(schedule.get('chargingProgramId', False))
                found = False
                for chargingProgram in self.attrs.get('departureProfiles', {}).get('profiles', []):
                    if chargingProgram.get('id',None) == chargingProgramId:
                        found = True
                        break
                if not found:
                    raise SeatInvalidRequestException('The charging program id provided for the departure profile schedule is unknown.')
                else:
                    profileIds = []
                    profileIds.append(chargingProgramId)
            else:
                raise SeatInvalidRequestException('No charging program id provided for departure profile schedule.')

            newDepProfileSchedule = {}
            # Prepare data and execute
            newDepProfileSchedule['id'] = id
            # Converting schedule to data map
            if schedule.get("enabled",False):
                newDepProfileSchedule['enabled']=True
            else:
                newDepProfileSchedule['enabled']=False
            if schedule.get("recurring",False):
                newDepProfileSchedule['recurringTimer']= {
                    "startTime": schedule.get('time',"00:00"),
                    "recurringOn":{""
                        "mondays":(schedule.get('days',"nnnnnnn")[0]=='y'),
                        "tuesdays":(schedule.get('days',"nnnnnnn")[1]=='y'),
                        "wednesdays":(schedule.get('days',"nnnnnnn")[2]=='y'),
                        "thursdays":(schedule.get('days',"nnnnnnn")[3]=='y'),
                        "fridays":(schedule.get('days',"nnnnnnn")[4]=='y'),
                        "saturdays":(schedule.get('days',"nnnnnnn")[5]=='y'),
                        "sundays":(schedule.get('days',"nnnnnnn")[6]=='y'),
                    }
                }
            else:
                if self._relevantCapabilties.get('departureProfiles', {}).get('supportsSingleTimer', False):
                    startDateTime = datetime.fromisoformat(schedule.get('date',"2025-01-01")+'T'+schedule.get('time',"00:00"))
                    _LOGGER.info(f'startDateTime={startDateTime.strftime("%Y-%m-%dT%H:%M:%SZ")}')
                    newDepProfileSchedule['singleTimer']= {
                        "startDateTime": startDateTime.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        }
                else:
                    raise SeatInvalidRequestException('Vehicle does not support single timer.')
            newDepProfileSchedule["profileIds"]= profileIds

            # Now we have to substitute the current departure profile schedule with the given id by the new one
            data= deepcopy(self.attrs.get('departureProfiles'))
            if len(data.get('timers', []))<1:
                raise SeatInvalidRequestException(f'No timers found in departure profile: {data}.')
            idFound=False
            for e in range(len(data.get('timers', []))):
                if data['timers'][e].get('id',-1)==id:
                    data['timers'][e] = newDepProfileSchedule
                    idFound=True
            if idFound:
                return await self._set_departure_profiles(data, action='set')
            raise SeatInvalidRequestException(f'Departure profile id {id} not found in {data.get('timers',[])}.')
        else:
            _LOGGER.info('Departure profiles are not supported.')
            raise SeatInvalidRequestException('Departure profiles are not supported.')

    async def set_departure_profile_active(self, id=1, action='off') -> bool:
        """ Activate/deactivate departure profiles. """
        data = {}
        supported = "is_departure_profile" + str(id) + "_supported"
        if getattr(self, supported) is not True:
            raise SeatConfigException(f'This vehicle does not support departure profile id "{id}".')
        if self._relevantCapabilties.get('departureProfiles', {}).get('active', False):
            data= deepcopy(self.attrs.get('departureProfiles'))
            if len(data.get('timers', []))<1:
                raise SeatInvalidRequestException(f'No timers found in departure profile: {data}.')
            idFound=False
            for e in range(len(data.get('timers', []))):
                if data['timers'][e].get('id',-1)==id:
                    if action in ['on', 'off']:
                        if action=='on':
                            enabled=True
                        else:
                            enabled=False
                        data['timers'][e]['enabled'] = enabled
                        idFound=True
                        _LOGGER.debug(f'Changing departure profile {id} to {action}.')
                    else:
                        raise SeatInvalidRequestException(f'Profile action "{action}" is not supported.')
            if idFound:
                return await self._set_departure_profiles(data, action=action)
            raise SeatInvalidRequestException(f'Departure profile id {id} not found in {data.get('timers',[])}.')
        else:
            raise SeatInvalidRequestException('Departure profiles are not supported.')

    async def _set_departure_profiles(self, data=None, action=None) -> bool:
        """ Set departure profiles. """
        if not self._relevantCapabilties.get('departureProfiles', {}).get('active', False):
            raise SeatInvalidRequestException('Departure profiles are not supported.')
        if self._requests['departureprofile'].get('id', False):
            timestamp = self._requests.get('departureprofile', {}).get('timestamp', datetime.now())
            expired = datetime.now() - timedelta(minutes=1)
            if expired > timestamp:
                self._requests.get('departureprofile', {}).pop('id')
            else:
                raise SeatRequestInProgressException('Scheduling of departure profile is already in progress')
        try:
            self._requests['latest'] = 'Departureprofile'
            converted_data = convert_datetime_to_string(data) # datetime to string
            response = await self._connection.setDepartureprofile(self.vin, self._apibase, converted_data, spin=False)
            if not response:
                self._requests['departureprofile'] = {'status': 'Failed'}
                _LOGGER.error('Failed to execute departure profile request')
                raise SeatException('Failed to execute departure profile request')
            else:
                self._requests['remaining'] = response.get('rate_limit_remaining', -1)
                self._requests['departureprofile'] = {
                    'timestamp': datetime.now(),
                    'status': response.get('state', 'Unknown'),
                    'id': response.get('id', 0),
                }
                # if firebaseStatus is FIREBASE_STATUS_ACTIVATED, the request is assumed successful. Waiting for push notification before rereading status
                if self.firebaseStatus == FIREBASE_STATUS_ACTIVATED:
                    _LOGGER.debug('POST request for change of departure profiles assumed successful. Waiting for push notification')
                    return True
                # Update the departure profile data and check, if they have changed as expected
                retry = 0
                actionSuccessful = False
                while not actionSuccessful and retry < 2:
                    await asyncio.sleep(15)
                    await self.get_departure_profiles()
                    if action=='minSocPercentage':
                        _LOGGER.debug('Checking if new minSocPercentage is as expected:')
                        _LOGGER.debug(f'Value of minSocPercentage sent:{data.get('minSocPercentage',-2)}')
                        _LOGGER.debug(f'Value of minSocPercentage read:{self.attrs.get('departureTimers',{}).get('minSocPercentage',-1)}')
                        if data.get('minSocPercentage',-2)==self.attrs.get('departureTimers',{}).get('minSocPercentage',-1):
                            actionSuccessful=True
                    else:
                        sendData = data.get('timers',[])
                        newData = self.attrs.get('departureProfiles',{}).get('timers',[])
                        _LOGGER.debug('Checking if new departure profiles are as expected:')
                        _LOGGER.debug(f'Value of data sent:{sendData}')
                        _LOGGER.debug(f'Value of data read:{newData}')
                        if sendData==newData:
                            actionSuccessful=True
                    retry = retry +1
                if actionSuccessful:
                    self._requests.get('departureprofile', {}).pop('id')
                    return True
                _LOGGER.error('Response to PUT request seemed successful but the departure profiles status did not change as expected.')
                return False
        except (SeatInvalidRequestException, SeatException):
            raise
        except Exception as error:
            _LOGGER.warning(f'Failed to execute departure profile request - {error}')
            self._requests['departureprofile'] = {'status': 'Exception'}
        raise SeatException('Failed to set departure profile schedule')


    # Send a destination to vehicle
    async def send_destination(self, destination=None) -> bool:
        """ Send destination to vehicle. """

        if destination==None:
            _LOGGER.error('No destination provided')
            raise
        else:
            data=[]
            data.append(destination)
        try:
            response = await self._connection.sendDestination(self.vin, self._apibase, data, spin=False)
            if not response:
                _LOGGER.error('Failed to execute send destination request')
                raise SeatException('Failed to execute send destination request')
            else:
                return True
        except (SeatInvalidRequestException, SeatException):
            raise
        except Exception as error:
            _LOGGER.warning(f'Failed to execute send destination request - {error}')
        raise SeatException('Failed to send destination to vehicle')

   # Climatisation electric/auxiliary/windows (CLIMATISATION)
    async def set_climatisation_temp(self, temperature=20) -> bool:
        """Set climatisation target temp."""
        if self.is_electric_climatisation_supported or self.is_auxiliary_climatisation_supported:
            if 16 <= float(temperature) <= 30:
                data = {
                    'climatisationWithoutExternalPower': self.climatisation_without_external_power, 
                    'targetTemperature':    temperature, 
                    'targetTemperatureUnit':    'celsius'
                    }
                mode = 'settings'
            else:
                _LOGGER.error(f'Set climatisation target temp to {temperature} is not supported.')
                raise SeatInvalidRequestException(f'Set climatisation target temp to {temperature} is not supported.')
            return await self._set_climater(mode, data)
        else:
            _LOGGER.error('No climatisation support.')
            raise SeatInvalidRequestException('No climatisation support.')

    async def set_window_heating(self, action = 'stop') -> bool:
        """Turn on/off window heater."""
        if self.is_window_heater_supported:
            if action in ['start', 'stop']:
                data = {'action': {'type': action + 'WindowHeating'}}
            else:
                _LOGGER.error(f'Window heater action "{action}" is not supported.')
                raise SeatInvalidRequestException(f'Window heater action "{action}" is not supported.')
            return await self._set_climater(f'windowHeater {action}', data)
        else:
            _LOGGER.error('No climatisation support.')
            raise SeatInvalidRequestException('No climatisation support.')

    async def set_battery_climatisation(self, mode = False) -> bool:
        """Turn on/off electric climatisation from battery."""
        if self.is_electric_climatisation_supported:
            if mode in [True, False]:
                data = {
                    'climatisationWithoutExternalPower': mode, 
                    'targetTemperature':    self.climatisation_target_temperature, #keep the current target temperature
                    'targetTemperatureUnit':    'celsius'
                    }
                mode = 'settings'
            else:
                _LOGGER.error(f'Set climatisation without external power to "{mode}" is not supported.')
                raise SeatInvalidRequestException(f'Set climatisation without external power to "{mode}" is not supported.')
            return await self._set_climater(mode, data)
        else:
            _LOGGER.error('No climatisation support.')
            raise SeatInvalidRequestException('No climatisation support.')

    async def set_climatisation(self, mode = 'off', temp = None, hvpower = None, spin = None) -> bool:
        """Turn on/off climatisation with electric/auxiliary heater."""
        data = {}
        # Validate user input
        if mode.lower() not in ['electric', 'auxiliary', 'start', 'stop', 'on', 'off']:
            _LOGGER.error(f"Invalid mode for 'set_climatisation': {mode}")
            raise SeatInvalidRequestException(f"Invalid mode for set_climatisation: {mode}")
        elif mode == 'auxiliary' and spin is None:
            raise SeatInvalidRequestException("Starting auxiliary heater requires provided S-PIN")
        if temp is not None:
            if not isinstance(temp, float) and not isinstance(temp, int):
                _LOGGER.error(f"Invalid type for temp. type={type(temp)}")
                raise SeatInvalidRequestException(f"Invalid type for temp")
            elif not 16 <= float(temp) <=30:
                raise SeatInvalidRequestException(f"Invalid value for temp")
        else:
            temp = self.climatisation_target_temperature
        #if hvpower is not None:
        #    if not isinstance(hvpower, bool):
        #        raise SeatInvalidRequestException(f"Invalid type for hvpower")
        if self.is_electric_climatisation_supported:
            if self._relevantCapabilties.get('climatisation', {}).get('active', False):
                if mode in ['Start', 'start', 'Electric', 'electric', 'On', 'on']:
                    mode = 'start'
                if mode in ['start', 'auxiliary']:
                    #if hvpower is not None:
                    #    withoutHVPower = hvpower
                    #else:
                    #    withoutHVPower = self.climatisation_without_external_power
                    data = {
                            'targetTemperature': temp,
                            'targetTemperatureUnit': 'celsius',
                    }
                    return await self._set_climater(mode, data, spin)
                else:
                    if self._requests['climatisation'].get('id', False) or self.electric_climatisation:
                        request_id=self._requests.get('climatisation', 0)
                        mode = 'stop'
                        data={}
                        return await self._set_climater(mode, data, spin)
                    else:
                        _LOGGER.error('Can not stop climatisation because no running request was found')
                        return False
        else:
            _LOGGER.error('No climatisation support.')
        raise SeatInvalidRequestException('No climatisation support.')

    async def _set_climater(self, mode, data, spin = False) -> bool:
        """Climater actions."""
        if not self._relevantCapabilties.get('climatisation', {}).get('active', False):
            _LOGGER.info('Remote control of climatisation functions is not supported.')
            raise SeatInvalidRequestException('Remote control of climatisation functions is not supported.')
        if self._requests['climatisation'].get('id', False):
            timestamp = self._requests.get('climatisation', {}).get('timestamp', datetime.now())
            expired = datetime.now() - timedelta(minutes=1)
            if expired > timestamp:
                self._requests.get('climatisation', {}).pop('id')
            else:
                raise SeatRequestInProgressException('A climatisation action is already in progress')
        try:
            self._requests['latest'] = 'Climatisation'
            response = await self._connection.setClimater(self.vin, self._apibase, mode, data, spin)
            if not response:
                self._requests['climatisation'] = {'status': 'Failed'}
                _LOGGER.error('Failed to execute climatisation request')
                raise SeatException('Failed to execute climatisation request')
            else:
                #self._requests['remaining'] = response.get('rate_limit_remaining', -1)
                self._requests['climatisation'] = {
                    'timestamp': datetime.now(),
                    'status': response.get('state', 'Unknown'),
                    'id': response.get('id', 0),
                }
                # if firebaseStatus is FIREBASE_STATUS_ACTIVATED, the request is assumed successful. Waiting for push notification before rereading status
                if self.firebaseStatus == FIREBASE_STATUS_ACTIVATED:
                    _LOGGER.debug('POST request for climater assumed successful. Waiting for push notification')
                    return True
                # Update the climater data and check, if they have changed as expected
                retry = 0
                actionSuccessful = False
                while not actionSuccessful and retry < 2:
                    await asyncio.sleep(15)
                    await self.get_climater()
                    if mode == 'start':
                        if self.electric_climatisation:
                            actionSuccessful = True
                    elif mode == 'stop':
                        if not self.electric_climatisation:
                            actionSuccessful = True
                    elif mode == 'settings':
                        if data.get('targetTemperature',0)== self.climatisation_target_temperature and data.get('climatisationWithoutExternalPower',False)== self.climatisation_without_external_power:
                            actionSuccessful = True
                    elif mode == 'windowHeater start':
                        if self.window_heater:
                            actionSuccessful = True
                    elif mode == 'windowHeater stop':
                        if not self.window_heater:
                            actionSuccessful = True
                    else:
                        _LOGGER.error(f'Missing code in vehicle._set_climater() for mode {mode}')
                        raise
                    retry = retry +1
                if actionSuccessful:
                    _LOGGER.debug('POST request for climater successful. New status as expected.')
                    self._requests.get('climatisation', {}).pop('id')
                    return True
                _LOGGER.error('Response to POST request seemed successful but the climater status did not change as expected.')
                return False
        except (SeatInvalidRequestException, SeatException):
            raise
        except Exception as error:
            _LOGGER.warning(f'Failed to execute climatisation request - {error}')
            self._requests['climatisation'] = {'status': 'Exception'}
        raise SeatException('Climatisation action failed')

    # Parking heater heating/ventilation (RS)
    async def set_pheater(self, mode, spin) -> bool:
        """Set the mode for the parking heater."""
        if not self.is_pheater_heating_supported:
            _LOGGER.error('No parking heater support.')
            raise SeatInvalidRequestException('No parking heater support.')
        if self._requests['preheater'].get('id', False):
            timestamp = self._requests.get('preheater', {}).get('timestamp', datetime.now())
            expired = datetime.now() - timedelta(minutes=1)
            if expired > timestamp:
                self._requests.get('preheater', {}).pop('id')
            else:
                raise SeatRequestInProgressException('A parking heater action is already in progress')
        if not mode in ['heating', 'ventilation', 'off']:
            _LOGGER.error(f'{mode} is an invalid action for parking heater')
            raise SeatInvalidRequestException(f'{mode} is an invalid action for parking heater')
        if mode == 'off':
            data = {'performAction': {'quickstop': {'active': False }}}
        else:
            data = {'performAction': {'quickstart': {'climatisationDuration': self.pheater_duration, 'startMode': mode, 'active': True }}}
        try:
            self._requests['latest'] = 'Preheater'
            _LOGGER.debug(f'Executing setPreHeater with data: {data}')
            response = await self._connection.setPreHeater(self.vin, self._apibase, data, spin)
            if not response:
                self._requests['preheater'] = {'status': 'Failed'}
                _LOGGER.error(f'Failed to set parking heater to {mode}')
                raise SeatException(f'setPreHeater returned "{response}"')
            else:
                self._requests['remaining'] = response.get('rate_limit_remaining', -1)
                self._requests['preheater'] = {
                    'timestamp': datetime.now(),
                    'status': response.get('state', 'Unknown'),
                    'id': response.get('id', 0),
                }
                return True
        except (SeatInvalidRequestException, SeatException):
            raise
        except Exception as error:
            _LOGGER.warning(f'Failed to set parking heater mode to {mode} - {error}')
            self._requests['preheater'] = {'status': 'Exception'}
        raise SeatException('Pre-heater action failed')

    # Lock 
    async def set_lock(self, action, spin) -> bool:
        """Remote lock and unlock actions."""
        #if not self._services.get('rlu_v1', False):
        if not self._relevantCapabilties.get('transactionHistoryLockUnlock', {}).get('active', False):
            _LOGGER.info('Remote lock/unlock is not supported.')
            raise SeatInvalidRequestException('Remote lock/unlock is not supported.')
        if self._requests['lock'].get('id', False):
            timestamp = self._requests.get('lock', {}).get('timestamp', datetime.now() - timedelta(minutes=5))
            expired = datetime.now() - timedelta(minutes=1)
            if expired > timestamp:
                self._requests.get('lock', {}).pop('id')
            else:
                raise SeatRequestInProgressException('A lock action is already in progress')
        if action not in ['lock', 'unlock']:
            _LOGGER.error(f'Invalid lock action: {action}')
            raise SeatInvalidRequestException(f'Invalid lock action: {action}')
        try:
            self._requests['latest'] = 'Lock'
            response = await self._connection.setLock(self.vin, self._apibase, action, spin)
            if not response:
                self._requests['lock'] = {'status': 'Failed'}
                _LOGGER.error(f'Failed to {action} vehicle')
                raise SeatException(f'Failed to {action} vehicle')
            else:
                self._requests['remaining'] = response.get('rate_limit_remaining', -1)
                self._requests['lock'] = {
                    'timestamp': datetime.now(),
                    'status': response.get('state', 'Unknown'),
                    'id': response.get('id', 0),
                }
                # if firebaseStatus is FIREBASE_STATUS_ACTIVATED, the request is assumed successful. Waiting for push notification before rereading status
                if self.firebaseStatus == FIREBASE_STATUS_ACTIVATED:
                    _LOGGER.debug('POST request for lock/unlock assumed successful. Waiting for push notification')
                    return True
                # Update the lock data and check, if they have changed as expected
                retry = 0
                actionSuccessful = False
                while not actionSuccessful and retry < 2:
                    await asyncio.sleep(15)
                    await self.get_statusreport()
                    if action == 'lock':
                        if self.door_locked:
                            actionSuccessful = True
                    else:
                        if not self.door_locked:
                            actionSuccessful = True
                    retry = retry +1
                if actionSuccessful:
                    _LOGGER.debug('POST request for lock/unlock successful. New status as expected.')
                    self._requests.get('lock', {}).pop('id')
                    return True
                _LOGGER.error('Response to POST request seemed successful but the lock status did not change as expected.')
                return False
        except (SeatInvalidRequestException, SeatException):
            raise
        except Exception as error:
            _LOGGER.warning(f'Failed to {action} vehicle - {error}')
            self._requests['lock'] = {'status': 'Exception'}
        raise SeatException('Lock action failed')

    # Honk and flash (RHF)
    async def set_honkandflash(self, action, lat=None, lng=None) -> bool:
        """Turn on/off honk and flash."""
        if not self._relevantCapabilties.get('honkAndFlash', {}).get('active', False):
            _LOGGER.info('Remote honk and flash is not supported.')
            raise SeatInvalidRequestException('Remote honk and flash is not supported.')
        if self._requests['honkandflash'].get('id', False):
            timestamp = self._requests.get('honkandflash', {}).get('timestamp', datetime.now() - timedelta(minutes=2))
            expired = datetime.now() - timedelta(minutes=1)
            if expired > timestamp:
                self._requests.get('honkandflash', {}).pop('id')
            else:
                raise SeatRequestInProgressException('A honk and flash action is already in progress')
        if action == 'flash':
            operationCode = 'flash'
        elif action == 'honkandflash':
            operationCode = 'honkandflash'
        else:
            raise SeatInvalidRequestException(f'Invalid action "{action}", must be one of "flash" or "honkandflash"')
        try:
            # Get car position
            if lat is None:
                lat = self.attrs.get('findCarResponse', {}).get('lat', None)
            if lng is None:
                lng = self.attrs.get('findCarResponse', {}).get('lon', None)
            if lat is None or lng is None:
                raise SeatConfigException('No location available, location information is needed for this action')
            lat = int(lat*10000.0)/10000.0
            lng = int(lng*10000.0)/10000.0
            data = {
                    'mode': operationCode,
                    'userPosition': {
                        'latitude': lat,
                        'longitude': lng
                    }
            }
            self._requests['latest'] = 'HonkAndFlash'
            response = await self._connection.setHonkAndFlash(self.vin, self._apibase, data)
            if not response:
                self._requests['honkandflash'] = {'status': 'Failed'}
                _LOGGER.error(f'Failed to execute honk and flash action')
                raise SeatException(f'Failed to execute honk and flash action')
            else:
                self._requests['remaining'] = response.get('rate_limit_remaining', -1)
                self._requests['honkandflash'] = {
                    'timestamp': datetime.now(),
                    'status': response.get('state', 'Unknown'),
                    'id': response.get('id', 0),
                }
                return True
        except (SeatInvalidRequestException, SeatException):
            raise
        except Exception as error:
            _LOGGER.warning(f'Failed to {action} vehicle - {error}')
            self._requests['honkandflash'] = {'status': 'Exception'}
        raise SeatException('Honk and flash action failed')

    # Refresh vehicle data (VSR)
    async def set_refresh(self) -> bool:
        """Wake up vehicle and update status data."""
        if not self._relevantCapabilties.get('state', {}).get('active', False):
           _LOGGER.info('Data refresh is not supported.')
           raise SeatInvalidRequestException('Data refresh is not supported.')
        if self._requests['refresh'].get('id', False):
            timestamp = self._requests.get('refresh', {}).get('timestamp', datetime.now() - timedelta(minutes=5))
            expired = datetime.now() - timedelta(minutes=1)
            if expired > timestamp:
                self._requests.get('refresh', {}).pop('id')
            else:
                raise SeatRequestInProgressException('Last data refresh request less than 3 minutes ago')
        try:
            self._requests['latest'] = 'Refresh'
            response = await self._connection.setRefresh(self.vin, self._apibase)
            if not response:
                _LOGGER.error('Failed to request vehicle update')
                self._requests['refresh'] = {'status': 'Failed'}
                raise SeatException('Failed to execute data refresh')
            else:
                self._requests['remaining'] = response.get('rate_limit_remaining', -1)
                self._requests['refresh'] = {
                    'timestamp': datetime.now(),
                    'status': response.get('status', 'Unknown'),
                    'id': response.get('id', 0)
                }
                # if firebaseStatus is FIREBASE_STATUS_ACTIVATED, the request is assumed successful. Waiting for push notification before rereading status
                if self.firebaseStatus == FIREBASE_STATUS_ACTIVATED:
                    _LOGGER.debug('POST request for wakeup vehicle assumed successful. Waiting for push notification')
                    return True
                await self.update(updateType=1) #full update after set_refresh
                return True
        except(SeatInvalidRequestException, SeatException):
            raise
        except Exception as error:
            _LOGGER.warning(f'Failed to execute data refresh - {error}')
            self._requests['refresh'] = {'status': 'Exception'}
        raise SeatException('Data refresh failed')

 #### Vehicle class helpers ####
    # Vehicle info
    @property
    def attrs(self):
        return self._states

    def has_attr(self, attr):
        return is_valid_path(self.attrs, attr)

    def get_attr(self, attr):
        return find_path(self.attrs, attr)

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
        return self._url

    @property
    def unique_id(self):
        return self.vin


 #### Information from vehicle states ####
    # Car information
    @property
    def nickname(self):
        return self._properties.get('vehicleNickname', '')

    @property
    def is_nickname_supported(self) -> bool:
        if self._properties.get('vehicleNickname', False):
            return True
        else:
            return False

    @property
    def deactivated(self) -> bool:
        if 'mode' in self._connectivities:
            if self._connectivities.get('mode','')=='online':
                return False
        return True
        #for car in self.attrs.get('realCars', []):
        #    if self.vin == car.get('vehicleIdentificationNumber', ''):
        #        return car.get('deactivated', False)

    @property
    def is_deactivated_supported(self) -> bool:
        if 'mode' in self._connectivities:
            return True
        return False
        #for car in self.attrs.get('realCars', []):
        #    if self.vin == car.get('vehicleIdentificationNumber', ''):
        #        if car.get('deactivated', False):
        #            return True

    @property
    def brand(self):
        """Return brand"""
        return self._specification.get('factoryModel', False).get('vehicleBrand', 'Unknown')

    @property
    def is_brand_supported(self) -> bool:
        """Return true if brand is supported."""
        if self._specification.get('factoryModel', False).get('vehicleBrand', False):
            return True
        else:
            return False

    @property
    def model(self):
        """Return model"""
        if self._specification.get('carBody', False):
            model = self._specification.get('factoryModel', False).get('vehicleModel', 'Unknown') + ' ' + self._specification.get('carBody', '')
            return model
        return self._specification.get('factoryModel', False).get('vehicleModel', 'Unknown')

    @property
    def is_model_supported(self) -> bool:
        """Return true if model is supported."""
        if self._specification.get('factoryModel', False).get('vehicleModel', False):
            return True
        else:
            return False

    @property
    def model_year(self):
        """Return model year"""
        return self._specification.get('factoryModel', False).get('modYear', 'Unknown')

    @property
    def is_model_year_supported(self) -> bool:
        """Return true if model year is supported."""
        if self._specification.get('factoryModel', False).get('modYear', False):
            return True
        else:
            return False

    @property
    def model_image_small(self):
        """Return URL for model image"""
        return self._modelimages.get('images','').get('front_cropped','')

    @property
    def is_model_image_small_supported(self) -> bool:
        """Return true if model image url is not None."""
        if self._modelimages is not None:
            if self._modelimages.get('images','').get('front_cropped','')!='':
                return True
        return False

    @property
    def model_image_large(self):
        """Return URL for model image"""
        return self._modelimages.get('images','').get('front', '')

    @property
    def is_model_image_large_supported(self) -> bool:
        """Return true if model image url is not None."""
        if self._modelimages is not None:
            return True
        else:
            return False

    # Lights
    @property
    def parking_light(self) -> bool:
        """Return true if parking light is on"""
        response = self.attrs.get('status').get('lights', 0)
        if response == 'on':
            return True
        else:
            return False

    @property
    def is_parking_light_supported(self) -> bool:
        """Return true if parking light is supported"""
        if self.attrs.get('status', False):
            if 'lights' in self.attrs.get('status'):
                return True
        return False

    # Connection status
    @property
    def last_connected(self) -> datetime:
        """Return when vehicle was last connected to connect servers."""
        last_connected_utc = self.attrs.get('status').get('updatedAt','')
        if isinstance(last_connected_utc, datetime):
            last_connected = last_connected_utc.replace(tzinfo=timezone.utc).astimezone(tz=None)
        else:
            # it seems, that last_connected_utc was provided as a string. If the string contains a '.', then the timestamp was provided with milliseconds
            if '.' in last_connected_utc: 
                last_connected = datetime.strptime(last_connected_utc,'%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc).astimezone(tz=None)
            else:
                last_connected = datetime.strptime(last_connected_utc,'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).astimezone(tz=None)
        return last_connected #.strftime('%Y-%m-%d %H:%M:%S')

    @property
    def is_last_connected_supported(self) -> bool:
        """Return when vehicle was last connected to connect servers."""
        if 'updatedAt' in self.attrs.get('status', {}):
            return True
        return False

    # Update status
    @property
    def last_full_update(self):
        """Return when the last full update for the vehicle took place."""
        return self._last_full_update.astimezone(tz=None)

    @property
    def is_last_full_update_supported(self) -> bool:
        """Return when last full update for vehicle took place."""
        if hasattr(self,'_last_full_update'):
            return True
        return False

    # Service information
    @property
    def distance(self) -> int:
        """Return vehicle odometer."""
        value = self.attrs.get('mileage').get('mileageKm', 0)
        return int(value)

    @property
    def is_distance_supported(self) -> bool:
        """Return true if odometer is supported"""
        if self.attrs.get('mileage', False):
            if 'mileageKm' in self.attrs.get('mileage'):
                return True
        return False

    @property
    def service_inspection(self) -> int:
        """Return time left until service inspection"""
        value = -1
        value = int(self.attrs.get('maintenance', {}).get('inspectionDueDays', 0))
        return int(value)

    @property
    def is_service_inspection_supported(self) -> bool:
        if self.attrs.get('maintenance', False):
            if 'inspectionDueDays' in self.attrs.get('maintenance'):
                return True
        return False

    @property
    def service_inspection_distance(self) -> int:
        """Return time left until service inspection"""
        value = -1
        value = int(self.attrs.get('maintenance').get('inspectionDueKm', 0))
        return int(value)

    @property
    def is_service_inspection_distance_supported(self) -> bool:
        if self.attrs.get('maintenance', False):
            if 'inspectionDueKm' in self.attrs.get('maintenance'):
                return True
        return False

    @property
    def oil_inspection(self) -> int:
        """Return time left until oil inspection"""
        value = -1
        value = int(self.attrs.get('maintenance', {}).get('oilServiceDueDays', 0))
        return int(value)

    @property
    def is_oil_inspection_supported(self) -> bool:
        if self.attrs.get('maintenance', False):
            if 'oilServiceDueDays' in self.attrs.get('maintenance'):
                if self.attrs.get('maintenance').get('oilServiceDueDays', None) is not None:
                    return True
        return False

    @property
    def oil_inspection_distance(self) -> int:
        """Return distance left until oil inspection"""
        value = -1
        value = int(self.attrs.get('maintenance').get('oilServiceDueKm', 0))
        return int(value)

    @property
    def is_oil_inspection_distance_supported(self) -> bool:
        if self.attrs.get('maintenance', False):
            if 'oilServiceDueKm' in self.attrs.get('maintenance'):
                if self.attrs.get('maintenance').get('oilServiceDueKm', None) is not None:
                    return True
        return False

    @property
    def adblue_level(self) -> int:
        """Return adblue level."""
        return int(self.attrs.get('maintenance', {}).get('0x02040C0001', {}).get('value', 0))

    @property
    def is_adblue_level_supported(self) -> bool:
        """Return true if adblue level is supported."""
        if self.attrs.get('maintenance', False):
            if '0x02040C0001' in self.attrs.get('maintenance'):
                if 'value' in self.attrs.get('maintenance')['0x02040C0001']:
                    if self.attrs.get('maintenance')['0x02040C0001'].get('value', 0) is not None:
                        return True
        return False

    # Charger related states for EV and PHEV
    @property
    def charging(self) -> int:
        """Return battery level"""
        #cstate = self.attrs.get('charging').get('status').get('charging').get('state','')
        cstate = self.attrs.get('mycar',{}).get('services',{}).get('charging',{}).get('status','')
        return 1 if cstate in ['charging', 'Charging'] else 0

    @property
    def is_charging_supported(self) -> bool:
        """Return true if charging is supported"""
        #if self.attrs.get('charging', False):
        #    if 'status' in self.attrs.get('charging', {}):
        #        if 'charging' in self.attrs.get('charging')['status']:
        #            if 'state' in self.attrs.get('charging')['status']['charging']:
        #                return True
        if self.attrs.get('mycar', False):
            if 'services' in self.attrs.get('mycar', {}):
                if 'charging' in self.attrs.get('mycar')['services']:
                    if 'status' in self.attrs.get('mycar')['services']['charging']:
                        return True
        return False

    @property
    def min_charge_level(self):
        """Return the charge level that car charges directly to"""
        if self.attrs.get('departuretimers', {}):
            return self.attrs.get('departuretimers', {}).get('minSocPercentage', 0)
        else:
            return 0

    @property
    def is_min_charge_level_supported(self) -> bool:
        """Return true if car supports setting the min charge level"""
        if self.attrs.get('departuretimers', {}).get('minSocPercentage', False):
            return True
        return False

    @property
    def battery_level(self) -> int:
        """Return battery level"""
        #if self.attrs.get('charging', False):
        #    return int(self.attrs.get('charging').get('status', {}).get('battery', {}).get('currentSocPercentage', 0))
        if self.attrs.get('mycar', False):
            return int(self.attrs.get('mycar',{}).get('services', {}).get('charging', {}).get('currentPct', 0))
        else:
            return 0

    @property
    def is_battery_level_supported(self) -> bool:
        """Return true if battery level is supported"""
        #if self.attrs.get('charging', False):
        #    if 'status' in self.attrs.get('charging'):
        #        if 'battery' in self.attrs.get('charging')['status']:
        #            if 'currentSocPercentage' in self.attrs.get('charging')['status']['battery']:
        #                return True
        if self.attrs.get('mycar', False):
            if 'services' in self.attrs.get('mycar'):
                if 'charging' in self.attrs.get('mycar')['services']:
                    if 'currentPct' in self.attrs.get('mycar')['services']['charging']:
                        return True
        return False

    @property
    def charge_max_ampere(self):
        """Return charger max ampere setting."""
        if self.attrs.get('charging', False):
            if self.attrs.get('charging',{}).get('info',{}).get('settings',{}).get('maxChargeCurrentAcInAmperes', None):
                return self.attrs.get('charging',{}).get('info',{}).get('settings',{}).get('maxChargeCurrentAcInAmperes', 0)
            else:
                return self.attrs.get('charging').get('info').get('settings').get('maxChargeCurrentAc')
        return 0

    @property
    def is_charge_max_ampere_supported(self) -> bool:
        """Return true if Charger Max Ampere is supported"""
        if self.attrs.get('charging', False):
            if 'info' in self.attrs.get('charging', {}):
                if 'settings' in self.attrs.get('charging')['info']:
                    if 'maxChargeCurrentAc' in self.attrs.get('charging', {})['info']['settings']:
                        return True
        return False

    @property
    def slow_charge(self) -> bool:
        """Return charger max ampere setting."""
        if self.charge_max_ampere=='reduced':
            return True
        return False

    @property
    def is_slow_charge_supported(self) -> bool:
        """Return true if Slow Charge is supported"""
        if self.is_charge_max_ampere_supported:
            if self.charge_max_ampere in ('reduced', 'maximum'):
                return True
        return False

    @property
    def charging_cable_locked(self) -> bool:
        """Return plug locked state"""
        response = ''
        if self.attrs.get('charging', False):
            response = self.attrs.get('charging').get('status', {}).get('plug', {}).get('lock', '')
        return True if response in ['Locked', 'locked'] else False

    @property
    def is_charging_cable_locked_supported(self) -> bool:
        """Return true if plug locked state is supported"""
        if self.attrs.get('charging', False):
            if 'status' in self.attrs.get('charging'):
                if 'plug' in self.attrs.get('charging')['status']:
                    if 'lock' in self.attrs.get('charging')['status']['plug']:
                        return True
        return False

    @property
    def charging_cable_connected(self) -> bool:
        """Return plug locked state"""
        response = ''
        if self.attrs.get('charging', False):
            response = self.attrs.get('charging', {}).get('status', {}).get('plug').get('connection', 0)
        return True if response in ['Connected', 'connected'] else False

    @property
    def is_charging_cable_connected_supported(self) -> bool:
        """Return true if charging cable connected is supported"""
        if self.attrs.get('charging', False):
            if 'status' in self.attrs.get('charging', {}):
                if 'plug' in self.attrs.get('charging').get('status', {}):
                    if 'connection' in self.attrs.get('charging')['status'].get('plug', {}):
                        return True
        return False

    @property
    def charging_time_left(self):
        """Return minutes to charging complete"""
        #if self.external_power:
        if self.charging:
            #if self.attrs.get('charging', {}).get('status', {}).get('charging', {}).get('remainingTimeInMinutes', False):
            #    minutes = int(self.attrs.get('charging', {}).get('status', {}).get('charging', {}).get('remainingTimeInMinutes', 0))
            if self.attrs.get('mycar', {}).get('services', {}).get('charging', {}).get('remainingTime', False):
                minutes = int(self.attrs.get('mycar', {}).get('services', {}).get('charging', {}).get('remainingTime', 0))
            else:
                minutes = 0
            return minutes
            #try:
            #    if minutes == -1: return '00:00'
            #    if minutes == 65535: return '00:00'
            #    return "%02d:%02d" % divmod(minutes, 60)
            #except Exception:
            #    pass
        #return '00:00'
        return 0

    @property
    def is_charging_time_left_supported(self) -> bool:
        """Return true if charging is supported"""
        return self.is_charging_supported

    @property
    def charging_power(self) -> int:
        """Return charging power in watts."""
        if self.attrs.get('charging', False):
            return int(self.attrs.get('charging', {}).get('chargingPowerInWatts', 0))
        else:
            return 0

    @property
    def is_charging_power_supported(self) -> bool:
        """Return true if charging power is supported."""
        if self.attrs.get('charging', False):
            if self.attrs.get('charging', {}).get('chargingPowerInWatts', False) is not False:
                return True
        return False

    @property
    def charge_rate(self) -> int:
        """Return charge rate in km per h."""
        if self.attrs.get('charging', False):
            return int(self.attrs.get('charging', {}).get('chargingRateInKilometersPerHour', 0))
        else:
            return 0

    @property
    def is_charge_rate_supported(self) -> bool:
        """Return true if charge rate is supported."""
        if self.attrs.get('charging', False):
            if self.attrs.get('charging', {}).get('chargingRateInKilometersPerHour', False) is not False:
                return True
        return False

    @property
    def external_power(self):
        """Return true if external power is connected."""
        response = ''
        if self.attrs.get('charging', False):
            response = self.attrs.get('charging', {}).get('status', {}).get('plug', {}).get('externalPower', '')
        else:
            response = ''
        return True if response in ['stationConnected', 'available', 'Charging', 'ready'] else False

    @property
    def is_external_power_supported(self) -> bool:
        """External power supported."""
        if self.attrs.get('charging', {}).get('status', {}).get('plug, {}').get('externalPower', False):
            return True
        else:
            return False

    @property
    def charging_state(self):
        """Return true if vehicle is charging."""
        #check = self.attrs.get('charging', {}).get('status', {}).get('state', '')
        check = self.attrs.get('mycar',{}).get('services',{}).get('charging',{}).get('status','')
        if check in ('charging','Charging'):
            return True
        else:
            return False

    @property
    def is_charging_state_supported(self) -> bool:
        """Charging state supported."""
        #if self.attrs.get('charging', {}).get('status', {}).get('state', False):
        #    return True
        if self.attrs.get('mycar', False):
            if 'services' in self.attrs.get('mycar', {}):
                if 'charging' in self.attrs.get('mycar')['services']:
                    if 'status' in self.attrs.get('mycar')['services']['charging']:
                        return True
        return False

    @property
    def energy_flow(self):
        """Return true if energy is flowing to (i.e. charging) or from (i.e. climating with battery power) the battery."""
        if self.charging_state:
            return True
        #check = self.attrs.get('charging', {}).get('status', {}).get('state', '')
        check = self.attrs.get('mycar',{}).get('services',{}).get('charging',{}).get('status','')
        if self.is_electric_climatisation_supported:
            if self.electric_climatisation and check not in {'charging','Charging', 'conservation','Conservation'}:
                # electric climatisation is on and car is not charging or conserving power 
                return True
        return False

    @property
    def is_energy_flow_supported(self) -> bool:
        """Energy flow supported."""
        if self.is_charging_state_supported:
            return True
        else:
            return False

    @property
    def target_soc(self):
        """Return the target soc."""
        return self.attrs.get('charging', {}).get('info', {}).get('settings', {}).get('targetSoc', 0)

    @property
    def is_target_soc_supported(self) -> bool:
        """Target state of charge supported."""
        if self.attrs.get('charging', {}).get('info', {}).get('settings', {}).get('targetSoc', False):
            return True
        else:
            return False

    # Vehicle location states
    @property
    def position(self):
        """Return  position."""
        output = {}
        try:
            if self.vehicle_moving:
                output = {
                    'lat': None,
                    'lng': None,
                    'address': None,
                    'timestamp': None
                }
            else:
                posObj = self.attrs.get('findCarResponse', {})
                lat = posObj.get('lat')
                lng = posObj.get('lon')
                position_to_address = posObj.get('position_to_address')
                parkingTime = posObj.get('parkingTimeUTC', None)
                output = {
                    'lat' : lat,
                    'lng' : lng,
                    'address': position_to_address,
                    'timestamp' : parkingTime
                }
        except:
            output = {
                'lat': '?',
                'lng': '?',
            }
        return output

    @property
    def is_position_supported(self) -> bool:
        """Return true if carfinder_v1 service is active."""
        if self.attrs.get('findCarResponse', {}).get('lat', False):
            return True
        elif self.attrs.get('isMoving', False):
            return True
        return False

    @property
    def vehicle_moving(self) -> bool:
        """Return true if vehicle is moving."""
        return self.attrs.get('isMoving', False)

    @property
    def is_vehicle_moving_supported(self) -> bool:
        """Return true if vehicle supports position."""
        if self.is_position_supported:
            return True
        else:
            return False

    @property
    def parking_time(self) -> str:
        """Return timestamp of last parking time."""
        parkTime_utc = self.attrs.get('findCarResponse', {}).get('parkingTimeUTC', 'Unknown')
        if isinstance(parkTime_utc, datetime):
            parkTime = parkTime_utc.replace(tzinfo=timezone.utc).astimezone(tz=None)
        else:
            parkTime = datetime.strptime(parkTime_utc,'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).astimezone(tz=None)
        return parkTime.strftime('%Y-%m-%d %H:%M:%S')

    @property
    def is_parking_time_supported(self) -> bool:
        """Return true if vehicle parking timestamp is supported."""
        if 'parkingTimeUTC' in self.attrs.get('findCarResponse', {}):
            return True
        else:
            return False

    # Vehicle fuel level and range
    @property
    def primary_range(self):
        value = -1
        if 'engines' in self.attrs.get('mycar'):
            value = self.attrs.get('mycar')['engines']['primary'].get('rangeKm', 0)
        return int(value)

    @property
    def is_primary_range_supported(self) -> bool:
        if self.attrs.get('mycar', False):
            if 'engines' in self.attrs.get('mycar', {}):
                if 'primary' in self.attrs.get('mycar')['engines']:
                    if 'rangeKm' in self.attrs.get('mycar')['engines']['primary']:
                        return True
        return False

    @property
    def primary_drive(self):
        value=''
        if 'engines' in self.attrs.get('mycar'):
            value = self.attrs.get('mycar')['engines']['primary'].get('fuelType', '')
        return value

    @property
    def is_primary_drive_supported(self) -> bool:
        if self.attrs.get('mycar', False):
            if 'engines' in self.attrs.get('mycar', {}):
                if 'primary' in self.attrs.get('mycar')['engines']:
                    if 'fuelType' in self.attrs.get('mycar')['engines']['primary']:
                        return True
        return False

    @property
    def secondary_range(self):
        value = -1
        if 'engines' in self.attrs.get('mycar'):
            value = self.attrs.get('mycar')['engines']['secondary'].get('rangeKm', 0)
        return int(value)
 
    @property
    def is_secondary_range_supported(self) -> bool:
        if self.attrs.get('mycar', False):
            if 'engines' in self.attrs.get('mycar', {}):
                if 'secondary' in self.attrs.get('mycar')['engines']:
                    if 'rangeKm' in self.attrs.get('mycar')['engines']['secondary']:
                        return True
        return False

    @property
    def secondary_drive(self):
        value=''
        if 'engines' in self.attrs.get('mycar'):
            value = self.attrs.get('mycar')['engines']['secondary'].get('fuelType', '')
        return value
 
    @property
    def is_secondary_drive_supported(self) -> bool:
        if self.attrs.get('mycar', False):
            if 'engines' in self.attrs.get('mycar', {}):
                if 'secondary' in self.attrs.get('mycar')['engines']:
                    if 'fuelType' in self.attrs.get('mycar')['engines']['secondary']:
                        return True
        return False

    @property
    def electric_range(self):
        value = -1
        if self.is_secondary_drive_supported:
            if self.secondary_drive == 'electric':
                return self.secondary_range
        elif self.is_primary_drive_supported:
            if self.primary_drive == 'electric':
                return self.primary_range
        return -1

    @property
    def is_electric_range_supported(self) -> bool:
        if self.is_secondary_drive_supported:
            if self.secondary_drive == 'electric':
                return self.is_secondary_range_supported
        elif self.is_primary_drive_supported:
            if self.primary_drive == 'electric':
                return self.is_primary_range_supported
        return False

    @property
    def combustion_range(self):
        value = -1
        if self.is_primary_drive_supported:
            if not self.primary_drive == 'electric':
                return self.primary_range
        elif self.is_secondary_drive_supported:
            if not self.secondary_drive == 'electric':
                return self.secondary_range
        return -1

    @property
    def is_combustion_range_supported(self) -> bool:
        if self.is_primary_drive_supported:
            if not self.primary_drive == 'electric':
                return self.is_primary_range_supported
        elif self.is_secondary_drive_supported:
            if not self.secondary_drive == 'electric':
                return self.is_secondary_range_supported
        return False

    @property
    def combined_range(self) -> int:
        return int(self.combustion_range)+int(self.electric_range)

    @property
    def is_combined_range_supported(self) -> bool:
        if self.is_combustion_range_supported and self.is_electric_range_supported:
            return True
        return False

    @property
    def fuel_level(self) -> int:
        value = -1
        if self.is_fuel_level_supported:
            if not self.primary_drive == 'electric':
                value= self.attrs.get('mycar')['engines']['primary'].get('levelPct',0)
            elif not self.secondary_drive == 'electric':
                 value= self.attrs.get('mycar')['engines']['primary'].get('levelPct',0)
        return int(value)

    @property
    def is_fuel_level_supported(self) -> bool:
        if self.is_primary_drive_supported:
            if not self.primary_drive == 'electric':
                if "levelPct" in self.attrs.get('mycar')['engines']['primary']:
                    return self.is_primary_range_supported
        elif self.is_secondary_drive_supported:
            if not self.secondary_drive == 'electric':
                if "levelPct" in self.attrs.get('mycar')['engines']['secondary']:
                    return self.is_secondary_range_supported
        return False

    # Climatisation settings
    @property
    def climatisation_target_temperature(self):
        """Return the target temperature from climater."""
        if self.attrs.get('climater', False):
            value = self.attrs.get('climater').get('settings', {}).get('targetTemperatureInCelsius', 0)
            return value
        return False

    @property
    def is_climatisation_target_temperature_supported(self) -> bool:
        """Return true if climatisation target temperature is supported."""
        if self.attrs.get('climater', False):
            if 'settings' in self.attrs.get('climater', {}):
                if 'targetTemperatureInCelsius' in self.attrs.get('climater', {})['settings']:
                    return True
        return False

    @property
    def climatisation_time_left(self):
        """Return time left for climatisation in hours:minutes."""
        if self.attrs.get('airConditioning', {}).get('remainingTimeToReachTargetTemperatureInSeconds', False):
            minutes = int(self.attrs.get('airConditioning', {}).get('remainingTimeToReachTargetTemperatureInSeconds', 0))/60
            try:
                if not 0 <= minutes <= 65535:
                    return "00:00"
                return "%02d:%02d" % divmod(minutes, 60)
            except Exception:
                pass
        return "00:00"

    @property
    def is_climatisation_time_left_supported(self) -> bool:
        """Return true if remainingTimeToReachTargetTemperatureInSeconds is supported."""
        if self.attrs.get('airConditioning', {}).get('remainingTimeToReachTargetTemperatureInSeconds', False):
            return True
        return False

    @property
    def climatisation_without_external_power(self):
        """Return state of climatisation from battery power."""
        return self.attrs.get('climater').get('settings').get('climatisationWithoutExternalPower', False)

    @property
    def is_climatisation_without_external_power_supported(self) -> bool:
        """Return true if climatisation on battery power is supported."""
        if self.attrs.get('climater', False):
            if 'settings' in self.attrs.get('climater', {}):
                if 'climatisationWithoutExternalPower' in self.attrs.get('climater', {})['settings']:
                    return True
        return False

    @property
    def outside_temperature(self):
        """Return outside temperature."""
        response = int(self.attrs.get('StoredVehicleDataResponseParsed')['0x0301020001'].get('value', 0))
        if response:
            return round(float((response / 10) - 273.15), 1)
        else:
            return False

    @property
    def is_outside_temperature_supported(self) -> bool:
        """Return true if outside temp is supported"""
        if self.attrs.get('StoredVehicleDataResponseParsed', False):
            if '0x0301020001' in self.attrs.get('StoredVehicleDataResponseParsed'):
                if "value" in self.attrs.get('StoredVehicleDataResponseParsed')['0x0301020001']:
                    return True
        return False

    # Climatisation, electric
    @property
    def electric_climatisation_attributes(self):
        """Return climatisation attributes."""
        data = {
            'source': self.attrs.get('climater', {}).get('settings', {}).get('heaterSource', {}).get('content', ''),
            'status': self.attrs.get('climater', {}).get('status', {}).get('climatisationStatus', {}).get('climatisationState', '')
        }
        return data

    @property
    def is_electric_climatisation_attributes_supported(self) -> bool:
        """Return true if vehichle has climater."""
        return self.is_climatisation_supported

    @property
    def electric_climatisation(self) -> bool:
        """Return status of climatisation."""
        if self.attrs.get('climater', {}).get('status', {}).get('climatisationStatus', {}).get('climatisationState', False):
            climatisation_type = self.attrs.get('climater', {}).get('settings', {}).get('heaterSource', '')
            status = self.attrs.get('climater', {}).get('status', {}).get('climatisationStatus', {}).get('climatisationState', '')
            if status in ['heating', 'cooling', 'on']: #and climatisation_type == 'electric':
                return True
        return False

    @property
    def is_electric_climatisation_supported(self) -> bool:
        """Return true if vehichle has climater."""
        return self.is_climatisation_supported

    @property
    def auxiliary_climatisation(self) -> bool:
        """Return status of auxiliary climatisation."""
        climatisation_type = self.attrs.get('climater', {}).get('settings', {}).get('heaterSource', {}).get('content', '')
        status = self.attrs.get('climater', {}).get('status', {}).get('climatisationStatus', {}).get('climatisationState', '')
        if status in ['heating', 'cooling', 'ventilation', 'heatingAuxiliary', 'on'] and climatisation_type == 'auxiliary':
            return True
        elif status in ['heatingAuxiliary'] and climatisation_type == 'electric':
            return True
        else:
            return False

    @property
    def is_auxiliary_climatisation_supported(self) -> bool:
        """Return true if vehicle has auxiliary climatisation."""
        #if self._services.get('rclima_v1', False):
        #if self._relevantCapabilties.get('climatisation', {}).get('active', False):
            #functions = self._services.get('rclima_v1', {}).get('operations', [])
            #for operation in functions:
            #    if operation['id'] == 'P_START_CLIMA_AU':
            #if 'P_START_CLIMA_AU' in functions:
            #        return True
        return False

    @property
    def is_climatisation_supported(self) -> bool:
        """Return true if climatisation has State."""
        if self.attrs.get('climater', {}).get('status', {}).get('climatisationStatus', {}).get('climatisationState', False):
            return True
        return False

    @property
    def window_heater(self) -> bool:
        """Return status of window heater."""
        if self.attrs.get('climater', False):
            for elem in self.attrs.get('climater', {}).get('status', {}).get('windowHeatingStatus', {}).get('windowHeatingStatus', []):
                if elem.get('windowHeatingState','off')=='on':
                    return True
        return False

    @property
    def is_window_heater_supported(self) -> bool:
        """Return true if vehichle has heater."""
        if self.is_electric_climatisation_supported:
            if self.attrs.get('climater', False):
                if self.attrs.get('climater', {}).get('status', {}).get('windowHeatingStatus', {}).get('windowHeatingStatus', []):
                    if len(self.attrs.get('climater', {}).get('status', {}).get('windowHeatingStatus', {}).get('windowHeatingStatus', []))>0:
                        return True
        return False

    @property
    def seat_heating(self) -> bool:
        """Return status of seat heating."""
        if self.attrs.get('airConditioning', {}).get('seatHeatingSupport', False):
            for element in self.attrs.get('airConditioning', {}).get('seatHeatingSupport', {}):
                if self.attrs.get('airConditioning', {}).get('seatHeatingSupport', {}).get(element, False):
                    return True
        return False

    @property
    def is_seat_heating_supported(self) -> bool:
        """Return true if vehichle has seat heating."""
        if self.attrs.get('airConditioning', {}).get('seatHeatingSupport', False):
            return True
        return False

    @property
    def warnings(self) -> int:
        """Return warnings."""
        return len(self.attrs.get('warninglights', {}).get('statuses',[]))

    @property
    def is_warnings_supported(self) -> bool:
        """Return true if vehichle has warnings."""
        if self.attrs.get('warninglights', False):
            return True
        return False

    # Parking heater, "legacy" auxiliary climatisation
    @property
    def pheater_duration(self):
        return self._climate_duration

    @pheater_duration.setter
    def pheater_duration(self, value):
        if value in [10, 20, 30, 40, 50, 60]:
            self._climate_duration = value
        else:
            _LOGGER.warning(f'Invalid value for duration: {value}')

    @property
    def is_pheater_duration_supported(self) -> bool:
        return self.is_pheater_heating_supported

    @property
    def pheater_ventilation(self):
        """Return status of combustion climatisation."""
        return self.attrs.get('heating', {}).get('climatisationStateReport', {}).get('climatisationState', False) == 'ventilation'

    @property
    def is_pheater_ventilation_supported(self) -> bool:
        """Return true if vehichle has combustion climatisation."""
        return self.is_pheater_heating_supported

    @property
    def pheater_heating(self):
        """Return status of combustion engine heating."""
        return self.attrs.get('heating', {}).get('climatisationStateReport', {}).get('climatisationState', False) == 'heating'

    @property
    def is_pheater_heating_supported(self) -> bool:
        """Return true if vehichle has combustion engine heating."""
        if self.attrs.get('heating', {}).get('climatisationStateReport', {}).get('climatisationState', False):
            return True
        else:
            return False

    @property
    def pheater_status(self):
        """Return status of combustion engine heating/ventilation."""
        return self.attrs.get('heating', {}).get('climatisationStateReport', {}).get('climatisationState', 'Unknown')

    @property
    def is_pheater_status_supported(self) -> bool:
        """Return true if vehichle has combustion engine heating/ventilation."""
        if self.attrs.get('heating', {}).get('climatisationStateReport', {}).get('climatisationState', False):
            return True
        else:
            return False

    # Windows
    @property
    def windows_closed(self) -> bool:
        return (self.window_closed_left_front and self.window_closed_left_back and self.window_closed_right_front and self.window_closed_right_back)

    @property
    def is_windows_closed_supported(self) -> bool:
        """Return true if window state is supported"""
        response = ""
        if self.attrs.get('status', False):
            if 'windows' in self.attrs.get('status'):
                response = self.attrs.get('status')['windows'].get('frontLeft', '')
        return True if response != '' else False

    @property
    def window_closed_left_front(self):
        response = self.attrs.get('status')['windows'].get('frontLeft', '')
        if response == 'closed':
            return True
        else:
            return False

    @property
    def is_window_closed_left_front_supported(self) -> bool:
        """Return true if window state is supported"""
        response = ""
        if self.attrs.get('status', False):
            if 'windows' in self.attrs.get('status'):
                response = self.attrs.get('status')['windows'].get('frontLeft', '')
        return True if response != "" else False

    @property
    def window_closed_right_front(self) -> bool:
        response = self.attrs.get('status')['windows'].get('frontRight', '')
        if response == 'closed':
            return True
        else:
            return False

    @property
    def is_window_closed_right_front_supported(self) -> bool:
        """Return true if window state is supported"""
        response = ""
        if self.attrs.get('status', False):
            if 'windows' in self.attrs.get('status'):
                response = self.attrs.get('status')['windows'].get('frontRight', '')
        return True if response != "" else False

    @property
    def window_closed_left_back(self) -> bool:
        response = self.attrs.get('status')['windows'].get('rearLeft', '')
        if response == 'closed':
            return True
        else:
            return False

    @property
    def is_window_closed_left_back_supported(self) -> bool:
        """Return true if window state is supported"""
        response = ""
        if self.attrs.get('status', False):
            if 'windows' in self.attrs.get('status'):
                response = self.attrs.get('status')['windows'].get('rearLeft', '')
        return True if response != "" else False

    @property
    def window_closed_right_back(self) -> bool:
        response = self.attrs.get('status')['windows'].get('rearRight', '')
        if response == 'closed':
            return True
        else:
            return False

    @property
    def is_window_closed_right_back_supported(self) -> bool:
        """Return true if window state is supported"""
        response = ""
        if self.attrs.get('status', False):
            if 'windows' in self.attrs.get('status'):
                response = self.attrs.get('status')['windows'].get('rearRight', '')
        return True if response != "" else False

    @property
    def sunroof_closed(self) -> bool:
        # Due to missing test objects, it is yet unclear, if 'sunroof' is direct subentry of 'status' or a subentry of 'windows'. So both are checked.
        response = ""
        if 'sunRoof' in self.attrs.get('status'):
            response = self.attrs.get('status').get('sunRoof', '')
        #else:
        #    response = self.attrs.get('status')['windows'].get('sunRoof', '')
        if response == 'closed':
            return True
        else:
            return False

    @property
    def is_sunroof_closed_supported(self) -> bool:
        """Return true if sunroof state is supported"""
        # Due to missing test objects, it is yet unclear, if 'sunroof' is direct subentry of 'status' or a subentry of 'windows'. So both are checked.
        response = ""
        if self.attrs.get('status', False):
            if 'sunRoof' in self.attrs.get('status'):
                response = self.attrs.get('status').get('sunRoof', '')
            #elif 'sunRoof' in self.attrs.get('status')['windows']:
            #    response = self.attrs.get('status')['windows'].get('sunRoof', '')
        return True if response != '' else False

    # Locks
    @property
    def door_locked(self) -> bool:
        # LEFT FRONT
        response = self.attrs.get('status')['doors']['frontLeft'].get('locked', 'false')
        if response != 'true':
            return False
        # LEFT REAR
        response = self.attrs.get('status')['doors']['rearLeft'].get('locked', 'false')
        if response != 'true':
            return False
        # RIGHT FRONT
        response = self.attrs.get('status')['doors']['frontRight'].get('locked', 'false')
        if response != 'true':
            return False
        # RIGHT REAR
        response = self.attrs.get('status')['doors']['rearRight'].get('locked', 'false')
        if response != 'true':
            return False

        return True

    @property
    def is_door_locked_supported(self) -> bool:
        response = 0
        if self.attrs.get('status', False):
            if 'doors' in self.attrs.get('status'):
                response = self.attrs.get('status')['doors'].get('frontLeft', {}).get('locked', 0)
        return True if response != 0 else False

    @property
    def trunk_locked(self):
        locked=self.attrs.get('status')['trunk'].get('locked', 'false')
        return True if locked == 'true' else False

    @property
    def is_trunk_locked_supported(self) -> bool:
        if self.attrs.get('status', False):
            if 'trunk' in self.attrs.get('status'):
                if 'locked' in self.attrs.get('status').get('trunk'):
                    return True
        return False

    # Doors, hood and trunk
    @property
    def hood_closed(self):
        """Return true if hood is closed"""
        open = self.attrs.get('status')['hood'].get('open', 'false')
        return True if open == 'false' else False

    @property
    def is_hood_closed_supported(self) -> bool:
        """Return true if hood state is supported"""
        response = 0
        if self.attrs.get('status', False):
            if 'hood' in self.attrs.get('status', {}):
                response = self.attrs.get('status')['hood'].get('open', 0)
        return True if response != 0 else False

    @property
    def door_closed_left_front(self):
        open=self.attrs.get('status')['doors']['frontLeft'].get('open', 'false')
        return True if open == 'false' else False

    @property
    def is_door_closed_left_front_supported(self) -> bool:
        """Return true if window state is supported"""
        if self.attrs.get('status', False):
            if 'doors' in self.attrs.get('status'):
                if 'frontLeft' in self.attrs.get('status').get('doors', {}):
                    return True
        return False

    @property
    def door_closed_right_front(self):
        open=self.attrs.get('status')['doors']['frontRight'].get('open', 'false')
        return True if open == 'false' else False

    @property
    def is_door_closed_right_front_supported(self) -> bool:
        """Return true if window state is supported"""
        if self.attrs.get('status', False):
            if 'doors' in self.attrs.get('status'):
                if 'frontRight' in self.attrs.get('status').get('doors', {}):
                    return True
        return False

    @property
    def door_closed_left_back(self):
        open=self.attrs.get('status')['doors']['rearLeft'].get('open', 'false')
        return True if open == 'false' else False

    @property
    def is_door_closed_left_back_supported(self) -> bool:
        if self.attrs.get('status', False):
            if 'doors' in self.attrs.get('status'):
                if 'rearLeft' in self.attrs.get('status').get('doors', {}):
                    return True
        return False

    @property
    def door_closed_right_back(self):
        open=self.attrs.get('status')['doors']['rearRight'].get('open', 'false')
        return True if open == 'false' else False

    @property
    def is_door_closed_right_back_supported(self) -> bool:
        """Return true if window state is supported"""
        if self.attrs.get('status', False):
            if 'doors' in self.attrs.get('status'):
                if 'rearRight' in self.attrs.get('status').get('doors', {}):
                    return True
        return False

    @property
    def trunk_closed(self):
        open = self.attrs.get('status')['trunk'].get('open', 'false')
        return True if open == 'false' else False

    @property
    def is_trunk_closed_supported(self) -> bool:
        """Return true if window state is supported"""
        response = 0
        if self.attrs.get('status', False):
            if 'trunk' in self.attrs.get('status', {}):
                response = self.attrs.get('status')['trunk'].get('open', 0)
        return True if response != 0 else False

    # Departure timers
    @property
    def departure1(self):
        """Return timer status and attributes."""
        if self.attrs.get('departureTimers', False):
            try:
                data = {}
                timerdata = self.attrs.get('departureTimers', {}).get('timers', [])
                timer = timerdata[0]
                timer.pop('timestamp', None)
                timer.pop('timerID', None)
                timer.pop('profileID', None)
                data.update(timer)
                return data
            except:
                pass
        elif self.attrs.get('timers', False):
            try:
                response = self.attrs.get('timers', [])
                if len(self.attrs.get('timers', [])) >= 1:
                    timer = response[0]
                    timer.pop('id', None)
                else:
                    timer = {}
                return timer
            except:
                pass
        return None

    @property
    def is_departure1_supported(self) -> bool:
        """Return true if timer 1 is supported."""
        if len(self.attrs.get('departureTimers', {}).get('timers', [])) >= 1:
            return True
        elif len(self.attrs.get('timers', [])) >= 1:
            return True
        return False

    @property
    def departure2(self):
        """Return timer status and attributes."""
        if self.attrs.get('departureTimers', False):
            try:
                data = {}
                timerdata = self.attrs.get('departureTimers', {}).get('timers', [])
                timer = timerdata[1]
                timer.pop('timestamp', None)
                timer.pop('timerID', None)
                timer.pop('profileID', None)
                data.update(timer)
                return data
            except:
                pass
        elif self.attrs.get('timers', False):
            try:
                response = self.attrs.get('timers', [])
                if len(self.attrs.get('timers', [])) >= 2:
                    timer = response[1]
                    timer.pop('id', None)
                else:
                    timer = {}
                return timer
            except:
                pass
        return None

    @property
    def is_departure2_supported(self) -> bool:
        """Return true if timer 2 is supported."""
        if len(self.attrs.get('departureTimers', {}).get('timers', [])) >= 2:
            return True
        elif len(self.attrs.get('timers', [])) >= 2:
            return True
        return False

    @property
    def departure3(self):
        """Return timer status and attributes."""
        if self.attrs.get('departureTimers', False):
            try:
                data = {}
                timerdata = self.attrs.get('departureTimers', {}).get('timers', [])
                timer = timerdata[2]
                timer.pop('timestamp', None)
                timer.pop('timerID', None)
                timer.pop('profileID', None)
                data.update(timer)
                return data
            except:
                pass
        elif self.attrs.get('timers', False):
            try:
                response = self.attrs.get('timers', [])
                if len(self.attrs.get('timers', [])) >= 3:
                    timer = response[2]
                    timer.pop('id', None)
                else:
                    timer = {}
                return timer
            except:
                pass
        return None

    @property
    def is_departure3_supported(self) -> bool:
        """Return true if timer 3 is supported."""
        if len(self.attrs.get('departureTimers', {}).get('timers', [])) >= 3:
            return True
        elif len(self.attrs.get('timers', [])) >= 3:
            return True
        return False

    # Departure profiles
    @property
    def departure_profile1(self):
        """Return profile status and attributes."""
        if self.attrs.get('departureProfiles', False):
            try:
                data = {}
                timerdata = self.attrs.get('departureProfiles', {}).get('timers', [])
                timer = timerdata[0]
                #timer.pop('timestamp', None)
                #timer.pop('timerID', None)
                #timer.pop('profileID', None)
                data.update(timer)
                return data
            except:
                pass
        return None

    @property
    def is_departure_profile1_supported(self) -> bool:
        """Return true if profile 1 is supported."""
        if len(self.attrs.get('departureProfiles', {}).get('timers', [])) >= 1:
            return True
        return False

    @property
    def departure_profile2(self):
        """Return profile status and attributes."""
        if self.attrs.get('departureProfiles', False):
            try:
                data = {}
                timerdata = self.attrs.get('departureProfiles', {}).get('timers', [])
                timer = timerdata[1]
                #timer.pop('timestamp', None)
                #timer.pop('timerID', None)
                #timer.pop('profileID', None)
                data.update(timer)
                return data
            except:
                pass
        return None

    @property
    def is_departure_profile2_supported(self) -> bool:
        """Return true if profile 2 is supported."""
        if len(self.attrs.get('departureProfiles', {}).get('timers', [])) >= 2:
            return True
        return False

    @property
    def departure_profile3(self):
        """Return profile status and attributes."""
        if self.attrs.get('departureProfiles', False):
            try:
                data = {}
                timerdata = self.attrs.get('departureProfiles', {}).get('timers', [])
                timer = timerdata[2]
                #timer.pop('timestamp', None)
                #timer.pop('timerID', None)
                #timer.pop('profileID', None)
                data.update(timer)
                return data
            except:
                pass
        return None

    @property
    def is_departure_profile3_supported(self) -> bool:
        """Return true if profile 3 is supported."""
        if len(self.attrs.get('departureProfiles', {}).get('timers', [])) >= 3:
            return True
        return False

    # Trip data
    @property
    def trip_last_entry(self):
        return self.attrs.get('tripstatistics', {}).get('short', [{},{}])[-1]

    @property
    def trip_last_average_speed(self):
        return self.trip_last_entry.get('averageSpeedKmph')

    @property
    def is_trip_last_average_speed_supported(self) -> bool:
        response = self.trip_last_entry
        if response and type(response.get('averageSpeedKmph', None)) in (float, int):
            return True
        else:
            return False

    @property
    def trip_last_average_electric_consumption(self):
        return self.trip_last_entry.get('averageElectricConsumption')

    @property
    def is_trip_last_average_electric_consumption_supported(self) -> bool:
        response = self.trip_last_entry
        if response and type(response.get('averageElectricConsumption', None)) in (float, int):
            return True
        else:
            return False

    @property
    def trip_last_average_fuel_consumption(self):
        return self.trip_last_entry.get('averageFuelConsumption')

    @property
    def is_trip_last_average_fuel_consumption_supported(self) -> bool:
        response = self.trip_last_entry
        if response and type(response.get('averageFuelConsumption', None)) in (float, int):
            return True
        else:
            return False

    @property
    def trip_last_average_auxillary_consumption(self):
        return self.trip_last_entry.get('averageAuxConsumption')

    @property
    def is_trip_last_average_auxillary_consumption_supported(self) -> bool:
        response = self.trip_last_entry
        if response and type(response.get('averageAuxConsumption', None)) in (float, int):
            return True
        else:
            return False

    @property
    def trip_last_average_aux_consumer_consumption(self):
        value = self.trip_last_entry.get('averageAuxConsumerConsumption')
        return value

    @property
    def is_trip_last_average_aux_consumer_consumption_supported(self) -> bool:
        response = self.trip_last_entry
        if response and type(response.get('averageAuxConsumerConsumption', None)) in (float, int):
            return True
        else:
            return False

    @property
    def trip_last_duration(self):
        return self.trip_last_entry.get('travelTime')

    @property
    def is_trip_last_duration_supported(self) -> bool:
        response = self.trip_last_entry
        if response and type(response.get('travelTime', None)) in (float, int):
            return True
        else:
            return False

    @property
    def trip_last_length(self):
        return self.trip_last_entry.get('mileageKm')

    @property
    def is_trip_last_length_supported(self) -> bool:
        response = self.trip_last_entry
        if response and type(response.get('mileageKm', None)) in (float, int):
            return True
        else:
            return False

    @property
    def trip_last_recuperation(self):
        #Not implemented
        return self.trip_last_entry.get('recuperation')

    @property
    def is_trip_last_recuperation_supported(self) -> bool:
        #Not implemented
        response = self.trip_last_entry
        if response and type(response.get('recuperation', None)) in (float, int):
            return True
        else:
            return False

    @property
    def trip_last_average_recuperation(self):
        #Not implemented
        value = self.trip_last_entry.get('averageRecuperation')
        return value

    @property
    def is_trip_last_average_recuperation_supported(self) -> bool:
        #Not implemented
        response = self.trip_last_entry
        if response and type(response.get('averageRecuperation', None)) in (float, int):
            return True
        else:
            return False

    @property
    def trip_last_total_electric_consumption(self):
        #Not implemented
        return self.trip_last_entry.get('totalElectricConsumption')

    @property
    def is_trip_last_total_electric_consumption_supported(self) -> bool:
        #Not implemented
        response = self.trip_last_entry
        if response and type(response.get('totalElectricConsumption', None)) in (float, int):
            return True
        else:
            return False

    @property
    def trip_last_cycle_entry(self):
        return self.attrs.get('tripstatistics', {}).get('cyclic', [{},{}])[-1]

    @property
    def trip_last_cycle_average_speed(self):
        return self.trip_last_cycle_entry.get('averageSpeedKmph')

    @property
    def is_trip_last_cycle_average_speed_supported(self) -> bool:
        response = self.trip_last_cycle_entry
        if response and type(response.get('averageSpeedKmph', None)) in (float, int):
            return True
        else:
            return False

    @property
    def trip_last_cycle_average_electric_consumption(self):
        return self.trip_last_cycle_entry.get('averageElectricConsumption')

    @property
    def is_trip_last_cycle_average_electric_consumption_supported(self) -> bool:
        response = self.trip_last_cycle_entry
        if response and type(response.get('averageElectricConsumption', None)) in (float, int):
            return True
        else:
            return False

    @property
    def trip_last_cycle_average_fuel_consumption(self):
        return self.trip_last_cycle_entry.get('averageFuelConsumption')

    @property
    def is_trip_last_cycle_average_fuel_consumption_supported(self) -> bool:
        response = self.trip_last_cycle_entry
        if response and type(response.get('averageFuelConsumption', None)) in (float, int):
            return True
        else:
            return False

    @property
    def trip_last_cycle_average_auxillary_consumption(self):
        return self.trip_last_cycle_entry.get('averageAuxConsumption')

    @property
    def is_trip_last_cycle_average_auxillary_consumption_supported(self) -> bool:
        response = self.trip_last_cycle_entry
        if response and type(response.get('averageAuxConsumption', None)) in (float, int):
            return True
        else:
            return False

    @property
    def trip_last_cycle_average_aux_consumer_consumption(self):
        value = self.trip_last_cycle_entry.get('averageAuxConsumerConsumption')
        return value

    @property
    def is_trip_last_cycle_average_aux_consumer_consumption_supported(self) -> bool:
        response = self.trip_last_cycle_entry
        if response and type(response.get('averageAuxConsumerConsumption', None)) in (float, int):
            return True
        else:
            return False

    @property
    def trip_last_cycle_duration(self):
        return self.trip_last_cycle_entry.get('travelTime')

    @property
    def is_trip_last_cycle_duration_supported(self) -> bool:
        response = self.trip_last_cycle_entry
        if response and type(response.get('travelTime', None)) in (float, int):
            return True
        else:
            return False

    @property
    def trip_last_cycle_length(self) -> int:
        return self.trip_last_cycle_entry.get('mileageKm')

    @property
    def is_trip_last_cycle_length_supported(self) -> bool:
        response = self.trip_last_cycle_entry
        if response and type(response.get('mileageKm', None)) in (float, int):
            return True
        else:
            return False

    @property
    def trip_last_cycle_recuperation(self) -> float:
        #Not implemented
        return self.trip_last_cycle_entry.get('recuperation')

    @property
    def is_trip_last_cycle_recuperation_supported(self) -> bool:
        #Not implemented
        response = self.trip_last_cycle_entry
        if response and type(response.get('recuperation', None)) in (float, int):
            return True
        else:
            return False

    @property
    def trip_last_cycle_average_recuperation(self) -> float:
        #Not implemented
        value = self.trip_last_cycle_entry.get('averageRecuperation')
        return value

    @property
    def is_trip_last_cycle_average_recuperation_supported(self) -> bool:
        #Not implemented
        response = self.trip_last_cycle_entry
        if response and type(response.get('averageRecuperation', None)) in (float, int):
            return True
        else:
            return False

    @property
    def trip_last_cycle_total_electric_consumption(self) -> float:
        #Not implemented
        return self.trip_last_cycle_entry.get('totalElectricConsumption')

    @property
    def is_trip_last_cycle_total_electric_consumption_supported(self) -> bool:
        #Not implemented
        response = self.trip_last_cycle_entry
        if response and type(response.get('totalElectricConsumption', None)) in (float, int):
            return True
        else:
            return False

    # Area alarm
    @property
    def area_alarm(self) -> bool:
        """Return True, if attribute areaAlarm is not {}"""
        alarmPresent = self.attrs.get('areaAlarm', {})
        if alarmPresent !={}:
            # Delete an area alarm if it is older than 900 seconds
            alarmTimestamp = self.attrs.get('areaAlarm', {}).get('timestamp', 0)
            if alarmTimestamp < datetime.now(tz=None) - timedelta(seconds= 900):
                self.attrs.pop("areaAlarm")
                alarmPresent = {}
        return False if alarmPresent == {} else True

    @property
    def is_area_alarm_supported(self) -> bool:
        """Return True, if vehicle supports area alarm (always True at the moment)"""
        # Always True at the moment. Have to check, if the geofence capability is a necessary condition
        return True

    #  Status of set data requests
    @property
    def refresh_action_status(self):
        """Return latest status of data refresh request."""
        return self._requests.get('refresh', {}).get('status', 'None')

    @property
    def refresh_action_timestamp(self) -> str:
        """Return timestamp of latest data refresh request."""
        timestamp = self._requests.get('refresh', {}).get('timestamp', DATEZERO)
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def charger_action_status(self):
        """Return latest status of charger request."""
        return self._requests.get('batterycharge', {}).get('status', 'None')

    @property
    def charger_action_timestamp(self) -> str:
        """Return timestamp of latest charger request."""
        timestamp = self._requests.get('charger', {}).get('timestamp', DATEZERO)
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def climater_action_status(self):
        """Return latest status of climater request."""
        return self._requests.get('climatisation', {}).get('status', 'None')

    @property
    def climater_action_timestamp(self) -> str:
        """Return timestamp of latest climater request."""
        timestamp = self._requests.get('climatisation', {}).get('timestamp', DATEZERO)
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def pheater_action_status(self):
        """Return latest status of parking heater request."""
        return self._requests.get('preheater', {}).get('status', 'None')

    @property
    def pheater_action_timestamp(self) -> str:
        """Return timestamp of latest parking heater request."""
        timestamp = self._requests.get('preheater', {}).get('timestamp', DATEZERO)
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def honkandflash_action_status(self):
        """Return latest status of honk and flash action request."""
        return self._requests.get('honkandflash', {}).get('status', 'None')

    @property
    def honkandflash_action_timestamp(self) -> str:
        """Return timestamp of latest honk and flash request."""
        timestamp = self._requests.get('honkandflash', {}).get('timestamp', DATEZERO)
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def lock_action_status(self):
        """Return latest status of lock action request."""
        return self._requests.get('lock', {}).get('status', 'None')

    @property
    def lock_action_timestamp(self) -> str:
        """Return timestamp of latest lock action request."""
        timestamp = self._requests.get('lock', {}).get('timestamp', DATEZERO)
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def timer_action_status(self):
        """Return latest status of departure timer request."""
        return self._requests.get('departuretimer', {}).get('status', 'None')

    @property
    def timer_action_timestamp(self) -> str:
        """Return timestamp of latest departure timer request."""
        timestamp = self._requests.get('departuretimer', {}).get('timestamp', DATEZERO)
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")

    @property
    def refresh_data(self) -> bool:
        """Get state of data refresh"""
        #if self._requests.get('refresh', {}).get('id', False):
        #    timestamp = self._requests.get('refresh', {}).get('timestamp', DATEZERO)
        #    expired = datetime.now() - timedelta(minutes=2)
        #    if expired < timestamp:
        #        return True
        #State is always false
        return False

    @property
    def is_refresh_data_supported(self) -> bool:
        """Data refresh is supported."""
        if self._connectivities.get('mode', '') == 'online':
            return True
        else:
            return False

    @property
    def update_data(self) -> bool:
        """Get state of data update"""
        return False

    @property
    def is_update_data_supported(self) -> bool:
        """Data update is supported."""
        return True

    # Honk and flash
    @property
    def request_honkandflash(self) -> bool:
        """State is always False"""
        return False

    @property
    def is_request_honkandflash_supported(self) -> bool:
        """Honk and flash is supported if service is enabled."""
        if self._relevantCapabilties.get('honkAndFlash', {}).get('active', False):
            return True
        else:
            return False

    @property
    def request_flash(self) -> bool:
        """State is always False"""
        return False

    @property
    def is_request_flash_supported(self) -> bool:
        """Honk and flash is supported if service is enabled."""
        if self._relevantCapabilties.get('honkAndFlash', {}).get('active', False):
            return True
        else:
            return False

    # Requests data
    @property
    def request_in_progress(self) -> bool:
        """Request in progress is always supported."""
        try:
            for section in self._requests:
                if self._requests[section].get('id', False):
                    return True
        except:
            pass
        return False

    @property
    def is_request_in_progress_supported(self) -> bool:
        """Request in progress is always supported."""
        return False

    @property
    def request_results(self) -> dict:
        """Get last request result."""
        data = {
            'latest': self._requests.get('latest', 'N/A'),
            'state': self._requests.get('state', 'N/A'),
        }
        for section in self._requests:
            if section in ['departuretimer', 'departureprofiles', 'batterycharge', 'climatisation', 'refresh', 'lock', 'preheater']:
                timestamp = self._requests.get(section, {}).get('timestamp', DATEZERO)
                data[section] = self._requests[section].get('status', 'N/A')
                data[section+'_timestamp'] = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        return data

    @property
    def is_request_results_supported(self) -> bool:
        """Request results is supported if in progress is supported."""
        return False # deactivated because it provides no usefull information
        #return self.is_request_in_progress_supported

    @property
    def requests_remaining(self) -> int:
        """Get remaining requests before throttled."""
        if self.attrs.get('rate_limit_remaining', False):
            self.requests_remaining = self.attrs.get('rate_limit_remaining')
            self.attrs.pop('rate_limit_remaining')
        return self._requests['remaining']

    @requests_remaining.setter
    def requests_remaining(self, value) -> None:
        self._requests['remaining'] = value

    @property
    def is_requests_remaining_supported(self) -> bool:
        return False # deactivated because it provides no usefull information
        #if self.is_request_in_progress_supported:
        #    return True if self._requests.get('remaining', False) else False

    #### Helper functions ####
    def __str__(self) -> str:
        return self.vin

    @property
    def json(self) -> str:
        def serialize(obj):
            if isinstance(obj, datetime):
                return obj.strftime("%Y-%m-%dT%H:%M:%SZ")

        return to_json(
            OrderedDict(sorted(self.attrs.items())),
            indent=4,
            default=serialize
        )


    async def stopFirebase(self) -> int:
        # Check if firebase is activated
        if self.firebaseStatus not in (FIREBASE_STATUS_ACTIVATED, FIREBASE_STATUS_ACTIVATION_STOPPED):
            _LOGGER.info(f'No need to stop firebase. Firebase status={self.firebaseStatus}')
            return self.firebaseStatus
        
        if self.firebase == None:
            _LOGGER.error(f'Internal error: Firebase status={self.firebaseStatus} but firebase variable not set. Setting firebase status back to not initialised.')
            self.firebaseStatus = FIREBASE_STATUS_NOT_INITIALISED
            return self.firebaseStatus

        success = await self.firebase.firebaseStop()
        if not success:
            _LOGGER.warning('Stopping of firebase messaging failed.')
            return self.firebaseStatus
        
        #await asyncio.sleep(5) 
        self.firebaseStatus = FIREBASE_STATUS_NOT_INITIALISED
        _LOGGER.info('Stopping of firebase messaging was successful.')
        return self.firebaseStatus

    async def initialiseFirebase(self, firebaseCredentialsFileName='', updateCallback=None) -> int:
        # Check if firebase shall be used
        if firebaseCredentialsFileName == None:
            _LOGGER.debug('No use of firebase wanted.')
            self.firebaseStatus = FIREBASE_STATUS_NOT_WANTED
            return self.firebaseStatus
        self._firebaseCredentialsFileName = firebaseCredentialsFileName

        # Check if firebase not already initialised
        if self.firebaseStatus!= FIREBASE_STATUS_NOT_INITIALISED:
            _LOGGER.debug(f'No need to initialise firebase anymore. Firebase status={self.firebaseStatus}')
            return self.firebaseStatus
        
        # Read the firebase credentials file and check if an existing subscription has to be deleted
        loop = asyncio.get_running_loop()
        credentials = await loop.run_in_executor(None, readFCMCredsFile, firebaseCredentialsFileName)
        subscribedVin = credentials.get('subscription',{}).get('vin','')
        subscribedUserId = credentials.get('subscription',{}).get('userId','')
        subscribedBrand = credentials.get('subscription',{}).get('brand','')
        if subscribedVin != '' and subscribedUserId != '':
            if subscribedVin != self.vin or subscribedUserId != self._connection._user_id or subscribedBrand != self._connection._session_auth_brand:
                _LOGGER.debug(self._connection.anonymise(f'Change of vin, userId or brand. Deleting subscription for vin={subscribedVin} and userId={subscribedUserId}.'))
                result = await self._connection.deleteSubscription(credentials)

        # Start firebase
        if self.firebase == None:
            self.firebase = Firebase()
        success = await self.firebase.firebaseStart(self.onNotification, firebaseCredentialsFileName, brand=self._connection._session_auth_brand)
        if not success:
            self.firebaseStatus = FIREBASE_STATUS_ACTIVATION_FAILED
            _LOGGER.warning('Activation of firebase messaging failed.')
            return self.firebaseStatus
        
        self.updateCallback = updateCallback
        # Read possibly new credentials and subscribe vin and userId for push notifications
        loop = asyncio.get_running_loop()
        credentials = await loop.run_in_executor(None, readFCMCredsFile, firebaseCredentialsFileName)
        result = await self._connection.subscribe(self.vin, credentials)
        _LOGGER.debug(f'Result of subscription={result}.')
        credentials['subscription']= {
            'vin' : self.vin,
            'userId' : self._connection._user_id,
            'brand' : self._connection._session_auth_brand,
            'id' : result.get('id', ''),
        }
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, writeFCMCredsFile, credentials, firebaseCredentialsFileName)

        await asyncio.sleep(5) # Wait to ignore the first notifications 
        self.firebaseStatus = FIREBASE_STATUS_ACTIVATED
        _LOGGER.info('Activation of firebase messaging was successful.')
        return self.firebaseStatus



    async def onNotification(self, obj: Any, notification: str, data_message: Any) -> None:
        # Do something with the notification
        _LOGGER.debug(f'Received push notification: notification id={notification}, type={obj.get('data',{}).get('type','')}, requestId={obj.get('data',{}).get('requestId','[None]')}')
        _LOGGER.debug(f'   data_message={data_message}, payload={obj.get('data',{}).get('payload','[None]')}')

        if self.firebaseStatus != FIREBASE_STATUS_ACTIVATED:
            if self.firebaseStatus != FIREBASE_STATUS_ACTIVATION_STOPPED:
                _LOGGER.info(f'While firebase is not fully activated, received notifications are just acknowledged.')
                # As long as the firebase status is not set to activated, ignore the notifications
                return
            else:
                # It seems that the firebase connection still works although fcmpushclient.is_started() returned False some time ago
                _LOGGER.info(f'Firebase status={self.firebaseStatus}, but PyCupra still receives push notifications.')
                self.firebaseStatus = FIREBASE_STATUS_ACTIVATED
                _LOGGER.info(f'Set firebase status back to {self.firebaseStatus}.')

 
        type = obj.get('data',{}).get('type','')
        requestId = obj.get('data',{}).get('requestId','')
        payload = obj.get('data',{}).get('payload','')
        openRequest = -1
        if requestId != '':
            _LOGGER.info(f'Received notification of type \'{type}\', request id={requestId} ')
        else:
            _LOGGER.info(f'Received notification of type \'{type}\' ')

        if notification == self._firebaseLastMessageId:
            _LOGGER.info(f'Received notification {notification} again. Just acknoledging it, nothing to do.')
            return 

        self._firebaseLastMessageId = notification # save the id of the last notification
        if type in ('vehicle-access-locked-successful', 'vehicle-access-unlocked-successful'): # vehicle was locked/unlocked
            if self._requests.get('lock', {}).get('id', None):
                openRequest= self._requests.get('lock', {}).get('id', None)
                if openRequest == requestId:
                    _LOGGER.debug(f'The notification closes an open request initiated by PyCupra.')
                    self._requests.get('lock', {}).pop('id')
            if (self._last_get_statusreport < datetime.now(tz=None) - timedelta(seconds= 10)) or openRequest == requestId:
                # Update the status report only if the last one is older than timedelta or if the notification belongs to an open request initiated by PyCupra
                #await self.get_statusreport() # Call not needed because it's part of updateCallback(2)
                if self.updateCallback:
                    await self.updateCallback(2)
            else:
                _LOGGER.debug(f'It is now {datetime.now(tz=None)}. Last update of status report was at {self._last_get_statusreport}. So no need to update.')
                # Wait 2 seconds
                await asyncio.sleep(2)
        elif type ==  'departure-times-updated': 
            if self._requests.get('departuretimer', {}).get('id', None):
                openRequest= self._requests.get('departuretimer', {}).get('id', None)
                if openRequest == requestId:
                    _LOGGER.debug(f'The notification closes an open request initiated by PyCupra.')
                    self._requests.get('departuretimer', {}).pop('id')
            if (self._last_get_departure_timers < datetime.now(tz=None) - timedelta(seconds= 30)) or openRequest == requestId:
                # Update the departure timers only if the last one is older than timedelta or if the notification belongs to an open request initiated by PyCupra
                await self.get_departure_timers()
                if self.updateCallback:
                    await self.updateCallback(2)
            else:
                _LOGGER.debug(f'It is now {datetime.now(tz=None)}. Last update of departure timers was at {self._last_get_departure_timers}. So no need to update.')
                # Wait 5 seconds
                await asyncio.sleep(5)
        elif type ==  'departure-profiles-updated': # !!! Is this the right type?
            if self._requests.get('departureprofile', {}).get('id', None):
                openRequest= self._requests.get('departureprofile', {}).get('id', None)
                if openRequest == requestId:
                    _LOGGER.debug(f'The notification closes an open request initiated by PyCupra.')
                self._requests.get('departureprofile', {}).pop('id')
            if (self._last_get_departure_profiles < datetime.now(tz=None) - timedelta(seconds= 30)) or openRequest == requestId:
                # Update the departure profiles only if the last one is older than timedelta or if the notification belongs to an open request initiated by PyCupra
                await self.get_departure_profiles()
                if self.updateCallback:
                    await self.updateCallback(2)
            else:
                _LOGGER.debug(f'It is now {datetime.now(tz=None)}. Last update of departure profiles was at {self._last_get_departure_profiles}. So no need to update.')
                # Wait 5 seconds
                await asyncio.sleep(5)
        elif type in ('charging-status-changed', 'charging-started', 'charging-stopped', 'charging-settings-updated'):
            if self._requests.get('batterycharge', {}).get('id', None):
                openRequest= self._requests.get('batterycharge', {}).get('id', None)
                if openRequest == requestId:
                    _LOGGER.debug(f'The notification closes an open request initiated by PyCupra.')
                    self._requests.get('batterycharge', {}).pop('id')
            if (self._last_get_charger < datetime.now(tz=None) - timedelta(seconds= 10)) or openRequest == requestId:
                # Update the charging data only if the last one is older than timedelta or if the notification belongs to an open request initiated by PyCupra
                await self.get_charger()
                if self.updateCallback:
                    await self.updateCallback(2)
            else:
                _LOGGER.debug(f'It is now {datetime.now(tz=None)}. Last get_charger was at {self._last_get_charger}. So no need to update.')
                # Wait 5 seconds
                await asyncio.sleep(5)
        elif type in ('climatisation-status-changed','climatisation-started', 'climatisation-stopped', 'climatisation-settings-updated', 'climatisation-error-fail'):
            if self._requests.get('climatisation', {}).get('id', None):
                openRequest= self._requests.get('climatisation', {}).get('id', None)
                if openRequest == requestId:
                    _LOGGER.debug(f'The notification closes an open request initiated by PyCupra.')
                    self._requests.get('climatisation', {}).pop('id')
            if (self._last_get_climater < datetime.now(tz=None) - timedelta(seconds= 10)) or openRequest == requestId:
                # Update the climatisation data only if the last one is older than timedelta or if the notification belongs to an open request initiated by PyCupra
                await self.get_climater()
                if self.updateCallback:
                    await self.updateCallback(2)
            else:
                _LOGGER.debug(f'It is now {datetime.now(tz=None)}. Last get_climater was at {self._last_get_climater}. So no need to update.')
                # Wait 5 seconds
                await asyncio.sleep(5)
        elif type in ('vehicle-area-alarm-vehicle-exits-zone-triggered', 'vehicle-area-alarm-vehicle-enters-zone-triggered'):
            #if self._last_get_position < datetime.now(tz=None) - timedelta(seconds= 30):
            #    # Update position data only if the last one is older than timedelta
            #    await self.get_position()
            #else:
            #    _LOGGER.debug(f'It is now {datetime.now(tz=None)}. Last get_position was at {self._last_get_position}. So no need to update.')
            if payload != '':
                payloadDict = json.loads(payload) # Convert json string to dict
                #_LOGGER.debug(f'payloadDict is dict: {isinstance(payloadDict, dict)}')
                zones = payloadDict.get('description',{}).get('values',[])
            else:
                _LOGGER.warning(f'Missing information about areas. Payload ={payload}')
                zones = []
            areaAlarm = {'areaAlarm' : {
                'type': 'vehicle-exits-zone' if type=='vehicle-area-alarm-vehicle-exits-zone-triggered' else 'vehicle-enters-zone',
                'timestamp': datetime.now(tz=None),
                'zones': zones
                }
            }
            self._states.update(areaAlarm)
            if self.updateCallback:
                await self.updateCallback(2)
        elif type in ('vehicle-wake-up-succeeded', 'vehicle-wakeup-succeeded'):
            if self._requests.get('refresh', {}).get('id', None):
                openRequest= self._requests.get('refresh', {}).get('id', None)
                if openRequest == requestId:
                    _LOGGER.debug(f'The notification closes an open request initiated by PyCupra.')
                    self._requests.get('refresh', {}).pop('id')
            if (self._last_full_update < datetime.now(tz=None) - timedelta(seconds= 30)) or openRequest == requestId:
                # Do full update only if the last one is older than timedelta or if the notification belongs to an open request initiated by PyCupra
                if self.updateCallback:
                    await self.updateCallback(1)
            else:
                _LOGGER.debug(f'It is now {datetime.now(tz=None)}. Last full update was at {self._last_full_update}. So no need to update.')
                # Wait 5 seconds
                await asyncio.sleep(2)
        elif type == 'vehicle-honk-and-flash-started':
            if self._requests.get('refresh', {}).get('id', None):
                openRequest= self._requests.get('refresh', {}).get('id', None)
                if openRequest == requestId:
                    _LOGGER.debug(f'The notification closes an open request initiated by PyCupra.')
                    self._requests.get('refresh', {}).pop('id')
            # Nothing else to do
        elif type in ('vehicle-area-alert-added', 'vehicle-area-alert-updated'):
            _LOGGER.info(f'   Intentionally ignoring a notification of type \'{type}\')')
        else:
            _LOGGER.warning(f'   Don\'t know what to do with a notification of type \'{type}\'. Please open an issue.)')

