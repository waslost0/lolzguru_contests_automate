import base64
import os
import re
import time
import datetime
import requests
import codecs
import json

import urllib3
from bs4 import BeautifulSoup
import pytesseract
from PIL import Image, UnidentifiedImageError
from requests import RequestException

urllib3.disable_warnings()

PYTESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract'
pytesseract.pytesseract.tesseract_cmd = PYTESSERACT_PATH


try:
    if len(open('session').read()) != 32:
        os.remove('session')
except:
    pass


def get_current_time():
    return datetime.datetime.now().strftime('%m.%d.%y %H:%M:%S')


class ImageWorker:
    """
    Working with captcha image.
    """

    def __init__(self):
        """Constructor"""
        self.captcha_image_filename = 'captcha_image.jpg'
        self.cropped_captcha_filename = 'cropped_captcha.jpg'

    def convert_base64_to_image(self, image_in_base64):
        """
        Convert base64 string to image file.
        :param image_in_base64:
        :return:
        """
        image_in_base64 = str(image_in_base64).replace('data:image/jpeg;base64,', '')
        image_data = base64.b64decode(image_in_base64)

        # Save image as image file
        with open(self.captcha_image_filename, 'wb') as file:
            file.write(image_data)

    def corp_image(self):
        """
        Crop and save image.
        :return:
        """
        try:
            # Open image
            image_to_crop = Image.open(self.captcha_image_filename, 'r')
            # Crop image
            image = image_to_crop.crop((-1, 8, 65, 22))
            # Save image
            image.save(self.cropped_captcha_filename)
        except UnidentifiedImageError as error:
            raise(error)

    def change_image_pixels(self):
        """
        Change pixels to black or white.
        If pixel RGB(32, 32, 32) close to black change to  RGB(0, 0, 0).
        :return:
        """
        try:
            image = Image.open(self.cropped_captcha_filename, 'r')
            pixels = list(image.getdata())
            new_pixels_list = []
            for rgb in pixels:
                if rgb[0] < 160:
                    rgb = (0, 0, 0)
                if rgb[0] > 160:
                    rgb = (255, 255, 255)
                new_pixels_list.append(rgb)
            image.putdata(new_pixels_list)
            image.save(self.cropped_captcha_filename)
        except UnidentifiedImageError as error:
            raise error
            print(error)

    def image_to_string(self):
        """
        Recognize text on image than convert to string via pytesseract library.
        :return: Recognized string
        """
        img = Image.open(self.cropped_captcha_filename)
        config = '--psm 10 --oem 1 -c tessedit_char_whitelist=0123456789+?'
        try:
            return pytesseract.image_to_string(img, config=config)
        except pytesseract.pytesseract.TesseractNotFoundError:
            raise("Tesseract не установлен!")
            exit(-1)

    def process_image(self, base64_string: str) -> str:
        """
        Convert and get tex from image.
        :param base64_string:
        :return:
        """
        self.convert_base64_to_image(base64_string)
        self.corp_image()
        self.change_image_pixels()
        return self.image_to_string()


