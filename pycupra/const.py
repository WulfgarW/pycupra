"""Constants for pycupra library."""

BASE_SESSION = 'https://ola.prod.code.seat.cloud.vwgroup.com'
BASE_AUTH = 'https://identity.vwgroup.io'

# Data used in communication
CLIENT_LIST = {
    'seat': {
        'CLIENT_ID': '99a5b77d-bd88-4d53-b4e5-a539c60694a3@apps_vw-dilab_com',
        'SCOPE': 'openid profile nickname birthdate phone',
        'REDIRECT_URL': 'seat://oauth-callback',
        'TOKEN_TYPES': 'code id_token token'
    },
    'cupra': {
        'CLIENT_ID': '3c756d46-f1ba-4d78-9f9a-cff0d5292d51@apps_vw-dilab_com',
        'CLIENT_SECRET': 'eb8814e641c81a2640ad62eeccec11c98effc9bccd4269ab7af338b50a94b3a2',
        'SCOPE': 'openid profile nickname birthdate phone',
        'REDIRECT_URL': 'cupra://oauth-callback',
        'TOKEN_TYPES': 'code id_token token'
    }
}


XCLIENT_ID = '3c756d46-f1ba-4d78-9f9a-cff0d5292d51@apps_vw-dilab.com' 
XAPPVERSION = '2.10.0'
XAPPNAME = 'com.cupra.mycupra'
USER_AGENT_CUPRA = 'OLACupra/2.10.0 (Android 12; sdk_gphone64_x86_64; Google) Mobile' 
USER_AGENT_SEAT = 'OLASeat/2.10.1 (Android 12; sdk_gphone64_x86_64; Google) Mobile'
APP_URI = 'https://ola.prod.code.seat.cloud.vwgroup.com'

HEADERS_SESSION = {
    'seat': {
    'Connection': 'keep-alive',
    'Content-Type': 'application/json',
    'Accept-charset': 'UTF-8',
    'Accept': 'application/json',
    #'X-Client-Id': XCLIENT_ID,
    #'X-App-Version': XAPPVERSION,
    #'X-App-Name': XAPPNAME,
    'User-Agent': USER_AGENT_SEAT,
    #'User-ID': '?????', # to be set later
    'Accept-Language': 'en_GB',
    },
    'cupra': {
    'Connection': 'keep-alive',
    'Content-Type': 'application/json',
    'Accept-charset': 'UTF-8',
    'Accept': 'application/json',
    #'X-Client-Id': XCLIENT_ID,
    #'X-App-Name': XAPPNAME,
    'User-Agent': USER_AGENT_CUPRA,
    #'User-ID': '?????', # to be set later,
    #'Accept-Encoding': 'gzip', # to be deleted later!!!
    'Accept-Language': 'en_GB',
    }
}

HEADERS_AUTH = {
    'seat': {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': USER_AGENT_SEAT,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'x-requested-with': XAPPNAME,
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        #'X-App-Name': XAPPNAME
    },
    'cupra':{
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': USER_AGENT_CUPRA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'x-requested-with': XAPPNAME,
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        #'X-App-Name': XAPPNAME
    }
}

TOKEN_HEADERS = {
    'seat': {
        'Accept': 'application/json',
        'X-Platform': 'Android',
        #'X-Language-Id': 'XX',
        #'X-Country-Id': 'XX',
        #'Accept-Language': 'XX',
        'Accept-Charset': 'UTF-8',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Connection': 'keep-alive',
        'Accept-Encoding': 'gzip',
        'User-Agent': USER_AGENT_SEAT,
        'app-version': '2.10.0',
        'app-brand': 'seat',
        'app-market': 'android',
        #'User-ID': '?????', # to be set later
        'Authorization': 'Bearer'
    },
    'cupra': {
        'Accept': 'application/json',
        'X-Platform': 'Android',
        #'X-Language-Id': 'XX',
        #'X-Country-Id': 'XX',
        #'Accept-Language': 'XX',
        'Accept-Charset': 'UTF-8',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Connection': 'keep-alive',
        'Accept-Encoding': 'gzip',
        'User-Agent': USER_AGENT_CUPRA,
        'app-version': '2.10.0',
        'app-brand': 'cupra',
        'app-market': 'android',
        #'User-ID': '?????', # to be set later
        'Authorization': 'Bearer'
    }
}

#ERROR_CODES = {
#    '11': 'Charger not connected'
#}

