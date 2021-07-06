import os
from cogs.Google_API.Google import Create_Service

API_NAME = 'photoslibrary'
API_VERSION = 'v1'
CLIENT_SECRET_FILE = 'cogs/Google_API/Client_secret.json'
SCOPES = ['https://photos.app.goo.gl/Krn5hNzstqugQ541A','https://www.googleapis.com/auth/photoslibrary']

service = Create_Service(CLIENT_SECRET_FILE,API_NAME, API_VERSION, SCOPES)
