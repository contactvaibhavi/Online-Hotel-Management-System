from twilio.rest import Client

account_sid = 'AC4813fd548f065ee195b1aa2feb96c58f' # Found on Twilio Console Dashboard
auth_token = 'cda8141ecc84ab6ae0489aacab4d3586' # Found on Twilio Console Dashboard
myPhone = '+919013908350' # Phone number you used to verify your Twilio account
TwilioNumber = '+12692206694' # Phone number given to you by Twilio

client = Client(account_sid, auth_token)

client.messages.create(
        to=myPhone,
        from_=TwilioNumber,
        body='I sent a text message from twilio! ' + u'\U0001f680')