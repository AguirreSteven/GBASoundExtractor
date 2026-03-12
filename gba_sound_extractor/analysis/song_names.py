"""Built-in song name database for popular GBA games.

Song names are sourced from the community decompilation projects
(pokeemerald, pokeruby, pokefirered) and fan wikis.  The database
is keyed by 4-character game code (e.g. ``"BPEE"`` for Pokemon
Emerald US) and maps song indices to human-readable names.
"""

from typing import Optional


class SongNameDatabase:
    """Look up known song names by game code and song index."""

    def __init__(self):
        self._db: dict[str, dict[int, str]] = _build_database()

    def get_name(self, game_code: str, song_index: int) -> Optional[str]:
        """Return the song name for *game_code* at *song_index*, or None."""
        game = self._db.get(game_code)
        if game is None:
            return None
        return game.get(song_index)

    def has_game(self, game_code: str) -> bool:
        return game_code in self._db

    def supported_games(self) -> list[str]:
        return list(self._db.keys())


def _build_database() -> dict[str, dict[int, str]]:
    """Construct the built-in name database.

    Each entry is  game_code -> {song_index: name, ...}
    """
    db: dict[str, dict[int, str]] = {}

    # ------------------------------------------------------------------
    # Pokemon Emerald (US) — BPEE
    # Names from pokeemerald/sound/songs.h
    # ------------------------------------------------------------------
    db["BPEE"] = {
        0: "(Silence)",
        1: "Littleroot Town",
        2: "Oldale Town",
        3: "Dewford Town",
        4: "Lavaridge Town",
        5: "Fallarbor Town",
        6: "Verdanturf Town",
        7: "Pacifidlog Town",
        8: "Petalburg City",
        9: "Slateport City",
        10: "Mauville City",
        11: "Rustboro City",
        12: "Fortree City",
        13: "Lilycove City",
        14: "Mossdeep City",
        15: "Sootopolis City",
        16: "Ever Grande City",
        17: "Route 101",
        18: "Route 110",
        19: "Route 120",
        20: "Route 104 (Underwater)",
        21: "Surfing",
        22: "Underwater",
        23: "Cycling",
        24: "Pokemon Center",
        25: "Pokemon Gym",
        26: "Victory Road",
        27: "Wild Pokemon Battle",
        28: "Trainer Battle",
        29: "Gym Leader Battle",
        30: "Champion Battle",
        31: "Wild Pokemon Victory",
        32: "Trainer Victory",
        33: "Gym Leader Victory",
        34: "Level Up",
        35: "Pokemon Healed",
        36: "Obtain Badge",
        37: "Obtain Item",
        38: "Pokemon Caught",
        39: "Title Screen",
        40: "Introduction",
        41: "Rival Encounter",
        42: "Rival Battle",
        43: "Team Aqua/Magma Encounter",
        44: "Team Aqua/Magma Battle",
        45: "Elite Four Battle",
        46: "Surf Theme",
        47: "Cave of Origin",
        48: "Sealed Chamber",
        49: "Trick House",
        50: "Safari Zone",
        51: "Battle Frontier",
        52: "Battle Factory",
        53: "Battle Arena",
        54: "Battle Dome",
        55: "Battle Pike",
        56: "Battle Palace",
        57: "Battle Pyramid",
        58: "Battle Tower",
        59: "Rayquaza Appears",
        60: "Drought",
        61: "Abnormal Weather",
        62: "Regi Battle",
        63: "Rival Exit",
        64: "Safari Zone Timer",
        65: "Groudon/Kyogre Battle",
        66: "Ending Theme",
        67: "Credits",
        68: "Hall of Fame",
        69: "Fallarbor Town (Alt)",
        70: "Sealed Chamber (Open)",
        71: "Contest",
        72: "Contest Winner",
        73: "Battle Tower Lobby",
        74: "Evolution",
        75: "Evolution Success",
        76: "Frontier Brain Battle",
        77: "Pokeball Obtained (Fanfare)",
    }

    # ------------------------------------------------------------------
    # Pokemon FireRed (US) — BPRE
    # ------------------------------------------------------------------
    db["BPRE"] = {
        0: "(Silence)",
        1: "Pallet Town",
        2: "Viridian City",
        3: "Pewter City",
        4: "Cerulean City",
        5: "Lavender Town",
        6: "Vermilion City",
        7: "Celadon City",
        8: "Fuchsia City",
        9: "Cinnabar Island",
        10: "Indigo Plateau (Exterior)",
        11: "Saffron City",
        12: "Route 1",
        13: "Route 3",
        14: "Route 11",
        15: "Route 24",
        16: "Cycling",
        17: "Pokemon Center",
        18: "Pokemon Gym",
        19: "Victory Road",
        20: "Wild Pokemon Battle",
        21: "Trainer Battle",
        22: "Gym Leader Battle",
        23: "Champion Battle",
        24: "Wild Pokemon Victory",
        25: "Trainer Victory",
        26: "Gym Leader Victory",
        27: "Level Up",
        28: "Pokemon Healed",
        29: "Obtain Badge",
        30: "Obtain Item",
        31: "Pokemon Caught",
        32: "Title Screen",
        33: "Introduction",
        34: "Rival Encounter",
        35: "Rival Battle",
        36: "SS Anne",
        37: "Pokemon Tower",
        38: "Silph Co.",
        39: "Elite Four Battle",
        40: "Surfing",
        41: "Rocket Hideout",
        42: "Team Rocket Battle",
        43: "Ending Theme",
        44: "Credits",
        45: "Hall of Fame",
        46: "Evolution",
        47: "Evolution Success",
        48: "Sevii Islands",
        49: "Mt. Ember Exterior",
        50: "Trainer Tower",
    }

    # ------------------------------------------------------------------
    # Pokemon LeafGreen (US) — BPGE
    # ------------------------------------------------------------------
    db["BPGE"] = dict(db["BPRE"])  # Same music as FireRed

    # ------------------------------------------------------------------
    # Pokemon Ruby (US) — AXVE
    # ------------------------------------------------------------------
    db["AXVE"] = {
        0: "(Silence)",
        1: "Littleroot Town",
        2: "Oldale Town",
        3: "Dewford Town",
        4: "Lavaridge Town",
        5: "Fallarbor Town",
        6: "Verdanturf Town",
        7: "Pacifidlog Town",
        8: "Petalburg City",
        9: "Slateport City",
        10: "Mauville City",
        11: "Rustboro City",
        12: "Fortree City",
        13: "Lilycove City",
        14: "Mossdeep City",
        15: "Sootopolis City",
        16: "Ever Grande City",
        17: "Route 101",
        18: "Route 110",
        19: "Route 120",
        20: "Route 104 (Underwater)",
        21: "Surfing",
        22: "Underwater",
        23: "Cycling",
        24: "Pokemon Center",
        25: "Pokemon Gym",
        26: "Victory Road",
        27: "Wild Pokemon Battle",
        28: "Trainer Battle",
        29: "Gym Leader Battle",
        30: "Champion Battle",
        31: "Wild Pokemon Victory",
        32: "Trainer Victory",
        33: "Gym Leader Victory",
        34: "Level Up",
        35: "Pokemon Healed",
        36: "Obtain Badge",
        37: "Obtain Item",
        38: "Pokemon Caught",
        39: "Title Screen",
    }

    # ------------------------------------------------------------------
    # Pokemon Sapphire (US) — AXPE
    # ------------------------------------------------------------------
    db["AXPE"] = dict(db["AXVE"])  # Same music as Ruby

    # ------------------------------------------------------------------
    # Fire Emblem (US) — AFEJ (FE7: Blazing Blade)
    # ------------------------------------------------------------------
    db["AFEJ"] = {
        0: "(Silence)",
        1: "Opening ~ Precious Things",
        2: "Strike",
        3: "Companions",
        4: "An Unexpected Caller",
        5: "Recollection of a Pact",
        6: "Reminiscence",
        7: "Rise to the Challenge",
        8: "Softly with Grace",
        9: "Winds Across the Plains",
        10: "Fly, Pegasus",
        11: "Loyalty",
        12: "Determination",
        13: "Unfulfilled Heart",
        14: "Shadow Approaches",
        15: "Shattered Life",
        16: "Victory or Death",
        17: "Everything into the Dark",
        18: "Battle Theme",
        19: "Attack!",
        20: "Defense",
        21: "Comrades",
        22: "Main Theme",
        23: "Game Over",
        24: "Victory Fanfare",
        25: "Chapter Clear",
        26: "Shop",
        27: "Arena Battle",
    }

    # ------------------------------------------------------------------
    # Fire Emblem: The Sacred Stones (US) — BE8J
    # ------------------------------------------------------------------
    db["BE8J"] = {
        0: "(Silence)",
        1: "The Sacred Stones (Theme)",
        2: "Truth, Despair, and Hope",
        3: "Comrades",
        4: "Lyon",
        5: "Determination",
        6: "Rise Above",
        7: "The Prince's Despair",
        8: "Companions",
        9: "Attack!",
        10: "Defense",
        11: "Victory",
        12: "Shop",
        13: "Arena",
        14: "Chapter Clear",
        15: "Game Over",
    }

    # ------------------------------------------------------------------
    # Golden Sun (US) — AGSE
    # ------------------------------------------------------------------
    db["AGSE"] = {
        0: "(Silence)",
        1: "Main Theme",
        2: "Vale",
        3: "Vault",
        4: "Bilibin",
        5: "Imil",
        6: "Kalay",
        7: "Tolbi",
        8: "Lalivero",
        9: "Overworld",
        10: "Sol Sanctum",
        11: "Mercury Lighthouse",
        12: "Venus Lighthouse",
        13: "Saturos Battle",
        14: "Battle Theme",
        15: "Boss Battle",
        16: "Fusion Dragon Battle",
        17: "Victory",
        18: "Inn",
        19: "Sanctum",
        20: "Shop",
    }

    # ------------------------------------------------------------------
    # Golden Sun: The Lost Age (US) — AGFE
    # ------------------------------------------------------------------
    db["AGFE"] = {
        0: "(Silence)",
        1: "Main Theme",
        2: "Felix's Theme",
        3: "Overworld (Gondowan)",
        4: "Overworld (Eastern Sea)",
        5: "Lemuria",
        6: "Prox",
        7: "Battle Theme",
        8: "Boss Battle",
        9: "Final Boss (Doom Dragon)",
        10: "Victory",
        11: "Shop",
        12: "Inn",
        13: "Contigo",
        14: "Shaman Village",
        15: "Mars Lighthouse",
    }

    # ------------------------------------------------------------------
    # Metroid Fusion (US) — AMTE
    # ------------------------------------------------------------------
    db["AMTE"] = {
        0: "(Silence)",
        1: "Title Screen",
        2: "Main Deck",
        3: "Sector 1 (SRX)",
        4: "Sector 2 (TRO)",
        5: "Sector 3 (PYR)",
        6: "Sector 4 (AQA)",
        7: "Sector 5 (ARC)",
        8: "Sector 6 (NOC)",
        9: "SA-X Encounter",
        10: "Boss Battle",
        11: "Serris/Yakuza Battle",
        12: "Omega Metroid",
        13: "Escape Sequence",
        14: "Item Acquired",
        15: "Game Over",
        16: "Ending",
    }

    # ------------------------------------------------------------------
    # Metroid: Zero Mission (US) — BMXE
    # ------------------------------------------------------------------
    db["BMXE"] = {
        0: "(Silence)",
        1: "Title Screen",
        2: "Brinstar",
        3: "Norfair",
        4: "Kraid's Lair",
        5: "Ridley's Lair",
        6: "Tourian",
        7: "Chozodia",
        8: "Space Pirate Mother Ship",
        9: "Boss Battle",
        10: "Kraid Battle",
        11: "Ridley Battle",
        12: "Mother Brain",
        13: "Mecha Ridley",
        14: "Escape Sequence",
        15: "Item Acquired",
        16: "Game Over",
        17: "Ending",
    }

    # ------------------------------------------------------------------
    # Kirby & the Amazing Mirror (US) — B8KE
    # ------------------------------------------------------------------
    db["B8KE"] = {
        0: "(Silence)",
        1: "Title Screen",
        2: "Rainbow Route",
        3: "Moonlight Mansion",
        4: "Cabbage Cavern",
        5: "Mustard Mountain",
        6: "Carrot Castle",
        7: "Olive Ocean",
        8: "Peppermint Palace",
        9: "Radish Ruins",
        10: "Candy Constellation",
        11: "Boss Battle",
        12: "Dark Mind Battle",
        13: "Mini Game",
        14: "Goal",
        15: "Game Over",
    }

    # ------------------------------------------------------------------
    # Kirby: Nightmare in Dream Land (US) — A7KE
    # ------------------------------------------------------------------
    db["A7KE"] = {
        0: "(Silence)",
        1: "Title Screen",
        2: "Vegetable Valley",
        3: "Ice Cream Island",
        4: "Butter Building",
        5: "Grape Garden",
        6: "Yogurt Yard",
        7: "Orange Ocean",
        8: "Rainbow Resort",
        9: "Boss Battle",
        10: "King Dedede Battle",
        11: "Nightmare Battle",
        12: "Victory Dance",
        13: "Game Over",
    }

    # ------------------------------------------------------------------
    # Mario & Luigi: Superstar Saga (US) — A88E
    # ------------------------------------------------------------------
    db["A88E"] = {
        0: "(Silence)",
        1: "Title Screen",
        2: "Stardust Fields",
        3: "Hoohoo Mountain",
        4: "Beanbean Town",
        5: "Woohoo Hooniversity",
        6: "Teehee Valley",
        7: "Joke's End",
        8: "Bowser's Castle",
        9: "Battle Theme",
        10: "Boss Battle",
        11: "Cackletta Battle",
        12: "Victory",
        13: "Shop",
        14: "Game Over",
        15: "Ending",
    }

    # ------------------------------------------------------------------
    # The Legend of Zelda: The Minish Cap (US) — BZME
    # ------------------------------------------------------------------
    db["BZME"] = {
        0: "(Silence)",
        1: "Title Screen",
        2: "Hyrule Town",
        3: "Minish Village",
        4: "Hyrule Field",
        5: "Mt. Crenel",
        6: "Castor Wilds",
        7: "Dark Hyrule Castle",
        8: "Dungeon Theme",
        9: "Boss Battle",
        10: "Vaati Battle",
        11: "Item Get",
        12: "Heart Container",
        13: "Game Over",
        14: "Ending / Credits",
    }

    # ------------------------------------------------------------------
    # Castlevania: Aria of Sorrow (US) — ACBE
    # ------------------------------------------------------------------
    db["ACBE"] = {
        0: "(Silence)",
        1: "Title Screen",
        2: "Castle Corridor",
        3: "Chapel",
        4: "Study",
        5: "Dance Hall",
        6: "Inner Quarters",
        7: "Floating Garden",
        8: "Clock Tower",
        9: "Underground Reservoir",
        10: "Top Floor",
        11: "Forbidden Area",
        12: "Chaotic Realm",
        13: "Boss Battle",
        14: "Graham Battle",
        15: "Chaos Battle",
        16: "Game Over",
        17: "Ending",
    }

    # ------------------------------------------------------------------
    # Advance Wars (US) — AWRE
    # ------------------------------------------------------------------
    db["AWRE"] = {
        0: "(Silence)",
        1: "Title Screen",
        2: "Andy's Theme",
        3: "Max's Theme",
        4: "Sami's Theme",
        5: "Olaf's Theme",
        6: "Grit's Theme",
        7: "Kanbei's Theme",
        8: "Eagle's Theme",
        9: "Drake's Theme",
        10: "Sturm's Theme",
        11: "Victory",
        12: "Defeat",
        13: "Map Theme",
        14: "CO Power",
    }

    # ------------------------------------------------------------------
    # Advance Wars 2: Black Hole Rising (US) — AW2E
    # ------------------------------------------------------------------
    db["AW2E"] = {
        0: "(Silence)",
        1: "Title Screen",
        2: "Andy's Theme",
        3: "Max's Theme",
        4: "Sami's Theme",
        5: "Colin's Theme",
        6: "Hawke's Theme",
        7: "Lash's Theme",
        8: "Adder's Theme",
        9: "Flak's Theme",
        10: "Sturm's Theme",
        11: "Victory",
        12: "Defeat",
        13: "CO Power",
        14: "Super CO Power",
    }

    return db
