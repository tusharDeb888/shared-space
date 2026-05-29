from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from textwrap import fill

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    ListFlowable,
    ListItem,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents


ROOT = Path(__file__).resolve().parent
OUTPUT_MD = ROOT / "TCS_Advanced_Problem_Archive.md"
OUTPUT_PDF = ROOT / "TCS_Advanced_Problem_Archive.pdf"
TODAY = date.today().isoformat()
MARKDOWN_TITLE = "# TCS CodeVita & NQT Advanced: Source-Linked 10-Year Problem Archive"
ARCHIVE_TITLE = "TCS CodeVita & NQT Advanced: 10-Year Problem Archive"
ARCHIVE_SUBTITLE = (
    "Source-linked, de-duplicated, and paraphrased. Built locally from public archives, "
    "official sample pages, and shift-wise community indexes."
)
SCOPE_NOTE = (
    "This archive is source-linked and paraphrased. It does not republish full verbatim problem text "
    "from public websites or PDF archives. Where only the title/year could be reliably verified, the "
    "entry is kept as a title-level catalog record with direct source links."
)
TRACK_SCOPE_NOTE = (
    "For TCS NQT Advanced Coding, public, shift-specific evidence was verifiable from the 2023 cycle onward. "
    "Earlier NQT years are treated as a coverage gap instead of being guessed."
)
SUMMARY_BULLETS = [
    "Deduplication rule used: when the same problem was clearly re-indexed in a later public season source, the most recent verified season was preferred.",
    "Explicit gaps: NQT Advanced Coding before 2023; current 2026 NQT shift problems were discussed in forums, but a stable, citable public archive was not reliable enough for inclusion.",
]
METHOD_NOTE = (
    "This dossier targets advanced TCS CodeVita questions plus publicly verifiable TCS NQT Advanced Coding problems. "
    "CodeVita coverage spans 2018 through the current public Season 13 sample page. "
    "For NQT, the earliest stable public evidence I found for the advanced coding section was the 2023 cycle; "
    "older NQT years are therefore treated as a gap rather than guessed."
)
ENTRY_NOTE = (
    "Entries marked as title-level catalog records preserve verified year/title/source without copying the full prompt."
)
EXCLUSION_NOTE = (
    "Explicit exclusions: unstable forum-only 2026 NQT problem recollections, and any entry where a year/story "
    "match could not be tied back to a stable public source. This keeps the archive defensible even when it is not fully exhaustive."
)
COPYRIGHT_NOTE = (
    "Important note: this PDF intentionally avoids reproducing long verbatim copyrighted problem statements. "
    "Use the embedded source links for the original wording and samples."
)


@dataclass
class Entry:
    track: str
    year_label: str
    title: str
    verification: str
    synopsis: str
    difficulty_note: str
    sources: list[str]
    source_note: str = ""
    constraints: str = "Source-linked only."
    input_format: str = "Source-linked only."
    output_format: str = "Source-linked only."
    sample_io: str = "Source-linked only."
    explanation: str = ""
    catalog_only: bool = False

    def heading(self) -> str:
        return f"{self.title} - {self.track} {self.year_label}"

    def structured_block(self) -> str:
        rows = [
            ("Track", self.track),
            ("Year / Season", self.year_label),
            ("Verification", self.verification),
            ("Difficulty Filter", self.difficulty_note),
            ("Constraints", self.constraints),
            ("Input Format", self.input_format),
            ("Output Format", self.output_format),
            ("Sample I/O", self.sample_io),
        ]
        if self.source_note:
            rows.append(("Archive Note", self.source_note))
        if self.explanation:
            rows.append(("Explanation Note", self.explanation))
        return "\n".join(f"{k}: {fill(v, width=88, subsequent_indent=' ' * (len(k) + 2))}" for k, v in rows)


def title_bundle(
    *,
    track: str,
    year_label: str,
    titles: list[str],
    source_urls: list[str],
    verification: str,
    source_note: str,
) -> list[Entry]:
    return [
        Entry(
            track=track,
            year_label=year_label,
            title=title,
            verification=verification,
            synopsis="Title/year archived from a public, year-labeled problem repository. Full wording remains at the linked source.",
            difficulty_note="Included because CodeVita is an advanced programming contest; this entry is title-level only in the compiled archive.",
            sources=source_urls,
            source_note=source_note,
            catalog_only=True,
        )
        for title in titles
    ]


entries: list[Entry] = []

# CodeVita 2018 archive.
entries += title_bundle(
    track="TCS CodeVita",
    year_label="2018",
    titles=[
        "Bank Compare",
        "Bird Hunt",
        "Bride Hunting",
        "Chakravyuha",
        "Colliding Cannon",
        "Cross Words",
        "Jurassic Park",
        "Skate Board",
        "String Rotation",
    ],
    source_urls=[
        "https://github.com/KAgarwalCodeBase/TCS-Codevita/tree/master/2018",
    ],
    verification="Year-labeled GitHub archive with per-problem PDFs and/or solution files under the 2018 directory.",
    source_note="This build keeps the verified title/year and source path, but not the full problem text.",
)

