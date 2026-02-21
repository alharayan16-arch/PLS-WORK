async def load_extensions():
    try:
        await bot.load_extension("giveaways")
        print("giveaways loaded")

        await bot.load_extension("welcome")
        print("welcome loaded")

        await bot.load_extension("staff")
        print("staff loaded")

        await bot.load_extension("goodbye")
        print("goodbye loaded")

    except Exception as e:
        print("EXTENSION ERROR:", e)