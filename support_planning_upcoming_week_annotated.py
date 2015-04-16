# We're importing all of the modules we'll need for the script. 

import re # Regexes
import random # Ability to generate random numbers.
import requests # For making HTTP (GET, PUT, etc.) requests
import sys # For interacting with the interpreter.
from pprint import pprint # For pretty printing.
import json # To interpret JSON.
from datetime import datetime # For manipulating date and time.
from settings import TRELLO_KEY, TRELLO_TOKEN # We need the API key and token to make Trello API requests, we're getting them from the settings file.
from texttable import Texttable # For printing text in formatted ASCII tables.
from email_support_stats import send_email, TABLE_CSS, table_css_dict # We're importing how to send an email and format a table from another file we keep on Scout for doing that.
import cStringIO # For manipulating file data as strings. This one (rather than stringIO) is written in C for speed.
import time # For manipulating time.
import util # Importing util, used with the JSON module.
import cgi # For running CGI.

# These are variables we'll pass in to our email (email_support_stats knows what to do with it), and our Trello API call.

SUBJECT = "Support Planning - cards for this week"
id_list_for_this_week = "5502ee221bd87cffdb55b78a"

from optparse import OptionParser # To help parse our scripts options—see below.

# These are the options for the file. So, you could run it as python support_planning_upcoming_week.py --no-header, and a header wouldn't be included. That's my understanding.

parser = OptionParser()
# parser.add_option('-w', '--weeks_back', metavar='N', type=int, default=0,
#                    help='number of weeks back')
parser.add_option('--header',dest='header',action='store_true', help="include the header in the output")
parser.add_option('--no-header',dest='header',action='store_false', help="don't include the header in the output")
parser.add_option('--quiet',dest='quiet',action='store_true', help="don't print final output")
parser.add_option('--email_settings', metavar='example.json', dest='email_settings_file',type=str,
                  default='', help="send email based on email settings file")
parser.set_defaults(header=True, quiet=False)

(options, args) = parser. parse_args()

# Assigning variables to the settings we configured just above.

# weeks_back = options.weeks_back
header = options.header
quiet = options.quiet
email_settings_file = options.email_settings_file


base = 'https://trello.com/1/' # This is the base URL from which our Trello API calls are built out.
params_key_and_token = {'key':TRELLO_KEY,'token':TRELLO_TOKEN} # Providing the Trello API key and token, which we'll pass.
id_board = '34mdhhef' # Support Planning board.
data = {
  "cards" : "visible",
  "members" : "all",
  "lists" : "all"
} # These are filtering options for the API call.

url = '%sboards/%s' % (base, id_board) # We're making a call to base+boards/+the board ID, so https://www.trello.com/1/boards/34mdhhef
response = requests.get(url, params=params_key_and_token, data = data) # We're storing the response to a GET request made to that URL, with our API key and token as parameters of the URL, and our data (the cards, members, and lists option) passed as HTTP request data.

board = response.json() # Taking the response, parsing it as JSON, storing it in board.
cards = board['cards'] # Storing the cards as a list of the nested "cards" parameter.
lists = board['lists'] # Same, but "lists" parameter.
members = board['members'] # And same, but "members" parameter

# Pass the member ID to Trello, get the full name back. We've defined it as a function so we can sub in each person's member ID.

def get_member_full_name(id_member):
  matches = [m for m in members if m["id"] == id_member] 
  return matches[0]["fullName"] if matches else None

# Getting the name of the list, based on the list ID. Defined as a function.

def get_list_name(id_list):
  matches = [l for l in lists if l["id"] == id_list]
  return matches[0]["name"] if matches else None

# If the list that a card is on matches the list that we give to the script, give us back the card ID.

def get_cards_in_list(id_list):
  return [c for c in cards if c["idList"] == id_list]

# We're pulling up the cards, storing the card name, url, link, and assigned member (whose name we pull from that previously-defined function, based on their ID). Then, we store the results in the cards_with_info list.

def get_card_info_to_print(cards):
  cards_with_info = []
  for card in cards:
    card_info = {} 
    card_info["name"] = card["name"]
    card_info["url"] = card["url"]
    card_info["html_link"] = '<a href="%s">%s</a>' % (card["url"], cgi.escape(card["name"]))
    card_info["member_names"] = ", ".join([get_member_full_name(id_member) for id_member in card["idMembers"]])
    cards_with_info.append(card_info)
  return cards_with_info

# Formatting our ASCII table.

def output_texttable_string(cards):
  table = Texttable()
  table.set_cols_width([40, 40])
  table.header(['Card title', 'Members'])
  for card in cards:
    table.add_row([card["name"], card["member_names"]])

  return table.draw()

# Formatting our HTML table.

def output_to_html(cards):
  output_html = cStringIO.StringIO()
  output_html.write('<table style="%s">\n' % table_css_dict['table_th_td'])
  output_html.write("  <tr>\n")
  
  output_html.write('    <td style="%s%s">%s</td>\n' % (table_css_dict['table_th_td'], table_css_dict['td'], "Card title"))
  output_html.write('    <td style="%s%s">%s</td>\n' % (table_css_dict['table_th_td'], table_css_dict['td'], "Members"))
  
  output_html.write("  </tr>\n")
  for card in cards:
    output_html.write("  <tr>\n")
    
    output_html.write('    <td style="%s%s">%s</td>\n' % (table_css_dict['table_th_td'], table_css_dict['td'], card["html_link"]))
    output_html.write('    <td style="%s%s">%s</td>\n' % (table_css_dict['table_th_td'], table_css_dict['td'], card["member_names"]))
    
    output_html.write("  </tr>\n")
  output_html.write("</table>")
  return output_html  

cards_for_this_week = get_cards_in_list(id_list_for_this_week) # Actually running the function.

cards_info_to_print = get_card_info_to_print(cards_for_this_week) # Filtering those results to get only the stuff we want to print.

text = output_texttable_string(cards_info_to_print) # Generating the ASCII version of the info we want to print.

### This sends the email, if there is information to send. If not, no email is sent.

if email_settings_file:
  output_html = output_to_html(cards_info_to_print)
  resp = send_email(email_settings_file, SUBJECT, text, output_html.getvalue())
  if not quiet:
    print resp
if not quiet:
  print text

#print get_member_full_name("5473527f207b1f22447db5c0")

#print util.json_to_string_indented(cards_info_to_print)