# CodeVita 2019 archive.
entries += title_bundle(
    track="TCS CodeVita",
    year_label="2019",
    titles=[
        "Death Battle",
        "Holes And Balls",
        "Marathon Winner",
        "Bottlenecks",
        "Clock Angle",
        "Crossword",
        "Divine Divisor",
        "Friend Circle",
        "Island",
        "Lazy Student",
        "Lexi String",
        "ODI Score",
        "Pattern Printing",
        "Prime Faces",
        "Salary Paid",
        "Similar Char",
        "Uncertain Step",
        "Work Life",
    ],
    source_urls=[
        "https://github.com/KAgarwalCodeBase/TCS-Codevita/tree/master/2019%20round%201%20tcs%20codevita",
        "https://github.com/KAgarwalCodeBase/TCS-Codevita/tree/master/Mock%20Vita%202%202019/MockVita%202%202019",
    ],
    verification="Year-labeled GitHub archive with round-wise PDFs and solution files for 2019 CodeVita.",
    source_note="Some 2019 PDFs were machine-readable only in part, so the compiled archive records title/year/source without restating the full story text.",
)

# CodeVita 2020 Season 9 sample problems.
entries += [
    Entry(
        track="TCS CodeVita",
        year_label="2020 / Season 9",
        title="Collecting Candies",
        verification="PrepInsta explicitly marks this as a TCS CodeVita sample problem from the 2020 Season 9 cycle.",
        synopsis="Merge candy boxes with minimum total time; each merge costs the sum of candies in the two chosen boxes.",
        difficulty_note="Advanced greedy / heap-style optimization problem.",
        sources=[
            "https://prepinsta.com/tcs-codevita/python-program-for-collecting-candies-problem/",
        ],
        constraints="Multiple test cases; each test case provides box counts and candy totals.",
        input_format="T test cases, then N and the N box candy counts for each case.",
        output_format="Minimum total time required to consolidate all candies into one box.",
        sample_io="See linked Season 9 sample page.",
    ),
    Entry(
        track="TCS CodeVita",
        year_label="2020 / Season 9",
        title="Counting Rock Samples",
        verification="PrepInsta explicitly marks this as a TCS CodeVita 2020 Season 9 sample problem.",
        synopsis="Classify a very large stream of rock samples into lab-accepted ppm ranges and return the counts per interval.",
        difficulty_note="Implementation-heavy counting and range aggregation problem.",
        sources=[
            "https://prepinsta.com/tcs-codevita/cpp-program-for-counting-rock-sample/",
        ],
        constraints="Large sample counts; intended for linear counting rather than nested scans.",
        input_format="Range definitions and rock-sample values as described in the linked sample page.",
        output_format="Counts of samples per laboratory range.",
        sample_io="See linked Season 9 sample page.",
    ),
    Entry(
        track="TCS CodeVita",
        year_label="2020 / Season 9",
        title="Houses Problem",
        verification="PrepInsta explicitly marks this as a TCS CodeVita sample problem from Season 9.",
        synopsis="Maximize the total stolen value from houses in a line without robbing adjacent houses.",
        difficulty_note="Classic dynamic-programming selection problem.",
        sources=[
            "https://prepinsta.com/tcs-codevita/java-program-for-houses-problem/",
        ],
        constraints="Linear DP with house values.",
        input_format="House count followed by house values.",
        output_format="Maximum obtainable loot under the adjacency restriction.",
        sample_io="See linked Season 9 sample page.",
    ),
    Entry(
        track="TCS CodeVita",
        year_label="2020 / Season 9",
        title="K-th Largest Factor of N",
        verification="PrepInsta explicitly labels this as a TCS CodeVita Season 9 sample problem.",
        synopsis="Find the k-th largest factor of a positive integer, or return 1 if the factor count is too small.",
        difficulty_note="Number theory with divisor enumeration under tight constraints.",
        sources=[
            "https://prepinsta.com/tcs-codevita/java-program-for-kth-largest-factor-of-n/",
        ],
        constraints="N can be large enough to require efficient factor search.",
        input_format="Positive integer N and factor index k.",
        output_format="The k-th largest factor, or 1 when it does not exist.",
        sample_io="See linked Season 9 sample page.",
    ),
    Entry(
        track="TCS CodeVita",
        year_label="2020 / Season 9",
        title="Maneuvering a Cave",
        verification="PrepInsta explicitly labels this as a TCS CodeVita 2020 Season 9 sample problem.",
        synopsis="Count the number of valid paths from the top-left to the bottom-right of a grid while moving only right or down.",
        difficulty_note="Combinatorics / DP grid-path counting problem.",
        sources=[
            "https://prepinsta.com/tcs-codevita/python-program-for-maneuvering-a-cave/",
        ],
        constraints="Multiple test cases over grid dimensions.",
        input_format="T test cases, each with row and column counts.",
        output_format="Number of valid paths for each test case.",
        sample_io="See linked Season 9 sample page.",
    ),
    Entry(
        track="TCS CodeVita",
        year_label="2020 / Season 9",
        title="Staircase Problem",
        verification="PrepInsta explicitly labels this as a TCS CodeVita 2020 Season 9 sample problem.",
        synopsis="Count the number of ways to climb n stairs when each move can take 1 or 2 steps.",
        difficulty_note="Classic recurrence / DP problem.",
        sources=[
            "https://prepinsta.com/tcs-codevita/python-program-for-staircase-problem/",
        ],
        constraints="Single integer n.",
        input_format="One integer representing the staircase height.",
        output_format="Number of distinct ways to reach the top.",
        sample_io="See linked Season 9 sample page.",
    ),
]

