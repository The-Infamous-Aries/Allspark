import asyncio
import aiohttp
import json

TEST_TEXT = "Testing translation of this sentence for style."

async def fetch_json(session, url, **kwargs):
    try:
        async with session.get(url, **kwargs) as resp:
            status = resp.status
            try:
                data = await resp.json()
            except Exception:
                data = await resp.text()
            return status, data
    except Exception as e:
        return None, str(e)

async def post_json(session, url, data=None, **kwargs):
    try:
        async with session.post(url, data=data or {}, **kwargs) as resp:
            status = resp.status
            try:
                payload = await resp.json()
            except Exception:
                payload = await resp.text()
            return status, payload
    except Exception as e:
        return None, str(e)

async def test_roast_apis(session):
    print("\n== Roast APIs ==")
    # Mild: Chuck Norris
    status, data = await fetch_json(session, "https://api.chucknorris.io/jokes/random")
    print("ChuckNorris:", status, str(data)[:120])
    # Mashape Insult (mattbas)
    status, data = await fetch_json(session, "https://insult.mattbas.org/api/insult.json")
    print("Mattbas Insult:", status, str(data)[:120])
    # Evil Insult (Insane / NSFW)
    status, data = await fetch_json(session, "https://evilinsult.com/generate_insult.php?lang=en&type=json")
    print("EvilInsult:", status, str(data)[:120])

async def test_compliment_apis(session):
    print("\n== Compliment APIs ==")
    # Wholesome: Complimentr (primary)
    status, data = await fetch_json(session, "https://www.complimentr.com/api", headers={"Accept": "application/json"})
    print("Wholesome (Complimentr):", status, str(data)[:120])
    # Wholesome secondary: Popcat Compliment
    status, data = await fetch_json(session, "https://api.popcat.xyz/compliment", headers={"Accept": "application/json"})
    print("Wholesome (Popcat Compliment):", status, str(data)[:120])
    # Affirmations: Affirmations.dev
    status, data = await fetch_json(session, "https://www.affirmations.dev/")
    print("Affirmation (Affirmations.dev):", status, str(data)[:120])
    # Corporate BS
    status, data = await fetch_json(session, "https://corporatebs-generator.sameerkumar.website/")
    print("Corporate BS:", status, str(data)[:120])
    # Flirty: Popcat Pickup Lines
    status, data = await fetch_json(session, "https://api.popcat.xyz/pickuplines", headers={"Accept": "application/json"})
    print("Popcat PickupLines:", status, str(data)[:120])

async def test_translators(session):
    print("\n== FunTranslations Translators ==")
    endpoint_chains = {
        'old_tyme': [('shakespeare', 'FunTranslations Shakespeare'), ('oldenglish', 'FunTranslations Old English')],
        'hood': [('jive', 'FunTranslations Jive'), ('ebonics', 'FunTranslations Ebonics')],
        'robot': [('leetspeak', 'FunTranslations Leetspeak')],
        'redneck': [('redneck', 'FunTranslations Redneck'), ('southern-accent', 'FunTranslations Southern Accent')]
    }
    for style, chain in endpoint_chains.items():
        success = False
        for ep, label in chain:
            status, data = await post_json(session, f"https://api.funtranslations.com/translate/{ep}.json", {"text": TEST_TEXT})
            ok_or_rate_limited = status in (200, 429)
            if isinstance(data, dict):
                translated = data.get('contents', {}).get('translated')
            else:
                translated = None
            print(f"{label}: status={status}, ok_or_rate_limited={ok_or_rate_limited}, translated={bool(translated)}")
            if status == 200 and translated:
                success = True
                break
        if not success:
            print(f"{style} chain: no successful translation; API-only behavior retains original.")

async def main():
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        await test_roast_apis(session)
        await test_compliment_apis(session)
        await test_translators(session)

if __name__ == "__main__":
    asyncio.run(main())