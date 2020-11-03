# -*- coding: utf-8 -*-
"""
testing.py

By: Emily Sturdivant, esturdivant@usgs.gov
Last modified: 1/10/17

OVERVIEW: Script creates child pages that mimic the directory structure and
populates the pages using a combination of fields from the landing page and the metadata.
Directories within home must be named as desired for each child page.
Currently, the script creates a new child page for each metadata file.

REQUIRES: pysb, lxml, config_autoSB.py, autoSB.py
To install pysb with pip: pip install -e git+https://my.usgs.gov/stash/scm/sbe/pysb.git#egg=pysb

ALTERNATIVE: only create child page from metadata if data files also exist...
...or if there are multiple metadata files in the directory.
"""
#%% Import packages
import sciencebasepy as pysb
import os
import glob
from lxml import etree
import json
import pickle
from datetime import datetime
import sys
import re
try:
    sb_auto_dir = os.path.dirname(os.path.realpath(__file__))
except:
    sb_auto_dir = os.path.dirname(os.path.realpath('sb_automation.py'))
    sb_auto_dir = r'/Users/esturdivant/GitHub/science-base-automation'
sys.path.append(sb_auto_dir) # Add the script location to the system path just to make sure this works.
from autoSB import *
from config_autoSB import * # Input sciencebase password
import shutil


#%% Log into SB if it's timed out
sb = log_in(useremail, password)

#%%
print('Removing all .xml_orig files in {} tree.'.format(os.path.basename(parentdir)))
remove_files(parentdir, pattern='**/*.xml_orig')


#%% Backup the XMLs resulting from SB upload
today = datetime.now().strftime("%Y%m%d")
xmlstash = os.path.join(stash_dir, 'output_xmls_{}'.format(today))
os.makedirs((xmlstash), exist_ok=True)
xmllist = glob.glob(os.path.join(parentdir, '[!x]*/**/*.[xX][mM][lL]'))#, recursive=True)
for fp in xmllist:
    shutil.copy(fp, xmlstash)
shutil.make_archive(xmlstash, 'zip', xmlstash)



# from Tkinter import *
import getpass

useremail = 'esturdivant@usgs.gov'
password = getpass.getpass('ScienceBase password: ')

#%% Initialize SB session
sb = log_in(useremail, password)

# get JSON item for parent page
landing_item = sb.get_item(landing_id)
#print("CITATION: {}".format(landing_item['citation'])) # print to QC citation
# make dictionary of ID and URL values to update in XML
new_values = {'landing_id':landing_item['id'], 'doi':dr_doi}
if 'pubdate' in locals():
    new_values['pubdate'] = pubdate
if 'find_and_replace' in locals():
    new_values['find_and_replace'] = find_and_replace
if 'metadata_additions' in locals():
    new_values['metadata_additions'] = metadata_additions
if "metadata_replacements" in locals():
    new_values['metadata_replacements'] = metadata_replacements
if "remove_fills" in locals():
    new_values['remove_fills'] = remove_fills

#%% Work with landing page and XML
"""
Work with landing page and XML
"""
# Remove all child pages
if replace_subpages:
    if not update_subpages:
        print('WARNING: You chose not to update subpages, but also to replace them. Both are not possible so we will remove and create them.')
    print("Deleting all child pages of landing page...")
    print(delete_all_children(sb, landing_id))
    landing_item = remove_all_files(sb, landing_id, verbose=verbose)
    update_subpages = True


#%% Change folder name to match XML title
"""
Change folder name to match XML title
"""
rename_dirs_from_xmls(parentdir)

#%% Create SB page structure
"""
Create SB page structure: nested child pages following directory hierarchy
Inputs: parent directory, landing page ID
This one should overwrite the entire data release (excluding the landing page).
"""
# Check whether logged in.
if not sb.is_logged_in():
    print('Logging back in...')
    try:
        sb = pysb.SbSession(env=None).login(useremail,password)
    except NameError:
        sb = pysb.SbSession(env=None).loginc(useremail)

# If there's no id_to_json.json file available, we need to create the subpage structure.
if not update_subpages and not os.path.isfile(os.path.join(parentdir,'id_to_json.json')):
    print("id_to_json.json file is not in parent directory, so we will perform update_subpages routine.")
    update_subpages = True

if update_subpages:
    dict_DIRtoID = setup_subparents(sb, parentdir, landing_id, imagefile)
    # Save dictionaries
    with open(os.path.join(parentdir,'dir_to_id.json'), 'w') as f:
        json.dump(dict_DIRtoID, f)
