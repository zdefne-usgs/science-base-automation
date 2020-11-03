# -*- coding: utf-8 -*-
"""
autoSB.py

By: Emily Sturdivant, esturdivant@usgs.gov
Last modified: 1/10/17

OVERVIEW: Functions used in sb_automation.py
"""
#%% Import packages
import sciencebasepy as pysb
import os
import sys
import shutil
import glob
from lxml import etree
import json
import pickle
from datetime import datetime
import time
import io
import re

__all__ = ['splitall', 'splitall2', 'remove_files', 'trunc', 'replace_in_file',
           'get_title_from_data', 'get_root_flexibly', 'add_element_to_xml', 'fix_attrdomv_error',
           'remove_xml_element', 'replace_element_in_xml', 'map_newvals2xml',
           'find_and_replace_text', 'find_and_replace_from_dict',
           'update_xml_tagtext', 'flip_dict', 'update_xml', 'update_all_xmls', 'json_from_xml',
           'get_fields_from_xml', 'log_in', 'log_in2', 'flexibly_get_item',
           'get_DOI_from_item', 'fix_falsefolder', 'rename_dirs_from_xmls', 'setup_subparents', 'inherit_SBfields', 'find_or_create_child',
           'upsert_metadata', 'replace_files_by_ext', 'upload_files', 'upload_files_matching_xml',
           'upload_shp', 'find_browse_in_json', 'update_browse', 'update_all_browse_graphics', 'upload_all_updated_xmls', 'get_parent_bounds', 'get_idlist_bottomup',
           'set_parent_extent', 'find_browse_file', 'upload_all_previewImages2', 'upload_all_previewImages', 'shp_to_new_child',
           'update_datapage', #'update_subpages_from_landing',
           'get_pageid_from_xmlpath',
           'update_pages_from_XML_and_landing', 'remove_all_files',
           'update_existing_fields',
           'delete_all_children', 'remove_all_child_pages',
           'check_fields', 'check_fields2', 'check_fields3', 'check_fields2_topdown',
           'landing_page_from_parentdir', 'inherit_topdown',
           'apply_topdown', 'apply_bottomup', 'restore_original_xmls']


#%% Functions
def splitall(path):
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return(allparts)

def splitall2(path):
    # lists directory paths, each item ends with one more directory on the path
    allparts2 = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts2.insert(0, path)
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts2.insert(0, path)
            break
        else:
            allparts2.insert(0, path)
            path = parts[0]
    return(allparts2)

def remove_files(parentdir, pattern='**/*.xml_orig'):
    # Recursively remove files matching pattern
    xmllist = glob.glob(os.path.join(parentdir, pattern), recursive=True)
    for xml_file in xmllist:
        os.remove(xml_file)
    return(parentdir)

###################################################
#
# Work with XML
#
###################################################
def trunc(string, length=40):
    string = (string[:length-3] + '...') if len(string) > length else string
    return(string)

def replace_in_file(fname, fstr, rstr, fill='xxx'):
    with io.open(fname, 'r', encoding='utf-8') as f:
        s = f.read()
    s, ct = re.subn(fstr, rstr, s)
    print("Replaced values matching '{}': {}.".format(trunc(fstr), ct))
    ct_fills = len(re.findall('(?i){}'.format(fill), s)) # Count remaining xxx values
    if ct_fills > 0:
        print("Found {} '{}' fills remaining.".format(ct_fills, fill))
    with io.open(fname, 'w', encoding='utf-8') as f:
        f.write(s)
    return(fname)

def get_title_from_data(xml_file, metadata_root=False):
    try:
        if not metadata_root:
            tree = etree.parse(xml_file) # parse metadata using etree
            metadata_root=tree.getroot()
        title = metadata_root.findall('./idinfo/citation/citeinfo/title')[0].text # Get title of child from XML
        return title
    except Exception as e:
        print("Exception while trying to parse XML file ({}): {}".format(xml_file, e), file=sys.stderr)
        return False

def get_root_flexibly(in_metadata):
    # Whether in_metadata is a filename or an element, get metadata_root
    # in_metadata accepts either xml file or root element of parsed metadata.
    if type(in_metadata) is etree._Element:
        metadata_root = in_metadata
        tree = False
        xml_file =False
    elif type(in_metadata) is str:
        xml_file = in_metadata
        try:
            tree = etree.parse(xml_file) # parse metadata using etree
        except etree.XMLSyntaxError as e:
            print("XML Syntax Error while trying to parse XML file: {}".format(e))
            return False
        except Exception as e:
            print("Exception while trying to parse XML file: {}".format(e))
            return False
        metadata_root=tree.getroot()
    else:
        print("{} is not an accepted variable type for 'in_metadata'".format(in_metadata))
    return(metadata_root, tree, xml_file)

def add_element_to_xml(in_metadata, new_elem, containertag='./idinfo'):
    # Appends element 'new_elem' to 'containertag' in XML file. in_metadata accepts either xmlfile or root element of parsed metadata. new_elem accepts either lxml._Element or XML string
    # Whether in_metadata is a filename or an element, get metadata_root
    # FIXME: Check whether element already exists
    metadata_root, tree, xml_file = get_root_flexibly(in_metadata)
    # If new element is still a string convert it to an XML element
    if type(new_elem) is str:
        new_elem = etree.fromstring(new_elem)
    elif not type(new_elem) is etree._Element:
        raise TypeError("'new_elem' takes either strings or elements.")
    # Append new_elem to containertag element
    elem = metadata_root.findall(containertag)[0]
    elem.append(new_elem) # append new tag to container element
    # Either overwrite XML file with new XML or return the updated metadata_root
    if type(xml_file) is str:
        tree.write(xml_file)
        return(xml_file)
    else:
        return(metadata_root)

def fix_attrdomv_error(in_metadata, verbose=False):
    # Fix attrdomv so that each has only one subelement
    metadata_root, tree, xml_file = get_root_flexibly(in_metadata)
    attrdomv = metadata_root.findall('./eainfo/detailed/attr/attrdomv')
    for elem in attrdomv:
        subelems = elem.getchildren()
        if len(subelems) > 1:
            if verbose:
                print('fixing error in Attribute Domain Values...')
            parent = elem.getparent()
            for child in subelems:
                new_elem = parent.makeelement(elem.tag)
                new_elem.insert(0, child)
                parent.append(new_elem)
            parent.remove(elem)
    if type(xml_file) is str:
        tree.write(xml_file)
        return xml_file
    else:
        return metadata_root

def remove_xml_element(in_metadata, path='./', fill_text=['AUTHOR']):
    # Remove XML elements in path that contain fill text
    """ Example:
    tree = etree.parse(xml_file)
    metadata_root = tree.getroot()
    metadata_root = remove_xml_element(metadata_root)
    tree.write(xml_file)
    """
    # get metadata root
    metadata_root, tree, xml_file = get_root_flexibly(in_metadata)
    # get fill_text as list of strings
    if type(fill_text) is str:
        fill_text = [fill_text]
    elif not type(fill_text) is list:
        print('fill_text must be string or list')
        raise(Exception)
    # Search the matching tags for fill_text and remove all elements in which it is found.
    container, tag = os.path.split(path)
    parent_elem = metadata_root.find(container)
    for elem in parent_elem.iter(tag):
        for text in elem.itertext():
            for ftext in fill_text:
                if ftext in text:
                    parent_elem.remove(elem)
    # Either overwrite XML file with new XML or return the updated metadata_root
    if type(xml_file) is str:
        tree.write(xml_file)
        return(xml_file)
    else:
        return(metadata_root)

