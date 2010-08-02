def lev(a, b):
    if not a: return len(b)
    if not b: return len(a)
    return min(lev(a[1:], b[1:])+(a[0] != b[0]), lev(a[1:], b)+1, lev(a, b[1:])+1)

def search_non_contiguous_strings(search, strings_to_search, case_sensitive=False):
    matches = []
    if not case_sensitive:
        search = search.lower()
    for string in strings_to_search:
        string = string.lower()
        oldindex = 0
        for char in search:
            result = string.find(char, oldindex)
            if result == -1:
                break
            else:
                oldindex = result
        else:
            print 'Levenshtein distance between %s and %s is %s' % (search, string, lev(search, string))
            matches.append(string)
    matches.sort(key=lambda k: lev(k, search))
    return matches

def search_strings(search, strings_to_search, case_sensitive=False):
    matches = []
    if not case_sensitive:
        search = search.lower()
    for string in strings_to_search:
        string = string.lower()
        if string.startswith(search):
            matches.append(string)
    matches.sort()
    return matches