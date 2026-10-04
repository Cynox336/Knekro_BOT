import random
try:
    from .gacha_pool import (
        PROMOTIONAL_5STAR,
        STANDARD_5STARS,
        TICKET_5STAR_NAME,
        FOUR_STARS,
        THREE_STARS
    )
except ImportError:
    from gacha_pool import (
        PROMOTIONAL_5STAR,
        STANDARD_5STARS,
        TICKET_5STAR_NAME,
        FOUR_STARS,
        THREE_STARS
    )

# -- Parámetros del Gacha --
WISH_COST = 160
MAX_PITY_5STAR = 80
SOFT_PITY_5STAR_START = 60
MAX_TICKETS_PER_USER = 3

# -- Cálculo de Probabilidad 5★ --
def calculate_5star_prob(pity: int) -> float:
    base_rate = 0.006
    if pity < SOFT_PITY_5STAR_START:
        return base_rate
    elif pity >= MAX_PITY_5STAR:
        return 1.0
    else:
        extra = (pity - SOFT_PITY_5STAR_START + 1) * 0.05
        return min(base_rate + extra, 1.0)

# -- Tirada Individual --
def perform_single_pull(pity_5star: int, pity_4star: int, guaranteed_5star: int, current_tickets: int = 0, custom_5stars: list = None):
    pity_5star += 1
    pity_4star += 1

    prob_5 = calculate_5star_prob(pity_5star)
    prob_4 = 0.051

    roll = random.random()
    event_type = None

    available_5stars = list(STANDARD_5STARS)
    if custom_5stars:
        for cp in custom_5stars:
            available_5stars.append({
                "name": f"✨ {cp['name']} (Comunidad)",
                "description": cp.get("description", "Premio 5★ creado por la comunidad."),
                "rarity": 5
            })

    if current_tickets >= MAX_TICKETS_PER_USER:
        available_5stars = [it for it in available_5stars if it["name"] != TICKET_5STAR_NAME]
        if not available_5stars:
            available_5stars = [STANDARD_5STARS[1]]

    if roll < prob_5:
        pity_5star = 0
        pity_4star = 0

        if guaranteed_5star == 1:
            item = PROMOTIONAL_5STAR
            guaranteed_5star = 0
            event_type = "5STAR_GUARANTEED"
        else:
            if random.random() < 0.5:
                item = PROMOTIONAL_5STAR
                guaranteed_5star = 0
                event_type = "5STAR_WON_5050"
            else:
                item = random.choice(available_5stars)
                guaranteed_5star = 1
                event_type = "5STAR_LOST_5050"

        if item.get("name") == TICKET_5STAR_NAME:
            current_tickets += 1

        return item, pity_5star, pity_4star, guaranteed_5star, event_type, current_tickets

    elif roll < (prob_5 + prob_4) or pity_4star >= 10:
        pity_4star = 0
        item = random.choice(FOUR_STARS)
        event_type = "4STAR"
        return item, pity_5star, pity_4star, guaranteed_5star, event_type, current_tickets

    else:
        item = random.choice(THREE_STARS)
        event_type = "3STAR"
        return item, pity_5star, pity_4star, guaranteed_5star, event_type, current_tickets

# -- Tiradas Múltiples --
def simulate_pulls(count: int, initial_pity_5: int, initial_pity_4: int, initial_guaranteed: int, current_tickets: int = 0, custom_5stars: list = None):
    results = []
    pity_5 = initial_pity_5
    pity_4 = initial_pity_4
    guaranteed = initial_guaranteed
    tickets = current_tickets

    for _ in range(count):
        item, pity_5, pity_4, guaranteed, event_type, tickets = perform_single_pull(
            pity_5, pity_4, guaranteed, current_tickets=tickets, custom_5stars=custom_5stars
        )
        results.append({
            "item": item,
            "event_type": event_type
        })

    return results, pity_5, pity_4, guaranteed, tickets