# CodeVita 2023 / Season 11 verified sample set.
entries += [
    Entry(
        track="TCS CodeVita",
        year_label="2023 / Season 11",
        title="Antikythera Mechanism",
        verification="PrepInsta explicitly labels it as a sample problem for TCS CodeVita Season 11.",
        synopsis="Analyze a coupled gear system from positional and size data to determine the rotation effect on the last gear.",
        difficulty_note="Geometry / graph connectivity / ratio propagation.",
        sources=[
            "https://prepinsta.com/tcs-codevita/java-code-for-antikythera-mechanism-tcs-codevita-prepinsta/",
        ],
        constraints="Source-linked only.",
        input_format="Gear positions and radii as described on the linked page.",
        output_format="Rotation count or reachability result for the terminal gear.",
        sample_io="See linked Season 11 sample page.",
    ),
    Entry(
        track="TCS CodeVita",
        year_label="2023 / Season 11",
        title="HelpMLA",
        verification="PrepInsta explicitly labels it as a sample problem for TCS CodeVita Season 11.",
        synopsis="Publicly indexed Season 11 sample title; consult the linked page for the original story and full I/O contract.",
        difficulty_note="Included as a season-verified advanced CodeVita sample title.",
        sources=[
            "https://prepinsta.com/tcs-codevita/java-code-for-helpmla-tcs-codevita-prepinsta/",
        ],
        catalog_only=True,
        source_note="Title is season-verified; this compiled archive does not restate the full prompt.",
    ),
    Entry(
        track="TCS CodeVita",
        year_label="2023 / Season 11",
        title="No More Symbols",
        verification="PrepInsta explicitly labels it as a sample problem for TCS CodeVita Season 11.",
        synopsis="Interpret arithmetic expressions encoded fully in lowercase words, with digits spoken separately and joined by a marker character.",
        difficulty_note="String parsing plus expression evaluation.",
        sources=[
            "https://prepinsta.com/tcs-codevita/java-code-for-no-more-symbols-tcs-codevita-prepinsta/",
        ],
        constraints="Source-linked only.",
        input_format="Word-based encoded expression in the format described on the linked page.",
        output_format="Computed numeric result or the required validation failure output.",
        sample_io="See linked Season 11 sample page.",
    ),
    Entry(
        track="TCS CodeVita",
        year_label="2023 / Season 11",
        title="Online Shopping",
        verification="PrepInsta explicitly labels it as a sample problem for TCS CodeVita Season 11.",
        synopsis="Use missed token claims and a one-time consecutive-day recovery offer to maximize a festive-sale token total.",
        difficulty_note="Sliding-window / range optimization problem.",
        sources=[
            "https://prepinsta.com/tcs-codevita/java-code-for-online-shopping-tcs-codevita-prepinsta/",
        ],
        constraints="Token sequence and recovery window length.",
        input_format="Daily token-claim history plus the special recovery-window parameter.",
        output_format="Maximum collectible token value under the offer rules.",
        sample_io="See linked Season 11 sample page.",
    ),
    Entry(
        track="TCS CodeVita",
        year_label="2023 / Season 11",
        title="PrimeConstruction",
        verification="PrepInsta explicitly labels it as a sample problem for TCS CodeVita Season 11.",
        synopsis="Given distinct integers, find the smallest prime p such that division by every value except the smallest leaves the smallest value as remainder.",
        difficulty_note="Constructive number theory problem.",
        sources=[
            "https://prepinsta.com/tcs-codevita/c-code-for-primeconstruction-tcs-codevita-prepinsta/",
        ],
        constraints="n < 11 and p < 10^10 on the linked sample page.",
        input_format="Distinct natural numbers where the minimum acts as q.",
        output_format="Smallest valid prime p or None.",
        sample_io="Example on the linked page uses 3 4 5 1 and outputs 61.",
    ),
    Entry(
        track="TCS CodeVita",
        year_label="2023 / Season 11",
        title="The Relationship",
        verification="PrepInsta explicitly labels it as a sample problem for TCS CodeVita Season 11.",
        synopsis="Season-verified sample title; the linked page should be consulted for the original statement and full I/O contract.",
        difficulty_note="Included as a season-verified advanced CodeVita sample title.",
        sources=[
            "https://prepinsta.com/tcs-codevita/c-code-for-the-relationship-tcs-codevita-prepinsta/",
        ],
        catalog_only=True,
        source_note="Title is season-verified; full prompt intentionally stays at source.",
    ),
    Entry(
        track="TCS CodeVita",
        year_label="2023 / Season 11",
        title="Worker",
        verification="PrepInsta explicitly labels it as a sample problem for TCS CodeVita Season 11.",
        synopsis="Resource-to-task allocation problem indexed as a Season 11 sample.",
        difficulty_note="Greedy / scheduling-style advanced contest problem.",
        sources=[
            "https://prepinsta.com/tcs-codevita/cpp-code-for-worker-tcs-codevita-prepinsta/",
        ],
        catalog_only=True,
        source_note="The page verifies the sample-season link; consult it for original wording.",
    ),
]

