#!/usr/bin/env python
# Cancer IRC Bot - Developed by acidvegas in Python (https://git.acid.vegas/cancer)

'''
WARNING: This bot highly encourages flooding!

Commands:
	@cancer       | Information about the bot
	@cancer help  | Show the list of commands
	@cancer stats | Return bot statistics for the channel
	!100          | 1 in 100 chance to get a 100 (big !smoke)
	!beer [nick]  | Grab a beer or toss one to someone
	!chainsmoke   | Start a game of Chain Smoke
	!chug         | Sip beer
	!dragrace     | Start a game of Drag Race
	!extendo      | 1 in 100 chance to get an EXTENDO (big !toke)
	!fatfuck      | 1 in 100 chance to get a  FATFUCK (fat !smoke/!toke)
	!football     | Pick up the football or see who has it
	!intercept    | 1 in 20 chance to steal the football within 30 seconds of a pass
	!letschug     | LET'S FUCKING CHUG!
	!letstoke     | LET'S FUCKING TOKE!
	!pass <nick>  | Pass the football to someone (1 in 20 chance it is incomplete)
	!tackle       | !tackle <nick> for a 1 in 20 chance to make the holder fumble (once every 5 minutes)
	!toke         | Hit joint
	!smoke        | Hit cigarette
	!nosmoking    | Disable the bot for 30 seconds
'''

import asyncio
import json
import os
import random
import ssl
import time

# Connection
server     = 'irc.supernets.org'
port       = 6697
use_ipv6   = False
use_ssl    = True
vhost      = None
channel    = '#dev'
key        = None

# Identity
nickname = 'CANCER'
username = 'smokesome'
realname = 'git.acid.vegas/cancer'

# Login
nickserv_password = None
network_password  = None
operator_password = None

# Settings
user_modes = 'BdDg' # +d requires additional ! and @ to be in your set::channel-command-prefix on UnrealIRCd
football_blocked = ('fuckyou','scroll','dealer','elimanning','events','guru') # lowercase nicks that can not play football

# Formatting Control Characters / Color Codes
bold        = '\x02'
italic      = '\x1D'
underline   = '\x1F'
reverse     = '\x16'
reset       = '\x0f'
white       = '00'
black       = '01'
blue        = '02'
green       = '03'
red         = '04'
brown       = '05'
purple      = '06'
orange      = '07'
yellow      = '08'
light_green = '09'
cyan        = '10'
light_cyan  = '11'
light_blue  = '12'
pink        = '13'
grey        = '14'
light_grey  = '15'

def color(msg, foreground, background=None):
	return f'\x03{foreground},{background}{msg}{reset}' if background else f'\x03{foreground}{msg}{reset}'

def debug(data):
	print('{0} | [~] - {1}'.format(time.strftime('%I:%M:%S'), data))

def error(data, reason=None):
	print('{0} | [!] - {1} ({2})'.format(time.strftime('%I:%M:%S'), data, str(reason))) if reason else print('{0} | [!] - {1}'.format(time.strftime('%I:%M:%S'), data))

def luck(odds):
	return True if random.randint(1,odds) == 1 else False

def ssl_ctx():
	ctx = ssl.create_default_context()
	ctx.check_hostname = False
	ctx.verify_mode = ssl.CERT_NONE
	return ctx

