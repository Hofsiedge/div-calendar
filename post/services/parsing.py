import datetime, locale, re, requests, aiohttp
from bs4 import BeautifulSoup
from ..models import Post
from security.models import Security
from misc.services import fetch_async

locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')


# TODO: correct limit handling (joining batches of 10-30 posts)
async def search_rbc(session: aiohttp.ClientSession, security: Security, offset: int, limit: int):

    if security is None:
        return []

    url = f"https://www.rbc.ru/search/?query={{}}&project=rbcnews&category=TopRbcRu_finances&offset={offset}&limit={limit}"
    result = []

    # TODO: refactor to have a query as an argument instead of security
    for query in (security.ticker, security.name):
        async with session.get(url.format(query)) as r:
            if r.status != 200:
                return None
            text = await r.text()

        soup = BeautifulSoup(text, 'html.parser')
        links = soup.findAll("a", {"class": "search-item__link"})
        posts = []

        categories = iter(soup.findAll('span', {'class': 'search-item__category'}))
        p1 = re.compile(r'\d\d? \w{3} \d{4}, \d\d:\d\d')    # %d %b %Y, %H:%M
        p2 = re.compile(r'\d\d? \w{3}, \d\d:\d\d')          # %d %b, %H:%M
        p3 = re.compile(r'\d\d:\d\d')                       # %H:%M

        for link in links:
            date_str = next(categories).text.strip()[9:]

            if p1.match(date_str):
                date = datetime.datetime.strptime(date_str, '%d %b %Y, %H:%M')
            elif p2.match(date_str):
                date = datetime.datetime.strptime(
                    ' 2020,'.join(date_str.split(',')),
                    '%d %b %Y, %H:%M'
                )
            else:
                date = datetime.datetime.strptime(date_str, '%H:%M')
                date = datetime.datetime.combine(
                    datetime.datetime.now().date(),
                    date.time()
                )

            post = Post(
                security    = security,
                date        = date,
                title       = link.find("span", {"class": "search-item__title"}).text.strip(),
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
def search_posts(securities: list, offset: int, limit: int) -> list:
    securities = list(Security.objects.filter(ticker__in=securities))
    queries = [s.ticker for s in securities]
    queries.extend([s.name for s in securities])
    # TODO: redactoring with queries
    posts = fetch_async(securities, search_rbc, offset, limit)
    result = []
    for post_collection in posts:
        for post in post_collection:
            if post is not None:
                result.append(post)
    return result
