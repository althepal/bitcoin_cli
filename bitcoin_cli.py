#!/usr/bin/env python
import sys
from subprocess import call, check_output
import os
import json
import pprint
import re
import time
import shlex
import readline

rc_file_name = ".bitcoin_clirc"
RPC_USER = 'bitcoinrpc'
RPC_PASS = ''
HISTORY_FILE = '.bitcoin_cli_history'
rc_buffers = {}
try:
	rc_path = os.path.join(os.environ["HOME"], rc_file_name)
	with open(rc_path, 'r') as rc_file:
#		line = rc_file.readline()
		for line in rc_file:
			parts = line.split()
			if parts[0] == 'RPC_PASS':
				RPC_PASS = parts[1]
			elif parts[0] == 'RPC_USER':
				RPC_USER = parts[1]
			elif parts[0] == 'buffer':
				rc_buffers[parts[1]] = parts[2]
except:
	pass

if not RPC_USER or not RPC_PASS:
	print "You must set RPC_USER and RPC_PASS to run script."
	exit()


command_abbrevs = {
	'ga': 'getaccount',
	'gaba': 'getaddressesbyaccount',
	'gt': 'gettransaction',
	'gcc': 'getconnectioncount',
	'grt': 'getrawtransaction',
	'gradd': 'getreceivedbyaddress',
	'gracc': 'getreceivedbyaccount',
	'gna': 'getnewaddress',
	'drt': 'decoderawtransaction',
	'crt': 'createrawtransaction',
	'srt': 'signrawtransaction',
	'b': 'getbalance',
	'i': 'getinfo',
	'lt': 'listtransactions',
	'lu': 'listunspent',
	'la': 'listaccounts',
	'lsb': 'listsinceblock',
	'lracc': 'listreceivedbyaccount',
	'lradd': 'listreceivedbyaddress',
	'lag': 'listaddressgroupings',
	'wpp': 'walletpassphrase',
	'q': 'quit',
	'h': 'history',
}
reverse_abbrevs = {}
for abbrev, cmd in command_abbrevs.iteritems():
	reverse_abbrevs[cmd] = abbrev

help_out = """
addmultisigaddress <nrequired> <'["key","key"]'> [account]
backupwallet <destination>
createrawtransaction [{"txid":txid,"vout":n},...] {address:amount,...}
decoderawtransaction <hex string>
dumpprivkey <bitcoinaddress>
getaccount <bitcoinaddress>
getaccountaddress <account>
getaddressesbyaccount <account>
getbalance [account] [minconf=1]
getblock <hash>
getblockcount
getblockhash <index>
#getblocktemplate [params]
getconnectioncount
getdifficulty
#getgenerate
#gethashespersec
getinfo
#getmininginfo
getnewaddress [account]
getpeerinfo
getrawmempool
getrawtransaction <txid> [verbose=0]
getreceivedbyaccount <account> [minconf=1]
getreceivedbyaddress <bitcoinaddress> [minconf=1]
gettransaction <txid>
#getwork [data]
help [command]
importprivkey <bitcoinprivkey> [label]
keypoolrefill
listaccounts [minconf=1]
listaddressgroupings
listreceivedbyaccount [minconf=1] [includeempty=false]
listreceivedbyaddress [minconf=1] [includeempty=false]
listsinceblock [blockhash] [target-confirmations]
listtransactions [account] [count=10] [from=0]
listunspent [minconf=1] [maxconf=9999999]  ["address",...]
move <fromaccount> <toaccount> <amount> [minconf=1] [comment]
sendfrom <fromaccount> <tobitcoinaddress> <amount> [minconf=1] [comment] [comment-to]
sendmany <fromaccount> {address:amount,...} [minconf=1] [comment]
sendrawtransaction <hex string>
sendtoaddress <bitcoinaddress> <amount> [comment] [comment-to]
setaccount <bitcoinaddress> <account>
setgenerate <generate> [genproclimit]
settxfee <amount>
signmessage <bitcoinaddress> <message>
signrawtransaction <hex string> [{"txid":txid,"vout":n,"scriptPubKey":hex},...] [<privatekey1>,...] [sighashtype="ALL"]
#stop <detach>
submitblock <hex data> [optional-params-obj]
validateaddress <bitcoinaddress>
verifymessage <bitcoinaddress> <signature> <message>
walletlock
walletpassphrase <passphrase> <timeout>
walletpassphrasechange <oldpassphrase> <newpassphrase>
"""

