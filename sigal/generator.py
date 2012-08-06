#!/usr/bin/env python2
# -*- coding:utf-8 -*-

# sigal - simple static gallery generator
# Copyright (C) 2009-2012 - Simon C. (saimon.org)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; If not, see http://www.gnu.org/licenses/

"""
Generate html pages for each directory of images
"""

import os
import codecs

from PIL import Image
from distutils.dir_util import copy_tree
from fnmatch import fnmatch
from jinja2 import Environment, PackageLoader

DEFAULT_THEME = "default"
INDEX_PAGE = "index.html"
DESCRIPTION_FILE = "album_description"
SIGAL_LINK = "https://github.com/saimn/sigal"
PATH_SEP = u" » "
THEMES_PATH = os.path.normpath(os.path.join(
        os.path.abspath(os.path.dirname(__file__)), 'themes'))


def do_link(link, title):
    "return html link"
    return '<a href="%s">%s</a>' % (link, title)


class Generator():
    """ Generate html pages for each directory of images """

    def __init__(self, settings, path, theme=DEFAULT_THEME, tpl=INDEX_PAGE):
        self.data = {}
        self.settings = settings
        self.path = os.path.normpath(path)
        self.theme = settings['theme'] or theme
        self.theme_path = os.path.join(THEMES_PATH, self.theme)
        theme_rel_path = os.path.relpath(self.theme_path,
                                         os.path.dirname(__file__))

        env = Environment(loader=PackageLoader('sigal', theme_rel_path))
        self.template = env.get_template(tpl)

        self.ctx = {}
        self.ctx['sigal_link'] = SIGAL_LINK

    def directory_list(self):
        "get the list of directories with files of particular extensions"
        ignored = ['theme', self.settings['thumb_dir'],
                   self.settings['bigimg_dir']]

        for dirpath, dirnames, filenames in os.walk(self.path):
            dirpath = os.path.normpath(dirpath)
            if os.path.split(dirpath)[1] not in ignored and \
                    not fnmatch(dirpath, '*theme*'):
                # sort images and sub-albums by name
                filenames.sort(key=str.lower)
                dirnames.sort(key=str.lower)

                self.data[dirpath] = {}
                self.data[dirpath]['img'] = [f for f in filenames \
                                             if os.path.splitext(f)[1] in \
                                                 self.settings['fileextlist']]
                self.data[dirpath]['subdir'] = [d for d in dirnames \
                                                    if d not in ignored]

    def get_meta_value(self, data):
        """
        Return the value for a line like:
           key = "value"
        """
        data = data.split('=')[1].strip()

        # Strip quotes
        if data[0] == '"':
            data = data[1:]
        if data[-1] == '"':
            data = data[:-1]

        return data

    def get_metadata(self, path):
        """
        Get album metadata from DESCRIPTION_FILE:
          - album_name
          - album_description
          - album_representative
        """
        descfile = os.path.join(path, DESCRIPTION_FILE)
        if not os.path.isfile(descfile):
            return

        with codecs.open(descfile, "r", "utf-8") as f:
            for l in f:
                if "album_name" in l:
                    self.data[path]['title'] = self.get_meta_value(l)
                if "album_description" in l:
                    self.data[path]['description'] = self.get_meta_value(l)
                if "album_representative" in l:
                    self.data[path]['representative'] = self.get_meta_value(l)

    def find_representative(self, path):
        """
        find the representative image for a given album/path
        at the moment, this is the first image found.
        """

        files = [f for f in os.listdir(path)
                 if os.path.isfile(os.path.join(path, f))
                 and os.path.splitext(f)[1] in self.settings['fileextlist']]

        for f in files:
            # find and return the first landscape image
            im = Image.open(os.path.join(path, f))
            if im.size[0] > im.size[1]:
                return f

        # else simply return the 1st image
        return files[0]

    def generate(self):
        """
        Render the html page
        """

        # copy static files in the output dir
        theme_outpath = os.path.join(os.path.abspath(self.path), 'theme')
        copy_tree(self.theme_path, theme_outpath)

        self.directory_list()

        for dirpath in self.data.keys():
            # default: get title from directory name
            self.data[dirpath]['title'] = os.path.basename(dirpath).\
                                          replace('_', ' ').\
                                          replace('-', ' ').capitalize()

            self.get_metadata(dirpath)
            # print self.data[dirpath]

        # loop on directories
        for dirpath in self.data.keys():
            self.ctx['theme'] = {
                'name': self.theme,
                'path': os.path.relpath(theme_outpath, dirpath)
                }
            self.ctx['home_path'] = os.path.join(os.path.relpath(self.path,
                                                                 dirpath),
                                                 INDEX_PAGE)

            # paths to upper directories (with titles and links)
            tmp_path = dirpath
            self.ctx['paths'] = do_link(INDEX_PAGE,
                                        self.data[tmp_path]['title'])

            while tmp_path != self.path:
                tmp_path = os.path.normpath(os.path.join(tmp_path, '..'))
                link = os.path.relpath(tmp_path, dirpath) + "/" + INDEX_PAGE
                self.ctx['paths'] = do_link(link,
                                            self.data[tmp_path]['title']) + \
                                            PATH_SEP + self.ctx['paths']

            self.ctx['images'] = []
            for i in self.data[dirpath]['img']:
                image = {
                    'file': i,
                    'thumb': os.path.join(self.settings['thumb_dir'],
                                          self.settings['thumb_prefix'] + i)
                    }
                self.ctx['images'].append(image)

            self.ctx['albums'] = []
            for d in self.data[dirpath]['subdir']:

                dpath = os.path.join(dirpath, d)

                alb_thumb = ''
                if 'representative' in self.data[dpath]:
                    alb_thumb = self.data[dpath]['representative']

                if not alb_thumb or \
                   not os.path.isfile(os.path.join(dpath, alb_thumb)):
                    alb_thumb = self.find_representative(dpath)

                album = {
                    'path': os.path.join(d, INDEX_PAGE),
                    'title': self.data[dpath]['title'],
                    'thumb': os.path.join(d, self.settings['thumb_dir'],
                                          self.settings['thumb_prefix'] +
                                          alb_thumb),
                    }
                self.ctx['albums'].append(album)

            page = self.template.render(self.data[dirpath],
                                        **self.ctx).encode('utf-8')

            # save page
            f = open(os.path.join(dirpath, INDEX_PAGE), 'w')
            f.write(page)
            f.close()