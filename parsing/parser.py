import requests
import pandas as pd

LIMIT = 100

def parse_moex(query: str, limit: int) -> pd.DataFrame:
    r = requests.get(f"https://www.moex.com//iss/securities.json?q={query}&limit={LIMIT}&lang=ru")
    if r.status_code != 200:
        return None
    columns = r.json()['securities']['columns']
    data = r.json()['securities']['data']
    mapping = {'secid': 'ticket', 'name': 'name', 'type': 'type'}
    df = pd.DataFrame(columns=columns, data=data)
    df = df[['secid', 'name', 'type']][df.type.str.match(r".*(share|bond)")].reset_index(drop=True)
    df = df[:limit]
    df.rename(columns={'secid': 'ticket'}, inplace=True)
    df.type = df.type.map({'common_share': 'stock', 'preferred_share': 'stock', 'exchange_bond': 'bond'})
    return df


def search(query: str, limit: int):
    res = parse_moex(query, limit)
    if res is None:
        return None
    return res.to_dict(orient='records')
