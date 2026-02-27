from datetime import date

LEVELS = [0, 100, 250, 500, 900, 1400, 2000]

def calc_level(xp: int) -> int:
    lvl = 1
    for i, border in enumerate(LEVELS, start=1):
        if xp >= border:
            lvl = i
    return lvl

def update_streak(last_date, today: date, streak: int):
    if last_date is None:
        return 1, today

    diff = (today - last_date).days
    if diff == 0:
        return streak, last_date
    if diff == 1:
        return streak + 1, today
    return 1, today