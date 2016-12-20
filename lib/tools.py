"""Data Retriever Tools

This module contains miscellaneous classes and functions used in Retriever
scripts.

"""
from __future__ import print_function
from future import standard_library
standard_library.install_aliases()

from builtins import str
from builtins import input
from builtins import next
import difflib
import os
import io
from io import StringIO as newfile
import warnings
import unittest
import shutil
from decimal import Decimal
from hashlib import md5

from retriever import HOME_DIR
from retriever.lib.models import *
import csv
import json
import xml.etree.ElementTree as ET
warnings.filterwarnings("ignore")

TEST_ENGINES = dict()


def name_matches(scripts, arg):
    matches = []
    for script in scripts:
        if arg.lower() == script.shortname.lower(): return [script]
        max_ratio = max([difflib.SequenceMatcher(None, arg.lower(), factor).ratio() for factor in (script.shortname.lower(), script.name.lower(), script.filename.lower())] +
                        [difflib.SequenceMatcher(None, arg.lower(), factor).ratio() for factor in [tag.strip().lower() for tagset in script.tags for tag in tagset]]
                        )
        if arg.lower() == 'all':
            max_ratio = 1.0
        matches.append((script, max_ratio))
    matches = [m for m in sorted(matches, key=lambda m: m[1], reverse=True) if m[1] > 0.6]
    return [match[0] for match in matches]


def final_cleanup(engine):
    """Perform final cleanup operations after all scripts have run."""
    pass


config_path = os.path.join(HOME_DIR, 'connections.config')


def get_saved_connection(engine_name):
    """Given the name of an engine, returns the stored connection for that engine
    from connections.config."""
    parameters = {}
    if os.path.isfile(config_path):
        config = open(config_path, "r")
        for line in config:
            values = line.rstrip('\n').split(',')
            if values[0] == engine_name:
                try:
                    parameters = eval(','.join(values[1:]))
                except:
                    pass
    return parameters


def save_connection(engine_name, values_dict):
    """Saves connection information for an engine in connections.config."""
    lines = []
    if os.path.isfile(config_path):
        config = open(config_path, "r")
        for line in config:
            if line.split(',')[0] != engine_name:
                lines.append('\n' + line.rstrip('\n'))
        config.close()
        os.remove(config_path)
        config = open(config_path, "w")
    else:
        config = open(config_path, "w")
    if "file" in values_dict:
        values_dict["file"] = os.path.abspath(values_dict["file"])
    config.write(engine_name + "," + str(values_dict))
    for line in lines:
        config.write(line)
    config.close()


def get_default_connection():
    """Gets the first (most recently used) stored connection from
    connections.config."""
    if os.path.isfile(config_path):
        config = open(config_path, "r")
        default_connection = config.readline().split(",")[0]
        config.close()
        return default_connection
    else:
        return None


def choose_engine(opts, choice=True):
    """Prompts the user to select a database engine"""
    from retriever.engines import engine_list

    if "engine" in list(opts.keys()):
        enginename = opts["engine"]
    elif opts["command"] == "download":
        enginename = "download"
    else:
        if not choice:
            return None
        print("Choose a database engine:")
        for engine in engine_list:
            if engine.abbreviation:
                abbreviation = "(" + engine.abbreviation + ") "
            else:
                abbreviation = ""
            print("    " + abbreviation + engine.name)
        enginename = input(": ")
    enginename = enginename.lower()

    engine = Engine()
    if not enginename:
        engine = engine_list[0]
    else:
        for thisengine in engine_list:
            if (enginename == thisengine.name.lower() or
                    thisengine.abbreviation and
                    enginename == thisengine.abbreviation):
                engine = thisengine

    engine.opts = opts
    return engine


def reset_retriever(scope):
    """Remove stored information on scripts, data, and connections"""

    warning_messages = {
        'all': "\nThis will remove existing scripts, cached data, and information on database connections. \nSpecifically it will remove the scripts and raw_data folders and the connections.config file in {}. \nDo you want to proceed? (y/N)\n",
        'scripts': "\nThis will remove existing scripts. \nSpecifically it will remove the scripts folder in {}.\nDo you want to proceed? (y/N)\n",
        'data': "\nThis will remove raw data cached by the Retriever. \nSpecifically it will remove the raw_data folder in {}. \nDo you want to proceed? (y/N)\n",
        'connections': "\nThis will remove stored information on database connections. \nSpecifically it will remove the connections.config file in {}. \nDo you want to proceed? (y/N)\n"
    }

    path = os.path.normpath(HOME_DIR)
    warn_msg = warning_messages[scope].format(path)
    confirm = input(warn_msg)
    while not (confirm.lower() in ['y', 'n', '']):
        print("Please enter either y or n.")
        confirm = input()
    if confirm.lower() == 'y':
        if scope in ['data', 'all']:
            shutil.rmtree(os.path.join(path, 'raw_data'))
        if scope in ['scripts', 'all']:
            shutil.rmtree(os.path.join(path, 'scripts'))
        if scope in ['connections', 'all']:
            try:
                os.remove(os.path.join(path, 'connections.config'))
            except:
                pass


