# motioneye-pruner
Delete motioneye media files in chronological order until a minimum percentage of disk space is free.

This is a companion program for motioneye.

The only built-in deletion method deletes files after they have reached a certain age, so I wrote this to delete the oldest files from the motioneye data directory until a percentage of free disk space has been freed.  The media path is preserved, as are any first-level directories inside the media path (usually directories for individual cameras).  It will also skip any file titled '.donotdelete'.

It attempts to play safe by retrieving the media path from motioneye.conf instead of letting you specify it yourself.  Still, there's nothing to prevent a misconfigured media path setting from trashing something important so please make sure Motioneye is configured properly before unleashing the beast.

Also, this is my very first python program, so be aware that it's possible I've overlooked something.  Keep this in mind as this program has no problem ruthlessly deleting files it finds in the media path.

Arguments:

  -h, --help            show this help message and exit
  
  -c , --config CONFIG  path to motioneye config file (default: /etc/motioneye/motioneye.conf)
  
  -f , --free FREE      minimum free disk space, percent (default: 20.00)
  
  -v, --verbose         verbose output
  
  -n, --dryrun          perform a trial run with no changes made
