#!/usr/bin/python
#
# First created 2016-2-28 by Ryan Stanley (rstanley75@gmail.com)
#
# This is a companion program for motioneye.
# I found the built-in method for file deletion to be inadequate for my needs.
# The only built-in deletion method deletes files after they have reached a certain age,
# so I wrote this to delete the oldest files from the motioneye data directory 
# until a percentage of free disk space has been freed.
#
# This is my very first python program.  Please be gentle.
#

import os, sys, math, errno, argparse

pretend = False
verbose = False

# Returns the media_path setting from the motioneye config file.
def get_media_path(configfile):
	with open(configfile, "r") as f:
		for line in f:
			if (line.strip()).startswith('media_path'):
				item, value = (line.strip()).split(" ",2)
				return(value)

# Returns the percentage of free disk space.
def check_free_percent(rootfolder):
	statv= os.statvfs(rootfolder)
	return 100.0 - ( 100.0 * float(statv.f_blocks - statv.f_bfree) / float(statv.f_blocks - statv.f_bfree + statv.f_bavail) )

# Returns the free disk space.
def check_free_space(rootfolder):
	statv= os.statvfs(rootfolder)
	return statv.f_bavail * statv.f_frsize / 1024

# Returns the number of used blocks.
def check_used_blocks(rootfolder):
	statv= os.statvfs(rootfolder)
	return float(statv.f_blocks * statv.f_bsize) - float(statv.f_bfree * statv.f_bsize)

# Returns how much data is left to reach the minumum percentage of free space.
def check_space_to_min(rootfolder, minpercent):
	statv= os.statvfs(rootfolder)
	targetpercent = minpercent - check_free_percent(rootfolder);
	if targetpercent > 0:
		return float(targetpercent / 100.0) * float(statv.f_blocks * statv.f_frsize / 1024)
	else:
		return 0.0

# This is the important part, this returns our list of files by oldest date.
def files_by_oldest(rootfolder):
	# I don't know why this next line works, I found it on stackoverflow.
	return sorted((os.path.join(dirname, filename) for dirname, dirnames, filenames in os.walk(rootfolder) for filename in filenames), key=lambda fn: os.stat(fn).st_mtime),reversed==True

# Return True if 'filename' is in 'keeplist', otherwise return False.
def check_keepfiles(filename, keeplist):
	for flap in keeplist:
		if filename.endswith(flap):
			return True
	return False

# Overwrite 'filename' with zero length data, part of the workaround for Copy On Write filesystems that are 100% full.
def overwrite_with_zero_data(filename):
	try:
		if (pretend):
			if (verbose): print("If this wasn't a dry run", filename, "would be overwritte with zero length data.")
		else:
			if (verbose): print("Overwriting", filename, "with zero length data.")
			f = open(filename, 'w')		# Open 'filename' for writing.
			f.close()			# and then immediately close it, resulting in a zero length file.
		return True
	except OSError as e:
		if e.errno != errno.ENOENT:
			return False
	
# Deletes 'filename' from the disk and return True, return False if there is an error.
def silentremove(filename):
	try:
		if (pretend):
			return True
		else:
			if os.path.isfile(filename):
				os.remove(filename)
			elif os.path.isdir(filename):
				os.rmdir(filename)
			else:
				return False
		return True
	except OSError as e:
		if e.errno != errno.ENOENT:
			return False

