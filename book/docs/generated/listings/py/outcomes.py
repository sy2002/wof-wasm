# tools/junit_compare.py, lines 22-39
def outcomes(paths):
    """{test id: outcome} over the files, and the ids seen more than once."""
    seen = {}
    twice = []
    for path in paths:
        for case in ET.parse(path).getroot().iter('testcase'):
            test = '%s::%s' % (case.get('classname'), case.get('name').split('@', 1)[0])
            outcome = 'passed'
            for child in case:
                if child.tag in ('failure', 'error'):
                    outcome = child.tag
                    break
                if child.tag == 'skipped':
                    outcome = 'skipped: %s' % (child.get('message') or '').strip()
            if test in seen:
                twice.append(test)
            seen[test] = outcome
    return seen, twice
