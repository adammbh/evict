import random

from discord import ButtonStyle, Interaction, Embed, Message

from discord.ui import View, button

from vesta.framework import Context
from typing import Optional, List, Tuple, Dict


class Deck:
    def __init__(self):
        self.cards = []
        ranks = [
            ("A", 11),
            ("2", 2),
            ("3", 3),
            ("4", 4),
            ("5", 5),
            ("6", 6),
            ("7", 7),
            ("8", 8),
            ("9", 9),
            ("10", 10),
            ("J", 10),
            ("Q", 10),
            ("K", 10),
        ]
        suits = ["♠", "♥", "♦", "♣"]

        for suit in suits:
            for rank, value in ranks:
                self.cards.append((f"{rank}{suit}", value))
        random.shuffle(self.cards)

    def draw(self) -> Tuple[str, int]:
        return self.cards.pop()


def hand_value(hand: List[Tuple[str, int]]) -> int:
    total = sum(card[1] for card in hand)
    aces = sum(1 for card in hand if card[1] == 11)

    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total


class BlackjackGame:
    def __init__(self, bet: int):
        self.bet = bet
        self.deck = Deck()
        self.player_hand = [self.deck.draw(), self.deck.draw()]
        self.dealer_hand = [self.deck.draw(), self.deck.draw()]

    def player_hit(self):
        self.player_hand.append(self.deck.draw())

    def dealer_play(self):
        while hand_value(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deck.draw())

    def calculate_result(self) -> Dict:
        player_total = hand_value(self.player_hand)
        dealer_total = hand_value(self.dealer_hand)

        if player_total > 21:
            return {"outcome": "loss", "multiplier": -1, "message": "You lost!"}
        if dealer_total > 21:
            return {"outcome": "win", "multiplier": 2, "message": "You won!"}
        if player_total > dealer_total:
            return {"outcome": "win", "multiplier": 2, "message": "You won!"}
        if player_total == dealer_total:
            return {"outcome": "push", "multiplier": 1, "message": "It's a tie!"}
        return {"outcome": "loss", "multiplier": -1, "message": "You lost!"}


# ==============================================
# EMBEDS
# ==============================================


def create_active_embed(ctx: Context, game: "BlackjackGame") -> Embed:
    embed = Embed(
        title="Blackjack",
        color=ctx.config.colors.neutral,
        description=f"You Bet ${game.bet:,}",
    )
    embed.set_author(
        name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
    )

    embed.add_field(name="Your Hand", value=format_hand(game.player_hand), inline=True)

    embed.add_field(
        name="Dealer's Hand", value=f"{game.dealer_hand[0][0]} [?]", inline=True
    )
    return embed


def create_result_embed(ctx: Context, game: "BlackjackGame", result: Dict) -> Embed:
    color = {
        "win": ctx.config.colors.approved,
        "loss": ctx.config.colors.warned,
        "push": ctx.config.colors.neutral,
    }[result["outcome"]]

    amount = game.bet * result["multiplier"]
    description = (
        f"You {'won' if result['outcome'] == 'win' else 'lost'} ${abs(amount):,}"
    )

    embed = Embed(title=f"{result['message']}", description=description, color=color)
    embed.set_author(
        name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
    )

    embed.add_field(name="Your Hand", value=format_hand(game.player_hand), inline=True)
    embed.add_field(
        name="Dealer's Hand", value=format_hand(game.dealer_hand), inline=True
    )

    return embed


def format_hand(hand: List[Tuple[str, int]]) -> str:
    cards = " ".join(card[0] for card in hand)
    total = hand_value(hand)
    return f"{cards}\nTotal: {total}"


# ==============================================
# GAME VIEW
# ==============================================


class BlackjackView(View):
    def __init__(self, ctx: Context, game: BlackjackGame):
        super().__init__(timeout=60.0)
        self.ctx = ctx
        self.game = game
        self.message: Optional[Message] = None

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.embed("You are not the author of this embed!")
            return False
        return True

    async def on_timeout(self):
        await self.ctx.bot.pool.execute(
            """
            UPDATE economy SET wallet = wallet - $1 
            WHERE user_id = $2
            """,
            self.game.bet,
            self.ctx.author.id,
        )

        if self.message:
            await self.message.edit(
                content=f"You took too long! You lost ${self.game.bet:,}",
                embed=None,
                view=None,
            )

    async def update_display(self):
        await self.message.edit(
            embed=create_active_embed(self.ctx, self.game), view=self
        )

    async def end_game(self):
        self.stop()
        self.game.dealer_play()
        result = self.game.calculate_result()

        if result["multiplier"] != 0:
            await self.ctx.bot.pool.execute(
                "UPDATE economy SET wallet = wallet + $1 WHERE user_id = $2",
                self.game.bet * result["multiplier"],
                self.ctx.author.id,
            )

        await self.message.edit(
            embed=create_result_embed(self.ctx, self.game, result), view=None
        )

    @button(label="Hit", style=ButtonStyle.green)
    async def hit(self, interaction: Interaction, button: button):
        await interaction.response.defer()
        self.game.player_hit()
        if hand_value(self.game.player_hand) > 21:
            await self.end_game()
        else:
            await self.update_display()

    @button(label="Stay", style=ButtonStyle.red)
    async def stay(self, interaction: Interaction, button: button):
        await interaction.response.defer()
        await self.end_game()


__all__ = [
    "BlackjackGame",
    "BlackjackView",
    "create_active_embed",
    "create_result_embed",
]