### API Endpoints below, not yet in use ###
# API AUTH endpoints
AUTH_OIDCONFIG = 'https://identity.vwgroup.io/.well-known/openid-configuration'                     # OpenID configuration
AUTH_TOKEN = 'https://identity.vwgroup.io/oidc/v1/token'                                      # Endpoint for exchanging code for token
AUTH_REFRESH = 'https://ola.prod.code.seat.cloud.vwgroup.com/authorization/api/v1/token'             # Endpoint for token refresh (also used for exchanging code for token for Seat)
AUTH_TOKENKEYS = 'https://identity.vwgroup.io/oidc/v1/keys'                                         # Signing keys for tokens

# API endpoints
API_MBB_STATUSDATA = 'https://customer-profile.vwgroup.io/v3/customers/{userId}/mbbStatusData'
API_PERSONAL_DATA= 'https://customer-profile.vwgroup.io/v3/customers/{userId}/personalData'
#Other option for personal data is '{baseurl}/v1/users/{self._user_id}'

API_VEHICLES = '{APP_URI}/v2/users/{userId}/garage/vehicles'                                  # Garage info
API_MYCAR = '{baseurl}/v5/users/{userId}/vehicles/{vin}/mycar'                                # Vehicle status report
API_RANGES = '{baseurl}/v1/vehicles/{vin}/ranges'                                             # Range information
API_CHARGING = '{baseurl}/v1/vehicles/{vin}/charging'                                                # Vehicle charging information 
API_CHARGING_PROFILES = '{baseurl}/vehicles/{vin}/charging/profiles'                                 # Vehicle charging profile information 
#API_OPERLIST = '{homeregion}/api/rolesrights/operationlist/v3/vehicles/{vin}'                       # API Endpoint for supported operations
#API_CHARGER = 'fs-car/bs/batterycharge/v1/{BRAND}/{COUNTRY}/vehicles/{vin}/charger'                 # Charger data
API_CLIMATER_STATUS = '{baseurl}/v1/vehicles/{vin}/climatisation/status'                             # Climatisation data
API_CLIMATER = '{baseurl}/v2/vehicles/{vin}/climatisation'                                           # Climatisation data
API_CLIMATISATION_TIMERS = '{baseurl}/vehicles/{vin}/climatisation/timers'                            # Climatisation timers
API_DEPARTURE_TIMERS = '{baseurl}/v1/vehicles/{vin}/departure-timers'                                 # Departure timers
API_DEPARTURE_PROFILES = '{baseurl}/v1/vehicles/{vin}/departure/profiles'                             # Departure profiles
API_POSITION = '{baseurl}/v1/vehicles/{vin}/parkingposition'                                         # Position data
API_POS_TO_ADDRESS= 'https://maps.googleapis.com/maps/api/directions/json?origin={lat},{lon}&destination={lat},{lon}&traffic_model=best_guess&departure_time=now&language=de&key={apiKeyForGoogle}&mode=driving'
API_TRIP_V1 = '{baseurl}/v1/vehicles/{vin}/driving-data/{dataType}?from=1970-01-01T00:00:00Z&to=2099-12-31T09:59:01Z' # Old trip statistics (whole history) SHORT/LONG/CYCLIC (WEEK only with from)
API_TRIP = '{baseurl}/v2/vehicles/{vin}/driving-data/CUSTOM?from={startDate}T00:00:00Z&to={endDateTime}&distanceUnit=km&speedUnit=kmph' # Trip statistics (whole history) SHORT/LONG/CYCLIC (WEEK only with from)
API_MILEAGE = '{baseurl}/v1/vehicles/{vin}/mileage'                                                  # Total km etc
API_MAINTENANCE = '{baseurl}/v1/vehicles/{vin}/maintenance'                                          # Inspection information
API_MEASUREMENTS = '{baseurl}/v1/vehicles/{vin}/measurements/engines'                                # ???
API_STATUS = '{baseurl}/v2/vehicles/{vin}/status'                                                    # Status information like locks and windows
API_WARNINGLIGHTS = '{baseurl}/v3/vehicles/{vin}/warninglights'                                      # ???
API_SHOP = '{baseurl}/v1/shop/vehicles/{vin}/articles'                                               # ???
#API_ACTION = '{baseurl}/v1/vehicles/{vin}/{action}/requests/{command}'                               # Actions (e.g. ActionCharge="charging", ActionChargeStart="start",ActionChargeStop="stop")
API_RELATION_STATUS = '{baseurl}/v1/users/{userId}/vehicles/{vin}/relation-status'            # ???
API_INVITATIONS = '{baseurl}/v1/user/{userId}/invitations'                                    # ???
API_CAPABILITIES = '{APP_URI}/v1/user/{userId}/vehicle/{vin}/capabilities'                    # ???
#API_CAPABILITIES_MANAGEMENT = '{API_CAPABILITIES}/management'                                        # ???
API_IMAGE = '{baseurl}/v2/vehicles/{vin}/renders'
API_HONK_AND_FLASH = '{baseurl}//v1/vehicles/{vin}/honk-and-flash'
API_ACCESS = '{baseurl}//v1/vehicles/{vin}/access/{action}'                                          # to lock or unlock vehicle
API_REQUESTS = '{baseurl}/vehicles/{vin}/{capability}/requests'
API_REFRESH = '{baseurl}/v1/vehicles/{vin}/vehicle-wakeup/request'
API_SECTOKEN = '{baseurl}/v2/users/{userId}/spin/verify'
API_DESTINATION = '{baseurl}/v1/users/vehicles/{vin}/destination'
API_LITERALS= '{APP_URI}/v1/content/apps/my-cupra/literals/{language}'                               # Message texts in different langauages, e.g. 'en_GB'
API_ACTIONS = '{baseurl}/v1/vehicles/{vin}/{capability}/actions'                           # capability e.g. 'charging', mode (e.g. 'update-settings') will be added as postfix
API_AUXILIARYHEATING = '{baseurl}/v1/vehicles/{vin}/auxiliary-heating'                              # action (start/stop) will be added as postfix

