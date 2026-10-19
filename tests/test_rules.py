from finder import rules
from finder.job import Job


def j(title, text="", location="Aarhus", postcode=8000, source="Jobindex"):
    return Job(source=source, id="1", title=title, company="X", url="u", location=location, postcode=postcode, text=text)


def test_relevant_titles_pass():
    for t in ["Junior Controller", "Økonomiassistent", "Business Analyst", "Barselsvikar: Controller", "BI-analytiker",
              "Supply Chain Planner", "Indkøbsassistent", "Financial Analyst", "Regnskabsassistent til barselsvikariat"]:
        assert rules.reject_reason(j(t)) is None, t


def test_excluded_titles():
    for t in ["Senior Financial Controller", "Økonomichef", "Studentermedhjælper til økonomi", "Head of Finance",
              "Finance Manager", "Butiksassistent", "Praktikant i controlling", "Erfaren bogholder", "Data Engineer",
              "Pædagog"]:
        assert rules.reject_reason(j(t)), t


def test_junior_manager_allowed():
    assert rules.reject_reason(j("Junior Category Manager")) is None


def test_experience():
    assert rules.reject_reason(j("Controller", "Du har minimum 5 års erfaring med controlling"))
    assert rules.reject_reason(j("Controller", "You have 3+ years of experience in FP&A"))
    assert rules.reject_reason(j("Controller", "Gerne 1-2 års erfaring")) is None


def test_location():
    assert rules.reject_reason(j("Controller", postcode=6000, location="Kolding")) == "område: Kolding"
    assert rules.reject_reason(j("Controller", postcode=8600)) is None
    assert rules.reject_reason(j("Controller", postcode=7100)) is None
    assert rules.reject_reason(j("Controller", postcode=7500)) is not None
    assert rules.reject_reason(j("Controller", postcode=None, location="Silkeborg, Holstebro eller Kolding")) is None
    assert rules.reject_reason(j("Controller", postcode=None, location="Odense")) is not None


def test_fill_from_text():
    x = j("Controller", "Barselsvikariat fra 1. december. 30 timer om ugen.")
    rules.fill_from_text(x)
    assert x.temporary is True and x.hours == "deltid"
    y = j("Controller", "Fuldtidsstilling, 37 timer")
    rules.fill_from_text(y)
    assert y.hours == "fuldtid" and y.temporary is None


def test_dedupe_key():
    a = j("Junior Controller")
    b = j("Junior controller", source="LinkedIn")
    a.company, b.company = "Terma A/S", "Terma"
    assert rules.dedupe_key(a) == rules.dedupe_key(b)


def test_noise_titles():
    for t in ["Create great content and control the live stream", "Postdoc position in biology", "Bioanalytiker søges",
              "Vagtplanlægger", "Indkøbselev til vores Produktteam", "Planning Expert, Site Scheduling",
              "Data Scientist Supporting Global Planning", "Interim Financial Controller", "Regnskabsansvarlig",
              "Eksterne lektorer til undervisning på HD"]:
        assert rules.reject_reason(j(t)), t
    assert rules.reject_reason(j("Kasserer", "Vi søger en frivillig kasserer")), "frivillig"


def test_jobnet_hours_and_location():
    x = j("Lønbogholder – 30 timer", source="Jobnet")
    rules.fill_from_text(x)
    assert x.hours == "deltid"
    y = j("Økonomimedarbejder", source="Jobnet")
    rules.fill_from_text(y)
    assert y.hours == "fuldtid"
    assert rules.reject_reason(j("Controller", source="Jobnet", postcode=None, location="")) is not None
    assert rules.reject_reason(j("Controller", source="Jobnet", postcode=None, location="Thisted")) is not None
