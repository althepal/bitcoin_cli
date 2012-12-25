bitcoin_cli
===========

a CLI for bitcoin

This is a project I created to learn a bit more about bitcoin and brush up on my Python.

The purpose of this project is to make it easier to work with the original client written by Satoshi.

This CLI runs commands against a running instance of Bitcoin-QT.

Getting Started:
	1. Run Bitcoin-QT in server mode (on a MAC: open /Applications/Bitcoin-Qt.app/ --args -server)
	2. in bitcoin.conf, add the following lines:
	  server = 1
	  rpcuser = <user> # this does not have to be an actual user on the system, only used to access bitcoin server
	  rpcpassword = <pass>
	3. Set RPC_USER and RPC_PASS in this script.
	4. Alternitavely, you can create ~/.bitcoin_clirc and set user and pass there
	   RPC_USER bitcoinrpc
	   RPC_PASS password

Using the script:

The script uses libreadline, so most of the basic command line key binding are present. A history of commands
is stored and can be accessed using the up and down arrows, as well as !<history number>.

Variable Storage
A useful aspect of this script is storing values of commands. Variables are accessed by prefixing the variable name
with a hash (#). The last command output is stored in #LAST. There is tab-completion for variables, and this extends
to indexes on the variable when it is a dict or list.

Storing variables can be done in several ways:
1. By default, the last command output is stored in #LAST
2. Prefix any command with "store" and the output will be stored in #CB (clipboard). e.g. >> store listunspent
3. Prefix any command with storeto <variable name>. e.g. storeto unspent listunspent
4. Use "set" to set a variable. e.g. set unspent #LAST

List or dict objects can be accessed using a period (.) between indexes. e.g. #unspent.3.amount


Additional Features
sh <search arg>
 search command history for a string
!<history number>
 run a command from history
history <number>
 print last <number> commands. defaults to 20
info
 prints out basic info about the accounts.
 For commands that take an account name, the account number listed in the info command can be used instead
 e.g. balance 3
To represent an integer or float, add i (for int) or f (for float) to end of number
 e.g. sendtoaddress <address> 0.5f