valid_cmds = {}
for line in re.finditer('(.*?)\n', help_out):
	l = line.group(1).strip()
	if l == '' or l[0] == '#':
		continue
	s = l.split()
	cmd = s[0]
	if len(s) > 1:
		args = s[1:]
	else:
		args = [None]
	valid_cmds[cmd] = args

def full_cmd(abbrev):
	global command_abbrevs
	if command_abbrevs.has_key(abbrev):
		return command_abbrevs[abbrev]
	else:
		return abbrev

class CmdError(Exception):
	def __init__(self, cmd, param, curl_cmd, error_value):
		self.error_value = error_value
		self.cmd = cmd
		self.param = param
		self.curl_cmd = curl_cmd
#		print "CMD ERROR: %s" % self
	def __str__(self):
		return repr(self.value)

class Interactive:
	cmd_results = {}
	def __init__(self, screen=None, pre_load=True):
		global rc_buffers
		self.buffers = rc_buffers
		self.print_api_cmd = False
		self.screen = screen
		if pre_load:
			self.printStuff()
	def loadStuff(self):
		self.run_cmd("getbalance")
		self.run_cmd("listaccounts")
		self.account_names = self.cmd_results['listaccounts'][None].keys()
		self.run_cmd("getblockcount")
		self.getaddresses()

	def buffer_complete(self, begin_buffer):
		parts = begin_buffer.split('.')
		if len(parts) > 1:
			part_num = 1
			name = parts[0]
			val = self.buffers[name]
			stub = name + '.'
			while part_num < len(parts) - 1:
				idx = parts[part_num]
				stub += idx + '.'
				part_num += 1
				if type(val) is list:
					idx = int(idx)
				val = val[idx]
			remain = parts[part_num]
			if type(val) is list:
				sv = [str(i) for i in range(len(val))]
				completes = [stub + i for i in sv if i.startswith(remain)]
			else:
				completes = [stub + i for i in val.viewkeys() if i.startswith(remain)]
			if len(completes) == 1:
				try:
					if type(val) is list:
						remain = int(remain)
					v2 = val[remain]
					if isinstance(v2, (list, dict)):
						completes[0] += '.'
				except Exception:
					pass
		else:
			completes = [i for i in self.buffers if i.startswith(begin_buffer)]
			if len(completes) == 1:
				if self.buffers.has_key(begin_buffer) and isinstance(self.buffers[begin_buffer], (dict, list)):
					completes[0] += '.'

		return ['#' + i for i in completes]
	def p(self, o='', formatted=False, split_lists=True):
		if o == '':
			output = "\n"
		elif formatted:
			output = o
		elif isinstance(o, (str, unicode)):
			output = o
		elif split_lists and type(o) is list:
			self.p("\n")
			for l in o:
				self.p(l)
			return
		else:
			output = pprint.pformat(o, width=40) + "\n"
		if self.screen:
			self.screen.addstr(output)
			if output[-1] != "\n":
				self.screen.addstr("\n")
		else:
			print output
	def api_cmd(self, cmd, params=[]):
		json_params = json.dumps(params)
		db = "--data-binary '{\"method\":\"%s\",\"params\":%s}'" % (cmd, json_params)
		curl_cmd="/usr/bin/curl -s --user %s:%s %s http://127.0.0.1:8332/" % (RPC_USER, RPC_PASS, db)
		cmd_out = json.loads(check_output(curl_cmd, shell=True))
		if self.print_api_cmd:
			self.p(db, True)
		if cmd_out['error'] == None:
			return cmd_out['result']
		else:
			raise CmdError(cmd, json_params, curl_cmd, cmd_out['error'])
	def getaddresses(self):
		for account_name in self.cmd_results['listaccounts'][None]:
			if account_name == '': account_name = '_'
			self.run_cmd("getaddressesbyaccount '%s'" % account_name)
	def printStuff(self):
		self.loadStuff()
		self.p(self.getStuff(), True)
	def getStuff(self):
		stuff = "Balance: %f\nAccounts\n----------\n" % self.cmd_results['getbalance'][None]
		ctr = 0
		for account_name in self.account_names:
			ctr += 1
			acc_addrs = ''
			if self.cmd_results['getaddressesbyaccount'].has_key(account_name):
				acc_addrs += ', '.join(self.cmd_results['getaddressesbyaccount'][account_name])
			if acc_addrs == '':
				acc_addrs = '-- no addresses --'
			acc_balance = self.cmd_results['listaccounts'][None][account_name]
			if account_name == '':
				account_name = '-- no name --'
			stuff += "(ACC%d) %s: %fBTC (%s)\n" % (ctr, account_name, acc_balance, acc_addrs)
		return stuff;
	def buffer_val(self, name):
			parts = name.split('.')
			orig_buff = parts.pop(0)
			val = self.buffers[orig_buff]
			for v in parts:
				if type(val) is list:
					v = int(v)
				val = val[v]
			return val

	def run_cmd(self, cmd_line, show_results=False):
		cmd_line = str(cmd_line)
		cmd_line = cmd_line.strip()
		if cmd_line == '':
			return
		args = shlex.split(cmd_line)
		if args[0] == 'store':
			save_to_buffer = 'CB'
			args.pop(0)
		elif args[0] == 'storeto':
			args.pop(0)
			save_to_buffer = args.pop(0)
		else:
			save_to_buffer = False
		cmd = full_cmd(args.pop(0))
		params = args
		if cmd == 'quit':
			self.p("Finished")
			exit()
		elif cmd == 'info':
			self.printStuff()
		elif cmd == 'cmds':
			c = valid_cmds.keys()
			c.sort()
			c2 = []
			for c3 in c:
				if reverse_abbrevs.has_key(c3):
					c2.append("%s(%s)" % (c3, reverse_abbrevs[c3]))
				else:
					c2.append(c3)
			for i in range(0, len(c), 6):
				c4 = '  '.join(c2[i:i+6])
				self.p(c4, True)
		elif cmd == 'set':
			if len(args) != 2:
				self.p("Incorrect args. Need 2, name and value")
			else:
				name = args[0]
				val = args[1]
				if val[0] == '#':
					val2 = val[1:]
					try:
						val = self.buffer_val(val2)
					except Exception:
						self.p("Invalid reference ({})".format(val))
						return
				else:
					try:
						val = int(val)
					except ValueError:
						pass
				self.buffers[name] = val
		elif cmd == 'showcurl':
			self.print_api_cmd = not self.print_api_cmd
			self.p("SHOW CURL: " + str(self.print_api_cmd), True)
		elif cmd == 'buffers':
			self.p(self.buffers)
		elif cmd == 'info':
			self.printStuff()
		elif cmd[0] == '#':
			name = cmd[1:]
			if len(params) == 0:
				try:
					val = self.buffer_val(cmd[1:])
					pval = pprint.pformat(val, width=40) + "\n"
					self.p("{} = {}".format(cmd, pval))
				except Exception:
					self.p("{} not found".format(cmd))
			else:
				try:
					newval = self.buffer_val(params[0][1:])
					self.buffers[name] = newval
					self.p("{} = {}".format(name, newval))
				except Exception:
					self.p("Invalid value")

		elif cmd == 'history':
			if len(args) > 0:
				try:
					show_num = int(args[0])
				except ValueError:
					self.p("Invalid history length (must be integer)")
					return
			else:
				show_num = 20
			h_len = readline.get_current_history_length()
			if h_len < show_num:
				show_num = h_len
			print "XX {} {}".format(show_num, h_len)
			for n in range(h_len - show_num, h_len):
				self.p("{}: {}".format(n + 1, readline.get_history_item(n + 1)))
		elif cmd == 'sh':
			if len(params) == 0:
				self.p("sh <search arg>")
				return
			search_arg = params[0]
			cnt = 0
			found = []
			h_len = readline.get_current_history_length()
			self.p("History search for {}".format(search_arg))
			for n in range(1, h_len):
				c = readline.get_history_item(n)
				if re.search(search_arg, c):
					self.p("{}: {}".format(n, c))

		elif cmd[0] == '!':
			h_num = cmd[1:]
			self.p("HN {}".format(h_num))
			h_num = int(h_num)
			h_len = readline.get_current_history_length()
			if h_num >= h_len:
				self.p("{} {}".format(h_num, h_len))
				raise ValueError
			cmd_line = readline.get_history_item(h_num)
			readline.replace_history_item(h_len - 1, cmd_line)
			self.p("History Cmd: {}".format(cmd_line))
			self.run_cmd(cmd_line, True)

		else:
			if not valid_cmds.has_key(cmd):
				self.p("Invalid command (%s)\n" % cmd, True)
				return
			if len(params) == 0:
				key = None
			else:
				# if first param is a digit, and command takes an account, then the digit is the account number
				md = re.match('^(\d+)$', params[0])
				if md:
					cmd_params = valid_cmds[cmd]
					if re.search('account', cmd_params[0]):
						params[0] = "ACC%s" % md.group(1)

				for i in range(len(params)):
					if params[i] == '_':
						params[i] = ''
					elif params[i] == 'None':
						params[i] = ''
					elif params[i][0] == '#':
						try:
							params[i] = self.buffer_val(params[i][1:])
						except Exception:
							self.p("Invalid reference ({})".format(params[i]))
					elif re.match('[\d.]+i$', params[i]):
						try:
							params[i] = int(params[i][:-1])
						except ValueError:
							self.p("Invalid integer value ({})".format(params[i]))
							return
					elif re.match('[\d.]+f$', params[i]):
						try:
							params[i] = float(params[i][:-1])
						except ValueError:
							self.p("Invalid float value ({})".format(params[i]))
							return
					else:
						m = re.match('^ACC(\d+)$', params[i])
						if m:
							acc_num = int(m.group(1))
							if acc_num > len(self.account_names):
								self.p('Invalid account\n', True)
								return
							account_name = self.account_names[acc_num - 1]
							params[i] = account_name
							self.p("Account Name: {}".format(account_name))
				key = params[0]
			if cmd == 'signrawtransaction':
				hash = params[0]
				decoded = self.api_cmd("decoderawtransaction", [hash])
				self.p(decoded)
				txid = decoded['vin'][0]['txid']
				spk = decoded['vout'][0]['scriptPubKey']['hex']
				sign = [{ 'txid': txid, 'vout': 0, 'scriptPubKey': spk }]
				self.p(sign)
				params.append(sign)
			elif cmd == 'createrawtransaction':