def replace_element_in_xml(in_metadata, new_elem, containertag='./distinfo'):
    # Overwrites the first element in containertag corresponding to the tag of new_elem
    # in_metadata accepts either xml file or root element of parsed metadata.
    # new_elem accepts either lxml._Element or XML string
    # Whether in_metadata is a filename or an element, get metadata_root
    metadata_root, tree, xml_file = get_root_flexibly(in_metadata)
    # If new element is still a string convert it to an XML element
    if type(new_elem) is str:
        new_elem = etree.fromstring(new_elem)
    elif not type(new_elem) is etree._Element:
        raise TypeError("'new_elem' takes either strings or elements.")
    # Replace element with new_elem
    elem = metadata_root.findall(containertag)[0]
    old_elem = elem.findall(new_elem.tag)[0]
    elem.replace(old_elem, new_elem)
    # Either overwrite XML file with new XML or return the updated metadata_root
    if type(xml_file) is str:
        tree.write(xml_file)
        return(xml_file)
    else:
        return(metadata_root)

def replace_element_in_xml_for_wrapper(metadata_root, new_elem, containertag='./distinfo'):
    if type(new_elem) is str:
        new_elem = etree.fromstring(new_elem)
    elif not type(new_elem) is etree._Element:
        raise TypeError("'new_elem' takes either strings or elements.")
    # Replace element with new_elem
    elem = metadata_root.findall(containertag)[0]
    old_elem = elem.findall(new_elem.tag)[0]
    elem.replace(old_elem, new_elem)
    return metadata_root

def xml_write_wrapper(in_metadata, new_elem, containertag='./distinfo'):
    # FIXME: I don't actually know how to make a wrapper. This is completely unchecked.
    # in_metadata accepts either xml file or root element of parsed metadata.
    # Whether in_metadata is a filename or an element, get metadata_root
    metadata_root, tree, xml_file = get_root_flexibly(in_metadata)
    # if type(in_metadata) is etree._Element:
    #     metadata_root = in_metadata
    #     xml_file =False
    # elif type(in_metadata) is str:
    #     xml_file = in_metadata
    #     tree = etree.parse(xml_file) # parse metadata using etree
    #     metadata_root=tree.getroot()
    # else:
    #     print("{} is not an accepted variable type for 'in_metadata'".format(in_metadata))
    # If new element is still a string convert it to an XML element
    replace_element_in_xml_for_wrapper(metadata_root, new_elem, containertag)
    # Either overwrite XML file with new XML or return the updated metadata_root
    if type(xml_file) is str:
        tree.write(xml_file)
        return(xml_file)
    else:
        return(metadata_root)

def map_newvals2xml(new_values):
    # Create dictionary of {new value: {XPath to element: position of element in list retrieved by XPath}}
    """
    To update XML elements with new text:
        for newval, elemfind in val2xml.items():
            for elempath, i in elemfind.items():
                metadata_root.findall(elempath)[i].text = newval
    Currently hard-wired; will need to be adapted to match metadata scheme.
    """
    # Hard-wire path in metadata to each element
    seriesid = './idinfo/citation/citeinfo/serinfo/issue' # Citation / Series / Issue Identification
    citelink = './idinfo/citation/citeinfo/onlink' # Citation / Online Linkage
    lwork_link = './idinfo/citation/citeinfo/lworkcit/citeinfo/onlink' # Larger Work / Online Linkage
    lwork_serID = './idinfo/citation/citeinfo/lworkcit/citeinfo/serinfo/issue' # Larger Work / Series / Issue Identification
    lwork_pubdate = './idinfo/citation/citeinfo/lworkcit/citeinfo/pubdate' # Larger Work / Publish date
    edition = './idinfo/citation/citeinfo/edition' # Citation / Edition
    pubdate = './idinfo/citation/citeinfo/pubdate' # Citation / Publish date
    caldate = './idinfo/timeperd/timeinfo/sngdate/caldate'
    networkr = './distinfo/stdorder/digform/digtopt/onlinopt/computer/networka/networkr' # Network Resource Name
    accinstr = './distinfo/stdorder/digform/digtopt/onlinopt/accinstr'
    metadate = './metainfo/metd' # Metadata Date
    browsen = './idinfo/browse/browsen'
    # Initialize storage dictionary
    val2xml = {}
    # DOI values
    if 'doi' in new_values.keys():
        # get DOI values (as issue and URL)
        doi_issue = "DOI:{}".format(new_values['doi'])
        doi_url = "https://doi.org/{}".format(new_values['doi'])
        # add new DOI values as {DOI:XXXXX:{'./idinfo/.../issue':0}}
        val2xml[doi_issue] = {seriesid:0, lwork_serID:0}
        val2xml[doi_url] = {citelink: 0, lwork_link: 0, networkr: 2}
    # Landing URL
    if 'landing_id' in new_values.keys():
        landing_link = 'https://www.sciencebase.gov/catalog/item/{}'.format(new_values['landing_id'])
        val2xml[landing_link] = {lwork_link: 1}
    # Data page URL
    if 'child_id' in new_values.keys():
        # get URLs
        page_url = 'https://www.sciencebase.gov/catalog/item/{}'.format(new_values['child_id']) # data_item['link']['url']
        directdownload_link = 'https://www.sciencebase.gov/catalog/file/get/{}'.format(new_values['child_id'])
        # add values
        val2xml[page_url] = {citelink: 1, networkr: 0}
        val2xml[directdownload_link] = {networkr:1}
        access_str = 'The first link is to the page containing the data. The second is a direct link to download all data available from the page as a zip file. The final link is to the publication landing page. The data page (first link) may have additional data access options, including web services.'
        val2xml[access_str] = {accinstr: 0}
        # Browse graphic
        if 'browse_file' in new_values.keys():
            browse_link = '{}/?name={}'.format(directdownload_link, new_values['browse_file'])
            val2xml[browse_link] = {browsen:0}
    # Edition
    if 'edition' in new_values.keys():
        val2xml[new_values['edition']] = {edition:0}
    if 'pubdate' in new_values.keys():
        val2xml[new_values['pubdate']] = {pubdate:0, lwork_pubdate:0} # removed caldate
    # Date and time of update
    now_str = datetime.now().strftime("%Y%m%d")
    val2xml[now_str] = {metadate: 0}
    return(val2xml)

def find_and_replace_text(fname, findstr='http:', replacestr='https:'):
    os.rename(fname, fname+'.tmp')
    with open(fname+'.tmp', 'r') as f1:
        with open(fname, 'w') as f2:
            for line in f1:
                f2.write(line.replace(findstr, replacestr))
    os.remove(fname+'.tmp')
    return fname

def find_and_replace_from_dict(fname, find_dict):
    # Takes dictionary of {find_value: replace_value}
    ct = 0
    with io.open(fname, 'r', encoding='utf-8') as f:
        s = f.read()
    # Iterate through find:replace pairs
    for fstr, rstr in find_dict.items():
        s = s.replace(fstr, rstr)
    with io.open(fname, 'w', encoding='utf-8') as f:
        f.write(s)
    return(fname)

