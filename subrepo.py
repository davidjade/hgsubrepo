# subrepo.py - perform batch-like commands on subrepos
#
# Copyright 2010 Andrew Petersen <KirbySaysHi@gmail.com>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

'''allows for easy(er) management of mutiple subrepositories at once'''

from mercurial.i18n import _
from hgext.fetch import fetch
from mercurial import hg, util, commands
import os, string

def subrepo(ui, repo, action=None, **opts):
    '''allows for easy(er) management of mutiple subrepositories at once

    This extension provides the ability to batch-process subrepositories
    with hg commands. Each command generally loops through the 
    subrepositories listed in .hgsub, and simply calls an hg action.

    Subrepositories can be complicated, and this extension should not be
    used as a bludgeon, but rather a scalpal. It is for the occasions that
    active development of the main repo is dependent on the subrepos having
    the newest, bleeding edge code. This extension is nothing but a series 
    of for loops!

    Watch the output in case user intervention / remediation is required,
    and always remember that updating subrepos will usually require a commit
    of the parent repo in order to update the .hgsubstate file (and thus the
    revision the subrepo is locked at).
    '''

    optList = opts.get('list', None)
    optReclone = opts.get('reclone', None)
    optRecurse = opts.get('recurse', None)
    optAll = opts.get('all', None)

    if optList:
        ui.status("listing subrepos:\n-------\n")
        func = lambda repoPath, remotePath: ListRepo(ui, repoPath, remotePath)
        doCommand(ui, repo, func, (optRecurse or optAll), False)	# never use doForAll for listing subrepos
        ui.status("-------\n")
        return

    if optReclone:
        ui.status("checking for missing subrepo clones...\n")
        doReclone(ui, repo, (optRecurse or optAll))
        ui.status("finishing recloning\n")
        if action == None: return

    if action == None:
        ui.status("hg subrepo: missing action\n")
        commands.help_(ui, "subrepo")
    else:
        # force optAll mode for user-defined actions
        forceAllForCommands = ui.config("subrepo", "forceAllForCommands")
        if not forceAllForCommands == None:
            if action in (forceAllForCommands.split(';')): optAll = True

        # do action for all subrepos
        ui.status("doing '%s' for all subrepos, watch output for necessity of user intervention...\n" % action)
        func = lambda repoPath, remotePath: doHgTextCommand(ui, repoPath, action)
        doCommand(ui, repo, func, (optRecurse or optAll), optAll)
        ui.status("---------------------------\n")

        # special messages for some actions
        if action == "fetch": ui.status("finished fetching, be sure to commit parent repo to update .hgsubstate\n")


# execute a function for each subrepo with optional recloning and optional recursion
# func is defined as func(localPath, remotePath)
def doCommand(ui, repo, func, recurse, doForRoot, relativePath=""):
    if relativePath == "" and doForRoot:
        func(".", ui.config('paths', 'default'))
    if os.path.exists(os.path.join(repo.root, ".hgsub")):
        for local, remote in getSubreposFromHgsub(repo):
            subrepoPath = os.path.join(relativePath, local)
            if os.path.exists(subrepoPath):
                func(subrepoPath, remote)
                if recurse:
                    doCommand(ui, hg.repository(ui, subrepoPath, False), func, recurse, doForRoot, subrepoPath)
            else:
                ui.status("* %s is missing (perhaps you should reclone)\n" % subrepoPath)



def doHgTextCommand(ui, repoPath, commandText):
    ui.status("---------------------------\n")
    ui.status("* %s\n" % repoPath)
    currentwd = os.getcwd()
    os.chdir(repoPath)
    pout = util.popen("hg %s" % commandText)
    ui.status(pout.read())
    os.chdir(currentwd)


def ListRepo(ui, repoPath, remotePath):
    ui.status("* %s\t@ %s\n" %(repoPath, remotePath))


def getSubreposFromHgsub(repo):
    # XXX arguably this could, or should use:
    #  mercurial.subrepo.state(repo['.'])
    f = repo.wopener('.hgsub')
    return [map(string.strip, line.split('=')) for line in f]


# reclone all missing subrepos
def doReclone(ui, repo, recurse, relativePath=""):
    if os.path.exists(os.path.join(repo.root, ".hgsub")):
        for local, remote in getSubreposFromHgsub(repo):
            subrepoPath = os.path.join(relativePath, local)
            if os.path.exists(subrepoPath):
                ui.status("* %s exists \n" % subrepoPath)
            else:
                recloneSubrepo(ui, subrepoPath, remote)
            if recurse:
                doReclone(ui,  hg.repository(ui, subrepoPath, False), recurse, subrepoPath)


def recloneSubrepo(ui, local, remote):
    # todo: clone at the revision specified in .hgsubstate?
    ui.status("* %s is missing, recloning...\n" % local);
    hg.clone(ui, remote, dest=local)


# Macro extension meta-data
cmdtable = {
    "subrepo":
        (subrepo,
         [
          ('l', 'list', None, _('list registered subrepositories then quit')),
          ('r', 'recurse', None, _('operate recursively within each subrepository')),
          ('a', 'all', None, _('operate in root repo as well as recursively within each subrepository')),
          ('c', 'reclone', None, _('reclone all missing but registered subrepositories (as defined in .hgsub), ' +
		  'leaving existing ones intact; this does not look at nor modify .hgsubstate! ' +
		  'If an ACTION is specified it will execute after recloning all missing subrepos.')),
         ],
         _('hg subrepo [-l] [-r] [-a] [-c] [ACTION] '))
}
