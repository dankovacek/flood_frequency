
import os
import requests
import re
import wget
import zipfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

db_dir = BASE_DIR + '/' + 'hydat_db'

dbf = 'Hydat_sqlite3_20191016.zip'

file_version =  dbf.split('_')[-1].split('.')[0]


print('Extracting...')
z = zipfile.ZipFile(db_dir + '/' + dbf, 'r')
for i, f in enumerate(z.filelist):
    f.filename = 'Hydat_{}.sqlite3'.format(file_version)
    
    z.extract(f, db_dir)
