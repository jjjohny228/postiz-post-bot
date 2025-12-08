import asyncio
import ssl
from datetime import datetime, timedelta
from enum import Enum

import pandas as pd
import aiohttp
from aiogram.types import Message

from config import Config


class Platforms(str, Enum):
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"


class ApostolVideoUploader:
    """
    Class to upload video using Apostol api
    """
    async def upload_video(self, file_path: str, message: Message):
        """
        Function to parse file and upload video to the platforms
        """
        while True:
            df = pd.read_csv(file_path)

            if df.empty:
                print("The file is empty, the job is complete.")
                return True

            row_index_to_drop = []
            should_wait_for_next_hour = False

            for idx, row in df.iterrows():
                post_time = row['post_time']
                channel_id = row['channel_id']
                description = row['title'] if not pd.isna(row['title']) else ''
                video_url = row['video_url']
                platform = row['channel_platform']

                # post video
                try:
                    if platform == Platforms.TIKTOK.value:
                        response_status_code = await self.__post_tiktok_video(post_time, channel_id, description, video_url)
                    elif platform == Platforms.YOUTUBE.value:
                        valid_video_description = await self.__cut_description_for_youtube_videos(description)
                        response_status_code = await self.__post_youtube_video(post_time, channel_id, valid_video_description, video_url)
                    else:
                        raise ValueError(f'Platform not supported: {platform}')

                    if response_status_code == 429:
                        print('Postiz limit was exceeded. Need to wait next hour.')
                        should_wait_for_next_hour = True
                        # Don't mark this row as successful, we'll retry it after waiting
                        break
                    elif response_status_code >= 200 and response_status_code < 300:
                        # Only mark as successful if status code is 2xx
                        row_index_to_drop.append(idx)
                    else:
                        print(f'Unexpected status code: {response_status_code} for row {idx}')
                        # Don't mark as successful, but continue processing

                except Exception as e:
                    print(f'Error while posting videos for row {idx}: {e}')
                    # Continue processing other rows even if one fails

            # Delete successful lines
            if row_index_to_drop:
                df = df.drop(row_index_to_drop)
                df.to_csv(file_path, index=False)

            # Wait for next hour if rate limit was hit
            if should_wait_for_next_hour:
                await self.__wait_until_next_hour(message)
                # Continue the loop to retry remaining rows
                continue

            # If no rows were processed successfully in this iteration, exit to avoid infinite loop
            if not row_index_to_drop:
                return True


    @staticmethod
    async def __cut_description_for_youtube_videos(description: str) -> str:
        """
        Function cuts video description due to the YouTube limitation.
        Max description length is 100 characters.
        """
        if len(description) > 100:
            return description[-100:]
        return description

    @staticmethod
    async def __post_tiktok_video(post_time: str, channel_id: str, description: str, video_url: str):
        postiz_post_url = Config.POSTIZ_POST_VIDEOS_URL
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
                        "privacy_level": "PUBLIC_TO_EVERYONE", # After authorization, replace with PUBLIC_TO_EVERYONE, SELF_ONLY
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
        # Создаем SSL контекст, который не проверяет сертификаты
        # ВНИМАНИЕ: Это небезопасно для продакшена, но необходимо если есть проблемы с сертификатами
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(postiz_post_url, json=data, headers=headers) as response:
                return response.status

    @staticmethod
    async def __post_youtube_video(post_time: str, channel_id: str, description: str, video_url: str):
        postiz_post_url = Config.POSTIZ_POST_VIDEOS_URL
        video_title = description if len(description) > 2 else '   '
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
                            "content": '',
                            "image": [
                                {
                                    "id": "string",
                                    "path": video_url
                                }
                            ]
                        }
                    ],
                    "settings": {
                        "__type": "youtube",
                        "title": video_title,
                        "type": "public",
                        "selfDeclaredMadeForKids": "no",
                    }
                },
            ],
        }
        headers = {
            'Authorization': Config.POSTIZ_API_KEY,
            'Content-Type': 'application/json'
        }
        # Создаем SSL контекст, который не проверяет сертификаты
        # ВНИМАНИЕ: Это небезопасно для продакшена, но необходимо если есть проблемы с сертификатами
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(postiz_post_url, json=data, headers=headers) as response:
                return response.status

    @staticmethod
    async def __wait_until_next_hour(message_from_user: Message):
        now = datetime.now()
        next_hour = (now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1, minutes=10))
        wait_seconds = (next_hour - now).total_seconds()
        await message_from_user.answer('Было запощено 30 видео. Нужно подождать следующий час.')
        await asyncio.sleep(wait_seconds)


# if __name__ == '__main__':
#     ApostolVideoUploader().upload_video('result/csv_result/1764939218_sample-bulk.csv')
#
#
# async def post_tiktok_video(post_time: str, channel_id: str, description: str, video_url: str):
#     postiz_post_url = 'https://api.postiz.com/public/v1/posts'
#     data = {
#         "type": "schedule",
#         "tags": [],
#         "shortLink": "true",
#         "date": post_time,
#         "posts": [
#             {
#                 "integration": {
#                     "id": channel_id
#                 },
#                 "value": [
#                     {
#                         "content": description,
#                         "image": [
#                             {
#                                 "id": "string",
#                                 "path": video_url
#                             }
#                         ]
#                     }
#                 ],
#                 "settings": {
#                     "__type": "tiktok",
#                     "privacy_level": "PUBLIC_TO_EVERYONE", # после авторизации заменить на PUBLIC_TO_EVERYONE, SELF_ONLY
#                     "duet": "false",
#                     "stitch": "false",
#                     "comment": "true",
#                     "autoAddMusic": "no",
#                     "brand_content_toggle": "false",
#                     "brand_organic_toggle": "false",
#                     "content_posting_method": "DIRECT_POST"
#                 }
#             },
#         ],
#     }
#     headers = {
#         'Authorization': Config.POSTIZ_API_KEY,
#         'Content-Type': 'application/json'
#     }
#     response = requests.post(postiz_post_url, json=data, headers=headers)
#     return response.status_code
#
#
# async def post_videos_from_csv(file_path: str, message_from_user: Message):
#     """
#     Function reads csv file and posts videos.
#     Due to the postiz limit (30 api requests an hour), there is limitation to wait next hour
#     """
#     async def wait_until_next_hour():
#         now = datetime.now()
#         next_hour = (now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1, minutes=10))
#         wait_seconds = (next_hour - now).total_seconds()
#         await message_from_user.answer('Было запощено 30 видео. Нужно подождать следующий час.')
#         await asyncio.sleep(wait_seconds)
#
#     while True:
#         df = pd.read_csv(file_path)
#
#         if df.empty:
#             print("Файл пуст, работа завершена.")
#             break
#
#         row_index_to_drop = []
#
#         for idx, row in df.iterrows():
#             post_time = row['post_time']
#             channel_id = row['channel_id']
#             description = row['title'] if not pd.isna(row['title']) else ''
#             video_url = row['video_url']
#             channel_platform = row['channel_platform']
#
#             # post video
#             result_status = await post_tiktok_video(post_time, channel_id, description, video_url)
#             row_index_to_drop.append(idx)
#
#             if result_status == 429:
#                 print('Postiz limit was exceeded. Need to wait next hour.')
#                 await wait_until_next_hour()
#             # After waiting, interrupt the current cycle to reread the file
#             break
#
#         # Delete successful lines
#         if row_index_to_drop:
#             df = df.drop(row_index_to_drop)
#             df.to_csv(file_path, index=False)
#         else:
#             # If there is an error, abort without deleting
#             break
#
#     return True
