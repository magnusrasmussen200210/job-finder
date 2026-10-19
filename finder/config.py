"""Alt det, Magnus kan have lyst til at justere: søgeord, filtre og område."""
import re

# Søgninger der køres på hvert jobsite. Jobindex og Jobnet er danske, LinkedIn får også de engelske.
QUERIES_DA = [
    "controller",
    "business analyst",
    "forretningsanalytiker",
    "analytiker",
    "dataanalytiker",
    "data analyst",
    "business intelligence",
    "power bi",
    "økonomiassistent",
    "økonomimedarbejder",
    "regnskabsassistent",
    "bogholder",
    "finance assistant",
    "financial analyst",
    "planner",
    "planlægger",
    "indkøbsassistent",
    "supply chain analyst",
    "pricing",
    "barselsvikariat",
    "junior økonomi",
]
QUERIES_LINKEDIN = [
    "controller",
    "business analyst",
    "data analyst",
    "financial analyst",
    "BI analyst",
    "finance",
    "økonomi",
    "analytiker",
    "planner",
    "barselsvikariat",
]

# Jobbet skal ligge inden for ca. 1 times kørsel fra Aarhus C. Afgøres ud fra postnummer.
ALLOWED_POSTCODES = (
    [(8000, 8304), (8306, 8999)]          # Østjylland og Midtjylland (Aarhus, Randers, Silkeborg, Horsens, Viborg, Djursland), ikke Samsø
    + [(7000, 7184)]                      # Fredericia, Vejle, Juelsminde, Tørring
    + [(7300, 7362)]                      # Jelling, Give, Brande, Ejstrupholm
    + [(7400, 7451), (7470, 7470)]        # Herning, Ikast, Bording, Sunds, Karup
    + [(9500, 9500), (9550, 9550)]        # Hobro, Mariager
)
# Bynavne inden for området, bruges når der ikke er et postnummer (fx "Aarhus, Silkeborg eller Kolding").
ALLOWED_TOWNS = re.compile(
    r"aarhus|århus|risskov|viby|højbjerg|brabrand|lystrup|skejby|tilst|hasselager|harlev|tranbjerg|egå|åbyhøj|"
    r"skanderborg|galten|hørning|ry\b|odder|hinnerup|hadsten|hammel|randers|silkeborg|horsens|hedensted|"
    r"viborg|bjerringbro|grenaa|grenå|ebeltoft|rønde|kolind|herning|ikast|brande|vejle|fredericia|"
    r"juelsminde|give\b|hobro|mariager|langå|kjellerup|them\b|nørre snede|østjylland|midtjylland",
    re.I,
)

# Titler der aldrig er relevante (for senior, ledelse, studiejob, butik osv.).
EXCLUDE_TITLE = re.compile(
    r"\bsenior|\bsr\.?\s|\blead\b|leder\b|\w*chef\b|head of|director|direktør|\bvp\b|vice president|\bcfo\b|"
    r"\bpartner\b|erfaren|experienced|principal|expert|ekspert|interim|ansvarlig\b|"
    r"student|studie|studerende|praktik|intern\b|internship|elev\b|lærling|apprentice|frivillig|fleksjob|"
    r"butik|ekspedient|salgsassistent|kasseassistent|lagermedarbejder|chauffør|vagtplan|arbejdstidsplan|driftsplan|security|sikkerhed|"
    r"sygeplejer|lærer\b|pædagog|læge\b|tandlæge|bioanalytiker|laborant|postdoc|ph\.?d|lektor|professor|"
    r"forsker|researcher|adjunkt|ingeniør|engineer|developer|udvikler|scientist|architect|arkitekt",
    re.I,
)
# "Manager" er kun med, hvis titlen også siger junior/assistant.
MANAGER = re.compile(r"manager", re.I)
JUNIOR = re.compile(r"junior|assistant|assistent|graduate|trainee|nyuddannet", re.I)

# Mindst ét af disse skal stå i titlen.
RELEVANT_TITLE = re.compile(
    r"controller|controlling|analyst|analytiker|analyse|økonomi|finans|finance|financial|regnskab|bogholder|bogføring|account|revision|revisor|"
    r"business intelligence|\bbi\b|power bi|\bdata|rapportering|reporting|budget|planner|planlægger|planning|"
    r"forecast|demand|category|indkøb|purchas|procurement|buyer|supply chain|pricing|prisanaly|kreditor|debitor|"
    r"lønbogholder|payroll|treasury|fp&a|kalkul|commercial|sales support|salgssupport|excel|kpi|insight",
    re.I,
)

# Krav om 3+ års erfaring frasorteres.
TOO_MUCH_EXPERIENCE = re.compile(
    r"(?:minimum|mindst|min\.|over|flere end)?\s*\b([3-9]|1[0-9])\s*\+?\s*(?:-\s*\d+\s*)?(?:års|år)\b[^.\n]{0,60}erfaring"
    r"|\b([3-9]|1[0-9])\s*\+?\s*(?:-\s*\d+\s*)?years?\b[^.\n]{0,60}experience",
    re.I,
)
STUDY_JOB = re.compile(r"som frivillig|frivillige|ulønnet|studiejob|studenterjob|ved siden af (?:dit|dine) studie|studentermedhjælp|praktikplads|praktikforløb", re.I)

TEMPORARY = re.compile(
    r"barsel|vikariat|\bvikar\b|tidsbegræns|midlertidig|projektansættelse|projektansat|fixed[- ]term|temporary|"
    r"maternity|parental leave|ansættelsesperiode|\bfrem til (?:den )?\d|tiltrædelse[^.]{0,40}\bog til\b",
    re.I,
)
PART_TIME = re.compile(r"deltid|part[- ]time|\b(?:[12]\d|3[0-4])(?:[,.]\d+)?\s*timer?\s*(?:om|pr\.?|/|i)\s*ugen", re.I)
FULL_TIME = re.compile(r"fuldtid|full[- ]time|\b37\s*timer", re.I)

# Kort profil til LLM-vurderingen. Ingen kontaktoplysninger, da repoet er offentligt.
PROFILE = """\
Kandidat: 24 år, bor i Aarhus C, har bil. Færdig med HA (erhvervsøkonomi) med tilvalg i datalogi fra Aarhus Universitet i 2026.
Kan starte med det samme. Søger fuldtid eller deltid, gerne tidsbegrænset eller barselsvikariat, ikke studiejob eller praktik.
Erfaring: godt et års erfaring som student business analyst i en stor produktionsvirksomhed (dashboards i SAP Web Analytics,
Excel/Power Query på salgs- og fakturadata, KPI-opfølgning, budgetter og opfølgning for cost centers i logistik, prismodel).
Selvlært Power BI. Bachelorprojekt om ML-forecasting af salg. Tidligere tjener, skiinstruktør, medstifter af en lille it-virksomhed.
Stærkt engelsk. Vil ikke stå i butik.
Relevant: junior controller, økonomiassistent, business/data/BI-analytiker, planner, indkøb, pricing og andre job med Excel og tal,
som en nyuddannet med ca. 1 års studieerfaring realistisk kan få. Ikke relevant: krav om 3+ års erfaring, ledelse,
senior-stillinger, revisoruddannelse/HD som krav, rene udviklerjob, studiejob og praktik.
"""
LLM_MODEL = "claude-haiku-5-5"
LLM_MIN_SCORE = 6
