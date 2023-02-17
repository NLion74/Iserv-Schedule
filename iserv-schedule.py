import os
import asyncio
from bs4 import BeautifulSoup
import requests
import pandas as pd
from discord_webhook import DiscordWebhook
from dataclasses import dataclass
import pickle

username = ""
password = "" # You will have to disable 2fA
domain = ""
your_class = ""

notify_method = ["discord_webhook", "matrix_notifier"] # Available options: discord_webhook, matrix_notifier

# Discord Webhook
webhook_url = "" # Optional only required when using discord webhook notify_method

# Matrix-Notifier
url = ""
room_id = ""
auth_secret = ""

paths = {
        "login": "/iserv/auth/login?_target_path=/iserv/auth/auth?_iserv_app_url%3D%2Fiserv%2F%26client_id%3D16_6cic5kw2maskwckgg804kg400w8wkwwc4o484koswsgsk40okw%26nonce%3D334a68be-3900-4304-ae1d-ad6a97de420d%26redirect_uri%3Dhttps%253A%2F%2Figs-buxtehude.de%2Fiserv%2Fapp%2Fauthentication%2Fredirect%26response_type%3Dcode%26scope%3Dopenid%2520uuid%2520iserv%253Asession-id%2520iserv%253Aweb-ui%2520iserv%253A2fa%253Aconfiguration%2520iserv%253Aaccess-groups%26state%3DeyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiIsImtpZCI6IjEifQ.eyJyZWRpcmVjdF91cmkiOiJodHRwczpcL1wvaWdzLWJ1eHRlaHVkZS5kZVwvaXNlcnZcLyIsIm5vbmNlIjoiMzM0YTY4YmUtMzkwMC00MzA0LWFlMWQtYWQ2YTk3ZGU0MjBkIiwiYWRtaW4iOmZhbHNlLCJpc3MiOiJodHRwczpcL1wvaWdzLWJ1eHRlaHVkZS5kZVwvaXNlcnZcLyIsImV4cCI6MTY2OTIyOTA2OSwibmJmIjoxNjY5MTQyNjA5LCJpYXQiOjE2NjkxNDI2NjksInNpZCI6IiJ9.5lYYvDxPn7foBhGRwzKatK9IHbRG1jntIwQuue96c5WH8ZJxMmqgmDbOU0I-jK6a0pLWyzAacmyGko4s4TNz-g",
        "logout": "/iserv/app/logout",
        "plantd": "/iserv/fs/file/local/Groups/Ansicht/heute/f1/subst_001.htm",
        "plantm": "/iserv/fs/file/local/Groups/Ansicht/morgen/subst_001.htm"
    }
messages = {
        "login_failed": "Anmeldung fehlgeschlagen!"
    }
days = {
    "Montag": "Monday",
    "Dienstag": "Tuesday",
    "Mittwoch": "Wednesday",
    "Donnerstag": "Thursday",
    "Freitag": "Friday",
    "Samstag": "Saturday",
    "Sonntag": "Sunday",
}


@dataclass
class ScheduleChange:
    Type: str
    Hour: str
    Class: str
    Teacher: str
    Room: str
    Subject: str
    Comment: str
    Day: str
    Date: str


async def login(username, password):
    payload = {'_username': f'{username}', '_password': f'{password}'}

    session = requests.session()
    r = session.post(
        url=domain + paths["login"],
        headers={
            "Content-Type": 'application/x-www-form-urlencoded',
            "User-Agent": 'Mozilla/5.0'
        },
        data=payload,
        allow_redirects=True
    )
    if str(r.status_code).startswith(('4', '5')):
        print("Login failed")
        return False

    elif messages["login_failed"] in r.text:
        print("Login failed")
        return False

    return session


async def logout(session):
    r = session.get(
        url=domain + paths["logout"]
    )

    if str(r.status_code).startswith(('4', '5')):
        print("Logout Failed")
        return False

    return True


async def fetchplans(session):
    plan = session.get(url=domain + paths["plantd"])
    soup = BeautifulSoup(plan.content, 'lxml')
    plantd = soup.find_all("table", class_="mon_list")

    return plantd


async def fetchday(session):
    plan = session.get(url=domain + paths["plantd"])
    soup = BeautifulSoup(plan.content, 'lxml')
    titles = soup.find_all("div", class_="mon_title")
    title = titles[0]
    title = str(title).rsplit('<div class="mon_title">')[1]
    title = str(title).rsplit('</div>')[0]
    title = str(title).rsplit(',')[0]
    date = str(title).rsplit(' ')[0]
    day = str(title).rsplit(' ')[1]

    return day, date


async def fetchdf(plan):
    df = pd.read_html(str(plan))[0]
    df.columns = ['Type', 'Hour', 'Class', 'Teacher', 'Room', 'Subject', 'Comment']

    return df


