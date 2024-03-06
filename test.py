import re


reg1 = re.compile(r'"text" *: *"((?:[^"]|\\\\"|\\.)*)"')


def get_plain_from_match(match, escaped=False, ord=1):
    plain = match if isinstance(match, str) else match.group(ord)
    if escaped:
        plain = re.sub(pattern=r'\\\\', string=plain, repl=r'\\')
    plain = re.sub(pattern=r'\\\\([^\\])', string=plain, repl=r'\\\1')
    plain = re.sub(pattern=r"\\'", string=plain, repl=r"'")
    return plain


def sub_replace(pattern: re.Pattern, string: str, repl, dupe=False, search_all=True):
    ls = list(string)
    if search_all:
        endless_count = 0
        last_match = None
        last_pos = 0
        match = pattern.search(string, last_pos)
        # can delete the 2 lines below
        # if match is None:
        #     return string
        while match is not None:
            if last_match is not None and last_match.string == match.string:
                endless_count += 1
                if endless_count >= 200:
                    print("ENDLESS LOOP HERE: " + string)
                    break  # prevent endless loop
            span = match.span()
            ls[span[0]:span[1]] = repl(match, dupe=dupe)
            last_pos = span[1]
            match = pattern.search(''.join(ls), last_pos)
            last_match = match
        return ''.join(ls)
    else:
        match = pattern.match(string)
        return string if match is None else repl(match, dupe=dupe)


def repls(a, dupe):
    print(a.group(1))
    b = get_plain_from_match(a.string)
    print(b)
    return '"translate":"aa"'


def main():
    string = '{"extra":[{"text":"/\\\\"}],"text":""}'
    # print(get_plain_from_match(string))
    print(sub_replace(reg1, string, repls))


if __name__ == "__main__":
    main()