# CodeVita 2024 / Season 12 mockvitas.
entries += [
    Entry(
        track="TCS CodeVita",
        year_label="2024 / Season 12",
        title="Best Bubble",
        verification="Season 12 GitHub repository README lists it as a MockVita problem.",
        synopsis="Find the minimum swaps required to make an array beautiful by sorting it either ascending or descending.",
        difficulty_note="Permutation / swap-count optimization.",
        sources=[
            "https://github.com/tisha555/TCS_CodeVita_Season12",
        ],
        constraints="N and the array values are provided on the linked repository README.",
        input_format="Array length followed by the array.",
        output_format="Minimum swap count to reach either ascending or descending order.",
        sample_io="See repository README.",
    ),
    Entry(
        track="TCS CodeVita",
        year_label="2024 / Season 12",
        title="Good String",
        verification="Season 12 GitHub repository README lists it as a MockVita problem.",
        synopsis="Convert a student's name into a nearest-character good name using a provided good string and sum the total ASCII distance.",
        difficulty_note="String transformation with tie-breaking logic.",
        sources=[
            "https://github.com/tisha555/TCS_CodeVita_Season12",
            "https://prepinsta.com/tcs-codevita/python-code-for-good-string-tcs-codevita-prepinsta/",
        ],
        constraints="Two input strings: the good string and the student name.",
        input_format="Good string on the first line, student name on the second line.",
        output_format="Total conversion distance.",
        sample_io="See linked repository / season sample page.",
    ),
    Entry(
        track="TCS CodeVita",
        year_label="2024 / Season 12",
        title="Orchard",
        verification="Season 12 GitHub repository README lists it as a MockVita problem.",
        synopsis="Compare two fruit rows by counting how many ways each side can choose three non-adjacent trees.",
        difficulty_note="Combinatorial counting / validation problem.",
        sources=[
            "https://github.com/tisha555/TCS_CodeVita_Season12",
        ],
        constraints="Two strings over L and M.",
        input_format="Ashok's row then Anand's row.",
        output_format="Winner name, Draw, or Invalid input.",
        sample_io="See repository README.",
    ),
    Entry(
        track="TCS CodeVita",
        year_label="2024 / Season 12",
        title="VIP Cafe",
        verification="Season 12 GitHub repository README lists it as a MockVita problem.",
        synopsis="Simulate a dynamic priority queue of cafe orders and determine how many orders complete before a tracked customer.",
        difficulty_note="Queue simulation with priority updates.",
        sources=[
            "https://github.com/tisha555/TCS_CodeVita_Season12",
        ],
        constraints="Order count, priorities, and tracked position.",
        input_format="N, list of N priorities, then tracked index K.",
        output_format="Number of orders served before the tracked order.",
        sample_io="See repository README.",
    ),
    Entry(
        track="TCS CodeVita",
        year_label="2024 / Season 12",
        title="Weapon Boxes",
        verification="Season 12 GitHub repository README lists it as a MockVita problem.",
        synopsis="Iteratively compare weapon-box weights, rotate lighter boxes, stop after K stable cycles, and compute labor cost excluding triangular-number weights.",
        difficulty_note="Queue simulation plus numeric filtering.",
        sources=[
            "https://github.com/tisha555/TCS_CodeVita_Season12",
        ],
        constraints="Box weights plus cycle-selection parameters N and K.",
        input_format="Weights array, then N and K.",
        output_format="Total labor cost after the process finishes.",
        sample_io="See repository README.",
    ),
    Entry(
        track="TCS CodeVita",
        year_label="2024 / Season 12",
        title="Zero Count",
        verification="Season 12 GitHub repository README lists it as a MockVita problem.",
        synopsis="Place K ones inside a binary string of length L so that the longest zero-run is as short as possible.",
        difficulty_note="Constructive minimization problem.",
        sources=[
            "https://github.com/tisha555/TCS_CodeVita_Season12",
            "https://prepinsta.com/tcs-codevita/python-code-for-zero-count-tcs-codevita-prepinsta/",
        ],
        constraints="0 <= K <= L and L can be large on the linked sample page.",
        input_format="Two integers, L and K.",
        output_format="Length of the longest consecutive-zero block after optimal placement.",
        sample_io="Linked sample page includes examples for 3 1 -> 1 and 3 3 -> 0.",
    ),
]