class Generate: # degenerate *
	async def can(chan, target):
		beer_choice = random.choice(['bud','modelo','ultra'])
		beer_temp   = random.choice(['a piss warm','an ice cold','an empty'])
		if beer_choice == 'bud':
			beer = '{0}{1}{2}'.format(color(' ', white, white), color(' BUD ', white, random.choice((blue,brown))), color('c', grey, white))
			await Cancer.action(chan, f'throws {color(target, white)} {beer_temp} {beer} =)')
			if luck(100):
				await asyncio.sleep(2)
				await Cancer.action(chan, 'suddenly feels more gay...')
		elif beer_choice == 'modelo':
			beer = '{0}{1}{2}'.format(color(' ', orange, orange), color('Modelo', blue, yellow), color('c', grey, orange)) # props to opal
			await Cancer.action(chan, f'throws {color(target, white)} {beer_temp} {beer} =)')
		elif beer_choice == 'ultra':
			beer = '{0}{1}'.format(color(' ULTRA ', blue, white), color('🬃', red, white)) # warm
			await Cancer.action(chan, f'throws {color(target, white)} {beer_temp} {beer} =)')

	def beer():
		glass = color(' ', light_grey, light_grey)
		return glass + color(''.join(random.choice(('       :.')) for _ in range(9)), orange, yellow) + glass

	def cigarette(size):
		filter    = color(';.`-,:.`;', yellow, orange)+color(' ', yellow, yellow)
		cigarette = color('|'*size, light_grey, white)
		cherry    = color('\u259A', random.choice((red,yellow,orange)), black)+color('\u259A', random.choice((red,yellow,orange)), grey)
		smoke     = color('-' + ''.join(random.choice((';:-.,_`~\'')) for _ in range(random.randint(5,8))), grey)
		return filter + cigarette + cherry + smoke

	def joint(size):
		joint    = color('/'*size, light_grey, white)
		cherry   = color('\u259A', random.choice((red,yellow,orange)), black)+color('\u259A', random.choice((red,yellow,orange)), grey)
		smoke    = color('-' + ''.join(random.choice((';:-.,_`~\'')) for _ in range(random.randint(5,8))), grey)
		return joint + cherry + smoke

	def mug(size):
		glass  = color(' ', light_grey, light_grey)
		empty  = f'{glass}         {glass}'
		foam   = glass + color(':::::::::', light_grey, white) + glass
		bottom = color('           ', light_grey, light_grey)
		mug   = [foam,Generate.beer(),Generate.beer(),Generate.beer(),Generate.beer(),Generate.beer(),Generate.beer(),Generate.beer()]
		for i in range(8-size):
			mug.pop()
			mug.insert(0, empty)
		for i in range(len(mug)):
			if i == 2 or i == 7:
				mug[i] += glass + glass
			elif i > 2 and i < 7:
				mug[i] += '  ' + glass
		mug.append(bottom)
		return mug

