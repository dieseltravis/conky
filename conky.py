#!/usr/bin/python3
# -*- coding: utf-8 -*-
# original conky bot was in ruby https://gist.github.com/dieseltravis/474412a3ea2c64951312
# portions of @lynnesbian's mstdn-ebooks below, license: Mozilla Public License Version 2.0.txt

from mastodon import Mastodon, StreamListener
from datetime import date, datetime
from bs4 import BeautifulSoup
import asyncio, json, logging, random, re, schedule

# conky's words from the show's 5 seasons, in order
WORDS = [
	["DOOR"],["FUN"],["HELP"],["LITTLE"],["BACK"],["TIME"],["DAY"],["WHAT"],["LOOK"],["GOOD"],["THERE"],["OKAY"],["THIS"],
	["HOUSE","PLAYHOUSE"],["OVER"],["MORE"],["OUT"],["ALL"],["COOL"],["EASY"],["BEGIN"],["ZYZZYBALUBAH"],["WATCH"],
	["NOW"],["IT"],
	["WELL"],["ONE"],["END"],["GO"],["NICE"],["STOP"],["HERE","HEAR"],["WAIT"],["THAT"],["REMEMBER"],
	["GREAT","GRRRRR"],["AROUND"],["HOW"],["FAST"],["THING"],["PLACE"],["ON","NO"],["SHOW"],["DO"],["WORD"]
]

MATCH_MENTION = re.compile(r"https://([^/]+)/(@[^\s]+)")
REPL_MENTION = r"\2@\1"
MATCH_PLMENTION = re.compile(r"https://([^/]+)/users/([^\s/]+)")
REPL_PLMENTION = r"@\2@\1"
MATCH_USER = re.compile(r"^@[^@]+@[^ ]+\s*")
RE_EMPTY = r""

word = []
rx_match_word = re.compile(r'(conky_3000)')
last_word_date: date
last_word_datetime: datetime
_client: Mastodon = None  # type: ignore

# load values from json formatted .config file
config = json.load(open(".config", 'r'))

def create() -> Mastodon:
	client: Mastodon
	try:
		client = Mastodon(
				client_id = config["key"],
				client_secret = config["secret"],
				access_token = config["token"],
				api_base_url = config["api_base_url"],
				user_agent = "conky v2.0 (using mastodonpy)"
			)
	except Exception as error:
		logging.error(repr(error))
		exit()
	return client

def update_todays_word():
	global word
	global rx_match_word
	global last_word_date
	global last_word_datetime

	today: date = date.today()
	today_num = today.timetuple().tm_yday
	word_index = today_num % len(WORDS)

	# Pee-Wee's Christmas, Merry Merry Christmas!
	if (today.month == 12 and today.day > 23) or (today.month == 1 and today.day == 1):
		logging.info("Christmas Special!")
		word = ["YEAR"]
	else:
		word = WORDS[word_index]
	logging.debug(word)

	# update globals
	rx_match_word = re.compile("\\b(" + ("|".join(word)) + ")\\b", re.I)
	logging.debug(rx_match_word)
	last_word_date = today
	last_word_datetime = datetime.now()

def conky_scream_real_loud() -> str:
	# start loud for a few bytes
	return ('A' * random.randrange(1, 32) +
		# tone it down for a byte or two
		'a' * random.randrange(1, 16) +
		# exhale for a byte or two
		'h' * random.randrange(1, 16) +
		# punctuate but only a byte's worth
		'!' * random.randrange(1, 8) +
		# random binary conky glitch
		"{:08d}".format(int(format(random.getrandbits(8), 'b'))))

def get_html_text(html: str) -> str:
  return BeautifulSoup(html, "html.parser").get_text()

# Mastodon actions:
def follow(client: Mastodon, user_id):
	logging.info("Follow user: " + str(user_id))
	try:
		client.account_follow(user_id, reblogs=False)
	except Exception as error:
		logging.error(repr(error))
		pass

def unfollow(client: Mastodon, user_id):
	logging.info("Unfollow user: " + str(user_id))
	try:
		client.account_unfollow(user_id)
	except Exception as error:
		logging.error(repr(error))
		pass

def favorite(client: Mastodon, status_id):
	logging.info("Fav status: " + str(status_id))
	try:
		client.status_favourite(status_id)
	except Exception as error:
		logging.error(repr(error))
		pass

def reply(client: Mastodon, toot, text):
	toot_text = "@" + toot['account']['acct'] + " " + text
	logging.info("Reply: " + toot_text)
	try:
		client.status_post(toot_text, in_reply_to_id = toot)
	except Exception as error:
		logging.error(repr(error))