async def fetchrows(df):
    rows= []
    for i, row in df.iterrows():
        if str(row['Class']) == your_class or your_class in str((row['Class'])):
            if str(row['Type']) == str(row['Class']) and str(row['Hour']) == str(row['Class']) and str(
                    row['Teacher']) == str(row['Class']) and str(row['Room']) == str(row['Class']) and str(
                    row['Subject']) == str(row['Class']) and str(row['Comment']) == str(row['Class']):
                continue
            else:
                rows.append({'Type': row['Type'],
                             'Hour': row['Hour'],
                             'Class': row['Class'],
                             'Teacher': row['Teacher'],
                             'Room': row['Room'],
                             'Subject': row['Subject'],
                             'Comment': row['Comment'],})

    rows = [dict(t) for t in {tuple(d.items()) for d in rows}]

    return rows


async def changefetch(rows, day, date):
    changes = []
    for i in range(len(rows)):
        Type = rows[i]["Type"]
        Hour = rows[i]["Hour"]
        Class = rows[i]["Class"]
        Teacher = rows[i]["Teacher"]
        Room = rows[i]["Room"]
        Subject = rows[i]["Subject"]
        Comment = rows[i]["Comment"]
        Day = day
        Date = date

        if Type == "Lehrertausch":
            Type = "Vertretung"
        elif Type == "Unterricht geändert" or Type == "Unterricht geändert	" or Type == "Unterricht geÃ¤ndert":
            Type = "Unterrichtsänderung"
        elif Type == "Raum-Vtr.":
            Type = "Raumänderung"

        if Day in days:
            Day = days[Day]
        else:
            print("Something went wrong with the days")
            continue


        change = ScheduleChange(Type=Type,
                                Hour=Hour,
                                Class=Class,
                                Teacher=Teacher,
                                Room=Room,
                                Subject=Subject,
                                Comment=Comment,
                                Day=Day,
                                Date=Date)
        changes.append(change)

    return changes


async def notify(changes, prev_changes):
    if notify_method == "discord_webhook":
        if not webhook_url.startswith("https://discord.com/api/webhooks/"):
            print(f"{webhook_url} is not a discord webhook url. Url has to startwith: https://discord.com/api/webhooks/")
            quit()

    i = 0
    matches = []
    for change in changes:
        for prev_change in prev_changes:
            if str(change) in str(prev_change):
                matches.append(str(change))
        i += 1
    for change in changes:
        if str(change) not in matches:
            print(change)
            message = f'> Day: {change.Day}\n'\
                      f'> Type: {change.Type}\n'\
                      f'> Hours: {change.Hour}\n'\
                      f'> Subject: {change.Subject}\n'\
                      f'> Teacher: {change.Teacher}\n'\
                      f'> Class: {change.Class}\n'\
                      f'> Room: {change.Room}'

            await send(notify_method=notify_method, message=message)
        else:
            continue


async def send(notify_method, message):
    for method in notify_method:
        if method.lower() == "discord_webhook":
            webhook = DiscordWebhook(url=webhook_url, rate_limit_retry=True, content=message)
            webhook.execute()
        elif method.lower() == "matrix_notifier":
            try:
                requests.post(url, data=message.encode("utf-8"), headers={"Channel": room_id, "Authorization": auth_secret, "markdown": "true"})
            except requests.exceptions.RequestException:
                print("Matrix-Nofier seems to be down")
            except UnicodeError:
                message = message.replace("â†’", "-->")
                try:
                    requests.post(url, data=message.encode("utf-8"), headers={"Channel": room_id, "Authorization": auth_secret, "markdown": "true"})
                except requests.exceptions.RequestException:
                    print("Matrix-Nofier seems to be down")
                except UnicodeError:
                    message = message.encode("utf-8")
                    try:
                        requests.post(url, data=message.encode("utf-8"), headers={"Channel": room_id, "Authorization": auth_secret, "markdown": "true"})
                    except requests.exceptions.RequestException:
                        print("Matrix-Nofier seems to be down")


async def save(changes):
    try:
        with open("./saved/changes.p", "wb") as f:
            pickle.dump(changes, f)
            f.close()
    except UnicodeEncodeError:
        print("Unicode error while saving prevtable.")
        raise


async def main():
    session = await login(username, password)
    if not session:
        quit()

    plan = await fetchplans(session)

    day, date = await fetchday(session)

    await logout(session)

    if os.path.exists("./saved"):
        if os.path.exists("./saved/changes.p"):
            prev_changes = pickle.load(open('./saved/changes.p', 'rb'))
        else:
            prev_changes = []
    else:
        os.mkdir("./saved")
        prev_changes = []

    df = await fetchdf(plan)

    rows = await fetchrows(df)

    changes = await changefetch(rows, day, date)

    if prev_changes:
        if not changes[0].Day == prev_changes[0].Day:
            prev_changes = []

    if str(prev_changes) == str(changes):
        print("Nothing changed exiting")
        quit()

    await notify(changes, prev_changes)

    await save(changes)

    print("Sucessfully ran")


if __name__ == "__main__":
    asyncio.run(main())