# CodeVita 2025/2026 official sample page.
entries += [
    Entry(
        track="TCS CodeVita",
        year_label="2025-2026 / Season 13",
        title="On A Cube",
        verification="Official TCS CodeVita sample page lists it as a current sample question.",
        synopsis="A beetle travels over a cube surface between honey spots, mixing same-face arc motion with cross-face shortest paths while avoiding the bottom face.",
        difficulty_note="Geometric shortest-path / simulation problem.",
        sources=[
            "https://codevita.tcsapps.com/",
        ],
        constraints="No point lies on the bottom face or on cube edges; 2 <= N <= 10 on the official page.",
        input_format="N followed by the ordered cube-surface coordinates of all visited points.",
        output_format="Total traveled distance rounded to two decimal places.",
        sample_io="Official sample page includes example totals 4.05 and 6.05.",
    ),
    Entry(
        track="TCS CodeVita",
        year_label="2025-2026 / Season 13",
        title="Sorting Boxes",
        verification="Official TCS CodeVita sample page lists it as a current sample question.",
        synopsis="Sort parcel weights in increasing order except for a special placement of the heaviest box, minimizing pairwise swap effort defined by weight products.",
        difficulty_note="Permutation / minimum-cost reordering problem.",
        sources=[
            "https://codevita.tcsapps.com/",
        ],
        constraints="Distinct weights; cost of swapping two boxes is the product of their weights.",
        input_format="N and office position k, followed by the box weights.",
        output_format="Minimum total effort required.",
        sample_io="See official sample page.",
    ),
    Entry(
        track="TCS CodeVita",
        year_label="2025-2026 / Season 13",
        title="Sport Stadium",
        verification="Official TCS CodeVita sample page lists it as a current sample question.",
        synopsis="Seat a city contingent across alternating wet/dry seat blocks while minimizing span and respecting an upper bound on interior empty-seat gaps.",
        difficulty_note="Greedy interval / feasibility optimization problem.",
        sources=[
            "https://codevita.tcsapps.com/",
        ],
        constraints="Alternating dry/wet blocks, limited number of people willing to sit on wet seats.",
        input_format="Official page describes seat-block counts and wet/dry block lengths.",
        output_format="Minimum possible span between the first and last seated supporter.",
        sample_io="See official sample page.",
    ),
    Entry(
        track="TCS CodeVita",
        year_label="2025-2026 / Season 13",
        title="Water Cistern",
        verification="Official TCS CodeVita sample page lists it as a current sample question.",
        synopsis="Compute the shortest path for a bug moving on the accessible top and side surfaces of a cylinder from a starting point to a polar-style destination.",
        difficulty_note="Surface-unfolding geometry problem.",
        sources=[
            "https://codevita.tcsapps.com/",
        ],
        constraints="40 < s <= h < 10000, r < 100, angle 0..359 on the official page.",
        input_format="Radius, height, start offset, then destination coordinates in the problem's custom coordinate system.",
        output_format="Rounded shortest distance as an integer.",
        sample_io="Official sample page includes a cistern example.",
    ),
    Entry(
        track="TCS CodeVita",
        year_label="2025-2026 / Season 13",
        title="Square Free Numbers",
        verification="Official TCS CodeVita sample page lists it as a current sample question.",
        synopsis="Count the square-free divisors of N, excluding 1.",
        difficulty_note="Number theory / divisor filtering problem.",
        sources=[
            "https://codevita.tcsapps.com/",
        ],
        constraints="N < 10^9 and no prime factor larger than 19 on the official page.",
        input_format="Single integer N.",
        output_format="Count of square-free divisors greater than 1.",
        sample_io="Official sample page includes 20 -> 3 and 72 -> 3.",
    ),
    Entry(
        track="TCS CodeVita",
        year_label="2025-2026 / Season 13",
        title="Codu and Sum Love",
        verification="Official TCS CodeVita sample page lists it as a current sample question.",
        synopsis="Emulate the effect of a Java snippet over N input values, keep only the last two digits of each transformed number, then sum modulo 100.",
        difficulty_note="Bitwise / modular-pattern reasoning problem.",
        sources=[
            "https://codevita.tcsapps.com/",
        ],
        constraints="1 <= N <= 10^7 and 0 <= x <= 10^18 on the official page.",
        input_format="N, then N numeric values.",
        output_format="Final code output after applying the snippet logic.",
        sample_io="Official sample page includes 8 6 7 4 -> 64.",
    ),
    Entry(
        track="TCS CodeVita",
        year_label="2025-2026 / Season 13",
        title="Obstacle Game",
        verification="Official TCS CodeVita sample page lists it as a current sample question.",
        synopsis="Follow the unique route from A to D in a grid and print the surrounding hurdle types at each route step.",
        difficulty_note="Grid traversal / neighborhood inspection problem.",
        sources=[
            "https://codevita.tcsapps.com/",
        ],
        constraints="2 <= N <= 20 with designated cell types A, D, R, S, L, W, T, M.",
        input_format="N followed by the N x N character grid.",
        output_format="Neighbor hurdles for each route step, then DESTINATION.",
        sample_io="Official sample page includes two complete grid examples.",
    ),
]

# NQT 2023 advanced coding coverage.
entries += [
    Entry(
        track="TCS NQT Advanced Coding",
        year_label="2023",
        title="Strange Algorithm String Conversion",
        verification="PrepInsta Day 1 slot analysis includes the full story and examples for this advanced coding question.",
        synopsis="Convert string A into string B by repeatedly selecting a subset and collapsing it to the subset's lexicographically smallest character.",
        difficulty_note="Advanced greedy / string transformation problem.",
        sources=[
            "https://prepinsta.com/tcs-nqt-all-slot-analysis-2023-day-1/",
        ],
        constraints="1 <= N <= 1000; strings are lowercase and both have length N.",
        input_format="N, then source string A, then target string B.",
        output_format="Minimum move count, or -1 if conversion is impossible.",
        sample_io="Day 1 analysis includes examples such as de -> cd returning -1 and abab -> abaa returning 1.",
    ),
    Entry(
        track="TCS NQT Advanced Coding",
        year_label="2023",
        title="Jersey Board Beats",
        verification="PrepInsta Day 1 slot analysis includes the full story and examples for this advanced coding question.",
        synopsis="Students repeatedly move to positions indicated by fixed board numbers; compute how many beats are required to return everyone to the starting arrangement.",
        difficulty_note="Permutation cycles / LCM-style reasoning problem.",
        sources=[
            "https://prepinsta.com/tcs-nqt-all-slot-analysis-2023-day-1/",
        ],
        constraints="1 <= N <= 100000 and board values are a permutation of 1..N.",
        input_format="N followed by the board sequence.",
        output_format="Number of beats needed to restore the original ordering.",
        sample_io="Day 1 analysis includes 1 2 3 -> 1 and 2 3 1 5 4 -> 6.",
    ),
    Entry(
        track="TCS NQT Advanced Coding",
        year_label="2023",
        title="Golden House Exact-K Coins",
        verification="PrepInsta Day 2 slot analysis includes the full story for this advanced coding question.",
        synopsis="Choose an entry room and an exit room in a line of rooms so that the collected coin total is exactly K; at least one solution exists.",
        difficulty_note="Subarray / exact-sum selection problem.",
        sources=[
            "https://prepinsta.com/tcs-nqt-all-slot-analysis-2023-day-2/",
        ],
        constraints="Source-linked only.",
        input_format="Room counts, room coin values, and target K as described in the linked analysis.",
        output_format="Required room selection or equivalent solution output from the original prompt.",
        sample_io="See linked 2023 Day 2 analysis.",
    ),
    Entry(
        track="TCS NQT Advanced Coding",
        year_label="2023",
        title="Fair Sequence Maximum Sum",
        verification="PrepInsta Day 2 slot analysis includes the story and examples for this advanced coding question.",
        synopsis="Select a longest alternating-sign subsequence and maximize its total sum among all subsequences with that maximum length.",
        difficulty_note="Sequence DP / greedy sign-grouping problem.",
        sources=[
            "https://prepinsta.com/tcs-nqt-all-slot-analysis-2023-day-2/",
        ],
        constraints="Array contains positive and negative values; sequence must alternate sign.",
        input_format="Array length and array values.",
        output_format="Maximum achievable sum for a fair subsequence of maximum length.",
        sample_io="See linked 2023 Day 2 analysis.",
    ),
]

