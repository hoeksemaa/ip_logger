import argparse
from twilio.rest import Client

import twilio_auth
import contacts
import re
from ip2geotools.databases.noncommercial import DbIpCity
from datetime import datetime, timedelta

def send_twilio_text(message, from_number, to_number, client):
	message = client.messages \
		.create(
			body=message,
			from_=from_number,
			to=to_number
	)

def get_args():
	parser = argparse.ArgumentParser()
	parser.add_argument("-p", "--person", type=str, required=True, help="name of the person to send image to")
	parser.add_argument("-f", "--filepath", type=str, required=True, help="name of the ip log filepath to scrape from")
	args = vars(parser.parse_args())
	return args

def init_client():
	client = Client(
		twilio_auth.creds["account_sid"],
		twilio_auth.creds["auth_token"])
	return client

def get_ips(filepath):
	pattern = r'^(\d+\.\d+\.\d+\.\d+) \S+ \S+ \[(.*?)\] "(.*?)" (\d{3}) (\d+|-) "(.*?)" "(.*?)"'
	f = open(filepath, "r")
	data = []
	for line in f:
		columns = re.split(pattern, line)
		data.append(columns)
	return data

def filter_ips(data):
	counts = {}
	counts["total"] = 0
	return [request[1] for request in data if request[4] == '200']
	for ip in valid_requests:
		if ip not in counts.keys():
			counts[ip] = 0
		counts[ip] += 1
		counts["total"] += 1
	return counts

def get_response(ip, max_retries=5, delay=5):
	for i in range(max_retries):
		try:
			response = DbIpCity.get(ip, api_key='free')
			return response
		except Exception as e: # Catching broad exception for simplicity. Ideally, handle specific exceptions.
			if i < max_retries - 1:  # i is 0 indexed
				print(f"Error: {e}. Retrying in {delay} seconds...")
				time.sleep(delay)
				delay *= 2  # Double the delay for exponential backoff
			else:
				print("Max retries reached. Exiting.")
				raise

def geolocate_ips(data):
	cities = {}
	countries = {}
	total = 0
	for ip in data:
		response = get_response(ip)
		if response.city not in cities.keys():
			cities[response.city] = 0
		if response.country not in countries.keys():
			countries[response.country] = 0
		countries[response.country] += 1
		cities[response.city] += 1
		total += 1
	return cities, countries, total

def format_msg(bundle):
	cities, countries, total = bundle
	cities = dict(sorted(cities.items(), key=lambda x: x[1], reverse=True))
	countries = dict(sorted(countries.items(), key=lambda x: x[1], reverse=True))
	yesterday = datetime.now() - timedelta(days=1)
	msg = str(yesterday.date()) + " ip report on 200 codes:" + '\n\n'
	msg += "Total: " + str(total)
	msg += "\n\nCities ordered:"
	for key in cities.keys():
		msg += '\n'
		msg += str(key) + ": "
		msg += str(cities[key])
	msg += "\n\nCountries ordered:"
	for key in countries.keys():
		msg += '\n'
		msg += str(key) + ": "
		msg += str(countries[key])
	return msg

def main():
	args   = get_args()
	client = init_client()
	data   = get_ips(args["filepath"])	
	data   = filter_ips(data)
	bundle = geolocate_ips(data)
	msg    = format_msg(bundle)
	send_twilio_text(
		msg, 
		contacts.contacts["twilio"], 
		contacts.contacts[args["person"]], 
		client)

if __name__=='__main__':
    main()