# Still to analyse if needed
#'{baseurl}/settings/api/v1?vin={vin}&vehicle-model=LeonST&region=US&enrolment-country=DE&platform=MOD3'
#'{baseurl}/v1/users/{self._user_id}/vin/{vin}/terms-and-conditions'
#'{baseurl}/v2/subscriptions'
#'{baseurl}/v1/users/{self._user_id}/vehicles/{vin}/leads/history'
#'{baseurl}/v1/users/{self._user-id}/vehicles/{vin}/consents/xxcryptickeyxxx?locale=en_DE' #{"userId":"xxxxxxx","locale":"en_DE","error":{"title":"Consent failed to load.","detail":"CUPRAApp_ME3_Vehicle_VehiclePermissions_MainViewAccepted_Low_Type1_Wrong"}}

API_CONNECTION= '{APP_URI}/v1/vehicles/{vin}/remote-availability' # until 26.03.2026 '{APP_URI}/vehicles/{vin}/connection'
#API_CONSENTS='{APP_URI}/v1/users/{self._user_id}/consents'
API_PSP='{baseurl}/v2/users/{userId}/vehicles/{vin}/psp'     # primary service provider (Werkstatt)
API_USER_INFO= 'https://identity-userinfo.vwgroup.io/oidc/userinfo' #{"sub":"xxx","name":"xxx","given_name":"xxx","family_name":"xxx","nickname":"xxx","email":"###","email_verified":true,"birthdate":"###","updated_at":123456789,"picture":"https://customer-pictures.vwgroup.io/v1/###/profile-picture"}

PUBLIC_MODEL_IMAGES_SERVER = 'prod-ola-public-bucket.s3.eu-central-1.amazonaws.com'                      # non-indivdual model images are on this server

# API endpoints for status
REQ_STATUS = {
    'climatisation': 'fs-car/bs/climatisation/v1/{BRAND}/{COUNTRY}/vehicles/{vin}/climater/actions/{id}',
    'batterycharge': 'fs-car/bs/batterycharge/v1/{BRAND}/{COUNTRY}/vehicles/{vin}/charger/actions/{id}',
    'departuretimer': 'fs-car/bs/departuretimer/v1/{BRAND}/{COUNTRY}/vehicles/{vin}/timer/actions/{id}',
    'vsr': 'fs-car/bs/vsr/v1/{BRAND}/{COUNTRY}/vehicles/{vin}/requests/{id}/jobstatus',
    'default': 'fs-car/bs/{section}/v1/{BRAND}/{COUNTRY}/vehicles/{vin}/requests/{id}/status'
}

FCM_PROJECT_ID='ola-apps-prod'
FCM_APP_ID={
    'cupra': '1:530284123617:android:9b9ba5a87c7ffd37fbeea0',
    'seat':  '1:530284123617:android:d6187613ac3d7b08fbeea0'
}
FCM_API_KEY='AIzaSyCoSp1zitklb1EDj5yQumN0VNhDizJQHLk'
FIREBASE_STATUS_NOT_INITIALISED= 0
FIREBASE_STATUS_ACTIVATED= 1
FIREBASE_STATUS_NOT_WANTED= -2
FIREBASE_STATUS_ACTIVATION_FAILED= -1
FIREBASE_STATUS_ACTIVATION_STOPPED= -3

SUMTYPE_DAILY='daily'
SUMTYPE_MONTHLY='monthly'

EUDA_CLIENT_LIST = {
    'CLIENT_ID': 'f85e5b69-e3b2-43aa-9c0d-1b7d0e0b576f@apps_vw-dilab_com',
    'SCOPE': 'openid profile cars',
    'REDIRECT_URL': 'https://eu-data-act.drivesomethinggreater.com/login',
}

