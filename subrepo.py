# subrepo.py - perform batch-like commands on subrepos
#
# Copyright 2010 Andrew Petersen <KirbySaysHi@gmail.com>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

'''allows for easy(er) management of mutiple subrepositories at once'''

from mercurial.i18n import _
from hgext.fetch import fetch
from mercurial import hg, util, commands, cmdutil
import os, string

# Macro extension meta-data
cmdtable = {}
command = cmdutil.command(cmdtable)

@command('subrepo',
	[
	('r', 'recurse', None, _('operate recursively within each subrepository')),
	('a', 'all', None, _('operate in root repo as well as recursively within each subrepository')),
	('c', 'reclone', None, _('reclone all missing but registered subrepositories (as defined in .hgsub), ' +
	'leaving existing ones intact; this does not look at nor modify .hgsubstate! ' +
	'If an ACTION is specified it will execute after recloning all missing subrepos.')),
	('b', 'bottomup', None, _('operate bottom up, reversing the order that ACTION is applied'))
	],
	_('hg subrepo [-r] [-a] [-c] [-b] [ACTION] '))

def subrepo(ui, repo, action=None, **opts):
    '''allows for easy(er) management of mutiple subrepositories at once

    This extension provides the ability to batch-process subrepositories
    with hg commands. Each command generally loops through the 
    subrepositories listed in .hgsub, and simply calls an hg action 
    (as specified by ACTION)

    Note that ACTION can include parameters if quoted, e.g. "pull -rev xxx"

    There is also a built-in special action that can be invoked, "list".
    It will list all of the subrepos that are defined and then quit.

    Subrepositories can be complicated, and this extension should not be
    used as a bludgeon, but rather a scalpal. It is for the occasions that
    active development of the main repo is dependent on the subrepos having
    the newest, bleeding edge code. This extension is nothing but a series 
    of for loops!

    Watch the output in case user intervention / remediation is required,
    and always remember that updating subrepos will usually require a commit
    of the parent repo in order to update the .hgsubstate file (and thus the
    revision the subrepo is locked at).
    
    Configuration:
    
    You can designate that certain actions always run with the -all option.
    This is useful for actions such as status, incoming, outgoing, etc...
    To designate these, place something like this in your config settings:
    
    [subrepo]

    forceAllForCommands = list;status;incoming;outgoing;summary
    '''

    optReclone = opts.get('reclone', None)
    optRecurse = opts.get('recurse', None)
    optAll = opts.get('all', None)
    optBottomUp = opts.get('bottomup', None)

    # force optAll mode for user-defined actions
    forceAllForCommands = ui.config("subrepo", "forceAllForCommands")
    if not forceAllForCommands == None:
        if action in (forceAllForCommands.split(';')): optAll = True

    if optReclone:
        ui.status("checking for missing subrepo clones...\n")
        doReclone(ui, repo, (optRecurse or optAll))
        ui.status("finishing recloning\n")
        if action == None: return

    if action == None:
        ui.status("hg subrepo: missing action\n")
        commands.help_(ui, "subrepo")

    elif action == "list":
        ui.status("listing subrepos:\n-------\n")
        func = lambda ui, repoPath, remotePath: ListRepo(ui, repoPath, remotePath)
        doCommand(ui, repo, func, (optRecurse or optAll), False)
        ui.status("-------\n")
        return

        # Note: if you want to handle an action with a custom handler, here is where you would trap it
        # before the default generic doHgTextCommand handler is called for the action. You should define a lambda
        # that takes three parameters:
        #     ui         : the ui object to use for status messages
        #     repoPath   : the relative path to the repo to operate on
        #     remotePath : the remote path for the subrepo
        #
        # This lambda can then use any helper function that you write to handle the action, optionally
        # capturing and passing any other parameters like repo, options, etc...
        #
        # elif action == "ActionNameToTrap":
        #     func = lambda ui, repoPath, remotePath: yourCustomActionFunction(ui, repoPath, repo, opts, etc...)
        #     doCommand(ui, repo, func, (optRecurse or optAll), optAll)
        #     return
        #

    else:

        # do action for all subrepos
        ui.status("doing '%s' for all subrepos, watch output for necessity of user intervention...\n" % action)
        func = lambda ui, repoPath, remotePath: doHgTextCommand(ui, repoPath, action)
        if optBottomUp:
            doCommandReverse(ui, repo, func, (optRecurse or optAll), optAll)
        else:
            doCommand(ui, repo, func, (optRecurse or optAll), optAll)
        ui.status("---------------------------\n")

        # special messages for some actions
        if action == "fetch": ui.status("finished fetching, be sure to commit parent repo to update .hgsubstate\n")


# execute a function for each subrepo with optional recloning and optional recursion
# func is defined as func(localPath, remotePath)
def doCommand(ui, repo, func, recurse, all, relativePath=""):
    if relativePath == "" and all:
        func(ui, ".", ui.config('paths', 'default'))
    if os.path.exists(os.path.join(repo.root, ".hgsub")):
        for local, remote in getSubreposFromHgsub(repo):
            subrepoPath = os.path.join(relativePath, local)
            if os.path.exists(subrepoPath):
                func(ui, subrepoPath, remote)
                if recurse:
                    doCommand(ui, hg.repository(ui, subrepoPath, False), func, recurse, all, subrepoPath)
            else:
                ui.status("* %s is missing (perhaps you should reclone)\n" % subrepoPath)

				
# execute a function for each subrepo with optional recloning and optional recursion, in bottom up or reverse order
# func is defined as func(localPath, remotePath)
def doCommandReverse(ui, repo, func, recurse, all, relativePath=""):
    if os.path.exists(os.path.join(repo.root, ".hgsub")):
        for local, remote in getSubreposFromHgsub(repo):
            subrepoPath = os.path.join(relativePath, local)
            if os.path.exists(subrepoPath):
                if recurse:
                    doCommandReverse(ui, hg.repository(ui, subrepoPath, False), func, recurse, all, subrepoPath)
                func(ui, subrepoPath, remote)
            else:
                ui.status("* %s is missing (perhaps you should reclone)\n" % subrepoPath)
    if relativePath == "" and all:
        func(ui, ".", ui.config('paths', 'default'))


# generic helper to execute a hg command
def doHgTextCommand(ui, repoPath, commandText):
    ui.status("---------------------------\n")
    ui.status("* %s\n" % repoPath)
    currentwd = os.getcwd()
    os.chdir(repoPath)
    pout = util.popen("hg %s" % commandText)
    ui.status(pout.read())
    os.chdir(currentwd)


# helper to list a subrepo's information
def ListRepo(ui, repoPath, remotePath):
    ui.status("* %s\t@ %s\n" % (repoPath, remotePath))


# produce a list of subrepos for a repo
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


# clone a single repo
def recloneSubrepo(ui, local, remote):
    # todo: clone at the revision specified in .hgsubstate?
    ui.status("* %s is missing, recloning...\n" % local);
    hg.clone(ui, remote, dest=local)


