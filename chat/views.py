from datetime import datetime
import time

from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.contrib import messages as alert_messages
from django.core.cache import cache
from django.utils import timezone

from twilio.rest import Client
from twilio.http.http_client import TwilioHttpClient
from twilio.base.exceptions import TwilioRestException, TwilioException




client=None
save_cache = 1

def login(request):


	if request.method == "POST":

		account_sid = request.POST['account_sid']
		auth_token = request.POST['auth_token']

		# proxy = ""
		# proxy_client = TwilioHttpClient(proxy={'http': proxy, 'https': proxy})
		# proxy_client = TwilioHttpClient(proxy={'http': proxy})
		global client
		try:
			# client = Client(account_sid, auth_token, http_client=proxy_client)
			client = Client(account_sid, auth_token)
		except TwilioException as e:
			messages.error(request, e)
			return redirect(login)

		global save_cache
		if "cancel" in request.POST:
			save_cache = 0
		else:
			save_cache = 1


		try:
			client.verify.services.list()
			if(save_cache==1 or save_cache==0):
				print("----Setting cache")
				cache.set("account_sid", account_sid, None)
				cache.set("auth_token", auth_token, None)
				
				phone_numbers = client.incoming_phone_numbers.list()

				cache.set("twilio_numbers", phone_numbers, None)
				
				if(cache.get("all_chats")==None):
					msgs = client.messages.list()
					all_chats = {}
					phone_numbers_pn = [pn.phone_number for pn in phone_numbers]
					
					for msg in msgs:
						if msg.to not in phone_numbers_pn:
							target_number = msg.to
						else:
							target_number = msg.from_

						if target_number in all_chats:
							all_chats[target_number].append({"from_number": msg.from_, "to_number": msg.to, "message": msg.body, "transmission_time_stamp": msg.date_sent, "status": msg.status, "sid": msg.sid})
						else:
							all_chats[target_number] = [{"from_number": msg.from_, "to_number": msg.to, "message": msg.body, "transmission_time_stamp": msg.date_sent, "status": msg.status, "sid": msg.sid}]
					
					cache.set("all_chats", all_chats, None)

		except TwilioException as e:
			client=None
			messages.error(request, "Ensure you authenticate with the correct information")
		except:
			client=None
			messages.error(request, "Error occurred")

		return redirect(index)


	account_sid = cache.get("account_sid")
	auth_token = cache.get("auth_token")
	if account_sid!=None:
		if auth_token!=None:
			print("----Redirect from login page to index page using cache")
			client = Client(account_sid, auth_token)

			return redirect(index)

	return render(request, "login.html")