else: # Import pre-created dictionaries if all SB pages exist
    with open(os.path.join(parentdir,'dir_to_id.json'), 'r') as f:
        dict_DIRtoID = json.load(f)

#%% After trying to delete and getting the pages all confused...
falsefolder_id = '5d013787e4b05cc71cad2520'
fix_falsefolder(sb, falsefolder_id, useremail, password)


#%% Check max size
# List all files in directory, except original xml and other bad apples
datadir = os.path.dirname(xml_file)
up_files = [os.path.join(datadir, fn) for fn in os.listdir(datadir)
            if not fn.endswith('_orig')
            and not fn.endswith('DS_Store')
            and not fn.endswith('.lock')
            and os.path.isfile(os.path.join(datadir, fn))]
bigfiles = []
for fn in up_files:
    print(os.path.basename(fn))

for fn in up_files:
    if os.path.getsize(fn) > max_MBsize*1000000: # convert megabytes to bytes
        bigfiles.append(os.path.basename(fn))
        up_files.remove(fn)
for fn in up_files:
    print([os.path.basename(fn), os.path.getsize(fn)/1000000])
print('\n'.join([os.path.basename(fn) for fn in up_files]))



#%% Perform upload_files for one data page, based on the XML file.
datadir = os.path.dirname(xml_file)
pageid = dict_DIRtoID[os.path.relpath(datadir, os.path.dirname(parentdir))]
data_title = get_title_from_data(xml_file)
if [len(glob.glob(os.path.join(datadir, '**/*.xml'), recursive=True)) == 1
    and not [fn for fn in os.listdir(datadir) if os.path.isdir(os.path.join(datadir,fn))]]:
    # Change subparent title to data title
    data_item = flexibly_get_item(sb, pageid)
    orig_title = data_item['title']
    data_item['title'] = data_title
    data_item = sb.update_item(data_item)
    print("RENAMED: page '{}' in place of '{}'".format(trunc(data_title), orig_title))
# Or create/find a new page to match the XML file
else:
    # Create (or find) data page based on title
    data_item = find_or_create_child(sb, pageid, data_title, verbose=verbose)
landing_item = sb.get_item(landing_id)
new_values = {'landing_id':landing_item['id'], 'doi':dr_doi}
if 'pubdate' in locals():
    new_values['pubdate'] = pubdate
try:
    # If pubdate in new_values, set it as the date for the SB page
    data_item["dates"][0]["dateString"]= new_values['pubdate'] #FIXME add this to a function in a more generalized way?
except:
    pass
data_item, bigfiles1 = upload_files(sb, data_item, xml_file, max_MBsize=max_MBsize, replace=True, verbose=verbose)
dict_DIRtoID[xml_file] = data_item['id']
# started: 3:37
# completed:


#%% For each XML file in each directory upload the data to the correct page
# Upload data to ScienceBase
if update_data:...

def upload_data_in_XMLdirs(parentdir, start_xml_idx=0):
    if verbose:
        print('\n---\nWalking through XML files to upload the data...')
    cnt = 0
    xmllist = glob.glob(os.path.join(parentdir, '**/*.xml'), recursive=True)
    xmllist = xmllist[start_xml_idx:]
    for xml_file in xmllist:
        cnt += 1
        print("File {}: {}".format(cnt + start_xml_idx, xml_file))
        # Get SB page ID from the XML
        datapageid = get_pageid_from_xmlpath(xml_file, sb=sb, dict_DIRtoID=dict_DIRtoID, valid_ids=valid_ids, parentdir=parentdir)
        # Log into SB if it's timed out
        sb = log_in(useremail, password)
        data_item = sb.get_item(datapageid)
        # Update publication date in item
        try:
            # If pubdate in new_values, set it as the date for the SB page
            data_item["dates"][0]["dateString"]= new_values['pubdate']
            #FIXME add this to a function in a more generalized way?
        except:
            pass
        # Upload all files in directory to the SB page
        data_item, bigfiles1 = upload_files(sb, data_item, xml_file, max_MBsize=max_MBsize, replace=True, verbose=verbose)
        # Record files that were not uploaded because they were above the max_MBsize threshold
        if bigfiles1:
            if not 'bigfiles' in locals():
                bigfiles = []
            bigfiles += bigfiles1
        # Log in to SB if it's timed out
        sb = log_in(useremail, password)
        # Upload XML to ScienceBase
        elif update_XML:
            # If XML was updated, but data was not uploaded, replace only XML.
            data_item = upsert_metadata(sb, data_item, xml_file)
        if 'previewImage' in data_inherits and "imagefile" in locals():
            data_item = sb.upload_file_to_item(data_item, imagefile)
        if verbose:
            now_str = datetime.now().strftime("%H:%M:%S on %Y-%m-%d")
            print('Completed {} out of {} total xml files at {}.\n'.format(cnt, len(xmllist), now_str))
        # store values in dictionaries
        dict_DIRtoID[xml_file] = data_item['id']