# orig_trans, to_addr, amount, change_addr
				if len(params) != 4:
					self.p("createrawtransaction orig_trans to_addr amount change_addr")
					return
				trans_info = self.api_cmd("gettransaction", [params[0]])
				orig_trans_amount = trans_info['amount']

				xfer_amount = float(params[2])
				fee = 0.0005
				# prevent floating point rounding error
				change = float(orig_trans_amount) - xfer_amount - fee
				change = round(change * 1e8) * 1e-8
				if change < 0:
					self.p("Invalid amount")
					return
				x3 = [{'txid': params[0], 'vout': 0}]
				xfer_to_addr = params[1]
				change_addr = params[3]
				trans_out = {xfer_to_addr: xfer_amount}
				if change > 0:
					trans_out[change_addr] = change
				params = [x3, trans_out]
			elif cmd == 'listunspent' and len(params) == 3:
				params[2] = [params[2]]
			param = ' '.join(['"%s"' % x for x in params])
			try:
				cmd_result = self.api_cmd(cmd, params)
				self.buffers['LAST'] = cmd_result
				if show_results:
					if cmd == 'getrawmempool':
						self.p("NUM Trans: %d" % (len(cmd_result)), True)
						return
					elif cmd == 'help':
						tmp = re.sub('\\\\n', "\n", cmd_result)
						self.p(tmp, True)
					else:
						if cmd == 'listaddressgroupings':
							split_lists = False
						else:
							split_lists = True
						self.p(cmd_result, split_lists=split_lists)
						if type(cmd_result) is list:
							self.p("LIST SIZE: %d\n" % len(cmd_result), True)
						elif type(cmd_result) is dict:
							self.p("DICT SIZE: %d\n" % len(cmd_result), True)
				else:
					try:
						self.cmd_results[cmd][key] = cmd_result
					except KeyError:
						self.cmd_results[cmd] = {key: cmd_result}
				if save_to_buffer:
					self.buffers[save_to_buffer] = cmd_result
					self.p("Result was stored to #{}".format(save_to_buffer))
			except CmdError as e:
				self.p("ERROR: %s" % (e.error_value), True)
				self.p("ERROR: cmd='%s'\n param='%s'\n curl_cmd='%s'\n" % (e.cmd, e.param, e.curl_cmd), True)
				pass


new_delims = ""
readline.set_completer_delims(new_delims)
inter = Interactive()
def completer(text, state):
	if text[0] == '#':
		options = inter.buffer_complete(text[1:])
	else:
		options = [i for i in valid_cmds if i.startswith(text)]
	if state < len(options):
		return options[state]
	else:
		return None
readline.set_completer(completer)

histfile = os.path.join(os.environ["HOME"], HISTORY_FILE)
try:
	readline.read_history_file(histfile)
except IOError:
	pass
import atexit
atexit.register(readline.write_history_file, histfile)
del os, histfile
if 'libedit' in readline.__doc__:
	readline.parse_and_bind("bind ^I rl_complete")
else:
	readline.parse_and_bind("tab: complete")	

while 1:
	arg = raw_input('Bitcoin >> ').strip()
	inter.run_cmd(arg, True)
