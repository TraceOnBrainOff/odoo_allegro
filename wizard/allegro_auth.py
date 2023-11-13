import requests
import json
import time
import webbrowser
import logging

_logger = logging.getLogger(__name__)

from odoo.exceptions import UserError

def get_code(CLIENT_ID, CLIENT_SECRET):
    CODE_URL = "https://allegro.pl/auth/oauth/device"
    try:
        payload = {'client_id': CLIENT_ID}
        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        api_call_response = requests.post(CODE_URL, auth=(CLIENT_ID, CLIENT_SECRET),
                                          headers=headers, data=payload, verify=False)
        code = api_call_response.json()
        return code
    except requests.exceptions.HTTPError as err:
        raise UserError("OAuth get_code error:"+err)


def get_new_token(device_code, CLIENT_ID, CLIENT_SECRET):
    TOKEN_URL = "https://allegro.pl/auth/oauth/token"
    try:
        headers = {'Content-type': 'application/x-www-form-urlencoded'}
        data = {'grant_type': 'urn:ietf:params:oauth:grant-type:device_code', 'device_code': device_code}
        api_call_response = requests.post(TOKEN_URL, auth=(CLIENT_ID, CLIENT_SECRET),
                                          headers=headers, data=data, verify=False)
        tokens = api_call_response.json()
        return tokens
    except requests.exceptions.HTTPError as err:
        raise UserError("OAuth get_code error:"+err)

def get_next_token(refresh_token, CLIENT_ID, CLIENT_SECRET): #Used for getting a new access token from a refresh token
    TOKEN_URL = "https://allegro.pl/auth/oauth/token"
    try:
        data = {'grant_type': 'refresh_token', 'refresh_token': refresh_token}
        access_token_response = requests.post(TOKEN_URL, data=data, verify=False,
                                              allow_redirects=False, auth=(CLIENT_ID, CLIENT_SECRET))
        tokens = access_token_response.json()
        return tokens
    except requests.exceptions.HTTPError as err:
        raise SystemExit(err)

def await_for_token(interval, device_code, CLIENT_ID, CLIENT_SECRET):
    while True:
        time.sleep(interval)
        result_access_token = get_new_token(device_code, CLIENT_ID, CLIENT_SECRET)
        token = result_access_token.json()
        if result_access_token.status_code == 400:
            if token['error'] == 'slow_down':
                interval += interval
            if token['error'] == 'access_denied':
                raise UserError("Token - Access Denied")
        else:
            #{ ###EXAMPLE RESPONSE###
            #"access_token":"eyJ...dUA",
            #"token_type":"bearer",
            #"refresh_token":"eyJ...SDA",
            #"expires_in":43199,
            #"scope":"allegro_api",
            #"allegro_api": true,
            #"jti":"2184f3be-f6de-4a66-bd8f-b11347d7ba80"
            #}
            return token

def token_check(parent, ICP, CLIENT_ID, CLIENT_SECRET): #Entry point - pass client_id, client_secret and ICP into here, returns access_token
    encoded_token = ICP.get_param("allegro.application.token")
    override_token = ICP.get_param("allegro.application.refresh_token_ovr")
    current_time_secs = int(time.time())
    if encoded_token != False: #Exists, access/refresh tokens can be up-to-date or expired
        decoded_token = json.loads(encoded_token)
        if current_time_secs > decoded_token['access_token_expire_time']: #Access Token is expired
            if current_time_secs > decoded_token['refresh_token_expire_time']: #Refresh Token is expired, user re-authentication is required
                return get_new_tokens(ICP, CLIENT_ID, CLIENT_SECRET) #Start over
            else: #Refresh Token is OK
                new_token = get_next_token(decoded_token['refresh_token'], CLIENT_ID, CLIENT_SECRET) #Get new pair of tokens from the current refresh token
                save_token(ICP, new_token)
                parent.env.cr.commit()
                return new_token['access_token']
        else: #Access Token is OK
            return decoded_token['access_token'] 
    elif encoded_token == False and override_token: #Use the hacky method of manually setting the token from settings
        new_token = get_next_token(override_token, CLIENT_ID, CLIENT_SECRET) #Get new pair of tokens from the current refresh token
        save_token(ICP, new_token)
        ICP.set_param("allegro.application.refresh_token_ovr", "") #Clear it to avoid future confusion
        parent.env.cr.commit()
        return new_token['access_token']
    elif encoded_token == False and override_token == False: #Doesn't exist
        return get_new_tokens(ICP, CLIENT_ID, CLIENT_SECRET)

def save_token(ICP, token):
    dumps = json.dumps({
            'access_token': token['access_token'],
            'refresh_token': token['refresh_token'],
            'access_token_expire_time': int(time.time())+token['expires_in'],
            'refresh_token_expire_time': int(time.time())+7880000 #3 months' worth of seconds (minus 10k leeway because allegro doesn't provide the expiry for the refresh token)
    })
    ICP.set_param("allegro.application.token", dumps)

def get_new_tokens(ICP, CLIENT_ID, CLIENT_SECRET):
    result = get_code(CLIENT_ID, CLIENT_SECRET) #For manual auth
    print(f"Get Ver URL {result}")
    webbrowser.open(result['verification_uri_complete'])
    token = await_for_token(int(result['interval']), result['device_code'], CLIENT_ID, CLIENT_SECRET)
    save_token(ICP, token)
    return token['access_token']