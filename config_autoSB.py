# -*- coding: utf-8 -*-
"""
config_autoSB.py

By: Emily Sturdivant, esturdivant@usgs.gov
Last modified: 1/10/17

OVERVIEW: Configuration file for sb_automation.py
REQUIRES: autoSB.py, pysb, lxml
"""
#%% Import packages
import sciencebasepy as pysb
import os
import glob
from lxml import etree
import json
import pickle
import sys
sys.path.append(os.path.dirname(os.path.realpath(__file__))) # Add the script location to the system path just to make sure this works.
from autoSB import *
import getpass

"""
Input variables
"""
#-----------------------
#   REQUIRED
#-----------------------
# SB username (should be entire USGS email):
useremail = 'zdefne@usgs.gov'
# SB password. If commented out, you will be prompted for your password each time you run the script.
password = ""
with open('key.txt', 'r') as kfile:
    password=kfile.read()
    
# URL of data release landing page (e.g. 'https://www.sciencebase.gov/catalog/item/__item_ID__'):
# landing_link = "https://www.sciencebase.gov/catalog/item/5a54fbc3e4b01e7be242b917" # testing page
# landing_link = "https://www.sciencebase.gov/catalog/item/5d5ece47e4b01d82ce961e36" # Deep Dive volume II
landing_link = "https://www.sciencebase.gov/catalog/item/5f5aa37082cefd9f20868a9c" #VEG
landing_link = "https://www.sciencebase.gov/catalog/item/5f28109582cef313ed9cd787" #UVVR

# Path to local top-level directory of data release (equivalent to landing page):
# OSX: If this is a server mounted and visible in your Volumes: r'/Volumes/[directory on server]'
# parentdir = r'/Volumes/stor/Projects/DeepDive/5_datarelease_packages/vol2/release_v4_forSB' # OSX format
# parentdir = r"D:\DeepDive\5_datarelease_packages\vol1\sb_upload_test" # WINDOWS format
parentdir = r'E:/GIS/Landsat_UVVR\METADATA\VEG' 
parentdir = r'E:/GIS/Landsat_UVVR\METADATA\UVVR' 

# DOI of data release (e.g. '10.5066/F78P5XNK'):
# dr_doi = "10.5066/P9V7F6UX" # DOI for Deep Dive volume I
dr_doi = "10.5066/[[DOInumber]]"

# Year of publication, if it needs to updated. Used as the date in citation publication date and the calendar date in time period of content.
pubdate = '2020'

# The edition element in the metadata can be modified here.
#edition = '1.0'

# Image file (with path) to be used as preview image. If commented out, the preview image will be ignored.
# File name of browse graphic; assumes that it is within parentdir
# previewImage = 'bb20160318_parentpage_browse.png'
# previewImage = os.path.join(parentdir, previewImage)

#-------------------------------------------------------------------------------
#   OPTIONAL - ScienceBase page inheritance
#-------------------------------------------------------------------------------
# SB fields that will be copied (inherited) from landing page to sub-pages (subparents), which are different from data pages.
# Recommended: citation, contacts, body (='abstract' in XML; 'summary' in SB), purpose, webLinks
# body =
# relatedItems = Associated items
subparent_inherits = ['citation', 'contacts', 'body', 'webLinks', 'relatedItems'] #'purpose',
subparent_inherits = [] #'purpose',

# SB fields that data pages inherit from their parent page. All other fields will be automatically populated from the XML.
# Recommended: citation, body, webLinks
data_inherits = ['citation', 'contacts', 'body', 'webLinks', 'relatedItems']
data_inherits = []

# SB fields that will be populated from the XML file in the top directory, assuming an error-free XML is present.
# Note that body = abstract. The Summary item on SB will automatically be created from body.
# Default: [].
landing_fields_from_xml = []

# qcfields_dict = {'contacts':3, 'webLinks':0, 'facets':1} # Comment out to keep it simple and save time
# qcfields_dict = {'contacts':9, 'webLinks':3, 'facets':1}
#-------------------------------------------------------------------------------
# Time-saving options
#-------------------------------------------------------------------------------
# Default True:
update_subpages     = True # False to save time if page structure is already established.
delete_all_subpages = False # True to delete all child pages before running. Not necessary.
update_XML          = False # False to save time if XML already has most up-to-date values.
update_data         = True # False to save time if up-to-date data files have already been uploaded.
update_extent       = False
verbose             = True
# page_per_filename   = False

