#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Generates a .mid MIDI file from recent earthquakes via USGS website API. Note values are scaled to earthquake magnitude,
depth in Earth's crust, distance from current location, and time from the present.

Input parameters are:
1) Number of days back from current day to collect data
2) Desired key in which to generate notes (i.e. BbMAJOR)
3) Minimum magnitude of earthquakes to include
4) Path to output .mid file
"""

import requests
import datetime
import argparse
from miditime.miditime import MIDITime
import sys
import os
import json
import geopy.distance
from jenks import jenks
from gooey import Gooey
import numpy

if getattr(sys, 'frozen', False):
	DATA_DIR = os.path.dirname(sys.executable)
else:
	DATA_DIR = os.path.dirname(os.path.realpath(__file__))

QUAKE_RAW = os.path.join(DATA_DIR,'quakes.csv')
QUAKE_PARSED = os.path.join(DATA_DIR,'parsed_quakes.csv')
SCALES = {
	'CHROMATIC': ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B'],
	'CMAJOR': ['C','D','E','F','G','A','B'],
	'AMINOR': ['A','B','C','D','E','F','G#'],
	'FMAJOR': ['F','G','A','Bb','C','D','E'],
	'DMINOR': ['D','E','F','G','A','Bb','C#'],
	'BbMAJOR': ['Bb','C','D','Eb','F','G','A'],
	'GMINOR': ['G','A','Bb','C','D','Eb','F#'],
	'EbMAJOR': ['Eb','F','G','Ab','Bb','C','D'],
	'CMINOR': ['C','D','Eb','F','G','Ab','B'],
	'AbMAJOR': ['Ab','Bb','C','Db','Eb','F','G'],
	'FMINOR': ['F','G','Ab','Bb','C','Db','E'],
	'DbMAJOR': ['Db','Eb','F','Gb','Ab','Bb','C'],
	'BbMINOR': ['Bb','C','Db','Eb','F','Gb','A'],
	'F#MAJOR': ['F#','G#','A#','B','C#','D#','F'],
	'EbMINOR': ['Eb','F','Gb','Ab','Bb','B','D'],
	'BMAJOR': ['B','C#','D#','E','F#','G#','A#'],
	'G#MINOR': ['G#','A#','B','C#','D#','E','G'],
	'EMAJOR': ['E','F#','G#','A','B','C#','D#'],
	'C#MINOR': ['C#','D#','E','F#','G#','A','C'],
	'AMAJOR': ['A','B','C#','D','E','F#','G#'],
	'F#MINOR': ['F#','G#','A','B','C#','D','F'],
	'DMAJOR': ['D','E','F#','G','A','B','C#'],
	'BMINOR': ['B','C#','D','E','F#','G','A#'],
	'GMAJOR': ['G','A','B','C','D','E','F#'],
	'EMINOR': ['E','F#','G','A','B','C','D#']
	}

@Gooey
def return_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-d','--days', help='Number of days back from current day to collect earthquake data', type=int, default=7)
    parser.add_argument('-k','--key', help='Key in which to generate notes (i.e. "EbMINOR")', choices=SCALES.keys(), type=str, default='CHROMATIC')
    parser.add_argument('-m','--minmag', help='Minimum magnitude of earthquake to include in note list.', default=2.5)
    parser.add_argument('-t','--tempo', help='Tempo in beats per minute.', default=120, type=int)
    parser.add_argument('-o','--outfile', help='Desired path to output .mid file. Default is .py script directory.', default=os.path.join(DATA_DIR,'quakes.mid'))
    parser.add_argument('-b','--base', help='Base octave for output (0 lowest to 10 highest).', default=3, type=int)
    parser.add_argument('-r','--range', help='Octave range for output (1 to 9, depending on base octave).', default=5, type=int)
    parser.add_argument('-p','--patches', help='List of desired patches (0-127) to be mapped to output based on magnitude (low to high).',\
    					 nargs='*', type=int)
    #default=['48', '58', '57', '71', '73'], type=str



    # if len(sys.argv) < 2:
    #     parser.print_help()
    #     exit(1)

    return parser.parse_args()

def getDateRange(days=7):
	#Return date range in year-mo-day
	numDays = datetime.timedelta(days=days)
	startTime = datetime.date.today()-numDays
	endTime = datetime.date.today()
	fStart = (str(startTime.year)+'-'+str(startTime.month)+'-'+str(startTime.day))
	fEnd = (str(endTime.year)+'-'+str(endTime.month)+'-'+str(endTime.day))
	return (fStart,fEnd)

def getRequest(dateRange, minMag=2.5):
	#Default end time is current time
	print ('Getting earthquake data...')
	r = requests.get('http://earthquake.usgs.gov/fdsnws/event/1/query?format=csv&starttime='+dateRange[0]+'&minmagnitude='+str(minMag))
	with open(QUAKE_RAW,'w') as f:
		f.write(r.text)
	print ('Earthquake data retrieved')

def getLocation():
	#Return lat/lon as a tuple
	send_url = 'http://freegeoip.net/json'
	print ("Getting location...")
	r = requests.get(send_url)
	j = json.loads(r.text)
	lat = j['latitude']
	lon = j['longitude']
	location = (float(lat),float(lon))
	print ("Found!")
	return location

def getRelativeMins(csvTime):
	rawTime=csvTime
	t=rawTime.split('T')
	d=t[0].split('-')
	t=t[1].split('.')
	t=t[0].split(':')
	quakeTime=datetime.datetime(int(d[0]),int(d[1]),int(d[2]),int(t[0]),int(t[1]),int(t[2]),0)
	utcTime=datetime.datetime.utcnow()
	timeDiff=utcTime-quakeTime
	secs = int(timeDiff.total_seconds())
	mins = secs/60
	return mins

def getRelativeDist(location1, location2):
	distance = round(geopy.distance.vincenty(location1,location2).miles, 2)
	return distance


def parseQuakes(myLocation):
	domains={}
	distMin, distMax = (999999999,-999999999)
	depthMin, depthMax = (999999999,-999999999)
	magMin, magMax = (999999999,-999999999)
	with open(QUAKE_RAW,'r') as f:
		flist=f.readlines()
		flist.pop(0)
	with open(QUAKE_PARSED,'w') as fout:
		fout.write('RelTime(mins),Distance(mi),Depth(km),Mag')
		print ('Converting quake data...')
		for line in flist:
			words=line.split(',')
			mins = getRelativeMins(words[0])
			quakeLocation = (float(words[1]),float(words[2]))
			distance = float(getRelativeDist(myLocation, quakeLocation))
			depth = float(words[3])
			mag = float(words[4])
			fout.write('\n{},{},{},{}'.format(mins, distance, depth, mag))
			#Create dict of domains
			if distance < distMin:
				distMin = distance
			elif distance > distMax:
				distMax = distance
			
			if depth < depthMin:
				depthMin = depth
			elif depth > depthMax:
				depthMax = depth
			
			if mag < magMin:
				magMin = mag
			elif mag > magMax:
				magMax = mag
	domains.update({'distance':(distMin, distMax), 'depth':(depthMin, depthMax), 'magnitude':(magMin, magMax)})
	print ("Conversion completed")
	return domains


def value_to_pitch(mymidi, domain, inval, key):
	scalePct = mymidi.linear_scale_pct(domain[0], domain[1], float(inval))
	#chromatic = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
	scale = SCALES[key]
	note = mymidi.scale_to_note(scalePct, scale)
	midiPitch = mymidi.note_to_midi_pitch(note)
	print("MAGNITUDE: "+str(inval))
	print("DOMAIN: "+str(domain))
	print("PITCH SCALE PCT: "+str(scalePct))
	print("NOTE: "+str(note))
	print("MIDI PITCH: "+str(midiPitch)+'\n')
	return midiPitch

def value_to_vol(mymidi, domain, inval):
	scalePct = mymidi.linear_scale_pct(domain[0], domain[1], float(inval), reverse=True)
	#The lower the input value the higher the volume (for distance)
	vol = scalePct*127
	print("DISTANCE: "+str(inval))
	print("DOMAIN: "+str(domain))
	print("VOL SCALE PCT: "+str(scalePct))
	print("VOL: "+str(int(vol))+'\n')
	return int(vol)

def get_jenks_breaks(col_index, num_breaks):
	data=[]
	with open(QUAKE_PARSED,'r') as f:
		flist=f.readlines()
		flist.pop(0)
		for line in flist:
			values = line.strip().split(',')
			data.append(float(values[col_index]))
	breaks = jenks(data, num_breaks)
	return breaks


def sort_values(value, bins):
	i=0
	for b in bins:
		if value >= bins[-2]:
			print bins
			print "Bin "+str(len(bins)-2)+" LAST!"
			return len(bins)-2
		else:
			if b <= value and value <= bins[i+1]:
				print "Bin "+str(i)
				return i
		# print b
		# print bins[i]
		# print value
		# if b == bins[0]:
		# 	if b <= value and value < bins[1]:
		# 		print "Bin 0"
		# 		return 0
		# elif b == bins[-2]:
		# 	if b <= value and value <= bins[-1]:
		# 		print "Bin "+str(len(bins)-2)+" LAST!"
		# 		return len(bins)-2
		# else:
		# 	if b <= value and value <= bins[i+1]:
		# 		print "Bin "+str(i)
		# 		return i
		i+=1
		print "VALUE = "+str(value)+"\nB = "+str(b)


def create_track_list(mymidi, domains, key, tracks):
	print ("Generating track list...")
	track_list=[]
	for i in range(len(tracks)):
		track_list.append([])
	patch=0
	patch_bins = get_jenks_breaks(3, len(tracks))
	print patch_bins
	with open(QUAKE_PARSED, 'r') as f:
		lines = f.readlines()
		lines.pop(0)
		for line in lines:
			values = line.strip().split(',')
			mag = float(values[3])
			#Define patches based on jenks natural breaks

			track = sort_values(mag, patch_bins)
			patch = int(tracks[track])
			channel = track

			# if patch_bins[0] <= mag and mag < patch_bins[1]:
			# 	channel=0
			# 	patch=tracks[0]
			# 	track=0
			# elif patch_bins[1] <= mag and mag < patch_bins[2]:
			# 	channel=1
			# 	patch=tracks[1]
			# 	track=1
			# elif patch_bins[2] <= mag and mag < patch_bins[3]:
			# 	channel=2
			# 	patch=tracks[2]
			# 	track=2
			# elif patch_bins[3] <= mag and mag < patch_bins[4]:
			# 	channel=3
			# 	patch=tracks[3]
			# 	track=3
			# elif patch_bins[4] <= mag and mag <= patch_bins[5]:
			# 	channel=4
			# 	patch=tracks[4]
			# 	track=4

			track_list[track].append([[
				int(int(values[0])/3), #Time
				value_to_pitch(mymidi, domains['magnitude'], mag, key), #Pitch
				value_to_vol(mymidi, domains['distance'], float(values[1])), #Attack
				float(values[2]), #Duration
				patch #Patch
				],channel])
	print ("We got notes!")
	return track_list


def main():
	args = return_args()
	dates = getDateRange(args.days)
	getRequest(dates, args.minmag)
	myLocation=getLocation()
	domains = parseQuakes(myLocation)
	#domains = {'distance': (33.69, 11845.77), 'depth': (0.42, 599.18), 'magnitude': (2.5, 7.2)}
	quake_midi = MIDITime(outfile=args.outfile, tempo=args.tempo, base_octave=args.base, octave_range=args.range)
	track_list = create_track_list(quake_midi, domains, args.key, args.patches)
	for note_list in track_list:
		quake_midi.add_track(note_list)
	print args.patches
	quake_midi.save_midi()

if __name__ == '__main__':
	main()
