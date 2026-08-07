# ******************************************************************************
# Project: CityJsonLoader - A QGIS Plugin.
#
# Purpose: This plugin allows for CityJSON files to be loaded in QGIS.
#
# GitHub page: https://github.com/cityjson/cityjson-qgis-plugin
#
# Contact: G.Stavropoulou@tudelft.nl
# ******************************************************************************
#
# Copyright © 2018–2026 3D geoinformation group, TU Delft, S. Vitalis and G. Stavropoulou. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# ******************************************************************************

import getpass
import sys
import xmlrpc.client
from optparse import OptionParser

# Configuration
PROTOCOL = "http"
SERVER = "plugins.qgis.org"
PORT = "80"
ENDPOINT = "/plugins/RPC2/"
VERBOSE = False


def main(parameters, arguments):
    """Main entry point.

    :param parameters: Command line parameters.
    :param arguments: Command line arguments.
    """
    address = f"{PROTOCOL}://{parameters.username}:{parameters.password}@{parameters.server}:{parameters.port}{ENDPOINT}"
    print(f"Connecting to: {hide_password(address)}")

    server = xmlrpc.client.ServerProxy(address, verbose=VERBOSE)

    try:
        plugin_id, version_id = server.plugin.upload(
            xmlrpc.client.Binary(open(arguments[0]).read())
        )
        print(f"Plugin ID: {plugin_id}")
        print(f"Version ID: {version_id}")
    except xmlrpc.client.ProtocolError as err:
        print("A protocol error occurred")
        print(f"URL: {hide_password(err.url, 0)}")
        print(f"HTTP/HTTPS headers: {err.headers}")
        print("Error code: %d" % err.errcode)
        print(f"Error message: {err.errmsg}")
    except xmlrpc.client.Fault as err:
        print("A fault occurred")
        print("Fault code: %d" % err.faultCode)
        print(f"Fault string: {err.faultString}")


def hide_password(url, start=6):
    """Returns the http url with password part replaced with '*'.

    :param url: URL to upload the plugin to.
    :type url: str

    :param start: Position of start of password.
    :type start: int
    """
    start_position = url.find(":", start) + 1
    end_position = url.find("@")
    return "{}{}{}".format(
        url[:start_position],
        "*" * (end_position - start_position),
        url[end_position:],
    )


if __name__ == "__main__":
    parser = OptionParser(usage="%prog [options] plugin.zip")
    parser.add_option(
        "-w",
        "--password",
        dest="password",
        help="Password for plugin site",
        metavar="******",
    )
    parser.add_option(
        "-u",
        "--username",
        dest="username",
        help="Username of plugin site",
        metavar="user",
    )
    parser.add_option(
        "-p", "--port", dest="port", help="Server port to connect to", metavar="80"
    )
    parser.add_option(
        "-s",
        "--server",
        dest="server",
        help="Specify server name",
        metavar="plugins.qgis.org",
    )
    options, args = parser.parse_args()
    if len(args) != 1:
        print("Please specify zip file.\n")
        parser.print_help()
        sys.exit(1)
    if not options.server:
        options.server = SERVER
    if not options.port:
        options.port = PORT
    if not options.username:
        # interactive mode
        username = getpass.getuser()
        print(f"Please enter user name [{username}] :", end=" ")
        res = input()
        if res != "":
            options.username = res
        else:
            options.username = username
    if not options.password:
        # interactive mode
        options.password = getpass.getpass()
    main(options, args)
