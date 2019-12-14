# Function for downloading the latest database version from WSC


import os
import requests
import re
import wget
import zipfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# first, check if a database folder already exists

def check_for_db_directory():
    """
    Check if the a database directory named /hydat_db exists.
    If not, create the db and 
    """

    db_directory = BASE_DIR + '/hydat_db'
    directories = [d[0] for d in os.walk(BASE_DIR) if d[0] == db_directory]

    if len(directories) != 0:
        # directory exists, check for the database file
        # and check the version against the newest file
        print('DB directory exists, check version.')
        return True
    else:
        # directory doesn't exist, create it
        print('Creating directory {}'.format(db_directory))
        os.mkdir(db_directory)
        return False
    

def get_filenames(url):
    """
    The location where the hydat database has the sqlite database
    file itself, as well as supporting documentation.
    This function returns the filenames of the documentation pdfs
    in both languages, as well as the database filename.
    Input the url for the file location at Environment Canada.
        -should be https://collaboration.cmc.ec.gc.ca/cmc/hydrometrics/www/
    Returns two separate variables:
        -the first is a list of the pdf filenames
        -the second is the database filename.
    """

    s = requests.get(url).text

    all_hrefs = [s.start() for s in re.finditer('a href=', s)]
    
    pdf_files = []
    db_filename = None
    for l in all_hrefs:

        # skip past the positions corresponding to 'a href='
        start = l + 8
        
        # get the non-DB readme files
        file_prefix = s[start:start + 10]
        
        if file_prefix in ['ECDataExpl', 'HYDAT_Defi', 'HYDAT_Rele']:
            end = s[start:].find('.pdf') + len('.pdf')

            # extract just the filename
            filename = s[start:start + end]
            # append to the list of filenames
            pdf_files.append(filename)
        if file_prefix == 'Hydat_sqli':
            end = s[start:].find('.zip') + len('.zip')
            db_filename = s[start: start + end]

    if db_filename == None:
        raise AssertionError('No database file was found.  Check https://collaboration.cmc.ec.gc.ca/cmc/hydrometrics/www/ to see if the page is up, and if a .zip file corresponding to the sqlite Hydat database file exists')
    return pdf_files, db_filename


def download_and_extract_db_file(dbf, url):
    """
    Input the filename extracted from Environment Canada website.
    Write and unzip the file in the db folder,
    """
    db_dir = BASE_DIR + '/hydat_db'

    file_version =  dbf.split('_')[-1].split('.')[0]
    txt = input("Download and extract the database file? \nNote: the file is roughly 280MB.  Please respond [y/n]")
    if txt == 'y':
        print('Downloading and saving documentation files to {}'.format(BASE_DIR + '/hydat_db'))
        try:
            print('Downloading file.')
            wget.download(url + '/' + dbf, db_dir)
            print('')
            print('Download complete.  Extracting...')
            z = zipfile.ZipFile(db_dir + '/' + dbf, 'r')
            for i, f in enumerate(z.filelist):
                f.filename = 'Hydat_{}.sqlite3'.format(file_version)
                
                z.extract(f, db_dir)
            print('File extracted.')
            return True
        except Exception as e:
            print('Error downloading and extracting the database file.')
            print(e)
            return False
    elif txt == 'n':
        print('Download cancelled.')
        return False
    else:
        print('Please type y for yes or n for no.')
        download_and_extract_db_file(dbf, url)
    

def download_and_save_info_docs(files, url):
    """
    Input the filenames extracted from Environment Canada website.
    Write the pdf files to the db folder.
    """
    txt = input("Download and extract the documentation?  Please respond [y/n]")
    if txt == 'y':
        print('Downloading and saving documentation files to {}'.format(BASE_DIR + '/hydat_db'))
        try:
            [wget.download(url + '/' + f, BASE_DIR + '/hydat_db') for f in files]
        except Exception as e:
            print('Error downloading documentation files.')
            print(e)
    elif txt == 'n':
        print('Download cancelled.')
    else:
        print('Please type y for yes or n for no.')
        download_and_save_info_docs(files, url) 


def check_for_updated_zip_file(url, hydat_file, existing_file, db_fname):
    """
    A zipped db file exists.  Check the date against the latest version.
    Download and extract if newer version is available.
    """

    print('{} existing database file(s) found:'.format(len(hydat_file)))
    for ef in hydat_file: 
        print('    {}'.format(ef))
    existing_file_version = existing_file.split('_')[-1].split('.')[0]
    latest_file_version = db_fname.split('_')[-1].split('.')[0]
    if int(existing_file_version) < int(latest_file_version):
        print('Your database file version is dated {}.'.format(existing_file_version))
        print('A newer version is available, dated {}.'.format(latest_file_version))
        return download_and_extract_db_file(db_fname, url)
    else:
        print('You have the latest file version.')
        return True
        

def check_for_updated_sql_file(url, hydat_file, existing_file, db_fname):
    """
    A sqlite3 db file exists.  Check the date against the latest version.
    Download and extract if newer version is available.
    """

    print('{} existing database file(s) found:'.format(len(hydat_file)))
    if existing_file == 'Hydat.sqlite3':
        return download_and_extract_db_file(db_fname, url)
    else:
        existing_file_version = existing_file.split('.')[0].split('_')[-1]
        latest_file_version = db_fname.split('_')[-1].split('.')[0]
        if int(existing_file_version) < int(latest_file_version):
            print('Your database file version is dated {}.'.format(existing_file_version))
            print('A newer version is available, dated {}.'.format(latest_file_version))
            return download_and_extract_db_file(db_fname, url)
        else:
            print('You have the latest file version.')
            return True
            

url = 'https://collaboration.cmc.ec.gc.ca/cmc/hydrometrics/www/'

pdf_filenames, db_fname = get_filenames(url)

check_db_directory = check_for_db_directory()

if len(pdf_filenames) < 2:
    # download the documentation for the hydat database
    download_and_save_info_docs(pdf_filenames, url)

if check_db_directory is False:
    # if the database directory didn't already exist, download 
    # all the info documents and the db file and extract to the db folder
    # otherwise check the version to see if a newer database file exists.
    download_and_save_info_docs(pdf_filenames, url)
    download_and_extract_db_file(db_fname, url)
else:
    all_files = os.listdir(BASE_DIR + '/hydat_db')
    hydat_zip_file = sorted([e for e in all_files if 'Hydat_sqlite3_' in e])
    hydat_sql_file = sorted([e for e in all_files if '.sqlite3' in e])

    print(hydat_zip_file)
    if len(hydat_sql_file) == 0 and len(hydat_zip_file) == 0:
        print('Hydat database file not found.  Downloading...')
        db_file_updated = download_and_extract_db_file(db_fname, url)
    if len(hydat_sql_file) != 0:
        latest_file = hydat_sql_file[-1]
        db_file_updated = check_for_updated_sql_file(url, hydat_sql_file, latest_file, db_fname)
    if len(hydat_zip_file) != 0 and len(hydat_sql_file) == 0:
        # don't download the zip if there was already an up-to-date sqlite3 file.
        latest_file = hydat_zip_file[-1]
        db_file_updated = check_for_updated_zip_file(url, hydat_zip_file, latest_file, db_fname)
    if db_file_updated == True:
        print('DB file successfully updated.')