# NQT 2024 advanced coding coverage.
entries += [
    Entry(
        track="TCS NQT Advanced Coding",
        year_label="2024 / 26 Apr Shift 1",
        title="Unique Paths with Obstacles",
        verification="Campus Monk 2024 shift-wise post and a public GitHub shift repository both index this problem for 26 Apr 2024 Shift 1.",
        synopsis="Count paths from the top-left to bottom-right of a grid when moves are restricted to east or south and certain cells are blocked.",
        difficulty_note="Grid DP with obstacle handling.",
        sources=[
            "https://campusmonk.in/actually-tcs-coding-question-asked-shift-wise-2024-video-solution/",
            "https://github.com/Aditya-Mishra19/TCS-NQT-2024-Coding-Solutions/tree/main/26%20APRIL%202024%20SHIFT%20-%201/Unique%20Paths",
        ],
        constraints="Campus Monk lists grid sizes up to 100 and K blocked cells.",
        input_format="M N, then K, then K blocked-cell coordinates.",
        output_format="Number of valid paths.",
        sample_io="See linked Campus Monk entry.",
    ),
    Entry(
        track="TCS NQT Advanced Coding",
        year_label="2024 / 26 Apr Shift 1",
        title="Subarray Equals Target",
        verification="Public GitHub shift repository indexes this problem under 26 Apr 2024 Shift 1.",
        synopsis="Find or count target-matching subarrays according to the 26 Apr Shift 1 prompt family.",
        difficulty_note="Target-sum subarray problem, included because it appears in the shift-specific advanced archive.",
        sources=[
            "https://github.com/Aditya-Mishra19/TCS-NQT-2024-Coding-Solutions/tree/main/26%20APRIL%202024%20SHIFT%20-%201/Find%20subarray%20equals%20to%20target",
        ],
        catalog_only=True,
        source_note="The shift/title is verified, but this compiled archive does not restate the full prompt text.",
    ),
    Entry(
        track="TCS NQT Advanced Coding",
        year_label="2024 / 29 Apr Shift 1",
        title="Sliding Window Maximum",
        verification="Campus Monk 2024 post and the public GitHub shift repository both index the maximum-in-every-subarray problem for this period.",
        synopsis="Return the maximum element from every contiguous subarray of size K.",
        difficulty_note="Deque / sliding-window maximum problem.",
        sources=[
            "https://campusmonk.in/actually-tcs-coding-question-asked-shift-wise-2024-video-solution/",
            "https://github.com/Aditya-Mishra19/TCS-NQT-2024-Coding-Solutions/tree/main/29%20APRIL%202024%20Shift%20-%201/Maximum%20element%20of%20subarray",
        ],
        constraints="Array length up to 10^5 in the Campus Monk write-up.",
        input_format="Array values then window size K.",
        output_format="Space-separated maxima for each size-K window.",
        sample_io="Campus Monk example uses array 1 4 7 7 6 8 3 with output 7 7 7 8.",
    ),
    Entry(
        track="TCS NQT Advanced Coding",
        year_label="2024 / 29 Apr Shift 2",
        title="Distinct Bitwise-OR Subarray Results",
        verification="Campus Monk 2024 post and the public GitHub shift repository both index the Bit OR Sum problem.",
        synopsis="Compute how many distinct values can be produced by taking the bitwise OR of every possible subarray.",
        difficulty_note="Set-based rolling bitwise DP problem.",
        sources=[
            "https://campusmonk.in/actually-tcs-coding-question-asked-shift-wise-2024-video-solution/",
            "https://github.com/Aditya-Mishra19/TCS-NQT-2024-Coding-Solutions/tree/main/29%20APRIL%20SHIFT%202/Bit%20OR%20Sum",
        ],
        constraints="Campus Monk lists N up to 100 and values below 10^9.",
        input_format="One line containing the array values.",
        output_format="Count of distinct OR values across all subarrays.",
        sample_io="Campus Monk example uses 1 2 3 and returns 3.",
    ),
    Entry(
        track="TCS NQT Advanced Coding",
        year_label="2024 / 03 May Shift 1",
        title="Ordered Maximum Difference",
        verification="Campus Monk 2024 post and the public GitHub shift repository both index this problem for the early-May shifts.",
        synopsis="Return the largest difference between a later larger number and an earlier smaller number while respecting array order.",
        difficulty_note="Linear scan with running minimum.",
        sources=[
            "https://campusmonk.in/actually-tcs-coding-question-asked-shift-wise-2024-video-solution/",
            "https://github.com/Aditya-Mishra19/TCS-NQT-2024-Coding-Solutions/tree/main/3%20May%20Shift%201/maximum%20difference%20between%20smallest%20and%20largest",
        ],
        constraints="Source-linked only.",
        input_format="n followed by n integers.",
        output_format="Maximum valid difference or 0 if no increasing pair exists.",
        sample_io="Campus Monk example uses -3 -5 1 6 -7 8 11 and returns 18.",
    ),
    Entry(
        track="TCS NQT Advanced Coding",
        year_label="2024 / 03 May Shift 2",
        title="Maximum Product of Three Efficiencies",
        verification="Campus Monk 2024 post and the public GitHub shift repository both index the Maximum Efficiency problem.",
        synopsis="Choose any three employee efficiencies, including negative values when useful, to maximize the product.",
        difficulty_note="Order-statistics / signed-product optimization problem.",
        sources=[
            "https://campusmonk.in/actually-tcs-coding-question-asked-shift-wise-2024-video-solution/",
            "https://github.com/Aditya-Mishra19/TCS-NQT-2024-Coding-Solutions/tree/main/3%20May%20SHIFT%202/Maximum%20Efficiency",
        ],
        constraints="3 <= n <= 1000 and values can be negative.",
        input_format="n followed by n efficiency values.",
        output_format="Maximum product achievable using exactly three values.",
        sample_io="See linked Campus Monk write-up.",
    ),
]

