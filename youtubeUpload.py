# Sample Python code for user authorization

import os
import time
import json
import httplib2
import http
import google.oauth2.credentials
import pprint
import argparse

from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

# The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
# the OAuth 2.0 information for this application, including its client_id and
# client_secret.
CLIENT_SECRETS_FILE = "client_secret.json"
REFRESH_TOKEN_FILE = "client_refresh.json"

# This OAuth 2.0 access scope allows for full read/write access to the
# authenticated user's account and requires requests to use an SSL connection.
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']
API_SERVICE_NAME = 'youtube'
API_VERSION = 'v3'
REFRESH_ACCESS = True

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
	http.client.IncompleteRead, http.client.ImproperConnectionState,
	http.client.CannotSendRequest, http.client.CannotSendHeader,
	http.client.ResponseNotReady, http.client.BadStatusLine)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")


def get_authenticated_service():
	global REFRESH_ACCESS
	try:
		with open(REFRESH_TOKEN_FILE, 'r') as refreshTokenFile:
			refreshTokenJson = json.load(refreshTokenFile)
			refreshTokenFile.close
			if "YouTube" in refreshTokenJson.keys():
				if not ("refresh_token" in refreshTokenJson["YouTube"].keys()):
					REFRESH_ACCESS = False
			else:
				REFRESH_ACCESS = False
	except FileNotFoundError:
		REFRESH_ACCESS = False


	if REFRESH_ACCESS:
		with open(CLIENT_SECRETS_FILE, 'r') as clientSecretsFile:
			clientSecretsJson = json.load(clientSecretsFile)
			clientSecretsFile.close
		
		credentials = Credentials(
			None,
			refresh_token=refreshTokenJson["YouTube"]["refresh_token"],
			token_uri=clientSecretsJson["installed"]["token_uri"],
			client_id=clientSecretsJson["installed"]["client_id"],
			client_secret=clientSecretsJson["installed"]["client_secret"]
		)
	else:
		flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
		credentials = flow.run_console()

		print ("Token: "+credentials.token)
		print ("Refresh Token: "+credentials.refresh_token)
		
		with open(REFRESH_TOKEN_FILE, 'w') as refreshTokenFile:
			refreshTokenJson = {'YouTube':{'refresh_token': credentials.refresh_token}}			
			json.dump(refreshTokenJson, refreshTokenFile)
			refreshTokenFile.close


	return build(API_SERVICE_NAME, API_VERSION, credentials = credentials)

def channels_list_by_username(service, **kwargs):
	results = service.channels().list(
		**kwargs
	).execute()
	
	#print(datetime.now().strftime('%Y-%m-%d %A %H:%M:%S'))
	print('%s: This channel\'s ID is %s. Its title is %s, and it has %s views.' 
		%(datetime.now().strftime('%Y-%m-%d %A %H:%M:%S'),
		results['items'][0]['id'],
		results['items'][0]['snippet']['title'],
		results['items'][0]['statistics']['viewCount']))

def initialize_upload(youtube, options):
	tags = None
	if options.keywords:
		tags = options.keywords.split(",")

	body=dict(
		snippet=dict(
			title=options.title,
			description=options.description,
			tags=tags,
			categoryId=options.category
		),
		status=dict(
			privacyStatus=options.privacyStatus
		)
	)

	# Call the API's videos.insert method to create and upload the video.
	insert_request = youtube.videos().insert(
		part=",".join(body.keys()),
		body=body,
		# The chunksize parameter specifies the size of each chunk of data, in
		# bytes, that will be uploaded at a time. Set a higher value for
		# reliable connections as fewer chunks lead to faster uploads. Set a lower
		# value for better recovery on less reliable connections.
		#
		# Setting "chunksize" equal to -1 in the code below means that the entire
		# file will be uploaded in a single HTTP request. (If the upload fails,
		# it will still be retried where it left off.) This is usually a best
		# practice, but if you're using Python older than 2.6 or if you're
		# running on App Engine, you should set the chunksize to something like
		# 1024 * 1024 (1 megabyte).
		media_body=MediaFileUpload(options.file, chunksize=-1, resumable=True)
	)

	resumable_upload(insert_request)

# This method implements an exponential backoff strategy to resume a
# failed upload.
def resumable_upload(insert_request):
	response = None
	error = None
	retry = 0
	while response is None:
		try:
			print (datetime.now().strftime('%Y-%m-%d %A %H:%M:%S') + ' Uploading file...')
			status, response = insert_request.next_chunk()
			if 'id' in response:
				print (datetime.now().strftime('%Y-%m-%d %A %H:%M:%S') + " Video id '%s' was successfully uploaded." % response['id'])
			else:
				exit(datetime.now().strftime('%Y-%m-%d %A %H:%M:%S') + "The upload failed with an unexpected response: %s" % response)
		except HttpError as e:
			if e.resp.status in RETRIABLE_STATUS_CODES:
				error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status,e.content)
			else:
				raise
		except RETRIABLE_EXCEPTIONS as e:
			error = "A retriable error occurred: %s" % e

		if error is not None:
			print (error)
			retry += 1
			if retry > MAX_RETRIES:
				exit("No longer attempting to retry.")

			max_sleep = 2 ** retry
			sleep_seconds = random.random() * max_sleep
			print ("Sleeping %f seconds and then retrying..." % sleep_seconds)
			time.sleep(sleep_seconds)

if __name__ == '__main__':
	# When running locally, disable OAuthlib's HTTPs verification. When
	# running in production *do not* leave this option enabled.
	os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
	service = get_authenticated_service()

	#channels_list_by_username(service,part='snippet,contentDetails,statistics',forUsername='TapanKhatri')

	argparser = argparse.ArgumentParser()

	argparser.add_argument("--file", required=True, help="Video file to upload")
	argparser.add_argument("--title", help="Video title", default="Test Title")
	argparser.add_argument("--description", help="Video description",
		default="Test Description")
	argparser.add_argument("--category", default="22",
		help="Numeric video category. " +
			"See https://developers.google.com/youtube/v3/docs/videoCategories/list")
	argparser.add_argument("--keywords", help="Video keywords, comma separated",
		default="")
	argparser.add_argument("--privacyStatus", choices=VALID_PRIVACY_STATUSES,
		default=VALID_PRIVACY_STATUSES[1], help="Video privacy status.")
	args = argparser.parse_args()

	if not os.path.exists(args.file):
		exit("Please specify a valid file using the --file= parameter.")

	youtube = get_authenticated_service()
	try:
		initialize_upload(youtube, args)
	except HttpError as e:
		print ("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))


