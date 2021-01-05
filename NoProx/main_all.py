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
    Lolz worker. Auto participate in contests.
    """

    def __init__(self):
        """
        Constructor.
        """
        self.host = 'lolz.guru'
        self.links = []
        self.black_list = []
        self.session = requests.Session()
        self.ImageWorker = ImageWorker()
        self.session.verify = False
        self.session.headers = {'cookie':'xf_viewedContestsHidden=1;'}

        try:
            self.xf_session = open('session').read()
            self.session.cookies['xf_session'] = self.xf_session
            self.session.cookies['xf_viewedContestsHidden'] = '1'
            self.session.cookies['xf_feed_custom_order'] = 'post_date'
            self.session.cookies['xf_logged_in'] = '1'
        except:
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
        try:
            item = page_html.find_all('a', class_='item messageDateInBottom datePermalink hashPermalink '
                                                  'OverlayTrigger muted')[0]
            post_id = item.get('data-href')
            return post_id.split('/')[1]
        except IndexError as e:
            raise e

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
                        self.set_df_id()
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
                        else:
                            print(f'Status: {req["error"]}')

                        print('_' * 50)
                time.sleep(10)
            except Exception as e:
                print("Ошибка", str(e))

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
        print('Login successful')
        lolz.participate_in_contests()
    else:
        print('Login fail')
        if os.path.isfile('session'):
            os.remove('session')
        if not lolz.login(username, password):
            print("Login fail...")
        else:
            print('Login successful!')
            open('session', 'w+').write(lolz.session.cookies.get("xf_session"))

            lolz.participate_in_contests()