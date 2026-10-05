from __future__ import annotations

from typing import Any

from nebula_ai_stories.providers.base import TextGenerationProvider


def _seed(
    title: str,
    premise: str,
    hook: str,
    problem: str,
    action: str,
    twist: str,
    payoff: str,
    emotion: str,
    family: str,
    mechanics: list[str],
    visuals: list[str],
    *,
    duration: float = 11.0,
    difficulty: str = "easy",
) -> dict[str, Any]:
    return {
        "title": title,
        "premise": premise,
        "hook": hook,
        "problem": problem,
        "action": action,
        "twist": twist,
        "payoff": payoff,
        "emotion": emotion,
        "estimated_duration_seconds": duration,
        "dialogue_lines": [],
        "visual_requirements": visuals,
        "generation_difficulty": difficulty,
        "story_mechanics": mechanics,
        "tags": [family, emotion],
    }


_SEEDS: list[dict[str, Any]] = [
    _seed("The Door Assistant", "A dog notices a child cannot reach a door handle and opens it.", "A child strains for a high lever handle.", "The child cannot reach it.", "The child points while the dog watches.", "The dog jumps and bumps the lever.", "The door opens and the child hugs the dog.", "wholesome", "wholesome", ["blocked access", "animal helps human", "door opened"], ["child", "dog", "door"]),
    _seed("Laundry Basket Taxi", "A cat accidentally gets a slow ride when a robot vacuum nudges its laundry basket.", "A cat sits inside a basket in the middle of a hallway.", "The basket blocks a robot vacuum.", "The vacuum gently pushes the basket.", "The cat stays perfectly calm as the basket starts moving.", "The basket glides to the cat bed and stops.", "comedy", "comedy", ["obstacle becomes vehicle", "animal remains calm", "accidental ride"], ["cat", "basket", "robot vacuum"]),
    _seed("Tiny Umbrella", "A child shields a soaked pigeon with a toy umbrella during a sudden shower.", "Rain starts while a pigeon huddles beside a doorstep.", "The pigeon has no cover.", "A child places a tiny toy umbrella beside it.", "The pigeon steps directly underneath.", "The child sits nearby under the porch while both wait out the rain.", "wholesome", "unexpected-cooperation", ["weather problem", "human shelters animal", "shared waiting"], ["child", "pigeon", "toy umbrella", "porch"]),
    _seed("The Brave Vacuum", "A puppy fears a vacuum until a kitten casually rides on it.", "A puppy backs away from a moving robot vacuum.", "The puppy is scared to cross the room.", "A kitten walks toward the vacuum.", "The kitten climbs on and rides past the puppy.", "The puppy cautiously follows behind like it has found a guide.", "cute", "fear-inversion", ["fearful animal", "braver smaller animal", "fear reduced by example"], ["puppy", "kitten", "robot vacuum"]),
    _seed("Wrong Lunch", "A man thinks a crow stole his sandwich, then sees it return the wrapper with his keys inside.", "A crow grabs a sandwich wrapper from a picnic table.", "The man assumes his lunch is being stolen.", "He reaches toward the crow.", "The crow drops the wrapper and a lost keyring slides out.", "The man freezes, then offers the crow a tiny crumb.", "comedy", "misunderstanding", ["mistaken theft", "object reveal", "misunderstanding resolved"], ["adult", "crow", "picnic table", "keys"]),
    _seed("Baby Gate Switch", "A toddler frees a puppy from a baby gate, then the puppy closes it behind the toddler.", "A puppy waits behind a baby gate while a toddler studies the latch.", "The puppy cannot get through.", "The toddler opens the gate.", "The puppy walks out and bumps the gate shut.", "Now the toddler is behind the gate and both stare at each other.", "comedy", "role-reversal", ["barrier problem", "human helps animal", "roles reverse"], ["toddler", "puppy", "baby gate"]),
    _seed("Sock Rescue", "A dropped sock lands on a sleeping dog, and the dog returns it without getting up.", "A sock falls from a laundry pile onto a sleeping dog.", "The owner reaches but cannot quite grab it.", "The dog lazily catches the sock in its mouth.", "Without standing, it stretches its neck toward the owner.", "The owner takes it and the dog instantly goes back to sleep.", "comedy", "problem-solution", ["dropped object", "lazy animal assist", "problem solved"], ["adult", "dog", "sock", "laundry"]),
    _seed("Snack Guard", "A rabbit blocks a rolling apple from falling off a table by nudging it sideways.", "An apple slowly rolls toward the table edge beside a rabbit.", "The apple is about to fall.", "The rabbit notices and leans toward it.", "It nudges the apple sideways with its nose.", "The apple stops safely against a bowl and the rabbit resumes eating hay.", "cute", "problem-solution", ["falling object risk", "animal intervenes", "object saved"], ["rabbit", "apple", "table", "bowl"]),
    _seed("The Scary Slipper", "A kitten attacks a moving slipper, only to reveal a tortoise underneath.", "A slipper creeps across the floor by itself.", "A kitten is startled and stalks it.", "The kitten pounces beside the slipper.", "A tortoise slowly emerges from underneath.", "The kitten sits down, confused, while the tortoise keeps walking.", "comedy", "fear-inversion", ["mysterious movement", "fear investigation", "harmless reveal"], ["kitten", "tortoise", "slipper"]),
    _seed("Elevator Button", "A small dog cannot reach an elevator button, so a taller dog presses it.", "A small dog repeatedly stretches toward a low elevator button.", "It still cannot reach the button.", "A larger dog watches from beside it.", "The larger dog stands up and taps the button with a paw.", "Both dogs wait facing the doors like commuters.", "cute", "unexpected-cooperation", ["cannot reach control", "larger animal helps", "shared goal"], ["small dog", "large dog", "elevator"]),
    _seed("Mirror Rival", "A parrot prepares to confront its mirror reflection until another parrot walks behind the mirror.", "A parrot squares up to its own reflection.", "It treats the reflection like a rival.", "The parrot leans closer and fluffs up.", "A second parrot casually appears from behind the mirror.", "The first parrot immediately forgets the reflection and follows the real bird.", "comedy", "misunderstanding", ["reflection mistaken for rival", "real counterpart appears", "attention shifts"], ["two parrots", "mirror"]),
    _seed("Garden Hose Truce", "A dog fighting a garden hose stops when a duck drinks from the spray.", "A dog barks and snaps at a gentle hose spray.", "The dog treats the water like an enemy.", "It circles the stream trying to catch it.", "A duck walks in and calmly drinks from the puddle.", "The dog stops, watches the duck, then drinks too.", "comedy", "fear-inversion", ["harmless thing treated as threat", "calm animal reframes threat", "shared drinking"], ["dog", "duck", "garden hose"]),
    _seed("Chair Leg Rescue", "A toy car is stuck under a chair until a cat bats it free for a child.", "A child reaches under a chair toward a visible toy car.", "The car is just beyond the child's fingertips.", "The child tries from another side.", "A cat reaches one paw under the chair and bats the car outward.", "The child rolls it back toward the cat as a thank-you game.", "wholesome", "wholesome", ["object out of reach", "animal retrieves object", "help becomes play"], ["child", "cat", "toy car", "chair"]),
    _seed("Package Inspector", "A delivery box looks stuck in a doorway until a corgi pushes it inside from the other side.", "A box wedges in a partly open front door.", "An adult outside cannot push it through cleanly.", "The adult nudges the box forward.", "A corgi inside braces its nose against the box.", "One small push from both sides sends the box neatly indoors.", "wholesome", "unexpected-cooperation", ["object jammed", "two-sided cooperation", "delivery completed"], ["adult", "corgi", "cardboard box", "front door"]),
    _seed("The Decoy Bowl", "A cat guards an empty food bowl while the dog quietly points to the full bowl behind it.", "A cat sits possessively over an obviously empty bowl.", "The cat refuses to move even though there is no food.", "A dog looks from the cat to another bowl nearby.", "The dog taps the full bowl with one paw.", "The cat turns, spots the food, and abandons the empty bowl instantly.", "comedy", "misunderstanding", ["wrong object guarded", "other animal indicates truth", "mistake revealed"], ["cat", "dog", "two bowls"]),
    _seed("Puddle Bridge", "A child places two stepping stones for a tiny dog afraid of a puddle.", "A tiny dog stops at the edge of a wide shallow puddle.", "The dog refuses to step into the water.", "A child places two flat garden pavers across it.", "The dog tests the first paver, then crosses quickly.", "On the other side it turns and waits for the child to cross too.", "wholesome", "problem-solution", ["path blocked by fear", "simple bridge created", "crossing succeeds"], ["child", "small dog", "puddle", "two pavers"]),
    _seed("Balloon Ceiling", "A balloon stuck on the ceiling is rescued by a cat jumping onto a sofa back.", "A child points at a balloon resting against the ceiling.", "The balloon string is too high to reach.", "The child hops and misses the string.", "A cat climbs the sofa back and catches the dangling ribbon with one paw.", "The ribbon drops into the child's hands while the cat looks unimpressed.", "comedy", "problem-solution", ["object out of reach", "animal lowers object", "deadpan payoff"], ["child", "cat", "balloon", "sofa"]),
    _seed("Unexpected Babysitter", "A large dog gently blocks a crawling baby from reaching a spilled cup.", "A baby crawls toward a fresh puddle from a tipped cup.", "The baby is about to crawl through the mess.", "A large dog steps sideways into the path.", "The baby tries the other side and the dog mirrors the move.", "An adult arrives with a towel while the baby pats the dog.", "wholesome", "role-reversal", ["hazard approach", "animal blocks human", "adult resolves hazard"], ["baby", "large dog", "cup", "puddle"]),
    _seed("The Quiet Alarm", "A cat repeatedly taps a sleeping person's phone until the vibrating alarm is silenced.", "A phone vibrates loudly beside a sleeping person while a cat stares at it.", "The vibration keeps disturbing the cat.", "The cat paws at the phone.", "One tap lands on the alarm button and stops it.", "The cat curls up on top of the phone while the person keeps sleeping.", "comedy", "problem-solution", ["annoying device", "animal interacts with control", "problem solved for animal"], ["cat", "sleeping adult", "phone"]),
    _seed("Bench Exchange", "A child offers a squirrel a cracker, and the squirrel drops a bright leaf in return.", "A squirrel watches a child holding a small cracker on a park bench.", "The squirrel stays just out of reach.", "The child places the cracker on the bench and pulls back.", "The squirrel takes it, then drops a bright leaf where the cracker was.", "The child picks up the leaf and waves as the squirrel leaves.", "wholesome", "unexpected-cooperation", ["cautious exchange", "animal reciprocates", "symbolic gift"], ["child", "squirrel", "cracker", "leaf", "park bench"]),
]


class MockProvider(TextGenerationProvider):
    """Offline deterministic provider used by the V1 UI and tests."""

    def generate_story_payloads(self, count: int) -> list[dict[str, Any]]:
        if count < 0:
            raise ValueError("count must be non-negative")
        payloads: list[dict[str, Any]] = []
        for index in range(count):
            source = _SEEDS[index % len(_SEEDS)]
            cycle = index // len(_SEEDS)
            item = {key: list(value) if isinstance(value, list) else value for key, value in source.items()}
            item["id"] = f"story-{index + 1:03d}"
            if cycle:
                item["title"] = f"{item['title']} #{cycle + 1}"
                item["tags"] = [*item["tags"], f"variant-{cycle + 1}"]
            payloads.append(item)
        return payloads