def index(request, target_number=None, twilio_number=None):
	print("index client", client)
	if not client:
		print("----Redirect from index page to login page for 'client' initialization")
		return redirect(login)

	print("----Successfully landed index page")

	if target_number == "None":
		target_number = None

	if twilio_number == "None":
		twilio_number = None

	if target_number==None:

		tgt_nmb = list(cache.get("all_chats"))

		if len(tgt_nmb) > 0:
			target_number = tgt_nmb[0]
		else:
			target_number = None
		

	if twilio_number==None:
		twilio_number = cache.get("twilio_numbers")
		if twilio_number!=[]:
			twilio_number=twilio_number[0].phone_number
		else:
			twilio_number = None

	if request.method == "POST":
		if "text_area_btn" in request.POST:
			_message = request.POST["chatArea"]

			msg = client.messages.create(
			    to= target_number,
			    from_= twilio_number,
			    body = _message,
			)

			time.sleep(3)

			msg=client.messages.get(msg.sid).fetch()
			all_chats = cache.get("all_chats")
			if target_number!=None:
				if target_number in all_chats:
					all_chats[target_number].append({"from_number": msg.from_, "to_number": target_number, "message": msg.body, "transmission_time_stamp": msg.date_created, "status": "loading", "sid": msg.sid})
				else:
					all_chats[target_number] = [{"from_number": msg.from_, "to_number": target_number, "message": msg.body, "transmission_time_stamp": msg.date_created, "status": "loading", "sid": msg.sid}]
			cache.set("all_chats", all_chats, None)
		elif "new_target_number_btn" in request.POST:
			all_chats = cache.get("all_chats")
			new_number = request.POST["new_target_number"]

			try:
				client.lookups.phone_numbers(new_number).fetch()
				target_number = new_number
				if target_number not in all_chats:
					all_chats[target_number] = []
				cache.set("all_chats", all_chats, None)
			except TwilioException as e:

				if e.status == 404:
					alert_messages.error(request, f"{new_number} is not a valid phone number. Try again.")
				else:
					alert_messages.error(request, "Error occurred")
			except:
				alert_messages.error(request, "Error occurred")

		else:

			try:
				_message = request.POST["chatArea"]

				msg = client.messages.create(
				    to= target_number,
				    from_= twilio_number,
				    body = _message,
				)

				time.sleep(3)

				msg=client.messages.get(msg.sid).fetch()
				all_chats = cache.get("all_chats")
				if target_number!=None:
					if target_number in all_chats:
						all_chats[target_number].append({"from_number": msg.from_, "to_number": target_number, "message": msg.body, "transmission_time_stamp": msg.date_created, "status": "loading", "sid": msg.sid})
					else:
						all_chats[target_number] = [{"from_number": msg.from_, "to_number": target_number, "message": msg.body, "transmission_time_stamp": msg.date_created, "status": "loading", "sid": msg.sid}]
				cache.set("all_chats", all_chats, None)
			except:
				alert_messages.error(request, "Error occurred")
				return redirect(index)


	twilio_numbers = []
	for number in cache.get("twilio_numbers"):
		twilio_numbers.append(number.phone_number)

	messages = cache.get("all_chats")

	target_messages = []

	for message in messages.get(target_number, []):
		if message["status"] == "loading":
			msg=client.messages.get(message["sid"]).fetch()
			message["status"] = msg.status
		if message["from_number"] == twilio_number:
			target_messages.append(message)
		if message["to_number"] == twilio_number:
			target_messages.append(message)

	
	target_messages.sort(key=lambda x: x["transmission_time_stamp"])

	twilio_numbers = list(set(twilio_numbers))
	twilio_numbers.sort()

	return render(request, "chat.html", {
		"target_messages": target_messages, "target_number": target_number, "twilio_number": twilio_number, "twilio_numbers": twilio_numbers, "all_messages": messages
	})



def twilioNumbers(request):
	if not client:
		print("----Redirect from twilioNumbers page to login page for 'client' initialization")
		return redirect(login)

	print("----Successfully landed twilioNumbers page")
	countries = [(i.country, i.country_code) for i in client.available_phone_numbers.list()]
	countries.sort()

	if request.method == "POST":

		country_code = request.POST['countries']
		available_phone_numbers = client.available_phone_numbers(country_code).local.list()
		phone_numbers = cache.get("twilio_numbers")

		return render(request, "twilio_numbers.html", {"numbers": phone_numbers, "countries": countries, "available_phone_numbers": available_phone_numbers})

	phone_numbers = cache.get("twilio_numbers")

	return render(request, "twilio_numbers.html", {"numbers": phone_numbers, "countries": countries, "available_phone_numbers": None})



def buy_twilio_number(request, number):
	try:
		incoming_phone_number = client.incoming_phone_numbers.create(phone_number=number)
		messages.success(request, f"{number} added successfully.")
		phone_numbers = client.incoming_phone_numbers.list()
		cache.set("twilio_numbers", phone_numbers, None)
	except TwilioRestException as e:
		messages.error(request, e.msg)
	return redirect(twilioNumbers)




from django.views.decorators.csrf import csrf_exempt
@csrf_exempt
def sms(request):
	if request.method == "POST":
		
		body = request.POST["Body"]
		to_number = request.POST["To"]
		from_number = request.POST["From"]
		status = request.POST["SmsStatus"]
		sid = request.POST["SmsSid"]

		all_chats = cache.get("all_chats")

		if from_number in all_chats:
			all_chats[from_number].append({"from_number": from_number, "to_number": to_number, "message": body, "transmission_time_stamp": timezone.now(), "status": status, "sid": sid})
		else:
			all_chats[from_number] = [{"from_number": from_number, "to_number": to_number, "message": body, "transmission_time_stamp": timezone.now(), "status": status, "sid": sid}]

		cache.set("all_chats", all_chats, None)

	return HttpResponse("sms received")


def logout(request):
	cache.delete("account_sid")
	cache.delete("auth_token")
	cache.delete("all_chats")
	cache.delete("twilio_numbers")
	global client
	client = None
	print("----Deleted authentication cache and 'client' set to None")
	return redirect(login)