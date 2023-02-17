import os
import asyncio
from bs4 import BeautifulSoup
import requests
import pandas as pd
from discord_webhook import DiscordWebhook

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
    rows = {"Type": [], "Hour": [], "Class": [], "Teacher": [], "Room": [], "Subject": [], "Comment": []}
    for i, row in df.iterrows():
        if str(row['Class']) == your_class or your_class in str((row['Class'])):
            if str(row['Type']) == str(row['Class']) and str(row['Hour']) == str(row['Class']) and str(
                    row['Teacher']) == str(row['Class']) and str(row['Room']) == str(row['Class']) and str(
                    row['Subject']) == str(row['Class']) and str(row['Comment']) == str(row['Class']):
                continue
            else:
                rows["Type"].append(row['Type'])
                rows["Hour"].append(row['Hour'])
                rows["Class"].append(row['Class'])
                rows["Teacher"].append(row["Teacher"])
                rows["Room"].append(row['Room'])
                rows["Subject"].append(row['Subject'])
                rows["Comment"].append(row['Comment'])

    return rows


async def notify(rows, day, date):
    if notify_method == "discord_webhook":
        if not webhook_url.startswith("https://discord.com/api/webhooks/"):
            print(f"{webhook_url} is not a discord webhook url. Url has to startwith: https://discord.com/api/webhooks/")
            quit()

    for i in range(len(rows['Class'])):
        Type = rows["Type"][i]
        Hour = rows["Hour"][i]
        Class = rows["Class"][i]
        Teacher = rows["Teacher"][i]
        Room = rows["Room"][i]
        Subject = rows["Subject"][i]
        Comment = rows["Comment"][i]
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

        message = f'> Day: {Day}\n'\
                  f'> Type: {Type}\n'\
                  f'> Hours: {Hour}\n'\
                  f'> Subject: {Subject}\n'\
                  f'> Teacher: {Teacher}\n'\
                  f'> Class: {Class}\n'\
                  f'> Room: {Room}'

        await send(notify_method=notify_method, message=message)

        '''if Type == "Unterrichtsänderung":
            message = f'{Day} there is a class change in the {Hour}th hour: {Subject}'
            await send(notify_method=notify_method, message=message)
        elif Type == "Betreuung":
            message = f'{Day} in the {Hour}th hour you are being supervised by {Teacherchange} in {Subject}.'
            print(message)
            await send(notify_method=notify_method, message=message)
        elif Type == "Ausfall" or Type == "Entfall":
            message = f'{Day} in the {Hour}th hour your {Subject} class is cancelled.'
            print(message)
            await send(notify_method=notify_method, message=message)
        elif Type == "Raumänderung":
            message = f'{Day} in the {Hour}th hour your room changes in {Subject}: {Room}'
            print(message)
            await send(notify_method=notify_method, message=message)
        elif Type == "Pausenaufsicht":
            message = f'{Day} in the {Hour}th hour your Teacher {Teacher} has break supervision'
            print(message)
            await send(notify_method=notify_method, message=message)
        elif Type == "Vertretung":
            message = f'{Day} in the {Hour}th hour you are being teached by {Teacherchange} instead of {Teacher} in {Subject}'
            print(message)
            await send(notify_method=notify_method, message=message)
        else:
            message = f'{Day} in the {Hour}th hour you have: {Type}'
            print(message)
            await send(notify_method=notify_method, message=message)'''


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


async def save(table):
    try:
        with open("./saved/prevtable.html", "w", encoding="utf-8") as f:
            f.write(table)
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

    if not os.path.exists("./saved/prevtable.html"):
        if os.path.exists("./saved"):
            with open('./saved/prevtable.html', 'w', encoding="utf-8") as f:
                prevtable = ""
                pass
        else:
            os.mkdir("./saved")
            with open('./saved/prevtable.html', 'w', encoding="utf-8") as f:
                prevtable = ""
                pass
    else:
        with open('./saved/prevtable.html', 'r', encoding="utf-8") as f:
            prevtable = f.read()
            f.close()

    if prevtable == str(plan):
        print("Nothing changed exiting")
        quit()

    df = await fetchdf(plan)

    rows = await fetchrows(df)

    await notify(rows, day, date)

    await save(str(plan))

    print("Sucessfully ran")


if __name__ == "__main__":
    asyncio.run(main())