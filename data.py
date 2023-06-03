from twilio.rest import Client
from decouple import config

client = Client(config('ACCOUNT_SID'), config('AUTH_TOKEN'))

client.messages.create(
        to=config('MYPHONE'),
        from_=config('TWILIO_NUMBER'),
        body='I sent a text message from twilio! ' + u'\U0001f680')