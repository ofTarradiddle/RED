"""Structure the existing demo disclosure without changing its wording."""


def refine_masthead(page):
    """Mutate a parsed page, keeping the shared header and navigation intact.

    Splitting only the known leading label preserves whichever disclosure the
    publisher selected, including the SPY-based allocation variant. Repeated
    application leaves the same structure rather than nesting new wrappers.
    """
    banner = page.select_one('.demo-strip')
    if banner is None or banner.select_one('.masthead-status-inner'):
        return page

    original = banner.get_text(' ', strip=True)
    label = 'Illustrative demo'
    if not original.startswith(label):
        return page

    inner = page.new_tag('div', attrs={'class': 'masthead-status-inner'})
    name = page.new_tag('span', attrs={'class': 'masthead-status-label'})
    name.string = label
    inner.append(name)
    remainder = original[len(label):].lstrip()
    if remainder:
        inner.append(' ')
        detail = page.new_tag('span', attrs={'class': 'masthead-status-detail'})
        detail.string = remainder
        inner.append(detail)
    banner.clear()
    banner.append(inner)
    return page
