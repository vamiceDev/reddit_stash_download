# This is a sample Python script.
import datetime
# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

import json,csv, os, zipfile, time

from stashapi import log
from stashapi.stashapp import StashInterface

from helper import make_filename, get_file, add_image_to_stash, add_gallery_to_stash, add_scene_to_stash, scan_and_wait
import praw, requests
from imgur_python import Imgur
import redgifs
from redgifs.errors import HTTPException
from bs4 import BeautifulSoup
from helper import OUT_FOLDER

from dotenv import load_dotenv

load_dotenv()

IN_FILENAME = os.getenv("IN_FILENAME")

MISSED_FILE = "reddit_missed.csv"


def main():
    start=time.perf_counter()
    reddit = praw.Reddit(
        client_id=os.getenv('REDDIT_CLIENT_ID'),
        client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
        password=os.getenv('REDDIT_PASSWORD'),
        user_agent=os.getenv('REDDIT_USER_AGENT'),
        username=os.getenv('REDDIT_USERNAME'),
    )
    imgur_client = Imgur({
        "client_id": os.getenv('IMGUR_CLIENT_ID'),
        "client_secret": os.getenv('IMGUR_CLIENT_SECRET'),
        # "access_token": os.getenv('IMGUR_ACCESS_TOKEN'),
        # "expires_in": os.getenv('IMGUR_EXPIRES_IN'),
        # "token_type": "bearer",
        # "refresh_token": os.getenv('IMGUR_REFRESH_TOKEN'),
        # "account_username": os.getenv('IMGUR_USERNAME'),
        # "account_id": os.getenv('IMGUR_ACCOUNT_ID'),
    })
    reddit_pass_dict = {'user': os.getenv('REDDIT_USERNAME'),
                        'passwd': os.getenv('REDDIT_PASSWORD'),
                        'api_type': 'json'}

    headers = {'user-agent': os.getenv('REDDIT_USER_AGENT'), }
    reddit_requests_client = requests.session()
    reddit_requests_client.headers = headers
    l = reddit_requests_client.post('http://www.reddit.com/api/login', data=reddit_pass_dict)

    reddit_requests_client.user = os.getenv('REDDIT_USERNAME')


    imgur_requests_client = requests.session()
    imgur_requests_client.headers = headers

    red = redgifs.API()
    red.login()

    missed_results=[]
    if not os.getenv('STASH_API_KEY'):
        stash = StashInterface({
            "scheme": os.getenv('STASH_SCHEME'),
            "host":  os.getenv('STASH_HOST'),
            "port": os.getenv('STASH_PORT'),
            "logger": log
        })
    else:
        stash = StashInterface({
            "scheme": os.getenv('STASH_SCHEME'),
            "host": os.getenv('STASH_HOST'),
            "port": os.getenv('STASH_PORT'),
            "ApiKey": os.getenv('STASH_API_KEY'),
            "logger": log
        })
    with open(IN_FILENAME, 'r', encoding="utf8") as in_file:
        data = csv.reader(in_file)
        i = 0
        missed = 0
        for row in data:
            entry_url=row[1]
            cur_missed=False
            # To avoid previous loops accidentally affecting this one, clear temp variables.
            index = result = download_url = img_id = album = img = img_urls = img_url = gif_url = \
                output_dir = submission = extension = \
                file_path = archive_name = None
            img_paths = []
            i += 1
            try:
                submission = reddit.submission(url=entry_url)
                submission.is_self
            except:
                missed_results.append(row)
                missed += 1
                continue
            if not submission.is_self:
                download_url = submission.url
                if 'imgur.com/a' in download_url:
                    img_id = download_url.rsplit('/', 1)[-1].split('.')[0]
                    try:
                        album = imgur_client.album_get(img_id)
                    except:
                        cur_missed=True
                    if not img or album['status'] != 200:
                        cur_missed=True
                    if not cur_missed:
                        img_urls = [x['link'] for x in album['response']['data']['images']]
                        output_dir = os.path.join(OUT_FOLDER, submission.subreddit.display_name)
                        if len(img_urls) == 0:
                            continue
                        if not os.path.exists(output_dir):
                            os.mkdir(output_dir)
                        if len(img_urls) == 1:
                            file_path = get_file(img_urls[0], submission,imgur_requests_client)
                            scan_and_wait(stash, file_path)
                            add_image_to_stash(stash, submission, file_path)
                        else:
                            img_paths = []
                            archive_name = make_filename(output_dir, submission, 'zip', )
                            if not os.path.exists(archive_name):
                                with zipfile.ZipFile(archive_name, mode='w') as archive:
                                    for index, img_url in enumerate(img_urls):
                                        file_path = get_file(img_url, submission,imgur_requests_client, index + 1)
                                        extension = img_url.rsplit(".", 1)[-1].split("?")[0]
                                        archive.write(file_path,
                                                      arcname=make_filename('', submission, extension, index + 1))
                                        os.remove(file_path)
                            scan_and_wait(stash, archive_name)
                            add_gallery_to_stash(stash, submission, archive_name, img_paths)
                elif 'imgur.com' in download_url:
                    img_id = download_url.rsplit('/', 1)[-1].split('.')[0]
                    try:
                        img = imgur_client.image_get(img_id)
                    except:
                        cur_missed=True
                    if not img or img['status'] != 200:
                        cur_missed=True
                    if not cur_missed:
                        img_url = img['response']['data']['link']
                        file_path = get_file(img_url, submission,imgur_requests_client)
                        scan_and_wait(stash, file_path)
                        add_image_to_stash(stash, submission, file_path)
                elif 'redgifs.com' in download_url:
                    img_id = download_url.rsplit('/', 1)[-1].split('.')[0].lower()
                    try:
                        result = red.get_gif(img_id.lower())
                    except HTTPException:
                        missed_results.append(row)
                        missed += 1
                        continue
                    gif_url = result.urls.hd
                    extension = gif_url.rsplit(".", 1)[-1].split("?")[0]
                    output_dir = os.path.join(OUT_FOLDER, submission.subreddit.display_name)
                    if not os.path.exists(output_dir):
                        os.mkdir(output_dir)
                    file_path = make_filename(output_dir, submission, extension)
                    if not os.path.exists(file_path):
                        try:
                            red.download(gif_url, file_path)
                        except TypeError:
                            missed_results.append(row)
                            missed += 1
                            continue
                    scan_and_wait(stash, file_path)
                    add_scene_to_stash(stash, submission, file_path)
                elif 'i.redd.it' in download_url:
                    file_path = get_file(download_url, submission,reddit_requests_client)
                    scan_and_wait(stash, file_path)
                    add_image_to_stash(stash, submission, file_path)
                elif 'reddit.com/gallery' in download_url:
                    result = reddit_requests_client.get(download_url)
                    soup = BeautifulSoup(result.text, 'html.parser')
                    result = soup.find("script", {"id": "data"})
                    if result:
                        info = json.loads(result.text[14:])
                    model_key = list(info['posts']['models'].keys())[0]
                    media = info['posts']['models'][model_key]['media']
                    img_urls = []
                    if not media['gallery']:
                        continue
                    for item in sorted(media['gallery']['items'], key=lambda x: x['id']):
                        media_id = item['mediaId']
                        meta = media['mediaMetadata'][media_id]
                        if meta['e'] == 'Image':
                            img_urls.append(meta['s']['u'])
                    if len(img_urls) == 0:
                        continue
                    output_dir = os.path.join(OUT_FOLDER, submission.subreddit.display_name)
                    if not os.path.exists(output_dir):
                        os.mkdir(output_dir)
                    if len(img_urls) == 1:
                        file_path = get_file(img_urls[0], submission,reddit_requests_client)
                        scan_and_wait(stash, file_path)
                        add_image_to_stash(stash, submission, file_path)
                    else:
                        img_paths = []
                        archive_name = make_filename(output_dir, submission, 'zip', )
                        if not os.path.exists(archive_name):
                            with zipfile.ZipFile(archive_name, mode='w') as archive:
                                for index, img_url in enumerate(img_urls):
                                    file_path = get_file(img_url, submission,reddit_requests_client, index)
                                    extension = img_url.rsplit(".", 1)[-1].split("?")[0]
                                    archive.write(file_path, arcname=make_filename('', submission, extension, index))
                                    img_paths.append(file_path)
                                    os.remove(file_path)
                        scan_and_wait(stash, archive_name)
                        add_gallery_to_stash(stash, submission, archive_name, img_paths)
                elif '.jpg' in download_url or '.png' in download_url:
                    file_path = get_file(download_url, submission,reddit_requests_client)
                    scan_and_wait(stash, file_path)
                    add_image_to_stash(stash, submission, file_path)
                elif download_url != '':
                    missed_results.append(row)
                    missed += 1
                if cur_missed:
                    if hasattr(submission,'preview'):
                        if len(submission.preview['images'])==1:
                            img_url=submission.preview['images'][0]['source']['url']
                            if 'external-preview.redd.it' in img_url:
                                file_path = get_file(img_url, submission,reddit_requests_client)
                                scan_and_wait(stash, file_path)
                                add_image_to_stash(stash, submission, file_path)
                            elif 'redditmedia.com' in img_url:
                                print(img_url)
                                missed_results.append(row)
                                missed += 1
                        else:
                            img_urls=[x['source']['url'] for x in submission.preview['images']]

                            img_paths = []
                            archive_name = make_filename(output_dir, submission, 'zip', )
                            if not os.path.exists(archive_name):
                                with zipfile.ZipFile(archive_name, mode='w') as archive:
                                    for index, img_url in enumerate(img_urls):
                                        file_path = get_file(img_url, submission,reddit_requests_client, index + 1)
                                        extension = img_url.rsplit(".", 1)[-1].split("?")[0]
                                        archive.write(file_path,
                                                      arcname=make_filename('', submission, extension, index + 1))
                                        os.remove(file_path)
                            else:
                                for index, img_url in enumerate(img_urls):
                                    file_path = get_file(img_url, submission,reddit_requests_client, index + 1)
                                    img_paths.append(file_path)
                            scan_and_wait(stash, archive_name)
                            add_gallery_to_stash(stash, submission, archive_name, img_paths)
                    else:
                        missed_results.append(row)
                        missed += 1
            else:
                missed_results.append(row)
                missed += 1
            if i % 100 == 0:
                print(i)
        print(f'missed: {missed}')
        print(f'entries: {i}')
        with open(MISSED_FILE, 'w', newline='') as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=' ',
                                   quotechar='|', quoting=csv.QUOTE_MINIMAL)
            csvwriter.writerows(missed_results)
        end=time.perf_counter()
        run_time=end-start
        print("Time: "+str(datetime.timedelta(seconds=run_time)))
        print("Time per entry: "+str(datetime.timedelta(seconds=run_time/i)))


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()
