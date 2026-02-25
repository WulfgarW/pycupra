#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Communicate with the My Cupra portal."""
"""First fork from https://github.com/robinostlund/volkswagencarnet where it was modified to support also Skoda Connect"""
"""Then forked from https://github.com/lendy007/skodaconnect for adaptation to Seat Connect"""
"""Then forked from https://github.com/Farfar/seatconnect for adaptation to the new API of My Cupra and My Seat"""
import re
import os
import json
import logging
import asyncio
import hashlib
import jwt
import string
import secrets
import xmltodict
from copy import deepcopy
import importlib.metadata
from typing import Any
import csv

from PIL import Image
from io import BytesIO
from sys import version_info, argv
from datetime import timedelta, datetime, timezone
from urllib.parse import urljoin, parse_qs, urlparse, urlencode
from json import dumps as to_json
from jwt.exceptions import ExpiredSignatureError
import aiohttp
from bs4 import BeautifulSoup
from base64 import b64decode, b64encode, urlsafe_b64decode, urlsafe_b64encode
from .utilities import json_loads
from .vehicle import Vehicle
from .exceptions import (
    PyCupraConfigException,
    PyCupraAuthenticationException,
    PyCupraAccountLockedException,
    PyCupraTokenExpiredException,
    PyCupraException,
    PyCupraEULAException,
    PyCupraMarketingConsentException,
    PyCupraThrottledException,
    PyCupraLoginFailedException,
    PyCupraInvalidRequestException,
    PyCupraRequestInProgressException,
    PyCupraServiceUnavailable
)

from requests_oauthlib import OAuth2Session
from oauthlib.oauth2.rfc6749.parameters import parse_authorization_code_response, parse_token_response, prepare_grant_uri

from aiohttp import ClientSession, ClientTimeout
from aiohttp.hdrs import METH_GET, METH_POST, METH_PUT, METH_DELETE

from .const import (
    HEADERS_SESSION,
    HEADERS_AUTH,
    TOKEN_HEADERS,
    BASE_SESSION,
    BASE_AUTH,
    CLIENT_LIST,
    XCLIENT_ID,
    XAPPVERSION,
    XAPPNAME,
    AUTH_OIDCONFIG,
    AUTH_TOKEN,
    AUTH_TOKENKEYS,
    AUTH_REFRESH,
    APP_URI,
    API_MBB_STATUSDATA,
    API_PERSONAL_DATA,
    API_USER_INFO,
    API_CONNECTION,
    API_PSP,
    API_VEHICLES,
    API_MYCAR,
    API_RANGES,
    API_STATUS,
    API_CHARGING,
    API_CHARGING_PROFILES,
    API_POSITION,
    API_POS_TO_ADDRESS,
    API_TRIP,
    API_TRIP_V1,
    API_CLIMATER_STATUS,
    API_CLIMATER,
    API_CLIMATISATION_TIMERS,
    API_DEPARTURE_TIMERS,
    API_DEPARTURE_PROFILES,
    API_MILEAGE,
    API_CAPABILITIES,
    #API_CAPABILITIES_MANAGEMENT,
    API_MAINTENANCE,
    API_WARNINGLIGHTS,
    API_MEASUREMENTS,
    API_RELATION_STATUS,
    API_INVITATIONS,
    #API_ACTION,
    API_ACTIONS,
    API_IMAGE,
    API_HONK_AND_FLASH,
    API_ACCESS,
    API_SECTOKEN,
    API_REQUESTS,
    API_REFRESH,
    API_DESTINATION,
    API_AUXILIARYHEATING,

    PUBLIC_MODEL_IMAGES_SERVER,
    FIREBASE_STATUS_NOT_INITIALISED,
    SUMTYPE_DAILY,
    SUMTYPE_MONTHLY,
)

version_info >= (3, 0) or exit('Python 3 required')
lib_version = importlib.metadata.version("pycupra")

_LOGGER = logging.getLogger(__name__)
BRAND_CUPRA = 'cupra'
TIMEOUT = timedelta(seconds=90)
loginInProgress = False