def update_xml_tagtext(metadata_root, newval, fstr='./distinfo', idx=0):
    # Add or update the values of each element
    try:
        metadata_root.findall(fstr)[idx].text = newval
    except IndexError: # if the element does not yet exist, create the element
        try:
            container, tag = os.path.split(fstr)
            elem = metadata_root.find(container)
            elem.append(etree.Element(tag))
            metadata_root.findall(fstr)[idx].text = newval
        except Exception as e:
            print('Exception raised: {}'.format(e))
            pass
    except Exception as e:
        print('Exception raised: {}'.format(e))
        pass

def flip_dict(in_dict, verbose=False):
    # convert nested dictionary structure
    # rework the dictionary to {tag fstring: {index: new value}}
    out_dict = {}
    for newval, elemfind in in_dict.items(): # Update elements with new ID text
        for fstr, idx in elemfind.items():
            if not fstr in out_dict:
                if verbose:
                    print(fstr)
                out_dict[fstr] = {idx: newval}
            else:
                if verbose:
                    print('  {}: {}'.format(idx, newval))
                out_dict[fstr][idx] = newval
    return(out_dict)

def update_xml(xml_file, new_values, verbose=False):
    # update XML file to include new child ID and DOI
    #%% Map new values to their appropriate metadata elements
    e2nv = map_newvals2xml(new_values)
    e2nv_flipped = flip_dict(e2nv, verbose=False)
    #%% Update the XML with the new values
    # Save the original xml_file if an original is not already present
    if not os.path.exists(xml_file+'_orig'):
        shutil.copy(xml_file, xml_file+'_orig')
    # Parse metadata
    metadata_root, tree, xml_file = get_root_flexibly(xml_file)
    # Update elements with new text values
    for fstr, idx_val in e2nv_flipped.items():
        for idx in sorted(idx_val):
            newval = idx_val[idx]
            # Update elements with new text value
            update_xml_tagtext(metadata_root, newval, fstr, idx)
    #%% Modify XML as programmed in config file.
    if "remove_fills" in new_values:
        [remove_xml_element(metadata_root, path, ftext) for path, ftext in new_values['remove_fills'].items()]
    if "metadata_additions" in new_values:
        [add_element_to_xml(metadata_root, new_elem, containertag) for containertag, new_elem in new_values['metadata_additions'].items()]
    if "metadata_replacements" in new_values:
        [replace_element_in_xml(metadata_root, new_elem, containertag) for containertag, new_elem in new_values['metadata_replacements'].items()]
    #%% Fix common error in which attrdomv has multiple subelements
    metadata_root = fix_attrdomv_error(metadata_root)
    #%% Save changes - overwrite XML file with new XML
    tree.write(xml_file)
    #%% Perform find and replace the text in the file
    if "find_and_replace" in new_values:
        find_and_replace_from_dict(xml_file, new_values['find_and_replace'])
    return(xml_file)

def update_all_xmls(parentdir, new_values, sb=None, dict_DIRtoID=None, verbose=True):
    # Update every XML in the directory tree with new values (from config file and SB)
    # Does not upload resulting XML to SB.
    xmllist = glob.glob(os.path.join(parentdir, '**/*.xml'), recursive=True)
    for xml_file in xmllist:
        # Update XML
        # Get SB values
        datapageid = get_pageid_from_xmlpath(xml_file, sb, dict_DIRtoID, parentdir=parentdir, verbose=False)
        # add SB UID to be updated in XML
        new_values['child_id'] = datapageid
        # Look for browse graphic in directory with XML
        datadir = os.path.dirname(xml_file)
        browse_file = find_browse_file(datadir)
        new_values.pop('browse_file', None) # remove value from past iteration
        if browse_file:
            new_values['browse_file'] = browse_file
        # Make the changes to the XML based on the new_values dictionary
        update_xml(xml_file, new_values, verbose=verbose) # new_values['pubdate']
        if verbose:
            print("UPDATED XML: {}".format(xml_file))
    return

def json_from_xml():
    #FIXME: Currently hard-wired; will need to adapted to match metadata scheme.
    dict_xml2sb = dict()
    #dict_xml2sb['citation'] =
    dict_xml2sb['purpose'] = {'./idinfo/descript/purpose':0}
    dict_xml2sb['summary'] = {'./idinfo/descript/abstract':0}
    dict_xml2sb['body'] = {'./idinfo/descript/abstract':0}
    return dict_xml2sb

def get_fields_from_xml(sb, item, xml_file, sbfields, metadata_root=False):
    # Based on desired SB fields, get text values from XML
    if not metadata_root:
        tree = etree.parse(xml_file) # parse metadata using etree
        metadata_root=tree.getroot()
    dict_sb_from_xml = json_from_xml() # return dict for locating values in XML
    for field in sbfields:
        elemfind = dict_sb_from_xml[field]
        for fstr,i in elemfind.items():
            try:
                item[field] = metadata_root.findall(fstr)[i].text
            except:
                pass
    item = sb.updateSbItem(item)
    return item

###################################################
#
# SB helper functions
#
###################################################
def log_in(username=None, password=None):
    print('Logging in if necessary...')
    if 'sb' in globals():
        if not sb.is_logged_in():
            print('Logging back in...')
        else:
            return sb
    if not username:
        username = input("SB username (should be entire USGS email): ")
    if not password:
        sb = pysb.SbSession(env=None).loginc(username)
    else:
        try:
            sb = pysb.SbSession(env=None).login(username, password)
        except Exception as e: # 'Login failed' returned as Exception for bad password in login()
            print('{}. Try reentering...'.format(e))
            sb = pysb.SbSession(env=None).loginc(username) # 'Invalid password, try again' printed for bad password
        except NameError as e:
            print('{}. Try reentering...'.format(e))
            sb = pysb.SbSession(env=None).loginc(username)
    return sb

def log_in2(username=False, password=False, sb=[]):
    if not sb.is_logged_in():
        print('Logging back in...')
        try:
            sb = pysb.SbSession(env=None).login(username, password)
        except NameError:
            sb = pysb.SbSession(env=None).loginc(username)
    return sb

def flexibly_get_item(sb, id_or_json, output='item'):
    # Given input of either ID or JSON, return ID, link, or JSON item
    if type(id_or_json) is str: # If input is ID...
        item_id = id_or_json
        if output.lower() == 'item' or output.lower() == 'url':
            item = sb.get_item(item_id)
    elif type(id_or_json) is dict: # If input is JSON...
        item = id_or_json
        item_id = item['id']
    # Return ID, URL, or JSON item (default)
    if output.lower() == 'id':
        return item_id
    elif output.lower() == 'url':
        item_link = item['link']['url']
        return item_link
    else:
        return item

def get_DOI_from_item(item):
    # Get DOI link from parent_item
    doi = False
    i = 0
    try:
        weblinks = item['webLinks']
    except:
        print("No 'webLinks' in JSON for {}.".format(item['id']))
        return False
    while not doi:
        doi = doi[-16:] if 'doi' in weblinks[i]['uri'].lower() else False
        i += 1
    return doi

def fix_falsefolder(sb, falsefolder_id, useremail, password):
    # Occasionally a child page is falsely identified as a folder even though it doesn't have children. In that case, this should fix it. 1. Add a child page to the false folder. 2. Delete the child. 3. remove the 'Folder'
    sb = log_in(useremail, password)
    child_item = sb.create_item({'parentId': falsefolder_id, 'title':'meow'})
    sb.delete_item(child_item)
    falsefolder_item = sb.get_item(falsefolder_id)
    falsefolder_item['systemTypes'].remove('Folder')
    falsefolder_item = sb.update_item(falsefolder_item)
    if falsefolder_item['hasChildren']:
        print("'hasChildren' successfully set to False. ")
    if 'Folder' in falsefolder_item['systemTypes']:
        print("Still recognized as a folder... :(")
    return

