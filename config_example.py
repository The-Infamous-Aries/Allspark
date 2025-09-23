#!/usr/bin/env python3
"""
Example script demonstrating how to use the new multi-server configuration system.

This script shows how to:
1. Get server-specific role and channel IDs
2. Use the configuration in Discord commands
3. Handle different servers with different configurations
"""

import discord
from discord.ext import commands
from config import (
    get_role_ids, 
    get_results_channel_id, 
    get_guild_id_from_context,
    get_server_config
)

# Example usage in a Discord command
class ExampleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="show_config")
    async def show_config(self, ctx):
        """Show the current server's configuration."""
        guild_id = get_guild_id_from_context(ctx)
        
        # Get server-specific configuration
        role_ids = get_role_ids(guild_id)
        results_channel_id = get_results_channel_id(guild_id)
        
        embed = discord.Embed(
            title="Server Configuration",
            description=f"Configuration for {ctx.guild.name if ctx.guild else 'DM'}",
            color=0x00ff00
        )
        
        embed.add_field(
            name="Results Channel ID",
            value=str(results_channel_id),
            inline=False
        )
        
        for role_name, role_id_list in role_ids.items():
            embed.add_field(
                name=f"{role_name} Role IDs",
                value=", ".join(map(str, role_id_list)) if role_id_list else "None",
                inline=True
            )
        
        await ctx.send(embed=embed)

    @commands.command(name="check_role")
    async def check_role(self, ctx, role_type: str):
        """Check if user has a specific role type."""
        guild_id = get_guild_id_from_context(ctx)
        role_ids = get_role_ids(guild_id)
        
        if role_type not in role_ids:
            await ctx.send(f"Unknown role type: {role_type}")
            return
        
        user_role_ids = [role.id for role in ctx.author.roles]
        has_role = any(role_id in user_role_ids for role_id in role_ids[role_type])
        
        if has_role:
            await ctx.send(f"✅ You have the {role_type} role!")
        else:
            await ctx.send(f"❌ You don't have the {role_type} role.")

    @discord.app_commands.command(name="server_info")
    async def server_info_slash(self, interaction: discord.Interaction):
        """Slash command example showing server configuration."""
        guild_id = get_guild_id_from_context(interaction)
        config = get_server_config(guild_id)
        
        embed = discord.Embed(
            title="Server Information",
            description="Current server configuration",
            color=0x0099ff
        )
        
        embed.add_field(
            name="Guild ID",
            value=str(guild_id) if guild_id else "DM/Unknown",
            inline=True
        )
        
        embed.add_field(
            name="Results Channel",
            value=f"<#{config['RESULTS_CHANNEL_ID']}>",
            inline=True
        )
        
        role_info = []
        for role_name, role_list in config['ROLE_IDS'].items():
            if role_list:
                role_mentions = [f"<@&{role_id}>" for role_id in role_list]
                role_info.append(f"**{role_name}**: {', '.join(role_mentions)}")
            else:
                role_info.append(f"**{role_name}**: None configured")
        
        embed.add_field(
            name="Configured Roles",
            value="\n".join(role_info) if role_info else "No roles configured",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

# Example of how to use in your existing code
def example_usage():
    """Example showing different ways to use the configuration system."""
    
    # Example 1: Get configuration for a specific guild ID
    guild_id = 1234567890123456789
    role_ids = get_role_ids(guild_id)
    results_channel = get_results_channel_id(guild_id)
    
    print(f"Server {guild_id}:")
    print(f"  Results Channel: {results_channel}")
    print(f"  Autobot Roles: {role_ids['Autobot']}")
    print(f"  Decepticon Roles: {role_ids['Decepticon']}")
    
    # Example 2: Get default configuration (when no guild_id provided)
    default_roles = get_role_ids()
    default_channel = get_results_channel_id()
    
    print(f"\nDefault Configuration:")
    print(f"  Results Channel: {default_channel}")
    print(f"  All Roles: {default_roles}")
    
    # Example 3: Get full server configuration
    full_config = get_server_config(guild_id)
    print(f"\nFull Config for {guild_id}: {full_config}")

if __name__ == "__main__":
    example_usage()