class Connection:
    """ Connection to Connect services """
  # Init connection class
    def __init__(self, session, brand='cupra', username='', password='', fulldebug=False, nightlyUpdateReduction=False, anonymise=True, tripStatisticsStartDate=None, logPrefix=None, hass=None, **optional):
        """ Initialize """
        self._logPrefix = logPrefix
        if self._logPrefix!= None:
            self._LOGGER= logging.getLogger(__name__+"_"+self._logPrefix)
        else:
            self._LOGGER = _LOGGER

        self._session = session
        self._lock = asyncio.Lock()
        self._session_fulldebug = fulldebug
        self._session_nightlyUpdateReduction = nightlyUpdateReduction
        self._session_anonymise = anonymise
        self._session_tripStatisticsStartDate = tripStatisticsStartDate
        self._session_headers = HEADERS_SESSION.get(brand).copy()
        self._session_base = BASE_SESSION
        self._session_auth_headers = HEADERS_AUTH.copy()
        self._session_token_headers = TOKEN_HEADERS.copy()
        self._session_cookies = ""
        self._session_nonce = self._getNonce()
        self._session_state = self._getState()

        self._session_auth_ref_url = BASE_SESSION
        self._session_spin_ref_url = BASE_SESSION
        self._session_first_update = False
        self._session_auth_brand = brand
        self._session_auth_username = username
        self._session_auth_password = password
        self._hass = hass
        self._session_tokens = {}

        self._vehicles = []
        self._userData = {}
        self.dailyTripData: dict = {}
        self.monthlyTripData: dict = {}

        self._LOGGER.info(f'Init PyCupra library, version {lib_version}')
        self._LOGGER.debug(f'Using service {self._session_base}')

        self._sessionRequestCounter = 0
        self._sessionRequestTimestamp = datetime.now(tz= None)
        self._sessionRequestCounterHistory = {}
        self._anonymisationDict={}
        self.addToAnonymisationDict(self._session_auth_username, '[USERNAME_ANONYMISED]')
        self.addToAnonymisationDict(self._session_auth_password, '[PASSWORD_ANONYMISED]')
        self._anonymisationKeys={'firstName', 'lastName', 'dateOfBirth', 'nickname'}
        self.addToAnonymisationKeys('name')
        self.addToAnonymisationKeys('given_name')
        self.addToAnonymisationKeys('email')
        self.addToAnonymisationKeys('family_name')
        self.addToAnonymisationKeys('birthdate')
        self.addToAnonymisationKeys('vin')
        self.addToAnonymisationKeys('mbbUserId')
        self._error401 = False

        try:
            if self._hass:
                self._dataBasePath = self._hass.config.path("pycupra_data")
            else:
                self._dataBasePath = os.path.join(".", "pycupra_data")
            if not os.path.exists(self._dataBasePath):
                self._LOGGER.error(f'Directory {self._dataBasePath} does not exist. This should only happen once. Creating it.')
                os.mkdir(self._dataBasePath)
        except Exception as error:
            raise PyCupraException(f'Error while checking for data folders and creating them if bot already present. Error: {error}')

    def _clear_cookies(self):
        self._session._cookie_jar._cookies.clear()
        self._session_cookies = ''

    def _getNonce(self):
        chars = string.ascii_letters + string.digits
        text = ''.join(secrets.choice(chars) for i in range(10))
        sha256 = hashlib.sha256()
        sha256.update(text.encode())
        return (b64encode(sha256.digest()).decode('utf-8')[:-1])

    def _getState(self):
        return self._getNonce()

    def readTokenFile(self, brand):
        try:
            if os.path.isfile(self._tokenFile):
                with open(self._tokenFile, "r") as f:
                    tokenString=f.read()
                f.close()
                tokens=json.loads(tokenString)
                self._session_tokens[brand]=tokens
                self._user_id=tokens['user_id']
                self.addToAnonymisationDict(self._user_id,'[USER_ID_ANONYMISED]')
                return True
            self._LOGGER.info('No token file present. readTokenFile() returns False.')
            return False
        except:
            self._LOGGER.warning('readTokenFile() not successful.')
            return False

    def writeTokenFile(self, brand):
        if not hasattr(self, '_tokenFile'):
            self._LOGGER.debug('No token file name provided. Therefore tokens were not written to file.')
            return False
        self._session_tokens[brand]['user_id']=self._user_id
        try:
            with open(self._tokenFile, "w") as f:
                f.write(json.dumps(self._session_tokens[brand]))
            f.close()
            return True
        except Exception as e:
            self._LOGGER.warning(f'writeTokenFile() not successful. Error: {e}')
            return False

    def deleteTokenFile(self):
        if not hasattr(self, '_tokenFile'):
            self._LOGGER.debug('No token file name provided. Therefore token file (if one exists) was not deleted.')
            return False
        try:
            os.remove(self._tokenFile)
            self._LOGGER.info(f'Deleted token file.')
            return True
        except Exception as e:
            self._LOGGER.warning(f'deleteTokenFile() not successful. Error: {e}')
            return False

    def writeImageFile(self, imageName, imageData, imageDict, vin):
        try:
            # Target directory in HA container (/config/www)
            if self._hass:
                base_path = self._hass.config.path("www")
            else:
                base_path = os.path.join(".", "www")
            images_dir = os.path.join(base_path, "pycupra")
            os.makedirs(images_dir, exist_ok=True)

            file_path = os.path.join(images_dir, f"image_{vin}_{imageName}.png")

            with open(file_path, "wb") as f:
                f.write(imageData)
            imageDict[imageName]=f'/local/pycupra/image_{vin}_{imageName}.png'
            #self._LOGGER.debug(f"Saved image: {file_path}") # Contains the vin, so should be commented out
            f.close()
            return True
        except Exception as e:
            self._LOGGER.warning(f'writeImageFile() not successful. Ignoring this problem. Error: {e}')
            return False

  # API login/logout/authorization
    async def doLogin(self,**data) -> bool:
        """Login method, clean login or use token from file and refresh it"""
        self._LOGGER.info('doLogin() first tries to read tokens from file and to refresh them.')

        # Remove cookies and re-init session
        self._clear_cookies()
        self._vehicles.clear()
        self._session_tokens = {}
        self._session_headers = HEADERS_SESSION.get(self._session_auth_brand, HEADERS_SESSION[self._session_auth_brand]).copy()
        self._session_auth_headers = HEADERS_AUTH.copy()
        self._session_nonce = self._getNonce()
        self._session_state = self._getState()

        if data.get('apiKey',None)!=None:
            self._googleApiKey=data.get('apiKey')
        if data.get('tokenFile',None)!=None:
            self._tokenFile=data.get('tokenFile')
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, self.readTokenFile, self._session_auth_brand)
            if result:
                rc=await self.refresh_token(self._session_auth_brand)
                if rc:
                    self._LOGGER.info('Successfully read tokens from file and refreshed them.')
                    return True
        self._LOGGER.info('Initiating new login with user name and password.')
        return await self._authorize(self._session_auth_brand)

    async def _authorize(self, client=BRAND_CUPRA) -> bool:
        """"Login" function. Authorize a certain client type and get tokens."""
        # Helper functions
        def extract_csrf(req):
            return re.compile('<meta name="_csrf" content="([^"]*)"/>').search(req).group(1)

        def extract_guest_language_id(req):
            return req.split('_')[1].lower()

        # Login/Authorization starts here
        try:
            self._LOGGER.debug('Checking for concurrent logins in progress')

            waitTimeExpired = datetime.now(tz=None) + timedelta(seconds= 15)
            global loginInProgress
            while loginInProgress:
                await asyncio.sleep(5)
                if waitTimeExpired < datetime.now(tz=None):
                    self._LOGGER.warning('Waited about 15 seconds for a concurrent login to finish without success. Assuming, it has ended.')
                    loginInProgress = False
            loginInProgress = True

            self._LOGGER.debug(f'Starting authorization process for client {client}')
            req = await self._session.get(
                url=AUTH_OIDCONFIG
            )
            if req.status != 200:
                self._LOGGER.debug(f'Get request to {AUTH_OIDCONFIG} was not successful. Response: {req}')
                return False
            response_data =  await req.json()
            self._LOGGER.debug(f'Get request to {AUTH_OIDCONFIG} was not successful. Response data: {response_data}')
            authorizationEndpoint = response_data['authorization_endpoint']
            authissuer = response_data['issuer']
            oauthClient = OAuth2Session(client_id=CLIENT_LIST[client].get('CLIENT_ID'), scope=CLIENT_LIST[client].get('SCOPE'), redirect_uri=CLIENT_LIST[client].get('REDIRECT_URL'))
            code_verifier = urlsafe_b64encode(os.urandom(40)).decode('utf-8')
            code_verifier = re.sub('[^a-zA-Z0-9]+', '', code_verifier)
            code_challenge_hash = hashlib.sha256(code_verifier.encode("utf-8")).digest()
            code_challenge = urlsafe_b64encode(code_challenge_hash).decode("utf-8")
            code_challenge = code_challenge.replace("=", "")
            authorization_url, state = oauthClient.authorization_url(authorizationEndpoint, code_challenge=code_challenge, code_challenge_method='S256', 
                                                                        nonce=self._session_nonce, state=self._session_state)

            # Get authorization page (login page)
            if self._session_fulldebug:
                self._LOGGER.debug(f'Get authorization page: "{authorization_url}"')
            try:
                req = await self._session.get(
                    url=authorization_url,
                        headers=self._session_auth_headers.get(client),
                        allow_redirects=False
                    )
                if req.headers.get('Location', False):
                    ref = req.headers.get('Location', '')
                    if 'error' in ref:
                        error = parse_qs(urlparse(ref).query).get('error', '')[0]
                        if 'error_description' in ref:
                            error = parse_qs(urlparse(ref).query).get('error_description', '')[0]
                            self._LOGGER.info(f'Unable to login, {error}')
                        else:
                            self._LOGGER.info(f'Unable to login.')
                        raise PyCupraException(error)
                    else:
                        if self._session_fulldebug:
                            self._LOGGER.debug(f'Got authorization endpoint: "{ref}"')
                        req = await self._session.get(
                            url=ref,
                            headers=self._session_auth_headers.get(client),
                            allow_redirects=False
                        )
                else:
                    self._LOGGER.warning(f'Unable to fetch authorization endpoint')
                    raise PyCupraException('Missing "location" header')
            except (PyCupraException):
                raise
            except Exception as error:
                self._LOGGER.warning(f'Failed to get authorization endpoint. {error}')
                raise PyCupraException(error)

            # If we need to sign in (first token)
            if 'signin-service' in ref:
                self._LOGGER.debug("Got redirect to signin-service")
                location = await self._signin_service(req, authissuer, authorizationEndpoint, client)
            else:
                # We are already logged on, shorter authorization flow
                location = req.headers.get('Location', None)

            # Follow all redirects until we reach the callback URL
            try:
                maxDepth = 10
                while not location.startswith(CLIENT_LIST[client].get('REDIRECT_URL')):
                    if location is None:
                        raise PyCupraException('Login failed')
                    if 'error' in location:
                        errorTxt = parse_qs(urlparse(location).query).get('error', '')[0]
                        if errorTxt == 'login.error.throttled':
                            timeout = parse_qs(urlparse(location).query).get('enableNextButtonAfterSeconds', '')[0]
                            raise PyCupraAccountLockedException(f'Account is locked for another {timeout} seconds')
                        elif errorTxt == 'login.errors.password_invalid':
                            raise PyCupraAuthenticationException('Invalid credentials')
                        else:
                            self._LOGGER.warning(f'Login failed: {errorTxt}')
                        raise PyCupraLoginFailedException(errorTxt)
                    if 'terms-and-conditions' in location:
                        raise PyCupraEULAException('The terms and conditions must be accepted first at your local SEAT/Cupra site, e.g. "https://cupraid.vwgroup.io/"')
                    if 'consent/marketing' in location:
                        raise PyCupraMarketingConsentException('The question to consent to marketing must be answered first at your local SEAT/Cupra site, e.g. "https://cupraid.vwgroup.io/"')
                    if 'user_id' in location: # Get the user_id which is needed for some later requests
                        self._user_id=parse_qs(urlparse(location).query).get('user_id', [''])[0]
                        self.addToAnonymisationDict(self._user_id,'[USER_ID_ANONYMISED]')
                        #self._LOGGER.debug('Got user_id: %s' % self._user_id)
                    if self._session_fulldebug:
                        self._LOGGER.debug(self.anonymise(f'Following redirect to "{location}"'))
                    response = await self._session.get(
                        url=location,
                        headers=self._session_auth_headers.get(client),
                        allow_redirects=False
                    )
                    if response.headers.get('Location', False) is False:
                        self._LOGGER.debug(f'Unexpected response: {await req.text()}')
                        raise PyCupraAuthenticationException('User appears unauthorized')
                    location = response.headers.get('Location', None)
                    # Set a max limit on requests to prevent forever loop
                    maxDepth -= 1
                    if maxDepth == 0:
                        raise PyCupraException('Too many redirects')
            except (PyCupraException, PyCupraEULAException, PyCupraAuthenticationException, PyCupraAccountLockedException, PyCupraLoginFailedException, PyCupraMarketingConsentException):
                self._LOGGER.warning(f'Running into login problems with location={location}')
                raise
            except Exception as e:
                # If we get an unhandled exception it should be because we can't redirect to the APP_URI URL and thus we have our auth code
                if 'code' in location:
                    if self._session_fulldebug:
                        self._LOGGER.debug('Got code: %s' % location)
                    pass
                else:
                    self._LOGGER.debug(f'Exception occured while logging in.')
                    raise PyCupraLoginFailedException(e)

            self._LOGGER.debug('Received authorization code, exchange for tokens.')
            # Extract code and tokens
            auth_code = parse_qs(urlparse(location).query).get('code', [''])[0]
            # Save access, identity and refresh tokens according to requested client"""
            if client=='cupra':
                # oauthClient.fetch_token() does not work in home assistant, using POST request instead
                #token_data= oauthClient.fetch_token(token_url=AUTH_TOKEN,  
                #                       client_id=CLIENT_LIST[client].get('CLIENT_ID'), client_secret=CLIENT_LIST[client].get('CLIENT_SECRET'), authorization_response=location, 
                #                       code_verifier=code_verifier, code=auth_code)
                data = {
                        'redirect_uri': CLIENT_LIST[client].get('REDIRECT_URL'),
                        'client_id': CLIENT_LIST[client].get('CLIENT_ID'),
                        'client_secret': CLIENT_LIST[client].get('CLIENT_SECRET'), 
                        'authorization_response': location,
                        'code': auth_code,
                        'code_verifier': code_verifier,
                        'grant_type': 'authorization_code'
                        }
                req = await self._session.post(
                    url=AUTH_TOKEN,
                    data = data,
                    headers=self._session_auth_headers.get(client),
                    allow_redirects=False
                    )
                token_data = await req.json()
            else:
                data = {
                        'redirect_uri': CLIENT_LIST[client].get('REDIRECT_URL'),
                        'client_id': CLIENT_LIST[client].get('CLIENT_ID'),
                        'code': auth_code,
                        'code_verifier': code_verifier,
                        'grant_type': 'authorization_code'
                        }
                req = await self._session.post(
                    url=AUTH_REFRESH,
                    data = data,
                    headers=self._session_auth_headers.get(client),
                    allow_redirects=False
                    )
                token_data = await req.json()
            self._session_tokens[client] = {}
            for key in token_data:
                if '_token' in key:
                    self._session_tokens[client][key] = token_data[key]
            if 'error' in self._session_tokens[client]:
                errorTxt = self._session_tokens[client].get('error', '')
                if 'error_description' in self._session_tokens[client]:
                    error_description = self._session_tokens[client].get('error_description', '')
                    raise PyCupraException(f'{errorTxt} - {error_description}')
                else:
                    raise PyCupraException(errorTxt)
            if self._session_fulldebug:
                for key in self._session_tokens.get(client, {}):
                    if 'token' in key:
                        self._LOGGER.debug(f'Got {key} for client {CLIENT_LIST[client].get("CLIENT_ID","")}, token: "{self._session_tokens.get(client, {}).get(key, None)}"')
            # Verify token, warn if problems are found
            verify = await self.verify_token(self._session_tokens[client].get('id_token', ''))
            if verify is False:
                self._LOGGER.warning(f'Token for {client} is invalid!')
            elif verify is True:
                self._LOGGER.debug(f'Token for {client} verified OK.')
            else:
                self._LOGGER.warning(f'Token for {client} could not be verified, verification returned {verify}.')
            loop = asyncio.get_running_loop()
            rt = await loop.run_in_executor(None, self.writeTokenFile, client)
        except (PyCupraEULAException):
            self._LOGGER.warning('Login failed, the terms and conditions might have been updated and need to be accepted. Login to  your local SEAT/Cupra site, e.g. "https://cupraid.vwgroup.io/" and accept the new terms before trying again')
            raise
        except (PyCupraMarketingConsentException):
            self._LOGGER.warning('Login failed, the marketing conditions might have been updated and need to be accepted or disagreed. Login to  your local SEAT/Cupra site, e.g. "https://cupraid.vwgroup.io/" and accept the new terms before trying again')
            raise
        except (PyCupraAccountLockedException):
            self._LOGGER.warning('Your account is locked, probably because of too many incorrect login attempts. Make sure that your account is not in use somewhere with incorrect password')
            raise
        except (PyCupraAuthenticationException):
            self._LOGGER.warning('Invalid credentials or invalid configuration. Make sure you have entered the correct credentials')
            raise
        except (PyCupraException):
            self._LOGGER.error('An API error was encountered during login, try again later')
            raise
        except (TypeError):
            self._LOGGER.warning(self.anonymise(f'Login failed for {self._session_auth_username}. The server might be temporarily unavailable, try again later. If the problem persists, verify your account at your local SEAT/Cupra site, e.g. "https://cupraofficial.se/"'))
        except Exception as error:
            self._LOGGER.error(self.anonymise(f'Login failed for {self._session_auth_username}, {error}'))
            loginInProgress = False
            return False
        loginInProgress = False
        return True

    async def _signin_service(self, html, authissuer, authorizationEndpoint, client=BRAND_CUPRA):
        """Method to signin to Connect portal."""
        # Extract login form and extract attributes
        try:
            response_data = await html.text()
            responseSoup = BeautifulSoup(response_data, 'html.parser')
            form_data = dict()
            if responseSoup is None:
                raise PyCupraLoginFailedException('Login failed, server did not return a login form')
            for t in responseSoup.find('form', id='emailPasswordForm').find_all('input', type='hidden'):
                if self._session_fulldebug:
                    self._LOGGER.debug(f'Extracted form attribute: {t["name"], t["value"]}')
                form_data[t['name']] = t['value']
            form_data['email'] = self._session_auth_username
            pe_url = authissuer+responseSoup.find('form', id='emailPasswordForm').get('action')
        except Exception as e:
            self._LOGGER.error('Failed to extract user login form.')
            raise

        # POST email
        self._session_auth_headers[client]['Referer'] = authorizationEndpoint
        self._session_auth_headers[client]['Origin'] = authissuer
        self._LOGGER.debug(self.anonymise(f"Start authorization for user {self._session_auth_username}"))
        req = await self._session.post(
            url = pe_url,
            headers = self._session_auth_headers.get(client),
            data = form_data
        )
        if req.status != 200:
            raise PyCupraException('Authorization request failed')
        try:
            response_data = await req.text()
            responseSoup = BeautifulSoup(response_data, 'html.parser')
            pwform = {}
            credentials_form = responseSoup.find('form', id='credentialsForm')
            all_scripts = responseSoup.find_all('script', {'src': False})
            if credentials_form is not None:
                self._LOGGER.debug('Found HTML credentials form, extracting attributes')
                for t in credentials_form.find_all('input', type='hidden'):
                    if self._session_fulldebug:
                        self._LOGGER.debug(f'Extracted form attribute: {t["name"], t["value"]}')
                    pwform[t['name']] = t['value']
                    form_data = pwform
                    post_action = responseSoup.find('form', id='credentialsForm').get('action')
            elif all_scripts is not None:
                self._LOGGER.debug('Found dynamic credentials form, extracting attributes')
                pattern = re.compile("templateModel: (.*?),\n")
                for sc in all_scripts:
                    if(pattern.search(sc.string)):
                        import json
                        data = pattern.search(sc.string)
                        jsondata = json.loads(data.groups()[0])
                        self._LOGGER.debug(self.anonymise(f'JSON: {jsondata}'))
                        if not jsondata.get('hmac', False):
                            raise PyCupraLoginFailedException('Failed to extract login hmac attribute')
                        if not jsondata.get('postAction', False):
                            raise PyCupraLoginFailedException('Failed to extract login post action attribute')
                        if jsondata.get('error', None) is not None:
                            raise PyCupraLoginFailedException(f'Login failed with error: {jsondata.get("error", None)}')
                        form_data['hmac'] = jsondata.get('hmac', '')
                        post_action = jsondata.get('postAction')
            else:
                raise PyCupraLoginFailedException('Failed to extract login form data')
            form_data['password'] = self._session_auth_password
        except (PyCupraLoginFailedException) as e:
            raise
        except Exception as e:
            raise PyCupraAuthenticationException("Invalid username or service unavailable")

        # POST password
        self._session_auth_headers[client]['Referer'] = pe_url
        self._session_auth_headers[client]['Origin'] = authissuer
        self._LOGGER.debug(f"Finalizing login")

        client_id = CLIENT_LIST[client].get('CLIENT_ID')
        pp_url = authissuer+'/'+post_action
        if not 'signin-service' in pp_url or not client_id in pp_url:
            pp_url = authissuer+'/signin-service/v1/'+client_id+"/"+post_action

        if self._session_fulldebug:
            self._LOGGER.debug(f'Using login action url: "{pp_url}"')
        req = await self._session.post(
            url=pp_url,
            headers=self._session_auth_headers.get(client),
            data = form_data,
            allow_redirects=False
        )
        return req.headers.get('Location', None)

    async def terminate(self) -> None:
        """Log out from connect services"""
        for v in self.vehicles:
            self._LOGGER.debug(self.anonymise(f'Calling stopFirebase() for vehicle {v.vin}'))
            newStatus = await v.stopFirebase()
            if newStatus != FIREBASE_STATUS_NOT_INITIALISED:
                self._LOGGER.debug(self.anonymise(f'stopFirebase() not successful for vehicle {v.vin}'))
                # Although stopFirebase() was not successful, the firebase status is reset to FIREBASE_STATUS_NOT_INITIALISED to allow a new initialisation
                v.firebaseStatus = FIREBASE_STATUS_NOT_INITIALISED
        await self.logout()

    async def logout(self) -> None:
        """Logout, revoke tokens."""
        self._LOGGER.info(f'Initiating logout.')
        self._session_headers.pop('Authorization', None)
        self._session_headers.pop('tokentype', None)
        self._session_headers['Content-Type'] = 'application/x-www-form-urlencoded'

        for client in self._session_tokens:
            # Ignore identity tokens
            for token_type in (
                token_type
                for token_type in self._session_tokens[client]
                if token_type in ['refresh_token', 'access_token']
            ):
                self._session_tokens[client][token_type] = None
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.deleteTokenFile,)

  # HTTP methods to API
    async def get(self, url, vin=''):
        """Perform a HTTP GET."""
        try:
            response = await self._request(METH_GET, url)
            return response
        except aiohttp.client_exceptions.ClientResponseError as error:
            data = {
                'status_code': error.status,
                'error': error.code,
                'error_description': error.message,
                'response_headers': error.headers,
                'request_info': error.request_info
            }
            if error.status == 401:
                self._LOGGER.warning('Received "Unauthorized" while fetching data. This can occur if tokens expired or refresh service is unavailable.')
                if self._error401 != True:
                    self._error401 = True
                    rc=await self.refresh_token(self._session_auth_brand)
                    if rc:
                        self._LOGGER.info('Successfully refreshed tokens after error 401.')
                        self._error401 = False
                        #return True
                    else:
                        self._LOGGER.info('Refresh of tokens after error 401 not successful.')
            elif error.status == 400:
                self._LOGGER.error('Received "Bad Request" from server. The request might be malformed or not implemented correctly for this vehicle.')
            elif error.status == 412:
                self._LOGGER.debug('Received "Pre-condition failed". Service might be temporarily unavailable.')
            elif error.status == 500:
                self._LOGGER.info('Received "Internal server error". The service is temporarily unavailable.')
            elif error.status == 502:
                self._LOGGER.info('Received "Bad gateway". Either the endpoint is temporarily unavailable or not supported for this vehicle.')
            elif 400 <= error.status <= 499:
                self._LOGGER.error('Received unhandled error indicating client-side problem.\nRestart or try again later.')
            elif 500 <= error.status <= 599:
                self._LOGGER.error('Received unhandled error indicating server-side problem.\nThe service might be temporarily unavailable.')
            else:
                self._LOGGER.error('Received unhandled error while requesting API endpoint.')
            self._LOGGER.debug(self.anonymise(f'HTTP request information: {data}'))
            return data
        except Exception as e:
            self._LOGGER.debug(f'Got non HTTP related error: {e}')
            return {
                'error_description': 'Non HTTP related error'
            }

    async def post(self, url, **data):
        """Perform a HTTP POST."""
        if data:
            return await self._request(METH_POST, url, **data)
        else:
            return await self._request(METH_POST, url)

    async def _request(self, method, url, **kwargs):
        """Perform a HTTP query"""
        if self._session_fulldebug:
            argsString =''
            if len(kwargs)>0:
                argsString = 'with '
                for k, val in kwargs.items():
                    argsString = argsString + f"{k}=\'{val}\' " 
            self._LOGGER.debug(self.anonymise(f'HTTP {method} "{url}" {argsString}'))
        try:
            if datetime.now(tz=None).date() != self._sessionRequestTimestamp.date():
                # A new day has begun. Store _sessionRequestCounter in history and reset timestamp and counter
                self._sessionRequestCounterHistory[self._sessionRequestTimestamp.strftime('%Y-%m-%d')]=self._sessionRequestCounter
                self._LOGGER.info(f'History of the number of API calls:')
                for key, value in self._sessionRequestCounterHistory.items():
                    self._LOGGER.info(f'   Date: {key}: {value} API calls')

                self._sessionRequestTimestamp= datetime.now(tz=None)
                self._sessionRequestCounter = 0
        except Exception as e:
            self._LOGGER.error(f'Error while preparing output of API call history. Error: {e}')
        self._sessionRequestCounter = self._sessionRequestCounter + 1
        async with self._session.request(
            method,
            url,
            headers=self._session_headers if (PUBLIC_MODEL_IMAGES_SERVER not in url) else {}, # Set headers to {} when reading from PUBLIC_MODEL_IMAGES_SERVER
            timeout=ClientTimeout(total=TIMEOUT.seconds),
            cookies=self._session_cookies,
            raise_for_status=False,
            **kwargs
        ) as response:
            response.raise_for_status()

            # Update cookie jar
            if self._session_cookies != '':
                self._session_cookies.update(response.cookies)
            else:
                self._session_cookies = response.cookies

            try:
                if response.status == 204:
                    res = {'status_code': response.status}
                elif response.status == 202 and method==METH_PUT:
                    res = response
                elif response.status == 200 and method==METH_DELETE:
                    res = response
                elif 200 <= response.status <= 299:
                    # If this is a revoke token url, expect Content-Length 0 and return
                    if int(response.headers.get('Content-Length', 0)) == 0 and 'revoke' in url:
                        if response.status == 200:
                            return True
                        else:
                            return False
                    else:
                        if 'xml' in response.headers.get('Content-Type', ''):
                            res = xmltodict.parse(await response.text())
                        elif 'image/png'  in response.headers.get('Content-Type', ''):
                            res = await response.content.read()
                        else:
                            res = await response.json(loads=json_loads)
                else:
                    res = {}
                    self._LOGGER.debug(self.anonymise(f'Not success status code [{response.status}] response: {response}'))
                if 'X-RateLimit-Remaining' in response.headers:
                    res['rate_limit_remaining'] = response.headers.get('X-RateLimit-Remaining', '')
            except Exception as e:
                res = {}
                self._LOGGER.debug(self.anonymise(f'Something went wrong [{response.status}] response: {response}, error: {e}'))
                return res

            if self._session_fulldebug:
                if 'image/png'  in response.headers.get('Content-Type', ''):
                    self._LOGGER.debug(self.anonymise(f'Request for "{url}" returned with status code [{response.status}]. Not showing response for Content-Type image/png.'))
                elif method==METH_PUT or method==METH_DELETE:
                    # deepcopy() of res can produce errors, if res is the API response on PUT or DELETE
                    self._LOGGER.debug(f'Request for "{self.anonymise(url)}" returned with status code [{response.status}]. Not showing response for http {method}')
                else:
                    self._LOGGER.debug(self.anonymise(f'Request for "{url}" returned with status code [{response.status}], response: {self.anonymise(deepcopy(res))}'))
            else:
                self._LOGGER.debug(f'Request for "{url}" returned with status code [{response.status}]')
            return res

    async def _data_call(self, query, **data):
        """Function for POST actions with error handling."""
        try:
            response = await self.post(query, **data)
            self._LOGGER.debug(self.anonymise(f'Data call returned: {response}'))
            return response
        except aiohttp.client_exceptions.ClientResponseError as error:
            self._LOGGER.debug(self.anonymise(f'Request failed. Data: {data}, HTTP request headers: {self._session_headers}'))
            if error.status == 401:
                self._LOGGER.error('Unauthorized')
            elif error.status == 400:
                self._LOGGER.error(f'Bad request')
            elif error.status == 429:
                self._LOGGER.warning('Too many requests. Further requests can only be made after the end of next trip in order to protect your vehicles battery.')
                return 429
            elif error.status == 500:
                self._LOGGER.error('Internal server error, server might be temporarily unavailable')
            elif error.status == 502:
                self._LOGGER.error('Bad gateway, this function may not be implemented for this vehicle')
            else:
                self._LOGGER.error(f'Unhandled HTTP exception: {error}')
            #return False
        except Exception as error:
            self._LOGGER.error(f'Failure to execute: {error}')
        return False

  # Class get data functions
    async def update_all(self) -> bool:
        """Update status."""
        try:
            # Get all Vehicle objects and update in parallell
            update_list = []
            for vehicle in self.vehicles:
                if vehicle.vin not in update_list:
                    self._LOGGER.debug(self.anonymise(f'Adding {vehicle.vin} for data refresh'))
                    update_list.append(vehicle.update(updateType=1))
                else:
                    self._LOGGER.debug(self.anonymise(f'VIN {vehicle.vin} is already queued for data refresh'))

            # Wait for all data updates to complete
            if len(update_list) == 0:
                self._LOGGER.info('No vehicles in account to update')
            else:
                self._LOGGER.debug('Calling update function for all vehicles')
                await asyncio.gather(*update_list)
            return True
        except (IOError, OSError, LookupError, Exception) as error:
            self._LOGGER.warning(f'An error was encountered during interaction with the API: {error}')
        except:
            raise
        return False

    async def get_userData(self) -> dict:
        """Fetch user profile."""
        await self.set_token(self._session_auth_brand)
        userData={}
        #API_PERSONAL_DATA provide nearly the same information as API_USER_INFO but a little bit less
        try:
            response = await self.get(API_PERSONAL_DATA.format(userId= self._user_id))
            if response.get('nickname'):
                userData= response
            else:
                self._LOGGER.debug('Could not retrieve profile information')
        except:
            self._LOGGER.debug('Could not fetch personal information.')

        try:
            response = await self.get(API_USER_INFO)
            if response.get('name'):
                userData = response
            else:
                self._LOGGER.debug('Could not retrieve profile information')
        except:
            self._LOGGER.debug('Could not fetch personal information.')
        self._userData=userData
        return userData

    async def get_vehicles(self) -> list:
        """Fetch vehicle information from user profile."""
        api_vehicles = []
        # Check if user needs to update consent
        try:
            await self.set_token(self._session_auth_brand)
            #self._LOGGER.debug('Achtung! getConsentInfo auskommentiert')
            response = await self.get(API_MBB_STATUSDATA.format(userId=self._user_id))
            if response.get('profileCompleted','incomplete'):
                if response.get('profileCompleted',False):
                    self._LOGGER.debug('User consent is valid, no missing information for profile')
                else:
                    self._LOGGER.debug('Profile incomplete. Please visit the web portal')
            else:
                self._LOGGER.debug('Could not retrieve profile information')
            """consent = await self.getConsentInfo()
            if isinstance(consent, dict):
                self._LOGGER.debug(f'Consent returned {consent}')
                if 'status' in consent.get('mandatoryConsentInfo', []):
                    if consent.get('mandatoryConsentInfo', [])['status'] != 'VALID':
                        self._LOGGER.error(f'The user needs to update consent for {consent.get("mandatoryConsentInfo", [])["id"]}. If problems are encountered please visit the web portal first and accept terms and conditions.')
                elif len(consent.get('missingMandatoryFields', [])) > 0:
                    self._LOGGER.error(f'Missing mandatory field for user: {consent.get("missingMandatoryFields", [])[0].get("name", "")}. If problems are encountered please visit the web portal first and accept terms and conditions.')
                else:
                    self._LOGGER.debug('User consent is valid, no missing information for profile')
            else:
                self._LOGGER.debug('Could not retrieve consent information')"""
        except:
            self._LOGGER.debug('Could not fetch consent information. If problems are encountered please visit the web portal first and make sure that no new terms and conditions need to be accepted.')

        # Fetch vehicles
        try:
            legacy_vehicles = await self.get(API_VEHICLES.format(APP_URI=APP_URI, userId=self._user_id))
            if legacy_vehicles.get('vehicles', False):
                self._LOGGER.debug('Found vehicle(s) associated with account.')
                for vehicle in legacy_vehicles.get('vehicles'):
                    vin = vehicle.get('vin', '')
                    self.addToAnonymisationDict(vin,'[VIN_ANONYMISED]')
                    response = await self.get(API_CAPABILITIES.format(APP_URI=APP_URI, userId=self._user_id, vin=vin))
                    #self._session_headers['Accept'] = 'application/json'
                    if response.get('capabilities', False):
                        vehicle["capabilities"]=response.get('capabilities')
                        vehicle["platform"] = response.get('platform', 'MOD3')
                        vehicle["capabilitiesQueriedOn"] = response.get('queriedOn', '')
                    else:
                        self._LOGGER.warning(f"Failed to aquire capabilities information about vehicle with VIN {vehicle}.")
                        if vehicle.get('capabilities',None)!=None:
                            self._LOGGER.warning(f"Keeping the old capability information.")
                        else:
                            self._LOGGER.warning(f"Initialising vehicle without capabilities.")
                            vehicle["capabilities"]=[]
                    response = await self.get(API_CONNECTION.format(APP_URI=APP_URI, vin=vin))
                    #self._session_headers['Accept'] = 'application/json'
                    if response.get('connection', False):
                        vehicle["connectivities"]=response.get('connection')
                    else:
                        self._LOGGER.warning(f"Failed to aquire connection information about vehicle with VIN {vehicle}")
                    api_vehicles.append(vehicle)
        except:
            raise

        # If neither API returns any vehicles, raise an error
        if len(api_vehicles) == 0:
            raise PyCupraConfigException("No vehicles were found for given account!")
        # Get vehicle connectivity information
        else:
            try:
                for vehicle in api_vehicles:
                    self._LOGGER.debug(self.anonymise(f'Checking vehicle {vehicle}'))
                    vin = vehicle.get('vin', '')
                    #for service in vehicle.get('connectivities', []):
                    #    if isinstance(service, str):
                    #        connectivity.append(service)
                    #    elif isinstance(service, dict):
                    #        connectivity.append(service.get('type', ''))

                    properties={}
                    for key in vehicle:
                        if not(key in {'capabilities', 'vin', 'specifications', 'connectivities'}):
                            properties[key]=vehicle.get(key)

                    newVehicle = {
                        'vin': vin,
                        'connectivities': vehicle.get('connectivities'),
                        'capabilities': vehicle.get('capabilities'),
                        'specification': vehicle.get('specifications'),
                        'properties': properties,
                        'logPrefix': self._logPrefix,
                    }
                    # Check if object already exist
                    self._LOGGER.debug(f'Check if vehicle exists')
                    if self.vehicle(vin) is not None:
                        self._LOGGER.debug(self.anonymise(f'Vehicle with VIN number {vin} already exist.'))
                        car = Vehicle(self, newVehicle)
                        if not car == self.vehicle(vin):
                            self._LOGGER.debug(self.anonymise(f'Updating {newVehicle} object'))
                            self._vehicles.remove(self.vehicle(vin))
                            self._vehicles.append(Vehicle(self, newVehicle))
                    else:
                        self._LOGGER.debug(self.anonymise(f'Adding vehicle {vin}, with connectivities: {vehicle.get('connectivities')}'))
                        self._vehicles.append(Vehicle(self, newVehicle))
            except:
                raise PyCupraLoginFailedException("Unable to fetch associated vehicles for account")

        # Update data for all vehicles
        await self.update_all()

        return api_vehicles

 #### API get data functions ####
   # Profile related functions
    #async def getConsentInfo(self):
        """Get consent information for user."""
        """try:
            await self.set_token(self._session_auth_brand)
            atoken = self._session_tokens[self._session_auth_brand]['access_token']
            # Try old pyJWT syntax first
            try:
                subject = jwt.decode(atoken, verify=False).get('sub', None)
            except:
                subject = None
            # Try new pyJWT syntax if old fails
            if subject is None:
                try:
                    exp = jwt.decode(atoken, options={'verify_signature': False}).get('sub', None)
                    subject = exp
                except:
                    raise Exception("Could not extract sub attribute from token")

            data = {'scopeId': 'commonMandatoryFields'}
            response = await self.post(f'https://profileintegrityservice.apps.emea.vwapps.io/iaa/pic/v1/users/{subject}/check-profile', json=data)
            if response.get('mandatoryConsentInfo', False):
                data = {
                    'consentInfo': response
                }
                return data
            elif response.get('status_code', {}):
                self._LOGGER.warning(f'Could not fetch realCarData, HTTP status code: {response.get("status_code")}')
            else:
                self._LOGGER.info('Unhandled error while trying to fetch consent information')
        except Exception as error:
            self._LOGGER.debug(f'Could not get consent information, error {error}')
        return False"""

    async def getCapabilities(self, vin, baseurl) -> dict | bool:
        """Get capabilities information."""
        await self.set_token(self._session_auth_brand)
        data={}
        try:
            response = await self.get(API_CAPABILITIES.format(APP_URI=baseurl, userId=self._user_id, vin=vin))
            if response.get('capabilities', False):
                data["capabilities"]=response.get('capabilities')
                data["platform"] = response.get('platform', 'MOD3')
                data["capabilitiesQueriedOn"] = response.get('queriedOn', '')
            elif response.get('status_code', {}):
                self._LOGGER.warning(f'Could not fetch capabilities information, HTTP status code: {response.get("status_code")}')
            else:
                self._LOGGER.info('Unhandled error while trying to fetch capabilities information')
        except Exception as error:
            self._LOGGER.warning(f'Could not fetch capabilities information, error: {error}')
        if data=={}:
            return False
        return data

    async def getConnectivities(self, vin, baseurl) -> dict | bool:
        """Get capabilities information."""
        await self.set_token(self._session_auth_brand)
        data={}
        try:
            response = await self.get(API_CONNECTION.format(APP_URI=baseurl, vin=vin))
            if response.get('connection', False):
                data=response
            elif response.get('status_code', {}):
                self._LOGGER.warning(f'Could not fetch connection information, HTTP status code: {response.get("status_code")}')
            else:
                self._LOGGER.info('Unhandled error while trying to fetch connection information')
        except Exception as error:
            self._LOGGER.warning(f'Could not fetch connection information, error: {error}')
        if data=={}:
            return False
        return data

    async def getBasicCarData(self, vin, baseurl) -> dict | bool:
        """Get car information from customer profile, VIN, nickname, etc."""
        await self.set_token(self._session_auth_brand)
        data={}
        try:
            response = await self.get(API_MYCAR.format(baseurl=baseurl, userId=self._user_id, vin=vin))
            if response.get('engines', {}):
                data['mycar']= response
            elif response.get('status_code', {}):
                self._LOGGER.warning(f'Could not fetch vehicle mycar report, HTTP status code: {response.get("status_code")}')
            else:
                self._LOGGER.info('Unhandled error while trying to fetch mycar data')
        except Exception as error:
            self._LOGGER.warning(f'Could not fetch mycar report, error: {error}')
        if data=={}:
            return False
        return data

    async def getRanges(self, vin, baseurl) -> dict | bool:
        """Get range information"""
        await self.set_token(self._session_auth_brand)
        data={}
        try:
            response = await self.get(API_RANGES.format(baseurl=baseurl, vin=vin))
            if response.get('ranges', {}):
                data['ranges']= response.get('ranges', {})
            elif response.get('status_code', {}):
                self._LOGGER.warning(f'Could not fetch range information, HTTP status code: {response.get("status_code")}')
            else:
                self._LOGGER.info('Unhandled error while trying to fetch range data')
        except Exception as error:
            self._LOGGER.warning(f'Could not fetch range data, error: {error}')
        if data=={}:
            return False
        return data

    async def getMileage(self, vin, baseurl) -> dict | bool:
        """Get car information from customer profile, VIN, nickname, etc."""
        await self.set_token(self._session_auth_brand)
        data={}
        try:
            response = await self.get(API_MILEAGE.format(baseurl=baseurl, vin=vin))
            if response.get('mileageKm', {}):
                data['mileage'] = response
            elif response.get('status_code', {}):
                self._LOGGER.warning(f'Could not fetch mileage information, HTTP status code: {response.get("status_code")}')
            else:
                self._LOGGER.info('Unhandled error while trying to fetch mileage information')
        except Exception as error:
            self._LOGGER.warning(f'Could not fetch mileage information, error: {error}')
        if data=={}:
            return False
        return data

    async def getVehicleHealthWarnings(self, vin, baseurl) -> dict | bool:
        """Get car information from customer profile, VIN, nickname, etc."""
        await self.set_token(self._session_auth_brand)
        data={}
        try:
            response = await self.get(API_WARNINGLIGHTS.format(baseurl=baseurl, vin=vin))
            if 'statuses' in response:
                data['warninglights'] = response
            elif response.get('status_code', {}):
                self._LOGGER.warning(f'Could not fetch warnlights, HTTP status code: {response.get("status_code")}')
            else:
                self._LOGGER.info('Unhandled error while trying to fetch warnlights')
        except Exception as error:
            self._LOGGER.warning(f'Could not fetch warnlights, error: {error}')
        if data=={}:
            return False
        return data

    #async def getOperationList(self, vin, baseurl):
        """Collect operationlist for VIN, supported/licensed functions."""
        """try:
            #await self.set_token('vwg')
            response = await self.get(f'{baseurl}/api/rolesrights/operationlist/v3/vehicles/{vin}')
            if response.get('operationList', False):
                data = response.get('operationList', {})
            elif response.get('status_code', {}):
                self._LOGGER.warning(f'Could not fetch operation list, HTTP status code: {response.get("status_code")}')
                data = response
            else:
                self._LOGGER.info(f'Could not fetch operation list: {response}')
                data = {'error': 'unknown'}
        except Exception as error:
            self._LOGGER.warning(f'Could not fetch operation list, error: {error}')
            data = {'error': 'unknown'}
        return data"""

    async def getModelImageURL(self, vin, baseurl) -> dict | None:
        """Construct the URL for the model image."""
        await self.set_token(self._session_auth_brand)
        try:
            try:
                response = await self.get(
                    url=API_IMAGE.format(baseurl=baseurl, vin=vin),
                )
                if response.get('front',False):
                    images: dict[str, str] ={}
                    for pos in {"front", "side", "top", "rear", "rbcFront", "rbcCable"}:
                        if pos in response:
                            pic = await self._request(
                                METH_GET,
                                url=response.get(pos,False),
                            )
                            if len(pic)>0:
                                loop = asyncio.get_running_loop()
                                await loop.run_in_executor(None, self.writeImageFile, pos,pic, images, vin)
                            if pos=='front':
                                # Crop the front image to a square format
                                try:
                                    im= Image.open(BytesIO(pic))
                                    width, height = im.size
                                    if height>width:
                                        width, height = height, width
                                    # Setting the points for cropped image
                                    left = (width-height)/2
                                    top = 0
                                    right = height+(width-height)/2
                                    bottom = height
                                    # Cropped image of above dimension
                                    im1 = im.crop((left, top, right, bottom))
                                    byteIO = BytesIO()
                                    im1.save(byteIO, format='PNG')
                                    await loop.run_in_executor(None, self.writeImageFile, pos+'_cropped',byteIO.getvalue(), images, vin)
                                except:
                                    self._LOGGER.warning('Cropping front image to square format failed.')
 
                    self._LOGGER.debug('Read images from web site and wrote them to file.')
                    response['images']=images
                    return response
                else:
                    self._LOGGER.debug(f'Could not fetch Model image URL, request returned with status code {response.status_code}')
            except:
                self._LOGGER.debug('Could not fetch Model image URL')
        except:
            self._LOGGER.debug('Could not fetch Model image URL, message signing failed.')
        return None

    async def getVehicleStatusReport(self, vin, baseurl) -> dict | bool:
        """Get stored vehicle status report (Connect services)."""
        data={}
        await self.set_token(self._session_auth_brand)
        try:
            response = await self.get(API_STATUS.format(baseurl=baseurl, vin=vin))
            if response.get('doors', False):
                data['status']= response
            elif response.get('status_code', {}):
                self._LOGGER.warning(f'Could not fetch vehicle status report, HTTP status code: {response.get("status_code")}')
            else:
                self._LOGGER.info('Unhandled error while trying to fetch status data')
        except Exception as error:
            self._LOGGER.warning(f'Could not fetch status report, error: {error}')
        if data=={}:
            return False
        return data

    async def getMaintenance(self, vin, baseurl) -> dict | bool:
        """Get stored vehicle status report (Connect services)."""
        data={}
        await self.set_token(self._session_auth_brand)
        try:
            response = await self.get(API_MAINTENANCE.format(baseurl=baseurl, vin=vin))
            if response.get('inspectionDueDays', {}):
                data['maintenance'] = response
            elif response.get('status_code', {}):
                self._LOGGER.warning(f'Could not fetch maintenance information, HTTP status code: {response.get("status_code")}')
            else:
                self._LOGGER.info('Unhandled error while trying to fetch maintenance information')
        except Exception as error:
            self._LOGGER.warning(f'Could not fetch maintenance information, error: {error}')
        if data=={}:
            return False
        return data

    async def getTripStatisticsV1(self, vin, baseurl) -> dict | bool:
        """Get short term trip statistics, if V1 works."""
        await self.set_token(self._session_auth_brand)
        try:
            data: dict[str, dict] ={'tripstatistics': {}} 
            dataType='SHORT'
            response = await self.get(API_TRIP_V1.format(baseurl=baseurl, vin=vin, dataType=dataType))
            if response.get('data',{}):
                self._LOGGER.info('The old trip statistics endpoint is online!!!')
                data['tripstatistics']['oldshort']= response.get('data',{})
            elif response.get('status_code', {}):
                self._LOGGER.warning(f'Could not fetch trip statistics, HTTP status code: {response.get("status_code")}')
            else:
                self._LOGGER.info(f'Unhandled error while trying to fetch trip statistics')
            if data.get('tripstatistics',{}) != {}:
                return data
        except Exception as error:
            self._LOGGER.warning(f'Could not fetch trip statistics from v1 endpoint, error: {error}')
        return False

    async def getTripStatistics(self, vin, baseurl, supportsCyclicTrips) -> dict | bool:
        """Get short term and cyclic trip statistics."""
        await self.set_token(self._session_auth_brand)
        if self._session_tripStatisticsStartDate==None:
            # If connection was not initialised with parameter tripStatisticsStartDate, then 330 day is used for the CYCLIC trips and 25 days for the SHORT trips
            # (This keeps the statistics shorter in Home Assistant)
            startDate = (datetime.now() - timedelta(days= 330)).strftime('%Y-%m-01') # startDate should be the first day of a month when data granularity level is month 
        else:
            startDate = self._session_tripStatisticsStartDate
        try:
            data: dict[str, dict] ={'tripstatistics': {}} 
            endDateTime = datetime.now().strftime('%Y-%m-%dT23:59:59Z')
            if supportsCyclicTrips:
                #dataType='CYCLIC'
                #response = await self.get(API_TRIP.format(baseurl=baseurl, vin=vin, dataType=dataType, startDate=startDate))
                response = await self.get(API_TRIP.format(baseurl=baseurl, vin=vin, startDate=startDate, endDateTime= endDateTime))
                if response.get('data',{}).get('dailySummary', []):
                    data['tripstatistics']['cyclic']= response.get('data',{}).get('dailySummary', [])
                elif response.get('status_code', {}):
                    self._LOGGER.warning(f'Could not fetch trip statistics, HTTP status code: {response.get("status_code")}')
                else:
                    self._LOGGER.info(f'Unhandled error while trying to fetch trip statistics')
            else:
                self._LOGGER.info(f'Vehicle does not support cyclic trips.')
            #dataType='SHORT'
            if self._session_tripStatisticsStartDate==None:
                # If connection was not initialised with parameter tripStatisticsStartDate, then 330 day is used for the CYCLIC trips and 25 days for the SHORT trips
                # (This keeps the statistics shorter in Home Assistant)
                startDate = (datetime.now() - timedelta(days= 25)).strftime('%Y-%m-%d')
            #response = await self.get(API_TRIP.format(baseurl=baseurl, vin=vin, dataType=dataType, startDate=startDate))
            response = await self.get(API_TRIP.format(baseurl=baseurl, vin=vin, startDate=startDate, endDateTime= endDateTime))
            if response.get('data',{}).get('dailySummary', []):
                data['tripstatistics']['short']= response.get('data',{}).get('dailySummary', [])
            elif response.get('status_code', {}):
                self._LOGGER.warning(f'Could not fetch trip statistics, HTTP status code: {response.get("status_code")}')
            else:
                self._LOGGER.info(f'Unhandled error while trying to fetch trip statistics')
            if data.get('tripstatistics',{}) != {}:
                data['tripstatistics']['dailySums'] = convertTripStatisticsData(data.get('tripstatistics',{}).get('short',{}))
                data['tripstatistics']['monthlySums'] = convertTripStatisticsData(data.get('tripstatistics',{}).get('cyclic',{}))
                if self.updateDailySumTripStatistics(data, vin):
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, self.writeSumTripStatisticsFile, self.vehicle(vin), SUMTYPE_DAILY)
                if self.updateMonthlySumTripStatistics(data, vin):
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, self.writeSumTripStatisticsFile, self.vehicle(vin), SUMTYPE_MONTHLY)
                return data
        except Exception as error:
            self._LOGGER.warning(f'Could not fetch trip statistics, error: {error}')
        return False

    async def getPosition(self, vin, baseurl) -> dict | bool:
        """Get position data."""
        await self.set_token(self._session_auth_brand)
        try:
            response = await self.get(API_POSITION.format(baseurl=baseurl, vin=vin))
            if response.get('lat', {}):
                data = {
                    'findCarResponse': response,
                    'isMoving': False
                }
                if hasattr(self, '_googleApiKey'):
                    apiKeyForGoogle= self._googleApiKey
                    lat= response.get('lat', 0)
                    lon= response.get('lon', 0)
                    response = await self.get(API_POS_TO_ADDRESS.format(lat=lat, lon=lon, apiKeyForGoogle=apiKeyForGoogle))
                    if response.get('routes', []):
                        if response.get('routes', [])[0].get('legs', False):
                            data['findCarResponse']['position_to_address'] = response.get('routes', [])[0].get('legs',[])[0].get('start_address','')
                return data
            elif response.get('status_code', {}):
                if response.get('status_code', 0) == 204:
                    self._LOGGER.debug(f'Seems car is moving, HTTP 204 received from position')
                    data = {
                        'isMoving': True,
                        #'rate_limit_remaining': 15
                    }
                    return data
                else:
                    self._LOGGER.warning(f'Could not fetch position, HTTP status code: {response.get("status_code")}')
            else:
                self._LOGGER.info('Unhandled error while trying to fetch positional data')
        except Exception as error:
            self._LOGGER.warning(f'Could not fetch position, error: {error}')
        return False

    async def getClimatisationtimer(self, vin, baseurl) -> dict | bool:
        """Get climatisation timers."""
        await self.set_token(self._session_auth_brand)
        try:
            response = await self.get(API_CLIMATISATION_TIMERS.format(baseurl=baseurl, vin=vin))
            if response.get('timers', 0)!=0: #check if element 'timers' present, even if empty
                data={}
                data['climatisationTimers'] = response
                return data
            elif response.get('status_code', {}):
                self._LOGGER.warning(f'Could not fetch climatisation timers, HTTP status code: {response.get("status_code")}')
            else:
                self._LOGGER.info('Unknown error while trying to fetch data for climatisation timers')
        except Exception as error:
            self._LOGGER.warning(f'Could not fetch climatisation timers, error: {error}')
        return False

    async def getDeparturetimer(self, vin, baseurl) -> dict | bool:
        """Get departure timers."""
        await self.set_token(self._session_auth_brand)
        try:
            response = await self.get(API_DEPARTURE_TIMERS.format(baseurl=baseurl, vin=vin))
            if response.get('timers', {}):
                data={}
                data['departureTimers'] = response
                return data
            elif response.get('status_code', {}):
                self._LOGGER.warning(f'Could not fetch departure timers, HTTP status code: {response.get("status_code")}')
            else:
                self._LOGGER.info('Unknown error while trying to fetch data for departure timers')
        except Exception as error:
            self._LOGGER.warning(f'Could not fetch departure timers, error: {error}')
        return False

    async def getDepartureprofiles(self, vin, baseurl) -> dict | bool:
        """Get departure timers."""
        await self.set_token(self._session_auth_brand)
        try:
            response = await self.get(API_DEPARTURE_PROFILES.format(baseurl=baseurl, vin=vin))
            if response.get('timers', {}):
                for e in range(len(response.get('timers', []))):
                    if response['timers'][e].get('singleTimer','')==None:
                        response['timers'][e].pop('singleTimer')
                    if response['timers'][e].get('recurringTimer','')==None:
                        response['timers'][e].pop('recurringTimer')
                data={}
                data['departureProfiles'] = response
                return data
            elif response.get('status_code', {}):
                self._LOGGER.warning(f'Could not fetch departure profiles, HTTP status code: {response.get("status_code")}')
            else:
                self._LOGGER.info('Unknown error while trying to fetch data for departure profiles')
        except Exception as error:
            self._LOGGER.warning(f'Could not fetch departure profiles, error: {error}')
        return False

    async def getClimater(self, vin, baseurl, oldClimatingData) -> dict | bool:
        """Get climatisation data."""
        #data={}
        #data['climater']={}
        data = {'climater': oldClimatingData}
        await self.set_token(self._session_auth_brand)
        try:
            response = await self.get(API_CLIMATER_STATUS.format(baseurl=baseurl, vin=vin))
            if response.get('climatisationStatus', {}) or response.get('auxiliaryHeatingStatus', {}):
                data['climater']['status']=response
            elif response.get('status_code', {}):
                self._LOGGER.warning(f'Could not fetch climatisation status, HTTP status code: {response.get("status_code")}')
            else:
                self._LOGGER.info('Unhandled error while trying to fetch climatisation status')
        except Exception as error:
            self._LOGGER.warning(f'Could not fetch climatisation status, error: {error}')
        try:
            response = await self.get((API_CLIMATER+'/settings').format(baseurl=baseurl, vin=vin))
            if response.get('targetTemperatureInCelsius', {}):
                data['climater']['settings']=response
            elif response.get('status_code', {}):
                self._LOGGER.warning(f'Could not fetch climatisation settings, HTTP status code: {response.get("status_code")}')
            elif response.get('carCapturedTimestamp', {}):
                self._LOGGER.info('API returned no climatisation settings for the vehicle, just a timestamp')
            else:
                self._LOGGER.info('Unhandled error while trying to fetch climatisation settings')
        except Exception as error:
            self._LOGGER.warning(f'Could not fetch climatisation settings, error: {error}')
        if data['climater']=={}:
            return False
        return data

    async def getCharger(self, vin, baseurl, oldChargingData, chargingProfilesActivated) -> dict | bool:
        """Get charger data."""
        await self.set_token(self._session_auth_brand)
        try:
            chargingStatus = {}
            chargingInfo = {}
            #chargingModes = {}
            chargingProfiles = {}
            response = await self.get((API_CHARGING+'/status').format(baseurl=baseurl, vin=vin))
            if response.get('battery', {}):
                chargingStatus = response
            elif response.get('status_code', {}):
                self._LOGGER.warning(f'Could not fetch charging status, HTTP status code: {response.get("status_code")}')
            else:
                self._LOGGER.info('Unhandled error while trying to fetch charging status')
            response = await self.get((API_CHARGING+'/info').format(baseurl=baseurl, vin=vin))
            if response.get('settings', {}):
                chargingInfo = response
            elif response.get('status_code', {}):
                self._LOGGER.warning(f'Could not fetch charging info, HTTP status code: {response.get("status_code")}')
            else:
                self._LOGGER.info('Unhandled error while trying to fetch charging info')
            """response = await self.get((API_CHARGING+'/modes').format(baseurl=baseurl, vin=vin))
            if response.get('battery', {}):
                chargingModes = response
            elif response.get('status_code', {}):
                self._LOGGER.warning(f'Could not fetch charging modes, HTTP status code: {response.get("status_code")}')
            else:
                self._LOGGER.info('Unhandled error while trying to fetch charging modes')"""
            if chargingProfilesActivated:
                response = await self.get(API_CHARGING_PROFILES.format(baseurl=baseurl, vin=vin))
                if response.get('profiles', 0)!=0:
                    chargingProfiles = response
                elif response.get('status_code', {}):
                    self._LOGGER.warning(f'Could not fetch charging profiles, HTTP status code: {response.get("status_code")}')
                else:
                    self._LOGGER.info('Unhandled error while trying to fetch charging profiles')
            data = {'charging': oldChargingData}
            if chargingStatus != {}:
                data['charging']['status'] = chargingStatus
            else:
                self._LOGGER.warning(f'getCharger() got no valid data for charging status')
            if chargingInfo != {}:
                data['charging']['info'] = chargingInfo
            else:
                self._LOGGER.warning(f'getCharger() got no valid data for charging info')
            #if chargingModes != {}:
            #    data['charging']['modes'] = chargingModes
            #else:
            #    self._LOGGER.warning(f'getCharger() got no valid data for charging modes')
            if chargingProfiles != {}:
                data['charging']['profiles'] = chargingProfiles
            else:
                if chargingProfilesActivated:
                    self._LOGGER.warning(f'getCharger() got no valid data for charging profiles')
            return data
        except Exception as error:
            self._LOGGER.warning(f'Could not fetch charger, error: {error}')
        return False

    async def getPreHeater(self, vin, baseurl) -> dict | bool:
        """Get parking heater data."""
        await self.set_token(self._session_auth_brand)
        try:
            response = await self.get(f"f'URL_not_yet_known'")
            if response.get('statusResponse', {}):
                data = {'heating': response.get('statusResponse', {})}
                return data
            elif response.get('status_code', {}):
                self._LOGGER.warning(f'Could not fetch pre-heating, HTTP status code: {response.get("status_code")}')
            else:
                self._LOGGER.info('Unhandled error while trying to fetch pre-heating data')
        except Exception as error:
            self._LOGGER.warning(f'Could not fetch pre-heating, error: {error}')
        return False

 #### API data set functions ####
    async def get_sec_token(self, spin, baseurl) -> str:
        """Get a security token, required for certain set functions."""
        data = {'spin': spin}
        url = API_SECTOKEN.format(baseurl=baseurl, userId=self._user_id)
        response = await self.post(url, json=data, allow_redirects=True)
        if response.get('securityToken', False):
            return response['securityToken']
        else:
            raise PyCupraException('Did not receive a valid security token. Maybewrong SPIN?' )

    async def _setViaAPI(self, endpoint, **data) -> dict | bool:
        """Data call to API to set a value or to start an action."""
        await self.set_token(self._session_auth_brand)
        try:
            url = endpoint 
            response = await self._data_call(url, **data)
            if not response:
                raise PyCupraException(f'Invalid or no response for endpoint {endpoint}')
            elif response == 429:
                raise PyCupraThrottledException('Action rate limit reached. Start the car to reset the action limit')
            else:
                data = {'id': '', 'state' : ''}
                if 'requestId' in response:
                    data['state'] = 'Request accepted'
                for key in response:
                    if isinstance(response.get(key), dict):
                        for k in response.get(key):
                            if 'id' in k.lower():
                                data['id'] = str(response.get(key).get(k))
                            if 'state' in k.lower():
                                data['state'] = response.get(key).get(k)
                    else:
                        if 'Id' in key or 'id' in key:
                            data['id'] = str(response.get(key))
                        if 'State' in key:
                            data['state'] = response.get(key)
                if response.get('rate_limit_remaining', False):
                    data['rate_limit_remaining'] = response.get('rate_limit_remaining', None)
                return data
        except:
            raise
        return False

    async def _setViaPUTtoAPI(self, endpoint, **data) -> dict | bool:
        """PUT call to API to set a value or to start an action."""
        await self.set_token(self._session_auth_brand)
        try:
            url = endpoint 
            response = await self._request(METH_PUT,url, **data)
            if not response:
                raise PyCupraException(f'Invalid or no response for endpoint {endpoint}')
            elif response == 429:
                raise PyCupraThrottledException('Action rate limit reached. Start the car to reset the action limit')
            else:
                data = {'id': '', 'state' : ''}
                if 'requestId' in response:
                    data['state'] = 'Request accepted'
                for key in response:
                    if isinstance(response.get(key), dict):
                        for k in response.get(key):
                            if 'id' in k.lower():
                                data['id'] = str(response.get(key).get(k))
                            if 'state' in k.lower():
                                data['state'] = response.get(key).get(k)
                    else:
                        if 'Id' in key:
                            data['id'] = str(response.get(key))
                        if 'State' in key:
                            data['state'] = response.get(key)
                if response.get('rate_limit_remaining', False):
                    data['rate_limit_remaining'] = response.get('rate_limit_remaining', None)
                return data
        except:
            raise
        return False

    async def subscribe(self, vin, credentials) -> dict | bool:
        url = f'{APP_URI}/v2/subscriptions'
        deviceId = credentials.get('gcm',{}).get('app_id','')
        token = credentials.get('fcm',{}).get('registration',{}).get('token','')

        data = {
            "deviceId": deviceId, 
            "locale":"en_GB",
            "services":{"charging":True,"climatisation":True},
            "token": token, 
            "userId": self._user_id, 
            "vin":vin
            }
        return await self._setViaAPI(url, json=data)

    async def deleteSubscription(self, credentials):
        await self.set_token(self._session_auth_brand)
        try:
            id = credentials.get('subscription',{}).get('id','')
            url = f'{APP_URI}/v1/subscriptions/{id}'
            response = await self._request(METH_DELETE, url)
            if response.status==200: 
                self._LOGGER.debug(f'Subscription {id} successfully deleted.')
                return response
            else:
                self._LOGGER.debug(f'API did not successfully delete subscription.')
                raise PyCupraException(f'Invalid or no response for endpoint {url}')
                return response
        except aiohttp.client_exceptions.ClientResponseError as error:
            self._LOGGER.debug(f'Request failed. Id: {id}, HTTP request headers: {self._session_headers}')
            if error.status == 401:
                self._LOGGER.error('Unauthorized')
            elif error.status == 400:
                self._LOGGER.error(f'Bad request')
            elif error.status == 429:
                self._LOGGER.warning('Too many requests. Further requests can only be made after the end of next trip in order to protect your vehicles battery.')
                return 429
            elif error.status == 500:
                self._LOGGER.error('Internal server error, server might be temporarily unavailable')
            elif error.status == 502:
                self._LOGGER.error('Bad gateway, this function may not be implemented for this vehicle')
            else:
                self._LOGGER.error(f'Unhandled HTTP exception: {error}')
            #return False
        except Exception as error:
            self._LOGGER.error(f'Error: {error}')
            raise
        return False

    async def setCharger(self, vin, baseurl, mode, data) -> dict | bool:
        """Start/Stop charger or change settings."""
        if mode in {'start', 'stop'}:
            capability='charging'
            return await self._setViaAPI((API_REQUESTS+'/{mode}').format(baseurl=baseurl, vin=vin, capability=capability, mode=mode))
        elif mode=='settings':
            return await self._setViaAPI((API_CHARGING+"/{mode}").format(baseurl=baseurl, vin=vin, mode=mode), json=data)
        elif mode=='update-settings' or mode=='update-battery-care':
            capability='charging'
            return await self._setViaAPI((API_ACTIONS+'/{mode}').format(baseurl=baseurl, vin=vin, capability=capability, mode=mode), json=data)
        else:
            self._LOGGER.error(f'Not yet implemented. Mode: {mode}. Command ignored')
            raise

    async def setClimater(self, vin, baseurl, mode, data, spin) -> dict | bool:
        """Execute climatisation actions."""
        try:
            # Only get security token if auxiliary heater is to be started
            if data.get('action', {}).get('settings', {}).get('heaterSource', None) == 'auxiliary':
                self._LOGGER.error(f'This action is not yet implemented: {data.get('action', {}).get('settings', {}).get('heaterSource', None)}. Command ignored')
                #self._session_headers['X-securityToken'] = await self.get_sec_token(vin=vin, spin=spin, action='rclima', baseurl=baseurl)
                pass
            if mode == "stop": # Stop climatisation
                capability='climatisation'
                return await self._setViaAPI((API_REQUESTS+'/stop').format(baseurl=baseurl, vin=vin, capability=capability))
            elif mode == "settings": # Set target temperature
                capability='climatisation'
                return await self._setViaAPI((API_CLIMATER+'/settings').format(baseurl=baseurl, vin=vin), json=data)
            elif mode == "windowHeater stop": # Stop window heater
                capability='windowheating'
                return await self._setViaAPI((API_REQUESTS+'/stop').format(baseurl=baseurl, vin=vin, capability=capability))
            elif mode == "windowHeater start": # Stop window heater
                capability='windowheating'
                return await self._setViaAPI((API_REQUESTS+'/start').format(baseurl=baseurl, vin=vin, capability=capability))
            elif mode == "start": # Start climatisation
                return await self._setViaAPI((API_CLIMATER+'/start').format(baseurl=baseurl, vin=vin), json = data)
            elif mode == "auxiliary_start": # Start auxiliary climatisation
                # Fetch security token 
                self._session_headers['SecToken']= await self.get_sec_token(spin=spin, baseurl=baseurl)
                response = await self._setViaAPI((API_AUXILIARYHEATING+'/start').format(baseurl=baseurl, vin=vin), json = data)
                # Clean up headers
                self._session_headers.pop('SecToken')
                return response
            elif mode == "auxiliary_stop": # Stop auxiliary climatisation
                return await self._setViaAPI((API_AUXILIARYHEATING+'/stop').format(baseurl=baseurl, vin=vin))
            else: # Unknown modes
                self._LOGGER.error(f'Unbekannter setClimater mode: {mode}. Command ignored')
                return False
        except:
            raise
        return False

    async def setClimatisationtimer(self, vin, baseurl, data) -> dict | bool:
        """Set climatisation timers."""
        try:
            capability = 'climatisation'
            url= (API_REQUESTS+'/timers').format(baseurl=baseurl, vin=vin, capability=capability)
            return await self._setViaPUTtoAPI(url, json = data)
        except:
            raise
        return False

    async def setAuxiliaryheatingtimer(self, vin, baseurl, data, spin) -> dict | bool:
        """Set climatisation timers."""
        try:
            capability = 'auxiliary-heating'
            url= (API_AUXILIARYHEATING+'/timers').format(baseurl=baseurl, vin=vin)
            
            # Fetch security token 
            self._session_headers['SecToken']= await self.get_sec_token(spin=spin, baseurl=baseurl)

            response = await self._setViaAPI(url, json = data)
            
            # Clean up headers
            self._session_headers.pop('SecToken')
            
            return response
        except:
            raise
        return False

    async def setDeparturetimer(self, vin, baseurl, data, spin) -> dict | bool:
        """Set departure timers."""
        try:
            url= API_DEPARTURE_TIMERS.format(baseurl=baseurl, vin=vin)
            if data:
                if data.get('minSocPercentage',False):
                    url=url+'/settings'
            return await self._setViaAPI(url, json = data)
        except:
            raise
        return False

    async def setDepartureprofile(self, vin, baseurl, data, spin) -> dict | bool:
        """Set departure profiles."""
        try:
            url= API_DEPARTURE_PROFILES.format(baseurl=baseurl, vin=vin)
            #if data:
                #if data.get('minSocPercentage',False):
                #    url=url+'/settings'
            return await self._setViaPUTtoAPI(url, json = data)
        except:
            raise
        return False

    async def sendDestination(self, vin, baseurl, data, spin):
        """Send destination to vehicle."""

        await self.set_token(self._session_auth_brand)
        try:
            url= API_DESTINATION.format(baseurl=baseurl, vin=vin)
            response = await self._request(METH_PUT, url, json=data)
            if response.status==202: #[202 Accepted]
                self._LOGGER.debug(f'Destination {data[0]} successfully sent to API.')
                return response
            else:
                self._LOGGER.debug(f'API did not successfully receive destination.')
                raise PyCupraException(f'Invalid or no response for endpoint {url}')
                return response
        except aiohttp.client_exceptions.ClientResponseError as error:
            self._LOGGER.debug(f'Request failed. Data: {data}, HTTP request headers: {self._session_headers}')
            if error.status == 401:
                self._LOGGER.error('Unauthorized')
            elif error.status == 400:
                self._LOGGER.error(f'Bad request')
            elif error.status == 429:
                self._LOGGER.warning('Too many requests. Further requests can only be made after the end of next trip in order to protect your vehicles battery.')
                return 429
            elif error.status == 500:
                self._LOGGER.error('Internal server error, server might be temporarily unavailable')
            elif error.status == 502:
                self._LOGGER.error('Bad gateway, this function may not be implemented for this vehicle')
            else:
                self._LOGGER.error(f'Unhandled HTTP exception: {error}')
            #return False
        except Exception as error:
            self._LOGGER.error(f'Error: {error}')
            raise
        return False

    async def setHonkAndFlash(self, vin, baseurl, data) -> dict | bool:
        """Execute honk and flash actions."""
        return await self._setViaAPI(API_HONK_AND_FLASH.format(baseurl=baseurl, vin=vin), json = data)

    async def setLock(self, vin, baseurl, action, spin) -> dict | bool:
        """Remote lock and unlock actions."""
        try:
            # Fetch security token 
            self._session_headers['SecToken']= await self.get_sec_token(spin=spin, baseurl=baseurl)

            response = await self._setViaAPI(API_ACCESS.format(baseurl=baseurl, vin=vin, action=action))

            # Clean up headers
            self._session_headers.pop('SecToken')

            return response

        except:
            self._session_headers.pop('SecToken')
            raise
        return False

    async def setPreHeater(self, vin, baseurl, data, spin) -> dict | bool:
        """Petrol/diesel parking heater actions."""
        try:
            # Fetch security token 
            self._session_headers['SecToken']= await self.get_sec_token(spin=spin, baseurl=baseurl)

            response = await self._setViaAPI(f"f'url_not_yet_known'", json = data)

            # Clean up headers
            self._session_headers.pop('SecToken')

            return response

        except:
            self._session_headers.pop('SecToken')
            raise
        return False

    async def setRefresh(self, vin, baseurl) -> dict | bool:
        """"Force vehicle data update."""
        return await self._setViaAPI(API_REFRESH.format(baseurl=baseurl, vin=vin))

 #### Token handling ####
    async def validate_token(self, token) -> datetime:
        """Function to validate a single token."""
        try:
            now = datetime.now()
            # Try old pyJWT syntax first
            try:
                exp = jwt.decode(token, verify=False).get('exp', None)
            except:
                exp = None
            # Try new pyJWT syntax if old fails
            if exp is None:
                try:
                    exp = jwt.decode(token, options={'verify_signature': False}).get('exp', None)
                except:
                    raise Exception("Could not extract exp attribute")

            expires = datetime.fromtimestamp(int(exp))

            # Lazy check but it's very inprobable that the token expires the very second we want to use it
            if expires > now:
                return expires
            else:
                self._LOGGER.debug(f'Token expired at {expires.strftime("%Y-%m-%d %H:%M:%S")}')
                return datetime.min # Return value datetime.min means that the token is not valid
        except Exception as e:
            self._LOGGER.info(f'Token validation failed, {e}')
        return datetime.min # Return value datetime.min means that the token is not valid

    async def verify_token(self, token) -> bool:
        """Function to verify a single token."""
        try:
            req = None
            # Try old pyJWT syntax first
            try:
                aud = jwt.decode(token, verify=False).get('aud', None)
            except:
                aud = None
            # Try new pyJWT syntax if old fails
            if aud is None:
                try:
                    aud = jwt.decode(token, options={'verify_signature': False}).get('aud', None)
                except:
                    raise Exception("Could not extract exp attribute")

            if not isinstance(aud, str):
                aud = next(iter(aud))
            self._LOGGER.debug(f"Verifying token for {aud}")
            # If audience indicates a client from https://identity.vwgroup.io
            for client in CLIENT_LIST:
                if self._session_fulldebug:
                    self._LOGGER.debug(f"Matching {aud} against {CLIENT_LIST[client].get('CLIENT_ID', '')}")
                if aud == CLIENT_LIST[client].get('CLIENT_ID', ''):
                    req = await self._session.get(url = AUTH_TOKENKEYS)
                    break
            if req == None:
                return False
            
            # Fetch key list
            keys = await req.json()
            pubkeys = {}
            # Convert all RSA keys and store in list
            for jwk in keys['keys']:
                kid = jwk['kid']
                if jwk['kty'] == 'RSA':
                    pubkeys[kid] = jwt.algorithms.RSAAlgorithm.from_jwk(to_json(jwk))
            # Get key ID from token and get match from key list
            token_kid = jwt.get_unverified_header(token)['kid']
            if self._session_fulldebug:
                try:
                    self._LOGGER.debug(f'Token Key ID is {token_kid}, match from public keys: {keys["keys"][token_kid]}')
                except:
                    pass
            pubkey = pubkeys[token_kid]

            # Verify token with public key
            if jwt.decode(token, key=pubkey, algorithms=['RS256'], audience=aud):
                return True
        except ExpiredSignatureError:
            return False
        except Exception as error:
            self._LOGGER.debug(f'Failed to verify {aud} token, error: {error}')
        return False

    async def refresh_token(self, client) -> bool:
        """Function to refresh tokens for a client."""
        try:
            # Refresh API tokens
            self._LOGGER.debug(f'Refreshing tokens for client "{client}"')
            if client != 'vwg':
                body = {
                    'grant_type': 'refresh_token',
                    'client_id': CLIENT_LIST[client].get('CLIENT_ID'),
                    'client_secret': CLIENT_LIST[client].get('CLIENT_SECRET'),
                    'refresh_token': self._session_tokens[client]['refresh_token']
                }
                url = AUTH_REFRESH
                self._session_token_headers[client]['User-ID']=self._user_id
                self._session_headers['User-ID']=self._user_id
            else:
                self._LOGGER.error(f'refresh_token() does not support client \'{client}\' ')
                raise
            #    body = {
            #        'grant_type': 'refresh_token',
            #        'scope': 'sc2:fal',
            #        'token': self._session_tokens[client]['refresh_token']
            #    }
            #    url = 'https://mbboauth-1d.prd.ece.vwg-connect.com/mbbcoauth/mobile/oauth2/v1/token'

            try:
                response = await self._session.post(
                    url=url,
                    headers=self._session_token_headers.get(client),
                    data = body,
                )
            except:
                raise

            if response.status == 200:
                tokens = await response.json()
                # Verify access_token
                if 'access_token' in tokens:
                    if not await self.verify_token(tokens['access_token']):
                        self._LOGGER.warning('Tokens could not be verified!')
                for token in tokens:
                    self._session_tokens[client][token] = tokens[token]
                return True
            elif response.status == 400:
                error = await response.json()
                if error.get('error', {}) == 'invalid_grant':
                    self._LOGGER.debug(f'VW-Group API token refresh failed: {error.get("error_description", {})}')
                    #if client == 'vwg':
                    #    return await self._getAPITokens()
                else:
                    self._LOGGER.debug(f'API token refresh failed. Error: {error}')
            else:
                resp = await response.json()
                self._LOGGER.warning(f'Something went wrong when refreshing tokens for "{client}".')
                self._LOGGER.debug(f'Headers: {TOKEN_HEADERS.get(client)}')
                self._LOGGER.debug(f'Request Body: {body}')
                self._LOGGER.warning(f'Something went wrong when refreshing VW-Group API tokens.')
        except Exception as error:
            self._LOGGER.warning(f'Could not refresh tokens: {error}')
        return False

    async def set_token(self, client) -> bool:
        """Switch between tokens."""
        # Lock to prevent multiple instances updating tokens simultaneously
        async with self._lock:
            # If no tokens are available for client, try to authorize
            tokens = self._session_tokens.get(client, None)
            if tokens is None:
                self._LOGGER.debug(f'Client "{client}" token is missing, call to authorize the client.')
                try:
                    # Try to authorize client and get tokens
                    if client != 'vwg':
                        result = await self._authorize(client)
                    else:
                        self._LOGGER.error('getAPITokens() commented out.')
                        result = False
                        #result = await self._getAPITokens()

                    # If authorization wasn't successful
                    if result is not True:
                        raise PyCupraAuthenticationException(f'Failed to authorize client {client}')
                except:
                    raise
            try:
                # Validate access token for client, refresh if validation fails
                valid = await self.validate_token(self._session_tokens.get(client, {}).get('access_token', ''))
                if valid == datetime.min:
                    self._LOGGER.debug(f'Tokens for "{client}" are invalid')
                    # Try to refresh tokens for client
                    if await self.refresh_token(client) is not True:
                        raise PyCupraTokenExpiredException(f'Tokens for client {client} are invalid')
                    else:
                        self._LOGGER.debug(f'Tokens refreshed successfully for client "{client}"')
                        pass
                else:
                    try:
                        self._LOGGER.debug(f'Access token for "{client}" is valid until {valid.strftime("%Y-%m-%d %H:%M:%S")}')
                    except:
                        pass
                # Assign token to authorization header
                self._session_headers['Authorization'] = 'Bearer ' + self._session_tokens[client]['access_token']
            except:
                raise PyCupraException(f'Failed to set token for "{client}"')
            return True

    def readSumTripStatisticsFile(self, vin: str, sumType: str):
        try:
            self._LOGGER.debug(self.anonymise(f"Reading {sumType} sum trip statistics file for vehicle {vin} if present."))
            csvFileName = os.path.join(self._dataBasePath, f"{vin}_drivingData_{sumType}Sums.csv")
            if not os.path.exists(csvFileName):
                self._LOGGER.warning(self.anonymise(f"Could not find {sumType} sum trip statistics file {csvFileName}. So starting without {sumType} sum trip statistics history."))
            else:
                with open(csvFileName, newline='') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        data: dict[str, Any] = {}
                        data['date']=row.get('date','2000-01-01')
                        data['startMileage']=int(row.get('startMileage','0'))
                        data['endMileage']=int(row.get('endMileage','0'))
                        data['fuelConsumption']=float(row.get('fuelConsumption','0.0'))
                        data['electricConsumption']=float(row.get('electricConsumption','0.0'))
                        data['drivingTime']=float(row.get('drivingTime','0.0'))
                        data['distanceDriven']=float(row.get('distanceDriven','0.0'))
                        data['speed']=float(row.get('speed','0.0'))
                        data['comment']=row.get('comment','')
                        if sumType == SUMTYPE_MONTHLY:
                            if self.monthlyTripData.get(vin,None)==None:
                                self.monthlyTripData[vin]={}
                            self.monthlyTripData[vin][(data.get('date','2000-01-01'))] = data
                        else:
                            if self.dailyTripData.get(vin,None)==None:
                                self.dailyTripData[vin]={}
                            self.dailyTripData[vin][(data.get('date','2000-01-01'))] = data
                    csvfile.close()
        except Exception as error:
            self._LOGGER.error(self.anonymise(f"Error while reading {sumType} sum trip statistics file for vehicle {vin}. Error: {error}."))
            raise PyCupraException(self.anonymise(f"Error while trying to read {sumType} sum trip statistics file for vehicle {vin}"))

    def writeSumTripStatisticsFile(self, vehicle: Vehicle, sumType: str):
        try:
            csvFileName = os.path.join(self._dataBasePath, f"{vehicle.vin}_drivingData_{sumType}Sums.csv")
            if os.path.exists(csvFileName):
                os.replace(csvFileName, csvFileName+".old")

            with open(csvFileName, 'w', newline='') as csvfile:
                fieldnames = ['rowNo','date', 'distanceDriven', 'startMileage', 'endMileage',  'drivingTime', 'fuelConsumption', 'electricConsumption', 'speed', 'comment']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                rowCounter = 0
                if sumType == SUMTYPE_MONTHLY:
                    vehiclesSumTripData = self.monthlyTripData.get(vehicle.vin,{})
                else:
                    vehiclesSumTripData = self.dailyTripData.get(vehicle.vin,{})
                listOfDatesSorted = sorted(vehiclesSumTripData)

                for entryDate in listOfDatesSorted:
                    if sumType == SUMTYPE_MONTHLY:
                        trip = self.monthlyTripData.get(vehicle.vin,{}).get(entryDate,{})
                    else:
                        trip = self.dailyTripData.get(vehicle.vin,{}).get(entryDate,{})
                    if trip=={}:
                        self._LOGGER.warning(f'Did not find trip for date {entryDate}')
                    writer.writerow({
                        'rowNo': rowCounter,
                        'date': trip.get('date',''),
                        'distanceDriven': trip.get('distanceDriven',0.0),
                        'startMileage': trip.get('startMileage',0),
                        'endMileage': trip.get('endMileage',0),
                        'drivingTime': trip.get('drivingTime',0.0),
                        'fuelConsumption': trip.get('fuelConsumption',0.0),
                        'electricConsumption': trip.get('electricConsumption',0.0),
                        'speed': trip.get('speed',0.0),
                        'comment': trip.get('comment',''),
                        })
                    rowCounter = rowCounter +1
                csvfile.close()
            self._LOGGER.debug(self.anonymise(f"Wrote {sumType} sum trip statistics file for vehicle {vehicle.vin}."))
        except Exception as error:
            self._LOGGER.error(self.anonymise(f"Error while writing {sumType} sum trip statistics file for vehicle {vehicle.vin}. Error: {error}."))
            raise PyCupraException(self.anonymise(f"Error while trying to write {sumType} sum trip statistics to file for vehicle {vehicle.vin}"))

    def updateDailySumTripStatistics(self, newTripData: dict,vin: str) -> bool:
        self._LOGGER.debug(self.anonymise(f'Updating daily sum trip statistics for vehicle {vin}'))
        listOfDailySums = newTripData.get('tripstatistics', {}).get('dailySums',[])
        updated = False
        vehicle = self.vehicle(vin)
        latestMileage:int = 0
        if vehicle.is_distance_supported:
            latestMileage = vehicle.distance
        backwardCalculatedMileage = latestMileage
        index = len(listOfDailySums)
        while index > 0:
            index=index-1
            currentDaySumElement = listOfDailySums[index]
            #self._LOGGER.debug(f'Entry = {currentDaySumElement}')
            entryDate = currentDaySumElement.get('date','2000-01-01')
            if self.dailyTripData.get(vin,{})=={}:
                self.dailyTripData[vin] = {}
            if self.dailyTripData[vin].get(entryDate,{})!={}:
                #entryDate is already present in self.dailyTripData
                if currentDaySumElement.get('drivingTime',0.0) > self.dailyTripData[vin].get(entryDate,{}).get('drivingTime', 0.0) or \
                    currentDaySumElement.get('distanceDriven',0.0) > self.dailyTripData[vin].get(entryDate,{}).get('distanceDriven', 0.0):
                    #Entry in self.dailyTripData does not represent the final values of the daily sum for the respective date
                    self._LOGGER.debug(f'API returned more current daily sum trip data for {entryDate}. Updating history.')
                    self.dailyTripData[vin][entryDate]['drivingTime'] = currentDaySumElement.get('drivingTime',0.0)
                    self.dailyTripData[vin][entryDate]['distanceDriven'] = currentDaySumElement.get('distanceDriven',0.0)
                    self.dailyTripData[vin][entryDate]['electricConsumption'] = currentDaySumElement.get('electricConsumption',0.0)
                    self.dailyTripData[vin][entryDate]['fuelConsumption'] = currentDaySumElement.get('fuelConsumption',0.0)
                    self.dailyTripData[vin][entryDate]['speed'] = currentDaySumElement.get('speed',0.0)
                    self.dailyTripData[vin][entryDate]['endMileage'] = backwardCalculatedMileage
                    if backwardCalculatedMileage!=latestMileage:
                        self.dailyTripData[vin][entryDate]['comment'] = 'End mileage calculated backwards for an older date, because driving time changed.'
                    updated = True
                else:
                    if index == len(listOfDailySums) -1 and latestMileage > self.dailyTripData[vin][entryDate]['endMileage']:
                        self._LOGGER.debug(f'Corrected end mileage for latest daily sum.')
                        self.dailyTripData[vin][entryDate]['endMileage'] = latestMileage
                        updated = True
                    #pass #self._LOGGER.debug(f'Daily sum trip data already present for {entryDate} and not shorter than the new data. Keeping it.')
            else:
                self.dailyTripData[vin][entryDate] = {}
                self.dailyTripData[vin][entryDate]['date'] = entryDate
                self.dailyTripData[vin][entryDate]['startMileage'] = backwardCalculatedMileage-int(currentDaySumElement.get('distanceDriven',0.0))
                self.dailyTripData[vin][entryDate]['endMileage'] = backwardCalculatedMileage
                self.dailyTripData[vin][entryDate]['electricConsumption'] = currentDaySumElement.get('electricConsumption',0.0)
                self.dailyTripData[vin][entryDate]['fuelConsumption'] = currentDaySumElement.get('fuelConsumption',0.0)
                self.dailyTripData[vin][entryDate]['drivingTime'] = currentDaySumElement.get('drivingTime',0.0)
                self.dailyTripData[vin][entryDate]['distanceDriven'] = currentDaySumElement.get('distanceDriven',0.0)
                self.dailyTripData[vin][entryDate]['speed'] = currentDaySumElement.get('speed',0.0)
                self.dailyTripData[vin][entryDate]['comment'] = ''
                if backwardCalculatedMileage!=latestMileage:
                    self.dailyTripData[vin][entryDate]['comment'] = 'End mileage calculated backwards for an older date, because it was not already present in daily sum history.'
                if backwardCalculatedMileage < 1:
                    self._LOGGER.debug(f'Calculated mileage is inplausibly small. Perhaps a problem with the odometer sensor.')
                    self.dailyTripData[vin][entryDate]['comment'] = 'Mileage is inplausibly small'
                updated = True
            if currentDaySumElement.get('distanceDriven',0.0)>0.0:
                backwardCalculatedMileage = backwardCalculatedMileage - int(currentDaySumElement.get('distanceDriven',0.0))
        return updated

    def updateMonthlySumTripStatistics(self, newTripData: dict,vin: str) -> bool:
        self._LOGGER.debug(self.anonymise(f'Updating monthly sum trip statistics for vehicle {vin}'))
        listOfMonthlySums = newTripData.get('tripstatistics', {}).get('monthlySums',[])
        updated = False
        vehicle = self.vehicle(vin)
        latestMileage:int = 0
        if vehicle.is_distance_supported:
            latestMileage = vehicle.distance
        backwardCalculatedMileage = latestMileage
        index = len(listOfMonthlySums)
        while index > 0:
            index=index-1
            currentMonthSumElement = listOfMonthlySums[index]
            #self._LOGGER.debug(f'Entry = {currentMonthSumElement}')
            entryDate = currentMonthSumElement.get('date','2000-01-01')
            if self.monthlyTripData.get(vin,{})=={}:
                self.monthlyTripData[vin] = {}
            if self.monthlyTripData[vin].get(entryDate,{})!={}:
                #entryDate is already present in self.monthlyTripData
                if currentMonthSumElement.get('drivingTime',0.0) > self.monthlyTripData[vin].get(entryDate,{}).get('drivingTime', 0.0) or \
                    currentMonthSumElement.get('distanceDriven',0.0) > self.monthlyTripData[vin].get(entryDate,{}).get('distanceDriven', 0.0):
                    #Entry in self.monthlyTripData does not represent the final values of the monthly sum for the respective date
                    self._LOGGER.debug(f'API returned more current monthly sum trip data for {entryDate}. Updating history.')
                    self.monthlyTripData[vin][entryDate]['drivingTime'] = currentMonthSumElement.get('drivingTime',0.0)
                    self.monthlyTripData[vin][entryDate]['distanceDriven'] = currentMonthSumElement.get('distanceDriven',0.0)
                    self.monthlyTripData[vin][entryDate]['electricConsumption'] = currentMonthSumElement.get('electricConsumption',0.0)
                    self.monthlyTripData[vin][entryDate]['fuelConsumption'] = currentMonthSumElement.get('fuelConsumption',0.0)
                    self.monthlyTripData[vin][entryDate]['speed'] = currentMonthSumElement.get('speed',0.0)
                    self.monthlyTripData[vin][entryDate]['endMileage'] = backwardCalculatedMileage
                    if backwardCalculatedMileage!=latestMileage:
                        self.monthlyTripData[vin][entryDate]['comment'] = 'End mileage calculated backwards for an older month, because driving time changed.'
                    updated = True
                else:
                    if index == len(listOfMonthlySums) -1 and latestMileage > self.monthlyTripData[vin][entryDate]['endMileage']:
                        self._LOGGER.debug(f'Corrected end mileage for latest monthly sum.')
                        self.monthlyTripData[vin][entryDate]['endMileage'] = latestMileage
                        updated = True
                    #pass #self._LOGGER.debug(f'Monthly sum trip data already present for {entryDate} and not shorter than the new data. Keeping it.')
            else:
                self.monthlyTripData[vin][entryDate] = {}
                self.monthlyTripData[vin][entryDate]['date'] = entryDate
                self.monthlyTripData[vin][entryDate]['startMileage'] = backwardCalculatedMileage - int(currentMonthSumElement.get('distanceDriven',0.0))
                self.monthlyTripData[vin][entryDate]['endMileage'] = backwardCalculatedMileage
                self.monthlyTripData[vin][entryDate]['electricConsumption'] = currentMonthSumElement.get('electricConsumption',0.0)
                self.monthlyTripData[vin][entryDate]['fuelConsumption'] = currentMonthSumElement.get('fuelConsumption',0.0)
                self.monthlyTripData[vin][entryDate]['drivingTime'] = currentMonthSumElement.get('drivingTime',0.0)
                self.monthlyTripData[vin][entryDate]['distanceDriven'] = currentMonthSumElement.get('distanceDriven',0.0)
                self.monthlyTripData[vin][entryDate]['speed'] = currentMonthSumElement.get('speed',0.0)
                self.monthlyTripData[vin][entryDate]['comment'] = ''
                if backwardCalculatedMileage!=latestMileage:
                    self.monthlyTripData[vin][entryDate]['comment'] = 'End mileage calculated backwards for an older date, because it was not already present in daily sum history.'
                if backwardCalculatedMileage < 1:
                    self._LOGGER.debug(f'Calculated mileage is inplausibly small. Perhaps a problem with the odometer sensor.')
                    self.monthlyTripData[vin][entryDate]['comment'] = 'Mileage is inplausibly small'
                updated = True
            if currentMonthSumElement.get('distanceDriven',0.0)>0.0:
                backwardCalculatedMileage = backwardCalculatedMileage - int(currentMonthSumElement.get('distanceDriven',0.0))
        return updated



 #### Class helpers ####
    @property
    def vehicles(self) -> list:
        """Return list of Vehicle objects."""
        return self._vehicles

    def vehicle(self, vin) -> Any:
        """Return vehicle object for given vin."""
        return next(
            (
                vehicle
                for vehicle in self.vehicles
                if vehicle.unique_id.lower() == vin.lower()
            ), None
        )

    def hash_spin(self, challenge, spin) -> str:
        """Convert SPIN and challenge to hash."""
        spinArray = bytearray.fromhex(spin);
        byteChallenge = bytearray.fromhex(challenge);
        spinArray.extend(byteChallenge)
        return hashlib.sha512(spinArray).hexdigest()

    def addToAnonymisationDict(self, keyword, replacement) -> None:
        self._anonymisationDict[keyword] = replacement

    def addToAnonymisationKeys(self, keyword) -> None:
        self._anonymisationKeys.add(keyword)

    def anonymise(self, inObj) -> Any:
        if self._session_anonymise:
            if isinstance(inObj, str):
                for key, value in self._anonymisationDict.items():
                    inObj = inObj.replace(key,value)
            elif isinstance(inObj, dict):
                for elem in inObj:
                    if elem in self._anonymisationKeys:
                        inObj[elem] = '[ANONYMISED]'
                    else:
                        inObj[elem]= self.anonymise(inObj[elem])
            elif isinstance(inObj, list):
                for i in range(len(inObj)):
                    inObj[i]= self.anonymise(inObj[i])
        return inObj

def convertTripStatisticsData(dataFromAPI) -> list:
    data = []
    for element in dataFromAPI:
        newEntry = {}
        newEntry['date']=element.get('day',{}).get('id',datetime(year=1970, month=1, day= 1)).strftime('%Y-%m-%d')
        for subElement in element.get('values',[]):
            if subElement['value'] != None: 
                newEntry[subElement['id']]=subElement['value']
            else:
                newEntry[subElement['id']]=subElement['total']
        data.append(newEntry)
    return data

#async def main():
    """Main method."""
    """if '-v' in argv:
        logging.basicConfig(level=logging.INFO)
    elif '-vv' in argv:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.ERROR)

    async with ClientSession(headers={'Connection': 'keep-alive'}) as session:
        connection = Connection(session, **read_config())
        if await connection.doLogin():
            if await connection.get_vehicles():
                for vehicle in connection.vehicles:
                    print(f'Vehicle id: {vehicle}')
                    print('Supported sensors:')
                    for instrument in vehicle.dashboard().instruments:
                        print(f' - {instrument.name} (domain:{instrument.component}) - {instrument.str_state}')


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
"""