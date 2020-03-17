import datetime
import random


def convert_upgrade_levels(mult_lvl, money_lvl, crit_lvl):
    """Errechnet den Wert eines Upgrade-Levels"""
    mult = 100 + mult_lvl * 5
    money = round(money_lvl * 1.8) + 2
    crit = round(crit_lvl * 1.5)
    return mult, money, crit


def lvlcalc(xp):
    """Errechnet aus den gegebenen XP das Level und den Fortschritt bis zum nächsten Level"""
    level = 0
    cap = 100
    while xp >= cap:
        level += 1
        xp -= cap
        cap += 5 * (level * level) + 50 * level + 100
    return level, xp, cap


def convert_pet(pet):
    tn = datetime.datetime.utcnow()
    stats = {
        "hunger": 0,
        "hygiene": 0,
        "fun": 0,
        "energy": 0
    }
    for stat in ["hunger", "hygiene", "fun", "energy"]:
        t = (tn - pet[stat]).total_seconds()
        p = 100 - int(t / 120)
        if p < 0:
            p = 0
        stats[stat] = p
    return stats


def get_tool_rarity(tool):
    if "infinity" in tool:
        rarity = 5
    elif "neutron" in tool:
        rarity = 4
    elif "komet" in tool:
        rarity = 3
    elif "stern" in tool:
        rarity = 2
    else:
        rarity = 1
    return rarity

def get_repair_item(rarity):
    if rarity == 5:
        item = "infinity ingot"
    elif rarity == 4:
        item = "neutron ingot"
    elif rarity == 3:
        item = "komet"
    elif rarity == 2:
        item = "stern"
    else:
        item = "meteorit"
    return item

def get_drop_odds(rarity):
    drops = {
        60 + rarity * 2: ["ziegelstein", "spinnwebe", "kleeblatt", "minipilz"],  # COMMON
        25 + rarity * 1.8: ["juwelfragment", "energiestaub", "sternenstaub"],  # UNCOMMON
        12 + rarity * 1.6: ["meteoritstück", "sternenstück", "kometstück"],  # RARE
        7 + rarity * 1.4: ["herzschuppe", "feuerstein", "griffklaue"],  # EPIC
        1 + rarity * 1.2: ["edelstein", "neutron nugget"]  # LEGENDARY
    }
    return drops

def get_random_drops(rarity, amount):
    drops = get_drop_odds(rarity)
    results = random.choices(list(drops.values()), weights=list(drops.keys()), k=amount)
    loot = {}
    for result in results:
        choice = random.choice(result)
        loot[choice] = loot.get(choice, 0) + 1
    return loot
