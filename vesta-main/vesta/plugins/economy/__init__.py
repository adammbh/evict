import random, asyncio

from discord import Embed, Message, User, Attachment

from discord.ext.commands import command, Cog, Author, group, cooldown, BucketType

from datetime import datetime, timedelta

from vesta.framework import Vesta, Context
from vesta.framework.discord.checks import has_economy, has_company

from .blackjack import BlackjackGame, BlackjackView, create_active_embed
from .classes import EconomyUser, Amount, BankAmount, BusinessAmount, BusinessMember


class Economy(Cog):
    def __init__(self, bot: Vesta):
        self.bot = bot

    @command()
    async def start(self, ctx: Context) -> Message:
        """
        Start your economy account
        """
        record = await self.bot.pool.fetchrow(
            """
            SELECT user_id FROM economy 
            WHERE user_id = $1
            """,
            ctx.author.id,
        )
        if record:
            return await ctx.embed("You already have an economy account!", "warned")

        await self.bot.pool.execute(
            """
            INSERT INTO economy (user_id, wallet, bank, daily, monthly, yearly) 
            VALUES ($1, 1000, 0, $2, $2, $2)
            """,
            ctx.author.id,
            datetime.min,
        )
        return await ctx.embed(
            "Account created with $1,000 wallet balance!", "approved"
        )

    @command(aliases=["bal"])
    @has_economy()
    async def balance(self, ctx: Context, member: User = Author) -> Message:
        """
        Check your balance
        """
        record = await self.bot.pool.fetchrow(
            """
            SELECT wallet, bank, created_at 
            FROM economy WHERE user_id = $1
            """,
            member.id,
        )

        embed = Embed(
            description=(
                f">>> **Wallet:** ${record['wallet']:,}\n"
                f"**Bank:** ${record['bank']:,}\n"
                f"-# **Created:** <t:{int(record['created_at'].timestamp())}:R>"
            )
        )

        embed.set_author(
            name=f"{member.display_name}'s balance"
            if member.id != ctx.author.id
            else "Your balance",
            icon_url=member.display_avatar.url,
        )

        return await ctx.send(embed=embed)

    @command(aliases=["give"])
    @has_economy()
    async def transfer(self, ctx: Context, user: EconomyUser, amount: Amount):
        """
        Transfer money to another user
        """
        await ctx.prompt(f"Transfer **${amount:,}** to {user.mention}?")

        await self.bot.pool.execute(
            "UPDATE economy SET wallet = wallet - $1 WHERE user_id = $2",
            amount,
            ctx.author.id,
        )
        await self.bot.pool.execute(
            "UPDATE economy SET wallet = wallet + $1 WHERE user_id = $2",
            amount,
            user.id,
        )

        return await ctx.embed(
            f"Transferred **${amount:,}** to {user.mention}!", "approved"
        )

    @command()
    @has_economy()
    async def daily(self, ctx: Context) -> Message:
        """
        Claim your daily reward (increases 25% per each streak).
        This streak doesn't reset.
        """
        record = await self.bot.pool.fetchrow(
            "SELECT daily, daily_streak FROM economy WHERE user_id = $1", ctx.author.id
        )

        last_daily = record["daily"]
        streak = record["daily_streak"]

        if last_daily.date() == datetime.utcnow().date():
            return await ctx.embed(
                "You've already claimed your daily reward today!", "warned"
            )

        base_reward = 5000
        reward = int(base_reward * (1.25**streak))

        if (datetime.utcnow() - last_daily).days == 1:
            streak += 1

        await self.bot.pool.execute(
            """
            UPDATE economy 
            SET wallet = wallet + $1, daily = $2, daily_streak = $3
            WHERE user_id = $4
            """,
            reward,
            datetime.utcnow(),
            streak,
            ctx.author.id,
        )

        return await ctx.embed(
            f"Claimed **${reward:,}** as your daily reward!", "approved"
        )

    @command()
    @has_economy()
    async def monthly(self, ctx: Context) -> Message:
        """
        Claim your monthly reward (increases 35% per each streak).
        """
        record = await self.bot.pool.fetchrow(
            "SELECT monthly, monthly_streak FROM economy WHERE user_id = $1",
            ctx.author.id,
        )

        last_monthly = record["monthly"]
        streak = record["monthly_streak"]

        if last_monthly and (datetime.utcnow() - last_monthly).days < 30:
            return await ctx.embed(
                "You've already claimed your monthly reward this month!", "warned"
            )

        base_reward = 15000
        reward = int(base_reward * (1.35**streak))

        if last_monthly and (datetime.utcnow() - last_monthly).days <= 31:
            streak += 1
        else:
            streak = 0

        await self.bot.pool.execute(
            """
            UPDATE economy 
            SET wallet = wallet + $1, monthly = $2, monthly_streak = $3
            WHERE user_id = $4
            """,
            reward,
            datetime.utcnow(),
            streak,
            ctx.author.id,
        )

        return await ctx.embed(
            f"Claimed **${reward:,}** as your monthly reward!", "approved"
        )

    @command()
    @has_economy()
    async def yearly(self, ctx: Context) -> Message:
        """
        Claim your yearly reward (increases 50% per each streak).
        """
        record = await self.bot.pool.fetchrow(
            "SELECT yearly, yearly_streak FROM economy WHERE user_id = $1",
            ctx.author.id,
        )

        last_yearly = record["yearly"]
        streak = record["yearly_streak"]

        if last_yearly and (datetime.utcnow() - last_yearly).days < 365:
            return await ctx.embed(
                "You've already claimed your yearly reward this year!", "warned"
            )

        base_reward = 50000
        reward = int(base_reward * (1.50**streak))

        if last_yearly and (datetime.utcnow() - last_yearly).days <= 366:
            streak += 1
        else:
            streak = 0

        await self.bot.pool.execute(
            """
            UPDATE economy 
            SET wallet = wallet + $1, yearly = $2, yearly_streak = $3
            WHERE user_id = $4
            """,
            reward,
            datetime.utcnow(),
            streak,
            ctx.author.id,
        )

        return await ctx.embed(
            f"Claimed **${reward:,}** as your yearly reward!", "approved"
        )

    @command(aliases=["dep"])
    @has_economy()
    async def deposit(self, ctx: Context, amount: Amount) -> Message:
        """
        Deposit money into your bank.
        """
        await self.bot.pool.execute(
            "UPDATE economy SET wallet = wallet - $1, bank = bank + $1 WHERE user_id = $2",
            amount,
            ctx.author.id,
        )

        return await ctx.embed(f"Deposited **${amount:,}** into your bank!", "approved")

    @command(aliases=["with"])
    @has_economy()
    async def withdraw(self, ctx: Context, amount: BankAmount) -> Message:
        """
        Withdraw money from your bank.
        """
        await self.bot.pool.execute(
            "UPDATE economy SET wallet = wallet + $1, bank = bank - $1 WHERE user_id = $2",
            amount,
            ctx.author.id,
        )

        return await ctx.embed(f"Withdrew **${amount:,}** from your bank!", "approved")

    @group(aliases=["lb"], invoke_without_command=True)
    async def leaderboard(self, ctx: Context) -> Message:
        """
        View the economy leaderboard.
        """
        records = await self.bot.pool.fetch(
            """
            SELECT user_id, wallet, bank, anonymous 
            FROM economy 
            WHERE (wallet + bank) > 0
            ORDER BY (wallet + bank) DESC 
            LIMIT 50
            """
        )

        if not records:
            return await ctx.embed("No economy accounts found!", "warned")

        leaderboard = []
        for record in records:
            total_balance = record["wallet"] + record["bank"]
            if record["anonymous"]:
                leaderboard.append(f"*Anonymous user* - **${total_balance:,}**")
            else:
                user = self.bot.get_user(record["user_id"])
                leaderboard.append(
                    f"{user.name if user else 'Unknown User'} - **${total_balance:,}**"
                )

        embed = Embed(title="Global Leaderboard")
        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )
        embed.set_footer(
            text=f"Top {len(leaderboard)} users",
            icon_url=ctx.bot.user.display_avatar.url,
        )

        return await ctx.paginate(leaderboard, embed=embed)

    @leaderboard.command(name="wallet")
    async def leaderboard_wallet(self, ctx: Context) -> Message:
        """
        View the top 50 economy users by wallet balance.
        """
        records = await self.bot.pool.fetch(
            """
            SELECT user_id, wallet, anonymous 
            FROM economy 
            WHERE wallet > 0
            ORDER BY wallet DESC 
            LIMIT 50
            """
        )

        if not records:
            return await ctx.embed("No economy accounts found!", "warned")

        leaderboard = []
        for record in records:
            if record["anonymous"]:
                leaderboard.append(f"*Anonymous user* - **${record['wallet']:,}**")
            else:
                user = self.bot.get_user(record["user_id"])
                leaderboard.append(
                    f"{user.name if user else 'Unknown User'} - **${record['wallet']:,}**"
                )

        embed = Embed(title="Wallet Leaderboard")
        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )
        embed.set_footer(
            text=f"Top {len(leaderboard)} users",
            icon_url=ctx.bot.user.display_avatar.url,
        )

        return await ctx.paginate(leaderboard, embed=embed)

    @leaderboard.command(name="bank")
    async def leaderboard_bank(self, ctx: Context) -> Message:
        """
        View the top 50 economy users by bank balance.
        """
        records = await self.bot.pool.fetch(
            """
            SELECT user_id, bank, anonymous 
            FROM economy 
            WHERE bank > 0
            ORDER BY bank DESC 
            LIMIT 50
            """
        )

        if not records:
            return await ctx.embed("No economy accounts found!", "warned")

        leaderboard = []
        for record in records:
            if record["anonymous"]:
                leaderboard.append(f"*Anonymous user* - **${record['bank']:,}**")
            else:
                user = self.bot.get_user(record["user_id"])
                leaderboard.append(
                    f"{user.name if user else 'Unknown User'} - **${record['bank']:,}**"
                )

        embed = Embed(title="Bank Leaderboard")
        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )
        embed.set_footer(
            text=f"Top {len(leaderboard)} users",
            icon_url=ctx.bot.user.display_avatar.url,
        )

        return await ctx.paginate(leaderboard, embed=embed)

    @leaderboard.command(name="server")
    async def leaderboard_server(self, ctx: Context) -> Message:
        """
        View the top 15 economy users in the server.
        """
        records = await self.bot.pool.fetch(
            """
            SELECT user_id, wallet, bank 
            FROM economy 
            WHERE user_id = ANY($1::bigint[]) AND (wallet + bank) > 0
            ORDER BY (wallet + bank) DESC 
            LIMIT 15
            """,
            [member.id for member in ctx.guild.members],
        )

        if not records:
            return await ctx.embed(
                "No economy accounts found in this server!", "warned"
            )

        leaderboard = []
        for record in records:
            user = ctx.guild.get_member(record["user_id"])
            if not user:
                continue
            total_balance = record["wallet"] + record["bank"]
            leaderboard.append(f"{user.name} - **${total_balance:,}**")

        embed = Embed(title="Server Leaderboard")
        embed.set_footer(
            text=f"Top {len(leaderboard)} members",
            icon_url=ctx.guild.icon.url if ctx.guild.icon else None,
        )
        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )

        return await ctx.paginate(leaderboard, embed=embed)

    @leaderboard.command(name="anonymous")
    async def leaderboard_anonymous(self, ctx: Context, option: str) -> Message:
        """
        Toggle anonymity in the leaderboard (doesn't apply for the server leaderboard).
        """
        if option.lower() not in ["enable", "disable"]:
            return await ctx.embed("Use `enable` or `disable`", "warned")

        is_anonymous = option.lower() == "enable"
        await self.bot.pool.execute(
            """UPDATE economy SET anonymous = $1 
            WHERE user_id = $2
            """,
            is_anonymous,
            ctx.author.id,
        )

        await ctx.embed(
            f"Your leaderboard visibility is now **{'anonymous' if is_anonymous else 'visible'}**",
            "approved",
        )

    @command(aliases=["bj"])
    @has_economy()
    @cooldown(1, 4, BucketType.user)
    async def blackjack(self, ctx: Context, amount: Amount) -> Message:
        """
        Start a blackjack game.
        """
        game = BlackjackGame(amount)
        view = BlackjackView(ctx, game)
        view.message = await ctx.send(embed=create_active_embed(ctx, game), view=view)

    @command(name="gamble")
    @has_economy()
    @cooldown(1, 3, BucketType.user)
    async def gamble(self, ctx: Context, amount: Amount) -> Message:
        """
        Gamble your money in a 50/50 chance.
        """
        if random.random() < 0.5:
            await self.bot.pool.execute(
                "UPDATE economy SET wallet = wallet + $1 WHERE user_id = $2",
                amount,
                ctx.author.id,
            )
            return await ctx.embed(f"You won **${amount:,}**!", "neutral")
        else:
            await self.bot.pool.execute(
                "UPDATE economy SET wallet = wallet - $1 WHERE user_id = $2",
                amount,
                ctx.author.id,
            )
            return await ctx.embed(f"You lost **${amount:,}**!", "neutral", tip="Stop gambling dude!")

    @command()
    @has_economy()
    @cooldown(1, 5, BucketType.user)
    async def slots(self, ctx: Context, amount: Amount) -> Message:
        """
        Spin the slots.
        """
        symbols = ["🍆", "🍒", "🍋", "🔔", "⭐", "7️⃣"]
        result = [random.choice(symbols) for _ in range(3)]

        embed = Embed(
            description=(
                f"**`___SLOTS___`**\n`  {result[0]}   `\n`|         |`\n`|         |`"
            )
        )

        embed2 = Embed(
            description=(
                "**`___SLOTS___`**\n"
                f"`  {result[0]} {result[1]}  `\n"
                "`|         |`\n"
                "`|         |`"
            )
        )

        msg = await ctx.send(embed=embed)
        await asyncio.sleep(1)
        await msg.edit(embed=embed2)

        await asyncio.sleep(1)
        edit = (
            "**`___SLOTS___`**\n"
            f"`  {result[0]} {result[1]} {result[2]} `\n"
            "`|         |`"
        )

        if result[0] == result[1] == result[2]:
            await self.bot.pool.execute(
                "UPDATE economy SET wallet = wallet + $1 WHERE user_id = $2",
                amount * 2,
                ctx.author.id,
            )
            edit += f"   and won ${amount * 2:,}\n"
        else:
            await self.bot.pool.execute(
                "UPDATE economy SET wallet = wallet - $1 WHERE user_id = $2",
                amount,
                ctx.author.id,
            )
            edit += f"   and lost ${amount:,}\n"

        edit += "`|         |`"
        return await msg.edit(embed=Embed(description=edit))

    @command(aliases=["cf"])
    @has_economy()
    @cooldown(1, 5, BucketType.user)
    async def coinflip(self, ctx: Context, amount: Amount) -> Message:
        """
        Flip a coin.
        """
        msg = await ctx.send(f"Flipping coin.... {ctx.config.emojis.economy.coin}")
        await asyncio.sleep(1.5)

        result = random.choice(["heads", "tails"])
        win = random.random() < 0.5

        if win:
            await self.bot.pool.execute(
                "UPDATE economy SET wallet = wallet + $1 WHERE user_id = $2",
                amount * 2,
                ctx.author.id,
            )
            outcome = f"won ${amount * 2:,}!"
        else:
            await self.bot.pool.execute(
                "UPDATE economy SET wallet = wallet - $1 WHERE user_id = $2",
                amount,
                ctx.author.id,
            )
            outcome = f"lost ${amount:,}"

        return await msg.edit(
            content=(f"The coin landed on **{result}**\nand you **{outcome}**")
        )

    @group(aliases=["company"], invoke_without_command=True)
    async def business(self, ctx: Context) -> Message:
        """
        Manage your business.
        """
        return await ctx.send_help(ctx.command)

    @business.command()
    @has_company()
    async def info(self, ctx: Context) -> Message:
        """
        View business info.
        """
        res = await self.bot.pool.fetchrow(
            "SELECT name, funds, thumbnail_url, created_at FROM businesses WHERE owner_id = $1 AND guild_id = $2",
            ctx.author.id, ctx.guild.id
        )
        
        embed = Embed(
            description=(
                f">>> **Founder**: {ctx.author.name}\n" 
                f"**Funds**: ${res['funds']:,}\n" 
                f"**Created**: <t:{int(res['created_at'].timestamp())}:R>")
        )
        embed.set_author(name=res["name"], icon_url=res["thumbnail_url"])
        return await ctx.send(embed=embed)

    @business.command(name="create")
    async def create(self, ctx: Context, *, name: str) -> Message:
        """
        Create business ($1M cost).
        """
        if len(name.split()) > 20:
            return await ctx.embed("Max 20 words!", "warned")
        
        if await self.bot.pool.fetchrow("SELECT 1 FROM businesses WHERE guild_id = $1 AND name = $2", ctx.guild.id, name):
            return await ctx.embed("Name taken!", "warned")
        
        if await self.bot.pool.fetchval("SELECT wallet FROM economy WHERE user_id = $1", ctx.author.id) < 1_000_000:
            return await ctx.embed("Need $1M!", "warned")
        
        await self.bot.pool.execute(
            "UPDATE economy SET wallet = wallet - 1000000 WHERE user_id = $1",
            ctx.author.id
        )
        await self.bot.pool.execute(
            "INSERT INTO businesses (owner_id, guild_id, name, created_at) VALUES ($1, $2, $3, $4)",
            ctx.author.id, ctx.guild.id, name[:100], datetime.utcnow()
        )
        return await ctx.embed(f"Created **{name[:100]}**!", "approved")

    @business.command()
    @has_company()
    async def icon(self, ctx: Context, image: Attachment) -> Message:
        """
        Set the business's icon.
        """
        if not image.content_type.startswith("image/"):
            return await ctx.embed("Send an image", "warned")
        
        await self.bot.pool.execute(
            "UPDATE businesses SET thumbnail_url = $1 WHERE owner_id = $2 AND guild_id = $3",
            image.url, ctx.author.id, ctx.guild.id
        )
        return await ctx.embed("Updated icon!", "approved")

    @business.command()
    @has_company()
    async def delete(self, ctx: Context) -> Message:
        """
        Delete your business.
        """
        await ctx.prompt("Do you want to delete your business permanently?")
        await self.bot.pool.execute(
            "DELETE FROM businesses WHERE owner_id = $1 AND guild_id = $2",
            ctx.author.id, ctx.guild.id
        )
        return await ctx.embed("Business deleted!", "approved")

    @business.group(aliases=["funds"], invoke_without_command=True)
    @has_company()
    async def vault(self, ctx: Context) -> Message:
        """
        Manage business funds.
        """
        funds = await self.bot.pool.fetchval(
            "SELECT funds FROM businesses WHERE owner_id = $1 AND guild_id = $2",
            ctx.author.id, ctx.guild.id
        )
        return await ctx.embed(f"Vault: ${funds:,}", "neutral")

    @vault.command()
    @has_company()
    async def deposit(self, ctx: Context, amount: Amount) -> Message:
        """
        Deposit money to the company's vault.
        """
        await self.bot.pool.execute(
            "UPDATE economy SET wallet = wallet - $1 WHERE user_id = $2",
            amount, ctx.author.id
        )
        await self.bot.pool.execute(
            "UPDATE businesses SET funds = funds + $1 WHERE owner_id = $2 AND guild_id = $3",
            amount, ctx.author.id, ctx.guild.id
        )
        return await ctx.embed(f"Deposited ${amount:,}!", "approved")

    @vault.command()
    @has_company()
    async def withdraw(self, ctx: Context, amount: BusinessAmount) -> Message:
        """
        Withdraw money from the company's vault.
        """
        await self.bot.pool.execute(
            "UPDATE businesses SET funds = funds - $1 WHERE owner_id = $2 AND guild_id = $3",
            amount, ctx.author.id, ctx.guild.id
        )
        await self.bot.pool.execute(
            "UPDATE economy SET wallet = wallet + $1 WHERE user_id = $2",
            amount, ctx.author.id
        )
        return await ctx.embed(f"Withdrew ${amount:,}!", "approved")

    @business.group(invoke_without_command=True)
    @has_company()
    async def jobs(self, ctx: Context) -> Message:
        """
        Manage jobs.
        """
        return await ctx.send_help(ctx.command)

    @jobs.command(name="create")
    @has_company()
    async def create_job(self, ctx: Context, name: str, visibility: str, salary: BusinessAmount) -> Message:
        """
        Create job (3x salary cost).
        """
        if len(name.split()) > 10:
            return await ctx.embed("Max 10 words!", "warned")
        
        biz = await self.bot.pool.fetchrow(
            "SELECT id, funds FROM businesses WHERE owner_id = $1 AND guild_id = $2",
            ctx.author.id, ctx.guild.id
        )
        cost = salary * 3
        
        if biz["funds"] < cost:
            return await ctx.embed(f"Need ${cost:,} in vault!", "warned")
        
        await self.bot.pool.execute(
            "UPDATE businesses SET funds = funds - $1 WHERE id = $2",
            cost, biz["id"]
        )
        await self.bot.pool.execute(
            "INSERT INTO jobs (business_id, name, visibility, salary) VALUES ($1, $2, $3, $4)",
            biz["id"], name[:50], visibility.lower(), salary
        )
        return await ctx.embed(f"Created the **{name}** job (${salary:,})!", "approved")

    @jobs.command(name="delete")
    @has_company()
    async def delete_job(self, ctx: Context, *, name: str) -> Message:
        """
        Delete job.
        """
        job = await self.bot.pool.fetchrow(
            """SELECT id FROM jobs 
            JOIN businesses ON jobs.business_id = businesses.id
            WHERE jobs.name = $1 AND businesses.owner_id = $2 AND businesses.guild_id = $3""",
            name, ctx.author.id, ctx.guild.id
        )
        
        if not job:
            return await ctx.embed("Job not found!", "warned")
        
        await self.bot.pool.execute("DELETE FROM workers WHERE job_id = $1", job["id"])
        await self.bot.pool.execute("DELETE FROM jobs WHERE id = $1", job["id"])
        return await ctx.embed(f"Deleted **{name}**!", "approved")

    @jobs.command(name="list")
    @has_company()
    async def list_jobs(self, ctx: Context) -> Message:
        """
        List company jobs.
        """
        jobs = await self.bot.pool.fetch(
            """SELECT j.name, j.salary, j.visibility, COUNT(w.user_id) as workers
            FROM jobs j
            LEFT JOIN workers w ON j.id = w.job_id
            WHERE j.business_id = (SELECT id FROM businesses WHERE owner_id = $1 AND guild_id = $2)
            GROUP BY j.id""",
            ctx.author.id, ctx.guild.id
        )
        
        if not jobs:
            return await ctx.embed("No jobs!", "info")
        
        entries = [f"**{j['name']}** (${j['salary']:,}) [{j['visibility']}] - {j['workers']} workers" for j in jobs]
        return await ctx.paginate(entries, title=f"Jobs in {ctx.author.display_name}'s Company")

    @business.command(name="employees", aliases=["workers"])
    @has_company()
    async def show_employees(self, ctx: Context) -> Message:
        """
        List employees.
        """
        employees = await self.bot.pool.fetch(
            """SELECT w.user_id, j.name as role
            FROM workers w
            JOIN jobs j ON w.job_id = j.id
            WHERE j.business_id = (SELECT id FROM businesses WHERE owner_id = $1 AND guild_id = $2)""",
            ctx.author.id, ctx.guild.id
        )
        
        if not employees:
            return await ctx.embed("No employees!", "info")
        
        entries = []
        for e in employees:
            user = ctx.guild.get_member(e["user_id"])
            entries.append(f"**{user.display_name if user else 'Unknown'}** - {e['role']}")
        
        return await ctx.paginate(entries, title=f"Employees of {ctx.author.display_name}'s Company")

    @business.command(name="hire")
    @has_company()
    async def hire(self, ctx: Context, user: EconomyUser, *, name: str) -> Message:
        """
        Hire someone.
        """
        if await self.bot.pool.fetchval("SELECT 1 FROM workers WHERE user_id = $1 AND guild_id = $2", user.id, ctx.guild.id):
            return await ctx.embed(f"**{user}** already employed!", "warned")
        
        job = await self.bot.pool.fetchrow(
            """SELECT id FROM jobs 
            JOIN businesses ON jobs.business_id = businesses.id
            WHERE jobs.name = $1 AND businesses.owner_id = $2 AND businesses.guild_id = $3""",
            name, ctx.author.id, ctx.guild.id
        )
        
        await self.bot.pool.execute(
            "INSERT INTO workers (user_id, guild_id, job_id) VALUES ($1, $2, $3)",
            user.id, ctx.guild.id, job["id"]
        )
        return await ctx.embed(f"Hired {user.mention} as **{name}**!", "approved")

    @business.command(name="fire")
    @has_company()
    async def fire(self, ctx: Context, user: BusinessMember) -> Message:
        """
        Fire employee.
        """
        job = await self.bot.pool.fetchrow(
            "SELECT name FROM jobs JOIN workers ON jobs.id = workers.job_id WHERE workers.user_id = $1",
            user.id
        )
        
        await ctx.prompt(f"Fire {user.mention} from **{job['name']}**?")
        await self.bot.pool.execute(
            "DELETE FROM workers WHERE user_id = $1 AND guild_id = $2",
            user.id, ctx.guild.id
        )
        return await ctx.embed(f"You fired {user.mention}!", "approved")

    @group(invoke_without_command=True)
    async def job(self, ctx: Context) -> Message:
        """
        Job commands.
        """
        return await ctx.send_help(ctx.command)

    @job.command()
    async def apply(self, ctx: Context, name: str) -> Message:
        """
        Apply for job.
        """
        job = await self.bot.pool.fetchrow(
            """SELECT owner_id, visibility FROM jobs 
            JOIN businesses ON jobs.business_id = businesses.id
            WHERE jobs.name = $1 AND businesses.guild_id = $2""",
            name, ctx.guild.id
        )
        
        if not job or job["visibility"] == "private":
            return await ctx.embed("Job not found!", "warned")
        
        owner = ctx.guild.get_member(job["owner_id"])
        try:
            await owner.send(f"{ctx.author.mention} applied for {name}!")
            return await ctx.embed("Application sent!", "approved")
        except:
            return await ctx.embed(f"Couldn't DM {owner.mention}, please contact them directly", "warned")

    @job.command()
    async def list(self, ctx: Context) -> Message:
        """
        List public jobs.
        """
        jobs = await self.bot.pool.fetch(
            """SELECT j.name, b.name as company, j.salary
            FROM jobs j
            JOIN businesses b ON j.business_id = b.id
            WHERE b.guild_id = $1 AND j.visibility = 'public'""",
            ctx.guild.id
        )
        
        if not jobs:
            return await ctx.embed("There are no jobs available!", "info")
        
        entries = [f"**{j['name']}** at {j['company']} (${j['salary']:,})" for j in jobs]
        return await ctx.paginate(entries, title=f"Jobs in {ctx.guild.name}")

    @job.command(aliases=["quit"])
    async def resign(self, ctx: Context) -> Message:
        """
        Quit your job.
        """
        await ctx.prompt("Quit your job?")
        await self.bot.pool.execute(
            "DELETE FROM workers WHERE user_id = $1",
            ctx.author.id
        )
        return await ctx.embed("You quit your job!", "approved")
    
    @command()
    async def work(self, ctx: Context) -> Message:
        """
        Work at your job (3h cooldown).
        """
        res = await self.bot.pool.fetchrow(
            """SELECT j.salary, w.last_worked, j.business_id, w.job_id
            FROM workers w
            JOIN jobs j ON w.job_id = j.id
            WHERE w.user_id = $1 AND w.guild_id = $2""",
            ctx.author.id, ctx.guild.id
        )
        
        if not res:
            return await ctx.embed("You don't have a job!", "warned")
        
        if res["last_worked"]:
            cd = timedelta(hours=3) - (datetime.utcnow() - res["last_worked"])
            if cd.total_seconds() > 0:
                h, m = divmod(int(cd.total_seconds()), 3600)
                m //= 60
                return await ctx.embed(f"Cooldown: {h}h {m}m left", "warned")
        
        gain = res["salary"]
        cut = gain // 10
        
        await self.bot.pool.execute(
            "UPDATE economy SET wallet = wallet + $1 WHERE user_id = $2",
            gain, ctx.author.id
        )
        await self.bot.pool.execute(
            "UPDATE businesses SET funds = funds + $1 WHERE id = $2",
            cut, res["business_id"]
        )
        await self.bot.pool.execute(
            "UPDATE workers SET last_worked = $1 WHERE user_id = $2 AND job_id = $3",
            datetime.utcnow(), ctx.author.id, res["job_id"]
        )
        return await ctx.embed(f"Earned ${gain:,}! Company got ${cut:,}", "approved")

async def setup(bot: Vesta) -> None:
    await bot.add_cog(Economy(bot))