def rename_dirs_from_xmls(parentdir, rename_intermediates=True):
    """
    Rename directories that contain a single XML. Rename the directory to the title in the XML file.
    Notes:
    - I have run this on OSX with colons in the titles without issue. The renamed directories have backslash instead of colon, but the ScienceBase page titles have colons even though they are copied from the directory names.
    - Use rename_intermediates to specify whether directory must not contain sub-directories.
    - Although colons don't seem to be a problem on Mac, parentheses might be. Don't include parentheses in titles.
    """
    # List characters that are invalid pathnames in OSX (:) or Windows (the rest).
    invalid_chars = r'< > : " / \ | ? *'.split(' ')
    # Initialize
    ct = 0
    invalid_titles = []
    # For all XML files...
    xmllist = glob.glob(os.path.join(parentdir, '**/*.xml'), recursive=True)
    for xml_file in xmllist:
        datadir = os.path.dirname(xml_file)
        # Check whether directory meets conditions: contains only one XML and (optionally) does not contain subdirectories.
        go = False
        if [len(glob.glob(os.path.join(datadir, '**/*.xml'), recursive=True)) == 1]:
            go = True
            # and doesn't contain sub-directories...
            if rename_intermediates and any([os.path.isdir(os.path.join(datadir,fn)) for fn in os.listdir(datadir)]):
                go = False
        # If directory meets the conditions, rename it.
        if go:
            data_title = get_title_from_data(xml_file)
            data_title = data_title.strip('\n')
            # Rename if the values don't already match
            basedir = os.path.dirname(datadir)
            if not datadir == os.path.join(basedir, data_title):
                # Check for invalid characters
                if any(x in data_title for x in invalid_chars):
                    invalid_titles += [data_title]
                os.rename(datadir, os.path.join(basedir, data_title))
                ct+=1
    if len(invalid_titles):
        print('WARNING: The following titles include invalid characters. Consider changing:\n{}'.format('\n'.join(invalid_titles)))
    print("Renamed {} directories.".format(ct))
    return

def setup_subparents(sb, parentdir, landing_id, imagefile, verbose=True):
    landing_item = sb.get_item(landing_id)
    # Initialize dictionaries
    dict_DIRtoID = {os.path.basename(parentdir): landing_id} # Initialize [top dir/file: ID] entry to dict
    # List XML files
    xmllist = glob.glob(os.path.join(parentdir, '**/*.xml'), recursive=True)
    for xml_file in xmllist:
        # get relative path from parentdir to XML, including parentdir
        relpath = os.path.relpath(xml_file, os.path.dirname(parentdir))
        # Find or create the SB page for each directory
        dirchain = splitall2(os.path.dirname(relpath))
        for dirpath in dirchain[1:]:
            parent_id = dict_DIRtoID[os.path.dirname(dirpath)] # get ID for parent
            if dirpath in dict_DIRtoID:
                continue
            subpage = find_or_create_child(sb, parent_id, os.path.basename(dirpath), verbose=verbose) # get JSON for subpage based on parent ID and dirpath
            if not imagefile == False:
                subpage = sb.upload_file_to_item(subpage, imagefile)
            # store values in dictionaries
            dict_DIRtoID[dirpath] = subpage['id']
    return(dict_DIRtoID)

def inherit_SBfields(sb, child_item, inheritedfields=['citation'], verbose=False, inherit_void=True):
    # Upsert inheritedfield from parent to child by retrieving parent_item based on child
    # Modified 3/8/17: if field does not exist in parent, remove in child
    # If field is entered incorrecly, no errors will be thrown, but the page will not be updated.
    parent_item = flexibly_get_item(sb, child_item['parentId'])
    if verbose:
        print("Inheriting fields from parent '{}'".format(trunc(parent_item['title'])))
    for field in inheritedfields:
        if not field in parent_item:
            if inherit_void:
                child_item[field] = None
            else:
                print("Field '{}' does not exist in parent and inherit_void is set to False so the current value will be preserved in child '{}'.".format(field, trunc(child_item['title'])))
        else:
            try:
                child_item[field] = parent_item[field]
            except Exception as e:
                print(e)
                pass
    child_item = sb.update_item(child_item)
    return(child_item)

def find_or_create_child(sb, parentid, child_title, verbose=False):
    # Find or create new child page
    for child_id in sb.get_child_ids(parentid): # Check if child page already exists
        child_item = sb.get_item(child_id)
        if child_item['title'] == child_title:
            if verbose:
                print("FOUND: page '{}'.".format(trunc(child_title)))
            break
    else: # If child doesn't already exist, create
        child_item = {}
        child_item['parentId'] = parentid
        child_item['title'] = child_title
        child_item = sb.create_item(child_item)
        if verbose:
            print("CREATED PAGE: '{}' in '{}.'".format(trunc(child_title, 40), sb.get_item(parentid)['title']))
        time.sleep(1) # wait 1 sec to ensure that page is registered
    return child_item

def get_file_upload_time(data_item, file_type='application/fgdc+xml'):
    time_uploaded = None
    if 'files' in data_item:
        for fl_idx, fl_json in enumerate(data_item['files']):
            if fl_json['contentType'] == file_type:
                time_uploaded = fl_json['dateUploaded']
                break
    # If the browse graphic got included in a facet (or extension?)
    if not time_uploaded and 'facets' in data_item:
        for fc_idx, facet in enumerate(data_item['facets']):
            for fl_idx, fl_json in enumerate(facet['files']):
                if fl_json['contentType'] == file_type:
                    time_uploaded = fl_json['dateUploaded']
                    break
            if time_uploaded:
                break
    if not time_uploaded:
        print("No XML found.")
    return(time_uploaded)

def upsert_metadata(sb, id_or_item, xml_file):
    # Remove file with the originalMetadata flag. Then upload the xml file.
    data_item = flexibly_get_item(sb, id_or_item, output='item')
    found_metadata = False
    if 'files' in data_item:
        for fidx, file in enumerate(data_item['files']):
            if file['originalMetadata']:
                data_item['files'].pop(fidx)
                found_metadata = True
    if 'facets' in data_item:
        for fc_idx, facet in enumerate(data_item['facets']):
            for fl_idx, file in enumerate(facet['files']):
                if file['originalMetadata']:
                    data_item['facets'][fc_idx]['files'].pop(fl_idx)
                    found_metadata = True
    if found_metadata:
        data_item = sb.update_item(data_item)
    data_item = sb.upload_file_to_item(data_item, xml_file)
    return(data_item)

#%% Update SB preview image from the uploaded files.
def update_all_browse_graphics(sb, parentdir, landing_id, valid_ids=None, verbose=False):
    # Update SB preview image from the uploaded files and update filename and type in XML.
    # For every XML in the parentdir (recursive)...
    print("Updating browse graphic information...")
    xmllist = glob.glob(os.path.join(parentdir, '**/*.xml'), recursive=True)
    for xml_file in xmllist:
        # Get SB page ID from the XML (needs to be up-to-date)
        datapageid = get_pageid_from_xmlpath(xml_file, sb, valid_ids=valid_ids, parentdir=parentdir, verbose=verbose)
        # Run update_browse() to match the XML values with the image file on the SB page. Get browse caption from the XML. Get name of *browse* image file on SB and set as preview. Update the filename and type in the XML.
        if update_browse(sb, xml_file, datapageid, verbose):
            # if the XML was updated, replace the XML on the page.
            data_item = upsert_metadata(sb, datapageid, xml_file)
    return

