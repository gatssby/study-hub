"""Pure deterministic discipline round robin; persistence belongs to the worker."""
import unicodedata
from .disciplines import discipline_for, pedagogical_key


def discipline(row):
    return discipline_for(row.get('subject'),row.get('front'),row.get('module'))


def discipline_key(name):
    return unicodedata.normalize('NFKD',name).encode('ascii','ignore').decode().casefold()


def choose(jobs,last_discipline=None):
    groups={}
    for job in jobs:groups.setdefault(discipline(job),[]).append(job)
    names=sorted(groups,key=discipline_key)
    if not names:return None
    after=[name for name in names if last_discipline is None or discipline_key(name)>discipline_key(last_discipline)]
    name=(after or names)[0]
    return min(groups[name],key=pedagogical_key)
