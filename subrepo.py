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
    optFetch = opts.get('fetch', None)

    if optList:
        ui.status("listing subrepos:\n-------\n")
        listSubrepos(ui, repo)
        ui.status("-------\n")

    if optReclone:
        ui.status("checking for missing subrepo clones...\n")
        for local, remote in getSubreposFromHgsub(repo):
            if os.path.exists(local):
                ui.status("* %s exists\n" % local)
            else:
                recloneSubrepo(ui, local, remote)
        ui.status("finishing recloning\n")

    if optPull:
        ui.status("pulling all subrepos...\n");
        for local, remote in getSubreposFromHgsub(repo):
            if os.path.exists(local):
                ui.status("---------------------------\n")
                pout = util.popen("cd " + local + " && hg pull && cd ..")
                ui.status(pout.read())
            else:
                recloneSubrepo(ui, local, remote)
        ui.status("---------------------------\n")

    if optUpdate:
        ui.status("updating all subrepos to tip, watch output for necessity of user intervention...\n");
        for local, remote in getSubreposFromHgsub(repo):
            if os.path.exists(local):
                ui.status("---------------------------\n")
                pout = util.popen("cd " + local + " && hg update && cd ..")
                ui.status(pout.read())
            else:
                recloneSubrepo(ui, local, remote)
        ui.status("---------------------------\n")

    if optFetch:
        ui.status("fetching all subrepos, watch output for necessity of user intervention...\n");
        for local, remote in getSubreposFromHgsub(repo):
            if os.path.exists(local):
                ui.status("---------------------------\n")
                pout = util.popen("cd " + local + " && hg fetch && cd ..")
                ui.status(pout.read())
            else:
                recloneSubrepo(ui, local, remote)
        ui.status("---------------------------\n")
        ui.status("finished fetching, be sure to commit parent repo to update .hgsubstate\n")

def getSubreposFromHgsub(repo):
    # XXX arguably this could, or should use:
    #  mercurial.subrepo.state(repo['.'])
    f = repo.wopener('.hgsub')
    return [map(string.strip, line.split('=')) for line in f]

def listSubrepos(ui, repo):
    for local, remote in getSubreposFromHgsub(repo):
        ui.status( "* %s\t@ %s\n" % (local, remote))

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
          ('p', 'pull', None, _('call hg pull within each subrepository')),
          ('u', 'update', None, _('call hg update within each subrepository')),
          ('f', 'fetch', None, _('call hg fetch within each subrepository'))
         ],
         _('hg subrepo [ACTION]'))
}
