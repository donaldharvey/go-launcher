def lev(a, b):
    if not a: return len(b)
    if not b: return len(a)
    return min(lev(a[1:], b[1:])+(a[0] != b[0]), lev(a[1:], b)+1, lev(a, b[1:])+1)

def search_non_contiguous_strings(search, strings_to_search, case_sensitive=False):
    matches = []
    if not case_sensitive:
        search = search.lower()
    for string in strings_to_search:
        lower_string = string.lower()
        oldindex = -1
        longest_substr = 1
        longest_substr_counter = 1
        longest_substr_index = 0
        for charindex, char in enumerate(search):
            result = lower_string.find(char, oldindex + 1)
            if result == -1:
                break
            else:
                if result - 1 == oldindex and charindex != 0: # Oldindex starts at 0, rather than -1
                    longest_substr_counter += 1
                    longest_substr_index = result - longest_substr_counter + 1
                    longest_substr = max(longest_substr_counter, longest_substr)
                else:
                    longest_substr_counter = 1
                    longest_substr_index = result
                oldindex = result
        else:
            print 'Longest substr', string[longest_substr_index:longest_substr_index+longest_substr]
            matches.append((string, longest_substr_index, longest_substr))
    matches.sort(key=lambda k: (k[1], -1 * k[2]))
    print 'Search string "%s" produced the following:' % search, matches
    return map(lambda m: m[0], matches)

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