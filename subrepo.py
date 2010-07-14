# subrepo.py - perform batch-like commands on subrepos
#
# Copyright 2010 Andrew Petersen <KirbySaysHi@gmail.com>
#
# This software may be used and distributed according to the terms of the
# GNU General Public License version 2 or any later version.

'''allows for easy(er) management of mutiple subrepositories at once'''

from mercurial.i18n import _
from hgext.fetch import fetch
from mercurial import hg, util
import os, string

def subrepo(ui, repo, **opts):
    '''allows for easy(er) management of mutiple subrepositories at once

    This extension provides the ability to batch-process subrepositories
    with a few defined commands. Each command generally loops through the
    subrepositories listed in .hgsub, and simply calls an hg action.

    Subrepositories can be complicated, and this extension should not be
    used as a bludgeon, but rather a scalpal. It is for the occasions that
    active development of the main repo is dependent on the subrepos having
    the newest, bleeding edge code. This extension is nothing
    but a series of for loops!

    Watch the output in case user intervention / remediation is required,
    and always remember that updating subrepos will usually require a commit
    of the parent repo in order to update the .hgsubstate file (and thus the
    revision the subrepo is locked at).
    '''

    optList = opts.get('list', None)
    optReclone = opts.get('reclone', None)
    optPull = opts.get('pull', None)
    optUpdate = opts.get('update', None)
    optIncoming = opts.get('incoming', None)
    optOutgoing = opts.get('outgoing', None)
    optFetch = opts.get('fetch', None)
    optStatus = opts.get('status', None)
    optNoRecurse = opts.get('norecurse', None)

    if optList:
        ui.status("listing subrepos:\n-------\n")
        func = lambda repoPath, remotePath: ListRepo(ui, repoPath, remotePath)
        doCommand(ui, repo, func, False, optNoRecurse)
        ui.status("-------\n")

    if optReclone:
        ui.status("checking for missing subrepo clones...\n")
        func = lambda repoPath, remotePath: doReclone(ui, repoPath, remotePath)
        doCommand(ui, repo, func, True, optNoRecurse)
        ui.status("finishing recloning\n")

    if optPull:
        ui.status("pulling all subrepos...\n")
        func = lambda repoPath, remotePath: doHgTextCommand(ui, repoPath, remotePath, "pull")
        doCommand(ui, repo, func, True, optNoRecurse)
        ui.status("---------------------------\n")

    if optUpdate:
        ui.status("updating all subrepos to tip, watch output for necessity of user intervention...\n")
        func = lambda repoPath, remotePath: doHgTextCommand(ui, repoPath, remotePath, "update")
        doCommand(ui, repo, func, True, optNoRecurse)
        ui.status("---------------------------\n")

    if optIncoming:
        ui.status("getting incoming changesets for all subrepos\n")
        func = lambda repoPath, remotePath: doHgTextCommand(ui, repoPath, remotePath, "incoming")
        doCommand(ui, repo, func, False, optNoRecurse)
        ui.status("---------------------------\n")

    if optOutgoing:
        ui.status("getting outgoing changesets for all subrepos\n")
        func = lambda repoPath, remotePath: doHgTextCommand(ui, repoPath, remotePath, "outgoing")
        doCommand(ui, repo, func, False, optNoRecurse)
        ui.status("---------------------------\n")

    if optFetch:
        ui.status("fetching all subrepos, watch output for necessity of user intervention...\n")
        func = lambda repoPath, remotePath: doHgTextCommand(ui, repoPath, remotePath, "fetch")
        doCommand(ui, repo, func, True, optNoRecurse)
        ui.status("---------------------------\n")
        ui.status("finished fetching, be sure to commit parent repo to update .hgsubstate\n")

    if optStatus:
        ui.status("getting status for all subrepos\n")
        func = lambda repoPath, remotePath: doHgTextCommand(ui, repoPath, remotePath, "status")
        doCommand(ui, repo, func, False, optNoRecurse)
        ui.status("---------------------------\n")


# execute a function for each subrepo with optional recloning and optional recursion
# func is defined as func(localPath, remotePath)
def doCommand(ui, repo, func, cloneMissing, noRecurse, relativePath=""):
    if os.path.exists(os.path.join(repo.root, ".hgsub")):
        for local, remote in getSubreposFromHgsub(repo):
            subrepoPath = os.path.join(relativePath, local)
            if not os.path.exists(subrepoPath) and cloneMissing:
                recloneSubrepo(ui, subrepoPath, remote)
            if os.path.exists(subrepoPath):
                func(subrepoPath, remote)
                if not noRecurse:
                    doCommand(ui, hg.repository(ui, subrepoPath, False), func, cloneMissing, noRecurse, subrepoPath)
            else:
                ui.status("* %s is missing (perhaps you should reclone)\n" % subrepoPath)



def doHgTextCommand(ui, repoPath, remotePath, commandText):
    ui.status("---------------------------\n")
    ui.status("* %s\n" % repoPath)
    currentwd = os.getcwd()
    os.chdir(repoPath)
    pout = util.popen("hg %s" % commandText)
    ui.status(pout.read())
    os.chdir(currentwd)


def ListRepo(ui, repoPath, remotePath):
    ui.status("* %s\t@ %s\n" %(repoPath, remotePath))


def doReclone(ui, repoPath, remotePath):
    return


def getSubreposFromHgsub(repo):
    # XXX arguably this could, or should use:
    #  mercurial.subrepo.state(repo['.'])
    f = repo.wopener('.hgsub')
    return [map(string.strip, line.split('=')) for line in f]


def recloneSubrepo(ui, local, remote):
    # todo: clone at the revision specified in .hgsubstate?
    ui.status("* %s is missing, recloning...\n" % local);
    hg.clone(ui, remote, dest=local)


# Macro extension meta-data
cmdtable = {
    "subrepo":
        (subrepo,
         [('l', 'list', None, _('list registered subrepositories')),
          ('c', 'reclone', None, _('reclone all missing but registered subrepositories (as defined in .hgsub), leaving existing ones intact; this does not look at nor modify .hgsubstate!')),
          ('i', 'incoming', None, _('call hg incoming within each subrepository')),
          ('o', 'outgoing', None, _('call hg outgoing within each subrepository')),
          ('p', 'pull', None, _('call hg pull within each subrepository')),
          ('u', 'update', None, _('call hg update within each subrepository')),
          ('f', 'fetch', None, _('call hg fetch within each subrepository')),
          ('s', 'status', None, _('call hg status within each subrepository')),
          ('', 'norecurse', None, _('do not operate recursively within each subrepository'))
         ],
         _('hg subrepo [ACTION]'))
}
