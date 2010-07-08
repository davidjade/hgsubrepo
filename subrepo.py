'''allows for easy(er) management of mutiple subrepositories at once'''

from mercurial.i18n import _
from mercurial import hg, dispatch, re
import shlex
import os 
import os.path

def subrepo(ui, repo, cmd, **opts):
	'''
	what this does...
	'''
	
	if cmd == "show":
		ui.status("listing subrepos:\n-------\n")
		listSubrepos(ui, repo)
		ui.status("-------\n")
	
	if cmd == "reclone":
		ui.status("checking for missing subrepo clones...\n")
		rs = getSubreposFromHgsub(repo)
		for r in rs:
			if os.path.exists(r[0]):
				ui.status("* " + r[0] + " exists\n")
			else:
				recloneSubrepo(ui, r[0], r[1])
	
	if cmd == "pull":
		ui.status("pulling all subrepos...\n");
		rs = getSubreposFromHgsub(repo)
		for r in rs:
			if os.path.exists(r[0]):
				ui.status(r[0]+"\n")
			else:
				recloneSubrepo(ui, r[0], r[1])
	
	if cmd is None:
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

def recloneSubrepo(ui, local, remote):
	ui.status("* " + local + " is missing, recloning...\n");
	args = shlex.split("clone "+remote+" "+local)
	dispatch._runcatch(ui, args)
	
# Macro extension meta-data
cmdtable = {
	# "command-name": (function-call, options-list, help-string)
    #"subrepo": (subrepo, [('ls', 'list', None, 'list current subrepos')], "hg subrepo [cmd]")
	"subrepos": 
		(subrepo, 
		 [],
		  #('l', 'show', None, _('list current subrepositories')),
		  #('c', 'clone', None, _('reclone subrepositories if missing'))], 
		 _('hg subrepo [ show | reclone | pull ]'))
}