def json2csv(input_file, output_file=None, header_values=None):
    """Convert Json file to CSV
    function is used for only testing and can handle the file of the size
    """
    if sys.version_info >= (3, 0, 0):
        if os.name =='nt':
            file_out = io.open(input_file)
        else:
            file_out = io.open(input_file, encoding='ISO-8859-1')
    else:
        file_out = io.open(input_file, encoding='latin-1')

    # set output file name and write header
    if output_file is None:
        output_file = os.path.splitext(os.path.basename(input_file))[0] + ".csv"

    if sys.version_info >= (3, 0, 0):
        csv_out = io.open(output_file, 'w', newline = '')
    else:
        csv_out = io.open(output_file, 'wb')

    if os.name == 'nt':
        outfile = csv.DictWriter(csv_out, dialect='excel', escapechar="\\", lineterminator='\n', fieldnames=header_values)
    else:
        outfile = csv.DictWriter(csv_out, dialect='excel', escapechar="\\", fieldnames=header_values)
    raw_data = json.loads(file_out.read())
    outfile.writeheader()

    for item in raw_data:
        outfile.writerow(item)
    file_out.close()
    os.system("rm -r {}".format(input_file))
    return output_file


def xml2csv(input_file, outputfile=None, header_values=None, row_tag="row"):
    """Convert xml to csv
    function is used for only testing and can handle the file of the size
    """
    if sys.version_info >= (3, 0, 0):
        if os.name =='nt':
            file_output = io.open(input_file)
        else:
            file_output = io.open(input_file, encoding='ISO-8859-1')
    else:
        file_output = io.open(input_file, encoding='latin-1')

    # set output file name and write header
    if outputfile is None:
        outputfile = os.path.splitext(os.path.basename(input_file))[0] + ".csv"

    if sys.version_info >= (3, 0, 0):
        csv_out = io.open(outputfile, 'w', newline = '')
    else:
        csv_out = io.open(outputfile, 'wb')

    if os.name == 'nt':
        csv_writer = csv.writer(csv_out, dialect='excel', escapechar='\\', lineterminator='\n')
    else:
        csv_writer = csv.writer(csv_out, dialect='excel', escapechar='\\')

    v = file_output.read()
    csv_writer.writerow(header_values)
    tree = ET.parse(newfile(v))
    root = tree.getroot()
    for rows in root.findall(row_tag):
        x = [name.text for name in header_values for name in rows.findall(name)]
        csv_writer.writerow(x)
    file_output.close()
    os.system("rm -r {}".format(input_file))
    return outputfile


def getmd5(data, data_type='lines', mode='rb'):
    """Get MD5 of a data source"""
    checksum = md5()
    if data_type == 'lines':
        for line in data:
            if type(line) == bytes:
                checksum.update(line)
            else:
                checksum.update(str(line).encode())
        return checksum.hexdigest()
    files = []
    if data_type == 'file':
        files = [os.path.normpath(data)]
    if data_type == 'dir':
        for root, directories, filenames in os.walk(os.path.normpath(data)):
            for filename in sorted(filenames):
                files.append(os.path.normpath(os.path.join(root, filename)))
    for file_path in files:
        if sys.version_info >= (3, 0, 0):
            if os.name == 'nt':
                input_file = io.open(file_path, 'r', encoding='ISO-8859-1')
            else:
                input_file = open(file_path, 'r', encoding='ISO-8859-1')
        else:
            input_file = io.open(file_path, encoding='latin-1')


        # lines = open(file_path, mode)
        # lines = io.open(file_path, 'rt')

        # lines = io.open(file_path, 'rU')
        for line in input_file:
            if type(line) == bytes:
                checksum.update(line)
            else:
                checksum.update(str(line).encode())
    return checksum.hexdigest()


