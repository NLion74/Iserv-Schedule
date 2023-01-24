import os
from bs4 import BeautifulSoup
import requests
import pandas as pd
from discord_webhook import DiscordWebhook

username = "your.user"
password = "your_pass" # You will have to disable 2fA
domain = "https://your.iserv.tld"
your_class = "class"

notify_method = "discord_webhook"
webhook_url = "webhook_url" # Optional only required when using discord webhook notify_method

paths = {
        "login": "/iserv/auth/login?_target_path=/iserv/auth/auth?_iserv_app_url%3D%2Fiserv%2F%26client_id%3D16_6cic5kw2maskwckgg804kg400w8wkwwc4o484koswsgsk40okw%26nonce%3D334a68be-3900-4304-ae1d-ad6a97de420d%26redirect_uri%3Dhttps%253A%2F%2Figs-buxtehude.de%2Fiserv%2Fapp%2Fauthentication%2Fredirect%26response_type%3Dcode%26scope%3Dopenid%2520uuid%2520iserv%253Asession-id%2520iserv%253Aweb-ui%2520iserv%253A2fa%253Aconfiguration%2520iserv%253Aaccess-groups%26state%3DeyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiIsImtpZCI6IjEifQ.eyJyZWRpcmVjdF91cmkiOiJodHRwczpcL1wvaWdzLWJ1eHRlaHVkZS5kZVwvaXNlcnZcLyIsIm5vbmNlIjoiMzM0YTY4YmUtMzkwMC00MzA0LWFlMWQtYWQ2YTk3ZGU0MjBkIiwiYWRtaW4iOmZhbHNlLCJpc3MiOiJodHRwczpcL1wvaWdzLWJ1eHRlaHVkZS5kZVwvaXNlcnZcLyIsImV4cCI6MTY2OTIyOTA2OSwibmJmIjoxNjY5MTQyNjA5LCJpYXQiOjE2NjkxNDI2NjksInNpZCI6IiJ9.5lYYvDxPn7foBhGRwzKatK9IHbRG1jntIwQuue96c5WH8ZJxMmqgmDbOU0I-jK6a0pLWyzAacmyGko4s4TNz-g",
        "logout": "/iserv/app/logout",
        "plantd": "/iserv/fs/file/local/Groups/Ansicht/heute/f1/subst_001.htm",
        "plantm": "/iserv/fs/file/local/Groups/Ansicht/morgen/subst_001.htm"
    }
messages = {
        "login_failed": "Anmeldung fehlgeschlagen!"
    }

def login(username, password):
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

    if messages["login_failed"] in r.text:
        print("Login failed")
        return False

    return session


def fetchplans(session):
    plan = session.get(url=domain + paths["plantd"])
    soup = BeautifulSoup(plan.content, 'lxml')
    plantd = soup.find_all("table", class_="mon_list")

    return plantd


def fetchday(session):
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


def fetchdf(plan):
    df = pd.read_html(str(plan))[0]
    df.columns = ['Type', 'Hour', 'Class', 'Teacher', 'Room', 'Subject', 'Comment']

    return df


def fetchrows(df):
    rows = {"Type": [], "Hour": [], "Class": [], "Teacher": [], "Teacher-change": [], "Room": [], "Subject": [], "Comment": []}
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
                rows["Teacher"].append(str(row["Teacher"]).rsplit("â†’")[0])
                try:
                    rows["Teacher-change"].append(str(row["Teacher"]).rsplit("â†’")[1])
                except:
                    rows["Teacher-change"].append(str(row["Teacher"]).rsplit("â†’")[(len(str(row["Teacher"]).rsplit("â†’")) - 1)])
                rows["Room"].append(row['Room'])
                rows["Subject"].append(row['Subject'])
                rows["Comment"].append(row['Comment'])

    return rows