# Deletes files in 'basepath' by oldest date, excluding any files in the keep list, until the targeted percentage of free disk space is remaining.
def delete_files_by_oldest(basepath, keepfiles, target_freepercent):
	totalsize = 0.0
	targetsize = check_space_to_min(basepath,target_freepercent)	# get how much actual space needs to be freed based on the target for percentage free

	# If we don't need to do anything, don't do anything
	if (totalsize >= targetsize):
		if (verbose): print("Adequate space remaining, no need to remove any files.")
		return True

	# If the filesystem is completely full, we're going to have some problems on Copy On Write filesystems.  This is part of a workaround.
	if (check_free_percent(basepath) == 0.0):
		filesystemfull_flag = True
	else:
		filesystemfull_flag = False
	
	for files in files_by_oldest(basepath):
		# When the follwing loop breaks, 'files' becomes a bool and the program throws an error.  This is a workaround to make the loop exit cleanly.
		if (type(files) == type(True)):
			break
		for fnord in files:
			# Skip deletion if file is in the keep files list.
			if (check_keepfiles(fnord,keepfiles)):
				if (verbose): print("Skipping %s" % (fnord))
				continue
			size = os.stat(fnord).st_size / 1024
			# Workaround for Copy On Write filesystems' inablility to delete files if there is zero free space.
			if (filesystemfull_flag):
				overwrite_with_zero_data(fnord)
				filesystemfull_flag = False
			# Remove the file
			if (silentremove(fnord)):
				totalsize = totalsize + size
				if (verbose): print("%s\t%0.2f\t%0.2f/%0.2f" % (fnord,size,totalsize,targetsize))
			# Break if we have deleted enough bytes to meet or exceed the target for free space.
			if (totalsize >= targetsize):
				break

	return True


# Recursively delete empty directories from 'path'.  I can't take credit for most of this, I got impatient and copied the important bits from stackoverflow.
def recursive_delete_if_empty(path,keepfiles):
	if not os.path.isdir(path):
		return False
	if check_keepfiles(path,keepfiles):
		return False
	if all([recursive_delete_if_empty(os.path.join(path, filename),keepfiles)
		for filename in os.listdir(path)]):
			try:
				if (pretend):
					if (verbose): print("Intended path:", path)
				else:
					if (verbose): print("Removing path: ",path)
					os.rmdir(path)
					return True
			except OSError as e:
				if e.errno != errno.ENOENT:
					return False
	else:
		return False

#####
# Let's a go
#####

def main():

	motioneye_configfile = "/etc/motioneye/motioneye.conf"		# path to motioneye config file
	target_freepercent = 20						# target for free disk space in percent
	keepfiles = [ ".donotdelete" ]					# files that should be kept no matter how old they are

	# Parse the command line arguments, if any
	parser = argparse.ArgumentParser(
		description="Prune motioneye media files until a minimum percentage of disk space is free.",
		epilog='''
			This program aims to provide an alternative to the built-in Preserve Pictures/Movies feature in Motioneye.  Instead of deleting after a period of time, this program deletes files from the Motioneye media path directory - starting with the oldest - to achieve a certain percentage of disk space has been freed.\n\n

			After the file deletion task has completed the program then deletes all empty directories, leaving the first-level directories inside the Motioneye media path directory.
			'''
		)
	parser.add_argument("-c", "--config", help="path to motioneye config file (default: %s)" % motioneye_configfile)
	parser.add_argument("-f", "--free", type=int, default=20, help="minimum free disk space, percent (default: %0.2f)" % target_freepercent)
	parser.add_argument("-v", "--verbose", help="verbose output", action="store_true")
	parser.add_argument("-n", "--dryrun", help="perform a trial run with no changes made", action="store_true")
	args = parser.parse_args()

	if args.config:
		motioneye_configfile = args.config
	if args.free:
		target_freepercent = args.free
	if args.verbose:
		global verbose
		verbose = True
	if args.dryrun:
		global pretend
		pretend = True

	basepath = get_media_path(motioneye_configfile)			# get the base path from the motioneye config file
	targetsize = check_space_to_min(basepath,target_freepercent)	# Calculate the amount of disk space to delete to meet the target free percentage
	keepfiles.append(basepath)
	keepfiles = keepfiles + os.listdir(basepath)			# Append directories in basepath to keepfiles list

	if (verbose):
		print("Motioneye Config Path:", motioneye_configfile)
		print("Media Path:",basepath)
		print("Keep files:",keepfiles)
		print("Target free (percent):",target_freepercent)
		print("Space free (percent):",round(check_free_percent(basepath)))
		print("Space free (bytes):",check_free_space(basepath))
		print("Required deletion to reach target free space:",targetsize)
		if (pretend): print("Dry run.  No files will be deleted.")

	# First we delete files starting with the oldest first until we reach our target percentage free
	delete_files_by_oldest(basepath, keepfiles, target_freepercent)

	# Next, we'll recursively prune the empty paths
	recursive_delete_if_empty(basepath,keepfiles)

	return 0

main()
sys.exit(0)
			
