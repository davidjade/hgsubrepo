'''allows for easy(er) management of mutiple subrepositories at once'''

from mercurial import hg
from mercurial import dispatch
from mercurial import re
import shlex
import os 
import os.path

def subrepo(ui, repo, cmd=None, **opts):
	'''
	what this does...
	'''
	
	if cmd == "list":
		ui.status("listing subrepos:\n-------\n")
		listSubrepos(ui, repo)
		ui.status("-------\n")
	elif cmd == "reclone":
		ui.status("checking for missing subrepo clones...\n")
		rs = getSubreposFromHgsub(repo)
		for r in rs:
			if os.path.exists(r[0]):
				ui.status("* " + r[0] + " exists\n");
			else:
				ui.status("* " + r[0] + " is missing, recloning...\n");
				args = shlex.split("clone "+r[1]+" "+r[0])
				dispatch._runcatch(ui, args)
	else:
		ui.status("No command given, listing subrepos:\n-------\n")
		listSubrepos(ui, repo)
		ui.status("-------\n")
		
	
def getSubreposFromHgsub(repo):
	root = repo.root
	f = open(root + "/.hgsub")
	d = f.readlines()
	result = [];
	for x in d:
		x = x.split('=')
		result.append([x[0].strip(), x[1].strip()])
	f.close()
	return result

def listSubrepos(ui, repo):
	for r in getSubreposFromHgsub(repo):
		ui.status( "* " + r[0] + "	@ " + r[1] + "\n" )
		
# Macro extension meta-data
cmdtable = {
	# "command-name": (function-call, options-list, help-string)
    #"subrepo": (subrepo, [('ls', 'list', None, 'list current subrepos')], "hg subrepo [cmd]")
	"subrepo": (subrepo, [], "hg subrepo [cmd]")
}