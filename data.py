from twilio.rest import Client
from decouple import config

client = Client(config('TWILIO_ACCOUNT_SID'), config('TWILIO_AUTH_TOKEN'))

client.messages.create(
        to=config('TWILIO_MYPHONE'),
        from_=config('TWILIO_NUMBER'),
        body='I sent a text message from twilio! ' + u'\U0001f680')