#%% 6/20/19
# For every file in the directory, check whether an older version exists in the SB page. Replace the file if the current version is not there.
datadir
filelist = os.listdir(datadir)

# Upload XMLs that have been updated since last upload to SB.
ct = 0
xmllist = glob.glob(os.path.join(parentdir, '**/*.xml'), recursive=True)
print("Searching {} XML files for changes since last upload...".format(len(xmllist)))
for xml_file in xmllist:
    # Get SB JSON item for page
    datapageid = get_pageid_from_xmlpath(xml_file, valid_ids=valid_ids)
    data_item = flexibly_get_item(sb, datapageid, output='item')
    # Get upload time of XML as UTC datetime object
    xml_uploaded = get_file_upload_time(data_item, file_type='application/fgdc+xml')
    xml_uploaded = datetime.strptime(xml_uploaded, '%Y-%m-%dT%H:%M:%SZ')
    # Get modified time of local XML as UTC datetime
    xml_modified = datetime.utcfromtimestamp(os.path.getmtime(xml_file))
    if xml_modified > xml_uploaded:
        # Replace the metadata file
        data_item = upsert_metadata(sb, data_item, xml_file)
        # print('UPLOADED: {}'.format(os.path.basename(xml_file)))
        ct += 1
print("Found and uploaded {} XML files.\n".format(ct))
    return


#%% 6/18/19
# Update SB preview image from the uploaded files.
update_all_browse_graphics(parentdir, landing_id, useremail, password)

datapageid = '5d016c77e4b05cc71cad2c2a'
sb = log_in(useremail, password)
data_item = sb.get_item(datapageid)
t_uploaded = get_xml_upload_time(data_item)

for file in data_item['files']:
    print(file['contentType'])
    print(file['dateUploaded'])
    print(file['originalMetadata'])
for idx, facet in enumerate(data_item['facets']):
    for file in facet['files']:
        print(file['contentType'])
        print(file['dateUploaded'])
        print(file['originalMetadata'])

for file in data_item['files']:
    print(file['contentType'])
    ftype = file['contentType']

for k in data_item['files'][0].keys():
    print(k)

#%% 6/20/19
# Remove ipynb mention from shoreline xmls in completed directory tree
import io

parentdir
xmllist = glob.glob(os.path.join(parentdir, '**/*.xml'), recursive=True)

fstr = ' as well as the iPython notebook \(.*\.ipynb\) used for processing\.'
rstr = '.'
fstr = 'Gutierrez, B\.T\., and Weber, K\.M\. 201[89]'
rstr = 'Gutierrez, B.T., and Weber, K.M., 2019'
for xml_file in xmllist:
    replace_in_file(xml_file, fstr, rstr, fill='xxx')

sb = log_in(useremail, password)
valid_ids = sb.get_ancestor_ids(landing_id)
upload_all_updated_xmls(sb, parentdir, valid_ids=valid_ids)

#%% Pass down fields from parents to children
print("\n---\nPassing down fields from parents to children...")
subparent_inherits = ['webLinks']#['citation', 'contacts', 'body', 'webLinks', 'relatedItems', 'purpose']
data_inherits = ['webLinks']#['citation', 'contacts', 'body', 'webLinks', 'relatedItems']
inherit_topdown(sb, landing_id, subparent_inherits, data_inherits, verbose=verbose)



#%% Get page ID corresponding to xml file.
sb = log_in(useremail, password)
valid_ids = sb.get_ancestor_ids(landing_id)
page_id = get_pageid_from_xmlpath(xml_file, valid_ids=valid_ids)
page_id

#%% 6/21/2019
# Zip all XMLs for IPDS
import shutil

root_dir = r'/Users/esturdivant/Desktop/xmls_testzip'
archive_path = r'/Users/esturdivant/Desktop/xmls_testzip'
if not os.path.exists(root_dir):
    os.makedirs(root_dir)
xmllist = glob.glob(os.path.join(parentdir, '**/*.xml'), recursive=True)
for xml_file in xmllist:
    d = os.path.join(root_dir, os.path.basename(xml_file))
    shutil.copy2(xml_file, d)
shutil.make_archive(root_dir, 'zip', root_dir)


