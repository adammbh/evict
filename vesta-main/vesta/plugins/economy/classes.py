from discord.ext.commands import Converter, BadArgument, UserConverter, MemberConverter
from discord import Member

from vesta.framework import Context


class EconomyUser(Converter):
    async def convert(self, ctx: Context, argument: str):
        """
        Converts a string argument to a user object for economy commands.
        """
        try:
            user = await UserConverter().convert(ctx, argument)

        except BadArgument:
            raise BadArgument("Invalid user!")

        if user.bot:
            raise BadArgument("Cannot target bots!")

        if user.id == ctx.author.id:
            raise BadArgument("Cannot transfer to yourself!")

        exists = await ctx.bot.pool.fetchrow(
            """
            SELECT * FROM economy 
            WHERE user_id = $1
            """,
            user.id,
        )
        if not exists:
            raise BadArgument(f"**{user.name}** has no economy account!")
        return user


class BusinessMember(Converter):
    async def convert(self, ctx: Context, arg: str) -> Member:
        """
        Convert to member and validate company employment
        """
        try:
            user = await MemberConverter().convert(ctx, arg)
        except BadArgument:
            raise BadArgument("Invalid user!")
        
        if user.bot:
            raise BadArgument("Can't target bots!")
        
        exists = await ctx.bot.pool.fetchval(
            """SELECT 1 FROM workers w
            JOIN jobs j ON w.job_id = j.id
            JOIN businesses b ON j.business_id = b.id
            WHERE w.user_id = $1 AND b.owner_id = $2""",
            user.id, ctx.author.id
        )
        if not exists:
            raise BadArgument(f"**{user}** doesn't work for you!")
        return user


class Amount(Converter):
    async def convert(self, ctx: Context, argument: str):
        """
        Converts a string argument to an integer amount for economy commands.
        """
        argument = argument.replace(",", "").lower()
        multipliers = {
            "k": 1_000,
            "m": 1_000_000,
            "b": 1_000_000_000,
            "t": 1_000_000_000_000,
        }

        wallet_balance = (
            await ctx.bot.pool.fetchrow(
                "SELECT wallet FROM economy WHERE user_id = $1", ctx.author.id
            )
        )["wallet"]

        if argument in ("all", "max", "everything"):
            if wallet_balance <= 0:
                raise BadArgument("You don't have any money in your wallet!")
            return wallet_balance

        if argument[-1] in multipliers:
            num_part = argument[:-1]
            suffix = argument[-1]
            try:
                amount = int(float(num_part) * multipliers[suffix])
                if amount <= 0:
                    raise BadArgument("Amount must be positive!")
                if amount > wallet_balance:
                    raise BadArgument("You don't have enough money in your wallet!")
                return amount
            except ValueError:
                raise BadArgument("Invalid amount format!")

        try:
            amount = int(argument)
            if amount <= 0:
                raise BadArgument("Amount must be positive!")
            if amount > wallet_balance:
                raise BadArgument("You don't have enough money in your wallet!")
            return amount
        except ValueError:
            raise BadArgument("Invalid amount format!")


class BankAmount(Converter):
    async def convert(self, ctx: Context, argument: str):
        """
        Converts a string argument to an integer amount for economy commands (checks bank balance).
        """
        argument = argument.replace(",", "").lower()
        multipliers = {
            "k": 1_000,
            "m": 1_000_000,
            "b": 1_000_000_000,
            "t": 1_000_000_000_000,
        }

        bank_balance = (
            await ctx.bot.pool.fetchrow(
                "SELECT bank FROM economy WHERE user_id = $1", ctx.author.id
            )
        )["bank"]

        if argument in ("all", "max", "everything"):
            if bank_balance <= 0:
                raise BadArgument("You don't have any money in your bank!")
            return bank_balance

        if argument[-1] in multipliers:
            num_part = argument[:-1]
            suffix = argument[-1]
            try:
                amount = int(float(num_part) * multipliers[suffix])
                if amount <= 0:
                    raise BadArgument("Amount must be positive!")
                if amount > bank_balance:
                    raise BadArgument("You don't have enough money in your bank!")
                return amount
            except ValueError:
                raise BadArgument("Invalid amount format!")

        try:
            amount = int(argument)
            if amount <= 0:
                raise BadArgument("Amount must be positive!")
            if amount > bank_balance:
                raise BadArgument("You don't have enough money in your bank!")
            return amount
        except ValueError:
            raise BadArgument("Invalid amount format!")


class BusinessAmount(Converter):
    async def convert(self, ctx: Context, argument: str):
        """
        Converts a string argument to an integer amount for business commands.
        """
        argument = argument.replace(",", "").lower()
        multipliers = {
            "k": 1_000,
            "m": 1_000_000,
            "b": 1_000_000_000,
            "t": 1_000_000_000_000,
        }

        if argument in ("all", "max", "everything"):
            business_funds = await ctx.bot.pool.fetchval(
                "SELECT funds FROM businesses WHERE owner_id = $1 AND guild_id = $2",
                ctx.author.id,
                ctx.guild.id,
            )
            if business_funds <= 0:
                raise BadArgument("Business vault is empty!")
            return business_funds

        if argument[-1] in multipliers:
            num_part = argument[:-1]
            suffix = argument[-1]
            try:
                return int(float(num_part) * multipliers[suffix])
            except ValueError:
                raise BadArgument("Invalid amount format!")

        try:
            return int(argument)
        except ValueError:
            raise BadArgument("Invalid amount format!")
