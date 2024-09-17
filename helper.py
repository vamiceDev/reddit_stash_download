from datetime import date

import os
import re

import requests
from requests.exceptions import HTTPError
import unicodedata

from dotenv import load_dotenv

load_dotenv()

OUT_FOLDER = os.getenv("OUT_FOLDER")


def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value)
    return value.strip('-_')[:120]


def make_filename(output_dir, submission, extension, index=None):
    if index:
        filename = '[' + slugify(submission.author, True) + '] ' + slugify(submission.title, True) + '_' + str(
            index).zfill(3) + '.' + extension
    else:
        filename = '[' + slugify(submission.author, True) + '] ' + slugify(submission.title, True) + '.' + extension
    return os.path.join(output_dir, filename[0:200])


def get_file(download_url, submission, session, index=None, ):
    extension = get_extension(download_url)
    output_dir = os.path.join(OUT_FOLDER, submission.subreddit.display_name)
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    output_file = make_filename(output_dir, submission, extension, index)
    if os.path.exists(output_file):
        return output_file
    try:
        response=session.get(download_url)
        response.raise_for_status()
        open(output_file,'wb').write(response.content)
        imgur_error_check(output_file,output_dir)
    except HTTPError:
        if len(os.listdir(output_dir)) == 0:
            os.rmdir(output_dir)
    return output_file

# Using the Imgur API to get a delete post will return the imgur_error.png file.
# This checks the downloaded file against that reference, and deletes it if it matches.
# Some archives returned the imgur_logo.jpg file instead, so this checks that as well.
def imgur_error_check(input_file,output_dir):
    imgur_error_file="imgur_error.png"
    if not imgur_error_check.imgur_error_size:
        imgur_error_check.imgur_error_size=os.path.getsize(imgur_error_file)
    file_size=os.path.getsize(input_file)
    if imgur_error_check.imgur_error_size==file_size:
        if open(imgur_error_file,"rb").read() == open(input_file,"rb").read():
            os.remove(input_file)
            if len(os.listdir(output_dir)) == 0:
                os.rmdir(output_dir)
            return

    imgur_logo_file="imgur_logo.jpg"
    if not imgur_error_check.imgur_logo_size:
        imgur_error_check.imgur_logo_size=os.path.getsize(imgur_logo_file)
    if imgur_error_check.imgur_logo_size==file_size:
        if open(imgur_logo_file,"rb").read() == open(input_file,"rb").read():
            os.remove(input_file)
            if len(os.listdir(output_dir)) == 0:
                os.rmdir(output_dir)
            return



imgur_error_check.imgur_error_size=None
imgur_error_check.imgur_logo_size=None



def get_extension(path):
    extension = path.rsplit(".", 1)[-1].split("?")[0]
    return extension

def get_file_id(stash, file_path):
    base_name = os.path.basename(file_path)
    results=stash.sql_query(f"SELECT id FROM files WHERE basename='{base_name}'")
    rows = results['rows']
    if rows:
        return rows[0][0]
    else:
        return None


def get_image_id(stash,file_path):
    file_id = get_file_id(stash,file_path)
    if not file_id:
        return None
    results=stash.sql_query(f"SELECT image_id FROM images_files WHERE file_id='{file_id}'")
    rows = results['rows']
    if rows:
        return rows[0][0]
    else:
        return None


def get_gallery_id(stash,file_path):
    file_id = get_file_id(stash,file_path)
    if not file_id:
        return None
    results=stash.sql_query(f"SELECT gallery_id FROM galleries_files WHERE file_id='{file_id}'")
    rows = results['rows']
    if rows:
        return rows[0][0]
    else:
        return None


def get_scene_id(stash,file_path):
    file_id = get_file_id(stash,file_path)
    if not file_id:
        return None
    results=stash.sql_query(f"SELECT scene_id FROM scenes_files WHERE file_id='{file_id}'")
    rows = results['rows']
    if rows:
        return rows[0][0]
    else:
        return None


def get_folder_id(stash,file_path):
    results=stash.sql_query(f"SELECT id FROM folders WHERE path='{os.path.dirname(file_path)}'")
    rows = results['rows']
    if rows:
        return rows[0][0]
    else:
        scan_and_wait(stash,os.path.dirname(file_path))
        return get_folder_id(stash,file_path)

def create_studio(stash, submission):
    result = stash.find_studio(studio=submission.subreddit.display_name)
    if result:
        return result['id']
    if not create_studio.reddit_id:
        result = stash.find_studio("Reddit")
        create_studio.reddit_id = result['id']
    icon_url = submission.subreddit.community_icon
    if not icon_url:
        icon_url = submission.subreddit.header_img
    if icon_url and requests.head(icon_url).status_code!=200:
        icon_url=None
    if icon_url:
        result = stash.create_studio({"name": submission.subreddit.display_name,
                                      "url": "https://reddit.com/r/" + submission.subreddit.display_name,
                                      "details": submission.subreddit.description,
                                      "parent_id": create_studio.reddit_id,
                                      "image": icon_url})
    else:
        result = stash.create_studio({"name": submission.subreddit.display_name,
                                      "url": "https://reddit.com/r/" + submission.subreddit.display_name,
                                      "details": submission.subreddit.description,
                                      "parent_id": create_studio.reddit_id})
    return result['id']


create_studio.reddit_id = None


