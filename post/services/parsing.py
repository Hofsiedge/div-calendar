import datetime, locale, re, requests
from bs4 import BeautifulSoup
from ..models import Post
from security.models import Security

locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')

def search_bcsexpress():
    pass

# TODO: correct limit handling (joining batches of 10-30 posts)
def search_rbc(ticker: str, offset: int, limit: int):
    security = Security.objects.get(ticker=ticker)
    if security is None:
        return []

    url = f"https://www.rbc.ru/search/?query={{}}&project=rbcnews&category=TopRbcRu_finances&offset={offset}&limit={limit}"
    result = []

    for query in {ticker, security.name}:
        r = requests.get(url.format(query))
        if r.status_code != 200:
            return None

        soup = BeautifulSoup(r.text, 'html.parser')
        links = soup.findAll("a", {"class": "search-item__link"})
        posts = []

        categories = iter(soup.findAll('span', {'class': 'search-item__category'}))
        p1 = re.compile(r'\d\d \w{3}, \d\d:\d\d')       # %d %b, %H:%M
        p2 = re.compile(r'\d\d \w{3} \d{4}, \d\d:\d\d') # %d %b %Y, %H:%M
        p3 = re.compile(r'\d\d:\d\d')                   # %H:%M

        for link in links:
            date_str = next(categories).text.strip()[9:]
            if p1.match(date_str):
                format_string = '%d %b, %H:%M'
            elif p2.match(date_str):
                format_string = '%d %b %Y, %H:%M'
            else:
                format_string = '%H:%M'

            date = datetime.datetime.strptime(date_str, format_string)
            post = Post(
                security    = security,
                date        = date,
                title       = link.find("span", {"class": "search-item__title"}).text,
                text        = link.find("span", {"class": "search-item__text"}).text.strip(),
                source      = 'РБК',
                poster      = '',
                link        = link['href'],
            )
            if post not in result:
                posts.append(post)
        result.extend(posts)

    return result


# TODO: caching
def search_posts(securities: list, offset: int, limit: int):
    data = []
    for security in securities:
        res = search_rbc(security, offset, limit)
        if res is not None:
            data.extend(res)

    return data