#%% Change find_and_replace so that keys are searchstr and values are replacestr
find_and_replace = {'https://doi.org/{}'.format(dr_doi): ['https://doi.org/10.5066/***'],
    'DOI:{}'.format(dr_doi): ['DOI:XXXXX'],
    'xxx': ['**ofrDOI**'],
    # 'E.R. Thieler': ['E. Robert Thieler', 'E. R. Thieler'],
    # 'https:': 'http:',
    'doi.org': 'dx.doi.org'
    }
fr2 = {'https://doi.org/10.5066/***':'https://doi.org/{}'.format(dr_doi),
    'DOI:XXXXX':'DOI:{}'.format(dr_doi),
    '**ofrDOI**':'xxx',
    # 'E.R. Thieler': ['E. Robert Thieler', 'E. R. Thieler'],
    # 'https:': 'http:',
    'dx.doi.org':'doi.org'
    }




datadir = os.path.dirname(xml_file)
sub_xmllist = glob.glob(os.path.join(datadir, '**/*.xml'), recursive=True)
innerdirs = [fn for fn in os.listdir(datadir) if os.path.isdir(os.path.join(datadir,fn))]
if len(sub_xmllist) == 1 and not innerdirs:
    print("One XML and no sub-directories...")

datadir = os.path.dirname(xml_file)
if [len(glob.glob(os.path.join(datadir, '**/*.xml'), recursive=True)) == 1
    and not [fn for fn in os.listdir(datadir) if os.path.isdir(os.path.join(datadir,fn))]]:
    print("One XML and no sub-directories...")
# convert the subparent into the data page

pageid = dict_DIRtoID[os.path.relpath(datadir, os.path.dirname(parentdir))]
# get subparent item that will become data page
data_item = flexibly_get_item(sb, pageid)



#%% Upload all XML files without updating them.
parentdir = r'/Volumes/ThunderVant/Projects/UAS_BlackBeach/Publishing/Data_publishing/data_release_revisedSept' # OSX Desktop
with open(os.path.join(parentdir,'dir_to_id.json'), 'r') as f:
    dict_DIRtoID = json.load(f)

replace_files_by_ext(sb, parentdir, dict_DIRtoID, match_str='*.xml') # only replaces the file if the file is already on the data page.

#%% Temp: upload images.zip
xml_file = '/Volumes/ThunderVant/Projects/UAS_BlackBeach/Publishing/Data_publishing/data_release_revisedSept/Field Data (images and reference points)/bb20160318_UAS_images_meta.xml'
d = 'Field Data (images and reference points)'

if not sb.is_logged_in():
    print('Logging back in...')
    try:
    sb = pysb.SbSession(env=None).login(useremail,password)
    except NameError:
    sb = pysb.SbSession(env=None).loginc(useremail)

with open(os.path.join(parentdir,'dir_to_id.json'), 'r') as f:
    dict_DIRtoID = json.load(f)

parentid = dict_DIRtoID[d]
# Create (or find) new data page based on title in XML
data_title = get_title_from_data(xml_file) # get title from XML
data_item = find_or_create_child(sb, parentid, data_title, verbose=verbose) # Create (or find) data page based on title
# Upload to ScienceBase
data_item, bigfiles1 = upload_files_matching_xml(sb, data_item, xml_file, max_MBsize=2000, replace=True, verbose=verbose)



#%% DEM

xml_file = '/Volumes/ThunderVant/Projects/UAS_BlackBeach/Publishing/Data_publishing/data_release_4upload_3/SfM products (point cloud, orthomosaic, and DEM)/bb20160318_sfm_dem_meta.xml'
d = 'SfM products (point cloud, orthomosaic, and DEM)'
parentid = dict_DIRtoID[d]
new_values['doi'] = dr_doi if 'dr_doi' in locals() else get_DOI_from_item(flexibly_get_item(sb, parentid))
# Create (or find) new data page based on title in XML
data_title = get_title_from_data(xml_file) # get title from XML
data_item = find_or_create_child(sb, parentid, data_title, verbose=verbose) # Create (or find) data page based on title
try: #FIXME: add this to a function in a more generalized way?
    data_item["dates"][0]["dateString"]= new_values['pubdate']
except:
    pass
# Upload to ScienceBase
data_item, bigfiles1 = upload_files_matching_xml(sb, data_item, xml_file, max_MBsize=2000, replace=True, verbose=verbose)

#%%QC
if quality_check_pages:
    qcfields_dict = {'contacts':4, 'webLinks':0, 'facets':1}
    print('Checking that each page has: \n{}'.format(qcfields_dict))
    pagelist = check_fields2_topdown(sb, landing_id, qcfields_dict, verbose=False)

