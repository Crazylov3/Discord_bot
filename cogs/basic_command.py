import discord
from discord.ext import commands
import numpy as np
from unidecode import unidecode
from statistics import mode
import json
import requests
from datetime import datetime


def text_city_preprocess(text):
    text1 = "thanh pho " + text
    text2 = "thi xa " + text
    text3 = "tinh " + text
    text4 = "huyen " + text
    text5 = "thu do " + text
    text6 = text + " city"
    text7 = text + " capital"
    text8 = "countryside " + text
    return text, text1, text2, text3, text4, text5, text6, text7, text8


def weather_get_info(content):
    list_day = content['list']
    days = {}
    for i, day_ in enumerate(list_day):
        day = datetime.utcfromtimestamp(day_['dt']).day
        if day not in days.keys():
            days[day] = [i]
        else:
            days[day].append(i)
    info = []
    for d in days.keys():
        dic = {"daytime": datetime.utcfromtimestamp(int(list_day[days[d][0]]['dt'])).strftime('%d/%m/%Y'),
               "temp": round(np.mean([list_day[i]['main']['temp'] for i in days[d]]) - 273),
               "temp_min": round(min([list_day[i]['main']['temp_min'] for i in days[d]]) - 273),
               "temp_max": round(max([list_day[i]['main']['temp_max'] for i in days[d]]) - 273),
               "humidity": round(np.mean([list_day[i]['main']['humidity'] for i in days[d]]), 2),
               "weather_des": mode([list_day[i]["weather"][0]["description"] for i in days[d]]),
               "wind_speed": round(np.mean([list_day[i]['wind']['speed'] for i in days[d]]), 2),
               "wind_gust": max([list_day[i]['wind']['gust'] for i in days[d]]), "city_name": content['city']['name']}
        info.append(dic)
    return info[:4]


class Basic_command(commands.Cog):
    def __init__(self, client):
        self.client = client
    @commands.command()
    async def clear(self,ctx,amount=50):
        await ctx.channel.purge(limit = amount)

    @commands.command()
    async def girl(self, ctx):
        async with ctx.channel.typing():
            while True:
                try:
                    id = np.random.randint(0, 1378)
                    embed = discord.Embed(title="Gái ...🤤", colour=ctx.guild.me.colour)
                    embed.set_image(
                        url=f"https://raw.githubusercontent.com/Crazylov3/Photo-Libary/main/Photos/{id}.png")
                    await ctx.send(embed=embed)
                    break
                except:
                    pass

    @commands.command()
    async def weather(self, ctx, *, city: str):
        async with ctx.channel.typing():
            city_decode_string = unidecode(city.strip().lower())
            with open("list_city_code.json", "r", encoding="utf-8") as j:
                file = json.load(j)
            city_name = text_city_preprocess(city_decode_string)
            for name in city_name:
                if name in file.keys():
                    city_code = file[name]
                    url = f"https://api.openweathermap.org/data/2.5/forecast?id={city_code}&APPID" \
                          f"=cd345a07012bfa798d77ab7e594ad2b2"
                    content = requests.get(url).json()
                    info = weather_get_info(content)
                    embed = discord.Embed(
                        description=f"```fix\nWeather forecast for {info[0]['city_name']}\n```",
                        colour=ctx.guild.me.colour
                    )
                    for day in info:
                        embed.add_field(name=f"{day['daytime']}",
                                        value=f" Weather: {day['weather_des']}\nTemperature: {day['temp']}°C ({day['temp_min']}°C - {day['temp_max']}°C)" 
                                              f"\nHumidity: {day['humidity']}%"
                                              f"\nWind speed: {day['wind_speed']} m/s  " + "|" + f"  Wind gust: {day['wind_gust']} m/s",
                                        inline=False
                                        )

                    # embed.set_footer(text=f"Invoked by {ctx.author.display_name}", icon_url=ctx.author.avatar_url)
                    await ctx.reply(embed=embed, mention_author=False, delete_after=120)
                    return
            await ctx.reply(content="**Invalid city name**\n *\\Try to use another name\\*", mention_author=False,
                            delete_after=60)


def setup(client):
    client.add_cog(Basic_command(client))
