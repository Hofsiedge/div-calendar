import requests
import pandas as pd
from bs4 import BeautifulSoup

def search_bcsexpress():
    pass

def search_rbc(ticker: str, offset: int, limit: int):
    url = "https://www.rbc.ru/search/?query={}&project=rbcnews&category=TopRbcRu_finances"
    r = requests.get(url.format(ticker))
    if r.status_code != 200:
        return None
    soup = BeautifulSoup(r.text, 'html.parser')
    links = soup.findAll("a", {"class": "search-item__link"})
    df = pd.DataFrame(columns=['title', 'text', 'poster', 'date', 'source', 'link'])
    title, text, date, _link = [], [], [], []

    for link in links:
        title.append(link.find("span", {"class": "search-item__title"}).text)
        text.append(link.find("span", {"class": "search-item__text"}).text.strip())
        _link.append(link['href'])

    categories = soup.findAll('span', {'class': 'search-item__category'})
    for span in categories:
        date.append(span.text.strip()[9:])

    df.title = title
    df.text = text
    df.link = _link
    df.date = date
    df.poster.fillna('', inplace=True)
    df.source.fillna('РБК', inplace=True)

    return df[offset:limit]


# TODO: caching
def search_posts(securities: list, offset: int, limit: int):
    data = []
    for security in securities:
        res = search_rbc(security, offset, limit)
        if res is not None:
            data.append(res)
    return pd.concat(data).to_dict(orient='records')