landing_item = sb.get_item(landing_id)
child_item = sb.get_item(child_id)

# Revise the XML, except for the values created by SB
# Recursively list all XML files in parentdir
xmllist = []
for root, dirs, files in os.walk(parentdir):
    for d in dirs:
    xmllist += glob.glob(os.path.join(root,d,'*.xml'))

"""
Tkinter learning
"""
# Button widget with counter
counter = 0
def counter_label(label):
  def count():
    global counter
    counter += 1
    label.config(text=str(counter))
    label.after(1000, count)
  count()

root = Tk() # Tk root widget initializes Tkinter. Appears as window with title bar after calling root.mainloop()
root.title("Counting Seconds")
label = Label(root, fg="green")
label.pack()
counter_label(label)
button = Button(root, text='Stop', width=25, command=root.destroy)
button.pack()

# Entry widget
master = Tk()
Label(master, text="First Name").grid(row=0)
Label(master, text="Last Name").grid(row=1)

e1 = Entry(master)
e2 = Entry(master)

e1.grid(row=0, column=1)
e2.grid(row=1, column=1)

mainloop( )

string = 'string'
json = {'json':1, 'hi':2}
type(string)
type(json)

#%% 1/9/18
# Orig:
xmllist = []
for root, dirs, files in os.walk(parentdir):
    for d in dirs:
    xmllist += glob.glob(os.path.join(root, d, '*.xml'))
d
root

# Revise the XML, except for the values created by SB
# Recursively list all XML files in parentdir
parentdir = r'/Volumes/stor/Projects/iPlover/iPlover_DR_2016/test_dir4upload' # OSX format
xmllist = glob.glob(os.path.join(parentdir, '**/*.xml'), recursive=True)
xml_file = xmllist[0]
xml_file
os.path.basename(os.path.split(xml_file)[0])
searchstr = xml_file.split('.')[0].split('_meta')[0] + '*browse*'
searchstr
browse_file = glob.glob(searchstr)[0]
new_values['browse_file'] = browse_file.split('/')[-1]


# Using pathlib
from pathlib import Path
p = Path(parentdir)
xmllist = list(p.glob('**/*.xml'))
xmllist
xml_file = xmllist[0]
xml_file
xml_file.parts
xml_file.root
xml_file.parent
xml_file.parents[1]
xml_file.parent.stem
xml_file.stem
xml_file.name

# Search for browse
searchstr = xml_file.stem.split('_meta')[0] + '*browse*'
try:
    browse_file = sorted(xml_file.parent.glob(searchstr))[0]
except:
    print("Couldn't find file matching the pattern '{}' in directory {} to add as browse image.".format(searchstr, xml_file.parent.stem))

searchstr = dataname + '*browse*'
xml_file.parent / searchstr

browse_file = glob.glob(xml_file.parent / searchstr)[0]

new_values ={}
new_values['browse_file'] = browse_file.name
new_values



####
#%% 2/14/18 - Restructure function to be more intuitive: go through each section of FGDC metadata
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
    access_str = 'The first link is to the page containing the data, the second link downloads all data available from the page as a zip file, and the third link is to the publication landing page.'
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
now_str = datetime.datetime.now().strftime("%Y%m%d")
val2xml[now_str] = {metadate: 0}

return val2xml




# digital transfer information
networkr = './distinfo/stdorder/digform/digtopt/onlinopt/computer/networka/networkr' # Network Resource Name
accinstr = './distinfo/stdorder/digform/digtopt/onlinopt/accinstr'
i = 0
acc_inst = 'The URLs in the network address section provide the following, respectively: '
if 'child_id' in new_values.keys():
    # link to containing page
    page_url = 'https://www.sciencebase.gov/catalog/item/{}'.format(new_values['child_id']) # data_item['link']['url']
    i = i
    update_xml_tagtext(metadata_root, page_url, networkr, i)
    acc_inst += 'Link number {} is to the page containing the data. '.format(i+1)
    # direct download everything on page
    directdownload_link = 'https://www.sciencebase.gov/catalog/file/get/{}'.format(new_values['child_id'])
    i += 1
    update_xml_tagtext(metadata_root, directdownload_link, networkr, i)
    acc_inst += 'Link number {} downloads all data available from the page as a zip file. '.format(i+1)
# link DOI, landing page
doi_url = "https://doi.org/{}".format(new_values['doi'])
i += 1
update_xml_tagtext(metadata_root, doi_url, networkr, i)
acc_inst += 'Link number {} downloads all data available from the page as a zip file. '.format(i+1)
