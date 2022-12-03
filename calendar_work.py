import os
import json
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError
from dateutil.parser import parse
from asyncio.exceptions import TimeoutError

SCOPES = ['https://www.googleapis.com/auth/calendar']


def search_creds(name):
    # Search through the json file to find if the user already has a registered key.
    if os.path.exists('tokens.json'):
        with open('tokens.json', 'r') as tokens:
            data = json.load(tokens)
        if name in data:
            # Write the user's credentials to a json file to be copied to creds.
            with open('token.json', 'w') as token:
                json.dump(data[name], token)
            return Credentials.from_authorized_user_file('token.json', SCOPES)
    # Return None if the user does not have any registered credentials.
    return None


async def get_credentials(bot, embed, author, author2):
    name = author
    creds = search_creds(name)
    author = author2

    if not creds or not creds.valid:
        # Send a request to refresh for the user's credentials if they are expired.
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        # Send a request to ask for the user's credentials if they do not have any registered.
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            flow.redirect_uri = "https://google.com"
            auth_url, _ = flow.authorization_url(prompt='consent')
            embed.description = f"To authorize the bot to access your calendar, sign in [here]({auth_url}) " \
                                "and then respond to this message with the resulting url."

            await author.send(embed=embed)
            try:
                response = await bot.wait_for("message", timeout=100)
                code = response.content
                # Slice the url to contain only the authorization code.
                code = code[code.find("code=") + 5:]
                code = code[:code.find('&')]
                # Use the inputted authorization code to fetch the user's token.
                flow.fetch_token(code=code)
                creds = flow.credentials
            except InvalidGrantError:
                await author.send("No valid code was sent. Please try again later.")
                return
            except TimeoutError:
                await author.send("The request timed out. Please try again later.")
                return

        # Write the contents of creds to a json file to be read and converted to a dictionary
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
        with open('token.json', 'r') as token:
            credentials = json.load(token)

        if os.path.exists('tokens.json'):
            with open('tokens.json', 'r') as tokens:
                data = json.load(tokens)
            # Overwrite the json file with the updated data dictionary.
            with open('tokens.json', 'w') as tokens:
                # Update the credentials in the json data
                if name in data:
                    data.update({name: credentials})
                else:
                    data[name] = credentials
                json.dump(data, tokens)
        # Create a json if it does not already exist.
        else:
            with open('tokens.json', 'w') as tokens:
                data = {name: credentials}
                json.dump(data, tokens)

        await author.send("Credentials received successfully.")
        return
    await author.send("You already have valid calendar credentials registered.")


# Search calendar for Discord bot.
async def search_calendar(mentions_string, date, mentions_real):
    name = mentions_string

    start_date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
    # Add one day to start_date to create a 24-hour window for events.
    end_date = start_date + timedelta(days=1)

    # Change the timezone to EST.
    start_date = start_date.isoformat() + '-05:00'
    end_date = end_date.isoformat() + '-05:00'

    creds = search_creds(name)

    try:
        service = build('calendar', 'v3', credentials=creds)

        # Call the Calendar API.
        await mentions_real.send("Getting the upcoming 10 events.")
        events_result = service.events().list(calendarId='primary', timeMax=end_date, timeMin=start_date,
                                              maxResults=10, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            await mentions_real.send("No upcoming events found.")
            return

        # Prints the start and name of the next 10 events.
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            start = datetime.strftime(parse(start), format='%H:%M, on %d %B.')
            this_event = event['summary']
            await mentions_real.send(f"You have {this_event} at {start}!")
    except HttpError as error:
        await mentions_real.send("An error occurred: %s" % error)
    except UnboundLocalError:
        await mentions_real.send("The username has not been registered to a calendar.")
    return


async def add_event(start, length, summary, author):
    name = str(author)
    creds = search_creds(name)
    summary = " ".join(summary)

    start = datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
    end = start + timedelta(hours=float(length))

    # Change the timezone to EST.
    start = start.isoformat() + '-05:00'
    end = end.isoformat() + '-05:00'

    try:
        service = build('calendar', 'v3', credentials=creds)

        event = {
            'summary': summary,
            'start': {
                "dateTime": start
            },
            'end': {
                "dateTime": end
            }
        }
        service.events().insert(calendarId='primary', sendNotifications=True, body=event).execute()
        await author.send("Event added to calendar successfully.")
    except UnboundLocalError:
        await author.send("You have not registered a calendar to your account. You can start by entering '!calendar'.")
