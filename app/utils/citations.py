import re
from typing import List, Optional


def format_ieee(authors: List[str], title: str, venue: Optional[str], year: Optional[int], doi: Optional[str]) -> str:
    """IEEE format: [1] J. K. Author, "Title of paper," Abbrev. Title of Periodical, vol. x, no. x, pp. xxx-xxx, Abbrev. Month, year, doi: xxx."""
    formatted_authors = []
    for a in authors[:4]:
        parts = a.strip().split()
        if len(parts) > 1:
            initials = " ".join([p[0].upper() + "." for p in parts[:-1]])
            formatted_authors.append(f"{initials} {parts[-1]}")
        else:
            formatted_authors.append(a.strip())

    if len(authors) > 4:
        authors_str = ", ".join(formatted_authors) + ", et al."
    else:
        authors_str = " and ".join([", ".join(formatted_authors[:-1]), formatted_authors[-1]]) if len(formatted_authors) > 1 else (formatted_authors[0] if formatted_authors else "Unknown Author")

    venue_part = f", in *{venue}*" if venue else ""
    year_part = f", {year}" if year else ""
    doi_part = f", doi: {doi}" if doi else ""

    return f'{authors_str}, "{title}"{venue_part}{year_part}{doi_part}.'


def format_apa(authors: List[str], title: str, venue: Optional[str], year: Optional[int], doi: Optional[str]) -> str:
    """APA 7th: Author, A. A., & Author, B. B. (Year). Title of article. Title of Periodical, DOI."""
    formatted_authors = []
    for a in authors[:5]:
        parts = a.strip().split()
        if len(parts) > 1:
            initials = " ".join([p[0].upper() + "." for p in parts[:-1]])
            formatted_authors.append(f"{parts[-1]}, {initials}")
        else:
            formatted_authors.append(a.strip())

    if len(authors) > 5:
        authors_str = ", ".join(formatted_authors) + ", et al."
    elif len(formatted_authors) > 1:
        authors_str = ", & ".join([", ".join(formatted_authors[:-1]), formatted_authors[-1]])
    else:
        authors_str = formatted_authors[0] if formatted_authors else "Unknown Author"

    year_str = f" ({year})" if year else " (n.d.)"
    venue_str = f". *{venue}*" if venue else ""
    doi_str = f". https://doi.org/{doi}" if doi else ""

    return f"{authors_str}{year_str}. {title}{venue_str}{doi_str}."


def format_mla(authors: List[str], title: str, venue: Optional[str], year: Optional[int], doi: Optional[str]) -> str:
    """MLA 9th: Author. "Title." Container, Year, DOI."""
    if not authors:
        authors_str = "Unknown Author. "
    elif len(authors) == 1:
        parts = authors[0].split()
        authors_str = f"{parts[-1]}, {' '.join(parts[:-1])}. " if len(parts) > 1 else f"{authors[0]}. "
    elif len(authors) == 2:
        parts1 = authors[0].split()
        p1 = f"{parts1[-1]}, {' '.join(parts1[:-1])}" if len(parts1) > 1 else authors[0]
        authors_str = f"{p1}, and {authors[1]}. "
    else:
        parts1 = authors[0].split()
        p1 = f"{parts1[-1]}, {' '.join(parts1[:-1])}" if len(parts1) > 1 else authors[0]
        authors_str = f"{p1}, et al. "

    venue_str = f"*{venue}*, " if venue else ""
    year_str = f"{year}, " if year else ""
    doi_str = f"https://doi.org/{doi}." if doi else ""

    return f'{authors_str}"{title}." {venue_str}{year_str}{doi_str}'.strip()


def format_harvard(authors: List[str], title: str, venue: Optional[str], year: Optional[int], doi: Optional[str]) -> str:
    """Harvard style."""
    if not authors:
        authors_str = "Anon."
    elif len(authors) == 1:
        parts = authors[0].split()
        authors_str = f"{parts[-1]}, {' '.join([p[0].upper() + '.' for p in parts[:-1]])}" if len(parts) > 1 else authors[0]
    else:
        formatted = []
        for a in authors[:3]:
            parts = a.split()
            formatted.append(f"{parts[-1]}, {' '.join([p[0].upper() + '.' for p in parts[:-1]])}" if len(parts) > 1 else a)
        authors_str = " & ".join(formatted) + (" et al." if len(authors) > 3 else "")

    year_str = f" ({year})" if year else " (n.d.)"
    venue_str = f" *{venue}*." if venue else ""
    doi_str = f" Available at: https://doi.org/{doi}" if doi else ""

    return f"{authors_str}{year_str} '{title}',{venue_str}{doi_str}"


def format_bibtex(paper_id: int, authors: List[str], title: str, venue: Optional[str], year: Optional[int], doi: Optional[str]) -> str:
    """Generate valid BibTeX record."""
    first_author_last = "author"
    if authors:
        parts = authors[0].strip().split()
        first_author_last = re.sub(r"\W+", "", parts[-1].lower())

    first_word_title = re.sub(r"\W+", "", title.split()[0].lower()) if title else "paper"
    year_str = str(year) if year else "nodate"
    cite_key = f"{first_author_last}{year_str}{first_word_title}_{paper_id}"

    authors_joined = " and ".join(authors) if authors else "Unknown"
    lines = [
        f"@article{{{cite_key},",
        f"  title = {{{{{title}}}}},",
        f"  author = {{{authors_joined}}},",
    ]
    if venue:
        lines.append(f"  journal = {{{venue}}},")
    if year:
        lines.append(f"  year = {{{year}}},")
    if doi:
        clean_doi = doi.replace("https://doi.org/", "")
        lines.append(f"  doi = {{{clean_doi}}},")
        lines.append(f"  url = {{https://doi.org/{clean_doi}}},")
    lines.append("}")
    return "\n".join(lines)


def format_citation(style: str, authors: List[str], title: str, venue: Optional[str], year: Optional[int], doi: Optional[str]) -> str:
    style_upper = style.upper()
    if style_upper == "APA":
        return format_apa(authors, title, venue, year, doi)
    elif style_upper == "MLA":
        return format_mla(authors, title, venue, year, doi)
    elif style_upper == "HARVARD":
        return format_harvard(authors, title, venue, year, doi)
    else:  # default IEEE
        return format_ieee(authors, title, venue, year, doi)
