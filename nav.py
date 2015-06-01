#!/usr/bin/env python
# encoding: utf-8

# Copyright (C) 2014 Francis Vega
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


"""Nav.

Usage:
  nav create <src> [<dst>] [-m] [-q=QUALITY] [-o=FORMAT] [-i=FORMAT] [-r=SIZE] [-t=TITLE]
  nav set [-q=QUALITY]

Commands:
  create                    Main command to create navigation
  set                       Set default settings

Arguments:
  <src>                     Source directory with image files
  <dst>                     Destination directory to write output files
  QUALITY                   Integer between (1-100)
  FILE                      Valid file name
  FORMAT                    Image format (jpg|png)

Options:
  -h --help                 Show this help message and exit
  -v --version              Show version and exit
  -i --inputformat=FORMAT   [default: png]
  -o --outputformat=FORMAT  [default: png]
  -q --quality=QUALITY      [default: 100]
  -r --resize=SIZE          [default: 100%]
  -m --mobile               Create htmls with image-width at 100%
  -t --title=TITLE             Title of htmls [default: Navigation]

Examples:
  nav create d:/Dropbox/Secuoyas/web/visual/ -wm
  nav set --quality 20
  nav set --outputformat jpg

"""

from __future__ import print_function
from __future__ import division
from docopt import docopt
import os
import sys
import time
import subprocess
import math
import zipfile
import re
import imghdr
import struct
import platform
import json
import shutil
import filecmp


# Defines
SCRIPT_FILE_PATH = os.path.realpath(__file__)
SCRIPT_DIR_PATH = os.path.dirname(SCRIPT_FILE_PATH)
CONFIG_DIR_PATH = os.path.join(SCRIPT_DIR_PATH, "nav-sheets")
CONFIG_FILE_PATH = os.path.join(CONFIG_DIR_PATH, "nav.conf")
DESKTOP_HTML_SHEET = os.path.join(CONFIG_DIR_PATH, "nav-desktop.html")
MOBILE_HTML_SHEET = os.path.join(CONFIG_DIR_PATH, "nav-mobile.html")
INDEX_HTML_SHEET = os.path.join(CONFIG_DIR_PATH, "nav-index.html")
INDEX_PAGE_NAME = "index.html"
OS = platform.system()

class Convert(object):

    def __init__(self):
        self.app = self.getConvertBin()

    def getConvertBin(self):
        return 'convert'
        # return "C:/Program Files/Adobe Photoshop CC 2014/convert.exe"

    def do(self, inputFile, outputFile, options):
            psdfix = ''
            if os.path.splitext(inputFile)[1] == ".psd":
                psdfix = "[0]"
            subprocess.call([self.app, '-resize', options['resize'], '-crop', options['crop'], '-quality', options['quality'], inputFile+psdfix, outputFile], shell=False)

