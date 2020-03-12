import datetime


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