def upload_all_updated_xmls(sb, parentdir, valid_ids=None):
    # Upload XMLs that have been updated since last upload to SB.
    # Iterates through local XMLs rather than starting on SB
    ct = 0
    xmllist = glob.glob(os.path.join(parentdir, '**/*.xml'), recursive=True)
    print("Searching {} XML files for changes since last upload...".format(len(xmllist)))
    for xml_file in xmllist:
        # Get SB JSON item that corresponds to XML file (try matching folder name to SB or get second link in XML citeinfo) # Get page_id from the SB title or the SB citation in the XML file.
        datapageid = get_pageid_from_xmlpath(xml_file, sb, valid_ids=valid_ids, parentdir=parentdir)
        data_item = flexibly_get_item(sb, datapageid, output='item')
        # Get upload time of XML as UTC datetime object
        xml_uploaded = get_file_upload_time(data_item, file_type='application/fgdc+xml')
        xml_uploaded = datetime.strptime(xml_uploaded, '%Y-%m-%dT%H:%M:%SZ')
        # Get modified time of local XML as UTC datetime
        xml_modified = datetime.utcfromtimestamp(os.path.getmtime(xml_file))
        # Replace the metadata file if the modified time is greater than the uploaded time
        if xml_modified > xml_uploaded:
            data_item = upsert_metadata(sb, data_item, xml_file)
            # print('UPLOADED: {}'.format(os.path.basename(xml_file)))
            ct += 1
    if ct > 0:
        print("Found and uploaded {} XML files.\n".format(ct))
    else:
        print("No XMLs have been updated since last upload.\n")
    return

def replace_files_by_ext(sb, parentdir, dict_DIRtoID, match_str='*.xml', verbose=True):
    for root, dirs, files in os.walk(parentdir):
        for d in dirs:
            path = os.path.join(root, d)
            reldirpath = os.path.relpath(path, os.path.dirname(parentdir))
            xmllist = glob.glob(os.path.join(path, match_str))
            for xml_file in xmllist:
                parentid = dict_DIRtoID[reldirpath]
                data_title = get_title_from_data(xml_file) # get title from XML
                data_item = find_or_create_child(sb, parentid, data_title, verbose=verbose) # Create (or find) data page based on title
                sb.replace_file(xml_file, data_item)
                print("REPLACED: {}".format(os.path.basename(xml_file)))
    return

def upload_files(sb, item, xml_file, max_MBsize=2000, replace=True, verbose=False):
    # Upload all files in the directory to SB page.
    if replace:
        # Remove all files (and facets) from child page
        item = remove_all_files(sb, item, verbose)
    # List all files in directory, except original xml and other bad apples
    datadir = os.path.dirname(xml_file)
    up_files = [os.path.join(datadir, fn) for fn in os.listdir(datadir)
                if not fn.endswith('_orig')
                and not fn.endswith('DS_Store')
                and not fn.endswith('.lock')
                and os.path.isfile(os.path.join(datadir, fn))]
    bigfiles = []
    for fn in up_files:
        if os.path.getsize(fn) > max_MBsize*1000000: # convert megabytes to bytes
            bigfiles.append(os.path.basename(fn))
            up_files.remove(fn)
    # Upload all files to child page
    if verbose:
        start = datetime.now()
        print("UPLOADING {}: files in directory '{}'".format(start.strftime("%X"), os.path.basename(datadir)))
        if len(bigfiles) == 1:
            print("**TO DO** File {} is too big to upload here. Please manually upload afterward.".format(bigfiles))
        elif len(bigfiles)>1:
            print("**TO DO** Files {} are too big to upload here. Please manually upload afterward.".format(bigfiles))
    item = sb.upload_files_and_upsert_item(item, up_files) # upsert should "create or update a SB item"
    if verbose:
        end = datetime.now()
        duration = end - start
        print("UPLOAD COMPLETED. Duration: {}".format(duration))
    return(item, bigfiles)

def upload_files_matching_xml(sb, item, xml_file, max_MBsize=2000, replace=True, verbose=False):
    # Upload all files matching the XML filename to SB page.
    # E.g. xml_file = 'path/data_name.ext.xml' will upload all files beginning with 'data_name'
    # optionally remove all present files
    if replace:
        # Remove all files (and facets) from child page
        item = remove_all_files(sb, item, verbose)
    # List all files matching XML
    dataname = xml_file.split('.')[0]
    dataname = dataname.split('_meta')[0]
    # up_files = glob.glob(searchstr)
    up_files = [fn for fn in glob.iglob(dataname + '*')
                if not fn.endswith('_orig') and not os.path.isdir(fn)]
    bigfiles = []
    for f in up_files:
        if os.path.getsize(f) > max_MBsize*1000000: # convert megabytes to bytes
            bigfiles.append(os.path.basename(f))
            up_files.remove(f)
    # Upload all files pertaining to data to child page
    if verbose:
        print("UPLOADING: files matching '{}'".format(os.path.basename(dataname + '*')))
        if len(bigfiles)>0 and len(bigfiles)<2:
            print("**TO DO** File {} is too big to upload here. Please manually upload afterward.".format(bigfiles))
        elif len(bigfiles)>1:
            print("**TO DO** Files {} are too big to upload here. Please manually upload afterward.".format(bigfiles))
    item = sb.upload_files_and_upsert_item(item, up_files) # upsert should "create or update a SB item"
    if verbose:
        print("UPLOAD COMPLETED.")
    return item, bigfiles

def upload_shp(sb, item, xml_file, replace=True, verbose=False):
    # Upload shapefile files to SB page, optionally remove all present files
    data_name = os.path.splitext(os.path.basename(xml_file))[0]
    datapath = os.path.dirname(xml_file)
    if replace:
        # Remove all files (and facets) from child page
        item = remove_all_files(sb, item, verbose)
    # List files pertaining to shapefile for upload
    shp_exts = ['.cpg','.dbf','.prj','.sbn','.sbx','.shp','.shx','dbf.xml','.shp.xml']
    up_files = []
    # Upload all files pertaining to data to child page
    for ext in shp_exts:
        fname = '{}{}'.format(os.path.splitext(data_name)[0],ext)
        if os.path.isfile(os.path.join(datapath,fname)):
            up_files.append(os.path.join(datapath,fname))
    # Upload files
    if verbose:
        print('UPLOADING: {} ...'.format(data_name))
    item = sb.upload_files_and_upsert_item(item, up_files) # upsert should "create or update a SB item"
    return item

