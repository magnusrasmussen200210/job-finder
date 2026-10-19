from dataclasses import dataclass, field


@dataclass
class Job:
    source: str          # "Jobindex", "Jobnet", "LinkedIn"
    id: str
    title: str
    company: str
    url: str
    location: str = ""   # by/område som tekst
    postcode: int | None = None
    text: str = ""       # teaser eller hele opslaget
    hours: str | None = None       # "fuldtid" / "deltid"
    temporary: bool | None = None  # True = tidsbegrænset, False = fast
    deadline: str | None = None
    posted: str | None = None
    detail_url: str | None = None  # side med hele opslaget, hentes kun ved LLM-vurdering
    query: str = ""                # søgningen der fandt jobbet
    exclude: str | None = None     # sat af en kilde, hvis jobbet åbenlyst skal frasorteres

    @property
    def key(self):
        return f"{self.source}:{self.id}"
