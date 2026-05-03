import logging
import asyncio
import os
import json
import string
import secrets

from .firebase_messaging import FcmPushClient, FcmRegisterConfig
from typing import Any


from .const import (
    FCM_PROJECT_ID,
    FCM_API_KEY,
    FCM_APP_ID
)

_LOGGER = logging.getLogger(__name__)
globalFirebaseCredentialsFileName = ''

class Firebase():
    def __init__(self, logPrefix=None):
        self._pushClient = None
        if logPrefix is not None:
            self._LOGGER= logging.getLogger(__name__+"_"+logPrefix)
        else:
            self._LOGGER = _LOGGER


    async def firebaseStart(self, onNotificationFunc, firebaseCredentialsFileName: str, brand='cupra') -> bool: 
        """ Starts the firebase cloud messaging receiver """
        try:
            loop = asyncio.get_running_loop()
            credentials = await loop.run_in_executor(None, readFCMCredsFile, firebaseCredentialsFileName)
            global globalFirebaseCredentialsFileName 
            globalFirebaseCredentialsFileName = firebaseCredentialsFileName

            fcm_project_id=FCM_PROJECT_ID
            fcm_app_id=FCM_APP_ID[brand]
            fcm_api_key=FCM_API_KEY
            chars = string.ascii_letters + string.digits
            fcmMessageSenderId = ''.join(secrets.choice(chars) for i in range(16)) 
            fcmMessageSenderId= 'fxpWQ_'+fcmMessageSenderId

            fcm_config = FcmRegisterConfig(fcm_project_id, fcm_app_id, fcm_api_key, fcmMessageSenderId)
            self._pushClient = FcmPushClient(onNotificationFunc, fcm_config, credentials, syncOnFCMCredentialsUpdated)
            fcm_token = await self._pushClient.checkin_or_register() #(firebaseCredentialsFileName)
            self._LOGGER.debug(f'Firebase.checkin_or_register() returned a token:{fcm_token}')
            await self._pushClient.start()
            await asyncio.sleep(5)
            return self._pushClient.is_started()
        except Exception as e:
            self._LOGGER.error(f'Error in firebaseStart. Error: {e}')
            return False

    async def firebaseStop(self) -> bool: 
        """ Stops the firebase cloud messaging receiver """
        try:
            await self._pushClient.stop()
            #await asyncio.sleep(5)
            self._pushClient = None
            return True
        except Exception as e:
            self._LOGGER.error(f'Error in firebaseStop. Error: {e}')
            return False

def readFCMCredsFile(credsFile) -> dict[str, Any]:
    """ Reads the firebase cloud messaging credentials from file"""
    try:
        if os.path.isfile(credsFile):
            with open(credsFile, "r") as f:
                credString=f.read()
            f.close()
            creds=json.loads(credString)
            return creds
        else:
            _LOGGER.debug(f'{credsFile} not found.')
            return {}
    except Exception as e:
        _LOGGER.warning(f'readFCMCredsFile() not successful. Error: {e}')
        return {}

def writeFCMCredsFile(creds, firebaseCredentialsFileName) -> None:
    """ Saves the firebase cloud messaging credentials to a file for future use """
    try:
        with open(firebaseCredentialsFileName, "w") as f:
            f.write(json.dumps(creds))
        f.close()
    except Exception as e:
        _LOGGER.warning(f'writeFCMCredsFile() not successful. Error: {e}')

def syncOnFCMCredentialsUpdated(creds: dict[str, Any]) -> None:
    asyncio.get_event_loop().create_task(onFCMCredentialsUpdated(creds))


async def onFCMCredentialsUpdated(creds: dict[str, Any]) -> None:
    """ Is called from firebase-messaging package """
    global globalFirebaseCredentialsFileName
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, writeFCMCredsFile, creds, globalFirebaseCredentialsFileName)
    #writeFCMCredsFile(creds, globalFirebaseCredentialsFileName)
    