def notify(rows, day, date):
    if notify_method == "discord_webhook":
        if not webhook_url.startswith("https://discord.com/api/webhooks/"):
            print(f"{webhook_url} is not a discord webhook url. Url has to startwith: https://discord.com/api/webhooks/")
            quit()

    for i in range(len(rows['Class'])):
        Type = rows["Type"][i]
        Hour = rows["Hour"][i]
        Class = rows["Class"][i]
        Teacher = rows["Teacher"][i]
        Teacherchange = rows["Teacher-change"][i]
        Room = rows["Room"][i]
        Subject = rows["Subject"][i]
        Comment = rows["Comment"][i]
        Day = day
        Date = date

        if "â†’" in Teacher:
            Teacher = str(Teacher).rsplit("â†’")[0]
        elif "â†’" in Teacherchange:
            Teacherchange = str(Teacherchange).rsplit("â†’")[1]

        if Type == "Lehrertausch":
            Type = "Vertretung"
        elif Type == "Unterricht geändert" or Type == "Unterricht geändert	":
            Type = "Unterrichtsänderung"
        elif Type == "Raum-Vtr.":
            Type = "Raumänderung"

        if Type == "Unterrichtsänderung":
            print(f'{Day} gibt es eine {Type} in der {Hour} Stunde: {Subject}')
            if notify_method == "discord_webhook":
                webhook = DiscordWebhook(url=webhook_url, rate_limit_retry=True, content=f'{Day} gibt es eine {Type} in der {Hour} Stunde: {Subject}')
                webhook.execute()
        elif Type == "Betreuung":
            print(f'{Day} in der {Hour} Stunde hast du {Type} von {Teacherchange} in {Subject}.')
            if notify_method == "discord_webhook":
                webhook = DiscordWebhook(url=webhook_url, rate_limit_retry=True, content=f'{Day} in der {Hour} Stunde hast du {Type} von {Teacherchange} in {Subject}.')
                webhook.execute()
        elif Type == "Ausfall" or Type == "Entfall":
            print(f'{Day} in der {Hour} Stunde hast du {Type} in {Subject}.')
            if notify_method == "discord_webhook":
                webhook = DiscordWebhook(url=webhook_url, rate_limit_retry=True, content=f'{Day} in der {Hour} Stunde hast du {Type} in {Subject}.')
                webhook.execute()
        elif Type == "Raumänderung":
            print(f'{Day} in der {Hour} Stunde hast du eine {Type} in {Subject}: {Room}')
            if notify_method == "discord_webhook":
                webhook = DiscordWebhook(url=webhook_url, rate_limit_retry=True, content=f'{Day} in der {Hour} Stunde hast du eine {Type} in {Subject}: {Room}')
                webhook.execute()
        elif Type == "Pausenaufsicht":
            print(f'{Day} in der {Hour} Stunde hat euer Lehrer {Teacher} {Type}')
            if notify_method == "discord_webhook":
                webhook = DiscordWebhook(url=webhook_url, rate_limit_retry=True, content=f'{Day} in der {Hour} Stunde hat euer Lehrer {Teacher} {Type}')
                webhook.execute()
        else:
            print(f'{Day} in der {Hour} Stunde hast du {Type}')
            if notify_method == "discord_webhook":
                webhook = DiscordWebhook(url=webhook_url, rate_limit_retry=True, content=f'{Day} in der {Hour} Stunde hat euer Lehrer {Teacher} {Type}')
                webhook.execute()


def save(table):
    with open("./saved/prevtable.html", "w") as f:
        f.write(table)
        f.close()


def main():
    session = login(username, password)
    if not session:
        quit()

    plan = fetchplans(session)

    with open('t.html') as f: # Gotta be removed
        table = f.read() # Gotta be removed

    day, date = fetchday(session)

    if not os.path.exists("./saved/prevtable.html"):
        with open('./saved/prevtable.html', 'w') as f:
            prevtable = ""
            pass
    else:
        with open('./saved/prevtable.html', 'r') as f:
            prevtable = f.read()
            f.close()

    if prevtable == str(plan):
        print("Nothing changed exiting")
        quit()

    df = fetchdf(plan) # Gotta be removed

    rows = fetchrows(df) # Gotta be removed

    notify(rows, day, date) # Gotta be removed

    save(str(plan))


if __name__ == "__main__":
    main()
