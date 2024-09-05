
# Overview
**This script is a Work in Progress. It is not guaranteed. MAKE A COPY OF YOUR STASH DB BEFORE PROCEEDING!**

This script downloads video and images from your saved posts on reddit and then adds them to stash.  Reddit's UI only lets you see your most recent 1,000 saved posts on the website, but you can request a zip containing all of your data from reddit, which this script uses.
# Getting your Reddit info
Visit https://www.reddit.com/settings/data-request to request a download of all your Reddit data.

This will take a few days, and will give you a download link to a zip file. Download and unzip it, taking note of the location.

# Environment file
Use the .blank_env file as a template for your environment variables from below.
Rename it .env to have the script load your info.

# Other Info

## Input File
INPUT_FILE is the location of your reddit info file. Specifically, the "saved_posts.csv" file.

## Output Folder
OUT_FOLDER is the location downloaded images, galleries, and scenes should be stored. It should be a path covered by Stash.

# APIS

## Reddit
Create a new app at https://www.reddit.com/prefs/apps/ Specify that it is a Script.  The redirect URI can be anything, including localhost, it won't be used.

The client_id is listed at the top of the description of the created app, under where it says "personal use script".  The client_secret can be found by clicking "update app", listed next to "secret"

Fill in the relevant information in the .env file under the REDDDIT portions.
## Imgur
Go to https://api.imgur.com/oauth2/addclient to create an API token.
This script only downloads data from Imgur, so you can select: 

"Anonymous usage without user authorization"

under Authorization Type.

Save the relevant information in the .env file under the IMGUR portions.

## Redgifs
Redgifs doesn't require a login, but does require a specific header to not reject the download request.
The redgifs python library: https://github.com/scrazzz/redgifs  handles this smoothly.

However, as of 9/5/2024, there is a bug: https://github.com/scrazzz/redgifs/issues/37 that requires downloading the most recent version from GitHub:

`pip install --force-reinstall git+https://github.com/scrazzz/redgifs`


# Result Formatting
## File structure
The script will make a subfolder for each subreddit, with the same name under OUT_FOLDER.

## File Name
Files will be stored in their subreddit folder, with the name "[user_name] post_title".extension, with both being stripped of special characters using the slugify method in helper.py

If the poster has deleted their account, the file will be "[None] post_title".extension


## Studio Structure
A new studio, titled "Reddit" will be created. Each subreddit will be it's own studio, a child studio of the main Reddit studio.
Subreddit studios will use that subreddit's icon, if available, as their image.

## Performer Structure
For any post where the poster hasn't deleted their account, a new performer with that name will be created.
Their picture will be that account's profile picture, if any exists.

The performer's URL will be set to their reddit user page:
https://www.reddit.com/user/user_name

## Image, gallery, scene structure
In all three cases, the title of the entry will be: "[user_name] post_title" (no file extension), stripped of special characters.

* The url for the post will be added to the entry's url list
* The poster will be added as a performer, with a new performer created if needed.
* The date will be set to the post's upload date.

# Speeding up the script
The script runs a metadata_scan after each file is downloaded. If the file is a scene, this can trigger the generation of previews, covers and hashes.

Disabling the automatic generation of these will speed up the script.