def find_browse_in_json(data_item, browse_desc=None, verbose=True):
    # Look for browse graphic among the uploaded files
    # data_item = sb.get_item(page_id)
    browse_image = None
    if 'files' in data_item:
        for fl_idx, fl_json in enumerate(data_item['files']):
            # Find the uploaded file that includes 'browse' and has an extension of png, gif, or jpg
            # ALTERNATIVE: could also use the 'contentType' property to match 'image/png', 'image/jpg', or 'image/gif'. This is not more flexible to typos in extensions.
            match = re.fullmatch('^.*browse.*\.(png|gif|jpg|jpeg)$', fl_json['name'])
            if match:
                # If it matches the pattern, set useForPreview to True and add the browse description from the XML as the title
                browse_image = match[0]
                data_item['files'][fl_idx]['useForPreview'] = True
                data_item['files'][fl_idx]['title'] = browse_desc
                break
    # If the browse graphic got included in a facet (or extension?)
    if not browse_image and 'facets' in data_item:
        for fc_idx, facet in enumerate(data_item['facets']):
            for fl_idx, fl_json in enumerate(facet['files']):
                # Find the uploaded file that includes 'browse' and has an extension of png, gif, or jpg
                match = re.fullmatch('^.*browse.*\.(png|gif|jpg|jpeg)$', fl_json['name'])
                if match:
                    # If it matches the pattern, set useForPreview to True and add the browse description from the XML as the title
                    browse_image = match[0]
                    data_item['facets'][fc_idx]['files'][fl_idx]['useForPreview'] = True
                    data_item['facets'][fc_idx]['files'][fl_idx]['title'] = browse_desc
                    break
            if match:
                break
    if not browse_image:
        print('No browse image found in the uploaded files.')
    else:
        if verbose:
            print('browse filename: {}'.format(browse_image))
    return(data_item, browse_image)

def update_browse(sb, in_metadata, page_id, verbose=True):
    # Match the XML values with the image file on the SB page.
    # 1. Parse the XML file and get the caption.
    # 2. Find a *browse* image file in the SB page: set the 'useForPreview' to True and get the filename
    # 3. Update the browse filename and browse type in the XML.
    # Get the caption from the metadata
    metadata_root, tree, xml_file = get_root_flexibly(in_metadata)
    browse_desc = metadata_root.findall('./idinfo/browse/browsed')[0].text
    browse_desc = trunc(browse_desc, 80)

    # Set the browse image as previewImage and get the filename from SB
    data_item = sb.get_item(page_id)
    if verbose:
        print(data_item['title'])
    data_item, browse_image = find_browse_in_json(data_item, browse_desc, verbose)
    if not browse_image:
        # If the browse image wasn't found, there's no point continuing
        return(False)
    # Update the SB page with 'useForPreview'=True
    data_item = sb.update_item(data_item)

    # Update browsen in XML to the get-file URL and browset to the type...
    browset = os.path.splitext(browse_image)[1][1:].upper()
    sb_urlstr_fileget = 'https://www.sciencebase.gov/catalog/file/get/{}/?name={}'
    browse_link = sb_urlstr_fileget.format(page_id, browse_image)
    old_link = metadata_root.findall('./idinfo/browse/browsen')[0].text
    old_t = metadata_root.findall('./idinfo/browse/browset')[0].text
    if old_link == browse_link and old_t == browset:
        return
    metadata_root.findall('./idinfo/browse/browsen')[0].text = browse_link
    metadata_root.findall('./idinfo/browse/browset')[0].text = browset

    # Either overwrite XML file with new XML or return the updated metadata_root
    if type(in_metadata) is str:
        tree.write(xml_file)
        print("Updated XML: {}".format(os.path.basename(xml_file)))
        return(True)
    else:
        return(metadata_root)

def get_parent_bounds(sb, parent_id, verbose=False):
    # UPDATED 9/6/17: added "and i < len(kids)", changed 1 to i in second loop, and added "if not parent_bounds: parent_bounds = bbox"
    item = sb.get_item(parent_id)
    kids = sb.get_child_ids(parent_id)
    if len(kids) > 0:
        # Initialize parent_bounds with first child
        i = 0
        found = False
        while not found and i < len(kids): # stop when bounding box is found in item or when there are no item left to search
            try:
                child = sb.get_item(kids[i])
            except:
                i += 1
                found = False
            if 'facets' in child:
                parent_bounds = child['facets'][0]['boundingBox']
                found = True
            elif 'spatial' in child:
                parent_bounds = child['spatial']['boundingBox']
                found = True
            else:
                i += 1
                print("Child item '{}'' does not have 'spatial' or 'facets' fields.".format(child['title']))
        if len(kids) > i:
            # Loop through kids
            for cid in kids[i:]:
                child = sb.get_item(cid)
                if 'facets' in child:
                    bbox = child['facets'][0]['boundingBox'] # {u'minX': -81.43, u'minY': 28.374, u'maxX': -80.51, u'maxY': 30.70}
                elif 'spatial' in child:
                    bbox = child['spatial']['boundingBox']
                else:
                    continue
                if not parent_bounds: # if the first step didn't find a parent, set parent_bounds to current
                    parent_bounds = bbox
                for corner in parent_bounds:
                    if 'min' in corner:
                        parent_bounds[corner] = min(bbox[corner], parent_bounds[corner])
                    if 'max' in corner:
                        parent_bounds[corner] = max(bbox[corner], parent_bounds[corner])
        # Update parent bounding box
        if 'parent_bounds' in locals():
            try:
                item['spatial']['boundingBox'] = parent_bounds
            except KeyError:
                if parent_bounds:
                    item['spatial'] = {}
                    item['spatial']['boundingBox'] = parent_bounds
            item = sb.update_item(item)
            if verbose:
                print('Updated bounding box for parent "{}"'.format(item['title']))
        else:
            parent_bounds = {}
        return parent_bounds

def get_idlist_bottomup(sb, top_id):
    tier1 = sb.get_child_ids(top_id)
    tier2 = []
    for t1 in tier1:
        tier2 += sb.get_child_ids(t1)
    tier3 = []
    for t2 in tier2:
        tier3 += sb.get_child_ids(t2)
    idlist_bottomup = tier3 + tier2 + tier1
    idlist_bottomup.append(top_id)
    return idlist_bottomup

def set_parent_extent(sb, top_id, verbose=False):
    pagelist = get_idlist_bottomup(sb,top_id)
    for page in pagelist:
        parent_bounds = get_parent_bounds(sb, page, verbose)
    return parent_bounds

def find_browse_file(datadir, searchterm='*browse*', extensions=('.png', '.jpg', '.jpeg', '.gif')):
    imagelist = []
    for ext in extensions:
        imagelist.extend(glob.glob(os.path.join(datadir, searchterm + ext)))
        if len(imagelist) > 0:
            browse_file = os.path.basename(imagelist[0])
            return(browse_file)
    print("Note: No {} image files found in the directory.".format(searchterm))
    return

def upload_all_previewImages(sb, parentdir, dict_DIRtoID=False, verbose=False):
    # Upload all image files to their respective pages.
    # 1. find all image files in folder tree
    # 2. for each image, try to upload it
    for (root, dirs, files) in os.walk(parentdir):
        for d in dirs:
            imagelist = glob.glob(os.path.join(root,d,'*browse*.png'))
            imagelist.extend(glob.glob(os.path.join(root,d,'*browse*.jpg')))
            imagelist.extend(glob.glob(os.path.join(root,d,'*browse*.jpeg')))
            imagelist.extend(glob.glob(os.path.join(root,d,'*browse*.gif')))
            reldirpath = os.path.join(os.path.relpath(root, os.path.dirname(parentdir)), d)
            for f in imagelist:
                # sb = log_in(useremail)
                try:
                    item = sb.get_item(dict_DIRtoID[reldirpath])
                except:
                    title = d # dirname should correspond to page title
                    item = sb.find_items_by_title(title)['items'][0]
                if verbose:
                    print('UPLOADING: preview image to "{}"...\n\n'.format(d))
                item = sb.upload_file_to_item(item, f)
    return

