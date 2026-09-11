def test_dbg():
    import backend.app.main as m
    from collections import Counter
    print("app type:", type(m.app))
    c = Counter(type(r).__name__ for r in m.app.routes)
    print("tipos:", c)
    for r in m.app.routes[5:8]:
        print(" ->", type(r), repr(getattr(r, 'path', None)), repr(getattr(r, 'path_format', None)), dir(r)[:0])
        print("    attrs:", [a for a in ('path','routes','app','prefix') if hasattr(r,a)])
