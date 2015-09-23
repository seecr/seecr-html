## begin license ##
#
# "Meresco Html" is a template engine based on generators, and a sequel to Slowfoot.
# It is also known as "DynamicHtml" or "Seecr Html".
#
# Copyright (C) 2014-2015 Seecr (Seek You Too B.V.) http://seecr.nl
# Copyright (C) 2014 Stichting Bibliotheek.nl (BNL) http://www.bibliotheek.nl
#
# This file is part of "Meresco Html"
#
# "Meresco Html" is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# "Meresco Html" is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with "Meresco Html"; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
## end license ##

from seecr.test import SeecrTestCase
from weightless.core import asString
from meresco.html.login import GroupsFile, UserGroupsForm
from os.path import join
from urllib import urlencode

class UserGroupsFormTest(SeecrTestCase):
    def setUp(self):
        super(UserGroupsFormTest, self).setUp()
        self.groupsFile = GroupsFile(filename=join(self.tempdir, 'groups'), availableGroups=['admin', 'users', 'special'])
        self.userGroups = UserGroupsForm(action='/action')
        self.userGroups.addObserver(self.groupsFile)
        self.groupsFile.setGroupsForUser(username='normal', groupnames=['users'])
        self.groupsFile.setGroupsForUser(username='bob', groupnames=['admin', 'users'])
        self.normalUser = self.groupsFile.userForName(username='normal')
        self.adminUser = self.groupsFile.userForName(username='bob')

    def testSetup(self):
        self.assertEquals(set(['admin', 'users']), self.adminUser.groups())

    def testHandleUpdateGroupsForUser(self):
        Body = urlencode({'username': [self.adminUser.name], 'groupname': ['special'], 'formUrl': ['/useraccount']}, doseq=True)
        session = {'user':self.adminUser}
        result = asString(self.userGroups.handleRequest(Method='POST', path='/action/updateGroupsForUser', session=session, Body=Body))
        self.assertEquals('HTTP/1.0 302 Found\r\nLocation: /useraccount\r\n\r\n', result)
        self.assertEquals(set(['admin', 'special']), self.adminUser.groups())

    def testHandleUpdateGroupsForUser_if_not_admin(self):
        Body = urlencode({'username': [self.adminUser.name], 'groupname': ['special'], 'formUrl': ['/useraccount']}, doseq=True)
        session = {'user':self.normalUser}
        result = asString(self.userGroups.handleRequest(Method='POST', path='/action/updateGroupsForUser', session=session, Body=Body))
        self.assertEquals('HTTP/1.0 404 Not Found', result.split('\r\n')[0])


    def testGroupsUserForm(self):
        kwargs = {
            'path': '/path/to/form',
            'arguments': {'key': ['value']},
        }
        self.assertEqualsWS("""<div id="usergroups-groups-user-form">
    <form name="groups" method="POST" action="/action/updateGroupsForUser">
        <input type="hidden" name="username" value="bob"/>
        <input type="hidden" name="formUrl" value="/path/to/form?key=value"/>
        <ul>
            <li><label><input type="checkbox" name="groupname" value="admin" checked="checked" disabled="disabled"/>admin</label></li>
            <li><label><input type="checkbox" name="groupname" value="special" />special</label></li>
            <li><label><input type="checkbox" name="groupname" value="users" checked="checked"/>users</label></li>
        </ul>
        <input type="submit" value="Aanpassen"/>
    </form>
</div>""", asString(self.userGroups.groupsUserForm(user=self.adminUser, **kwargs)))
