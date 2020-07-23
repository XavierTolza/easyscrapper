from urllib.request import urlopen


def wget(url, destfile):
    opened = urlopen(url)
    read = opened.read()
    save(read, destfile)


def save(content, file):
    wtype = ('wb' if type(content) == bytes else "w")
    with open(file, wtype) as f:
        f.write(content)
