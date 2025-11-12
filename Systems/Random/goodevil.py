import discord
from discord.ext import commands
import aiohttp
import asyncio
import json
import random
import time
import os
from config import GROQ_API_KEY


class GoodEvilSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name='roast', description='Get roasted by the bot! (Use at your own risk)')
    @discord.app_commands.describe(
        target="The user to roast (optional - defaults to yourself)",
        category="Choose roast type: Mild, Intellectual, Savage, Dark Humor, NSFW (Cursing), or Insane (Nonsense)",
        style="Choose output style: Old Time (Shakespeare), Slang, Southern (USA), Cockney, Robot, Pirate, Yoda, or Elvish (Sindarin)"
    )
    @discord.app_commands.choices(category=[
        discord.app_commands.Choice(name="Mild", value="mild"),
        discord.app_commands.Choice(name="Intellectual", value="intellectual"),
        discord.app_commands.Choice(name="Savage", value="savage"),
        discord.app_commands.Choice(name="Dark Humor", value="dark_humor"),
        discord.app_commands.Choice(name="NSFW", value="nsfw"),
        discord.app_commands.Choice(name="Insane", value="insane")
    ])
    @discord.app_commands.choices(style=[
        discord.app_commands.Choice(name="Old Time", value="old_time"),
        discord.app_commands.Choice(name="Slang", value="slang"),
        discord.app_commands.Choice(name="Southern", value="southern"),
        discord.app_commands.Choice(name="Cockney", value="cockney"),
        discord.app_commands.Choice(name="Robot", value="robot"),
        discord.app_commands.Choice(name="Pirate", value="pirate"),
        discord.app_commands.Choice(name="Yoda", value="yoda"),
        discord.app_commands.Choice(name="Elvish", value="elvish")
    ])
    async def roast(self, ctx: commands.Context, target: discord.Member = None, category: str = "insane", style: str = "robot"):
        """Get roasted by the bot"""
        
        
        try:
            # Defer the interaction to prevent timeout
            await ctx.defer()
            
            # Determine target
            if target is None:
                target = ctx.author
                target_name = ctx.author.display_name
                target_mention = ctx.author.mention
                target_avatar = ctx.author.display_avatar.url
            else:
                target_name = target.display_name
                target_mention = target.mention
                target_avatar = target.display_avatar.url
            
            # Helper: Generate roast via GROQ Chat Completions
            async def generate_groq_roast(category: str, style: str, subject_name: str, user_text: str | None = None):
                api_key = GROQ_API_KEY
                if not api_key:
                    print("GROQ_API_KEY missing; skipping Groq roast generation.")
                    return None
                style_instructions = {
                    "old_time": "Write in Shakespearean/Old English tone.",
                    "slang": "Use modern slang.",
                    "southern": "Use Southern USA colloquial tone.",
                    "cockney": "Use Cockney London slang and phrasing.",
                    "robot": "Write like a formal robot using technical jargon.",
                    "pirate": "Use pirate speak and nautical idioms.",
                    "yoda": "Speak like Yoda with inverted grammar.",
                    "elvish": "Use Sindarin-inspired poetic Elvish tone.",
                }.get(style, "Write in a straightforward modern tone.")
                category_instructions = {
                    "mild": "Gentle, light-hearted tease.",
                    "intellectual": "Clever, smart roast using witty logic or analogies.",
                    "savage": "Brutal, cutting roast.",
                    "dark_humor": "Edgy roast with dark humor.",
                    "nsfw": "Include cursing and explicit language.",
                    "insane": "Absurd, surreal nonsense roast with wild metaphors.",
                    "user": "Use the provided custom text as the subject and craft a specific roast about it.",
                }.get(category, "Generate a roast.")
                prompt_subject = user_text if (category == "user" and user_text) else subject_name
                system_prompt = (
                    "Discord roast bot. Output 1–2 sentences."
                )
                user_prompt = (
                    f"Subject: {prompt_subject}\n"
                    f"Roast type: {category_instructions}\nStyle: {style_instructions}\n"
                    "Return only the roast text."
                )
                try:
                    timeout = aiohttp.ClientTimeout(total=45)
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        url = "https://api.groq.com/openai/v1/chat/completions"
                        headers = {
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        }
                        payload = {
                            "model": "llama-3.1-8b-instant",
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            "temperature": 0.9,
                            "max_tokens": 60,
                            "top_p": 0.9,
                        }
                        async with session.post(url, headers=headers, json=payload) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                try:
                                    text = data["choices"][0]["message"]["content"].strip()
                                except Exception:
                                    text = None
                                if text:
                                    return {
                                        "roast": text,
                                        "source": "Groq",
                                        "category": category,
                                    }
                            else:
                                body = await resp.text()
                                print(f"Groq roast request failed: HTTP {resp.status} — {body[:300]}")
                except Exception as e:
                    print(f"Groq roast request error: {e}")
                return None

            savage_fallbacks = [
                "You're the reason even autocorrect gave up on hope.",
                "Your brain has buffering issues—and the wheel never stops.",
                "If mediocrity was graded, you'd curve the class down.",
                "I've met paperclips with more backbone than you.",
                "Your logic is so broken it needs a hazard sign.",
            ]
            insane_fallbacks = [
                "You’re the final boss of failure, unpatchable and persistent.",
                "Your presence lowers collective IQ like a distributed denial-of-sense.",
                "You’re a zero-day vulnerability in human decency.",
                "Evolution looked at you and toggled rollback.",
                "You are proof entropy can wear a name tag.",
            ]
            # Legacy 'Yo Momma' fallbacks removed; category no longer supported
            
            # BRUTAL fallback roasts - legacy
            fallback_roasts = [
                "You are the ultimate scourges of the world, the Antichrist together with your sophists and bishops.",
                "Your existence is a monument to everything wrong with humanity - a walking disaster that proves natural selection failed.",
                "I've seen more intelligent life forms growing on expired yogurt than whatever pathetic excuse for consciousness you possess.",
                "You're like a black hole of competence - everything you touch collapses into a singularity of failure and disappointment.",
                "Your family tree must be a circle, because only inbreeding could explain this level of genetic malfunction.",
                "You're the human equivalent of a participation trophy - utterly worthless but somehow still here.",
                "I've encountered used toilet paper with more dignity and purpose than your entire existence.",
                "Your IQ is so low, scientists are studying you as proof that evolution can go backwards.",
                "You're like a software bug that somehow learned to breathe - an error that should have been patched out of existence.",
                "The mere fact that you wake up every morning is an insult to every productive member of society.",
                "I've seen roadkill with more potential and charisma than whatever you call this pathetic display of humanity.",
                "You're the reason why some animals eat their young - nature's way of preventing whatever genetic disaster you represent.",
                "Your thought process is so broken, it makes Windows Vista look like a masterpiece of engineering.",
                "You're living proof that you can't fix stupid, but you can apparently give it internet access.",
                "I've met houseplants with more personality, intelligence, and purpose than your entire being."
            ]
            
            # Try the appropriate API based on category - NO CONTENT FILTERING
            roast_data = None
            apis_tried = []
            
            # Use GROQ to generate roast by category
            if category == "mild":
                roast_data = await generate_groq_roast(category, style, target_name)
                apis_tried.append('Groq Roast (mild)')
            
            elif category == "intellectual":
                roast_data = await generate_groq_roast(category, style, target_name)
                apis_tried.append('Groq Roast (intellectual)')
            
            elif category == "savage":
                roast_data = await generate_groq_roast(category, style, target_name)
                apis_tried.append('Groq Roast (savage)')
            
            elif category == "insane":
                roast_data = await generate_groq_roast(category, style, target_name)
                apis_tried.append('Groq Roast (insane)')
            
            elif category == "dark_humor":
                roast_data = await generate_groq_roast(category, style, target_name)
                apis_tried.append('Groq Roast (dark_humor)')

            elif category == "nsfw":
                roast_data = await generate_groq_roast(category, style, target_name)
                apis_tried.append('Groq Roast (nsfw)')
            elif category == "user":
                # For prefix command usage, prompt for text, then generate via Groq
                await ctx.send("📝 Please reply with the subject to roast within 60 seconds.")
                def check(m: discord.Message):
                    return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id
                try:
                    msg = await self.bot.wait_for('message', timeout=60, check=check)
                    user_text = msg.content.strip()
                    roast_data = await generate_groq_roast(category, style, target_name, user_text=user_text)
                    apis_tried.append('Groq Roast (user)')
                except asyncio.TimeoutError:
                    await ctx.send("❌ Timed out waiting for your custom roast subject.")
                    return
            # Use hardcoded fallback only as absolute last resort
            if not roast_data:
                roast_data = {
                    'roast': random.choice(fallback_roasts),
                    'source': 'Cybertron Roast Collection (Fallback)',
                    'category': 'fallback'
                }
                print(f"All APIs failed. APIs tried: {apis_tried}. Using hardcoded fallback.")
            else:
                print(f"Successfully got roast from: {apis_tried[-1] if apis_tried else 'unknown'}")
            
            # Groq already generates in requested style
            styled_text = roast_data['roast']
            style_source = 'Groq model'
            
            # Create category-specific embed styling
            if category == "mild":
                embed_title = "🙂 MILD ROAST 🙂"
                embed_color = 0x66CCFF
                field_names = ["🙂 Softness", "🎯 Accuracy", "😊 Playfulness"]
                field_values = [f"{random.randint(60, 80)}%", f"{random.randint(60, 85)}%", f"{random.randint(70, 90)}%"]
            elif category == "intellectual":
                embed_title = "🧠 INTELLECTUAL ROAST 🧠"
                embed_color = 0x2E8B57
                field_names = ["🧠 Wit", "🎯 Logic", "🔍 Nuance"]
                field_values = [f"{random.randint(70, 95)}%", f"{random.randint(70, 95)}%", f"{random.randint(65, 90)}%"]
            elif category == "savage":
                embed_title = "🔥 SAVAGE ROAST 🔥"
                embed_color = 0xFF4500
                field_names = ["🔥 Heat Level", "🎯 Accuracy", "💀 Brutality"]
                field_values = [f"{random.randint(70, 90)}%", f"{random.randint(60, 85)}%", f"{random.randint(75, 95)}%"]
            elif category == "dark_humor":
                embed_title = "🕶️ DARK HUMOR ROAST 🕶️"
                embed_color = 0x4B0082
                field_names = ["🕶️ Edge", "🎯 Precision", "😂 Punchline"]
                field_values = [f"{random.randint(70, 95)}%", f"{random.randint(65, 90)}%", f"{random.randint(75, 95)}%"]
            elif category == "nsfw":
                embed_title = "🚫 NSFW ROAST (Cursing) 🚫"
                embed_color = 0x8B0000
                field_names = ["🗣️ Cursing", "🎯 Precision", "💥 Impact"]
                field_values = [f"{random.randint(75, 100)}%", f"{random.randint(70, 95)}%", f"{random.randint(80, 100)}%"]
            elif category == "insane":
                embed_title = "🤯 INSANE ROAST (Nonsense) 🤯"
                embed_color = 0x8B0000
                field_names = ["🤯 Absurdity", "🎯 Precision", "💥 Chaos"]
                field_values = [f"{random.randint(80, 100)}%", f"{random.randint(60, 85)}%", f"{random.randint(85, 100)}%"]
            elif category == "user":
                embed_title = "📝 USER ROAST 📝"
                embed_color = 0xCCCCCC
                field_names = ["📝 Custom", "🎯 Target", "✨ Style"]
                field_values = ["100%", f"{random.randint(60, 90)}%", f"{random.randint(60, 90)}%"]
            else:
                embed_title = "🔥 ROAST DELIVERY! 🔥"
                embed_color = discord.Color.red().value
                field_names = ["🔥 Heat", "🎯 Accuracy", "💀 Damage"]
                field_values = [f"{random.randint(60, 90)}%", f"{random.randint(50, 85)}%", f"{random.randint(70, 95)}%"]
            
            # Build embed
            embed = discord.Embed(
                title=embed_title,
                color=embed_color,
                timestamp=discord.utils.utcnow()
            )
            embed.set_author(
                name=f"Roast requested by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url
            )
            embed.description = f"{target_mention}\n\n**{styled_text}**"
            
            embed.add_field(name=field_names[0], value=field_values[0], inline=True)
            embed.add_field(name=field_names[1], value=field_values[1], inline=True)
            embed.add_field(name=field_names[2], value=field_values[2], inline=True)
            
            embed.add_field(name="Category", value=f"`{category.replace('_', ' ').title()}`", inline=True)
            embed.add_field(name="Style", value=f"`{style.replace('_', ' ').title()}`", inline=True)
            
            embed.set_thumbnail(url=target_avatar)
            embed.set_footer(
                text=f"Source: {roast_data['source']} • Style: {style_source} • Roast responsibly!",
                icon_url=self.bot.user.display_avatar.url
            )
            
            # Send message and add BRUTAL reactions
            message = await ctx.send(embed=embed)
            
            try:
                brutal_reactions = ["💀", "☠️", "🔥", "⚰️", "🪦", "💥", "🗡️", "⚡"]
                await message.add_reaction(random.choice(brutal_reactions))
            except discord.HTTPException:
                pass
                
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Roast System Error",
                description="My roast generators are experiencing technical difficulties! Even my insult circuits need maintenance sometimes.",
                color=discord.Color.orange()
            )
            error_embed.set_footer(text="Error in roast delivery system")
            
            try:
                await ctx.send(embed=error_embed, ephemeral=True)
            except:
                await ctx.send("❌ Roast system temporarily down! You're still awesome though! 🔧", ephemeral=True)

    @commands.hybrid_command(name='compliment', description='Get a tailored compliment!')
    @discord.app_commands.describe(
        target="The user to compliment (optional - defaults to yourself)",
        category="Choose compliment type: Friendly, Intellectual, Ego Boost, Dark Humor, Flirty (Pick up lines), or Insane (Nonsense)",
        style="Choose output style: Old Time (Shakespeare), Slang, Southern (USA), Cockney, Robot, Pirate, Yoda, or Elvish (Sindarin)"
    )
    @discord.app_commands.choices(category=[
        discord.app_commands.Choice(name="Friendly", value="friendly"),
        discord.app_commands.Choice(name="Intellectual", value="intellectual"),
        discord.app_commands.Choice(name="Ego Boost", value="ego_boost"),
        discord.app_commands.Choice(name="Dark Humor", value="dark_humor"),
        discord.app_commands.Choice(name="Flirty", value="flirty"),
        discord.app_commands.Choice(name="Insane", value="insane")
    ])
    @discord.app_commands.choices(style=[
        discord.app_commands.Choice(name="Old Time", value="old_time"),
        discord.app_commands.Choice(name="Slang", value="slang"),
        discord.app_commands.Choice(name="Southern", value="southern"),
        discord.app_commands.Choice(name="Cockney", value="cockney"),
        discord.app_commands.Choice(name="Robot", value="robot"),
        discord.app_commands.Choice(name="Pirate", value="pirate"),
        discord.app_commands.Choice(name="Yoda", value="yoda"),
        discord.app_commands.Choice(name="Elvish", value="elvish")
    ])
    async def compliment(self, ctx: commands.Context, target: discord.Member = None, category: str = "friendly", style: str = "robot"):
        """Get a tailored compliment"""
        
        
        try:
            # Defer the interaction to prevent timeout
            await ctx.defer()
            
            # Determine target
            if target is None:
                target = ctx.author
                target_name = ctx.author.display_name
                target_mention = ctx.author.mention
                target_avatar = ctx.author.display_avatar.url
            else:
                target_name = target.display_name
                target_mention = target.mention
                target_avatar = target.display_avatar.url
            
            # Helper: Generate compliment via GROQ Chat Completions
            async def generate_groq_compliment(category: str, style: str, subject_name: str, user_text: str | None = None):
                api_key = GROQ_API_KEY
                if not api_key:
                    print("GROQ_API_KEY missing; skipping Groq compliment generation.")
                    return None
                style_instructions = {
                    "old_time": "Write in Shakespearean/Old English tone.",
                    "slang": "Use modern slang.",
                    "southern": "Use Southern USA colloquial tone.",
                    "cockney": "Use Cockney London slang and phrasing.",
                    "robot": "Write like a formal robot using technical jargon.",
                    "pirate": "Use pirate speak and nautical idioms.",
                    "yoda": "Speak like Yoda with inverted grammar.",
                    "elvish": "Use Sindarin-inspired poetic Elvish tone.",
                }.get(style, "Write in a straightforward modern tone.")
                category_instructions = {
                    "friendly": "Warm, kind, and uplifting compliment.",
                    "intellectual": "Smart, thoughtful compliment.",
                    "ego_boost": "Confidence-boosting, high praise.",
                    "dark_humor": "Edgy compliment with a dark humor twist.",
                    "flirty": "Playful pick-up line style.",
                    "insane": "Absurd, surreal nonsense compliment.",
                    "user": "Use the provided custom text as the subject and craft a specific compliment about it.",
                }.get(category, "Generate a compliment.")
                prompt_subject = user_text if (category == "user" and user_text) else subject_name
                system_prompt = (
                    "Discord compliment bot. Output 1–2 sentences."
                )
                user_prompt = (
                    f"Subject: {prompt_subject}\n"
                    f"Compliment type: {category_instructions}\nStyle: {style_instructions}\n"
                    "Return only the compliment text."
                )
                try:
                    timeout = aiohttp.ClientTimeout(total=45)
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        url = "https://api.groq.com/openai/v1/chat/completions"
                        headers = {
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        }
                        payload = {
                            "model": "llama-3.1-8b-instant",
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            "temperature": 0.8,
                            "max_tokens": 60,
                            "top_p": 0.9,
                        }
                        async with session.post(url, headers=headers, json=payload) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                try:
                                    text = data["choices"][0]["message"]["content"].strip()
                                except Exception:
                                    text = None
                                if text:
                                    return {
                                        "compliment": text,
                                        "source": "Groq",
                                        "category": category,
                                    }
                            else:
                                body = await resp.text()
                                print(f"Groq compliment request failed: HTTP {resp.status} — {body[:300]}")
                except Exception as e:
                    print(f"Groq compliment request error: {e}")
                return None
            
            # Category-specific local fallbacks (kept minimal)
            # Friendly and general fallbacks (used only if Groq fails for flirty)
            flirty_fallbacks = [
                "Is it hot in here or is it just your smile?",
                "You must be a magician, because whenever I look at you, everyone else disappears.",
                "Are you made of copper and tellurium? Because you're Cu-Te.",
                "If being charming was a crime, you'd be serving a life sentence.",
                "Your laugh is my new favorite sound.",
            ]
            
            # Try the appropriate API based on category
            compliment_data = None
            apis_tried = []
            
            if category == "friendly":
                compliment_data = await generate_groq_compliment(category, style, target_name)
                apis_tried.append('Groq Compliment (friendly)')
            elif category == "intellectual":
                compliment_data = await generate_groq_compliment(category, style, target_name)
                apis_tried.append('Groq Compliment (intellectual)')
            elif category == "ego_boost":
                compliment_data = await generate_groq_compliment(category, style, target_name)
                apis_tried.append('Groq Compliment (ego_boost)')
            elif category == "dark_humor":
                compliment_data = await generate_groq_compliment(category, style, target_name)
                apis_tried.append('Groq Compliment (dark_humor)')
            elif category == "flirty":
                compliment_data = await generate_groq_compliment(category, style, target_name)
                apis_tried.append('Groq Compliment (flirty)')
                if not compliment_data:
                    compliment_data = {
                        'compliment': random.choice(flirty_fallbacks),
                        'source': 'Flirty Fallback List',
                        'category': 'flirty'
                    }
            elif category == "insane":
                compliment_data = await generate_groq_compliment(category, style, target_name)
                apis_tried.append('Groq Compliment (insane)')
            
            elif category == "user":
                # For prefix command usage, prompt for text, then generate via Groq
                await ctx.send("📝 Please reply with your custom compliment subject within 60 seconds.")
                def check(m: discord.Message):
                    return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id
                try:
                    msg = await self.bot.wait_for('message', timeout=60, check=check)
                    user_text = msg.content.strip()
                    compliment_data = await generate_groq_compliment(category, style, target_name, user_text=user_text)
                    apis_tried.append('Groq Compliment (user)')
                except asyncio.TimeoutError:
                    await ctx.send("❌ Timed out waiting for your custom compliment subject.")
                    return
            # General fallback if all else fails
            if not compliment_data:
                general_fallbacks = [
                    "You make the world a better place just by being in it.",
                    "Your kindness is contagious and your presence is comforting.",
                    "The way you carry yourself inspires those around you.",
                ]
                compliment_data = {
                    'compliment': random.choice(general_fallbacks),
                    'source': 'General Compliment Fallback',
                    'category': 'fallback'
                }

            styled_text = compliment_data['compliment']
            style_source = 'Groq model'
            
            # Create category-specific embed styling
            if category == "friendly":
                embed_title = "🙂 FRIENDLY COMPLIMENT 🙂"
                embed_color = 0x90EE90
                field_names = ["💖 Warmth", "✨ Joy Boost", "🎯 Heart Accuracy"]
                field_values = [f"{random.randint(60, 90)}%", f"{random.randint(60, 90)}%", f"{random.randint(60, 90)}%"]
            elif category == "intellectual":
                embed_title = "🧠 INTELLECTUAL COMPLIMENT 🧠"
                embed_color = 0x2E8B57
                field_names = ["🧠 Wit", "🔍 Insight", "🎯 Precision"]
                field_values = [f"{random.randint(70, 95)}%", f"{random.randint(70, 95)}%", f"{random.randint(65, 90)}%"]
            elif category == "ego_boost":
                embed_title = "🦚 EGO BOOST 🦚"
                embed_color = 0x1E90FF
                field_names = ["📈 Confidence", "🌟 Prestige", "💬 Delivery"]
                field_values = [f"{random.randint(75, 100)}%", f"{random.randint(70, 95)}%", f"{random.randint(75, 95)}%"]
            elif category == "dark_humor":
                embed_title = "🕶️ DARK HUMOR COMPLIMENT 🕶️"
                embed_color = 0x4B0082
                field_names = ["🕶️ Edge", "🎯 Precision", "😂 Punchline"]
                field_values = [f"{random.randint(70, 95)}%", f"{random.randint(65, 90)}%", f"{random.randint(75, 95)}%"]
            elif category == "flirty":
                embed_title = "💘 FLIRTY COMPLIMENT (Pick up line) 💘"
                embed_color = 0xFF69B4
                field_names = ["😍 Charm", "💫 Spark", "🎯 Smooth Factor"]
                field_values = [f"{random.randint(65, 95)}%", f"{random.randint(65, 95)}%", f"{random.randint(65, 95)}%"]
            elif category == "insane":
                embed_title = "🤯 INSANE COMPLIMENT (Nonsense) 🤯"
                embed_color = 0x8B0000
                field_names = ["🤯 Absurdity", "🎯 Precision", "💥 Chaos"]
                field_values = [f"{random.randint(80, 100)}%", f"{random.randint(60, 85)}%", f"{random.randint(85, 100)}%"]
            else:
                embed_title = "✨ Compliment Delivery! ✨"
                embed_color = discord.Color.gold().value
                field_names = ["✨ Positivity", "🌟 Uplift", "🎯 Good Vibes"]
                field_values = [f"{random.randint(50, 80)}%", f"{random.randint(50, 80)}%", f"{random.randint(50, 80)}%"]
            
            # Build embed
            embed = discord.Embed(
                title=embed_title,
                color=embed_color,
                timestamp=discord.utils.utcnow()
            )
            embed.set_author(
                name=f"Compliment requested by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url
            )
            embed.description = f"{target_mention}\n\n**{styled_text}**"
            
            embed.add_field(name=field_names[0], value=field_values[0], inline=True)
            embed.add_field(name=field_names[1], value=field_values[1], inline=True)
            embed.add_field(name=field_names[2], value=field_values[2], inline=True)
            
            embed.add_field(name="Category", value=f"`{category.replace('_', ' ').title()}`", inline=True)
            embed.add_field(name="Style", value=f"`{style.replace('_', ' ').title()}`", inline=True)
            
            embed.set_thumbnail(url=target_avatar)
            embed.set_footer(
                text=f"Source: {compliment_data['source']} • Style: {style_source} • Keep shining!",
                icon_url=self.bot.user.display_avatar.url
            )
            
            message = await ctx.send(embed=embed)
            try:
                positive_reactions = ["😊", "💖", "🌟", "✨", "🥰", "💝", "🎉"]
                await message.add_reaction(random.choice(positive_reactions))
            except discord.HTTPException:
                pass
                
        except Exception as e:
            error_embed = discord.Embed(
                title="❌ Compliment System Error",
                description="My positivity generators are having a hiccup! Let me reboot my kindness protocols.",
                color=discord.Color.orange()
            )
            error_embed.set_footer(text="Error in compliment delivery system")
            
            try:
                await ctx.send(embed=error_embed, ephemeral=True)
            except:
                await ctx.send("❌ Compliment system temporarily down! You're still awesome though! ✨", ephemeral=True)

            # If "User" category selected in slash, prompt via modal for custom text
            if category == "user" and hasattr(ctx, "interaction") and ctx.interaction is not None:
                class UserRoastModal(discord.ui.Modal, title="Provide Custom Roast Text"):
                    def __init__(self):
                        super().__init__()
                        self.user_text = discord.ui.TextInput(label="Custom roast text", style=discord.TextStyle.paragraph, max_length=500)
                        self.add_item(self.user_text)
                    async def on_submit(self, interaction: discord.Interaction):
                        try:
                            # Generate via Groq using user-provided subject
                            api_key = GROQ_API_KEY
                            styled_text = self.user_text.value.strip()
                            style_source = 'Original style'
                            source_label = 'User Provided'
                            if api_key:
                                timeout = aiohttp.ClientTimeout(total=45)
                                async with aiohttp.ClientSession(timeout=timeout) as session:
                                    url = "https://api.groq.com/openai/v1/chat/completions"
                                    headers = {
                                        "Authorization": f"Bearer {api_key}",
                                        "Content-Type": "application/json",
                                    }
                                    style_map = {
                                        "old_time": "Write in Shakespearean/Old English tone.",
                                        "slang": "Use modern slang.",
                                        "southern": "Use Southern USA colloquial tone.",
                                        "cockney": "Use Cockney London slang and phrasing.",
                                        "robot": "Write like a formal robot using technical jargon.",
                                        "pirate": "Use pirate speak and nautical idioms.",
                                        "yoda": "Speak like Yoda with inverted grammar.",
                                        "elvish": "Use Sindarin-inspired poetic Elvish tone.",
                                    }
                                    system_prompt = (
                                        "Discord roast bot. Output 1–2 sentences. PG-13. No slurs, sexual content, or harassment."
                                    )
                                    user_prompt = (
                                        f"Subject: {self.user_text.value.strip()}\n"
                                        f"Style: {style_map.get(style, 'Write in a straightforward modern tone.')}\n"
                                        "Return only the roast text."
                                    )
                                    payload = {
                                        "model": "llama-3.1-8b-instant",
                                        "messages": [
                                            {"role": "system", "content": system_prompt},
                                            {"role": "user", "content": user_prompt},
                                        ],
                                        "temperature": 0.9,
                                        "max_tokens": 60,
                                        "top_p": 0.9,
                                    }
                                    async with session.post(url, headers=headers, json=payload) as resp:
                                        if resp.status == 200:
                                            data = await resp.json()
                                            try:
                                                styled_text = data["choices"][0]["message"]["content"].strip()
                                                style_source = 'Groq model'
                                                source_label = 'Groq'
                                            except Exception:
                                                pass
                                        else:
                                            body = await resp.text()
                                            print(f"Groq user roast request failed: HTTP {resp.status} — {body[:300]}")
                            embed = discord.Embed(
                                title="📝 USER ROAST 📝",
                                color=0xCCCCCC,
                                timestamp=discord.utils.utcnow()
                            )
                            embed.set_author(
                                name=f"Roast requested by {interaction.user.display_name}",
                                icon_url=interaction.user.display_avatar.url
                            )
                            embed.description = f"{target_mention}\n\n**{styled_text}**"
                            embed.add_field(name="📝 Custom", value="100%", inline=True)
                            embed.add_field(name="🎯 Target", value=f"{random.randint(60, 90)}%", inline=True)
                            embed.add_field(name="✨ Style", value=f"{random.randint(60, 90)}%", inline=True)
                            embed.add_field(name="Category", value="`User`", inline=True)
                            embed.add_field(name="Style", value=f"`{style.replace('_', ' ').title()}`", inline=True)
                            embed.set_thumbnail(url=target_avatar)
                            embed.set_footer(
                                text=f"Source: {source_label} • Style: {style_source} • Roast responsibly!",
                                icon_url=interaction.client.user.display_avatar.url
                            )
                            await interaction.response.send_message(embed=embed)
                        except Exception:
                            try:
                                await interaction.response.send_message("❌ Could not process your custom roast.", ephemeral=True)
                            except:
                                pass
                await ctx.interaction.response.send_modal(UserRoastModal())
                return
            # If "User" category selected in slash, prompt via modal for custom text
            if category == "user" and hasattr(ctx, "interaction") and ctx.interaction is not None:
                class UserComplimentModal(discord.ui.Modal, title="Provide Custom Compliment Text"):
                    def __init__(self):
                        super().__init__()
                        self.user_text = discord.ui.TextInput(label="Custom compliment text", style=discord.TextStyle.paragraph, max_length=500)
                        self.add_item(self.user_text)
                    async def on_submit(self, interaction: discord.Interaction):
                        try:
                            # Generate via Groq using user-provided subject
                            api_key = GROQ_API_KEY
                            styled_text = self.user_text.value.strip()
                            style_source = 'Original style'
                            source_label = 'User Provided'
                            if api_key:
                                timeout = aiohttp.ClientTimeout(total=45)
                                async with aiohttp.ClientSession(timeout=timeout) as session:
                                    url = "https://api.groq.com/openai/v1/chat/completions"
                                    headers = {
                                        "Authorization": f"Bearer {api_key}",
                                        "Content-Type": "application/json",
                                    }
                                    style_map = {
                                        "old_time": "Write in Shakespearean/Old English tone.",
                                        "slang": "Use modern slang.",
                                        "southern": "Use Southern USA colloquial tone.",
                                        "cockney": "Use Cockney London slang and phrasing.",
                                        "robot": "Write like a formal robot using technical jargon.",
                                        "pirate": "Use pirate speak and nautical idioms.",
                                        "yoda": "Speak like Yoda with inverted grammar.",
                                        "elvish": "Use Sindarin-inspired poetic Elvish tone.",
                                    }
                                    system_prompt = (
                                        "Discord compliment bot. Output 1–2 sentences. PG-13. No explicit content or stereotypes."
                                    )
                                    user_prompt = (
                                        f"Subject: {self.user_text.value.strip()}\n"
                                        f"Style: {style_map.get(style, 'Write in a straightforward modern tone.')}\n"
                                        "Return only the compliment text."
                                    )
                                    payload = {
                                        "model": "llama-3.1-8b-instant",
                                        "messages": [
                                            {"role": "system", "content": system_prompt},
                                            {"role": "user", "content": user_prompt},
                                        ],
                                        "temperature": 0.8,
                                        "max_tokens": 60,
                                        "top_p": 0.9,
                                    }
                                    async with session.post(url, headers=headers, json=payload) as resp:
                                        if resp.status == 200:
                                            data = await resp.json()
                                            try:
                                                styled_text = data["choices"][0]["message"]["content"].strip()
                                                style_source = 'Groq model'
                                                source_label = 'Groq'
                                            except Exception:
                                                pass
                                        else:
                                            body = await resp.text()
                                            print(f"Groq user compliment request failed: HTTP {resp.status} — {body[:300]}")
                            embed = discord.Embed(
                                title="📝 USER COMPLIMENT 📝",
                                color=0xCCCCCC,
                                timestamp=discord.utils.utcnow()
                            )
                            embed.set_author(
                                name=f"Compliment requested by {interaction.user.display_name}",
                                icon_url=interaction.user.display_avatar.url
                            )
                            embed.description = f"{target_mention}\n\n**{styled_text}**"
                            embed.add_field(name="📝 Custom", value="100%", inline=True)
                            embed.add_field(name="🌟 Uplift", value=f"{random.randint(60, 90)}%", inline=True)
                            embed.add_field(name="✨ Style", value=f"{random.randint(60, 90)}%", inline=True)
                            embed.add_field(name="Category", value="`User`", inline=True)
                            embed.add_field(name="Style", value=f"`{style.replace('_', ' ').title()}`", inline=True)
                            embed.set_thumbnail(url=target_avatar)
                            embed.set_footer(
                                text=f"Source: {source_label} • Style: {style_source} • Keep shining!",
                                icon_url=interaction.client.user.display_avatar.url
                            )
                            await interaction.response.send_message(embed=embed)
                        except Exception:
                            try:
                                await interaction.response.send_message("❌ Could not process your custom compliment.", ephemeral=True)
                            except:
                                pass
                await ctx.interaction.response.send_modal(UserComplimentModal())
                return

async def setup(bot):
    await bot.add_cog(GoodEvilSystem(bot))