import subprocess, time, json, datetime, os, sys
import constants, auth

def main():
	while(1):
		apiUrl = auth.API_DATA_URL % (constants.GAME_ID)
		command = constants.BASE_CURL % (apiUrl)

		# make call
		try:
			process = subprocess.check_output(('timeout %d {}' % (constants.CURL_TIMEOUT)).format(command), shell=True, stderr=subprocess.PIPE)
		except subprocess.CalledProcessError as exc:
			if exc.returncode == 124:
				log("Reached timeout of %d seconds on curl." % (constants.CURL_TIMEOUT))
				time.sleep(constants.SLEEP_TIME)
				continue

		currentTurn = json.loads(process)
		processCurl(currentTurn)
		time.sleep(constants.SLEEP_TIME)

def processCurl(currentTurn):
	# read data file
	with open(constants.TURN_FILE, 'a+') as turnFile:
		# if first scan
		if os.path.getsize(constants.TURN_FILE) is 0:
			currentTurn['turn_num'] = 1
			turnFile.write(json.dumps([currentTurn]))
			log("First scan! Starting turn #%d! Wrote to %s." % (currentTurn['turn_num'], constants.TURN_FILE))
			return

		turnData = json.loads(turnFile.read())
		currentTurn['turn_num'] = len(turnData) + 1

		lastTurn = turnData[len(turnData) - 1]

		# if this scan has a different end time than the last turn saved (i.e. new turn)
		if (str(currentTurn['turn_based_time_out']) != str(lastTurn['turn_based_time_out'])):
			turnData.append(currentTurn)
			turnFile.seek(0)
			turnFile.truncate()
			turnFile.write(json.dumps(turnData))
			log("Starting turn #%d! Wrote to %s." % (currentTurn['turn_num'], constants.TURN_FILE))
			postToSlack(currentTurn, lastTurn)

def postToSlack(currentTurn, lastTurn):
	log("Posting to slack...")
	attachments = []

	players = sorted(currentTurn['players'], key=lambda k: k['rank']) 

	for player in players:
		# get this player last turn
		for lastPlayer in lastTurn['players']:
			if player['name'] == lastPlayer['name']:
				playerLastTurn = lastPlayer

		# determine rank change
		if player['rank'] > playerLastTurn['rank']:
			rankDif = "(:red-down: %d )" % (player['rank'] - playerLastTurn['rank'])
		elif player['rank'] < playerLastTurn['rank']:
			rankDif = "(:green-up: %d )" % (playerLastTurn['rank'] - player['rank'])
		else:
			rankDif = ""

		title = '%d. %s %s' % (player['rank'], player['name'], rankDif)
		text = ':np-econ: %d :np-ind: %d :np-sci: %d' % (player['total_economy'], player['total_industry'], player['total_science'])

		attachments.append({
			'color': player['color'],
			#'author_icon': 'https://np.ironhelmet.com/images/avatars/160/%d.jpg' % (player['avatar']),
			'title': title,
			'text': text
		})

	# add turn end footer
	turnEnd = datetime.datetime.fromtimestamp(int(currentTurn['turn_based_time_out'] / 1000)).strftime('%a, %b %-d at %-I:%M:%S %p')
	attachments.append({
		'color': '#FFFFFF',
		'footer': 'This turn ends %s.' % (turnEnd)
	})

	post = {
        'username': constants.SLACK_USER,
        'channel': auth.SLACK_CHANNEL,
        'icon_url': constants.SLACK_ICON,
        'attachments': attachments,
		'text': 'Turn *%d* just started! Here is the leaderboard:' % (currentTurn['turn_num'])
    }

	command = constants.SLACK_CURL % (json.dumps(post), auth.SLACK_HOOK)
	process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def log(str):
	p = "%s : %s" % (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'), str)
	print(p)
	with open("log", "a") as l:
		l.write("%s\n" % p)

if __name__ == "__main__":
	main()