EUDA_HEADERS_SESSION = {
    'Connection': 'keep-alive',
    'Content-Type': '*/*', #'application/json',
    'Accept-charset': 'UTF-8',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',#'application/json',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0',#USER_AGENT_SEAT,
    'Referer': 'https://eu-data-act.drivesomethinggreater.com/de/en/user.html',
    #'User-ID': '?????', # to be set later
    'Accept-Encoding': 'gzip, deflate, br, zstd', # to be deleted later!!!
    'Accept-Language': 'de,en-US;q=0.7,en;q=0.3',
}

EUDA_HEADERS_AUTH = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
    'Referer': 'https://eu-data-act.drivesomethinggreater.com/de/en/login.html',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:146.0) Gecko/20100101 Firefox/146.0',#USER_AGENT_SEAT,
}


EUDA_AUTH_OIDC = 'https://identity.vwgroup.io/oidc/v1/authorize' # Authorization endpoint for EUDA login
EUDA_AUTH_ISSUER = 'https://identity.vwgroup.io' # Authorization issuer for EUDA login

EUDA_BASE_URL = 'https://eu-data-act.drivesomethinggreater.com'
EUDA_API_VEHICLES = '{baseurl}/proxy_api/consent/me/vehicles?viewPosition={viewPos}' # Endpoint to get vehicles
EUDA_API_FILE_DOWNLOAD = '{baseurl}/proxy_api/euda-apim/datadelivery/vehicles/{vin}/{id}/download' # Endpoint to download a data file
EUDA_API_FILE_LIST = '{baseurl}/proxy_api/euda-apim/datadelivery/vehicles/{vin}/{id}/list' # Endpoint to read a list of available files
EUDA_API_DATACLUSTERS = '{baseurl}/proxy_api/euda-apim/datarequest/vehicles/{vin}/metadata/{type}' # Endpoint to read data cluster information
EUDA_URL_DETAILS = '{baseurl}/content/euda/de/en/user/details?vin={vin}'

EUDA_API_TOKEN = '{baseurl}/libs/granite/csrf/token.json'
EUDA_API_PERMISSION_CHECK = '{baseurl}/services/permissioncheck'
EUDA_API_LOGOUT = '{baseurl}/services/logout' # still in test

EUDA_SHORT_TERM_DATA_START_MILEAGE_KEY = 'ecd266dd-f536-39c2-a575-352216b87f39'
EUDA_SHORT_TERM_DATA_MILEAGE_KEY = '9f55581a-4fa2-3570-9c9e-b80d210b9a42'
EUDA_SHORT_TERM_DATA_TRAVEL_TIME_KEY = 'f0890c07-e62e-32dc-ab3b-80431f070b13'
EUDA_SHORT_TERM_DATA_AVERAGE_ELECTR_ENGINE_CONSUMPTION_KEY = '3b1bdf91-8e59-333a-93ed-f8e5a980bc96'
EUDA_SHORT_TERM_DATA_AVERAGE_FUEL_CONSUMPTION_KEY = 'a0ee824b-9a53-34ee-8107-3ed94684efa7'

EUDA_LONG_TERM_DATA_START_MILEAGE_KEY = '2bfaa641-c972-3816-ae7c-73459bcd673d'
EUDA_LONG_TERM_DATA_MILEAGE_KEY = 'f8eba56b-ee3f-3c48-b852-03c9b956053f'
EUDA_LONG_TERM_DATA_TRAVEL_TIME_KEY = 'd2ad181b-511a-37d0-8109-e676e68c86b2'
EUDA_LONG_TERM_DATA_AVERAGE_ELECTR_ENGINE_CONSUMPTION_KEY = '79f1709e-028d-3b3a-936e-bbef63b92969'
EUDA_LONG_TERM_DATA_AVERAGE_FUEL_CONSUMPTION_KEY = 'df531c6f-8897-3236-a760-5975322e7021'
EUDA_LONG_TERM_DATA_AVERAGE_SPEED_KEY = '77838f59-786a-36fa-b1d4-47217a9fb40e'

EUDA_OUTSIDE_TEMPERATURE_KEY = '6810b781-e54a-35e8-af98-fcdefb54bac6'
EUDA_PARKING_BRAKE_KEY = 'f8bbe94d-06e1-3311-bf8f-c0c99cc67d48'
EUDA_OIL_LEVEL_ADDITIONAL_OIL_LEVEL_KEY = '78e92351-cf56-3c15-96d3-9b63d62ca618'
EUDA_OIL_LEVEL_ACTUAL_LEVEL_KEY = 'a3368611-8c63-3b7d-9d19-148a464c7a7b'