def check_toot(client: Mastodon, toot):
	# don't check boosts
	if toot['reblog'] is not None: return
	logging.info("not a reblog")
	# only check public
	if toot['visibility'] not in ["public"]: return
	logging.info("public")
	# skip favorited since they've already been processed
	if toot['favourited']: return
	logging.info("not fav'd")
	# make sure it is since the last secret word set time
	if toot['created_at'].timestamp() < last_word_datetime.timestamp(): return
	logging.info("created since last word")
	# check for bot and skip
	if toot['account']['bot']: return
	logging.info("not a robot")

	# check for text to stop following
	logging.info(toot['content'])
	toot_text = get_html_text(toot['content'])
	logging.info(toot_text)

	# from @lynnesbian:
	# https://github.com/Lynnesbian/mstdn-ebooks/blob/master/reply.py
	# remove the initial mention
	toot_compare = MATCH_USER.sub(RE_EMPTY, toot_text)
	# treat text as lowercase for easier keyword matching (if this bot uses it)
	toot_compare = toot_compare.lower()

	# check for stop command
	if toot_compare == "stop" or toot_compare == "unfollow":
		logging.info("Unfollow message from " + toot["account"]["username"] + ":" + toot_text)
		unfollow(client, toot["account"]["id"])
		return

	test_text = ""
	# only check CW text if added
	if toot['spoiler_text'] != "":
		test_text = toot['spoiler_text']
	else:
		test_text = toot_text
	logging.debug(rx_match_word)
	search = rx_match_word.search(test_text)
	logging.debug(search)
	if (search):
		favorite(client, toot)
		reply(client, toot, conky_scream_real_loud() + "\n #SecretWord")

# Mastodon event handlers:
def on_message(client: Mastodon, dm):
	# Reply to a DM
	dm_text = get_html_text(dm['content'])
	logging.info("DM from " + dm["account"]["username"] + ": " + dm_text)
	# skip favorited since they've already been processed
	if dm['favourited']: return
	logging.info("not fav'd")
	# check for bot and skip
	if dm['account']['bot']: return
	logging.info("not a robot")
	toot_text = "@" + dm['account']['acct'] + " ask " + config["author"]
	favorite(client, dm)
	try:
		client.status_post(toot_text, in_reply_to_id = dm, visibility = "direct")
	except Exception as error:
		logging.error(repr(error))
		pass

def on_follow(client: Mastodon, user):
	# Follow a user back
	logging.info("following " + user["username"])
	follow(client, user['id'])

def on_unfollow(client: Mastodon, user):
	# Unfollow a user
	logging.info("unfollowing " + user["username"])
	follow(client, user['id'])

def on_timeline(client: Mastodon, toot):
	check_toot(client, toot)

class TimelineListener(StreamListener):
	def __init__(self):
		logging.info("Listener created.")

	def on_notification(self, notification):
		logging.info("Notification: " + notification['type'])
		if notification['type'] == 'follow':
			on_follow(_client, notification['account'])

	def on_update(self, update):
		logging.info("Update: " + update['visibility'])
		if update['visibility'] == 'public':
			on_timeline(_client, update)
		if update['visibility'] == 'direct':
			on_message(_client, update)

def client_start():
	global _client
	logging.info("Starting client...")
	if _client is None:
		_client = create()
		logging.info("Starting listener")
		listener = TimelineListener()
		# run async and reconnect if necessary, waiting 300 seconds
		_client.stream_user(listener, run_async = True, reconnect_async = True, reconnect_async_wait_sec = 300)
	logging.info("Started client.")

def conky_start(do_toot = True):
	global word
	logging.info("Starting conky")
	logging.info(datetime.now().isoformat())
	update_todays_word()
	if do_toot:
		toot_text = "Today's secret word is: \n\n" + (" and ".join(word))
		logging.info(toot_text)
		_client.status_post(toot_text)
	logging.info("Started conky.")

async def scheduler_start():
  # does this even work async?
	logging.info("Starting scheduler")
	schedule.every().day.at('09:00').do(conky_start)
	# use listener to read user stream
	while True:
		schedule.run_pending()
		await asyncio.sleep(1)

async def main():
	logging.basicConfig(filename='conky.log',level=logging.DEBUG)
	logging.info(datetime.now().isoformat())
	logging.info("Pee-Wee's Playhouse!")

	client_start()
	scheduler_task = asyncio.create_task(scheduler_start())
	conky_start(False)
	logging.info("Tasks created.")
	await asyncio.gather(scheduler_task)

if __name__ == "__main__":
	asyncio.run(main())