max_MBsize = 2000 # 2000 mb is the suggested threshold above which to use the large file uploader.
start_xml_idx = 0 # 0 to perform for all XMLs. This is included in case a process does not complete. '25' to start upload at file 26.

# Default False:
add_preview_image_to_all = False # True to put first image file encountered in a directory on its corresponding page
restore_original_xml     = False # True to restore original files saved on the first run of the code. Not necessary.
remove_original_xml      = False  # True to remove original files saved on the first run of the code.
# ------------------------------------------------------------------------------
#   OPTIONAL - XML changes
# ------------------------------------------------------------------------------
# To change the "Suggested citation" in the Other Citation Information, choose one of two options: either use the find_and_replace variable or the new_othercit variable, see below.

# FIND AND REPLACE. {key='desired value': value=['list of','values','to replace']}
# find_and_replace = {'**dr_doi**': dr_doi,
#     'xxx-ofr doi-***': '10.3133/ofr20191071',
#     # 'http:': 'https:',
#     'dx.doi.org': 'doi.org'
#     }

# REMOVE ELEMENT. If an element needs to be removed, this will occur before additions or replacements
# remove_fills = {'./idinfo/crossref':['AUTHOR', 'doi.org/10.3133/ofr20171015']}

# APPEND ELEMENT.
# Add {container: new XML element} item to metadata_additions dictionary for each element to be appended to the container element. Appending will not remove any elements.
# Example of a new cross reference:
# new_crossref = """
#     <crossref><citeinfo>
#         <origin>E.A. Himmelstoss</origin>
#         <origin>Meredith Kratzmann</origin>
#         <origin>E. Robert Thieler</origin>
#         <pubdate>2017</pubdate>
#         <title>National Assessment of Shoreline Change: Summary Statistics for Updated Vector Shorelines and Associated Shoreline Change Data for the Gulf of Mexico and Southeast Atlantic Coasts</title>
#         <serinfo><sername>Open-File Report</sername><issue>2017-1015</issue></serinfo>
#         <pubinfo>
#         <pubplace>Reston, VA</pubplace>
#         <publish>U.S. Geological Survey</publish>
#         </pubinfo>
#         <onlink>https://doi.org/10.3133/ofr20171015</onlink>
#     </citeinfo></crossref>
#     """
# metadata_additions = {'./idinfo':new_crossref}

# REPLACE ELEMENT. Replace suggested citation:
# new_othercit = """<othercit>
#                 Suggested citation: Lastname, F.M., {}, Title: U.S. Geological Survey data release, https://doi.org/{}.
#                 </othercit>""".format(pubdate, dr_doi)
# metadata_replacements = {'./idinfo/citation/citeinfo':new_othercit}

# Example of new distribution information:
# sb_distrib = """
#     <distrib>
# 		<cntinfo>
#             <cntorgp>
# 				<cntorg>U.S. Geological Survey - ScienceBase</cntorg>
# 			</cntorgp>
# 			<cntaddr>
# 				<addrtype>mailing and physical address</addrtype>
# 				<address>Denver Federal Center</address>
#                 <address>Building 810</address>
#                 <address>Mail Stop 302</address>
# 				<city>Denver</city>
# 				<state>CO</state>
# 				<postal>80225</postal>
# 				<country>USA</country>
# 			</cntaddr>
# 			<cntvoice>1-888-275-8747</cntvoice>
#             <cntemail>sciencebase@usgs.gov</cntemail>
# 		</cntinfo>
# 	</distrib>
#     """
# metadata_replacements = {'./distinfo':sb_distrib}

"""
Initialize
"""
#%% Initialize SB session
# password = getpass.getpass("ScienceBase password: ")
sb = log_in(useremail, password)

stash_dir = os.path.join(parentdir, '.assistants')

#%% Find landing page
if not "landing_id" in locals():
    try:
        landing_id = os.path.split(landing_link)[1] # get ID for parent page from link
    except:
        print("""Either the ID (landing_id) or the URL (landing_link) of the
            ScienceBase landing page must be specified in config_autoSB.py.""")