def sort_file(file_path):
    """Sort file by line and return the file
    function is used for only testing and can handle the file of the size
    """
    file_path = os.path.normpath(file_path)


    # infile = open(file_path, 'rU')
    if sys.version_info >= (3, 0, 0):
        if os.name == 'nt':
            input_file = io.open(file_path, 'r', encoding='ISO-8859-1')
        else:
            input_file = open(file_path, 'r', encoding='ISO-8859-1')
    else:
        input_file = io.open(file_path, encoding='latin-1')



    # # useles if line.strip()
    # if os.name=='nt':
    #     lines = [line.strip() for line in input_file]
    # else:
    #     lines = [line.strip() for line in ]
    lines = [line.strip().replace('\x00', '') for line in input_file]
    input_file.close()



    # outfile = open(file_path, 'w')
    if sys.version_info >= (3, 0, 0):
        if os.name == 'nt':
            outfile = io.open(file_path, 'w', encoding='ISO-8859-1')
        else:
            outfile = open(file_path, 'w', encoding='ISO-8859-1')

    else:
        outfile = io.open(file_path, 'wb')


    lines.sort()
    for line in lines:
        outfile.write(line + "\n")
    outfile.close()
    return file_path


def sort_csv(filename):
    """Sort CSV rows minus the header and return the file
    function is used for only testing and can handle the file of the size
    """
    filename = os.path.normpath(filename)
    if sys.version_info >= (3, 0, 0):
        if os.name == 'nt':
            input_file = io.open(filename, 'r', newline='', encoding='ISO-8859-1')
        else:
            input_file = open(filename, 'r', encoding='ISO-8859-1')
    else:
        input_file = io.open(filename, encoding='latin-1')
    # input_file = io.open(filename,'r', newline='', encoding='ISO-8859-1')


    # input_file = open(filename,  newline='', encoding='utf-8')
    csv_reader_infile = csv.reader(input_file, escapechar="\\")
    #  write the data to a temporary file and sort it
    temp_file = os.path.normpath("tempfile")

    if sys.version_info >= (3, 0, 0):
        if os.name == 'nt':
            file_temp = io.open(temp_file, 'w', newline='',  encoding='ISO-8859-1')
        else:
            file_temp = open(temp_file, 'w', encoding='ISO-8859-1')

    else:
        file_temp = io.open(temp_file, 'wb')

    if os.name == 'nt':
        csv_writer = csv.writer(file_temp, dialect='excel', escapechar='\\', lineterminator='\n')
    else:
        csv_writer = csv.writer(file_temp, dialect='excel', escapechar='\\', lineterminator='\n')
    i = 0
    for row in csv_reader_infile:
        if i == 0:
            # The first entry is the header line
            infields = row
            i += 1
        else:
            csv_writer.writerow(row)

    file_temp.close()
    input_file.close()


    # sort the temp file
    sorted_txt = sort_file(temp_file)



    # write sorted row content to csv filename with header "infields"
    # tmp = open(sorted_txt, "rU")
    # in_txt = csv.reader(tmp, delimiter=',')
    if sys.version_info >= (3, 0, 0):
        if os.name == 'nt':
            tmp = io.open(sorted_txt, 'r',newline='', encoding='ISO-8859-1')
        else:
            tmp = open(sorted_txt, 'r', encoding='ISO-8859-1')
    else:
        tmp = io.open(sorted_txt, encoding='latin-1')

    in_txt = csv.reader(tmp, delimiter=',', escapechar="\\")



    # if os.name == 'nt':
    #     out_csv = csv.writer(open(filename, 'w'), lineterminator='\n')
    # else:
    #     out_csv = csv.writer(open(filename, 'w'))

    if sys.version_info >= (3, 0, 0):
        if os.name == 'nt':
            file_temp = io.open(filename, 'w', newline='', encoding='ISO-8859-1')
        else:
            file_temp = io.open(filename, 'w', encoding='ISO-8859-1')
    else:
        file_temp = io.open(filename, 'wb')

    if os.name == 'nt':
        csv_writer = csv.writer(file_temp, dialect='excel', escapechar='\\', lineterminator='\n')
    else:
        csv_writer = csv.writer(file_temp, dialect='excel', escapechar='\\')

    csv_writer.writerow(infields)
    csv_writer.writerows(in_txt)
    tmp.close()
    file_temp.close()
    os.remove(os.path.normpath(temp_file))
    return filename


def create_file(data, output='output_file'):
    """Writes a string to a file for use by tests"""
    output_file = os.path.normpath(output)
    with open(output_file, 'w') as testfile:
        testfile.write(data)
        testfile.close()
    return output_file


def file_2string(input_file):
    """return file contents as a string"""
    input_file= os.path.normpath(input_file)
    if sys.version_info >= (3, 0, 0):
        input = io.open(input_file, 'rU')
    else:
        input = io.open(input_file, encoding='latin-1')

    obs_out = input.read()
    return obs_out