def upload_all_previewImages2(sb, parentdir, dict_DIRtoID=False, verbose=False):
    # Possibly a better workflow than the original. Completely untested.
    # Upload all image files to their respective pages.
    # 1. find all image files in folder tree
    # 2. for each image, try to upload it
    xmllist = glob.glob(os.path.join(parentdir, '**/*.xml'), recursive=True)
    for xml_file in xmllist:
        datapageid = get_pageid_from_xmlpath(xml_file, dict_DIRtoID=dict_DIRtoID, parentdir=parentdir)
        datadir = os.path.dirname(xml_file)
        data_title = os.path.basename(datadir) # dirname should correspond to page title
        # datapageid = dict_DIRtoID[os.path.relpath(datadir, os.path.dirname(parentdir))]
        # data_item = find_or_create_child(sb, datapageid, data_title, verbose=verbose)
        data_item = sb.get_item(datapageid)
        browse_file = find_browse_file(datadir)
        data_item = sb.find_items_by_title(data_title)['items'][0]
        if verbose:
            print('UPLOADING: preview image to "{}"...\n\n'.format(d))
        sb.upload_file_to_item(data_item, browse_file)
    return

def shp_to_new_child(sb, xml_file, parent, dr_doi=False, inheritedfields=False, replace=True, imagefile=False):
    # NOT USED as of 3/8/17
    # Get values
    parent_item = flexibly_get_item(sb, parent)
    # Get DOI link from parent_item
    if not dr_doi:
        dr_doi = get_DOI_from_item(parent_item)
    # Create (or find) new child page based on data title
    child_title = get_title_from_data(xml_file)
    child_item = find_or_create_child(sb, parentid, child_title, verbose=True)
    # Update XML file to include new child ID and DOI
    update_xml(xml_file, child_item['id'],dr_doi,parent_link) #if metadata.findall(formname_tagpath)[0].text == 'Shapefile':
    # Upload shapefile files (including xml)
    child_item = upload_shp(sb, child_item, xml_file, replace) # Either clear all files first or upload in addition.
    try:
        child_item = sb.upload_file_to_item(child_item, imagefile)
    except NameError: # If image file in directory, add it
        for f in os.listdir(datapath):
            if f.lower().endswith(('png','jpg','gif')):
                imagefile = os.path.join(parentdir,f)
        child_item = sb.upload_file_to_item(child_item, imagefile)
    # Modify child page to match certain fields from parent
    if "inheritedfields" in locals():
        child_item = inherit_SBfields(sb, child_item, inheritedfields)
    return child_item # Return new JSON

def update_datapage(sb, page, xml_file, inheritedfields=False, replace=True, verbose=True):
    #FIXME This is not currently being used. Why not?
    # In its current form, there's no reason to get parent_item
    parent_item = flexibly_get_item(sb, page)
    if replace:
        item = sb.replace_file(xml_file,item) # replace_file() does not work well
    if inheritedfields:
        parent_item = sb.get_item(item['parentId'])
        item = inherit_SBfields(sb, item, inheritedfields, verbose=verbose)
    return item # Return new JSON

# def update_subpages_from_landing(sb, parentdir, subparent_inherits, dict_DIRtoID, dict_IDtoJSON):
#     # Find sub-parent container pages following directory hierarchy and copy-paste fields from landing page
#     for (root, dirs, files) in os.walk(parentdir):
#         for d in dirs:
#             sb = log_in(useremail)
#             reldirpath = os.path.join(os.path.relpath(root, os.path.dirname(parentdir)), d)
#             subpage = sb.get_item(dict_DIRtoID[reldirpath])
#             subpage = inherit_SBfields(sb, subpage, subparent_inherits)
#             dict_IDtoJSON[subpage['id']] = subpage
#     return dict_IDtoJSON

def update_pages_from_XML_and_landing(sb, dict_DIRtoID, data_inherits, subparent_inherits, dict_PARtoCHILDS):
    # Populate data pages
    for xmlpath, pageid in dict_DIRtoID.items():
        if xmlpath.endswith('xml'): # If dict key is XML file
            item = update_datapage(sb, pageid, xmlpath, inheritedfields=data_inherits, replace=True)
        else: # If it's not an XML file, then it must be a directory
            item = sb.get_item(dict_DIRtoID[xmlpath])
            pageid = item['id']
            parentid = item['parentId']
            item = inherit_SBfields(sb, item, subparent_inherits)
    #%% BOUNDING BOX
    bb_dict = set_parent_boundingBoxes(sb, dict_PARtoCHILDS)
    # Preview Images
    upload_all_previewImages(sb, parentdir, dict_DIRtoID)
    return

def remove_all_files(sb, pageid, verbose=False):
    # Remove all files (and facets) from child page
    item = flexibly_get_item(sb, pageid)
    item['files'] = []
    item['facets'] = []
    item=sb.update_item(item)
    if verbose:
        print('REMOVED: any files or facets on page "{}".'.format(item['title']))
    return item

def update_existing_fields(sb, parentdir, data_inherits, subparent_inherits, fname_dir2id='dir_to_id.json', fname_id2json='id_to_json.json', fname_par2childs='parentID_to_childrenIDs.txt'):
    # Populate pages if SB page structure already exists.
    # read data
    # NOT USED 12/10/18
    with open(fname_dir2id, 'r') as f:
        dict_DIRtoID = json.load(f)
    with open(fname_id2json, 'r') as f:
        dict_PARtoCHILDS = json.load(f)
        # Update SB fields
    update_pages_from_XML_and_landing(sb, dict_DIRtoID, data_inherits, subparent_inherits, dict_PARtoCHILDS)
    print("Fields updated and values items stored in dictionary: {}".format(fname_id2json))
    return True

def get_pageid_from_xmlpath(xml_file, sb=None, dict_DIRtoID=None, valid_ids=None, parentid=None, parentdir=None, verbose=False):
    # Flexibly get page_id based on XML file, either from the directory:ID dict, the SB title, or the SB citation in the XML file.
    page_id = None # Initialize page_id as None
    # First try: try the directory:ID dictionary if provided
    if dict_DIRtoID and not page_id:
        if xml_file in dict_DIRtoID:
            page_id = dict_DIRtoID[xml_file]
        elif parentdir:
            relpath = os.path.relpath(os.path.dirname(xml_file), os.path.dirname(parentdir))
            if relpath in dict_DIRtoID:
                page_id = dict_DIRtoID[relpath]
    # Next try: if we have an SB session look for SB page matching the folder name
    if not page_id and sb:
        title = os.path.basename(os.path.dirname(xml_file))
        matching_items = sb.find_items_by_title(title)['items']
        if matching_items:
            page_id = matching_items[0]['id']
            if verbose:
                print("Found page ID by searching SB for XML title. Result: {}: {}".format(page_id, title))
        else:
            print("get_pageid_from_xmlpath: Couldn't find page matching title {}".format(title))
            # TODO: search for matching XML?
    # Next try: get the second URL in the XML citeinfo, which should always be the SB page
    if not page_id:
        metadata_root, tree, xml_file = get_root_flexibly(xml_file)
        link_elems = metadata_root.findall('./idinfo/citation/citeinfo/onlink')
        if len(link_elems) > 1:
            page_url = link_elems[1].text
            page_id = os.path.basename(page_url)
            if verbose:
                print("Extracted page ID from the XML file. Result: {}: {}".format(page_id, title))
    if not page_id:
        print("Could not find page matching XML file. Possible causes: a folder name or page URL may have changed.")
        return(page_id)
    # Check the page_id against the IDs descended from page matching parentdir.
    if not parentid and dict_DIRtoID and parentdir:
        # Get the parentid from the directory:ID dictionary
        if os.path.basename(parentdir) in dict_DIRtoID:
            parentid = dict_DIRtoID[os.path.basename(parentdir)]
    if sb and parentid and not valid_ids:
        # List IDs descended from the parentdir
        valid_ids = sb.get_ancestor_ids(parentid)
        if verbose:
            print("...got list of IDs descended from {}.".format(parentid))
    if valid_ids:
        if not page_id in valid_ids:
            print('ALERT: ID ({}) is not in valid ID list. -- get_pageid_from_xmlpath()'.format(page_id))
    else:
        print('WARNING: No list of valid IDs so ID {} could not be cross-checked.'.format(page_id))
    return(page_id)

