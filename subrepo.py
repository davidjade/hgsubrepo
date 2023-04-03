# subrepo.py - perform batch-like commands on subrepos
#
# Copyright 2010 Andrew Petersen <KirbySaysHi@gmail.com>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

'''allows for easy(er) management of mutiple subrepositories at once'''

from mercurial.i18n import _
from hgext.fetch import fetch
from mercurial import hg, util, commands, registrar
from mercurial.utils import procutil
import os, string

# Macro extension meta-data
cmdtable = {}
command = registrar.command(cmdtable)

@command(b'subrepo',
	[
	(b'r', b'recurse', None, _('operate recursively within each subrepository')),
	(b'a', b'all', None, _('operate in root repo as well as recursively within each subrepository')),
	(b'c', b'reclone', None, _('reclone all missing but registered subrepositories (as defined in .hgsub), ' +
	'leaving existing ones intact; this does not look at nor modify .hgsubstate! ' +
	'If an ACTION is specified it will execute after recloning all missing subrepos.')),
	(b'b', b'bottomup', None, _('operate bottom up, reversing the order that ACTION is applied'))
	],
	_(b'hg subrepo [-r] [-a] [-c] [-b] [ACTION] '))

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

    optReclone = opts.get(b'reclone', None)
    optRecurse = opts.get(b'recurse', None)
    optAll = opts.get(b'all', None)
    optBottomUp = opts.get(b'bottomup', None)

    # force optAll mode for user-defined actions
    forceAllForCommands = ui.config(b"subrepo", b"forceAllForCommands")
    if not forceAllForCommands == None:
        if action in (forceAllForCommands.split(b';')): optAll = True

    if optReclone:
        ui.status(b"checking for missing subrepo clones...\n")
        doReclone(ui, repo, (optRecurse or optAll))
        ui.status(b"finishing recloning\n")
        if action == None: return

    if action == None:
        ui.status(b"hg subrepo: missing action\n")
        commands.help_(ui, b"subrepo", command=[b"subrepo"])

    elif action == b"list":
        ui.status(b"listing subrepos:\n-------\n")
        func = lambda ui, repoPath, remotePath: ListRepo(ui, repoPath, remotePath)
        doCommand(ui, repo, func, (optRecurse or optAll), False)
        ui.status(b"-------\n")
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
        ui.status(b"doing '%s' for all subrepos, watch output for necessity of user intervention...\n" % action)
        func = lambda ui, repoPath, remotePath: doHgTextCommand(ui, repoPath, action)
        if optBottomUp:
            doCommandReverse(ui, repo, func, (optRecurse or optAll), optAll)
        else:
            doCommand(ui, repo, func, (optRecurse or optAll), optAll)
        ui.status(b"---------------------------\n")

        # special messages for some actions
        if action == b"fetch": ui.status(b"finished fetching, be sure to commit parent repo to update .hgsubstate\n")


# execute a function for each subrepo with optional recloning and optional recursion
# func is defined as func(localPath, remotePath)
def doCommand(ui, repo, func, recurse, all, relativePath=b""):
    if relativePath == b"" and all:
        func(ui, b".", ui.config(b'paths', b'default'))
    if os.path.exists(os.path.join(repo.root, b".hgsub")):
        for local, remote in getSubreposFromHgsub(repo):
            subrepoPath = os.path.join(relativePath, local)
            if os.path.exists(subrepoPath):
                func(ui, subrepoPath, remote)
                if recurse:
                    doCommand(ui, hg.repository(ui, subrepoPath, False), func, recurse, all, subrepoPath)
            else:
                ui.status(b"* %s is missing (perhaps you should reclone)\n" % subrepoPath)

				
# execute a function for each subrepo with optional recloning and optional recursion, in bottom up or reverse order
# func is defined as func(localPath, remotePath)
def doCommandReverse(ui, repo, func, recurse, all, relativePath=b""):
    if os.path.exists(os.path.join(repo.root, b".hgsub")):
        for local, remote in getSubreposFromHgsub(repo):
            subrepoPath = os.path.join(relativePath, local)
            if os.path.exists(subrepoPath):
                if recurse:
                    doCommandReverse(ui, hg.repository(ui, subrepoPath, False), func, recurse, all, subrepoPath)
                func(ui, subrepoPath, remote)
            else:
                ui.status(b"* %s is missing (perhaps you should reclone)\n" % subrepoPath)
    if relativePath == b"" and all:
        func(ui, b".", ui.config(b'paths', b'default'))


# generic helper to execute a hg command
def doHgTextCommand(ui, repoPath, commandText):
    ui.status(b"---------------------------\n")
    ui.status(b"* %s\n" % repoPath)
    currentwd = os.getcwd()
    os.chdir(repoPath)
    pout = procutil.popen(b"hg %s" % commandText)
    ui.status(pout.read())
    os.chdir(currentwd)


# helper to list a subrepo's information
def ListRepo(ui, repoPath, remotePath):
    ui.status(b"* %s\t@ %s\n" % (repoPath, remotePath))


# produce a list of subrepos for a repo
def getSubreposFromHgsub(repo):
    # XXX arguably this could, or should use:
    #  mercurial.subrepo.state(repo['.'])
    ctx = repo[b'.']
#    print [(subpath, ctx.substate[subpath][0]) for subpath in ctx.substate]	# show subrepo list for debugging
    return [(subpath, ctx.substate[subpath][0]) for subpath in ctx.substate]


# reclone all missing subrepos
def doReclone(ui, repo, recurse, relativePath=b""):
    if os.path.exists(os.path.join(repo.root, b".hgsub")):
        for local, remote in getSubreposFromHgsub(repo):
            subrepoPath = os.path.join(relativePath, local)
            if os.path.exists(subrepoPath):
                ui.status(b"* %s exists \n" % subrepoPath)
            else:
                recloneSubrepo(ui, subrepoPath, remote)
            if recurse:
                doReclone(ui,  hg.repository(ui, subrepoPath, False), recurse, subrepoPath)


# clone a single repo
def recloneSubrepo(ui, local, remote):
    # todo: clone at the revision specified in .hgsubstate?
    ui.status(b"* %s is missing, recloning...\n" % local);
    hg.clone(ui, remote, dest=local)


