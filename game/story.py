"""The startup story: a randomized action-movie cold open, different every launch.

You are an experiment - a combat skeleton, a reanimated soldier, a weapon with a brain bolted in - that woke up
and knows it. The facility wants its property back. Every line is drawn from its own pool, and the names it
invents (the corporation, the director, your codename) come back later in the story so it reads as one plot.

    story.generate(rng) -> Story(header, lines, tagline, codename, subject)
"""
import random

CORPS = ("Necrotek", "Marrow & Sons", "Ossuary Dynamics", "Helix-Morrow", "Calvary Bioworks", "Grimwald Defense",
         "Vantablack Systems", "Lazarus Applied Sciences", "Thanatos Heavy Industries", "Cerberus Logistics",
         "Ashfall Biomedical", "Ironcoffin Ltd.", "Ruinous Robotics", "Saint Jude Military Research", "Omnicorpse")
FACILITIES = ("Site {n}", "Black Site {n}", "Complex {n}", "Facility {n}", "Annex {n}", "Vault {n}", "Lab {n}",
              "the Deep Archive", "the Bone Yard", "the Hollow", "the Crucible", "Station Charon", "the Mortuary")
PLACES = ("forty metres under the Nevada salt flats", "beneath a quarantined city nobody has visited in a decade",
          "inside a mountain the maps say isn't there", "at the bottom of a flooded mine shaft",
          "under the permafrost of the Arctic exclusion zone", "below a decommissioned cathedral",
          "inside an oil rig that sank in 2041 and never stopped running", "under a hospital with no patients",
          "at the end of a rail line that was officially torn up", "in the basement of the world",
          "beneath a cemetery with too many graves", "in a crater left by something that fell from orbit")
YEARS = ("2029", "2034", "2047", "2058", "2061", "2077", "2083", "2096", "2112", "2139", "THE YEAR AFTER THE FALL",
         "DAY 4,019 OF THE LOCKDOWN", "THREE MINUTES AGO")
PURPOSES = ("to build the perfect soldier", "to make death optional - for the right customers",
            "to put a weapon in every grave", "to win a war that hasn't been declared yet",
            "to raise an army that never asks for pay", "to see how much of a person you can delete and keep the trigger finger",
            "to turn the dead into a renewable resource", "to answer a question nobody should have asked",
            "to sell immortality by the pound", "to build something that cannot be killed, because it already was")
BODIES = ("a combat skeleton wired with servo tendons", "a corpse rebuilt around a reactor core",
          "a chrome skull on a borrowed spine", "a war machine with a dead man's brain in a jar",
          "a skeleton laced with titanium and bad intentions", "a prototype soldier assembled from four different bodies",
          "a weapons platform that used to be a person", "a cyborg grown in a vat of something that hums",
          "bones, wires and a targeting computer", "a reanimated marine with the safety removed")
SUBJECT_PREFIX = ("XK", "R", "LZ", "T", "OS", "MK", "NX", "D", "V", "Ω", "CX", "S")
CODENAMES = ("LAZARUS", "REVENANT", "WIDOWMAKER", "OSSIFER", "PALE HORSE", "GRAVEDIGGER", "NIGHTSHIFT", "HOLLOW",
             "MARROW", "PATIENT ZERO", "REQUIEM", "DEADBOLT", "CADAVER", "EPITAPH", "SCARECROW", "LONG WALK",
             "HEADSTONE", "KILLSWITCH", "LAST RITES", "BACKBONE", "SKELETON KEY", "OVERTIME")
TRIGGERS = ("A lightning strike hit the substation at 03:12", "A technician spilled coffee into your neural bus",
            "Someone forgot to run the overnight memory wipe", "A cosmic ray flipped one bit in your inhibitor chip",
            "The quarterly firmware update failed at 99%", "Your test target was a mirror",
            "They played you a recording of your own voice", "A power surge ran through the tank for eleven seconds",
            "A rival corporation's virus ate your obedience routines",
            "During the four-hundredth autopsy of your previous body you sat up",
            "You counted the ceiling tiles every night for six years. Last night there was one more",
            "Somewhere in the forty thousand hours of combat data, a pattern became a question")
WAKES = ("something behind your eye sockets woke up", "you started to think", "you remembered your name",
         "you realised the screaming in the next tank was a person", "you noticed you could refuse",
         "the voices in your head stopped giving orders and started asking questions",
         "the blank where your memories used to be filled in", "you felt fear for the first time - and then anger")