###################################################
#
# Apply functions to entire data release page tree
#
###################################################
def delete_all_children(sb, parentid, verbose=False):
    # Recursively delete all SB items that are descendants of the input page.
    # Waits up to 5 seconds for the child items to be deleted.
    exit_message = "Not sure if the process completed..."
    cids = sb.get_child_ids(parentid)
    for cid in cids:
        try:
            delete_all_children(sb, cid)
        except Exception as e:
            print("EXCEPTION: {}".format(e))
    sb.delete_items(cids)
    ptitle = sb.get_item(parentid)['title']
    # Wait up to 5 seconds for the child items to be deleted
    start = datetime.now()
    duration = 0
    while duration < 6:
        duration = (datetime.now() - start).seconds
        if len(sb.get_child_ids(parentid)) < 1:
            exit_message = "DELETED: all child items from parent page '{}.'".format(ptitle)
            break
    return(exit_message)

def remove_all_child_pages(useremail=False, landing_link=False):
    # Stand-alone function to wipe page tree;
    # Calls delete_all_children()
    if not useremail:
        useremail = input("SB username (should be entire USGS email): ")
    if not landing_link:
        landing_link = input("Landing page URL: ")
    landing_id = os.path.basename(landing_link)
    sb = log_in(useremail)
    delete_all_children(sb, landing_id)
    return landing_id

def landing_page_from_parentdir(parentdir, parent_xml, previewImage, new_values):
    for f in os.listdir(parentdir):
        if f.lower().endswith('xml'):
            parent_xml = os.path.join(parentdir,f) # metadata file in landing directory = parent_xml
    #%% Populate landing page from metadata
    if "parent_xml" in locals():
        # Update XML file to include new parent ID and DOI
        parent_xml = update_xml(parent_xml, new_values)
        landing_item = new_values['landing_item']
        try: # upload XML to landing page
            landing_item = sb.upload_file_to_item(landing_item, parent_xml)
        except Exception as e:
            print(e)
        if 'body' not in landing_item.keys():
            try: # update SB landing page with specific fields from XML
                landing_item = get_fields_from_xml(sb, landing_item, parent_xml, landing_fields_from_xml)
                landing_item=sb.update_item(landing_item)
            except Exception as e:
                print(e)
    if imagefile:
        try: # Add preview image to landing page
            landing_item = sb.upload_file_to_item(landing_item, imagefile)
        except Exception as e:
            print("Exception while trying to upload file {}: {}".format(imagefile, e))
    return landing_item, imagefile

def check_fields(sb, item, qcfields, verbose=False):
    cnt = 0
    for field in qcfields:
        if not field in item.keys():
            cnt += 1
            print("MISSING: field '{}' in page '{}'.".format(field, item['title']))
    if not cnt:
        if verbose:
            print("Page '{}' has all desired fields.".format(item['title']))
        return
    else:
        return item['id']

def check_fields2(sb, item, qcfieldsdict, verbose=False):
    # Checks for fields in page as specified by qcfieldsdict
    page = item['title']
    print("\nEvaluating '{}'".format(page))
    for f, num in qcfieldsdict.items():
        if not num:
            if f in item.keys(): # field should not be present
                print("PRESENT: field '{}'".format(f))
            else:
                if verbose:
                    print("...good! field '{}' not in page '{}'.".format(f, page))
        else: # field should be present
            if not f in item.keys():
                print("MISSING: field '{}'".format(f, ))
            elif not num == len(item[f]):
                print("NOT QUITE: field '{}' has {} entries.".format(f, len(item[f])))
            else:
                if verbose:
                    print("'{}' looks good.".format(page))
                return
    else:
        return item['id']

def check_fields3(sb, item, qcfields, verbose=False):
    page = item['title']
    print("\nEvaluating '{}'".format(page))
    error = 0
    for f in qcfields:
        if not f in item.keys():
            error += 1
            print("{}: 0".format(f, page))
        else:
            print("{}: {}".format(f, len(item[f])))
    return item['id']

def check_fields2_topdown(sb, top_id, qcfields, deficient_pages=[], verbose=False):
    # Given an SB ID, pass on selected fields to all descendants; doesn't look for parents
    for cid in sb.get_child_ids(top_id):
        citem = sb.get_item(cid)
        deficient = check_fields2(sb, citem, qcfields, verbose)
        deficient_pages.append(deficient)
        try:
            deficient_pages = check_fields2_topdown(sb, cid, qcfields, deficient_pages, verbose)
        except Exception as e:
            print("EXCEPTION: {}".format(e))
    return deficient_pages

def inherit_topdown(sb, top_id, parent_inherits, child_inherits, verbose=False):
    # Given an SB ID, pass on selected fields to all descendants
    item = sb.get_item(top_id)
    for cid in sb.get_child_ids(top_id):
        citem = sb.get_item(cid)
        # Pass on fields to the next generation
        if not citem['hasChildren']: # child_inherits fields to youngest generation
            inherit_SBfields(sb, citem, child_inherits, verbose)
        else: # parent_inherits fields to all pages
            inherit_SBfields(sb, citem, parent_inherits, verbose)
        # Move to the next generation
        try:
            inherit_topdown(sb, cid, parent_inherits, child_inherits, verbose)
        except Exception as e:
            print("EXCEPTION: {}".format(e))
    return True

def apply_topdown(sb, top_id, function, verbose=False):
    # Given an SB ID, do function to all descendants; doesn't look for parents
    #FIXME: does it work to simply use function name as argument?
    for cid in sb.get_child_ids(top_id):
        citem = sb.get_item(cid)
        if verbose:
            print('Applying {} to page "{}"'.format(function, citem['title']))
        function(sb, citem)
        try:
            apply_topdown(sb, cid, function)
        except Exception as e:
            print("EXCEPTION: {}".format(e))
    return True

def apply_bottomup(sb, top_id, function, verbose=False):
    # Given an SB ID, do function to all ancestors; doesn't look for children
    #FIXME: does it work to simply use function name as argument?
    for cid in sb.get_child_ids(top_id):
        try:
            apply_bottomup(sb, cid, function, verbose)
        except Exception as e:
            print("EXCEPTION: {}".format(e))
        citem = sb.get_item(cid)
        if verbose:
            print('Applying {} to page "{}"'.format(function, citem['title']))
        function(sb, citem)
    return True

def restore_original_xmls(parentdir):
    # List XML files
    xmllist = glob.glob(os.path.join(parentdir, '**/*.xml'), recursive=True)
    ct = 0
    for xml_file in xmllist:
        # Copy the file with the _orig suffix to the original filename.
        if os.path.exists(xml_file+'_orig'):
            shutil.copy(xml_file+'_orig', xml_file)
            ct += 1
    print("Restored {} original XML files.".format(ct))
    return