class LolzWorker:
    """
    LOLZTeam worker. Auto participate in contests.
    """

    def __init__(self):
        """
        Constructor.
        """
        self.host = 'lolz.guru'
        self.links = []
        self.black_list = []
        self.is_like_contest = False
        self.session = requests.Session()
        self.ImageWorker = ImageWorker()
        self.session.verify = False
        self.session.headers = {'cookie': 'xf_viewedContestsHidden=1;'}
        self.set_df_id()
        try:
            self.xf_session = open('session').read()
            self.session.cookies['xf_session'] = self.xf_session
            self.session.cookies['xf_viewedContestsHidden'] = '1'
            self.session.cookies['xf_feed_custom_order'] = 'post_date'
            self.session.cookies['xf_logged_in'] = '1'
        except Exception:
            pass
        self.session.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                                              "Chrome/86.0.4240.75 Safari/537.36"}
        self.token = None


    def get_captcha_image(self, page_html) -> str:
        """
        Parse page and get captcha
        :param page_html:
        :return:
        """
        try:
            items = page_html.select('div[class="ddText"]')
            result_items = re.findall(r'\"data:image.*\"', str(items[0]))
            result_items = str(result_items).replace("\"", "")
        except Exception as e:
            raise e
        else:
            return result_items

    def get_username(self, page_html) -> str:
        try:
            self.username = page_html.select('b[id="NavigationAccountUsername"]')[0].contents[0]
        except IndexError as e:
            raise e
        else:
            return username

    def get_captcha_hash(self, page_html) -> str:
        try:
            captcha_hash = page_html.select('input[name="captcha_question_hash"]')[0]['value']
        except IndexError as e:
            raise e
        else:
            return captcha_hash

    def get_csrf(self, page_html) -> str:
        return page_html.split('_csrfToken: "')[1].split('"')[0]  # Переписать

    def get_post_id(self, page_html) -> str:
        """
        Get post id
        :return: post_id
        """
        try:
            post_id = page_html.find('a', {
                'class': 'item messageDateInBottom datePermalink '
                'hashPermalink OverlayTrigger muted'})['data-href']
            post_id = post_id.split('/')[1]
        except (IndexError, AttributeError) as error:
            raise error
        else:
            return post_id

    def like_contest_request(self, thread_page, post_id):
        """
        Like contest
        :return: json response
        """
        try:
            url = f'https://{self.host}/posts/{post_id}/like'
            data = {
                '_xfRequestUri': f'/threads/{thread_page}/',
                '_xfNoRedirect': 1,
                '_xfToken': self.token,
                '_xfResponseType': 'json',
            }

            response = self.session.post(url, data=data).json()
        except RequestException as e:
            raise e
        else:
            return response

    def like_contest(self, html_parse_bs, link):
        try:
            post_id = self.get_post_id(html_parse_bs)
            username_to_like, user_link = self.get_username_liked_person(html_parse_bs)
            like_result = self.like_contest_request(
                thread_page=link.replace('threads/', ''), post_id=post_id)

            if 'error' in like_result:
                print(like_result['error'][0])
                self.is_like_contest = False
            else:
                print(f'Поставил лайк: {username_to_like} https://{self.host}/{user_link}')
        except Exception as error:
            print(error)

    def get_username_liked_person(self, html_page) -> str:
        """
        Get contest`s username
        :return: username
        """
        try:
            item = html_page.find('a', class_='username')
            link = item['href']
            username = item.span.text
        except (KeyError, TypeError, AttributeError) as error:
            print(error)
            return '', ''
        else:
            return username, link

    def get_balance(self, html_page) -> str:
        """
        Get balance value
        """
        try:
            item = html_page.find('span', class_='balanceValue')
            balance_text = item.text
        except (KeyError, TypeError, AttributeError) as error:
            print(error)
            return ''
        else:
            return balance_text

    def participate_in_contests(self):
        """
        Participate in contests.
        Get urls from page than open one by one.
        :return:
        """

        while True:
            try:
                self.links, page = self.get_contests_urls()
                balance_value = self.get_balance(page)
                os.system("title " + f"Username: {self.username} † Balance: {balance_value} † Developed by waslost")

                for link in self.links:
                    if link not in self.black_list:
                        print('_' * 50)
                        print(f"{get_current_time()}")
                        print(f'https://{self.host}/{link}')
                        link = link.replace('unread', '')

                        with self.session.get(f'https://{self.host}/{link}') as page_req:
                            html_parse_bs = BeautifulSoup(page_req.text, 'html.parser')
                            if not self.check_page(html_parse_bs, link):
                                continue
                            captcha_in_base64 = self.get_captcha_image(html_parse_bs)
                            captcha_hash = self.get_captcha_hash(html_parse_bs)
                            csrf = self.get_csrf(page_req.text)

                        print('Решаю капчу...')
                        captcha_text = self.ImageWorker.process_image(captcha_in_base64)
                        captcha_result = self.parse_captcha_string(captcha_text)
                        print(f'Капча: {str(captcha_text).strip()} = {str(captcha_result).strip()}')

                        if captcha_result is None:
                            print('Can`t recognize captcha.')
                            continue

                        data = {
                            'captcha_question_answer': captcha_result,
                            'captcha_question_hash': captcha_hash,
                            '_xfRequestUri': link,
                            '_xfNoRedirect': 1,
                            '_xfToken': csrf,
                            '_xfResponseType': 'json',
                        }
                        req = self.session.post(f'https://{self.host}/{link}participate', data=data).json()

                        if '_redirectStatus' in req:
                            print(f'Status: {req["_redirectStatus"]}')
                            if self.is_like_contest:
                                html_parse_bs = BeautifulSoup(page_req.content, 'lxml')
                                self.like_contest(html_parse_bs, link)
                        else:
                            print(f'Status: {req["error"]}')

                        print('_' * 50)
                time.sleep(5)
            except Exception as e:
                raise e

    @staticmethod
    def parse_captcha_string(captcha_string: str):
        """
        Get captcha string. Get two digits from string and
        :param captcha_string:
        :return: sum of numbers -> int
        """
        try:
            if captcha_string.find('?') != -1:
                captcha_string = captcha_string[:captcha_string.find('?')]
            list_digits = captcha_string.split('+')
            if list_digits[1] == '':
                return None
            if int(list_digits[1]) > 25:
                list_digits[1] = list_digits[1][0]

        except (ValueError, IndexError) as error:
            print('Cant recognize captcha')
            print(error)
        else:
            return int(list_digits[0]) + int(list_digits[1])

    def check_page(self, html_page, link):
        if link not in self.black_list:
            res = html_page.find('div', class_='error mn-15-0-0')
            if res is not None:
                print(res.text.strip())
                self.black_list.append(link)
                return False
            elif html_page.find('label', class_='OverlayCloser') is not None:
                print('Запрашиваемая тема не найдена.')
                return False
            elif html_page.find('input', class_='textCtrl OptOut') is None:
                print('Вы участвуете в конкурсе.')
                self.black_list.append(link)
                return False
            return True


def load_data_from_file():
    try:
        if not os.path.exists('data.txt'):
            with codecs.open('data.txt', 'w', 'utf-8') as f:
                f.write('USERNAME:PASSWORD')

        with codecs.open('data.txt', 'r', 'utf-8') as f:
            data = f.readlines()

        data = data[0].split(':')
    except KeyError as error:
        print('Cannot find: %s', error.args[0])
    else:
        return data


if __name__ == '__main__':
    username, password = [item for item in load_data_from_file()]
    lolz = LolzWorker()
    if lolz.is_login():
        print('Login success!')
        lolz.participate_in_contests()
    else:
        print('Login error')
        if os.path.isfile('session'):
            os.remove('session')
        if not lolz.login(username, password):
            print("Authorize error...")
        else:
            print('Login success!')
            open('session', 'w+').write(lolz.session.cookies.get("xf_session"))
            lolz.participate_in_contests()