class Navzen(object):

    def __init__(self):
        self.convert = Convert()

    def errprint(self, msg):
        """Custom error printing."""
        print("\nERROR:", msg, end='\n', file=sys.stderr)
        sys.exit()


    def private(self, path):
        return os.path.basename(path).startswith("__")


    def directoryIsEmptyOfTypeFiles(self, path, typeOfFile):

        ls = []
        files = os.listdir(path)

        for f in files:
            if f.startswith(".") == False and self.private(f) == False:
                    ls.append(f)

        for item in ls:
            if os.path.isdir(os.path.join(path, item)) == False:
                if os.path.splitext(os.path.join(path, item))[1] == typeOfFile:
                    return False

        return True


    def getAllDirectoriesWithFormat(self, root, typeOfFile):

        roots = []
        rootsFiletered = []

        # Get all dirs
        for root, dirs, files in os.walk(root):
            roots.append(root)

        # Remove empty dirs and start with __
        for i in range(len(roots)):
            directory = roots[i]

            if self.directoryIsEmptyOfTypeFiles(directory, typeOfFile) == False:
                if self.private(directory) == False:
                    rootsFiletered.append(directory)

        return rootsFiletered


    def export(self, command):

        # Set outputdirectory
        # Si no se ha especificado directorio de salida...
        # ...añadimos uno por defecto
        if self.a['outputDirectory'] == None:
            if os.path.isfile(self.a['psdFile']):
                self.a['outputDirectory'] = os.path.join(os.path.basename(self.a['psdFile']), "navzen")
            if os.path.isfile(self.a['psdFile']) == False:
                self.a['outputDirectory'] = os.path.join(self.a['psdFile'], "navzen")

        # Creamos el directorio en caso de que no exista
        if os.path.isdir(self.a['outputDirectory']) == False:
            os.makedirs(self.a['outputDirectory'])

        # Si el input es un directorio
        if os.path.isdir(self.a['psdFile']):
            self.a['inputDirectory'] = self.a['psdFile']
        # Si el input es un fichero (en el caso de update) nos quedamos con el nombre del directorio de igual forma
        else:
            self.a['inputDirectory'] = os.path.dirname(self.a['psdFile'])

        # copy library files
        self.copyLibrarys()

        # load templates
        self.loadTemplates()

        # head info
        print("\n\033[95mNavzen\033[0m", end="\n")
        print("Simple HTML Navigation from images", end="\n\n")
        print("Convert formats: {0} to {1}".format(self.a['inputformat'], self.a['outputformat']), end="\n")
        print("Source Path {0}".format(self.a['psdFile']), end="\n")
        print("Destination Path {0}".format(self.a['outputDirectory']), end="\n\n")

        if command == 'update':
            self.update()

        if command == 'create':
            self.create()

        # rebuild index
        self.createIndex()

        # final info
        if not self.a['quiet'] and not self.a['kiet']:
            print("", end="\n")
            print("Mockup finished at {0}".format(os.path.abspath(self.a['outputDirectory'])), end="\n\n\033[0m")


    def create(self):

        self.a['inputDirectory'] = self.a['psdFile']

        allpsds = self.getFilesFromDirectory(self.a['inputDirectory'], self.a['inputformat'])

        if len(allpsds) > 0:

            try:
                i = 1
                for psd in allpsds:
                    self.a['psdFile'] = psd
                    self.update(create=True, totalFiles=len(allpsds), currentFile=i)
                    i+=1

                    if self.a['quiet'] == True and self.a['kiet'] == False:
                        sys.stdout.write("\rConverting {}%".format(str(int((100/len(allpsds))*(i-1)))))
                        sys.stdout.flush()

                print ("")

            except KeyboardInterrupt:
                errprint("\033[91mInterrupted by you\033[0m")

        else:
            self.errprint("There are no {0} files in {1}".format(self.a['inputformat'], self.a['inputDirectory']))
            return


    def update(self, create=False, totalFiles=1, currentFile=1):

        # Obtenemos el archivo anterior y posterior al actual
        self.a['prevPsdFile'] = self.getSideFile(self.a['psdFile'], -1)
        self.a['nextPsdFile'] = self.getSideFile(self.a['psdFile'], +1)

        # Del archivo anterior solo el html
        # Si crete == True, no tocamos el archivo anterior
        if create == False:
            self.createAsset(self.getSideFile(self.a['psdFile'] ,-1), image=False, thumb=False, html=True)

        # Del archivo actual la imagen, el thumb y el html
        #if os.path.isfile(self.a['psdFile']) == True and self.a['overwrite'] == True or os.path.isfile(self.a['psdFile']) == False:
        self.createAsset(self.a['psdFile'], image=True, thumb=True, html=True)
        if self.a['quiet'] == False and self.a['kiet'] == False:
            print ("\033[92m{:03d} % ... {}".format(int((100/totalFiles)*currentFile), os.path.basename(self.a['psdFile'])))

        """
        else:
            print ("\033[93m(Skip) " + os.path.basename(self.a['psdFile']))
        """

    def loadTemplates(self):

        if self.a['mobile']:
            self.a['template'] = self.loadTemplate(MOBILE_HTML_SHEET)
        else:
            self.a['template'] = self.loadTemplate(DESKTOP_HTML_SHEET)

        self.a['indexTemplate'] = self.loadTemplate(INDEX_HTML_SHEET)


    def loadTemplate(self, fileTemplate):
        try:
            file_html = open(fileTemplate, "r")
            content = file_html.read()
            file_html.close()
            if "[navzen-" not in content:
                return False
            return content
        except:
            self.errprint("El archivo {0} no existe o no puede abrirse".format(fileTemplate))


    def createAsset(self, psdFile, image=True, thumb=True, html=True):
        if image:
            if self.a['mobile'] == True:
                self.createImageFromPSD(psdFile, slice=True)
            else:
                self.createImageFromPSD(psdFile)
        if thumb:
            self.createThumbnailFromPSD(psdFile)
        if html:
            if self.a['mobile'] == True:
                pass
            self.createHtmlFromPSD(psdFile)


    def getSlices(self, height, sliceSize):
        height = int(height)
        sliceSize = int(sliceSize)

        sliceList = []
        while height > 0:
            if height > sliceSize:
                sliceList.append(sliceSize)
            else:
                sliceList.append(height)
            height -= sliceSize

        return sliceList


    def createImageFromPSD(self, psdFile, slice=False):

        if slice == False:

            self.convert.do(self.a['psdFile'],
                os.path.splitext(
                    os.path.join(self.a['outputDirectory'], self.changeExtension(os.path.basename(self.a['psdFile']), self.a['outputformat'] ))
                )[0] + "." + self.a['outputformat'],
                {
                    'quality':self.a['quality'],
                    'resize':self.a['resize'],
                    'crop':'100%'

                }
            )

        else:

            size = self.getImageSize(psdFile)
            width = size[0]
            height = size[1]
            slices = self.getSlices(height, self.a['sliceSize'])

            i = 0
            for slicePixels in slices:

                output = "{0}_slice_{1}.{2}".format(
                        os.path.join(self.a['outputDirectory'], os.path.splitext(os.path.basename(self.a['psdFile']))[0]),
                        str(i),
                        self.a['outputformat']
                )

                crop = '{0}x{1}+{2}+{3}'.format(int(width), slices[i], 0, int(i * int(self.a['sliceSize'])))

                self.convert.do(
                    self.a['psdFile'],
                    output,
                    {
                        'resize': self.a['resize'],
                        'crop': crop,
                        'quality': self.a['quality']
                    }
                )

                i += 1


    def createThumbnailFromPSD(self, psdFile):
        # large image
        self.convert.do(self.a['psdFile'],

            os.path.splitext(
                os.path.join(self.a['outputDirectory'], self.changeExtension(os.path.basename(self.a['psdFile']), self.a['outputformat'] ))
            )[0] + "_thumb." + self.a['outputformat'],
            {
                'quality':'100',
                'resize':'120x',
                'crop':'120x120+0+0'

            }
        )


    def createHtmlFromPSD(self, psdFile, slice=False):

        # HTML ACTUAL
        size = self.getImageSize(psdFile)
        width = size[0]
        height = size[1]
        slices = self.getSlices(height, self.a['sliceSize'])

        # Replace custom tags with real content
        tags = self.a['template']
        tags = tags.replace("[navzen-title]", "Navzen")
        tags = tags.replace("[navzen-img-width]", str(width))
        tags = tags.replace("[navzen-img-height]", str(height))
        tags = tags.replace("[navzen-next-html]", self.changeExtension(os.path.basename(self.getSideFile(psdFile, 1)), 'html'))

        if self.a['mobile'] == True:

            templateImgTag = re.search("<[^>]+\[navzen-img\][^>]+>", tags).group()

            i = 0
            imageTags = ""
            for slicePixels in slices:
                imageTags += '<img src=\"{0}_slice_{1}.{2}\">'.format(
                    os.path.splitext(os.path.basename(psdFile))[0],
                    str(i),
                    self.a['outputformat']
                )
                i +=1

            tags = tags.replace(templateImgTag, imageTags)

        # Desktop
        else:
            tags = tags.replace("[navzen-img]", self.changeExtension(os.path.basename(psdFile), self.a['outputformat']))
        html = open(
            os.path.join(
                self.a['outputDirectory'],
                self.changeExtension(os.path.basename(psdFile), "html")
            ),
            "w"
        )

        html.write(tags)
        html.close()


    def createIndex(self):

        indexPageLinks = ""
        allpsds = self.getFilesFromDirectory(self.a['inputDirectory'], self.a['inputformat'])
        for psd in allpsds:

            dataTags = self.taggy(os.path.basename(psd))

            spans = dataTags.split(" ")
            htmlSpans = ""
            for s in spans:
                htmlSpans += "\
            \n<span>"+s+"</span>"

            indexPageLinks += "\n\
            <!-- ITEM -->\n\
            <li>\n\
                <div class='result-box' data-tag='{0}'>\n\
                    <div class='left'>\n\
                        <a href={3}>\n\
                            <img src='{1}'>\n\
                        </a>\n\
                    </div>\n\
                    <div class='right'>\n\
                        <div class='title'>\n\
                            <a href={3}>\n\
                            <!-- spans -->\
                                {2}\n\
                            </a>\n\
                        </div>\n\
                        <!--<div class='actions'>\n\
                            <div class='psd'>\n\
                                <a href='#'>.psd</a>\n\
                            </div>\n\
                            <div class='png'>\n\
                                <a href='{3}'>.png</a>\n\
                            </div>\n\
                        </div>-->\n\
                    </div>\n\
                </div>\n\
            </li>\n".format(
                dataTags,

                "{0}_thumb.{1}".format(
                    os.path.splitext(os.path.basename(psd))[0],
                    self.a['outputformat']
                ),

                htmlSpans,

                self.changeExtension(os.path.basename(psd), 'html')
            )

        # Replace custom tags with real content
        index_html = self.loadTemplate(INDEX_HTML_SHEET)
        tags = index_html
        tags = tags.replace("[navzen-title]", "TITULO")
        tags = tags.replace("[navzen-li-result]", indexPageLinks)
        index_html = tags

        index = open(os.path.join(self.a['outputDirectory'], INDEX_PAGE_NAME), "w")

        index.write(index_html)
        index.close()


    def taggy(self, fn):
        fn= ".".join(fn.split(".")[:-1])
        fnSpacesByDash = fn.replace(" ", "-")
        tags = fnSpacesByDash.split("-")
        tags = [t for t in tags if t != "" and t != "_"]
        return " ".join(tags)


    def normalizePaths(self):
        self.a['psdFile'] = os.path.abspath(self.a['psdFile'])
        self.a['outputDirectory'] = os.path.abspath(self.a['outputDirectory'])


    def getSideFile(self, filePath, side):
        dirName = os.path.dirname(filePath)
        fileName = os.path.basename(filePath)
        allFiles = self.getFilesFromDirectory(os.path.dirname(filePath), self.a['inputformat'])

        try:
            sideFile = allFiles[allFiles.index(filePath)+(side)]
            return sideFile
        except:
            return allFiles[0]


    def getAllPsds(self, directory):
        return self.getFilesFromDirectory(directory, 'psd')


    def getAllJpgs(self, directory):
        return self.getFilesFromDirectory(directory, 'jpg')


    def getAllPngs(self, directory):
        return self.getFilesFromDirectory(directory, 'png')


    def getFilesFromDirectory(self, directory, extension):
        extSize = len(extension)

        try:

            return [ os.path.join(directory, file) for file in os.listdir(directory) if os.path.isfile(os.path.join(directory, file)) and file[extSize*-1:] == extension]
        except:
            self.errprint("No existen archivos tipo {0} en el directorio {1}".format(extension, directory))


    def copyLibrarys(self):
        shutil.copy("{0}/previz.js".format(CONFIG_DIR_PATH), self.a['outputDirectory'])
        shutil.copy("{0}/jquery.js".format(CONFIG_DIR_PATH), self.a['outputDirectory'])


    def getImageSize(self, fname):
        """Determines the image type of fhandle and return its size."""
        fhandle = open(fname, 'rb')
        ext = os.path.splitext(fname)[1]

        if ext == ".psd":
            fhandle.read(14)
            height, width = struct.unpack("!LL", fhandle.read(8))
            fhandle.close()
        else:
            head = fhandle.read(24)
            if len(head) != 24:
                return
            if imghdr.what(fname) == 'png':
                check = struct.unpack('>i', head[4:8])[0]
                if check != 0x0d0a1a0a:
                    return
                width, height = struct.unpack('>ii', head[16:24])
            elif imghdr.what(fname) == 'gif':
                width, height = struct.unpack('<HH', head[6:10])
            elif imghdr.what(fname) == 'jpeg':
                try:
                    fhandle.seek(0) # Read 0xff next
                    size = 2
                    ftype = 0
                    while not 0xc0 <= ftype <= 0xcf:
                        fhandle.seek(size, 1)
                        byte = fhandle.read(1)
                        while ord(byte) == 0xff:
                                byte = fhandle.read(1)
                                ftype = ord(byte)
                                size = struct.unpack('>H', fhandle.read(2))[0] - 2
                    # We are at a SOFn block
                    fhandle.seek(1, 1)  # Skip `precision' byte.
                    height, width = struct.unpack('>HH', fhandle.read(4))
                except Exception: #IGNORE:W0703
                    return
            else:
                return

        return width, height


    def changeExtension(self, filePath, extension):
        return '{0}.{1}'.format(os.path.splitext(filePath)[0], extension)

    def errprint(self, msg):
        """Custom error printing."""
        print("\nERROR:", msg, end='\n', file=sys.stderr)
        sys.exit()

args = docopt(__doc__, version='Nav 1.0')
#args = docopt(__doc__, argv="create /Users/hisco/Desktop/project")

def errprint(msg):
    """Custom error printing."""
    print("\nERROR:", msg, end='\n', file=sys.stderr)
    sys.exit()


# Argumentos

navzen = Navzen()
navzen.a = {
    'title': 'Navzen',
    'psdFile': args["<src>"],
    'outputDirectory': args["<dst>"],
    'inputformat': args['--inputformat'],
    'outputformat': args['--outputformat'],
    'quality': args["--quality"],
    'resize': args["--resize"],
    'crop': '100%',
    'mobile': args["--mobile"]
}


if args['create']:
    navzen.export('create')

if args['set']:
    pass