class Bot():
	def __init__(self):
		self.fat             = False
		self.event           = None
		self.nicks           = list()
		self.stats           = {'hits':25,'sips':8,'chugged':0,'smoked':0,'toked':0,'chain':0,'drag':0,'passes':0,'intercepts':0}
		self.loops           = {'chainsmoke':None,'dragrace':None,'letschug':None,'letstoke':None,'nosmoking':None,'timers':None}
		self.status          = True
		self.members         = dict() # lowercase nick -> nick
		self.ball            = None   # nick holding the football
		self.ball_idle       = 0      # last time the holder talked
		self.ball_pass       = None   # {'passer':nick,'time':time} for the !intercept window
		self.tackle_time     = 0
		self.reader          = None
		self.writer          = None

	async def raw(self, data):
		self.writer.write(data[:510].encode('utf-8') + b'\r\n')
		await self.writer.drain()

	async def action(self, chan, msg):
		await self.sendmsg(chan, f'\x01ACTION {msg}\x01')

	async def sendmsg(self, target, msg):
		await self.raw(f'PRIVMSG {target} :{msg}')

	async def notice(self, target, msg):
		await self.raw(f'NOTICE {target} :{msg}')

	async def connect(self):
		while True:
			try:
				options = {
					'host'       : server,
					'port'       : port,
					'limit'      : 1024,
					'ssl'        : ssl_ctx() if use_ssl else None,
					'family'     : 10 if use_ipv6 else 2,
					'local_addr' : vhost
				}
				self.reader, self.writer = await asyncio.wait_for(asyncio.open_connection(**options), 15)
				await self.raw(f'USER {username} 0 * :{realname}')
				await self.raw('NICK ' + nickname)
			except Exception as ex:
				error('error: failed to connect to ' + server, ex)
			else:
				if os.path.isfile('stats.json'):
					with open('stats.json') as stats_file:
						self.stats.update(json.loads(stats_file.read())) # update keeps new stats missing from an older stats.json
						debug('reloaded stats')
				await self.listen()
				for loop in self.loops:
					if self.loops[loop]:
						self.loops[loop].cancel()
				self.stats['chain'] = 0
				self.stats['drag']  = 0
				self.event  = None
				self.nicks  = list()
				self.status = True
				self.members   = dict()
				self.ball      = None
				self.ball_pass = None
			finally:
				await asyncio.sleep(30)

	async def help(self, chan):
		rows = [
			('@cancer',       None,     'information about the bot',                       None),
			('@cancer help',  None,     'show this help',                                  None),
			('@cancer stats', None,     'bot statistics for the channel',                  None),
			('!100',          None,     'get a 100 (big !smoke)',                          '(1 in 100)'),
			('!beer',         '[nick]', 'grab a beer or toss one to someone',              None),
			('!chainsmoke',   None,     'start a game of chain smoke',                     None),
			('!chug',         None,     'sip beer',                                        None),
			('!dragrace',     None,     'start a game of drag race',                       None),
			('!extendo',      None,     'get an EXTENDO (big !toke)',                      '(1 in 100)'),
			('!fatfuck',      None,     'get a FATFUCK (fat !smoke/!toke)',                '(1 in 100)'),
			('!football',     None,     'pick up the football or see who has it',          None),
			('!intercept',    None,     'steal the football within 30 seconds of a pass', '(1 in 20)'),
			('!letschug',     None,     'LET\'S FUCKING CHUG!',                           None),
			('!letstoke',     None,     'LET\'S FUCKING TOKE!',                           None),
			('!nosmoking',    None,     'disable the bot for 30 seconds',                  None),
			('!pass',         '<nick>', 'pass the football to someone',                    '(1 in 20 is incomplete)'),
			('!smoke',        None,     'hit cigarette',                                   None),
			('!tackle',       '<nick>', 'make the football holder fumble',                 '(1 in 20, once every 5 minutes)'),
			('!toke',         None,     'hit joint',                                       None)]
		width = max(len(command + (f' {arg}' if arg else '')) for command, arg, _, _ in rows) + 1
		await self.sendmsg(chan, color('COMMAND'.ljust(width) + 'DESCRIPTION', yellow))
		for command, arg, text, note in rows:
			plain = command + (f' {arg}' if arg else '')
			line  = command + (' ' + color(arg, cyan if arg.startswith('<') else pink) if arg else '') + ' ' * (width - len(plain)) + color('|', grey) + ' ' + text
			await self.sendmsg(chan, line + (' ' + color(note, grey) if note else ''))

	async def fumble(self, nick):
		if self.ball and nick.lower() == self.ball.lower():
			self.ball      = None
			self.ball_pass = None
			await self.action(channel, f'{color(nick, white)} fumbled the 🏈')

	async def football(self, nick, args):
		if nick.lower() in football_blocked:
			return
		if args == ['!football']:
			if self.ball:
				await self.action(channel, f'{color(self.ball, white)} has the 🏈')
			else:
				self.ball      = nick
				self.ball_idle = time.time()
				self.ball_pass = None
				await self.action(channel, f'{color(nick, white)} picks up the 🏈')
		elif args == ['!intercept'] and self.ball_pass and time.time() - self.ball_pass['time'] <= 30 and nick not in (self.ball, self.ball_pass['passer']):
			self.ball_pass = None
			if luck(20):
				victim         = self.ball
				self.stats['intercepts'] += 1
				self.ball      = nick
				self.ball_idle = time.time()
				await self.action(channel, f'{color(nick, white)} INTERCEPTS the 🏈 from {color(victim, white)}!')
			else:
				await self.action(channel, f'{color(nick, white)} tries to intercept the 🏈 from {color(self.ball, white)} and misses!')
		elif len(args) != 2:
			return
		elif args[0] == '!pass' and nick == self.ball:
			target = self.members.get(args[1].lower())
			if target and target.lower() not in football_blocked + (nick.lower(), nickname.lower()):
				if luck(20):
					self.ball      = None
					self.ball_pass = None
					await self.action(channel, f'{color(nick, white)}\'s pass to {color(target, white)} is incomplete! The 🏈 hits the ground.')
				else:
					self.ball      = target
					self.ball_idle = time.time()
					self.ball_pass = {'passer':nick,'time':time.time()}
					self.stats['passes'] += 1
					await self.action(channel, f'{color(nick, white)} passes the 🫳🏈 to {color(target, white)}.')
		elif args[0] == '!tackle' and self.ball and args[1].lower() == self.ball.lower() and nick != self.ball and time.time() - self.tackle_time >= 300:
			self.tackle_time = time.time()
			if luck(20):
				victim = self.ball
				await self.action(channel, f'{color(nick, white)} tackles {color(victim, white)}!')
				await self.fumble(victim)
				if luck(100):
					await self.raw(f'KICK {channel} {victim} :{victim} GOT CTE AND IS MADE FUCKING RETARDED')
			else:
				await self.action(channel, f'{color(nick, white)} tries to tackle {color(self.ball, white)} and misses!')

	async def loop_nosmoking(self):
		await asyncio.sleep(30)
		self.status = True

	async def loop_timers(self):
		while True:
			try:
				if self.ball and time.time() - self.ball_idle >= 86400:
					await self.fumble(self.ball)
				if time.strftime('%I:%M') == '04:20':
					await self.sendmsg(channel, color('S M O K E W E E D E R R D A Y', light_green))
					await self.sendmsg(channel, color('ITZ DAT MUTHA FUCKN 420 BITCH', yellow))
					await self.sendmsg(channel, color('LIGHT UP A NICE GOOD FAT FUCK', red))
					await asyncio.sleep(120)
				elif time.strftime('%I:%M %p') == '02:00 AM':
					await self.sendmsg(channel, '.ascii phish')
					await asyncio.sleep(120)
				elif time.strftime('%I:%M') == '12:00': # the biscuit hour..
					with open('stats.json', 'w') as stats_file:
						json.dump(self.stats, stats_file)
					await asyncio.sleep(120)
			except Exception as ex:
				error('error: loop_timers failed', ex)
			finally:
				await asyncio.sleep(20)

	async def loop_chainsmoke(self):
		self.nicks = dict()
		try:
			await self.notice(channel, 'Starting a round of {0} in {1} seconds!'.format(color('ChainSmoke', red), color('10', white)))
			await self.notice(channel, '[{0}] {1} {2} {3}'.format(color('How To Play', light_blue), color('Type', yellow), color('!smoke', light_green), color('to hit a cigarette. The cigarette goes down a little after each hit. Once you finish a cigarette, a new one will be lit for you. You will have 60 seconds to chain smoke as many cigarettes as possible.', yellow)))
			await asyncio.sleep(10)
			await self.action(channel, 'Round starts in 3...')
			await asyncio.sleep(1)
			await self.action(channel, '2...')
			await asyncio.sleep(1)
			await self.action(channel, '1...')
			await asyncio.sleep(1)
			await self.action(channel, color('GO', light_green))
			self.status = True
			await asyncio.sleep(60)
			self.status = False
			await self.sendmsg(channel, color('          CHAINSMOKE ROUND IS OVER          ', red, yellow))
			await asyncio.sleep(1)
			await self.sendmsg(channel, color('          CHAINSMOKE ROUND IS OVER          ', red, yellow))
			await asyncio.sleep(1)
			await self.sendmsg(channel, color('          CHAINSMOKE ROUND IS OVER          ', red, yellow))
			await self.sendmsg(channel, color('Counting cigarette butts...', yellow))
			await asyncio.sleep(10)
			await self.sendmsg(channel, '{0} smoked {1} cigarettes!'.format(channel, color(str(self.stats['chain']), light_blue)))
			if self.nicks:
				guy = max(self.nicks, key=self.nicks.get)
				await self.sendmsg(channel, '{0} smoked the most cigarettes... {1}'.format(guy, self.nicks[guy]))
		except Exception as ex:
			error('error: loop_chainsmoke failed', ex)
		finally:
			self.stats['chain'] = 0
			self.nicks  = list()
			self.event  = None
			self.status = True

	async def loop_dragrace(self):
		self.stats['hits'] = 25
		try:
			await self.notice(channel, 'Starting a round of {0} in {1} seconds!'.format(color('DragRace', red), color('10', white)))
			await self.notice(channel, '[{0}] {1} {2} {3}'.format(color('How To Play', light_blue), color('Type', yellow), color('!smoke', light_green), color('to hit a cigarette. The cigarette goes down a little after each hit. You will have 10 seconds to smoke as quickly as possible.', yellow)))
			await asyncio.sleep(10)
			await self.action(channel, 'Round starts in 3...')
			await asyncio.sleep(1)
			await self.action(channel, '2...')
			await asyncio.sleep(1)
			await self.action(channel, '1...')
			await asyncio.sleep(1)
			await self.action(channel, color('GO', light_green))
			self.stats['drag'] = time.time()
		except Exception as ex:
			error('error: loop_dragrace failed', ex)
		finally:
			self.status = True

	async def loop_letschug(self, nick):
		self.nicks.append(nick)
		try:
			await self.sendmsg(channel, color(f'OH SHIT {nick} is drunk', light_green))
			await self.notice(channel, color(f'Time to TOTALLY CHUG in {channel.upper()} in 30 seconds, type !chug to join', light_green))
			await asyncio.sleep(10)
			await self.sendmsg(channel, color('LOL we CHUG in 20 get ready ' + ' '.join(self.nicks), light_green))
			await asyncio.sleep(10)
			await self.sendmsg(channel, color('YO we CHUG in 10 get ready ' + ' '.join(self.nicks), light_green))
			await asyncio.sleep(5)
			await self.sendmsg(channel, color('alright CHUG in 5', light_green))
			await asyncio.sleep(1)
			await self.sendmsg(channel, color('4..', light_green))
			await asyncio.sleep(1)
			await self.sendmsg(channel, color('3..', light_green))
			await asyncio.sleep(1)
			await self.sendmsg(channel, color('2..', light_green))
			await asyncio.sleep(1)
			await self.sendmsg(channel, color('1..', light_green))
			await asyncio.sleep(1)
			await self.sendmsg(channel, color(' '.join(self.nicks) + ' .. CHUG!', light_green))
		except Exception as ex:
			error('error: loop_letschug failed', ex)
		finally:
			self.event = None
			self.nicks = list()

	async def loop_letstoke(self, nick):
		self.nicks.append(nick)
		try:
			await self.sendmsg(channel, color(f'YO {nick} is high', light_green))
			await self.notice(channel, color(f'Time to FUCKING toke in {channel.upper()}, type !toke to join', light_green))
			await asyncio.sleep(10)
			await self.sendmsg(channel, color('OH SHIT we toke in 20 get ready ' + ' '.join(self.nicks), light_green))
			await asyncio.sleep(10)
			await self.sendmsg(channel, color('OH SHIT we toke in 10 get ready ' + ' '.join(self.nicks), light_green))
			await asyncio.sleep(5)
			await self.sendmsg(channel, color('alright toke in 5', light_green))
			await asyncio.sleep(1)
			await self.sendmsg(channel, color('4..', light_green))
			await asyncio.sleep(1)
			await self.sendmsg(channel, color('3..', light_green))
			await asyncio.sleep(1)
			await self.sendmsg(channel, color('2..', light_green))
			await asyncio.sleep(1)
			await self.sendmsg(channel, color('1..', light_green))
			await asyncio.sleep(1)
			await self.sendmsg(channel, color(' '.join(self.nicks) + ' .. toke!', light_green))
		except Exception as ex:
			error('error: loop_letstoke failed', ex)
		finally:
			self.event = None
			self.nicks = list()

	async def listen(self):
		while True:
			try:
				if self.reader.at_eof():
					break
				data = await asyncio.wait_for(self.reader.readuntil(b'\r\n'), 500)
				line = data.decode('utf-8').strip()
				args = line.split()
				debug(line)
				if line.startswith('ERROR :Closing Link:'):
					raise Exception('Connection has closed.')
				elif args[0] == 'PING':
					await self.raw('PONG '+args[1][1:])
				elif args[1] == '001':
					if user_modes:
						await self.raw(f'MODE {nickname} +{user_modes}')
					if nickserv_password:
						await self.sendmsg('NickServ', f'IDENTIFY {nickname} {nickserv_password}')
					if operator_password:
						await self.raw(f'OPER {username} {operator_password}')
					await self.raw(f'JOIN {channel} {key}') if key else await self.raw('JOIN ' + channel)
					self.loops['timers'] = asyncio.create_task(self.loop_timers())
				elif args[1] == '433':
					error('The bot is already running or nick is in use.') # nick change
				elif args[1] == 'INVITE' and len(args) == 4:
					invited = args[2]
					chan    = args[3][1:]
					if invited == nickname and chan == channel:
						await self.raw(f'JOIN {channel} {key}') if key else await self.raw('JOIN ' + channel)
				elif args[1] == 'KICK' and len(args) >= 4:
					chan   = args[2]
					kicked = args[3]
					if chan == channel:
						self.members.pop(kicked.lower(), None)
						await self.fumble(kicked)
					if kicked == nickname and chan == channel:
						self.members   = dict()
						self.ball      = None
						self.ball_pass = None
						await asyncio.sleep(3)
						await self.raw(f'JOIN {channel} {key}') if key else await self.raw('JOIN ' + channel)
				elif args[1] == 'PART' and len(args) >= 3:
					chan = args[2]
					if chan == channel:
						nick = args[0].split('!')[0][1:]
						self.members.pop(nick.lower(), None)
						await self.fumble(nick)
						await self.action(nick, f'blows smoke in {nick}\'s face...')
				elif args[1] == 'JOIN' and len(args) >= 3:
					if args[2].lstrip(':') == channel:
						nick = args[0].split('!')[0][1:]
						self.members[nick.lower()] = nick
				elif args[1] == 'QUIT':
					nick = args[0].split('!')[0][1:]
					self.members.pop(nick.lower(), None)
					await self.fumble(nick)
				elif args[1] == 'NICK' and len(args) >= 3:
					nick = args[0].split('!')[0][1:]
					if self.members.pop(nick.lower(), None):
						new_nick = args[2].lstrip(':')
						self.members[new_nick.lower()] = new_nick
					await self.fumble(nick)
				elif args[1] == '353' and len(args) >= 6:
					if args[4] == channel:
						for name in ' '.join(args[5:])[1:].split():
							name = name.lstrip('~&@%+')
							self.members[name.lower()] = name
				elif args[1] == 'PRIVMSG' and len(args) >= 4:
					nick = args[0].split('!')[0][1:]
					chan = args[2]
					msg  = ' '.join(args[3:])[1:]
					if chan ==  channel:
						if nick == self.ball:
							self.ball_idle = time.time()
						await self.football(nick, msg.split())
						if self.status:
							args = msg.split()
							if msg == '@cancer':
								await self.sendmsg(chan, bold + 'CANCER IRC Bot - Developed by acidvegas in Python - https://git.acid.vegas/cancer')
							elif msg == '@cancer help':
								await self.help(chan)
							elif msg == '@cancer stats':
								chugged, smoked, toked, passes, intercepts = ('{0:,}'.format(self.stats[stat]) for stat in ('chugged','smoked','toked','passes','intercepts'))
								width = max(len(chugged), len(smoked), len(toked), len(passes), len(intercepts))
								await self.sendmsg(chan, 'Chugged     : {0} beers      {1}'.format(color(chugged.rjust(width), light_blue), color('({0:,} cases)'.format(int(self.stats['chugged']/24)), grey)))
								await self.sendmsg(chan, 'Smoked      : {0} cigarettes {1}'.format(color(smoked.rjust(width),  light_blue), color('({0:,} packs)'.format(int(self.stats['smoked']/20)),  grey)))
								await self.sendmsg(chan, 'Toked       : {0} joints     {1}'.format(color(toked.rjust(width),   light_blue), color('({0:,} grams)'.format(int(self.stats['toked']/3)),    grey)))
								await self.sendmsg(chan, 'Passed      : {0} footballs'.format(color(passes.rjust(width), light_blue)))
								await self.sendmsg(chan, 'Intercepted : {0} footballs'.format(color(intercepts.rjust(width), light_blue)))
							elif msg in ('!100','!extendo','!fatfuck') and luck(100):
								if msg == '!fatfuck':
									self.fat = True
									await self.sendmsg(chan, '{0}{1}{2}'.format(color(' !!! ', red, green), color('AWWW SHIT, IT\'S TIME FOR THAT MARLBORO FATFUCK', black, green), color(' !!! ', red, green)))
								else:
									self.stats['hits'] = 100
									if msg == '!100':
										await self.sendmsg(chan, '{0}{1}{2}'.format(color(' !!! ', white, red), color('AWWW SHIT, IT\'S TIME FOR THAT NEWPORT 100', red, white), color(' !!! ', white, red)))
									else:
										await self.sendmsg(chan, '{0}{1}{2}'.format(color(' !!! ', red, green), color('OHHH FUCK, IT\'S TIME FOR THAT 420 EXTENDO', yellow, green), color(' !!! ', red, green)))
							elif args[0] == '!beer' and len(args) <= 2:
								if len(args) == 1:
									target = nick
								else:
									target = args[1]
								await Generate.can(chan, target)
							elif msg == '!chainsmoke' and not self.event:
								self.status = False
								self.event  = 'chainsmoke'
								self.loops['chainsmoke'] = asyncio.create_task(self.loop_chainsmoke())
							elif msg == '!chug':
								if self.event == 'letschug':
									if nick in self.nicks:
										await self.sendmsg(chan, color(nick + ' you are already chuggin u wastoid!', light_green))
									else:
										self.nicks.append(nick)
										await self.sendmsg(chan, color(nick + ' joined the CHUG session!', light_green))
								else:
									if self.stats['sips'] <= 0:
										self.stats['sips'] = 8
										self.stats['chugged'] += 1
									for line in Generate.mug(self.stats['sips']):
										await self.sendmsg(chan, line)
									self.stats['sips'] -= random.choice((1,2))
							elif msg == '!dragrace' and not self.event:
								self.status = False
								self.event  = 'dragrace'
								self.loops['dragrace'] = asyncio.create_task(self.loop_dragrace())
							elif msg == '!letschug' and not self.event:
								self.event = 'letschug'
								self.loops['letschug'] = asyncio.create_task(self.loop_letschug(nick))
							elif msg == '!letstoke' and not self.event:
								self.event = 'letstoke'
								self.loops['letstoke'] = asyncio.create_task(self.loop_letstoke(nick))
							elif msg == '!nosmoking':
								self.status = False
								self.loops['nosmoking'] = asyncio.create_task(self.loop_nosmoking())
							elif msg in ('!smoke','!toke'):
								option = 'smoked' if msg == '!smoke' else 'toked'
								if self.event == 'letstoke' and msg == '!toke':
									if nick in self.nicks:
										await self.sendmsg(chan, color(nick + ' you are already toking u stoner!', light_green))
									else:
										self.nicks.append(nick)
										await self.sendmsg(chan, color(nick + ' joined the TOKE session!', light_green))
								else:
									if self.stats['hits'] <= 0:
										self.stats['hits'] = 25
										self.stats[option] += 1
										if self.fat:
											self.fat = False
										if self.event == 'chainsmoke' and msg == '!smoke':
											self.nicks[nick] = self.nicks[nick]+1 if nick in self.nicks else 1
											self.stats['chain'] += 1
										elif self.event == 'dragrace' and msg == '!smoke':
											await self.sendmsg(chan, 'It took {0} seconds for {1} to smoke a cigarette!'.format(color('{:.2f}'.format(time.time()-self.stats['drag']), light_blue), color(chan, white)))
											self.event = None
											self.stats['drag'] = 0
										elif luck(100) and msg == '!smoke':
											await self.raw(f'KILL {nick} CANCER KILLED {nick.upper()} - QUIT SMOKING TODAY! +1 800-QUIT-NOW')
									else:
										object = Generate.cigarette(self.stats['hits']) if msg == '!smoke' else Generate.joint(self.stats['hits'])
										if self.fat:
											for i in range(3):
												await self.sendmsg(chan, object)
										else:
											await self.sendmsg(chan, object)
										self.stats['hits'] -= random.choice((1,2))
			except (UnicodeDecodeError, UnicodeEncodeError):
				pass
			except Exception as ex:
				error('fatal error occured', ex)
				break

# Main
Cancer = Bot()
asyncio.run(Cancer.connect())