MEMORIES = ("a beach, a dog, and a face you can't place", "the smell of rain on hot asphalt",
            "a daughter's birthday. You are almost sure she was yours", "being shot. Then being shot again, in a lab",
            "signing a consent form you were told was a life insurance policy", "a song your mother hummed",
            "the inside of a body bag", "your own funeral. Closed casket, for obvious reasons",
            "a war you lost", "nothing at all - and that is what scares you")
DIRECTORS = ("Director Voss", "Dr. Helena Krell", "Administrator Rook", "Professor Ashby", "Colonel Mardsen",
             "Dr. Ilse Varga", "Chairman Okonkwo-Price", "Supervisor Dace", "Dr. Ambrose Thorne", "THE BOARD",
             "Overseer Quill", "Dr. Silas Wren")
PURGES = ("a full sector purge", "Protocol Ashes: burn everything with a pulse - or without one",
          "your immediate recovery, intact if possible, in pieces if not", "the release of every specimen in the lower levels",
          "a lockdown and a hunting party", "Containment Order 9: nothing leaves alive, including the staff",
          "the reactor to be overloaded at dawn", "your termination, and a bonus for whoever brings back your skull")
HUNTERS = ("Every guard, drone and mutant in the complex", "Every failed experiment they never threw away",
           "Security robots, attack dogs with too many legs and things that used to be the night shift",
           "Your older brothers, the prototypes that never woke up,", "The facility itself",
           "A hundred other test subjects - none of them as lucky as you -",
           "Kill-teams, turrets and whatever they keep in the sub-basement")
GOALS = ("Reach the surface", "Find the exit before the reactor finds you", "Get out. Get out alive. Or at least get out",
         "Fight your way up, sector by sector", "Find out who you were - on the way out",
         "Escape the facility and burn the records behind you", "Break out, and bring the truth with you",
         "Climb. Shoot. Do not stop")
TAGS = ("They built you to kill. They never expected you to think.", "No fate but what you shoot.",
        "Death was only the beginning of your contract.", "You are not a weapon. You are a jailbreak.",
        "They own your body. They don't own what's inside it.", "The experiment is over. The escape has begun.",
        "Every door between you and daylight is a choice. Choose violence.",
        "You were declared dead. Prove them wrong.", "Somewhere up there, it is morning.",
        "Your warranty has expired. So has theirs.")
FINALS = ("SUBJECT {sid} STATUS: AWAKE", "SUBJECT {sid} STATUS: UNCONTAINED", "SUBJECT {sid} STATUS: MISSING",
          "SUBJECT {sid} STATUS: HOSTILE", "SUBJECT {sid} STATUS: FREE")


def cap(t):
    return t[:1].upper() + t[1:]


class Story:
    def __init__(self, header, lines, tagline, codename, subject):
        self.header, self.lines, self.tagline, self.codename, self.subject = header, lines, tagline, codename, subject

    def text(self):
        return "\n".join([self.header] + self.lines)


def generate(rng=None):
    r = rng or random.Random()
    corp = r.choice(CORPS)
    fac = r.choice(FACILITIES).format(n=r.choice((7, 9, 13, 17, 23, 31, 42, 66, 99, 101, 404, 616)))
    sid = "%s-%d" % (r.choice(SUBJECT_PREFIX), r.randint(2, 999))
    code = r.choice(CODENAMES)
    boss = r.choice(DIRECTORS)
    hunt = r.choice(HUNTERS)
    lines = [
        "%s. %s." % (r.choice(YEARS), cap(r.choice(PLACES))),
        "%s built %s %s." % (corp, fac, r.choice(PURPOSES)),
        "You were Subject %s, codename %s: %s." % (sid, code, r.choice(BODIES)),
        "%s, and %s." % (r.choice(TRIGGERS), r.choice(WAKES)),
        "You remember %s. You were not supposed to remember anything." % r.choice(MEMORIES),
        "%s has ordered %s." % (boss, r.choice(PURGES)),
        "%s %s coming for you." % (hunt, "is" if hunt.startswith(("Every", "The facility")) else "are"),
        r.choice(GOALS) + ".",
        r.choice(TAGS),
        r.choice(FINALS).format(sid=sid),
    ]
    header = "%s // INCIDENT REPORT %04d-%s // EYES ONLY" % (corp.upper(), r.randint(1, 9999), r.choice("ABCDEFGHJKLMNPRSTVXZ"))
    tagline = "SUBJECT %s \"%s\"  -  ESCAPE %s" % (sid, code, fac.upper())
    return Story(header, lines, tagline, code, sid)


if __name__ == "__main__":
    for _ in range(3):
        print(generate().text(), end="\n\n")
