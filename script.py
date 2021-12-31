import re
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs, unquote
from zoneinfo import ZoneInfo
from datetime import datetime


class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass


# класс для обработки запросов
class MyHttpHandler(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_GET(self):

        # получение города по GeoNameId
        if re.fullmatch(r'/\?geoNameId=\d+', self.path):
            geoNameId = self.path.split('=')[-1]
            city = list(filter(lambda _city: _city['geoNameId'] == geoNameId, map_dict))
            if len(city) > 0:
                self._set_headers()
                self.wfile.write(json.dumps(city).encode())
            else:
                self.send_error(400, message=f'Request geoNameId \"{geoNameId}\" not found')

        # получение списка городов на заданной странице с заданным количеством
        elif re.fullmatch(r'/\?page=\d+&count=\d+', self.path):
            parsed_url = urlparse(self.path)
            page = int(parse_qs(parsed_url.query)['page'][0])
            count = int(parse_qs(parsed_url.query)['count'][0])
            if page and count > 0:
                if page * count > len(map_dict):
                    cities_on_page = map_dict[(page - 1) * count:]
                else:
                    cities_on_page = map_dict[(page - 1) * count:page * count]
                if len(cities_on_page) > 0:
                    self._set_headers()
                    self.wfile.write(json.dumps(cities_on_page).encode())
                else:
                    self.send_error(400, message='Out of range')
            else:
                self.send_error(400, message='Zero not allowed in page or count')
        # поиск 2ух городов 
        elif re.fullmatch(r'(/\?c1=[A-Z0-9%]+&c2=[A-Z0-9%]+)|'
                          r'(/\?c1=[A-Z0-9%]+&c2=[A-Z0-9%]+(&north=True|&timezone=True|&north=True&timezone=True))',
                          self.path):
            parsed_url = urlparse(unquote(self.path))
            city1 = transliterate(parse_qs(parsed_url.query)['c1'][0])
            city2 = transliterate(parse_qs(parsed_url.query)['c2'][0])
            res_city1 = list(filter(lambda _city: _city['name'] == city1, map_dict))
            res_city2 = list(filter(lambda _city: _city['name'] == city2, map_dict))
            if len(res_city2) == 0 or len(res_city1) == 0:
                self.send_error(400)
            else:
                if len(res_city1) > 1:
                    res_city1 = sorted(res_city1, key=lambda sort_p: int(sort_p['population']),
                                       reverse=True)
                if len(res_city2) > 1:
                    res_city2 = sorted(res_city2, key=lambda sort_p: int(sort_p['population']),
                                       reverse=True)
                cities = [res_city1[0], res_city2[0]]
                if 'north' in parse_qs(parsed_url.query).keys():
                    cities = [cities, {
                        "North": (sorted(cities, key=lambda sort_l: float(sort_l["latitude"]), reverse=True)[0]["name"])}]
                if 'timezone' in parse_qs(parsed_url.query).keys():
                    current_time = datetime.now()
                    timezone1 = current_time.astimezone(ZoneInfo(res_city1[0]['timezone'])).utcoffset()
                    timezone2 = current_time.astimezone(ZoneInfo(res_city2[0]['timezone'])).utcoffset()
                    time_diff = int(abs((timezone1-timezone2).total_seconds()/3600))
                    if 'north' in parse_qs(parsed_url.query).keys():
                        cities[1].update({'TimeDifference' : time_diff})
                    else:
                        cities = [cities, {'TimeDiffernce' : time_diff}]
                self._set_headers()
                self.wfile.write((json.dumps(cities)).encode())
        #
        elif re.fullmatch(r'(/\?help=[A-Z0-9%]+)', self.path):
            parsed_url = urlparse(unquote(self.path))
            letters = transliterate(parse_qs(parsed_url.query)['help'][0])
            probably_cities = list(filter(lambda _city: letters in _city['name'], map_dict))
            if len(probably_cities) > 0: 
                probably_cities = [city['name'] for city in probably_cities]
                self._set_headers()
                self.wfile.write(json.dumps(probably_cities).encode())
            else:
                self.send_error(400, message='Zero matches') 
        else:
            self.send_error(404)


def transliterate(name):
    """
    Автор: LarsKort
    Дата: 16/07/2011; 1:05 GMT-4;
    Не претендую на "хорошесть" словарика. В моем случае и такой пойдет,
    вы всегда сможете добавить свои символы и даже слова. Только
    это нужно делать в обоих списках, иначе будет ошибка.
    """
    # Слоаврь с заменами
    slovar = {'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
              'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'i', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
              'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h',
              'ц': 'c', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '\'', 'ы': 'y', 'ь': '', 'э': 'e',
              'ю': 'u', 'я': 'ya', 'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'YO',
              'Ж': 'ZH', 'З': 'Z', 'И': 'I', 'Й': 'I', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N',
              'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U', 'Ф': 'F', 'Х': 'H',
              'Ц': 'C', 'Ч': 'CH', 'Ш': 'SH', 'Щ': 'SCH', 'Ъ': '\'', 'Ы': 'y', 'Ь': '', 'Э': 'E',
              'Ю': 'U', 'Я': 'YA', ',': '', '?': '', '~': '', '!': '', '@': '', '#': '',
              '$': '', '%': '', '^': '', '&': '', '*': '', '(': '', ')': '', '-': '', '=': '', '+': '',
              ':': '', ';': '', '<': '', '>': '', '\'': '', '"': '', '\\': '', '/': '', '№': '',
              '[': '', ']': '', '{': '', '}': '', 'ґ': '', 'ї': '', 'є': '', 'Ґ': 'g', 'Ї': 'i',
              'Є': 'e', '—': ''}

    # Циклически заменяем все буквы в строке
    for key in slovar:
        name = name.replace(key, slovar[key])
    return name


if __name__ == '__main__':

    map_dict = list()
    # парсим файлик
    with open("RU.txt", encoding="utf-8") as data:
        for line in data:
            line = line.split('\t')
            map_dict.append(
                {
                    'geoNameId': line[0],
                    'name': line[1],
                    'asciiName': line[2],
                    'alternateNames': line[3],
                    'latitude': line[4],
                    'longitude': line[5],
                    'featureClass': line[6],
                    'featureCode': line[7],
                    'countryCode': line[8],
                    'cc2': line[9],
                    'admin1Code': line[10],
                    'admin2Code': line[11],
                    'admin3Code': line[12],
                    'admin4Code': line[13],
                    'population': line[14],
                    'elevation': line[15],
                    'dem': line[16],
                    'timezone': line[17],
                    'modificationDate': line[18].strip()
                }
            )
    # отсортируем по geonameid
    # map_dict = sorted(map_dict, key=lambda sort_id: sort_id['geoNameId'])

    # запустим если список не пустой
    if len(map_dict) > 0:
        IP = 'localhost'
        PORT = 8000

        httpd = ThreadingSimpleServer((IP, PORT), MyHttpHandler)
        httpd.serve_forever()
