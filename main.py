from slackclient import SlackClient
from datetime import datetime
from dateutil.parser import parse 
from dateutil.tz import gettz
from datetime import timedelta 
import pytz
import json
import requests
import os
import time
import xml.etree.ElementTree as et
from bs4 import BeautifulSoup

# Return the difference in hours (d1 - d2) 
def compare_date(d1, d2):
    return (d1 - d2).total_seconds() / 60 / 60

def slack_call(attachments, header_text):
    slack_token = os.environ['SLACK_API_TOKEN']
    sc = SlackClient(slack_token)
    attachments_json = json.dumps(attachments)
    sc.api_call(
        'chat.postMessage',
        channel='#test',
        text=header_text,
        attachments=attachments_json
    ) 

# Get amazon deals from RSS Feed
def retrieve_amazon_from_goldbox():
    return requests.get('http://rssfeeds.s3.amazonaws.com/goldbox')

r = retrieve_amazon_from_goldbox()

# Format the xml response
soup = BeautifulSoup(r.text, 'xml')
# Get all <item> tag in the list
items = soup.find_all('item')

# Get current date in UTC
current_time = datetime.utcnow().replace(tzinfo=pytz.UTC)
attachments = []

# Loop through all the <item> tag
for item in items:
    # Get the published date and conver to UTC
    pub_date = parse(item.find('pubDate').text, ignoretz=True).replace(tzinfo=pytz.UTC)
    # print('Time: ', current_time, ' vs ', pub_date, item.find('pubDate').text)
    # We only want to get offers started in the last 3 hours 
    if compare_date(current_time, pub_date) > 3 or compare_date(current_time, pub_date) <= 0:
        # Skip this item if the offer did not start in the last 3 hours 
        continue
    description_html = BeautifulSoup(item.find('description').text, 'html.parser')
    details_meta = description_html.find_all('td')
    standard_offer_format = {
        'title': item.find('title').text,
        'title_link': item.find('link').text
    }
    # Check whether it's a deal
    if 'Deal Price' in details_meta[3].text:
        # Format for a deal 
        deal_price = details_meta[3].text
        original_price = details_meta[2].text
        savings = details_meta[4].text
        dict_offer = {
            'text': '~{0}~, {1}, \n{2}'.format(original_price, deal_price, savings),
            'mrkdwn_in': ['text']
        }
        attachments.append(dict(standard_offer_format, **dict_offer))
    else:
        offer_desc = details_meta[2].text
        dict_offer = {
            'text': offer_desc
        }
        attachments.append(dict(standard_offer_format, **dict_offer))
print(len(attachments))
header_text = 'New offers from Amazon on {0}'.format(current_time.strftime('%d %B %Y'))
slack_call(attachments, header_text)