def create_performer(stash, submission):
    author = submission.author
    name = author.name.strip('-')
    result = stash.find_performer(name)
    if result:
        return result['id']
    if hasattr(author, 'icon_img'):
        img_url = author.icon_img
        result = stash.create_performer({"name": name,
                                         "image": img_url,
                                         "url": f"https://reddit.com/user/{name}"})
    else:
        result = stash.create_performer({"name": name,
                                         "url": f"https://reddit.com/user/{name}"})
    return result['id']


def is_image(path):
    return get_extension(path) in ["jpg", "jpeg", "gif", "png"]


def add_gallery_to_stash(stash, submission, file_path, img_paths):
    for path in img_paths:
        if not is_image(path):
            raise Exception("Not an image file")
    gallery_id = get_gallery_id(stash,file_path)
    if not gallery_id:
        with open("missing.txt", 'a', encoding="utf-8") as f:
            f.write("https://reddit.com" + submission.permalink + "\n")
            f.write(file_path + "\n")
            f.write("\n")
        return
    gallery=stash.find_gallery(gallery_id)
    if gallery['studio']:
        return
    title = '[' + slugify(submission.author, True) + '] ' + slugify(submission.title, True)

    studio_id = create_studio(stash, submission)
    created_date = date.fromtimestamp(submission.created_utc)
    date_str = created_date.strftime("%Y-%m-%d")
    if submission.author and 'performer_ids' not in gallery:
        performer_id = create_performer(stash, submission)
        stash.update_gallery({"id": gallery_id, "title": title,
                              "studio_id": studio_id, "url": "https://reddit.com" + submission.permalink,
                              "performer_ids": [performer_id], "date": date_str})
    else:
        stash.update_gallery({"id": gallery_id, "title": title,
                              "studio_id": studio_id, "url": "https://reddit.com" + submission.permalink,
                              "date": date_str})
    for index, img_path in enumerate(img_paths):
        img_id = get_image_id(stash,img_path)
        if not img_id:
            with open("missing.txt", 'a', encoding="utf-8") as f:
                f.write("https://reddit.com" + submission.permalink + "\n")
                f.write(img_path + "\n")
                f.write("\n")
            continue
        image = stash.find_image(img_id)
        if submission.author and 'performer_ids' not in image:
            performer_id = create_performer(stash, submission)
            stash.update_image({"id": img_id, "title": title + " " + str(index + 1),
                                "url": "https://reddit.com" + submission.permalink, "date": date_str,
                                "studio_id": studio_id, "performer_ids": [performer_id]})
        else:
            stash.update_image({"id": img_id, "title": title + " " + str(index),
                                "url": "https://reddit.com" + submission.permalink, "date": date_str,
                                "studio_id": studio_id})


def add_image_to_stash(stash, submission, file_path):
    if not is_image(file_path):
        add_scene_to_stash(stash, submission, file_path)
        return
    stash.create_image(file_path)
    img_id = get_image_id(stash,file_path)
    if not img_id:
        with open("missing.txt", 'a', encoding="utf-8") as f:
            f.write("https://reddit.com" + submission.permalink + "\n")
            f.write(file_path + "\n")
            f.write("\n")
        return
    title = '[' + slugify(submission.author, True) + '] ' + slugify(submission.title, True)

    image=stash.find_image(img_id)
    if image['studio']:
        return
    studio_id = create_studio(stash, submission)
    created_date = date.fromtimestamp(submission.created_utc)
    date_str = created_date.strftime("%Y-%m-%d")
    if submission.author and 'performer_ids' not in image:
        performer_id = create_performer(stash, submission)
        stash.update_image({"id": img_id, "title": title,
                            "url": "https://reddit.com" + submission.permalink, "date": date_str,
                            "studio_id": studio_id, "performer_ids": [performer_id]})
    else:
        stash.update_image({"id": img_id, "title": title, "url": "https://reddit.com" + submission.permalink,
                            "url": "https://reddit.com" + submission.permalink, "date": date_str,
                            "studio_id": studio_id, "date": date_str})


def add_scene_to_stash(stash, submission, output_file):
    scene_id = get_scene_id(stash,output_file)
    if not scene_id:
        with open("missing.txt", 'a', encoding="utf-8") as f:
            f.write("https://reddit.com" + submission.permalink + "\n")
            f.write(output_file + "\n")
            f.write("\n")
        return
    title = '[' + slugify(submission.author, True) + '] ' + slugify(submission.title, True)

    scene=stash.find_scene(scene_id)
    if scene['studio']:
        return
    studio_id = create_studio(stash, submission)
    created_date = date.fromtimestamp(submission.created_utc)
    date_str = created_date.strftime("%Y-%m-%d")
    if submission.author and 'performer_ids' not in scene:
        performer_id = create_performer(stash, submission)
        stash.update_scene({"id": scene_id, "title": title, "url": "https://reddit.com" + submission.permalink,
                            "studio_id": studio_id, "performer_ids": [performer_id], "date": date_str})
    else:
        stash.update_scene({"id": scene_id, "title": title, "url": "https://reddit.com" + submission.permalink,
                            "studio_id": studio_id, "date": date_str})


def scan_and_wait(stash, file_path):
    stash.metadata_scan(paths=[file_path])
    queue = stash.job_queue()
    if queue:
        scan_job = next((x for x in queue if 'Scanning' in x['description']), None)
        if scan_job:
            stash.wait_for_job(scan_job['id'])