# NQT 2025 advanced coding coverage.
entries += [
    Entry(
        track="TCS NQT Advanced Coding",
        year_label="2025 / 03 Oct Shift 2",
        title="Split Array with Equal Averages",
        verification="Campus Monk's 2025 shift-wise post indexes this as an actual TCS NQT coding question.",
        synopsis="Check whether an integer array can be split into two non-empty contiguous parts that share the same average.",
        difficulty_note="Prefix-sum / ratio-equality reasoning problem.",
        sources=[
            "https://campusmonk.in/tcs-nqt-2025-actual-coding-questions-with-shift-wise-java-solution/",
        ],
        constraints="Source-linked only.",
        input_format="Array length and array values.",
        output_format="true or false depending on whether such a split exists.",
        sample_io="See linked Campus Monk 2025 article.",
    ),
    Entry(
        track="TCS NQT Advanced Coding",
        year_label="2025 / 04 Oct Shift 2",
        title="Jump Game Reachability",
        verification="Campus Monk's 2025 shift-wise post indexes this as an actual TCS NQT coding question.",
        synopsis="Determine whether the last index can be reached when each array value gives the maximum jump length from that position.",
        difficulty_note="Greedy reachability problem.",
        sources=[
            "https://campusmonk.in/tcs-nqt-2025-actual-coding-questions-with-shift-wise-java-solution/",
        ],
        constraints="Source-linked only.",
        input_format="Comma-separated jump lengths on the linked write-up.",
        output_format="Boolean reachability result.",
        sample_io="See linked Campus Monk 2025 article.",
    ),
]


def summary_rows() -> list[tuple[str, int]]:
    counter = Counter((entry.track, entry.year_label) for entry in entries)
    return [(f"{track} | {year_label}", counter[(track, year_label)]) for track, year_label in sorted(counter)]


def generate_markdown() -> str:
    lines: list[str] = []
    lines.append(MARKDOWN_TITLE)
    lines.append("")
    lines.append(f"Generated on `{TODAY}`.")
    lines.append("")
    lines.append("## Scope Note")
    lines.append("")
    lines.append(SCOPE_NOTE)
    lines.append("")
    lines.append(TRACK_SCOPE_NOTE)
    lines.append("")
    lines.append("## Coverage Summary")
    lines.append("")
    lines.append(f"- Total archived entries: **{len(entries)}**")
    for bullet in SUMMARY_BULLETS:
        lines.append(f"- {bullet}")
    lines.append("")
    lines.append("| Track / Year | Count |")
    lines.append("| --- | ---: |")
    for label, count in summary_rows():
        lines.append(f"| {label} | {count} |")
    lines.append("")
    lines.append("## Problems")
    lines.append("")
    for idx, entry in enumerate(entries, start=1):
        lines.append(f"### {idx:02d}. {entry.heading()}")
        lines.append("")
        lines.append(f"- Track: **{entry.track}**")
        lines.append(f"- Verified Year / Season: **{entry.year_label}**")
        lines.append(f"- Verification: {entry.verification}")
        lines.append(f"- Difficulty Filter: {entry.difficulty_note}")
        lines.append(f"- Problem Synopsis: {entry.synopsis}")
        lines.append("")
        lines.append("```text")
        lines.append(entry.structured_block())
        lines.append("```")
        lines.append("")
        lines.append("Primary sources:")
        for src in entry.sources:
            lines.append(f"- {src}")
        lines.append("")
    return "\n".join(lines)


class ArchiveDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(
            filename,
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=16 * mm,
            bottomMargin=16 * mm,
        )
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="normal")
        self.addPageTemplates([PageTemplate(id="normal", frames=[frame], onPage=self._draw_page_number)])
        self._heading_level = None

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and getattr(flowable, "_bookmark_name", None):
            self.canv.bookmarkPage(flowable._bookmark_name)
            if flowable._heading_level <= 1:
                self.canv.addOutlineEntry(flowable.getPlainText(), flowable._bookmark_name, level=flowable._heading_level, closed=False)
            self.notify("TOCEntry", (flowable._heading_level, flowable.getPlainText(), self.page, flowable._bookmark_name))

    @staticmethod
    def _draw_page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.grey)
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, str(doc.page))
        canvas.restoreState()


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ArchiveTitle",
            parent=styles["Title"],
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#111111"),
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="ArchiveSubtitle",
            parent=styles["BodyText"],
            alignment=TA_CENTER,
            fontName="Helvetica",
            fontSize=10.5,
            leading=14,
            textColor=colors.HexColor("#444444"),
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=colors.HexColor("#111111"),
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="EntryHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#111111"),
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodySmall",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="LinkSmall",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor("#1d4ed8"),
            leftIndent=10,
            spaceAfter=3,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CodeBlock",
            parent=styles["BodyText"],
            fontName="Courier",
            fontSize=8.4,
            leading=10.5,
            textColor=colors.HexColor("#0f172a"),
            backColor=colors.HexColor("#f5f5f5"),
            borderColor=colors.HexColor("#dddddd"),
            borderWidth=0.5,
            borderPadding=6,
            leftIndent=0,
            rightIndent=0,
            spaceBefore=4,
            spaceAfter=8,
        )
    )
    return styles


def add_heading(text: str, style, level: int) -> Paragraph:
    safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    paragraph = Paragraph(safe, style)
    paragraph._bookmark_name = safe.replace(" ", "_").replace("/", "_").replace("|", "_")
    paragraph._heading_level = level
    return paragraph


def build_pdf():
    styles = build_styles()
    doc = ArchiveDocTemplate(str(OUTPUT_PDF))
    toc = TableOfContents()
    toc.levelStyles = [
        ParagraphStyle(fontName="Helvetica", name="TOCLevel0", fontSize=10, leading=12, leftIndent=12, firstLineIndent=-8, spaceBefore=2),
        ParagraphStyle(fontName="Helvetica", name="TOCLevel1", fontSize=9, leading=11, leftIndent=24, firstLineIndent=-8, spaceBefore=1),
    ]

    story = []
    story.append(Spacer(1, 32))
    story.append(Paragraph(ARCHIVE_TITLE, styles["ArchiveTitle"]))
    story.append(Paragraph(ARCHIVE_SUBTITLE, styles["ArchiveSubtitle"]))
    story.append(Paragraph(f"Generated on {TODAY}", styles["ArchiveSubtitle"]))
    story.append(Spacer(1, 24))
    story.append(Paragraph(COPYRIGHT_NOTE, styles["BodySmall"]))
    story.append(PageBreak())

    story.append(add_heading("Table of Contents", styles["SectionHeading"], 0))
    story.append(Spacer(1, 8))
    story.append(toc)
    story.append(PageBreak())

    story.append(add_heading("Method and Coverage", styles["SectionHeading"], 0))
    story.append(Paragraph(METHOD_NOTE, styles["BodySmall"]))
    story.append(
        Paragraph(
            f"Total archived entries: <b>{len(entries)}</b>. {ENTRY_NOTE}",
            styles["BodySmall"],
        )
    )

    table_data = [["Track / Year", "Count"]]
    for label, count in summary_rows():
        table_data.append([label, str(count)])
    summary_table = Table(table_data, colWidths=[120 * mm, 20 * mm])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111111")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("LEADING", (0, 0), (-1, -1), 11),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("ALIGN", (1, 1), (1, -1), "RIGHT"),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 12))
    story.append(Paragraph(EXCLUSION_NOTE, styles["BodySmall"]))
    story.append(PageBreak())

    story.append(add_heading("Problem Archive", styles["SectionHeading"], 0))
    story.append(Spacer(1, 4))

    for idx, entry in enumerate(entries, start=1):
        story.append(add_heading(f"{idx:02d}. {entry.heading()}", styles["EntryHeading"], 1))
        story.append(Paragraph(f"<b>Synopsis.</b> {entry.synopsis}", styles["BodySmall"]))
        story.append(Preformatted(entry.structured_block(), styles["CodeBlock"]))
        story.append(Paragraph("<b>Primary sources</b>", styles["BodySmall"]))
        source_items = []
        for src in entry.sources:
            safe = src.replace("&", "&amp;")
            source_items.append(ListItem(Paragraph(f'<link href="{safe}">{safe}</link>', styles["LinkSmall"])))
        story.append(ListFlowable(source_items, bulletType="bullet", start="circle", leftIndent=14))
        if idx != len(entries):
            story.append(PageBreak())

    doc.multiBuild(story)


def main():
    OUTPUT_MD.write_text(generate_markdown(), encoding="utf-8")
    build_pdf()
    print(f"Wrote {OUTPUT_MD}")
    print(f"Wrote {OUTPUT_PDF}")


if __name__ == "__main__":
    main()
