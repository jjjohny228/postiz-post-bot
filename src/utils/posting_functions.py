import asyncio

import pandas as pd
import requests
from datetime import datetime, timedelta
from aiogram.types import Message

from config import Config


async def post_tiktok_video(post_time: str, channel_id: str, description: str, video_url: str):
    postiz_post_url = 'https://api.postiz.com/public/v1/posts'
    data = {
        "type": "schedule",
        "tags": [],
        "shortLink": "true",
        "date": post_time,
        "posts": [
            {
                "integration": {
                    "id": channel_id
                },
                "value": [
                    {
                        "content": description,
                        "image": [
                            {
                                "id": "string",
                                "path": video_url
                            }
                        ]
                    }
                ],
                "settings": {
                    "__type": "tiktok",
                    "privacy_level": "PUBLIC_TO_EVERYONE", # после авторизации заменить на PUBLIC_TO_EVERYONE, SELF_ONLY
                    "duet": "false",
                    "stitch": "false",
                    "comment": "true",
                    "autoAddMusic": "no",
                    "brand_content_toggle": "false",
                    "brand_organic_toggle": "false",
                    "content_posting_method": "DIRECT_POST"
                }
            },
        ],
    }
    headers = {
        'Authorization': Config.POSTIZ_API_KEY,
        'Content-Type': 'application/json'
    }
    response = requests.post(postiz_post_url, json=data, headers=headers)
    return response.status_code


async def post_videos_from_csv(file_path: str, message_from_user: Message):
    """
    Function reads csv file and posts videos.
    Due to the postiz limit (30 api requests an hour), there is limitation to wait next hour
    """
    async def wait_until_next_hour():
        now = datetime.now()
        next_hour = (now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
        wait_seconds = (next_hour - now).total_seconds()
        await message_from_user.answer('Было запощено 30 видео. Нужно подождать следующий час.')
        await asyncio.sleep(wait_seconds)

    while True:
        df = pd.read_csv(file_path)

        if df.empty:
            print("Файл пуст, работа завершена.")
            break

        row_index_to_drop = []

        for idx, row in df.iterrows():
            post_time = row['post_time']
            channel_id = row['channel_id']
            description = row['title'] if not pd.isna(row['title']) else ''
            video_url = row['video_url']

            # post video
            result_status = await post_tiktok_video(post_time, channel_id, description, video_url)
            row_index_to_drop.append(idx)

            if result_status == 429:
                print('Postiz limit was exceeded. Need to wait next hour.')
                await wait_until_next_hour()
            # After waiting, interrupt the current cycle to reread the file
            break

        # Delete successful lines
        if row_index_to_drop:
            df = df.drop(row_index_to_drop)
            df.to_csv(file_path, index=False)
        else:
            # If there is an error, abort without deleting
            break

    return True
