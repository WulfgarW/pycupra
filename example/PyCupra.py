#!/usr/bin/env python3
""" Sample program to show the features of pycupra"""
import asyncio
import logging
import inspect
import sys
import os
import json
import pandas as pd
from aiohttp import ClientSession
from datetime import datetime

currentframe = inspect.currentframe()
if currentframe != None:
    currentdir = os.path.dirname(os.path.abspath(inspect.getfile(currentframe)))
    parentdir = os.path.dirname(currentdir)
    sys.path.insert(0, parentdir)

try:
    from pycupra import Connection
except ModuleNotFoundError as e:
    print(f"Unable to import library: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)
BRAND = 'cupra' # or 'seat' (Change it to 'seat' if you want to connect to the My Seat portal)

PRINTRESPONSE = True
INTERVAL = 5
TOKEN_FILE_NAME_AND_PATH='./pycupra_token.json'
CREDENTIALS_FILE_NAME_AND_PATH='./pycupra_credentials.json'
FIREBASE_CREDENTIALS_FILE_NAME_AND_PATH='./pycupra_firebase_credentials.json'
ALL_ATTRIBUTES_FILE_NAME_AND_PATH='./pycupra_all_attributes.txt'


COMPONENTS = {
    'sensor': 'sensor',
    'binary_sensor': 'binary_sensor',
    'lock': 'lock',
    'device_tracker': 'device_tracker',
    'switch': 'switch',
}

RESOURCES = [
		"adblue_level",
        "area_alarm",
		"auxiliary_climatisation",
		"battery_level",
		"charge_max_ampere",
		"charger_action_status",
		"charging",
        "charge_max_ampere",
        "charge_rate",
        "charging_power",
        "charging_state",
		"charging_cable_connected",
		"charging_cable_locked",
		"charging_time_left",
		"climater_action_status",
		"climatisation_target_temperature",
		"climatisation_without_external_power",
		"combined_range",
		"combustion_range",
        "departure1",
        "departure2",
        "departure3",
        "departure_profile1",
        "departure_profile2",
        "departure_profile3",
		"distance",
		"door_closed_left_back",
		"door_closed_left_front",
		"door_closed_right_back",
		"door_closed_right_front",
		"door_locked",
		"electric_climatisation",
		"electric_range",
		"energy_flow",
		"external_power",
		"fuel_level",
		"hood_closed",
		"last_connected",
		"last_full_update",
		"lock_action_status",
		"oil_inspection",
		"oil_inspection_distance",
		"outside_temperature",
		"parking_light",
		"parking_time",
		"pheater_heating",
		"pheater_status",
		"pheater_ventilation",
		"position",
		"refresh_action_status",
		"refresh_data",
        "request_flash",
        "request_honkandflash",
		"request_in_progress",
		"request_results",
		"requests_remaining",
		"service_inspection",
		"service_inspection_distance",
        "slow_charge",
		"sunroof_closed",
        "target_soc",
		"trip_last_average_auxillary_consumption",
		"trip_last_average_electric_consumption",
		"trip_last_average_fuel_consumption",
		"trip_last_average_speed",
		"trip_last_duration",
		"trip_last_entry",
		"trip_last_length",
		"trip_last_recuperation",
		"trip_last_total_electric_consumption",
		"trip_last_cycle_average_auxillary_consumption",
		"trip_last_cycle_average_electric_consumption",
		"trip_last_cycle_average_fuel_consumption",
		"trip_last_cycle_average_speed",
		"trip_last_cycle_duration",
		"trip_last_cycle_entry",
		"trip_last_cycle_length",
		"trip_last_cycle_recuperation",
		"trip_last_cycle_total_electric_consumption",
		"trunk_closed",
		"trunk_locked",
		"vehicle_moving",
        "warnings",
		"window_closed_left_back",
		"window_closed_left_front",
		"window_closed_right_back",
		"window_closed_right_front",
		"window_heater",
		"windows_closed",
        "seat_heating"
]

def is_enabled(attr):
    """Return true if the user has enabled the resource."""
    return attr in RESOURCES

def readCredentialsFile():
    try:
        with open(CREDENTIALS_FILE_NAME_AND_PATH, "r") as f:
            credentialsString=f.read()
        credentials=json.loads(credentialsString)
        return credentials
    except:
        _LOGGER.info('readCredentialsFile not successful. Perhaps no credentials file present.')
        return None

def exportToCSV(vehicle, csvFileName, dataType='short'):
    df= pd.DataFrame(vehicle._states['tripstatistics'][dataType])
    _LOGGER.debug('Exporting trip data to csv')
    df.to_csv(csvFileName)
    return True

def exportAllAttributes(vehicle, exportFileName):
    try:
        with open(exportFileName, "w") as f:
            print(vehicle.attrs, file=f)
        f.close()
        return True
    except Exception as e:
        _LOGGER.warning(f'exportAllAttributes() not successful. Error: {e}')
    return False

async def demo_set_charger(vehicle, action="start"):
    print('########################################')
    print('#       Start/Stop charging            #')
    print('########################################')
    success= await vehicle.set_charger(action)                      # mode = "start", "stop", "on" or "off". 
    if success:
        print("   Request completed successfully.")
    else:
        print("   Request failed.")
    return success

async def demo_set_charger_current(vehicle, value="reduced"):
    print('########################################')
    print('#       Change charging current        #')
    print('########################################')
    success= await vehicle.set_charger_current(value)   
    if success:
        print("   Request completed successfully.")
    else:
        print("   Request failed.")
    return success

async def demo_set_charger_target_soc(vehicle, value=80):
    print('########################################')
    print('#     Change target state of charge    #')
    print('########################################')
    success= await vehicle.set_charger_target_soc(value)
    if success:
        print("   Request completed successfully.")
    else:
        print("   Request failed.")
    return success

async def demo_set_timer_schedule(vehicle):
    print('########################################')
    print('#      Change one timer schedule       #')
    print('########################################')
    success= await vehicle.set_timer_schedule(id = 3,                             # id = 1, 2, 3
        schedule = {                                               # Set the departure time, date and periodicity
            "enabled": True,                                       # Set the timer active or not, True or False, required
            "recurring": False,                                    # True or False for recurring, required
            "date": "2025-03-21",                                  # Date for departure, required if recurring=False
            "time": "12:34",                                       # Time for departure, required
            "days": "nyynnnn",                                     # Days (mon-sun) for recurring schedule (n=disable, y=enable), required if recurring=True
            "nightRateActive": True,                               # True or False Off-peak hours, optional
            "nightRateStart": "23:00",                             # Off-peak hours start (HH:mm), optional
            "nightRateEnd": "06:00",                               # Off-peak hours end (HH:mm), optional
            "operationCharging": True,                             # True or False for charging, optional
            "operationClimatisation": False,                       # True or False fro climatisation, optional
            "targetTemp": 22,                                      # Target temperature for climatisation, optional
            }
        )
    if success:
        print("   Request completed successfully.")
    else:
        print("   Request failed.")
    return success

async def demo_set_departure_profile_schedule(vehicle):
    print('########################################')
    print('#    Change one departure profile      #')
    print('########################################')
    success= await vehicle.set_departure_profile_schedule(id = 3,                             # id = 1, 2, 3
        schedule = {                                               # Set the departure time, date and periodicity
            "enabled": True,                                       # Set the timer active or not, True or False, required
            "recurring": True,                                     # True or False for recurring, required
            "time": "12:34",                                       # Time for departure, required
            "days": "nyynnnn",                                     # Days (mon-sun) for recurring schedule (n=disable, y=enable), required if recurring=True
            "chargingProgramId": 2,                                # Id of the charging program to be used for the departure profile
            }
        )
    if success:
        print("   Request completed successfully.")
    else:
        print("   Request failed.")
    return success

async def demo_set_departure_profile_schedule_date(vehicle):
    print('########################################')
    print('#  Change one departure profile date   #')
    print('########################################')
    success= await vehicle.set_departure_profile_schedule(id = 2,                             # id = 1, 2, 3
        schedule = {                                               # Set the departure time, date and periodicity
            "enabled": False,                                      # Set the timer active or not, True or False, required
            "recurring": False,                                    # True or False for recurring, required
            "time": "11:11",                                       # Time for departure, required
            "date": "2025-10-21",                                  # Date in format YYYY-MM-DD, required
            "chargingProgramId": 3,                                # Id of the charging program to be used for the departure profile
            }
        )
    if success:
        print("   Request completed successfully.")
    else:
        print("   Request failed.")
    return success

async def demo_set_timer_active(vehicle, id=1, action="off"):
    print('########################################')
    print('#         (De-)Activate one timer      #')
    print('########################################')
    success= await vehicle.set_timer_active(id, action)                # id = 1, 2, 3, action = "on" or "off".
    if success:
        print("   Request completed successfully.")
    else:
        print("   Request failed.")
    return success

async def demo_set_departure_profile_active(vehicle, id=1, action="off"):
    print('########################################')
    print('#  (De-)Activate one departure profile #')
    print('########################################')
    success= await vehicle.set_departure_profile_active(id, action)     # id = 1, 2, 3, action = "on" or "off".
    if success:
        print("   Request completed successfully.")
    else:
        print("   Request failed.")
    return success

async def demo_set_charge_limit(vehicle, limit=30):
    print('########################################')
    print('#     Change minimum charge limit      #')
    print('########################################')
    success= await vehicle.set_charge_limit(limit)                           # limit = 0,10,20,30,40,50
    if success:
        print("   Request completed successfully.")
    else:
        print("   Request failed.")
    return success

async def demo_set_climatisation(vehicle, action="start", temp=18.0):
    print('########################################')
    print('#      Start/Stop climatisation        #')
    print('########################################')
    success= await vehicle.set_climatisation(action, temp)            # mode = "auxilliary", "electric" or "off". spin is S-PIN and only needed for aux heating
    if success:
        print("   Request completed successfully.")
    else:
        print("   Request failed.")
    return success

async def demo_set_climatisation_temp(vehicle, temp=18.0):
    print('########################################')
    print('#   Change climatisation temperature   #')
    print('########################################')
    success= await vehicle.set_climatisation_temp(temp)            # temperature = integer from 16 to 30
    if success:
        print("   Request completed successfully.")
    else:
        print("   Request failed.")
    return success

async def demo_set_battery_climatisation(vehicle, mode=True):
    print('########################################')
    print('#   Set battery climatisation setting  #')
    print('########################################')
    success= await vehicle.set_battery_climatisation(mode)          # mode = False or True
    if success:
        print("   Request completed successfully.")
    else:
        print("   Request failed.")
    return success

async def demo_set_windowheating(vehicle, action="stop"):
    print('########################################')
    print('#    Start/Stop window heating         #')
    print('########################################')
    success= await vehicle.set_window_heating(action)                        # action = "start" or "stop"
    if success:
        print("   Request completed successfully.")
    else:
        print("   Request failed.")
    return success

async def demo_set_honkandflash(vehicle, action="flash"):
    print('########################################')
    print('#    Initiate (honk and) flash         #')
    print('########################################')
    success= await vehicle.set_honkandflash(action)
    if success:
        print("   Request completed successfully.")
    else:
        print("   Request failed.")
    return success

async def demo_set_lock(vehicle, action="lock", spin="1234"):
    print('########################################')
    print('#       Lock/unlock vehicle            #')
    print('########################################')
    success= await vehicle.set_lock(action, spin)
    if success:
        print("   Request completed successfully.")
    else:
        print("   Request failed.")
    return success

async def demo_show_last_honkandflash_info(vehicle):
    print('########################################')
    print('# Show info of last honk&flash request #')
    print('########################################')
    status= vehicle.honkandflash_action_status 
    timestamp= vehicle.honkandflash_action_timestamp
    if True: #success:
        print(f"   Last honk and flash was at {timestamp}. Status: {status}")
    else:
        print("   No honk and flash request was found.")
    return timestamp

async def demo_send_destination(vehicle):
    print('########################################')
    print('#      Send destination to vehicle     #')
    print('########################################')
    success= await vehicle.send_destination(                       
        destination = {                                                 # Send destination address
            "address": {                                                # address data optional
                "city":"Weiterstadt",
		        "country":"Germany",
		        "stateAbbreviation":"Hessen",
		        "street":"Max-Planck-Straße",
		        "houseNumber":"3-5",
		        "zipCode":"64331"
            },
	        "poiProvider":"google",                                     # poiProvider mandatory
	        "geoCoordinate":{"latitude":49.89824,"longitude":8.59465},  # geoCoordinate mandatory
	        "destinationName":"Seat/Cupra Deutschland"
            }
        )
    if success:
        print("   Request completed successfully.")
    else:
        print("   Request failed.")
    return success


async def main():
    """Main method."""
    credentials= readCredentialsFile()
    if credentials==None or credentials.get('username','')=='' or (credentials.get('password','')==''):
        _LOGGER.warning('Can not use the credentials read from the credentials file.')
        raise
    if credentials.get('brand','')!='':
        BRAND = credentials.get('brand','')
        print('Read brand from the credentials file.')
    else:
        print('No brand found in the credentials file. Using the default value.')
    print(f'Now working with brand={BRAND}')
    async with ClientSession(headers={'Connection': 'keep-alive'}) as session:
        print('')
        print('######################################################')
        print('# Logging on to ola.prod.code.seat.cloud.vwgroup.com #')
        print('######################################################')
        print(f"Initiating new session to Cupra/Seat Cloud with {credentials.get('username')} as username")
        connection = Connection(session, BRAND, credentials.get('username'), credentials.get('password'), PRINTRESPONSE, nightlyUpdateReduction=False, anonymise=True, tripStatisticsStartDate='1970-01-01')
        print("Attempting to login to the Seat Cloud service")
        print(datetime.now())
        if await connection.doLogin(tokenFile=TOKEN_FILE_NAME_AND_PATH, apiKey=credentials.get('apiKey',None)):
            print('Login or token refresh success!')
            print(datetime.now())
            print('Fetching user information for account.')
            await connection.get_userData()
            print(f"\tName: {connection._userData.get('name','')}")
            print(f"\tNickname: {connection._userData.get('nickname','')}")
            print(f"\tEmail: {connection._userData.get('email','')}")
            print(f"\tPicture: {connection._userData.get('picture','')}")
            print("")
            print('Fetching vehicles associated with account.')
            await connection.get_vehicles()

            instruments = set()
            for vehicle in connection.vehicles:
                txt = vehicle.vin
                if vehicle == connection.vehicles[0]: # Firebase can only be activated for one vehicle. So we use it for the first one
                    newStatus = await vehicle.initialiseFirebase(FIREBASE_CREDENTIALS_FILE_NAME_AND_PATH, vehicle.update)
                    print('########################################')
                    print('#      Initialisation of firebase      #')
                    print(txt.center(40, '#'))
                    print(f"New status of firebase={newStatus}")

                print('')
                print('########################################')
                print('#         Setting up dashboard         #')
                print(txt.center(40, '#'))
                dashboard = vehicle.dashboard(mutable=True)

                """for instrument in (
                        instrument
                        for instrument in dashboard.instruments
                        if instrument.component in COMPONENTS
                        and is_enabled(instrument.slug_attr)):

                    instruments.add(instrument)
                """
                for instrument in dashboard.instruments:
                    if instrument.component in COMPONENTS and is_enabled(instrument.slug_attr):
                        instruments.add(instrument)
            print('')
            print('########################################')
            print('#          Vehicles discovered         #')
            print('########################################')
            for vehicle in connection.vehicles:
                print(f"\tVIN: {vehicle.vin}")
                print(f"\tModel: {vehicle.model}")
                print(f"\tManufactured: {vehicle.model_year}")
                print(f"\tConnect service deactivated: {vehicle.deactivated}")
                print("")
                if vehicle.is_nickname_supported: print(f"\tNickname: {vehicle.nickname}")
                print(f"\tObject attributes, and methods:")
                for prop in dir(vehicle):
                    if not "__" in prop:
                        try:
                            func = f"vehicle.{prop}"
                            typ = type(eval(func))
                            print(f"\t\t{prop} - {typ}")
                        except:
                            pass

        else:
            return False

        # Output all instruments and states
        print('')
        print('########################################')
        print('#      Instruments from dashboard      #')
        print('########################################')
        inst_list = sorted(instruments, key=lambda x: x.attr)
        for instrument in inst_list:
            print(f'{instrument.full_name}|{instrument.attr} - {instrument.str_state}|{instrument.state} - attributes: {instrument.attributes}')

        print('')
        print(f"Sleeping for {INTERVAL} seconds")
        await asyncio.sleep(INTERVAL)

        print('')
        print(datetime.now())
        print('')
        #print('########################################')
        #print('# Updating all values from MyCupra/Seat#')
        #print('########################################')
        #print("Updating ALL values from My Cupra/Seat Cloud ....")
        #if await connection.update_all():
        #    print("Success!")
        #else:
        #    print("Failed")

        # Sleep for a given amount of time and update individual API endpoints for each vehicle
        #print('')
        #print(f"Sleeping for {INTERVAL} seconds")
        #await asyncio.sleep(INTERVAL)

        for vehicle in connection.vehicles:
            """print('')
            print(datetime.now())
            print('')
            print('########################################')
            print('#          Update charger data         #')
            print(txt.center(40, '#'))
            await vehicle.get_charger()
            print('')
            print('########################################')
            print('#         Update climater data         #')
            print(txt.center(40, '#'))
            await vehicle.get_climater()
            print('')
            print('########################################')
            print('#         Update position data         #')
            print(txt.center(40, '#'))
            await vehicle.get_position()
            print('')
            print('########################################')
            print('#         Update preheater data        #')
            print(txt.center(40, '#'))
            await vehicle.get_preheater()
            print('')
            print('########################################')
            print('#          Update realcar data         #')
            print(txt.center(40, '#'))
            await vehicle.get_realcardata()
            print('')
            print('########################################')
            print('#          Update status data          #')
            print(txt.center(40, '#'))
            await vehicle.get_statusreport()
            print('')
            print('########################################')
            print('#       Update timer programming       #')
            print(txt.center(40, '#'))
            await vehicle.get_timerprogramming()
            print('')
            print('########################################')
            print('#        Update trip statistics        #')
            print(txt.center(40, '#'))
            await vehicle.get_trip_statistic()
            print('')
            print('Updates complete')

            print(f"Sleeping for {INTERVAL} seconds")
            await asyncio.sleep(INTERVAL)"""
            
            print('########################################')
            print('#     Export driving data to csv       #')
            print(txt.center(40, '#'))
            exportToCSV(vehicle, credentials.get('csvFileName','./drivingData.csv'), 'short') # possible value: short/cyclic
            print('')
            print('Export of driving data to csv complete')

            # Examples for using set functions:

            #await demo_set_charger(vehicle, action = "start")                         # action = "start" or "stop"
            #await demo_set_charger_current(vehicle, value='reduced')                  # value = 1-255/Maximum/Reduced (PHEV: 252 for reduced and 254 for max, EV: Maximum/Reduced)
            #await demo_set_charger_target_soc(vehicle, value=70)                      # value = 1-100

            #await demo_set_climatisation(vehicle, action = "start", temp=18.0)        # action = "auxilliary", "electric" or "off". spin is S-PIN and only needed for aux heating
            #await demo_set_climatisation_temp(vehicle, temp = 18.0)                   # temp = integer from 16 to 30
            #await demo_set_battery_climatisation(vehicle, mode=False)                 # mode = False or True
            #await demo_set_windowheating(vehicle, action = "stop")                    # action = "start" or "stop"

            #await demo_set_timer_schedule(vehicle)                                    # arguments id and schedule can be found in the demo function
            #await demo_set_timer_active(vehicle, id=3, action="off")                  # id = 1, 2, 3, action = "on" or "off".
            #await demo_set_charge_limit(vehicle, 30)                                  # limit = PHEV: 0/10/20/30/40/50, EV: 50/60/70/80/90/100
            
            #await demo_set_departure_profile_schedule(vehicle)                        # arguments id and schedule can be found in the demo function
            #await demo_set_departure_profile_schedule_date(vehicle)                        # arguments id and schedule can be found in the demo function
            #await demo_set_departure_profile_active(vehicle, id=3, action="off")                 # id = 1, 2, 3, action = "on" or "off".

            #await demo_set_lock(vehicle,action = "lock", 
            #                    spin = credentials.get('spin',''))                    # action = "unlock" or "lock". spin = SPIN, needed for both

            #await vehicle.set_pheater(mode = "heating", spin = "1234")                # action = "heating", "ventilation" or "off". spin = SPIN, not needed for off

            #await demo_set_honkandflash(vehicle, action="flash")                      # action = "honkandflash" or "flash"

            #await vehicle.set_refresh()                                               # Takes no arguments, will trigger forced update

            #print(f"Sleeping for {2*INTERVAL} seconds")
            #await asyncio.sleep(2*INTERVAL)
            #await demo_show_last_honkandflash_info(vehicle)                           # Returns the info of the last honkandflash_action

            #await demo_send_destination(vehicle)                                      # arguments can be found in the demo function

            print('########################################')
            print('#    Export all attributes to file    #')
            print(txt.center(40, '#'))
            rc= exportAllAttributes(vehicle, ALL_ATTRIBUTES_FILE_NAME_AND_PATH)
            print('')
            if rc:
                print('Export of all attributes successfully completed')
            else:
                print('Export of all attributes failed')

            if vehicle.firebaseStatus== 1: # firebase messaging activated
                # Do an endless loop to wait and receive firebase messages    
                i=0
                while True:
                    print(f"Sleeping for {6*INTERVAL} seconds")
                    await asyncio.sleep(6*INTERVAL)
                    i=i+1
                    _LOGGER.debug(f'Round {i}')

    sys.exit(1)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())

