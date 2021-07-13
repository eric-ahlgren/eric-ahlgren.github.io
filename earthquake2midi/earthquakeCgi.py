#!/usr/bin/python

# Import modules for CGI handling 
import cgi, cgitb
import subprocess

# Create instance of FieldStorage 
form = cgi.FieldStorage() 

# Get data from fields
days = form.getvalue('days')
key = form.getvalue('key')
tempo = form.getvalue('tempo')
min_magnitude = form.getvalue('min_magnitude')
base_octave = form.getvalue('base_octave')
octave_range = form.getvalue('octave_range')
save_file = form.getvalue('save_file')
patch_list = form.getvalue('patch_list')

subprocess.call(['python', '/Users/ericahlgren/Desktop/scripts/earthquake2Midi.py', '-d', days, '-k', key, '-m',\
					 min_magnitude, '-t', tempo, '-o', save_file, '-b', base_octave, '-r', octave_range, '-p', patch_list])

