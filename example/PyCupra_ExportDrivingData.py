#!/usr/bin/env python3
""" Sample program to export the trip statistics as csv file"""
import asyncio
import logging
import inspect
import sys
import os
import json
import pandas as pd
from aiohttp import ClientSession
from datetime import datetime

currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0, parentdir)

try:
    from pycupra import Connection
except ModuleNotFoundError as e:
    print(f"Unable to import library: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.WARN)
_LOGGER = logging.getLogger(__name__)
BRAND = 'cupra' # or 'seat' (Default value if no brand is provided via credentials file)

PRINTRESPONSE = True
INTERVAL = 5
TOKEN_FILE_NAME_AND_PATH='./pycupra_token.json'
CREDENTIALS_FILE_NAME_AND_PATH='./pycupra_credentials.json'

def readCredentialsFile():
    try:
        with open(CREDENTIALS_FILE_NAME_AND_PATH, "r") as f:
            credentialsString=f.read()
        credentials=json.loads(credentialsString)
        return credentials
    except:
        _LOGGER.info('readCredentialsFile not successful. Perhaps no credentials file present.')
        return None

def exportToCSV(vehicle, csvFileName, dataType='dailySums'):
    if len(vehicle.attrs.get('tripstatistics', {}).get(dataType, []))< 1:
        _LOGGER.warning(f'No trips statistics of type {dataType}')
        return False
    df= pd.DataFrame(vehicle._states['tripstatistics'][dataType])
    _LOGGER.debug('Exporting trip data to csv')
    df.to_csv(csvFileName)
    return True

async def main():
    """Main method."""
    print('')
    print('######################################################')
    print('#               Reading credentials file             #')
    print('######################################################')
    credentials= readCredentialsFile()
    if credentials is None or credentials.get('username','') == '' or (credentials.get('password','') == ''):
        _LOGGER.warning('Can not use the credentials read from the credentials file.')
        raise
    if credentials.get('brand','') != '':
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
        connection = Connection(session, BRAND, credentials.get('username'), credentials.get('password'), PRINTRESPONSE, nightlyUpdateReduction=False, anonymise=False)
        print("Attempting to login to the Seat Cloud service")
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
        else:
            return False

        for vehicle in connection.vehicles:
            txt = vehicle.vin
            print('########################################')
            print('#     Export driving data to csv       #')
            print(txt.center(40, '#'))
            exportToCSV(vehicle, credentials.get('csvFileName','./drivingData.csv'), 'dailySums') # possible 'dailySums' and 'monthlySums'
            print('')
            print('Export of driving data to csv complete')
    #sys.exit(1)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())

